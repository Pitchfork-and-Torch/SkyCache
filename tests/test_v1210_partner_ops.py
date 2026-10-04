"""v1.21.0 Partner Ops: doctor, status, export, ops-kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.partner_ops import (
    export_partner_html,
    partner_doctor,
    partner_status,
    write_partner_ops_kit,
)
from skycache.web.app import create_app


def _seed(tmp: Path) -> Settings:
    settings = Settings(data_dir=tmp / "data", sim_mode=True)
    settings.ensure_dirs()
    content = settings.content_dir
    pkg = content / "sample"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "manifest.json").write_text("{}", encoding="utf-8")
    return settings


def test_partner_doctor_export(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = partner_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.partner.doctor.v1"
    assert doc["go_sim_pilot"] is True

    st = partner_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.partner.status.v1"
    assert "ngo" in (st.get("kit_types") or [])

    exp = export_partner_html(tmp_path / "board.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "partner" in html
    assert "broadband" in html or "starlink" in html


def test_partner_ops_kit_and_api(tmp_path: Path):
    settings = _seed(tmp_path)
    kit = write_partner_ops_kit(tmp_path / "partner-ops-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/partner/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_sim_pilot") is True
