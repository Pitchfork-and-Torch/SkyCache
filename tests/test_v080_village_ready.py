"""v0.8.0 Village Ready + Skybrary Dual-Access - acceptance tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.health.power_guidance import hours_until_threshold, power_guidance
from skycache.ingest.normalizer import ContentManager
from skycache.models import PowerMode
from skycache.nexus.gateway import GatewayManager
from skycache.nexus.gateway_presets import PullReceiptLog, list_presets
from skycache.nexus.dtn import DtnQueue
from skycache.nexus.mesh_validate import validate_mesh_sim
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.catalog_export import export_works_catalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.skybrary.pack_profile import (
    build_pack_from_profile,
    get_profile,
    list_profiles,
    verify_pack_manifest,
)
from skycache.skybrary.provenance import provenance_report_from_content_dir
from skycache.web.app import create_app


def test_pack_profiles_20_include_stem_heritage_language():
    ids = {p["id"] for p in list_profiles()}
    assert "stem-2gb" in ids
    assert "local-heritage" in ids
    assert "emergency-health" in ids
    assert "language-xx" in ids
    lang = get_profile("language-sw")
    assert lang["languages"] == ["sw"]
    assert lang["id"] == "language-sw"


def test_pack_signed_manifest_and_verify(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    from skycache.config import samples_dir

    content.load_samples(samples_dir())
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    out = tmp_path / "kit"
    meta = build_pack_from_profile(
        sky,
        "all-open-small",
        content_dir=settings.content_dir,
        out_dir=out,
    )
    sky.close()
    catalog.close()
    assert meta["count"] >= 1
    assert meta.get("signed_manifest") is True
    assert meta["integrity"]["root_sha256"]
    assert (out / "profile-manifest.json").is_file()
    assert (out / "profile-manifest.sha256").is_file()
    v = verify_pack_manifest(out)
    assert v["ok"] is True


def test_power_guidance_hours_until_eco():
    g = power_guidance(80.0, PowerMode.NORMAL, on_ac=False, battery_wh=100.0)
    assert g["hours_until_eco"]["hours"] is not None
    assert g["hours_until_eco"]["hours"] > 0
    on_ac = hours_until_threshold(50.0, target_percent=40.0, on_ac=True)
    assert on_ac["hours"] is None
    assert on_ac["reason"] == "on_ac_or_charging"


def test_gateway_presets_and_receipts(tmp_path: Path):
    presets = list_presets()
    assert any(p["id"] == "gutenberg-sample" for p in presets)
    log = PullReceiptLog(tmp_path / "receipts.json")
    log.append({"ok": True, "bytes": 1024, "package_id": "demo"})
    s = log.summary()
    assert s["count"] == 1
    assert s["total_bytes"] == 1024

    dtn = DtnQueue(tmp_path / "dtn.json")
    gw = GatewayManager(
        dtn=dtn,
        node_id="n1",
        sim_uplink=True,
        receipt_log_path=tmp_path / "receipts2.json",
    )
    gw.request_package("pkg-a", priority_class="education")
    results = gw.schedule_pulls()
    assert results
    snap = gw.snapshot()
    assert "open_mirror_presets" in snap
    assert snap["receipts"]["count"] >= 1


def test_mesh_validate_2_and_3_node():
    r2 = validate_mesh_sim(nodes=2)
    assert r2["ok"] is True
    r3 = validate_mesh_sim(nodes=3)
    assert r3["ok"] is True


def test_catalog_export_and_provenance(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    out = tmp_path / "export"
    meta = export_works_catalog(sky, out, limit=100)
    sky.close()
    assert meta["ok"]
    assert (out / "catalog.json").is_file()
    assert (out / "index.html").is_file()
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="q"' in html and 'type="search"' in html
    assert 'id="works-data"' in html
    assert "works-data" in html
    assert "Not free commercial internet" in html
    cat = (out / "catalog.json").read_text(encoding="utf-8")
    # v0.9+ dual-access schema (v2); accept legacy v1 string only if present in older builds
    assert (
        "skycache.skybrary.catalog.v2" in cat
        or "skycache.skybrary.catalog.v1" in cat
    )
    assert "creators" in cat or "authors" in cat
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    from skycache.config import samples_dir

    content.load_samples(samples_dir())
    catalog.close()
    prov = provenance_report_from_content_dir(settings.content_dir)
    assert prov["item_count"] >= 1
    assert "items" in prov


def test_api_power_licenses_gateway_v080(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        admin_pin="1357",
        mock_battery_percent=72.0,
    )
    settings.ensure_dirs()
    client = TestClient(create_app(settings))

    r = client.get("/api/power/guidance")
    assert r.status_code == 200
    body = r.json()
    assert body["percent"] == 72.0
    assert "hours_until_eco" in body

    r = client.get("/api/power/maintainer-sheet")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "ECO" in r.text

    r = client.get("/api/licenses/export")
    assert r.status_code == 200
    assert "license" in r.text.lower()

    r = client.get("/api/nexus/gateway/presets")
    assert r.status_code == 200
    assert r.json()["presets"]

    r = client.post(
        "/api/admin/gateway/quota",
        headers={"X-Admin-Pin": "1357"},
        json={"daily_quota_mb": 250},
    )
    assert r.status_code == 200
    assert r.json()["daily_quota_mb"] == 250

    r = client.get("/api/skybrary/profiles")
    assert r.status_code == 200
    data = r.json()
    if isinstance(data, dict):
        profiles = data.get("profiles") or []
    else:
        profiles = data
    ids = {p["id"] for p in profiles if isinstance(p, dict) and "id" in p}
    assert "stem-2gb" in ids or "literacy-1gb" in ids
