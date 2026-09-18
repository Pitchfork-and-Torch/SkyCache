"""v1.6.0 Field Mesh Ops: doctor, readiness, disaster drill, field kit."""

from __future__ import annotations

from pathlib import Path

from skycache.nexus.field_mesh_ops import (
    build_field_mesh_kit,
    mesh_doctor,
    mesh_readiness,
    run_disaster_drill,
)


def test_mesh_doctor():
    rep = mesh_doctor()
    assert rep["schema"] == "skycache.mesh.doctor.v1"
    assert rep["go_sim_mesh"] is True
    assert "score" in rep
    assert isinstance(rep["checks"], list)


def test_mesh_readiness_sim(tmp_path: Path):
    rep = mesh_readiness(data_dir=tmp_path / "data", nodes=2, run_sim=True)
    assert rep["schema"] == "skycache.mesh.readiness.v1"
    assert rep["go_sim_mesh"] is True
    assert rep["sim_validate"] is not None
    assert rep["sim_validate"]["ok"] is True
    assert Path(rep["written"]).is_file()


def test_disaster_drill(tmp_path: Path):
    rep = run_disaster_drill(nodes=2, data_dir=tmp_path / "data")
    assert rep["schema"] == "skycache.mesh.disaster_drill.v1"
    assert rep["disaster"] is True
    assert rep["ok"] is True
    assert Path(rep["written"]).is_file()


def test_field_mesh_kit(tmp_path: Path):
    meta = build_field_mesh_kit(tmp_path / "kit", make_zip=True)
    assert meta["ok"] is True
    assert Path(meta["out_dir"], "README.md").is_file()
    assert Path(meta["out_dir"], "FIELD-CHECKLIST.md").is_file()
    assert Path(meta["out_dir"], "HOSTING.json").is_file()
    assert meta.get("zip")
    assert Path(meta["zip"]).is_file()
