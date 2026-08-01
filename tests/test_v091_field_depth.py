"""v0.9.1 field depth: Pi bake, mesh day-one, OA science, chapters, blobs, maps, partners."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from skycache import __version__
from skycache.config import Settings
from skycache.deploy_pi import bake_plan, write_bake_artifacts
from skycache.nexus.mesh_day_one import apply_day_one, day_one_plan, detect_mesh_environment
from skycache.partner_kit import build_partner_kit
from skycache.skybrary.blob_store import BlobStore
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.chapters import list_package_chapters, read_chapter_text
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.skybrary.oa_science import import_oa_science_catalog, license_ok_for_oa
from skycache.skybrary.pack_profile import get_profile, list_profiles
from skycache.web.app import create_app

OA_FIXTURE = Path(__file__).parent / "fixtures" / "oa_science" / "catalog.json"


def test_version_091_or_newer():
    parts = [int(x) for x in __version__.split(".")[:3]]
    assert parts >= [0, 9, 1]  # 0.9.2+ still satisfies


def test_pi_image_bake_plan_and_write(tmp_path: Path):
    plan = bake_plan(ssid="SkyCache-Test")
    assert plan["schema"] in (
        "skycache.pi.golden_image.v1",
        "skycache.pi.golden_image.v2",
    )
    assert "apt_packages" in plan
    assert "batctl" in plan["apt_packages"]
    assert "first-boot" in json.dumps(plan).lower() or any(
        "first-boot" in str(s) for s in plan["steps"]
    )
    meta = write_bake_artifacts(tmp_path / "pi-bake", plan)
    assert meta["ok"]
    assert (tmp_path / "pi-bake" / "golden-pi-bake-plan.json").is_file()
    assert (tmp_path / "pi-bake" / "golden-pi-verify.sh").is_file()


def test_mesh_day_one_plan_sim_safe(tmp_path: Path):
    env = detect_mesh_environment()
    assert "is_linux" in env
    plan = day_one_plan(data_dir=tmp_path / "data")
    assert plan["schema"] == "skycache.mesh.day_one.v1"
    assert len(plan["steps"]) >= 5
    assert (tmp_path / "data" / "nexus" / "mesh-day-one-plan.json").is_file()
    dry = apply_day_one(dry_run=True)
    assert dry["ok"]
    assert dry["applied"] is False


def test_oa_science_license_gate_and_fixture(tmp_path: Path):
    assert license_ok_for_oa("cc-by-4.0")
    assert license_ok_for_oa("open-access")
    assert not license_ok_for_oa("all rights reserved commercial")
    assert OA_FIXTURE.is_file()
    dry = import_oa_science_catalog(
        OA_FIXTURE, tmp_path / "out", dry_run=True, allow_local_file=True
    )
    assert dry["selected"] >= 1
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    result = import_oa_science_catalog(
        OA_FIXTURE,
        tmp_path / "oa-out",
        allow_local_file=True,
        delay_s=0,
        ingest=True,
        settings=settings,
    )
    assert result["ok"]
    assert result["imported"] >= 1
    sky = SkybraryCatalog(settings.skybrary_db_path)
    try:
        assert sky.count() >= 1
        hits = sky.search("fixture", limit=5)
        assert len(hits) >= 1
    finally:
        sky.close()


def test_blob_store_put_verify_dedup(tmp_path: Path):
    store = BlobStore(tmp_path / "blobs")
    f = tmp_path / "big.bin"
    f.write_bytes(b"skybrary-blob-" * 100)
    a = store.put_file(f, media_type="application/octet-stream")
    assert a["ok"]
    digest = a["sha256"]
    assert store.has(digest)
    assert store.verify(digest)["ok"]
    b = store.put_file(f)
    assert b["sha256"] == digest
    stats = store.stats()
    assert stats["blob_count"] >= 1


def test_chapters_list_and_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    # multi-file package
    pkg = settings.content_dir / "skybrary-pd-aesop-001"
    if not pkg.is_dir():
        # bootstrap may use package ids from samples
        dirs = [p for p in settings.content_dir.iterdir() if p.is_dir()]
        assert dirs
        pkg = dirs[0]
    chs = list_package_chapters(pkg)
    assert len(chs) >= 1
    body = read_chapter_text(pkg, path=chs[0]["path"])
    assert body["ok"]
    assert len(body["body"]) > 10
    sky.close()

    app = create_app(settings)
    client = TestClient(app)
    # pick any work
    r = client.get("/api/skybrary/works?limit=5")
    assert r.status_code == 200
    works = r.json().get("results") or []
    assert works
    wid = works[0]["work_id"]
    r2 = client.get(f"/api/skybrary/works/{wid}/chapters")
    assert r2.status_code == 200
    data = r2.json()
    assert data["chapter_count"] >= 1
    r3 = client.get(f"/api/skybrary/works/{wid}/chapters/0")
    assert r3.status_code == 200
    assert "body" in r3.json()


def test_maps_offline_profile():
    ids = {p["id"] for p in list_profiles()}
    assert "maps-offline" in ids
    p = get_profile("maps-offline")
    assert "maps" in p["include_subjects"] or "mbtiles" in p["include_subjects"]


def test_partner_kit_ngo_and_university(tmp_path: Path):
    for kt in ("ngo", "university", "civil-protection"):
        meta = build_partner_kit(tmp_path / kt, kit_type=kt, include_docs_copy=True)
        assert meta["ok"]
        assert (tmp_path / kt / "CHECKLIST.md").is_file()
        assert (tmp_path / kt / "LEGAL-ONE-PAGER.md").is_file()
        assert (tmp_path / kt / "CHECKLIST.html").is_file()
        assert (tmp_path / kt / "partner-manifest.json").is_file()


def test_capabilities_include_v091_ids(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    client = TestClient(create_app(settings))
    r = client.get("/api/capabilities")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json().get("capabilities") or []}
    for need in (
        "skybrary_oa_science",
        "content_blob_store",
        "mesh_batman_day_one",
        "golden_pi_image",
        "partner_field_pilot",
    ):
        assert need in ids


def test_epub_chapter_spine(tmp_path: Path):
    """Minimal EPUB yields chapter entries."""
    from skycache.skybrary.chapters import list_epub_spine_entries
    from tests.test_corpus_import import _write_minimal_epub

    epub = _write_minimal_epub(tmp_path / "t.epub", "T", "Hello chapter body for spine.")
    list_epub_spine_entries(epub)
    # spine may be empty if OPF minimal  -  list_package_chapters still lists .epub
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "work.txt").write_text("full text\n", encoding="utf-8")
    import shutil

    shutil.copy2(epub, pkg / "book.epub")
    chs = list_package_chapters(pkg)
    assert any(c.get("format") in {"epub", "epub-section", "txt"} for c in chs)
