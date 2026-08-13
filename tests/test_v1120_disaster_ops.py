"""v1.12.0 Disaster Drill Ops: doctor, run, report, closeout, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.disaster_ops import (
    disaster_closeout,
    disaster_doctor,
    disaster_run,
    write_disaster_kit,
    write_disaster_report_html,
)
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.web.app import create_app


def _seed(tmp: Path) -> Settings:
    settings = Settings(data_dir=tmp / "data", sim_mode=True, disaster_mode=False)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()
    return settings


def test_disaster_doctor_run_closeout(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = disaster_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.disaster.doctor.v1"
    assert doc["go_lab_drill"] is True

    run = disaster_run(data_dir=settings.data_dir, nodes=2)
    assert run["ok"] is True
    assert (settings.data_dir / "ops" / "disaster-drill-last.json").is_file()

    close = disaster_closeout(data_dir=settings.data_dir)
    assert close["disaster_mode_off"] is True
    assert close["lab_receipt_ok"] is True

    rep = write_disaster_report_html(tmp_path / "disaster-report.html", data_dir=settings.data_dir)
    assert rep["ok"] is True
    assert "Disaster" in Path(rep["path"]).read_text(encoding="utf-8")


def test_disaster_kit_and_api(tmp_path: Path):
    settings = _seed(tmp_path)
    kit = write_disaster_kit(tmp_path / "disaster-kit", data_dir=settings.data_dir, run_lab=True)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (Path(kit["out_dir"]) / "FIELD-CHECKLIST.md").is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/disaster/status")
    assert r.status_code == 200
    assert r.json().get("go_lab_drill") is True

    r2 = client.post("/api/disaster/run", json={"nodes": 2})
    assert r2.status_code == 200
    assert r2.json().get("ok") is True

    r3 = client.post("/api/disaster/closeout", json={})
    assert r3.status_code == 200
    assert r3.json().get("disaster_mode_off") is True
