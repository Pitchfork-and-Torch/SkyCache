"""Offline maps via MBTiles + content-addressed blobs (v0.9.2).

Multi-GB regional extracts stay **out of git**. Operators obtain legal OSM/MBTiles
files, put them in the blob store, and build maps-offline packs.

This module:
- Creates a tiny license-clean sample MBTiles (fixture / demo)
- Imports an operator MBTiles into blob store + package
- Documents regional extract workflow
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.skybrary.blob_store import BlobStore
from skycache.skybrary.integrity import sha256_file
from skycache.skybrary.license_gate import assert_license_allowed

# Minimal 1x1 PNG (67 bytes) for sample tile
_TINY_PNG = bytes(
    [
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
        0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00,
        0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE, 0xD4, 0xEF, 0x00, 0x00,
        0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ]
)


def write_sample_mbtiles(path: Path, *, name: str = "SkyCache sample region") -> Path:
    """Write a tiny valid MBTiles 1.3 SQLite for demos (not a real map corpus)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        path.unlink()
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
            """
            CREATE TABLE metadata (name text, value text);
            CREATE TABLE tiles (
              zoom_level integer,
              tile_column integer,
              tile_row integer,
              tile_data blob
            );
            CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);
            """
        )
        meta = {
            "name": name,
            "format": "png",
            "type": "baselayer",
            "version": "1.0.0",
            "description": (
                "SkyCache sample MBTiles fixture  -  1 demo tile. "
                "Not multi-GB regional data. Operator supplies real extracts."
            ),
            "attribution": "Sample tile for SkyCache maps-offline demo (CC-BY-4.0 packaging guide)",
            "minzoom": "0",
            "maxzoom": "0",
            "bounds": "-180.0,-85.0,180.0,85.0",
            "center": "0,0,0",
        }
        for k, v in meta.items():
            conn.execute("INSERT INTO metadata (name, value) VALUES (?, ?)", (k, v))
        # TMS row for z=0,x=0 -> y=0
        conn.execute(
            "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (0,0,0,?)",
            (_TINY_PNG,),
        )
        conn.commit()
    finally:
        conn.close()
    return path


def mbtiles_info(path: Path) -> dict[str, Any]:
    path = Path(path)
    conn = sqlite3.connect(str(path))
    try:
        meta = {
            r[0]: r[1]
            for r in conn.execute("SELECT name, value FROM metadata").fetchall()
        }
        n = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        return {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "tile_count": int(n),
            "metadata": meta,
        }
    finally:
        conn.close()


def import_mbtiles_to_pack(
    mbtiles_path: Path,
    out_pkg: Path,
    *,
    blobs: BlobStore | None = None,
    license_name: str = "ODbL",
    package_id: str = "maps-region-operator",
    title: str = "Offline region map (MBTiles)",
) -> dict[str, Any]:
    """Package an operator MBTiles file + optional blob store put."""
    lic = assert_license_allowed(license_name)
    mbtiles_path = Path(mbtiles_path)
    if not mbtiles_path.is_file():
        raise FileNotFoundError(mbtiles_path)
    info = mbtiles_info(mbtiles_path)
    out_pkg = Path(out_pkg)
    out_pkg.mkdir(parents=True, exist_ok=True)

    dest_name = "region.mbtiles"
    dest = out_pkg / dest_name
    dest.write_bytes(mbtiles_path.read_bytes())

    blob_meta = None
    if blobs is not None:
        blob_meta = blobs.put_file(
            dest,
            media_type="application/x-sqlite3",
            provenance={
                "source": "operator_mbtiles",
                "license": lic,
                "note": "Regional extract  -  not stored multi-GB in git",
            },
        )

    stamp = datetime.now(timezone.utc).isoformat()
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:40rem;margin:1.5rem auto;padding:0 1rem;line-height:1.5;
background:#0b1220;color:#f1f5f9}} h1{{color:#5eead4}} .meta{{color:#94a3b8}}</style></head><body>
<p class="meta">SkyCache maps-offline  |  license {lic}</p>
<h1>{title}</h1>
<p>MBTiles on this node: <code>{dest_name}</code> ({info['size_bytes']} bytes, {info['tile_count']} tiles).</p>
<p class="meta">SHA-256: {info['sha256'][:24]}...  |  Confirm ODbL/CC attribution before redistribute.</p>
<p>Multi-GB regional extracts are operator-supplied via blob store  -  never committed to the monorepo.</p>
</body></html>
"""
    (out_pkg / "index.html").write_text(html, encoding="utf-8")
    manifest = {
        "id": package_id,
        "kind": "maps_mbtiles",
        "priority_class": "maps",
        "title": {"en": title},
        "summary": {
            "en": f"Offline MBTiles pack ({info['tile_count']} tiles). License: {lic}."
        },
        "languages": ["en"],
        "received_at": stamp,
        "freshness_hours": 8760,
        "license": lic,
        "source": {
            "type": "mbtiles_import",
            "legal_note": "Operator-verified map license (often ODbL with attribution)",
            "extra": {
                "sha256": info["sha256"],
                "tile_count": info["tile_count"],
                "blob_sha256": (blob_meta or {}).get("sha256"),
                "subjects": ["maps", "mbtiles", "osm", "geography"],
            },
        },
        "files": [
            {"path": "index.html", "mime": "text/html", "role": "index"},
            {
                "path": dest_name,
                "mime": "application/x-sqlite3",
                "size_bytes": info["size_bytes"],
                "sha256": info["sha256"],
                "role": "payload",
            },
        ],
        "tags": ["maps", "mbtiles", "osm", "geography", "local_maps"],
        "icon": "maps",
        "size_bytes": info["size_bytes"] + len(html.encode("utf-8")),
    }
    (out_pkg / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "ok": True,
        "package_dir": str(out_pkg),
        "mbtiles": info,
        "blob": blob_meta,
        "license": lic,
        "legal": "Operator extracts only in large sizes; monorepo keeps sample fixtures tiny.",
    }
