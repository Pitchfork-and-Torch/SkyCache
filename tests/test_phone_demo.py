"""Phone-offline demo texts: local hub only, no cell plan required."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.skybrary.phone_demo import (
    DEMO_WORK_IDS,
    ZIP_FILENAME,
    build_demo_zip_bytes,
    demos_ready,
    ensure_demo_texts,
)
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.web.app import create_app


def test_ensure_and_zip_three_demos(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    assert not demos_ready(settings, sky)

    result = ensure_demo_texts(settings, sky)
    assert result["ok"] is True
    expected = len(DEMO_WORK_IDS)
    assert expected >= 3
    assert result["count_ready"] == expected
    assert result["count_expected"] == expected
    assert demos_ready(settings, sky)

    # Idempotent
    again = ensure_demo_texts(settings, sky)
    assert again["ok"] is True
    assert again["loaded_now"] is False

    data, n = build_demo_zip_bytes(settings)
    assert n == expected
    assert len(data) > 500
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        for wid in DEMO_WORK_IDS:
            assert f"{wid}/work.txt" in names
            body = zf.read(f"{wid}/work.txt").decode("utf-8")
            assert len(body) > 50
    sky.close()


def test_api_demo_pack_download(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True, admin_pin="2468")
    settings.ensure_dirs()
    client = TestClient(create_app(settings))

    r = client.get("/api/demo")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["count_ready"] == len(DEMO_WORK_IDS)
    assert body["count_ready"] >= 3
    assert body["download_all_path"] == "/api/demo/pack.zip"
    assert len(body["phone_steps"]) >= 3
    assert "cell" in body["honest"].lower() or "Wi-Fi" in body["honest"]

    r = client.get("/api/demo/pack.zip")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert ZIP_FILENAME in cd
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert len([n for n in zf.namelist() if n.endswith("work.txt")]) == len(DEMO_WORK_IDS)

    # Per-file download disposition
    wid = DEMO_WORK_IDS[0]
    r = client.get(f"/content/{wid}/work.txt?download=1")
    assert r.status_code == 200
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()
    assert b"Fox" in r.content or b"fox" in r.content.lower()

    # Onboarding mentions phone demo
    r = client.get("/api/onboarding")
    assert r.status_code == 200
    steps = r.json().get("steps") or []
    ids = [s.get("id") for s in steps]
    assert "phone_demo" in ids
    assert r.json().get("demo_download_path") == "/api/demo/pack.zip"
