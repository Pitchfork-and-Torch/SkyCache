"""v1.22.0 Dual Radio Ops: doctor, status, export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.dual_radio_ops import (
    dual_radio_doctor,
    dual_radio_status,
    export_dual_radio_html,
    write_dual_radio_kit,
)
from skycache.web.app import create_app


def _seed(tmp: Path) -> Settings:
    settings = Settings(data_dir=tmp / "data", sim_mode=True)
    settings.ensure_dirs()
    return settings


def test_dual_radio_doctor_export(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = dual_radio_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.dual_radio.doctor.v1"
    assert doc["go_sim_validation"] is True
    assert int(doc.get("board_count") or 0) >= 4
    assert int(doc.get("frame_count") or 0) >= 5

    st = dual_radio_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.dual_radio.status.v1"
    assert isinstance(st.get("boards"), list)
    assert len(st["boards"]) >= 4

    exp = export_dual_radio_html(
        tmp_path / "board.html",
        data_dir=settings.data_dir,
    )
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "dual-radio" in html or "dual radio" in html
    assert "broadband" in html or "starlink" in html


def test_dual_radio_kit_and_api(tmp_path: Path):
    settings = _seed(tmp_path)
    kit = write_dual_radio_kit(
        tmp_path / "dual-radio-kit",
        data_dir=settings.data_dir,
    )
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    pack_dir = tmp_path / "dual-radio-kit" / "validation-pack"
    assert (pack_dir / "storyboard.html").is_file()
    assert (pack_dir / "board-matrix.json").is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/dual-radio/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_sim_validation") is True
    assert body.get("go_sim_validation") is True
