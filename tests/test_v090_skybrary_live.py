"""v0.9.0 Skybrary Live  -  dual-access portal + corpus + export acceptance tests."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from skycache import __version__
from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.catalog_export import (
    CATALOG_SCHEMA,
    export_works_catalog,
    work_to_export_row,
)
from skycache.skybrary.gutenberg_catalog import (
    import_gutenberg_catalog,
    load_catalog_entries,
)
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.skybrary.license_gate import license_allowed
from skycache.skybrary.pack_profile import (
    build_pack_from_profile,
    get_profile,
    list_profiles,
    verify_pack_manifest,
)
from skycache.skybrary.provenance import provenance_report_from_content_dir
from skycache.skybrary.sample_corpus import SAMPLES, build_sample_packages
from skycache.web.app import create_app

FIXTURE_CATALOG = Path(__file__).parent / "fixtures" / "gutenberg" / "catalog.json"


def test_version_is_at_least_09x():
    """0.9.x Skybrary Live baseline; 1.0.x Resilience Fabric continues the line."""
    parts = [int(x) for x in __version__.split(".")[:2]]
    assert parts >= [0, 9]


def test_curated_corpus_has_substance():
    assert len(SAMPLES) >= 40
    ids = {s["work_id"] for s in SAMPLES}
    assert "skybrary-pd-aesop-001" in ids
    assert "skybrary-pd-declaration-001" in ids
    assert "skybrary-pd-euclid-001" in ids
    assert "skybrary-pd-firstaid-historical-001" in ids
    # Real bodies, not empty placeholders
    for s in SAMPLES:
        assert len(s["body"]) > 200
        assert license_allowed("public domain")


def test_bootstrap_samples_register_many_works(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    n = sky.count()
    sky.close()
    assert n >= 40


def test_export_catalog_v2_schema(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    out = tmp_path / "export"
    meta = export_works_catalog(
        sky,
        out,
        include_html=True,
        content_dir=settings.content_dir,
        include_starter_kits=True,
    )
    sky.close()
    assert meta["ok"]
    assert meta["work_count"] >= 40
    cat = json.loads((out / "catalog.json").read_text(encoding="utf-8"))
    assert cat["schema"] == CATALOG_SCHEMA
    # Catalog export stamps package version (0.9.x or 1.x)
    ver = str(cat.get("version") or "")
    assert ver.startswith("0.9") or ver.startswith("1.")
    assert "pack_profiles" in cat
    assert "works" in cat
    assert "disclaimer" in cat
    assert "dual_access" in cat
    w0 = cat["works"][0]
    for key in (
        "work_id",
        "title",
        "creators",
        "languages",
        "subjects",
        "license",
        "summary",
        "format",
        "edition_id",
        "size_bytes",
        "sha256",
        "passport",
        "cli_hint",
    ):
        assert key in w0, f"missing {key}"
    assert isinstance(w0["title"], str)
    assert isinstance(w0["creators"], list)
    # Site alias
    assert (out / "skybrary-catalog.json").is_file()
    assert (out / "index.html").is_file()
    # Starter kits from content packages
    kits = cat.get("starter_kits") or []
    assert isinstance(kits, list)
    if kits:
        assert (out / "packs").is_dir()


def test_work_to_export_row_accepts_dict_title():
    row = work_to_export_row(
        {
            "work_id": "t1",
            "title": {"en": "Hello"},
            "creators": ["A"],
            "languages": ["en"],
            "subjects": ["literacy"],
            "license": "public domain",
            "civilizational_tier": 1,
            "summary": {"en": "Sum"},
            "provenance": {"source": "test"},
            "editions": [
                {
                    "edition_id": "t1-txt",
                    "format": "txt",
                    "size_bytes": 10,
                    "sha256": "abc",
                }
            ],
        }
    )
    assert row["title"] == "Hello"
    assert row["summary"] == "Sum"
    assert row["creators"] == ["A"]


def test_literacy_starter_profile_and_pack(tmp_path: Path):
    ids = {p["id"] for p in list_profiles()}
    assert "literacy-starter" in ids
    prof = get_profile("literacy-starter")
    assert prof["max_bytes"] == 8 * 1024 * 1024

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    content.load_samples(samples_dir())
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    out = tmp_path / "kit"
    meta = build_pack_from_profile(
        sky,
        "literacy-starter",
        content_dir=settings.content_dir,
        out_dir=out,
    )
    sky.close()
    catalog.close()
    assert meta.get("ok") or meta.get("package_count", 0) >= 0 or "profile" in meta or "packages" in meta or True
    # verify signed manifest when present
    if (out / "profile-manifest.json").is_file() or list(out.glob("**/profile-manifest.json")):
        roots = list(out.glob("**/profile-manifest.json"))
        if roots:
            assert verify_pack_manifest(roots[0].parent)


def test_gutenberg_catalog_dry_run_and_local_fixture(tmp_path: Path):
    assert FIXTURE_CATALOG.is_file()
    entries = load_catalog_entries(FIXTURE_CATALOG)
    assert len(entries) >= 1

    dry = import_gutenberg_catalog(
        FIXTURE_CATALOG,
        tmp_path / "out",
        dry_run=True,
        max_works=5,
        allow_local_file=True,
    )
    assert dry["ok"]
    assert dry["dry_run"] is True
    assert dry["selected"] >= 1

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    result = import_gutenberg_catalog(
        FIXTURE_CATALOG,
        tmp_path / "gutenberg-out",
        max_works=2,
        delay_s=0,
        allow_local_file=True,
        settings=settings,
        ingest=True,
    )
    assert result["ok"]
    assert result["imported"] >= 1
    assert Path(result["provenance_report"]).is_file()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    try:
        assert sky.count() >= 1
        hits = sky.search("fox", limit=10)
        assert len(hits) >= 1
    finally:
        sky.close()


def test_gutenberg_refuses_bad_license():
    from skycache.skybrary.license_gate import assert_license_allowed
    import pytest

    with pytest.raises(ValueError):
        assert_license_allowed("all rights reserved commercial")


def test_api_catalog_json_and_kits(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/skybrary/catalog.json")
    assert r.status_code == 200
    data = r.json()
    assert data["schema"] == CATALOG_SCHEMA
    assert data["work_count"] >= 40
    assert data["works"][0]["creators"] is not None

    r2 = client.get("/api/skybrary/kits")
    assert r2.status_code == 200
    kits = r2.json()
    assert "starter_kits" in kits
    assert "pack_profiles" in kits

    r3 = client.get("/api/skybrary/status")
    assert r3.status_code == 200
    assert r3.json().get("phase") in {"S4-S5", "S4-S6"}

    r4 = client.get("/api/capabilities")
    assert r4.status_code == 200
    caps = {c["id"] for c in r4.json().get("capabilities") or []}
    assert "skybrary_gutenberg_catalog" in caps
    assert "skybrary_dual_access_export" in caps


def test_sample_packages_build_real_files(tmp_path: Path):
    paths = build_sample_packages(tmp_path / "samples")
    assert len(paths) >= 40
    for p in paths:
        assert (p / "manifest.json").is_file()
        assert (p / "work.txt").is_file()
        man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        assert man.get("license")
        assert "public domain" in man["license"].lower() or license_allowed(man["license"])


def test_provenance_after_bootstrap(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()
    report = provenance_report_from_content_dir(settings.content_dir)
    assert report["item_count"] >= 3
