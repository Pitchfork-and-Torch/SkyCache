"""v1.10.0 Federation Ops: doctor, gossip export/import, sim, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.nexus.federation_ops import (
    export_gossip,
    federation_doctor,
    import_gossip,
    run_federation_sim,
    write_federation_kit,
)
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.web.app import create_app


def _seed(tmp: Path) -> Settings:
    settings = Settings(data_dir=tmp / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()
    return settings


def test_federation_doctor_export_import(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = federation_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.federation.doctor.v1"
    assert doc["go_sim_federation"] is True

    gpath = tmp_path / "gossip.json"
    exp = export_gossip(gpath, data_dir=settings.data_dir)
    assert exp["ok"] is True
    assert gpath.is_file()

    other = Settings(data_dir=tmp_path / "peer", sim_mode=True)
    other.ensure_dirs()
    imp = import_gossip(gpath, data_dir=other.data_dir, peer_content_root=settings.content_dir)
    assert imp["ok"] is True


def test_federation_sim_and_kit(tmp_path: Path):
    settings = _seed(tmp_path)
    sim = run_federation_sim(data_dir=settings.data_dir, nodes=2, rounds=1)
    assert sim["ok"] is True
    assert Path(sim["receipt_path"]).is_file()

    kit = write_federation_kit(tmp_path / "federation-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (Path(kit["out_dir"]) / "FIELD-CHECKLIST.md").is_file()


def test_api_federation(tmp_path: Path):
    settings = _seed(tmp_path)
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/federation/status")
    assert r.status_code == 200
    assert r.json().get("doctor", {}).get("go_sim_federation") is True

    r2 = client.post("/api/federation/export-gossip", json={})
    assert r2.status_code == 200
    assert r2.json().get("ok") is True
