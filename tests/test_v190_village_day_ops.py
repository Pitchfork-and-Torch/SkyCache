"""v1.9.0 Village Day Ops: doctor, readiness, runbook, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.village_day_ops import (
    village_day_doctor,
    village_day_readiness,
    write_village_day_kit,
    write_village_day_runbook,
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


def test_village_day_doctor_and_readiness(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = village_day_doctor(data_dir=settings.data_dir, sim=True)
    assert doc["schema"] == "skycache.village_day.doctor.v1"
    assert doc["go_weekend_sim"] is True
    assert doc["score"] >= 70
    assert "handoff" in {c["id"] for c in doc["checks"]}

    ready = village_day_readiness(data_dir=settings.data_dir, sim=True)
    assert ready["schema"] == "skycache.village_day.readiness.v1"
    assert ready["go_weekend_sim"] is True
    assert Path(ready["receipt_path"]).is_file()


def test_village_day_runbook_and_kit(tmp_path: Path):
    settings = _seed(tmp_path)
    rb = write_village_day_runbook(tmp_path / "village-day", data_dir=settings.data_dir)
    assert rb["ok"] is True
    assert (Path(rb["out_dir"]) / "RUNBOOK.md").is_file()
    assert "Weekend" in (Path(rb["out_dir"]) / "RUNBOOK.md").read_text(encoding="utf-8") or "weekend" in (
        Path(rb["out_dir"]) / "RUNBOOK.md"
    ).read_text(encoding="utf-8").lower()

    kit = write_village_day_kit(tmp_path / "village-day-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (Path(kit["out_dir"]) / "FIELD-CHECKLIST.md").is_file()
    assert (Path(kit["out_dir"]) / "docs" / "first-boot.md").is_file()


def test_api_village_day(tmp_path: Path):
    settings = _seed(tmp_path)
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/village-day/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("go_weekend_sim") is True
    assert body.get("doctor", {}).get("schema") == "skycache.village_day.doctor.v1"

    r2 = client.post("/api/village-day/readiness", json={})
    assert r2.status_code == 200
    assert r2.json().get("go_weekend_sim") is True
