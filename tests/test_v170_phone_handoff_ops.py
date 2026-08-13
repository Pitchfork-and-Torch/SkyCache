"""v1.7.0 Phone Handoff Ops: doctor, join-card QR, export, import."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.capabilities.handoff_ops import (
    export_phone_handoff,
    handoff_doctor,
    import_phone_handoff,
    write_join_card,
)
from skycache.config import Settings
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


def test_join_card_and_qr(tmp_path: Path):
    out = tmp_path / "join"
    rep = write_join_card(
        out,
        portal_url="http://10.42.0.1:8080/",
        ssid="SkyCache-Test",
        node_name="lab",
    )
    assert rep["ok"] is True
    assert (out / "join.html").is_file()
    assert (out / "join-qr.svg").is_file()
    assert (out / "join.json").is_file()
    html = (out / "join.html").read_text(encoding="utf-8")
    assert "SkyCache-Test" in html
    assert "10.42.0.1" in html
    svg = (out / "join-qr.svg").read_text(encoding="utf-8")
    assert "<svg" in svg


def test_handoff_doctor_and_export_import(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = handoff_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.handoff.doctor.v1"
    assert doc["go_phone_path"] is True

    exp = export_phone_handoff(
        data_dir=settings.data_dir,
        limit=5,
        portal_url="http://192.168.4.1:8080/",
        ssid="SkyCache-Lab",
    )
    assert exp["ok"] is True
    assert Path(exp["bundle"]).is_dir()
    assert (settings.handoff_dir / "join.html").is_file()
    assert exp.get("zip")
    assert Path(exp["zip"]).is_file()

    # import into a second node
    other = Settings(data_dir=tmp_path / "node2", sim_mode=True)
    other.ensure_dirs()
    imp = import_phone_handoff(Path(exp["bundle"]), data_dir=other.data_dir)
    assert imp["ok"] is True
    assert len(imp.get("packages") or []) >= 1


def test_api_handoff(tmp_path: Path):
    settings = _seed(tmp_path)
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/handoff/status")
    assert r.status_code == 200
    assert r.json().get("go_phone_path") is True

    r2 = client.post(
        "/api/handoff/join-card",
        json={"portal_url": "http://10.0.0.1:8080/", "ssid": "Hub"},
    )
    assert r2.status_code == 200
    assert r2.json().get("ok") is True

    r3 = client.post("/api/handoff/export", json={"limit": 3})
    assert r3.status_code == 200
    assert r3.json().get("ok") is True
