"""dtn export must honor limit=0 (no or-50 coercion)."""

from __future__ import annotations

import argparse
from pathlib import Path

from skycache.__main__ import cmd_dtn
from skycache.nexus.dtn_ops import dtn_enqueue, dtn_export


def _seed(data: Path, n: int = 3) -> None:
    data.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        dtn_enqueue(
            data_dir=data,
            kind="message",
            priority_class="general",
            destination="*",
            text=f"msg{i}",
            package_id="",
            ttl_sec=3600,
            hop_limit=8,
        )


def test_dtn_export_limit_zero_direct(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data, 3)
    rep = dtn_export(data_dir=data, out_dir=tmp_path / "mule0", limit=0)
    assert rep.get("ok") is True
    assert rep.get("verify", {}).get("bundle_count") == 0


def test_dtn_export_limit_zero_cli(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data, 3)
    out = tmp_path / "mule_cli"
    ns = argparse.Namespace(
        dtn_cmd="export",
        data_dir=str(data),
        out=str(out),
        limit=0,
    )
    rc = cmd_dtn(ns)
    assert rc == 0
    # Re-export via direct with same semantics to read count from last file
    files = list(out.glob("skycache-mule-*.json"))
    assert files, "expected mule file"
    import json

    body = json.loads(files[0].read_text(encoding="utf-8"))
    assert body.get("bundles") == []


def test_dtn_export_limit_two(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data, 4)
    rep = dtn_export(data_dir=data, out_dir=tmp_path / "mule2", limit=2)
    assert rep.get("ok") is True
    assert rep.get("verify", {}).get("bundle_count") == 2
