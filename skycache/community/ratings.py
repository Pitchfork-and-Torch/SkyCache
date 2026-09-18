"""Anonymous local package ratings (no personal-data harvest)."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RatingsStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Tables created by Catalog schema; ensure present
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS package_ratings (
                package_id TEXT NOT NULL,
                voter_token TEXT NOT NULL,
                stars INTEGER NOT NULL CHECK (stars >= 1 AND stars <= 5),
                created_at TEXT NOT NULL,
                PRIMARY KEY (package_id, voter_token)
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def token_from_client(raw: str | None) -> str:
        """Hash optional client token - never store raw device identifiers."""
        base = (raw or "anonymous-local").strip()[:128]
        return hashlib.sha256(f"skycache-rate|{base}".encode()).hexdigest()[:32]

    def rate(self, package_id: str, stars: int, voter_token: str | None = None) -> dict[str, Any]:
        stars = int(stars)
        if stars < 1 or stars > 5:
            raise ValueError("stars must be 1..5")
        token = self.token_from_client(voter_token)
        self._conn.execute(
            """
            INSERT INTO package_ratings(package_id, voter_token, stars, created_at)
            VALUES (?,?,?,?)
            ON CONFLICT(package_id, voter_token) DO UPDATE SET
                stars=excluded.stars,
                created_at=excluded.created_at
            """,
            (package_id, token, stars, _iso()),
        )
        self._conn.commit()
        return self.summary(package_id)

    def summary(self, package_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n, COALESCE(AVG(stars),0) AS avg_stars
            FROM package_ratings WHERE package_id=?
            """,
            (package_id,),
        ).fetchone()
        return {
            "package_id": package_id,
            "count": int(row["n"] or 0),
            "average": round(float(row["avg_stars"] or 0), 2),
        }

    def top(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT package_id,
                   COUNT(*) AS n,
                   AVG(stars) AS avg_stars
            FROM package_ratings
            GROUP BY package_id
            HAVING n >= 1
            ORDER BY avg_stars DESC, n DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "package_id": r["package_id"],
                "count": int(r["n"]),
                "average": round(float(r["avg_stars"]), 2),
            }
            for r in rows
        ]
