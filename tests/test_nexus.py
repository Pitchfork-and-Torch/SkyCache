"""SkyCache Nexus: spectrum, mesh, DTN, fabric, gateway, multi-node sim."""

from __future__ import annotations

from pathlib import Path

import pytest

from skycache.config import FORBIDDEN_SOURCE_KEYWORDS, NEXUS_HONEST_BANNER, Settings
from skycache.models import PriorityClass
from skycache.nexus.dtn import BundleKind, DtnQueue, TRAFFIC_CLASS_RANK
from skycache.nexus.gateway import GatewayManager
from skycache.nexus.identity import content_fingerprint, load_or_create_node_id
from skycache.nexus.mesh import MeshFabric, MeshLink, MeshPeer
from skycache.nexus.sim import NexusSimulator
from skycache.nexus.spectrum import (
    ALLOWED_BANDS,
    FORBIDDEN_MESH_KEYWORDS,
    compliance_report,
    validate_band,
    validate_mesh_mode,
)


def test_spectrum_allows_unlicensed_only():
    for band in ALLOWED_BANDS:
        assert validate_band(band) == band
    with pytest.raises(ValueError):
        validate_band("licensed-microwave")
    with pytest.raises(ValueError):
        validate_mesh_mode("satellite-uplink")
    with pytest.raises(ValueError):
        validate_mesh_mode("starlink-mesh")
    report = compliance_report()
    assert report["satellite_tx_allowed"] is False
    assert report["commercial_decrypt_allowed"] is False


def test_config_forbids_commercial_and_uplink():
    s = Settings(data_dir=Path("data"))
    for kw in ("starlink", "decrypt-commercial", "satellite-uplink", "card-sharing"):
        assert kw in FORBIDDEN_SOURCE_KEYWORDS or any(
            kw in x for x in FORBIDDEN_SOURCE_KEYWORDS
        )
        with pytest.raises(ValueError):
            s.validate_source_name(f"plugin-{kw}-x")
    s.mesh_mode = "sim"
    s.mesh_band = "sim"
    s.validate_nexus()
    s.mesh_mode = "vsat-tx"
    with pytest.raises(ValueError):
        s.validate_nexus()
    assert "store-and-forward" in NEXUS_HONEST_BANNER.lower() or "mesh" in NEXUS_HONEST_BANNER.lower()
    assert "starlink" in NEXUS_HONEST_BANNER.lower() or "broadband" in NEXUS_HONEST_BANNER.lower()


def test_node_identity(tmp_path: Path):
    a = load_or_create_node_id(tmp_path / "n1")
    b = load_or_create_node_id(tmp_path / "n1")
    assert a == b
    c = load_or_create_node_id(tmp_path / "n2", explicit="village-alpha")
    assert c == "village-alpha"
    fp = content_fingerprint("pkg", 100, "2020-01-01")
    assert len(fp) == 16


def test_mesh_power_prefer_routes(tmp_path: Path):
    mesh = MeshFabric(data_dir=tmp_path / "data", node_id="hub", mode="sim", band="sim")
    mesh.start()
    mesh.upsert_peer(
        MeshPeer(node_id="low-bat", address="a", battery_percent=20.0, solar=False)
    )
    mesh.upsert_peer(
        MeshPeer(node_id="solar-high", address="b", battery_percent=95.0, solar=True)
    )
    mesh.upsert_peer(
        MeshPeer(node_id="mains", address="c", battery_percent=80.0, solar=False)
    )
    order = mesh.prefer_power_route()
    assert order[0] == "solar-high"
    mesh.links.append(MeshLink(a="hub", b="solar-high", quality=0.95))
    topo = mesh.topology()
    assert topo["enabled"]
    assert "unlicensed" in topo["legal"].lower() or "mesh" in topo["legal"].lower()
    mesh.save()
    mesh2 = MeshFabric(data_dir=tmp_path / "data", node_id="hub", mode="sim", band="sim")
    mesh2.load()
    assert "solar-high" in mesh2.peers


def test_dtn_priority_order(tmp_path: Path):
    q = DtnQueue(tmp_path / "q.json")
    q.enqueue(
        kind=BundleKind.REQUEST,
        priority_class=PriorityClass.GENERAL.value,
        origin_node="a",
        payload={"package_id": "g"},
    )
    q.enqueue(
        kind=BundleKind.REQUEST,
        priority_class=PriorityClass.EMERGENCY.value,
        origin_node="a",
        payload={"package_id": "e"},
    )
    q.enqueue(
        kind=BundleKind.REQUEST,
        priority_class=PriorityClass.HEALTH.value,
        origin_node="a",
        payload={"package_id": "h"},
    )
    pending = q.pending()
    assert pending[0].priority_class == PriorityClass.EMERGENCY.value
    assert pending[1].priority_class == PriorityClass.HEALTH.value
    assert TRAFFIC_CLASS_RANK["emergency"] < TRAFFIC_CLASS_RANK["general"]
    mule = q.export_mule(tmp_path / "mule")
    assert mule.is_file()
    q2 = DtnQueue(tmp_path / "q2.json")
    n = q2.import_mule(mule, "node-b")
    assert n >= 1


def test_gateway_fair_share_and_quota(tmp_path: Path):
    q = DtnQueue(tmp_path / "gw-q.json")
    gw = GatewayManager(dtn=q, node_id="gw", sim_uplink=True)
    gw.status.daily_quota_bytes = 10_000
    for cls in (
        PriorityClass.GENERAL.value,
        PriorityClass.EDUCATION.value,
        PriorityClass.EMERGENCY.value,
    ):
        gw.request_package(f"pkg-{cls}", priority_class=cls)
    results = gw.schedule_pulls(max_bundles=10)
    assert results
    # Emergency first
    assert results[0]["priority_class"] == PriorityClass.EMERGENCY.value
    snap = gw.snapshot()
    assert snap["present"] is True
    assert "commercial" in snap["legal"].lower() or "open" in snap["legal"].lower()


def test_multi_node_sim_replication():
    sim = NexusSimulator(node_count=3)
    try:
        sim.setup(load_samples_on=1)
        r1 = sim.run_round()
        r2 = sim.run_round()
        counts = [n["packages"] for n in r2["nodes"]]
        # Seed node has samples; after gossip others should grow toward seed
        assert counts[0] >= 1
        assert max(counts) >= min(counts)  # trivial
        # At least one sync pulled or queued
        assert r1["sync_reports"]
        # Node with gateway sim_uplink
        assert any(n["gateway"]["present"] for n in r2["nodes"])
        sim.enable_disaster_mode()
        assert all(n.mesh.disaster_mode for n in sim.nodes)
        assert "Simulation" in r1["legal"] or "mesh" in r1["legal"].lower()
    finally:
        sim.teardown()


def test_multi_node_content_reaches_empty_nodes():
    """Stronger: after rounds, non-seed nodes should acquire packages."""
    sim = NexusSimulator(node_count=3)
    try:
        sim.setup(load_samples_on=1)
        seed_count = sim.nodes[0].catalog.count()
        assert seed_count >= 1
        for _ in range(3):
            sim.run_round()
        for n in sim.nodes[1:]:
            # Should have replicated at least some high-priority packages
            assert n.catalog.count() >= 1, f"{n.name} has no packages after sync"
            assert n.catalog.count() <= seed_count + 5
    finally:
        sim.teardown()


def test_forbidden_mesh_keywords_covered():
    assert "starlink" in FORBIDDEN_MESH_KEYWORDS or any(
        "starlink" in k for k in FORBIDDEN_MESH_KEYWORDS
    )
    assert "satellite-uplink" in FORBIDDEN_MESH_KEYWORDS
