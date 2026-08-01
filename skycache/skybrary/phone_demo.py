"""Phone-offline demo texts - local hub Wi-Fi only (no cell plan required).

End-goal path for a person with a phone and no cellular service:
  1. Join the village / field hub SSID (unlicensed Wi-Fi AP).
  2. Open the captive portal / SkyCache PWA.
  3. Save the three public-domain demo texts to the phone (zip or per-file).

This module never needs the public internet. Demos are curated PD samples
shipped with SkyCache - not a complete archive, not commercial broadband.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.skybrary.sample_corpus import SAMPLES

# Stable package / work ids for the three demo texts
DEMO_WORK_IDS: tuple[str, ...] = tuple(s["work_id"] for s in SAMPLES)

ZIP_FILENAME = "skycache-skybrary-demo-3texts.zip"
ZIP_README = """SkyCache Skybrary - phone demo pack
====================================

Three short public-domain sample texts for offline demo use.

How you got this file
---------------------
You joined a local SkyCache hub Wi-Fi (no cell plan required) and saved
this zip from the village / field portal. The texts live on the hub disk;
they did not come from commercial satellite internet or the public cloud.

Contents
--------
- skybrary-pd-aesop-001/work.txt  - The Fox and the Grapes (Aesop)
- skybrary-pd-gettysburg-001/work.txt - Gettysburg Address (Lincoln)
- skybrary-pd-hippocratic-001/work.txt - Hippocratic Oath (PD excerpt)

Legal
-----
Public domain / open educational samples only.
Not medical advice. Not a complete archive of written knowledge.
Not free Starlink or commercial satellite broadband.

Software: https://github.com/Pitchfork-and-Torch/SkyCache
"""


def ensure_demo_texts(
    settings,
    sky: SkybraryCatalog,
    *,
    force_rebuild: bool = False,
) -> dict[str, Any]:
    """Ensure the three PD demos exist in content store + Skybrary catalog.

    Safe to call on every serve start. Idempotent unless force_rebuild.
    """
    loaded_now = False
    if force_rebuild or not demos_ready(settings, sky):
        bootstrap_samples_with_settings(settings, sky)
        loaded_now = True
    items = list_demo_items(settings, sky)
    ready = all(i.get("on_node") for i in items)
    return {
        "ok": ready,
        "loaded_now": loaded_now,
        "count_ready": sum(1 for i in items if i.get("on_node")),
        "count_expected": len(DEMO_WORK_IDS),
        "work_ids": list(DEMO_WORK_IDS),
        "items": items,
        "phone_path": (
            "Join hub Wi-Fi (no cell plan) -> open this portal -> "
            "Library -> Save demos to this phone"
        ),
        "download_all_path": "/api/demo/pack.zip",
        "honest": (
            "Local hub transfer only. Not free commercial broadband. "
            "Curated PD samples - not a complete archive."
        ),
    }


def demos_ready(settings, sky: SkybraryCatalog) -> bool:
    """True when all three demos are indexed and work.txt is on disk."""
    for wid in DEMO_WORK_IDS:
        work = sky.get_work(wid)
        if not work:
            return False
        pkg_id = work.get("package_id") or wid
        path = Path(settings.content_dir) / str(pkg_id) / "work.txt"
        if not path.is_file():
            alt = Path(settings.content_dir) / wid / "work.txt"
            if not alt.is_file():
                return False
    return True


def list_demo_items(settings, sky: SkybraryCatalog) -> list[dict[str, Any]]:
    """Metadata + on-node flags for each demo text."""
    titles = {s["work_id"]: s["title"].get("en", s["work_id"]) for s in SAMPLES}
    items: list[dict[str, Any]] = []
    for wid in DEMO_WORK_IDS:
        work = sky.get_work(wid)
        pkg_id = (work or {}).get("package_id") or wid
        work_path = Path(settings.content_dir) / str(pkg_id) / "work.txt"
        if not work_path.is_file():
            work_path = Path(settings.content_dir) / wid / "work.txt"
            if work_path.is_file():
                pkg_id = wid
        on_node = work_path.is_file()
        size = work_path.stat().st_size if on_node else 0
        items.append(
            {
                "work_id": wid,
                "package_id": pkg_id,
                "title": titles.get(wid, wid),
                "on_node": on_node,
                "skybrary_indexed": work is not None,
                "size_bytes": size,
                "read_path": f"/content/{pkg_id}/work.txt" if on_node else None,
                "download_path": (
                    f"/content/{pkg_id}/work.txt?download=1" if on_node else None
                ),
                "html_path": f"/content/{pkg_id}/index.html" if on_node else None,
            }
        )
    return items


def build_demo_zip_bytes(settings) -> tuple[bytes, int]:
    """Zip the three work.txt files (+ README). Raises FileNotFoundError if missing."""
    buf = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", ZIP_README)
        for wid in DEMO_WORK_IDS:
            src = Path(settings.content_dir) / wid / "work.txt"
            if not src.is_file():
                raise FileNotFoundError(f"Demo text not on this node: {wid}")
            zf.write(src, arcname=f"{wid}/work.txt")
            added += 1
    return buf.getvalue(), added


def demo_status_payload(
    settings,
    sky: SkybraryCatalog,
    *,
    ensure: bool = False,
) -> dict[str, Any]:
    """JSON for GET /api/demo (and optional ensure)."""
    if ensure:
        ensure_demo_texts(settings, sky)
    items = list_demo_items(settings, sky)
    ready_n = sum(1 for i in items if i.get("on_node"))
    ssid = getattr(settings, "hotspot_ssid", "SkyCache")
    return {
        "ok": ready_n >= len(DEMO_WORK_IDS),
        "version": "phone_demo_v1",
        "count_ready": ready_n,
        "count_expected": len(DEMO_WORK_IDS),
        "hotspot_ssid": ssid,
        "items": items,
        "download_all_path": "/api/demo/pack.zip",
        "download_all_filename": ZIP_FILENAME,
        "phone_steps": [
            f"Join Wi-Fi SSID: {ssid} (no cell plan).",
            "Open the captive portal or http://hub-ip:8080/ in the phone browser.",
            "Tap Library, then Save demos to this phone (downloads a zip).",
            "Or open each text and tap Save file - files land in phone Downloads/Files.",
        ],
        "zero_network": {
            "when": "Phone has no Wi-Fi AND no cell - cannot download over the air",
            "path": "/api/demo/zero-network",
            "kit_zip": "/api/demo/zero-network-kit.zip",
            "offline_html": "/api/demo/READ-OFFLINE.html",
            "transfer": ["USB/OTG", "microSD", "Bluetooth file send", "pre-deploy"],
            "open": "READ-OFFLINE.html on the phone (zero network to read)",
        },
        "honest": (
            "Hub Wi-Fi path needs local radio. Zero-radio phones need USB/SD/BT/pre-deploy kit. "
            "Not free commercial satellite broadband. "
            "Three curated public-domain samples - not a complete archive."
        ),
    }
