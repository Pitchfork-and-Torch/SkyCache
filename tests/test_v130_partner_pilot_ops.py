"""v1.3.0 Partner Pilot Ops: kits, zip, report validate, readiness."""

from __future__ import annotations

import json
from pathlib import Path

from skycache.partner_kit import (
    build_partner_kit,
    package_all_partner_kits,
    partner_readiness,
    validate_pilot_report,
)
from skycache.rx.station import save_station


def test_build_partner_kit_zip(tmp_path: Path):
    out = tmp_path / "kit-ngo"
    meta = build_partner_kit(out, kit_type="ngo", make_zip=True, include_docs_copy=False)
    assert meta["ok"] is True
    assert (out / "partner-manifest.json").is_file()
    assert (out / "FIELD-DAY.md").is_file()
    assert (out / "pilot-report.template.json").is_file()
    man = json.loads((out / "partner-manifest.json").read_text(encoding="utf-8"))
    assert man["schema"] == "skycache.partner.kit.v2"
    assert any("rx schedule" in c for c in man["cli"])
    assert meta.get("zip")
    assert Path(meta["zip"]).is_file()


def test_package_all(tmp_path: Path):
    out = tmp_path / "all"
    meta = package_all_partner_kits(out, include_docs_copy=False)
    assert meta["ok"] is True
    assert len(meta["kits"]) == 3
    assert (out / "HOSTING.json").is_file()
    zips = list(out.glob("*.zip"))
    assert len(zips) == 3


def test_validate_pilot_report_fail_and_pass(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    rep = validate_pilot_report(bad)
    assert rep["ok"] is False
    assert any("org" in e for e in rep["errors"])

    good = tmp_path / "good.json"
    good.write_text(
        json.dumps(
            {
                "schema": "skycache.partner.pilot_report.v1",
                "kit_type": "ngo",
                "org": "Demo Clinic",
                "location": "Lab",
                "date": "2026-07-31",
                "nodes_deployed": 1,
                "phones_served_estimate": 5,
                "packs_used": ["literacy-1gb"],
                "issues": [],
                "license_review_ok": True,
                "honest_scope_briefed": True,
                "notes": "sim only",
            }
        ),
        encoding="utf-8",
    )
    rep2 = validate_pilot_report(good)
    assert rep2["ok"] is True
    assert rep2["score"] >= 80


def test_partner_readiness(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "content").mkdir()
    (data / "content" / "sample").mkdir()
    (data / "content" / "sample" / "manifest.json").write_text("{}", encoding="utf-8")
    save_station(data, lat=40.0, lon=-74.0, alt_m=10.0, name="lab")
    rep = partner_readiness(data_dir=data)
    assert rep["schema"] == "skycache.partner.readiness.v1"
    assert "score" in rep
    assert "go_sim_pilot" in rep
    assert isinstance(rep["checks"], list)
    assert len(rep["checks"]) >= 5
