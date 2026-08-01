"""v1.20.0 Seal Ops: doctor, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.seal_ops import export_seal_html, seal_doctor, seal_status, write_seal_kit
from skycache.web.app import create_app


def test_seal_doctor_export_kit(tmp_path: Path):
    doc = seal_doctor()
    assert doc["schema"] == "skycache.seal.doctor.v1"
    assert "go_kit_path" in doc
    assert "go_seal_path" in doc

    st = seal_status()
    assert st["schema"] == "skycache.seal.status.v1"
    assert "host_probe" in st
    assert (st.get("plan_summary") or {}).get("hostname")

    exp = export_seal_html(tmp_path / "seal.html")
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "seal" in html or "golden" in html
    assert "2468" in html or "pin" in html

    kit = write_seal_kit(tmp_path / "seal-kit")
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (tmp_path / "seal-kit" / "SEAL-CHECKLIST.md").is_file() or (
        tmp_path / "seal-kit" / "seal" / "SEAL-CHECKLIST.md"
    ).is_file()


def test_seal_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/seal/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("schema") == "skycache.seal.doctor.v1"
    assert "go_kit_path" in body
