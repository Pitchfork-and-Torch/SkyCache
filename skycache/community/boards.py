"""Local community boards / forums (store-and-forward, no cloud)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_BOARDS = frozenset(
    {
        "general",
        "school",
        "clinic",
        "emergency",
        "farm",
        "announcements",
    }
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BoardStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS board_posts (
                id TEXT PRIMARY KEY,
                board TEXT NOT NULL DEFAULT 'general',
                author TEXT NOT NULL DEFAULT 'anonymous',
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                pinned INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_board_posts_board
                ON board_posts(board, created_at DESC);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def list_boards(self) -> list[dict[str, str]]:
        return [
            {"id": "announcements", "label": "Announcements"},
            {"id": "school", "label": "School"},
            {"id": "clinic", "label": "Clinic"},
            {"id": "emergency", "label": "Emergency"},
            {"id": "farm", "label": "Farm"},
            {"id": "general", "label": "General"},
        ]

    def post(
        self,
        *,
        board: str,
        title: str,
        body: str,
        author: str = "anonymous",
        pinned: bool = False,
    ) -> dict[str, Any]:
        board = (board or "general").lower().strip()
        if board not in ALLOWED_BOARDS:
            raise ValueError(f"Unknown board '{board}'")
        title = (title or "").strip()[:200]
        body = (body or "").strip()[:4000]
        author = (author or "anonymous").strip()[:64] or "anonymous"
        if not title or not body:
            raise ValueError("title and body required")
        # Soft anti-spam: reject obvious commercial-decrypt solicitations
        blob = f"{title} {body}".lower()
        for bad in ("starlink password", "decrypt card", "pirate stream"):
            if bad in blob:
                raise ValueError("Post refused: matches forbidden commercial-bypass language")

        pid = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO board_posts(id, board, author, title, body, created_at, pinned)
            VALUES (?,?,?,?,?,?,?)
            """,
            (pid, board, author, title, body, _iso(), 1 if pinned else 0),
        )
        self._conn.commit()
        return self.get(pid)  # type: ignore[return-value]

    def get(self, post_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM board_posts WHERE id=?", (post_id,)
        ).fetchone()
        return self._row(row) if row else None

    def list_posts(self, board: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        if board:
            rows = self._conn.execute(
                """
                SELECT * FROM board_posts WHERE board=?
                ORDER BY pinned DESC, created_at DESC LIMIT ?
                """,
                (board, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM board_posts
                ORDER BY pinned DESC, created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row(r) for r in rows]

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "board": row["board"],
            "author": row["author"],
            "title": row["title"],
            "body": row["body"],
            "created_at": row["created_at"],
            "pinned": bool(row["pinned"]),
        }
