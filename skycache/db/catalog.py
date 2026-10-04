"""SQLite content catalog."""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from skycache.models import (
    ContentFile,
    ContentPackage,
    PackageRecord,
    PriorityClass,
    SourceInfo,
)
from skycache.policy.prioritizer import compute_score, hours_since


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Catalog:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            sql = resources.files("skycache.db").joinpath("schema.sql").read_text(encoding="utf-8")
        except Exception:
            # Fallback when not installed as package data
            sql_path = Path(__file__).with_name("schema.sql")
            sql = sql_path.read_text(encoding="utf-8")
        self._conn.executescript(sql)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def log_event(self, level: str, kind: str, message: str, meta: dict | None = None) -> None:
        self._conn.execute(
            "INSERT INTO events(ts, level, kind, message, meta_json) VALUES (?,?,?,?,?)",
            (
                _iso(_utc_now()),
                level,
                kind,
                message,
                json.dumps(meta or {}),
            ),
        )
        self._conn.commit()

    def upsert_package(self, package: ContentPackage, path: Path, score: float | None = None) -> float:
        sc = score if score is not None else compute_score(package)
        now = _iso(_utc_now())
        self._conn.execute(
            """
            INSERT INTO packages (
                id, kind, priority_class, title_json, summary_json, languages_json,
                received_at, freshness_hours, size_bytes, license, source_json,
                files_json, tags_json, pinned, icon, path, score, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                kind=excluded.kind,
                priority_class=excluded.priority_class,
                title_json=excluded.title_json,
                summary_json=excluded.summary_json,
                languages_json=excluded.languages_json,
                received_at=excluded.received_at,
                freshness_hours=excluded.freshness_hours,
                size_bytes=excluded.size_bytes,
                license=excluded.license,
                source_json=excluded.source_json,
                files_json=excluded.files_json,
                tags_json=excluded.tags_json,
                pinned=excluded.pinned,
                icon=excluded.icon,
                path=excluded.path,
                score=excluded.score,
                updated_at=excluded.updated_at
            """,
            (
                package.id,
                package.kind,
                package.priority_class.value,
                json.dumps(package.title, ensure_ascii=False),
                json.dumps(package.summary, ensure_ascii=False),
                json.dumps(package.languages),
                _iso(package.received_at),
                package.freshness_hours,
                package.size_bytes,
                package.license,
                package.source.model_dump_json(),
                json.dumps([f.model_dump() for f in package.files]),
                json.dumps(package.tags),
                1 if package.pinned else 0,
                package.icon,
                str(path),
                sc,
                now,
                now,
            ),
        )
        self._conn.commit()
        return sc

    def _row_to_package(self, row: sqlite3.Row) -> ContentPackage:
        return ContentPackage(
            id=row["id"],
            kind=row["kind"],
            priority_class=PriorityClass(row["priority_class"]),
            title=json.loads(row["title_json"]),
            summary=json.loads(row["summary_json"]),
            languages=json.loads(row["languages_json"]),
            received_at=_parse_dt(row["received_at"]),
            freshness_hours=row["freshness_hours"],
            size_bytes=row["size_bytes"],
            license=row["license"],
            source=SourceInfo.model_validate_json(row["source_json"]),
            files=[ContentFile.model_validate(f) for f in json.loads(row["files_json"])],
            tags=json.loads(row["tags_json"]),
            pinned=bool(row["pinned"]),
            icon=row["icon"],
        )

    def get(self, package_id: str) -> PackageRecord | None:
        cur = self._conn.execute("SELECT * FROM packages WHERE id=?", (package_id,))
        row = cur.fetchone()
        if not row:
            return None
        pkg = self._row_to_package(row)
        age = hours_since(pkg.received_at)
        return PackageRecord(
            package=pkg,
            score=row["score"],
            path=row["path"],
            age_hours=age,
            is_stale=age > pkg.freshness_hours,
        )

    def list_packages(
        self,
        priority_class: str | None = None,
        lang: str | None = None,
        q: str | None = None,
        limit: int = 200,
    ) -> list[PackageRecord]:
        sql = "SELECT * FROM packages"
        params: list[object] = []
        clauses: list[str] = []
        if priority_class:
            clauses.append("priority_class=?")
            params.append(priority_class)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY pinned DESC, score DESC, received_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        out: list[PackageRecord] = []
        for row in rows:
            pkg = self._row_to_package(row)
            if lang and lang not in pkg.languages and "en" not in pkg.languages:
                # Still allow packages with only other languages if no filter match preference
                if lang not in pkg.title:
                    continue
            if q:
                blob = json.dumps(pkg.title) + json.dumps(pkg.summary) + " ".join(pkg.tags)
                if q.lower() not in blob.lower():
                    continue
            age = hours_since(pkg.received_at)
            out.append(
                PackageRecord(
                    package=pkg,
                    score=row["score"],
                    path=row["path"],
                    age_hours=age,
                    is_stale=age > pkg.freshness_hours,
                )
            )
        return out

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0])

    def total_size(self) -> int:
        row = self._conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM packages").fetchone()
        return int(row[0])

    def last_ingest(self) -> datetime | None:
        row = self._conn.execute(
            "SELECT received_at FROM packages ORDER BY received_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return _parse_dt(row["received_at"])

    def delete_package(self, package_id: str, remove_files: bool = True) -> bool:
        rec = self.get(package_id)
        if not rec:
            return False
        self._conn.execute("DELETE FROM packages WHERE id=?", (package_id,))
        self._conn.commit()
        if remove_files and rec.path:
            p = Path(rec.path)
            if p.exists() and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
        self.log_event("info", "evict", f"Removed package {package_id}")
        return True

    def candidates_for_eviction(self) -> list[PackageRecord]:
        """Lowest score first; never return pinned or emergency without pin check."""
        rows = self._conn.execute(
            """
            SELECT * FROM packages
            WHERE pinned=0 AND priority_class != 'emergency'
            ORDER BY score ASC, received_at ASC
            """
        ).fetchall()
        result: list[PackageRecord] = []
        for row in rows:
            pkg = self._row_to_package(row)
            age = hours_since(pkg.received_at)
            result.append(
                PackageRecord(
                    package=pkg,
                    score=row["score"],
                    path=row["path"],
                    age_hours=age,
                    is_stale=age > pkg.freshness_hours,
                )
            )
        return result

    def rescore_all(self) -> None:
        for rec in self.list_packages(limit=10_000):
            sc = compute_score(rec.package)
            self._conn.execute(
                "UPDATE packages SET score=?, updated_at=? WHERE id=?",
                (sc, _iso(_utc_now()), rec.package.id),
            )
        self._conn.commit()
