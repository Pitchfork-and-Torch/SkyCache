"""Skybrary S2: FTS catalog, facets, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.web.app import create_app


def test_fts_search_and_facets(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    ids = bootstrap_samples_with_settings(settings, sky)
    assert len(ids) >= 3
    hits = sky.search("liberty")
    assert any("gettysburg" in h["work_id"] for h in hits)
    fox = sky.search("fox grapes")
    assert any("aesop" in h["work_id"] for h in fox)
    fac = sky.facets()
    assert fac["work_count"] >= 3
    assert "public domain" in " ".join(fac["licenses"].keys()) or fac["licenses"]
    lit = sky.search("", subject="literacy")
    assert lit
    sky.close()


def test_skybrary_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        admin_pin="2468",
    )
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()

    client = TestClient(create_app(settings))
    r = client.get("/api/skybrary/status")
    assert r.status_code == 200
    assert r.json()["work_count"] >= 3
    r = client.get("/api/skybrary/works", params={"q": "oath"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert "facets" in body
    wid = body["results"][0]["work_id"]
    r = client.get(f"/api/skybrary/works/{wid}")
    assert r.status_code == 200
    r = client.get("/api/skybrary/facets")
    assert r.status_code == 200
