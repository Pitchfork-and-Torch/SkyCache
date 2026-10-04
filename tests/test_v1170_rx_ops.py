"""v1.17.0 RX Ops: doctor, status, export, kit, API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.capabilities.modes import LegalRfMode, satellite_receive_only_ok
from skycache.config import Settings
from skycache.ops.rx_ops import export_rx_html, rx_ops_doctor, rx_ops_status, write_rx_kit
from skycache.rx.doctor import rx_doctor_report
from skycache.rx.station import save_station
from skycache.web.app import create_app


def _check(doc: dict, cid: str) -> dict:
    hits = [c for c in doc.get("checks") or [] if c.get("id") == cid]
    assert hits, f"missing doctor check {cid}"
    return hits[0]


def test_satellite_receive_only_ok_fail_closed():
    for mode in (
        LegalRfMode.RECEIVE_ONLY.value,
        LegalRfMode.ISM_MESH.value,
        LegalRfMode.ISM_LORA_CONTROL.value,
        LegalRfMode.HYBRID_GATEWAY.value,
        LegalRfMode.AMATEUR_OPERATOR.value,
    ):
        ok, detail = satellite_receive_only_ok(mode)
        assert ok is True, mode
        assert "satellite TX never" in detail

    for bad in (
        "",
        "   ",
        "starlink-tx",
        "satellite-uplink",
        "oneweb-client",
        "decrypt-commercial",
        "vsat-tx",
        "not-a-real-mode",
    ):
        ok, detail = satellite_receive_only_ok(bad)
        assert ok is False, bad
        assert detail


def test_rx_ops_doctor_export(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=40.7, lon=-74.0, alt_m=10.0, name="lab")

    doc = rx_ops_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.rx.ops.doctor.v1"
    assert doc["go_rx_lab"] is True
    # live needs satdump on PATH - optional in CI
    assert "go_rx_live" in doc
    legal_check = _check(doc, "legal_receive_only")
    assert legal_check["ok"] is True
    claim = _check(doc, "no_commercial_claim")
    assert claim["ok"] is True

    st = rx_ops_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.rx.ops.status.v1"
    assert st.get("station") is not None
    assert st.get("legal", {}).get("satellite_tx") == "never"
    assert st.get("legal", {}).get("receive_only_ok") is True

    exp = export_rx_html(tmp_path / "rx.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "rx" in html and "receive" in html


def test_rx_doctor_reports_configured_mode_not_hardcoded(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    doc = rx_doctor_report(
        data_dir=settings.data_dir,
        legal_rf_mode="hybrid_gateway",
    )
    assert doc["legal"]["mode"] == "hybrid_gateway"
    assert doc["legal"]["receive_only_ok"] is True
    assert doc["legal"]["satellite_tx"] == "never"

    ops = rx_ops_doctor(
        data_dir=settings.data_dir,
        legal_rf_mode="ism_mesh",
    )
    assert ops["legal"]["mode"] == "ism_mesh"
    assert _check(ops, "legal_receive_only")["ok"] is True


def test_rx_doctor_fail_closed_on_forbidden_first_boot_mode(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=1.0, lon=2.0, name="tampered")
    (settings.data_dir / "first_boot.json").write_text(
        json.dumps(
            {
                "completed": True,
                "legal_rf_mode": "starlink-tx",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    doc = rx_ops_doctor(data_dir=settings.data_dir)
    legal_check = _check(doc, "legal_receive_only")
    assert legal_check["ok"] is False
    assert "starlink" in legal_check["detail"].lower()
    assert doc["go_rx_live"] is False
    assert doc["legal"]["receive_only_ok"] is False
    assert _check(doc, "no_commercial_claim")["ok"] is False


def test_rx_kit_and_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        legal_rf_mode="receive_only",
    )
    settings.ensure_dirs()
    kit = write_rx_kit(tmp_path / "rx-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    checklist = (tmp_path / "rx-kit" / "FIELD-CHECKLIST.md").read_text(encoding="utf-8")
    assert "legal_receive_only" in checklist

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/rx/ops")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_rx_lab") is True
    assert body.get("doctor", {}).get("legal", {}).get("mode") == "receive_only"
    r2 = client.get("/api/rx/status")
    assert r2.status_code == 200
    assert r2.json().get("legal", {}).get("mode") == "receive_only"
    assert r2.json().get("legal", {}).get("satellite_tx") == "never"
