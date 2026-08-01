"""Legal capability matrix, open fetch allowlist, pack profiles, verify."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skycache.capabilities.integrity_tree import verify_package_dir
from skycache.capabilities.matrix import build_capability_matrix
from skycache.capabilities.modes import LegalRfMode, validate_legal_rf_mode
from skycache.capabilities.open_fetch import validate_open_url
from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.skybrary.pack_profile import (
    BUILTIN_PROFILES,
    build_pack_from_profile,
    list_profiles,
)
from skycache.web.app import create_app


def test_legal_rf_modes():
    assert validate_legal_rf_mode("receive_only") == LegalRfMode.RECEIVE_ONLY
    assert validate_legal_rf_mode("ism_mesh") == LegalRfMode.ISM_MESH
    with pytest.raises(ValueError):
        validate_legal_rf_mode("satellite-uplink")
    with pytest.raises(ValueError):
        validate_legal_rf_mode("starlink-tx")
    with pytest.raises(ValueError):
        validate_legal_rf_mode("amateur_operator", amateur_license_affirmed=False)
    assert (
        validate_legal_rf_mode("amateur_operator", amateur_license_affirmed=True)
        == LegalRfMode.AMATEUR_OPERATOR
    )


def test_capability_matrix_and_open_url():
    m = build_capability_matrix(legal_rf_mode="ism_mesh", sim_mode=True)
    d = m.to_dict()
    assert d["summary"]["enabled"] >= 10
    assert any(c["id"] == "fta_weather_decode" for c in d["capabilities"])
    assert any(c["id"] == "wifi_mesh" for c in d["capabilities"])
    assert "Starlink" in " ".join(d["banned"]) or "starlink" in " ".join(d["banned"]).lower()
    validate_open_url("https://www.gutenberg.org/ebooks/123")
    with pytest.raises(ValueError):
        validate_open_url("https://evil.example/starlink-decrypt")
    with pytest.raises(ValueError):
        validate_open_url("https://not-allowlisted.example/file.txt")


def test_pack_profile_and_verify(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    assert list_profiles()
    meta = build_pack_from_profile(
        sky,
        "all-open-small",
        content_dir=settings.content_dir,
        out_dir=tmp_path / "pack",
    )
    assert meta["count"] >= 1
    # verify one package
    first = settings.content_dir / meta["selected_packages"][0]
    rep = verify_package_dir(first)
    assert rep["ok"] is True
    sky.close()


def test_pack_profiles_2_0_ids():
    ids = {p["id"] for p in list_profiles()}
    for required in (
        "emergency-health",
        "literacy-1gb",
        "stem-lite",
        "all-open-small",
        "literacy-100mb",
        "health-priority",
    ):
        assert required in ids
        assert required in BUILTIN_PROFILES
    eh = BUILTIN_PROFILES["emergency-health"]
    assert "emergency" in eh["prefer_priority_classes"]
    assert "health" in eh["prefer_priority_classes"]
    assert "emergency" in eh["include_priority_classes"]


def test_emergency_health_prefers_priority_packages(tmp_path: Path):
    """emergency-health must pick emergency/health content packages first."""
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    # Skybrary PD samples (education literature + hippocratic health_edu)
    bootstrap_samples_with_settings(settings, sky)
    # Field emergency/health sample packs from samples/packages
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    content.load_samples(samples_dir())
    catalog.close()

    meta = build_pack_from_profile(
        sky,
        "emergency-health",
        content_dir=settings.content_dir,
        out_dir=tmp_path / "pack-eh",
    )
    selected = meta["selected_packages"]
    assert meta["count"] >= 1
    # Must include field emergency/health packs when present on disk
    assert any("emergency" in s for s in selected), selected
    assert any("health" in s for s in selected), selected
    # Preferred classes should appear before pure education literature when both match
    classes = [row["priority_class"] for row in meta.get("selected") or []]
    if "emergency" in classes and "education" in classes:
        assert classes.index("emergency") < classes.index("education")
    if "health" in classes and "education" in classes:
        assert classes.index("health") < classes.index("education")

    # literacy-1gb / stem-lite / all-open-small still build
    for pid in ("literacy-1gb", "stem-lite", "all-open-small"):
        m = build_pack_from_profile(
            sky,
            pid,
            content_dir=settings.content_dir,
            out_dir=tmp_path / f"pack-{pid}",
        )
        assert "count" in m
        assert (tmp_path / f"pack-{pid}" / "profile-manifest.json").is_file()
    sky.close()


def test_admin_skybrary_pack_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        legal_rf_mode="hybrid_gateway",
        admin_pin="2468",
    )
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    catalog = Catalog(settings.db_path)
    ContentManager(settings, catalog).load_samples(samples_dir())
    catalog.close()
    sky.close()

    client = TestClient(create_app(settings))
    # no PIN
    r = client.post("/api/admin/skybrary/pack", json={"profile": "all-open-small"})
    assert r.status_code == 401

    r = client.post(
        "/api/admin/skybrary/pack",
        json={"profile": "emergency-health"},
        headers={"X-Admin-Pin": "2468"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert "emergency-health" in body["out_dir"].replace("\\", "/")
    assert Path(body["out_dir"]).is_dir()
    assert (Path(body["out_dir"]) / "profile-manifest.json").is_file()

    r = client.post(
        "/api/admin/skybrary/pack",
        json={"profile": "not-a-real-profile"},
        headers={"X-Admin-Pin": "2468"},
    )
    assert r.status_code == 400


def test_capabilities_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        legal_rf_mode="hybrid_gateway",
    )
    settings.ensure_dirs()
    client = TestClient(create_app(settings))
    r = client.get("/api/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["legal_rf_mode"] == "hybrid_gateway"
    assert body["summary"]["total"] >= 15
    r = client.get("/api/skybrary/profiles")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert "emergency-health" in ids
    assert "stem-lite" in ids
    assert len(r.json()) >= 4
