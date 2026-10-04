"""Zero-network kit: phone with no Wi-Fi and no cell can still *read* demos."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.skybrary.sample_corpus import SAMPLES
from skycache.skybrary.zero_network_kit import (
    HTML_NAME,
    KIT_FORMAT,
    KIT_ZIP_NAME,
    build_offline_reader_html,
    build_zero_network_zip_bytes,
    write_zero_network_kit,
)
from skycache.web.app import create_app


def test_write_kit_and_html_contains_all_texts(tmp_path: Path) -> None:
    out = tmp_path / "kit"
    meta = write_zero_network_kit(out)
    assert meta["format"] == KIT_FORMAT
    assert meta["work_count"] == len(SAMPLES)
    assert meta["work_count"] >= 3
    assert (out / HTML_NAME).is_file()
    assert (out / "README.txt").is_file()
    assert (out / "kit-manifest.json").is_file()
    html = (out / HTML_NAME).read_text(encoding="utf-8")
    assert "no Wi-Fi" in html or "No Wi-Fi" in html
    assert "Fox one day" in html
    assert "Four score and seven" in html
    assert "Apollo Physician" in html
    for s in SAMPLES:
        assert (out / "texts" / f"{s['work_id']}.txt").is_file()
        body = (out / "texts" / f"{s['work_id']}.txt").read_text(encoding="utf-8")
        assert len(body) > 50


def test_offline_html_no_external_network_deps() -> None:
    html = build_offline_reader_html()
    # No CDN / remote assets - must work file:// offline
    assert "http://" not in html
    assert "https://" not in html or "github.com" in html  # footer link only is ok text
    # Footer may mention github as plain text - ensure no script src external
    assert 'src="http' not in html
    assert "src='http" not in html
    assert 'href="http' not in html  # no stylesheet/script links
    assert "Four score" in html


def test_zip_and_api(tmp_path: Path) -> None:
    data, meta = build_zero_network_zip_bytes()
    assert meta["work_count"] == len(SAMPLES)
    assert meta["work_count"] >= 3
    assert len(data) > 1000
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert any(n.endswith(HTML_NAME) for n in names)
        assert any(n.endswith("README.txt") for n in names)

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True, admin_pin="2468")
    settings.ensure_dirs()
    client = TestClient(create_app(settings))

    r = client.get("/api/demo/zero-network")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "USB" in " ".join(body["transfer_paths"])
    assert body["download_kit_zip"] == "/api/demo/zero-network-kit.zip"

    r = client.get("/api/demo/READ-OFFLINE.html")
    assert r.status_code == 200
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()
    assert b"Fox" in r.content

    r = client.get("/api/demo/zero-network-kit.zip")
    assert r.status_code == 200
    assert KIT_ZIP_NAME in (r.headers.get("content-disposition") or "")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert any("READ-OFFLINE.html" in n for n in zf.namelist())

    # Hub Wi-Fi demo API advertises zero-network path
    r = client.get("/api/demo")
    assert r.status_code == 200
    zn = r.json().get("zero_network") or {}
    assert zn.get("kit_zip") == "/api/demo/zero-network-kit.zip"


def test_library_zero_network_zip_skips_self_include(tmp_path: Path) -> None:
    """Writing --out kit must not zip the growing kit zip into itself."""
    from skycache.ops.library_ops import write_library_zero_network

    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()
    # Stale large zip that would be re-included without the guard
    (kit_dir / KIT_ZIP_NAME).write_bytes(b"x" * 2_000_000)
    rep = write_library_zero_network(kit_dir, zip_bundle=True)
    assert rep["ok"] is True
    assert rep["work_count"] == len(SAMPLES)
    assert rep["parity"] is True
    zp = Path(rep["zip"])
    assert zp.is_file()
    assert zp.stat().st_size < 2_000_000
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        assert not any(n.lower().endswith(".zip") for n in names)
        assert any("READ-OFFLINE.html" in n for n in names)
        assert sum(1 for n in names if n.endswith(".txt") and "texts/" in n.replace("\\", "/")) >= len(
            SAMPLES
        )
