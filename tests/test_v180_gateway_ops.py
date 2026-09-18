"""v1.8.0 Gateway Ops: doctor, pull-preset passport, receipts, ethics kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.nexus.gateway_ops import (
    gateway_doctor,
    gateway_receipts,
    pull_preset,
    write_ethics_kit,
)
from skycache.web.app import create_app


def test_gateway_doctor_and_dry_run(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    doc = gateway_doctor(data_dir=settings.data_dir, sim=True)
    assert doc["schema"] == "skycache.gateway.doctor.v1"
    assert doc["go_sim_gateway"] is True
    assert doc["preset_count"] >= 1

    dry = pull_preset("gutenberg-sample", data_dir=settings.data_dir, dry_run=True)
    assert dry["ok"] is True
    assert dry["mode"] == "dry_run"
    assert dry["passport"]["schema"] == "skycache.gateway.pull_passport.v1"
    assert "redistribute" in dry["passport"]


def test_gateway_sim_pull_receipts_and_kit(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()

    sim = pull_preset("gutenberg-sample", data_dir=settings.data_dir, sim=True)
    assert sim["ok"] is True
    assert sim["mode"] == "sim"
    assert Path(sim["passport_path"]).is_file()
    assert Path(sim["fetch"]["path"]).is_file()

    rec = gateway_receipts(data_dir=settings.data_dir, limit=10)
    assert rec["summary"]["count"] >= 1
    assert any(r.get("preset") == "gutenberg-sample" for r in rec["recent"])

    kit = write_ethics_kit(tmp_path / "gateway-ethics-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (Path(kit["out_dir"]) / "ETHICS.md").is_file()
    assert (Path(kit["out_dir"]) / "presets.json").is_file()


def test_gateway_unknown_preset(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    bad = pull_preset("not-a-real-preset", data_dir=settings.data_dir, dry_run=True)
    assert bad["ok"] is False


def test_api_gateway(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    app = create_app(settings)
    client = TestClient(app)

    r = client.get("/api/gateway/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_sim_gateway") is True

    r2 = client.get("/api/gateway/presets")
    assert r2.status_code == 200
    assert len(r2.json().get("presets") or []) >= 1

    r3 = client.post(
        "/api/gateway/pull-preset",
        json={"preset_id": "gutenberg-sample", "dry_run": True},
    )
    assert r3.status_code == 200
    assert r3.json().get("ok") is True

    r4 = client.post(
        "/api/gateway/pull-preset",
        json={"preset_id": "gutenberg-sample", "dry_run": False, "sim": True},
    )
    assert r4.status_code == 200
    assert r4.json().get("ok") is True

    r5 = client.get("/api/gateway/receipts")
    assert r5.status_code == 200
    assert r5.json().get("summary", {}).get("count", 0) >= 1
