"""v1.18.0 Node Report Ops: doctor rollup, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.report_ops import (
    export_report_html,
    report_doctor,
    report_status,
    write_report_kit,
)
from skycache.web.app import create_app


def test_report_doctor_export(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True, legal_rf_mode="ism_mesh")
    settings.ensure_dirs()

    doc = report_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.report.doctor.v1"
    assert "go_partner_review" in doc
    assert int(doc.get("score") or 0) >= 1

    st = report_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.report.status.v1"
    assert len(st.get("gates") or []) >= 5

    exp = export_report_html(tmp_path / "node.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "readiness" in html or "node" in html


def test_report_kit_and_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    kit = write_report_kit(tmp_path / "report-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/report/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("schema") == "skycache.report.doctor.v1"
    assert "gates" in body
