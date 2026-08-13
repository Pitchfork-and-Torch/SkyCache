"""Skybrary works catalog with SQLite FTS5 full-text search."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.skybrary.license_gate import assert_license_allowed
from skycache.skybrary.models import Edition, Work

WORKS_MANIFEST_FORMAT = "skycache-works-manifest-v1"


def _iso(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class SkybraryCatalog:
    """Separate SQLite file (skybrary.db) for works/editions + FTS."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS works (
                work_id TEXT PRIMARY KEY,
                title_json TEXT NOT NULL,
                creators_json TEXT NOT NULL,
                languages_json TEXT NOT NULL,
                subjects_json TEXT NOT NULL,
                era TEXT,
                license TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                civilizational_tier INTEGER NOT NULL DEFAULT 3,
                summary_json TEXT NOT NULL,
                package_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS editions (
                edition_id TEXT PRIMARY KEY,
                work_id TEXT NOT NULL,
                format TEXT NOT NULL,
                path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL DEFAULT '',
                priority_class TEXT NOT NULL DEFAULT 'education',
                received_at TEXT NOT NULL,
                FOREIGN KEY (work_id) REFERENCES works(work_id)
            );

            CREATE INDEX IF NOT EXISTS idx_works_license ON works(license);
            CREATE INDEX IF NOT EXISTS idx_works_tier ON works(civilizational_tier);
            CREATE INDEX IF NOT EXISTS idx_editions_work ON editions(work_id);

            CREATE VIRTUAL TABLE IF NOT EXISTS works_fts USING fts5(
                work_id UNINDEXED,
                title,
                creators,
                subjects,
                summary,
                body,
                tokenize = 'porter unicode61'
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert_work(
        self,
        work: Work,
        *,
        package_id: str | None = None,
        body_text: str = "",
    ) -> None:
        assert_license_allowed(work.license)
        now = _iso()
        title_en = work.title.get("en") or next(iter(work.title.values()), work.work_id)
        summary_en = work.summary.get("en") or ""
        creators = ", ".join(work.creators)
        subjects = ", ".join(work.subjects)

        self._conn.execute(
            """
            INSERT INTO works (
                work_id, title_json, creators_json, languages_json, subjects_json,
                era, license, provenance_json, civilizational_tier, summary_json,
                package_id, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(work_id) DO UPDATE SET
                title_json=excluded.title_json,
                creators_json=excluded.creators_json,
                languages_json=excluded.languages_json,
                subjects_json=excluded.subjects_json,
                era=excluded.era,
                license=excluded.license,
                provenance_json=excluded.provenance_json,
                civilizational_tier=excluded.civilizational_tier,
                summary_json=excluded.summary_json,
                package_id=COALESCE(excluded.package_id, works.package_id),
                updated_at=excluded.updated_at
            """,
            (
                work.work_id,
                json.dumps(work.title, ensure_ascii=False),
                json.dumps(work.creators, ensure_ascii=False),
                json.dumps(work.languages, ensure_ascii=False),
                json.dumps(work.subjects, ensure_ascii=False),
                work.era,
                work.license,
                json.dumps(work.provenance, ensure_ascii=False),
                int(work.civilizational_tier),
                json.dumps(work.summary, ensure_ascii=False),
                package_id,
                now,
                now,
            ),
        )
        # FTS rebuild row
        self._conn.execute("DELETE FROM works_fts WHERE work_id=?", (work.work_id,))
        self._conn.execute(
            """
            INSERT INTO works_fts(work_id, title, creators, subjects, summary, body)
            VALUES (?,?,?,?,?,?)
            """,
            (work.work_id, title_en, creators, subjects, summary_en, body_text or summary_en),
        )
        self._conn.commit()

    def upsert_edition(self, edition: Edition) -> None:
        self._conn.execute(
            """
            INSERT INTO editions (
                edition_id, work_id, format, path, size_bytes, sha256,
                priority_class, received_at
            ) VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(edition_id) DO UPDATE SET
                format=excluded.format,
                path=excluded.path,
                size_bytes=excluded.size_bytes,
                sha256=excluded.sha256,
                priority_class=excluded.priority_class,
                received_at=excluded.received_at
            """,
            (
                edition.edition_id,
                edition.work_id,
                edition.format,
                edition.path,
                int(edition.size_bytes),
                edition.sha256,
                edition.priority_class,
                _iso(edition.received_at),
            ),
        )
        self._conn.commit()

    def get_work(self, work_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM works WHERE work_id=?", (work_id,)
        ).fetchone()
        if not row:
            return None
        return self._work_row(row)

    def list_editions(self, work_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM editions WHERE work_id=? ORDER BY format",
            (work_id,),
        ).fetchall()
        return [self._edition_row(r) for r in rows]

    def search(
        self,
        q: str = "",
        *,
        language: str | None = None,
        subject: str | None = None,
        license_q: str | None = None,
        era: str | None = None,
        max_tier: int | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        q = (q or "").strip()
        work_ids: list[str] | None = None

        if q:
            # FTS5: AND terms for multi-word queries
            terms = [t.replace('"', "") for t in q.split() if t.replace('"', "").strip()]
            safe = " ".join(terms)
            if not safe:
                work_ids = []
            else:
                try:
                    fts_rows = self._conn.execute(
                        """
                        SELECT work_id FROM works_fts
                        WHERE works_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (safe, limit * 3),
                    ).fetchall()
                    work_ids = [r["work_id"] for r in fts_rows]
                except sqlite3.OperationalError:
                    work_ids = None

        sql = "SELECT * FROM works WHERE 1=1"
        params: list[object] = []
        if work_ids is not None:
            if not work_ids:
                return []
            placeholders = ",".join("?" * len(work_ids))
            sql += f" AND work_id IN ({placeholders})"
            params.extend(work_ids)
        if language:
            sql += " AND languages_json LIKE ?"
            params.append(f"%{language}%")
        if subject:
            sql += " AND subjects_json LIKE ?"
            params.append(f"%{subject}%")
        if license_q:
            sql += " AND license LIKE ?"
            params.append(f"%{license_q}%")
        if era:
            sql += " AND era = ?"
            params.append(era)
        if max_tier is not None:
            sql += " AND civilizational_tier <= ?"
            params.append(int(max_tier))

        sql += " ORDER BY civilizational_tier ASC, work_id ASC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        out = [self._work_row(r) for r in rows]
        # Preserve FTS rank order when possible
        if work_ids:
            order = {wid: i for i, wid in enumerate(work_ids)}
            out.sort(key=lambda w: order.get(w["work_id"], 9999))
        return out

    def facets(self) -> dict[str, Any]:
        langs: dict[str, int] = {}
        subjects: dict[str, int] = {}
        licenses: dict[str, int] = {}
        eras: dict[str, int] = {}
        for row in self._conn.execute("SELECT languages_json, subjects_json, license, era FROM works"):
            for lang in json.loads(row["languages_json"] or "[]"):
                langs[lang] = langs.get(lang, 0) + 1
            for sub in json.loads(row["subjects_json"] or "[]"):
                subjects[sub] = subjects.get(sub, 0) + 1
            lic = row["license"] or "unknown"
            licenses[lic] = licenses.get(lic, 0) + 1
            if row["era"]:
                eras[row["era"]] = eras.get(row["era"], 0) + 1
        return {
            "languages": dict(sorted(langs.items(), key=lambda x: -x[1])),
            "subjects": dict(sorted(subjects.items(), key=lambda x: -x[1])),
            "licenses": dict(sorted(licenses.items(), key=lambda x: -x[1])),
            "eras": dict(sorted(eras.items(), key=lambda x: -x[1])),
            "work_count": self.count(),
        }

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM works").fetchone()[0])

    def list_works(self, *, limit: int = 10_000) -> list[dict[str, Any]]:
        """All works ordered by tier (no FTS). Used for federation manifests."""
        limit = max(1, min(int(limit), 50_000))
        rows = self._conn.execute(
            """
            SELECT * FROM works
            ORDER BY civilizational_tier ASC, work_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._work_row(r) for r in rows]

    def works_manifest(
        self,
        *,
        node_id: str = "",
        max_works: int = 10_000,
        compact: bool = False,
        max_tier: int | None = None,
    ) -> dict[str, Any]:
        """Lightweight works catalog snapshot for mesh gossip / federation.

        Metadata only (no full text bodies). Sim-friendly file or DTN payload.

        compact=True: smaller wire form for large catalogs (no summary/provenance/
        full editions path list). Prefer foundational civilizational_tier first.
        max_tier: if set, only include works with civilizational_tier <= max_tier.
        """
        # Over-fetch then filter so tier preference still works on large nodes
        fetch_n = max_works if max_tier is None else min(50_000, max(max_works * 4, max_works))
        works = self.list_works(limit=fetch_n)
        # Foundational first (lower tier number)
        works.sort(
            key=lambda w: (
                int(w.get("civilizational_tier") or 5),
                str(w.get("work_id") or ""),
            )
        )
        entries: list[dict[str, Any]] = []
        for w in works:
            tier = int(w.get("civilizational_tier") or 5)
            if max_tier is not None and tier > int(max_tier):
                continue
            if compact:
                eds = w.get("editions") or []
                primary = eds[0] if eds else {}
                entries.append(
                    {
                        "work_id": w["work_id"],
                        "title": w["title"],
                        "languages": w["languages"],
                        "license": w["license"],
                        "civilizational_tier": tier,
                        "package_id": w["package_id"],
                        "edition_count": len(eds),
                        "primary_format": primary.get("format") or "",
                        "primary_sha256": primary.get("sha256") or "",
                        "size_bytes": int(primary.get("size_bytes") or 0),
                    }
                )
            else:
                entries.append(
                    {
                        "work_id": w["work_id"],
                        "title": w["title"],
                        "creators": w["creators"],
                        "languages": w["languages"],
                        "subjects": w["subjects"],
                        "era": w["era"],
                        "license": w["license"],
                        "civilizational_tier": tier,
                        "package_id": w["package_id"],
                        "summary": w["summary"],
                        "provenance": w["provenance"],
                        "editions": [
                            {
                                "edition_id": e["edition_id"],
                                "format": e["format"],
                                "size_bytes": e.get("size_bytes") or 0,
                                "sha256": e.get("sha256") or "",
                                "priority_class": e.get("priority_class") or "education",
                                "path": e.get("path") or "",
                            }
                            for e in (w.get("editions") or [])
                        ],
                    }
                )
            if len(entries) >= max_works:
                break
        return {
            "format": WORKS_MANIFEST_FORMAT,
            "node_id": node_id,
            "ts": time.time(),
            "work_count": len(entries),
            "compact": bool(compact),
            "max_tier": max_tier,
            "works": entries,
            "legal": (
                "Open/PD works metadata only - federation gossip, not a "
                "complete archive claim. Bodies transfer via packages/handoff."
            ),
        }

    def export_works_manifest(
        self,
        path: Path,
        *,
        node_id: str = "",
        max_works: int = 10_000,
    ) -> Path:
        """Write works_manifest JSON to path (UTF-8, no BOM)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.works_manifest(node_id=node_id, max_works=max_works)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def import_works_manifest(
        self,
        source: Path | dict[str, Any],
        *,
        skip_invalid_license: bool = True,
    ) -> dict[str, Any]:
        """Merge a peer works_manifest into this catalog (metadata + editions).

        Does not copy package files - pair with handoff/fabric package pull.
        """
        if isinstance(source, Path):
            raw = json.loads(Path(source).read_text(encoding="utf-8-sig"))
        else:
            raw = source
        if not isinstance(raw, dict):
            raise ValueError("works_manifest must be a JSON object")
        fmt = raw.get("format") or ""
        if fmt and fmt != WORKS_MANIFEST_FORMAT:
            raise ValueError(
                f"Unsupported works_manifest format '{fmt}' "
                f"(expected {WORKS_MANIFEST_FORMAT})"
            )
        works = list(raw.get("works") or [])
        imported = 0
        skipped = 0
        errors: list[str] = []
        for entry in works:
            if not isinstance(entry, dict):
                skipped += 1
                continue
            wid = str(entry.get("work_id") or "").strip()
            if not wid:
                skipped += 1
                continue
            lic = str(entry.get("license") or "unknown")
            try:
                title = entry.get("title") or {"en": wid}
                if isinstance(title, str):
                    title = {"en": title}
                work = Work(
                    work_id=wid,
                    title=title,
                    creators=list(entry.get("creators") or []),
                    languages=list(entry.get("languages") or ["en"]),
                    subjects=list(entry.get("subjects") or []),
                    era=entry.get("era"),
                    license=lic,
                    provenance=dict(
                        entry.get("provenance")
                        or {
                            "source": "works_manifest",
                            "compact": bool(raw.get("compact")),
                        }
                    ),
                    civilizational_tier=int(entry.get("civilizational_tier") or 3),
                    summary=entry.get("summary") or {},
                )
                package_id = entry.get("package_id")
                self.upsert_work(
                    work,
                    package_id=str(package_id) if package_id else None,
                    body_text="",  # metadata-only federation; body via package
                )
                editions = list(entry.get("editions") or [])
                # Compact gossip: synthesize a stub edition from primary_* fields
                if not editions and (
                    entry.get("primary_format") or entry.get("primary_sha256")
                ):
                    editions = [
                        {
                            "edition_id": f"{wid}-primary",
                            "format": entry.get("primary_format") or "txt",
                            "path": "",
                            "size_bytes": int(entry.get("size_bytes") or 0),
                            "sha256": entry.get("primary_sha256") or "",
                            "priority_class": "education",
                        }
                    ]
                for ed in editions:
                    if not isinstance(ed, dict):
                        continue
                    eid = str(ed.get("edition_id") or "").strip()
                    if not eid:
                        continue
                    self.upsert_edition(
                        Edition(
                            edition_id=eid,
                            work_id=wid,
                            format=str(ed.get("format") or "txt"),
                            path=str(ed.get("path") or ""),
                            size_bytes=int(ed.get("size_bytes") or 0),
                            sha256=str(ed.get("sha256") or ""),
                            priority_class=str(ed.get("priority_class") or "education"),
                        )
                    )
                imported += 1
            except (ValueError, TypeError) as exc:
                if skip_invalid_license:
                    skipped += 1
                    errors.append(f"{wid}: {exc}")
                    continue
                raise
        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:20],
            "source_node": raw.get("node_id") or "",
            "work_count_after": self.count(),
        }

    def _work_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "work_id": row["work_id"],
            "title": json.loads(row["title_json"]),
            "creators": json.loads(row["creators_json"]),
            "languages": json.loads(row["languages_json"]),
            "subjects": json.loads(row["subjects_json"]),
            "era": row["era"],
            "license": row["license"],
            "provenance": json.loads(row["provenance_json"] or "{}"),
            "civilizational_tier": row["civilizational_tier"],
            "summary": json.loads(row["summary_json"]),
            "package_id": row["package_id"],
            "editions": self.list_editions(row["work_id"]),
        }

    def _edition_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "edition_id": row["edition_id"],
            "work_id": row["work_id"],
            "format": row["format"],
            "path": row["path"],
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
            "priority_class": row["priority_class"],
            "received_at": row["received_at"],
        }
