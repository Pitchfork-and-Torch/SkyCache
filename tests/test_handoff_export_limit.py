"""handoff export must honor limit=0 (no forced single package)."""

from __future__ import annotations

from pathlib import Path

from skycache.capabilities.handoff_ops import export_phone_handoff
from skycache.config import Settings


def _seed_packages(settings: Settings, n: int = 3) -> None:
    for i in range(n):
        d = settings.content_dir / f"pkg{i}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.json").write_text(
            '{"id":"pkg%d","title":{"en":"t"},"files":[]}' % i,
            encoding="utf-8",
        )


def test_export_phone_handoff_limit_zero(tmp_path: Path) -> None:
    data = tmp_path / "data"
    settings = Settings(data_dir=data)
    settings.ensure_dirs()
    _seed_packages(settings, 3)

    rep = export_phone_handoff(
        data_dir=data,
        out_dir=tmp_path / "out0",
        limit=0,
        include_join_card=False,
        zip_bundle=False,
    )
    assert rep.get("ok") is True
    assert rep.get("packages") == []


def test_export_phone_handoff_limit_two(tmp_path: Path) -> None:
    data = tmp_path / "data"
    settings = Settings(data_dir=data)
    settings.ensure_dirs()
    _seed_packages(settings, 4)

    rep = export_phone_handoff(
        data_dir=data,
        out_dir=tmp_path / "out2",
        limit=2,
        include_join_card=False,
        zip_bundle=False,
    )
    assert rep.get("ok") is True
    assert len(rep.get("packages") or []) == 2
