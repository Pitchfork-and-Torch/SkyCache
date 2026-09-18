"""Skybrary search/list_works honor --limit 0 (empty), not max(1, limit)."""
from __future__ import annotations

from pathlib import Path

from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.models import Work


def _seed(sky: SkybraryCatalog, n: int = 5) -> None:
    for i in range(n):
        sky.upsert_work(
            Work(
                work_id=f"w{i}",
                title={"en": f"Title {i}"},
                creators=["A"],
                languages=["en"],
                subjects=["s"],
                license="PD",
                summary={"en": f"hello world body {i}"},
            ),
            body_text=f"hello world body {i}",
        )


def test_search_limit_zero_returns_empty(tmp_path: Path) -> None:
    sky = SkybraryCatalog(tmp_path / "sky.db")
    try:
        _seed(sky)
        assert sky.search("hello", limit=0) == []
        assert len(sky.search("hello", limit=2)) == 2
    finally:
        sky.close()


def test_list_works_limit_zero_returns_empty(tmp_path: Path) -> None:
    sky = SkybraryCatalog(tmp_path / "sky.db")
    try:
        _seed(sky)
        assert sky.list_works(limit=0) == []
        assert len(sky.list_works(limit=3)) == 3
    finally:
        sky.close()
