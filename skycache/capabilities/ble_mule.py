"""Phone handoff mule - file-based bridge (Bluetooth-ready packaging).

Physical BLE transfer is operator-device-specific; we export a standard mule
JSON+packages folder phones can copy over any local link (BT, USB, SD).
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from skycache.nexus.dtn import DtnQueue


def export_handoff_bundle(
    *,
    dtn: DtnQueue,
    content_dir: Path,
    package_ids: list[str],
    out_dir: Path,
    node_id: str,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    bundle = out_dir / f"skycache-handoff-{stamp}"
    bundle.mkdir(parents=True, exist_ok=True)
    packs = bundle / "packages"
    packs.mkdir(exist_ok=True)
    copied = []
    for pid in package_ids:
        src = Path(content_dir) / pid
        if src.is_dir():
            dest = packs / pid
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            copied.append(pid)
    mule = dtn.export_mule(bundle / "dtn")
    meta = {
        "format": "skycache-handoff-v1",
        "node_id": node_id,
        "packages": copied,
        "dtn_mule": str(mule.name),
        "legal": (
            "Open content handoff only. User-consented local transfer. "
            "Not commercial broadband tethering."
        ),
        "created_at": stamp,
    }
    (bundle / "handoff.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return bundle


def import_handoff_bundle(
    bundle_dir: Path,
    *,
    dtn: DtnQueue,
    content_dest: Path,
    node_id: str,
) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    meta_path = bundle_dir / "handoff.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.is_file() else {}
    packs = bundle_dir / "packages"
    imported_packs = []
    if packs.is_dir():
        content_dest = Path(content_dest)
        content_dest.mkdir(parents=True, exist_ok=True)
        for child in packs.iterdir():
            if child.is_dir():
                dest = content_dest / child.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(child, dest)
                imported_packs.append(child.name)
    dtn_dir = bundle_dir / "dtn"
    n_dtn = 0
    if dtn_dir.is_dir():
        for f in dtn_dir.glob("skycache-mule-*.json"):
            n_dtn += dtn.import_mule(f, node_id)
    return {
        "packages": imported_packs,
        "dtn_imported": n_dtn,
        "meta": meta,
    }
