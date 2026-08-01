"""v1.14.0 Licenses Ops: doctor, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.licenses_ops import (
    export_licenses_html,
    licenses_doctor,
    licenses_status,
    write_licenses_kit,
)
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.web.app import create_app


def _seed(tmp: Path) -> Settings:
    settings = Settings(data_dir=tmp / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()
    return settings


def test_licenses_doctor_export(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = licenses_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.licenses.doctor.v1"
    assert doc["go_licenses_inventory"] is True

    st = licenses_status(data_dir=settings.data_dir)
    assert int(st.get("package_count") or 0) >= 1

    exp = export_licenses_html(tmp_path / "licenses.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8")
    assert "license" in html.lower()


def test_licenses_kit_and_api(tmp_path: Path):
    settings = _seed(tmp_path)
    kit = write_licenses_kit(tmp_path / "licenses-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/licenses/status")
    assert r.status_code == 200
    assert r.json().get("doctor", {}).get("go_licenses_inventory") is True
    r2 = client.get("/api/licenses")
    assert r2.status_code == 200
    assert int(r2.json().get("package_count") or 0) >= 1
