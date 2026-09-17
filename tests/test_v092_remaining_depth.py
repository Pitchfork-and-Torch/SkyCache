"""v0.9.2: downloadable SD kit hosting, dual-radio pack, MBTiles blobs, pagination support."""

from __future__ import annotations

import zipfile
from pathlib import Path

from skycache import __version__
from skycache.config import Settings
from skycache.deploy_pi import build_downloadable_sd_kit
from skycache.nexus.dual_radio_validation import board_matrix, write_validation_pack
from skycache.skybrary.blob_store import BlobStore
from skycache.skybrary.license_gate import license_allowed
from skycache.skybrary.mbtiles_pack import (
    import_mbtiles_to_pack,
    mbtiles_info,
    write_sample_mbtiles,
)


def test_version_092_plus():
    parts = [int(x) for x in __version__.split(".")[:3]]
    assert parts >= [0, 9, 2]


def test_downloadable_sd_kit_zip(tmp_path: Path):
    meta = build_downloadable_sd_kit(tmp_path / "dl")
    assert meta["ok"]
    z = Path(meta["zip"])
    assert z.is_file()
    assert z.stat().st_size > 500
    with zipfile.ZipFile(z, "r") as zf:
        names = zf.namelist()
        assert any(n.endswith("HOSTING.json") for n in names)
        assert any("bake-golden.sh" in n or "install-village-fabric" in n for n in names)
    assert "site" in meta["download_urls"]


def test_dual_radio_board_matrix_and_pack(tmp_path: Path):
    m = board_matrix()
    assert len(m["boards"]) >= 5
    ids = {b["id"] for b in m["boards"]}
    assert "rpi4-2gb" in ids
    assert "sim-laptop" in ids
    meta = write_validation_pack(tmp_path / "val")
    assert meta["ok"]
    assert meta["board_count"] >= 5
    assert (tmp_path / "val" / "storyboard.html").is_file()
    assert (tmp_path / "val" / "board-matrix.json").is_file()
    frames = list((tmp_path / "val" / "frames").glob("*.svg"))
    assert len(frames) >= 5


def test_sample_mbtiles_and_import_with_blob(tmp_path: Path):
    assert license_allowed("ODbL")
    mb = tmp_path / "sample.mbtiles"
    write_sample_mbtiles(mb)
    info = mbtiles_info(mb)
    assert info["tile_count"] >= 1
    assert info["size_bytes"] > 100
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    store = BlobStore(settings.data_dir / "blobs")
    meta = import_mbtiles_to_pack(
        mb,
        tmp_path / "pkg",
        blobs=store,
        license_name="ODbL",
    )
    assert meta["ok"]
    assert (tmp_path / "pkg" / "region.mbtiles").is_file()
    assert (tmp_path / "pkg" / "manifest.json").is_file()
    assert meta["blob"] and store.has(meta["blob"]["sha256"])


def test_webui_has_pagination_controls():
    root = Path(__file__).resolve().parents[1]
    html = (root / "webui" / "index.html").read_text(encoding="utf-8")
    css = (root / "webui" / "css" / "app.css").read_text(encoding="utf-8")
    js = (root / "webui" / "js" / "app.js").read_text(encoding="utf-8")
    assert "readerPaginate" in html
    assert "readerPagePrev" in html
    assert "paginate-on" in css
    assert "column" in css or "columns" in css
    assert "togglePagination" in js
    assert "readerPageNavigate" in js
