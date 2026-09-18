import json
import runpy
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings, package_root, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.web.app import create_app


def _client_with_samples(tmp_path) -> tuple[TestClient, Settings]:
    samples = samples_dir() / "packages"
    if not samples.is_dir() or not any(samples.iterdir()):
        runpy.run_path(str(package_root() / "scripts" / "make_sample_package.py"), run_name="__main__")

    data = tmp_path / "data"
    settings = Settings(data_dir=data, sim_mode=True, admin_pin="2468")
    settings.ensure_dirs()
    cat = Catalog(settings.db_path)
    ContentManager(settings, cat).load_samples(samples_dir())
    cat.close()
    return TestClient(create_app(settings)), settings


def test_api_packages(tmp_path, monkeypatch):
    client, _settings = _client_with_samples(tmp_path)
    r = client.get("/api/health")
    assert r.status_code == 200
    r = client.get("/api/packages")
    assert r.status_code == 200
    pkgs = r.json()
    assert len(pkgs) >= 6
    r = client.get("/api/status")
    assert r.json()["package_count"] >= 6
    r = client.get("/api/admin/status", headers={"X-Admin-Pin": "2468"})
    assert r.status_code == 200
    r = client.get("/")
    assert r.status_code == 200


def test_admin_handoff_export(tmp_path):
    """Wave 1.C3: PIN-gated one-button handoff writes data/handoff/ bundle."""
    client, settings = _client_with_samples(tmp_path)

    # No PIN -> 401
    r = client.post("/api/admin/handoff", json={})
    assert r.status_code == 401

    # Wrong PIN -> 401
    r = client.post(
        "/api/admin/handoff",
        json={},
        headers={"X-Admin-Pin": "0000"},
    )
    assert r.status_code == 401

    # Good PIN -> export under data/handoff
    r = client.post(
        "/api/admin/handoff",
        json={"limit": 3},
        headers={"X-Admin-Pin": "2468"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["package_count"] >= 1
    assert body["package_count"] <= 3
    assert body["bundle_name"].startswith("skycache-handoff-")
    assert body["url_path"] == f"/handoff/{body['bundle_name']}/"
    path = Path(body["path"])
    assert path.is_dir()
    assert path.parent == settings.handoff_dir.resolve()
    assert (path / "handoff.json").is_file()
    meta = json.loads((path / "handoff.json").read_text(encoding="utf-8"))
    assert meta["format"] == "skycache-handoff-v1"
    assert isinstance(meta["packages"], list)
    assert len(meta["packages"]) == body["package_count"]
    # packages copied onto disk
    for pid in meta["packages"]:
        assert (path / "packages" / pid).is_dir()

    # Static mount serves handoff.json for phone copy-on-Wi-Fi
    r = client.get(f"/handoff/{body['bundle_name']}/handoff.json")
    assert r.status_code == 200
    served = r.json()
    assert served["format"] == "skycache-handoff-v1"

    # Explicit package list
    only = meta["packages"][:1]
    r = client.post(
        "/api/admin/handoff",
        json={"packages": only},
        headers={"X-Admin-Pin": "2468"},
    )
    assert r.status_code == 200
    body2 = r.json()
    assert body2["packages"] == only
    assert body2["package_count"] == 1
