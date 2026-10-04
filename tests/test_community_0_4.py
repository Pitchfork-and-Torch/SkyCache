"""Nexus 0.4 community services: search, boards, ratings, licenses, control plane."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.community.boards import BoardStore
from skycache.community.licenses import LicenseInventory
from skycache.community.ratings import RatingsStore
from skycache.community.search import search_catalog
from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.nexus.control_plane import ControlPlane
from skycache.nexus.delta import delta_against_remote
from skycache.nexus.fabric import ContentFabric
from skycache.nexus.dtn import DtnQueue
from skycache.nexus.mesh import MeshFabric
from skycache.web.app import create_app


def _seed(tmp_path: Path) -> tuple[Settings, Catalog]:
    data = tmp_path / "data"
    settings = Settings(data_dir=data, sim_mode=True, mesh_mode="sim", mesh_band="sim")
    settings.ensure_dirs()
    cat = Catalog(settings.db_path)
    if samples_dir().is_dir():
        ContentManager(settings, cat).load_samples(samples_dir())
    return settings, cat


def test_search_and_licenses(tmp_path: Path):
    settings, cat = _seed(tmp_path)
    hits = search_catalog(cat, "health")
    assert any("health" in h["id"] or h["priority_class"] == "health" for h in hits)
    inv = LicenseInventory(cat).report()
    assert inv["package_count"] >= 1
    assert "by_license" in inv
    cat.close()


def test_ratings_and_boards(tmp_path: Path):
    settings, cat = _seed(tmp_path)
    rates = RatingsStore(settings.db_path)
    boards = BoardStore(settings.db_path)
    pid = cat.list_packages(limit=1)[0].package.id
    s = rates.rate(pid, 5, voter_token="device-a")
    assert s["average"] == 5
    rates.rate(pid, 3, voter_token="device-b")
    assert rates.summary(pid)["count"] == 2
    post = boards.post(
        board="school",
        title="Class starts 8am",
        body="Bring water bottles.",
        author="teacher",
    )
    assert post["board"] == "school"
    assert len(boards.list_posts(board="school")) >= 1
    rates.close()
    boards.close()
    cat.close()


def test_control_plane_and_delta(tmp_path: Path):
    settings, cat = _seed(tmp_path)
    cp = ControlPlane(settings.data_dir, "node-a", enabled=True, band="sim")
    msg = cp.publish("alert", {"text": "Flood drill"}, priority="emergency")
    assert msg.id
    assert cp.pending_alerts()
    mesh = MeshFabric(data_dir=settings.data_dir, node_id="node-a", mode="sim", band="sim")
    mesh.start()
    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    fabric = ContentFabric(
        node_id="node-a",
        catalog=cat,
        content=ContentManager(settings, cat),
        mesh=mesh,
        dtn=dtn,
        content_dir=settings.content_dir,
    )
    remote = [
        {
            "package_id": "missing-pack-xyz",
            "priority_class": "health",
            "size_bytes": 10,
            "score": 100,
            "fingerprint": "abc",
            "node_id": "peer",
        }
    ]
    delta = delta_against_remote(fabric, remote)
    assert delta["only_on_remote"] >= 1
    assert delta["pull_candidates"]
    cat.close()


def test_api_0_4_endpoints(tmp_path: Path):
    settings, cat = _seed(tmp_path)
    cat.close()
    client = TestClient(create_app(settings))
    r = client.get("/api/search", params={"q": "education"})
    assert r.status_code == 200
    assert "results" in r.json()
    r = client.get("/api/boards")
    assert r.status_code == 200
    r = client.post(
        "/api/boards/posts",
        json={"board": "clinic", "title": "Hours", "body": "Open today", "author": "nurse"},
    )
    assert r.status_code == 200
    pkgs = client.get("/api/packages").json()
    pid = pkgs[0]["id"]
    r = client.post(f"/api/packages/{pid}/rating", json={"stars": 4, "token": "t1"})
    assert r.status_code == 200
    r = client.get("/api/licenses")
    assert r.status_code == 200
    r = client.get("/api/onboarding")
    assert r.status_code == 200
    assert len(r.json()["steps"]) >= 4
    r = client.get("/api/nexus/power-map")
    assert r.status_code == 200
    r = client.get("/api/nexus/traffic")
    assert r.status_code == 200
    r = client.post("/api/nexus/control/alert", json={"text": "Test alert"})
    assert r.status_code == 200
    r = client.get("/api/admin/status", headers={"X-Admin-Pin": "2468"})
    assert r.status_code == 200
    body = r.json()
    assert "power_map" in body
    assert "traffic" in body
    assert "licenses" in body
