"""License passport API + redistribute posture + doctor --verify."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.community.passport import redistribute_posture
from skycache.config import Settings, package_root, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.web.app import create_app


def test_redistribute_posture():
    assert redistribute_posture("public domain")["redistribute"] == "yes"
    assert redistribute_posture("CC-BY-4.0")["redistribute"] == "yes"
    assert redistribute_posture("CC-BY-NC-4.0")["redistribute"] == "review"
    assert redistribute_posture("all rights reserved")["redistribute"] == "no"
    assert redistribute_posture("")["redistribute"] == "no"
    assert redistribute_posture("unknown")["redistribute"] == "review"


def test_package_and_work_passport_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        admin_pin="2468",
    )
    settings.ensure_dirs()
    cat = Catalog(settings.db_path)
    samples = samples_dir()
    if samples.is_dir():
        ContentManager(settings, cat).load_samples(samples)
    cat.close()

    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()

    client = TestClient(create_app(settings))

    pkgs = client.get("/api/packages").json()
    assert pkgs, "expected sample packages"
    pid = pkgs[0]["id"]
    r = client.get(f"/api/packages/{pid}/passport")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "package"
    assert body["id"] == pid
    assert "license" in body
    assert body["redistribute"] in {"yes", "no", "review"}
    assert "redistribute_note" in body
    assert "provenance" in body
    assert "retrieval_date" in body
    assert "legal" in body

    r404 = client.get("/api/packages/does-not-exist-xyz/passport")
    assert r404.status_code == 404

    works = client.get("/api/skybrary/works").json()
    assert works["count"] >= 1
    wid = works["results"][0]["work_id"]
    r = client.get(f"/api/skybrary/works/{wid}/passport")
    assert r.status_code == 200
    wbody = r.json()
    assert wbody["kind"] == "work"
    assert wbody["work_id"] == wid
    assert wbody["license"]
    assert wbody["redistribute"] in {"yes", "no", "review"}
    assert "sha256" in wbody  # may be null for incomplete, key present
    assert "provenance" in wbody

    r = client.get(f"/api/skybrary/works/{wid}/passport", params={"verify": "true"})
    assert r.status_code == 200
    # integrity may be null if package path missing; when present must be dict
    integ = r.json().get("integrity")
    if integ is not None:
        assert "ok" in integ

    r404 = client.get("/api/skybrary/works/no-such-work/passport")
    assert r404.status_code == 404


def test_skybrary_doctor_verify(tmp_path: Path, monkeypatch):
    """CLI doctor --verify uses integrity_tree over content dir."""
    from skycache.capabilities.integrity_tree import verify_content_tree
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.ingest import bootstrap_samples_with_settings

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()

    report = verify_content_tree(settings.content_dir)
    assert report["ok"] is True
    assert report["count"] >= 1
    # package_root available for smoke that scripts exist
    assert (package_root() / "skycache" / "community" / "passport.py").is_file()
