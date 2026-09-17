"""v1.11.0 Integrity Ops: doctor, verify, report, kit, API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.integrity_ops import (
    integrity_doctor,
    integrity_verify,
    write_integrity_kit,
    write_integrity_report_html,
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


def test_integrity_doctor_verify_report(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = integrity_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.integrity.doctor.v1"
    assert doc["go_integrity_sim"] is True

    ver = integrity_verify(data_dir=settings.data_dir, record=True)
    assert ver["ok"] is True
    assert Path(ver["receipt_path"]).is_file()

    doc2 = integrity_doctor(data_dir=settings.data_dir)
    assert doc2["go_integrity_scheduled"] is True

    rep = write_integrity_report_html(
        tmp_path / "integrity-report.html",
        data_dir=settings.data_dir,
    )
    assert rep["ok"] is True
    html = Path(rep["path"]).read_text(encoding="utf-8")
    assert "Integrity report" in html
    assert "open package" in html.lower() or "Open packages" in html or "open packages" in html


def test_integrity_kit_and_api(tmp_path: Path):
    settings = _seed(tmp_path)
    kit = write_integrity_kit(tmp_path / "integrity-kit", data_dir=settings.data_dir, run_verify=True)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (Path(kit["out_dir"]) / "integrity-report.html").is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/integrity/status")
    assert r.status_code == 200
    assert r.json().get("go_integrity_sim") is True

    r2 = client.post("/api/integrity/verify", json={"record": True})
    assert r2.status_code == 200
    assert r2.json().get("ok") is True


def test_cli_integrity_verify_record_flag(tmp_path: Path, capsys):
    """The command doctor/kit/README print (`integrity verify --record`) must parse and run."""
    import json

    from skycache.__main__ import build_parser

    settings = _seed(tmp_path)
    data_dir = str(settings.data_dir)

    def run(argv: list[str]) -> tuple[int, dict]:
        args = build_parser().parse_args(argv)
        code = int(args.func(args))
        return code, json.loads(capsys.readouterr().out)

    doc = integrity_doctor(data_dir=settings.data_dir)
    assert "skycache integrity verify --record" in doc["next_steps"]

    receipt = settings.data_dir / "ops" / "bitrot-last.json"

    code, rep = run(["integrity", "verify", "--data-dir", data_dir, "--no-record"])
    assert code == 0 and rep["ok"] is True
    assert rep["receipt_path"] is None
    assert not receipt.exists()

    code, rep = run(["integrity", "verify", "--data-dir", data_dir, "--record"])
    assert code == 0 and rep["ok"] is True
    assert Path(rep["receipt_path"]) == receipt
    assert receipt.is_file()

    receipt.unlink()
    code, rep = run(["integrity", "verify", "--data-dir", data_dir])
    assert code == 0 and receipt.is_file(), "recording stays the default"

    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["integrity", "verify", "--data-dir", data_dir, "--record", "--no-record"]
        )
