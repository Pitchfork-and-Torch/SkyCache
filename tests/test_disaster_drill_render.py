"""Disaster drill printable render stays inside the repo by default."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_disaster_drill_printable.py"


def test_default_render_writes_only_in_repo(tmp_path: Path):
    """Bare script run must not create ~/skycache-web/..."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    out = tmp_path / "drill.html"
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    subprocess.check_call(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        env=env,
    )
    assert out.is_file() and out.stat().st_size > 100
    leaked = fake_home / "skycache-web"
    assert not leaked.exists(), f"unexpected write under HOME: {list(leaked.rglob('*'))}"


def test_also_web_opt_in(tmp_path: Path):
    out = tmp_path / "docs" / "drill.html"
    web = tmp_path / "web" / "downloads" / "drill.html"
    subprocess.check_call(
        [sys.executable, str(SCRIPT), "--out", str(out), "--also-web", str(web)]
    )
    assert out.is_file() and web.is_file()
