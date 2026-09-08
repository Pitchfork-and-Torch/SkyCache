"""v1.34 Software Mission Seal: BLE sim, power calibrate, soak, tabletop, mission 100."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.capabilities.ble_profile import simulate_ble_exchange
from skycache.config import Settings
from skycache.ops.disaster_ops import disaster_tabletop_script, write_disaster_tabletop
from skycache.ops.mission_ops import (
    export_mission_html,
    mission_doctor,
    mission_status,
    seal_software_mission,
)
from skycache.ops.power_ops import load_power_calibration, write_power_calibration
from skycache.ops.soak_protocol import write_all_soak_protocols
from skycache.skybrary.sample_corpus import SAMPLES
from skycache.web.app import create_app


def test_ble_sim_roundtrip():
    out = simulate_ble_exchange({"node_id": "lab", "packages": ["a"]})
    assert out["ok"] is True
    assert out["live_radio"] is False
    assert int(out["frame_count"]) >= 1
    assert out["restored"]["node_id"] == "lab"


def test_power_calibration_lab_and_operator(tmp_path: Path):
    lab = load_power_calibration(data_dir=tmp_path / "empty")
    assert float(lab["battery_wh"]) > 0
    assert lab["source"] == "lab-default"
    wrote = write_power_calibration(
        tmp_path / "data",
        battery_wh=240.0,
        source="operator",
        notes="12V 20Ah",
    )
    assert wrote["ok"] is True
    loaded = load_power_calibration(data_dir=tmp_path / "data")
    assert loaded["battery_wh"] == 240.0
    assert loaded["site_owned"] is True


def test_soak_and_tabletop(tmp_path: Path):
    soak = write_all_soak_protocols(tmp_path / "soak")
    assert soak["ok"] is True
    assert soak["count"] >= 4
    script = disaster_tabletop_script()
    assert script["station_count"] >= 6
    tab = write_disaster_tabletop(tmp_path / "ops" / "tabletop.json", data_dir=tmp_path)
    assert tab["ok"] is True
    assert Path(tab["path"]).is_file()


def test_mission_doctor_is_one_hundred(tmp_path: Path):
    assert len(SAMPLES) >= 78
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    doc = mission_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.mission.doctor.v1"
    failed = [c["id"] for c in doc["checks"] if not c["ok"]]
    assert failed == [], failed
    assert doc["score"] == 100
    assert doc["go_software_mission"] is True
    assert len(doc["field_residuals"]) >= 6

    st = mission_status(data_dir=settings.data_dir)
    assert st["go_software_mission"] is True
    assert st["failed"] == []


def test_mission_seal_kit_and_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    kit = seal_software_mission(tmp_path / "mission-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (tmp_path / "mission-kit" / "mission-seal.json").is_file()
    assert (tmp_path / "mission-kit" / "ble-sim.json").is_file()
    assert (tmp_path / "mission-kit" / "soak" / "soak-rx.json").is_file()

    board = export_mission_html(tmp_path / "board.html", data_dir=settings.data_dir)
    html = Path(board["path"]).read_text(encoding="utf-8").lower()
    assert "software mission" in html
    assert "broadband" in html or "starlink" in html

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/mission/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("go_software_mission") is True
    assert body.get("doctor", {}).get("score") == 100
