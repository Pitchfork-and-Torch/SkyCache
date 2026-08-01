"""v1.4.0 Golden Node Bake Ops: plan v2, doctor, seal, sealed-manifest, kit zip."""

from __future__ import annotations

import json
from pathlib import Path

from skycache.deploy_pi import (
    bake_plan,
    build_downloadable_sd_kit,
    hash_file_sha256,
    pi_image_doctor,
    sealed_image_manifest,
    write_bake_artifacts,
    write_seal_checklist,
)


def test_bake_plan_v2():
    plan = bake_plan(include_optional_sdr=True)
    assert plan["schema"] == "skycache.pi.golden_image.v2"
    ids = {s["id"] for s in plan["steps"]}
    assert "readiness" in ids
    assert "rx_optional" in ids
    assert "seal" in ids
    assert "2468" in plan["forbidden_pins"]
    assert "rtl-sdr" in plan["apt_packages"]


def test_pi_image_doctor():
    rep = pi_image_doctor()
    assert rep["schema"] == "skycache.pi.doctor.v1"
    assert "score" in rep
    assert "go_kit_path" in rep
    assert isinstance(rep["checks"], list)


def test_write_bake_and_seal(tmp_path: Path):
    out = tmp_path / "bake"
    meta = write_bake_artifacts(out)
    assert meta["ok"] is True
    assert Path(meta["plan"]).is_file()
    assert Path(meta["verify_script"]).is_file()
    assert Path(meta["seal_checklist"]).is_file()
    plan = json.loads(Path(meta["plan"]).read_text(encoding="utf-8"))
    assert plan["schema"] == "skycache.pi.golden_image.v2"
    seal = write_seal_checklist(tmp_path / "seal-only")
    assert Path(seal["path"]).is_file()
    text = Path(seal["path"]).read_text(encoding="utf-8")
    assert "2468" in text
    assert "sealed-manifest" in text


def test_sealed_manifest_and_hash(tmp_path: Path):
    blob = tmp_path / "fake.img.xz"
    blob.write_bytes(b"not-a-real-image-but-ok-for-hash")
    h = hash_file_sha256(blob)
    assert h["ok"] is True
    assert len(h["sha256"]) == 64

    bad = sealed_image_manifest(url="http://insecure.example/x", sha256="abc")
    assert bad["ok"] is False

    good = sealed_image_manifest(
        url="https://example.com/skycache-village-pi.img.xz",
        sha256=h["sha256"],
        size_bytes=h["size_bytes"],
        out_path=tmp_path / "sealed-manifest.json",
        note="lab only",
    )
    assert good["ok"] is True
    assert Path(good["path"]).is_file()


def test_bundle_kit_zip(tmp_path: Path):
    meta = build_downloadable_sd_kit(tmp_path / "dl", include_optional_sdr=False)
    assert meta["ok"] is True
    z = Path(meta["zip"])
    assert z.is_file()
    assert z.stat().st_size > 1000
    assert meta["hosting"]["schema"] == "skycache.pi.download_kit.v2"
    stage = Path(meta["stage"])
    assert (stage / "bake" / "SEAL-CHECKLIST.md").is_file()
    assert (stage / "HOSTING.json").is_file()
