"""v1.16.0 Local Ops: doctor, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.local_ops import (
    export_ops_html,
    ops_doctor,
    ops_status,
    write_ops_kit,
)
from skycache.web.app import create_app


def test_ops_doctor_export(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()

    doc = ops_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.ops.doctor.v1"
    assert doc["go_local_lab"] is True
    assert doc["fleet_heartbeat_enabled"] is False

    st = ops_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.ops.status.v1"
    assert st["fleet_heartbeat_enabled"] is False
    assert (st.get("snapshot") or {}).get("schema") == "skycache.ops.local.v1"

    exp = export_ops_html(tmp_path / "board.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "local ops" in html or "fleet" in html


def test_ops_kit_and_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    kit = write_ops_kit(tmp_path / "ops-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/ops/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_local_lab") is True
    assert body.get("fleet_heartbeat_enabled") is False
    r2 = client.get("/api/ops/local")
    assert r2.status_code == 200
    assert r2.json().get("fleet_heartbeat", {}).get("enabled") is False
