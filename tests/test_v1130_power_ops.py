"""v1.13.0 Power Ops: doctor, status, sheet, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.power_ops import (
    power_doctor,
    power_status,
    write_power_kit,
    write_power_sheet,
)
from skycache.web.app import create_app


def test_power_doctor_status_sheet(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        power_provider="mock",
        mock_battery_percent=72.0,
    )
    settings.ensure_dirs()

    doc = power_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.power.doctor.v1"
    assert doc["go_power_lab"] is True

    st = power_status(data_dir=settings.data_dir)
    assert st["guidance"]["percent"] is not None
    assert "hours_until_eco" in st["guidance"]
    assert st["provider"] == "mock"

    sheet = write_power_sheet(tmp_path / "power-sheet.html", data_dir=settings.data_dir)
    assert sheet["ok"] is True
    html = Path(sheet["path"]).read_text(encoding="utf-8")
    assert "power sheet" in html.lower() or "Power sheet" in html


def test_power_kit_and_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        power_provider="mock",
        mock_battery_percent=55.0,
    )
    settings.ensure_dirs()
    kit = write_power_kit(tmp_path / "power-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (Path(kit["out_dir"]) / "FIELD-CHECKLIST.md").is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/power/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_power_lab") is True
    # legacy guidance still works
    r2 = client.get("/api/power/guidance")
    assert r2.status_code == 200
    assert "hours_until_eco" in r2.json()
