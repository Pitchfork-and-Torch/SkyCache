"""Nexus HTTP API endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.web.app import create_app


def _client(tmp_path: Path) -> TestClient:
    data = tmp_path / "data"
    settings = Settings(
        data_dir=data,
        sim_mode=True,
        admin_pin="2468",
        mesh_mode="sim",
        mesh_band="sim",
        nexus_enabled=True,
    )
    settings.ensure_dirs()
    cat = Catalog(settings.db_path)
    if samples_dir().is_dir():
        ContentManager(settings, cat).load_samples(samples_dir())
    cat.close()
    return TestClient(create_app(settings))


def test_nexus_status_endpoints(tmp_path: Path):
    client = _client(tmp_path)
    r = client.get("/api/nexus/status")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "SkyCache Nexus"
    assert "banner" in body
    assert "mesh" in body
    assert "gateway" in body
    assert body["spectrum"]["satellite_tx_allowed"] is False

    r = client.get("/api/nexus/mesh")
    assert r.status_code == 200
    assert r.json()["mode"] == "sim"

    r = client.get("/api/nexus/gateway")
    assert r.status_code == 200

    r = client.get("/api/nexus/fabric")
    assert r.status_code == 200
    assert "packages" in r.json()


def test_nexus_request_and_admin_disaster(tmp_path: Path):
    client = _client(tmp_path)
    r = client.post(
        "/api/nexus/request",
        json={"package_id": "health-ors-001", "priority_class": "health"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    r = client.post(
        "/api/admin/disaster",
        headers={"X-Admin-Pin": "2468"},
        json={"enabled": True},
    )
    assert r.status_code == 200
    assert r.json()["disaster_mode"] is True

    r = client.get("/api/admin/status", headers={"X-Admin-Pin": "2468"})
    assert r.status_code == 200
    admin = r.json()
    assert "nexus_dtn" in admin
    assert "gateway" in admin
    assert "Starlink" in admin["legal"] or "broadband" in admin["legal"].lower()


def test_status_legal_banner(tmp_path: Path):
    client = _client(tmp_path)
    r = client.get("/api/status")
    assert r.status_code == 200
    banner = r.json().get("legal_banner", "")
    assert banner
    assert "Starlink" in banner or "broadband" in banner.lower() or "mesh" in banner.lower()
