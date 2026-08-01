"""v1.17.0 RX Ops: doctor, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.rx_ops import export_rx_html, rx_ops_doctor, rx_ops_status, write_rx_kit
from skycache.rx.station import save_station
from skycache.web.app import create_app


def test_rx_ops_doctor_export(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=40.7, lon=-74.0, alt_m=10.0, name="lab")

    doc = rx_ops_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.rx.ops.doctor.v1"
    assert doc["go_rx_lab"] is True
    # live needs satdump on PATH - optional in CI
    assert "go_rx_live" in doc

    st = rx_ops_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.rx.ops.status.v1"
    assert st.get("station") is not None

    exp = export_rx_html(tmp_path / "rx.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "rx" in html and "receive" in html


def test_rx_kit_and_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    kit = write_rx_kit(tmp_path / "rx-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/rx/ops")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_rx_lab") is True
    r2 = client.get("/api/rx/status")
    assert r2.status_code == 200
