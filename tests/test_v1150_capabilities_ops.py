"""v1.15.0 Capabilities Ops: doctor, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.capabilities_ops import (
    capabilities_doctor,
    capabilities_status,
    export_capabilities_html,
    write_capabilities_kit,
)
from skycache.web.app import create_app


def test_capabilities_doctor_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Doctor reloads Settings from data_dir + env; pin must come from env prefix.
    monkeypatch.setenv("SKYCACHE_ADMIN_PIN", "739184")
    monkeypatch.setenv("SKYCACHE_LEGAL_RF_MODE", "ism_mesh")
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()

    doc = capabilities_doctor(data_dir=settings.data_dir, sim=True)
    assert doc["schema"] == "skycache.capabilities.doctor.v1"
    assert doc["go_capabilities_onboard"] is True
    assert doc["go_capabilities_field"] is True

    st = capabilities_status(data_dir=settings.data_dir, sim=True)
    assert int((st.get("summary") or {}).get("total") or 0) >= 5

    exp = export_capabilities_html(tmp_path / "cap.html", data_dir=settings.data_dir, sim=True)
    assert exp["ok"] is True
    assert "capability" in Path(exp["path"]).read_text(encoding="utf-8").lower()


def test_capabilities_kit_and_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SKYCACHE_ADMIN_PIN", "739184")
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    kit = write_capabilities_kit(tmp_path / "capabilities-kit", data_dir=settings.data_dir, sim=True)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/capabilities/status")
    assert r.status_code == 200
    assert r.json().get("doctor", {}).get("go_capabilities_onboard") is True
    r2 = client.get("/api/capabilities")
    assert r2.status_code == 200
