"""_pack_freshness must honor its limit kwarg."""

from __future__ import annotations

from pathlib import Path

from skycache.ops.local_metrics import _pack_freshness


def test_pack_freshness_honors_limit(tmp_path: Path) -> None:
    for i in range(8):
        d = tmp_path / f"pkg{i}"
        d.mkdir()
        (d / "manifest.json").write_text("{}", encoding="utf-8")

    capped = _pack_freshness(tmp_path, limit=3)
    assert capped["packages"] == 3
    assert "scanned up to 3 package dirs" in capped["sample_limit_note"]
    assert capped["newest_mtime"] is not None

    full = _pack_freshness(tmp_path, limit=50)
    assert full["packages"] == 8


def test_pack_freshness_zero_limit(tmp_path: Path) -> None:
    d = tmp_path / "pkg0"
    d.mkdir()
    (d / "manifest.json").write_text("{}", encoding="utf-8")
    empty = _pack_freshness(tmp_path, limit=0)
    assert empty == {"packages": 0, "newest_mtime": None, "oldest_mtime": None}
