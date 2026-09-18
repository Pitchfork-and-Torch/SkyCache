"""BoardStore.list_posts must honor limit=0 (empty list)."""

from __future__ import annotations

from pathlib import Path

from skycache.community.boards import BoardStore


def test_list_posts_limit_zero(tmp_path: Path) -> None:
    store = BoardStore(tmp_path / "boards.db")
    store.post(board="school", author="a", title="t", body="hello")
    assert store.list_posts(limit=0) == []
    assert store.list_posts(board="school", limit=0) == []
    store.close()


def test_list_posts_limit_one(tmp_path: Path) -> None:
    store = BoardStore(tmp_path / "boards.db")
    store.post(board="school", author="a", title="t1", body="one")
    store.post(board="school", author="b", title="t2", body="two")
    got = store.list_posts(board="school", limit=1)
    assert len(got) == 1
    store.close()
