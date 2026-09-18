"""DTN store-and-forward: integrity, TTL, hop-limit, mule, mesh custody, API."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.messaging.dtn_lite import DtnLiteStore
from skycache.models import PriorityClass
from skycache.nexus.dtn import (
    DTN_FORMAT_V1,
    BundleKind,
    DtnQueue,
    payload_digest,
    verify_mule_file,
)
from skycache.nexus.dtn_forward import forward_round, select_next_hops
from skycache.nexus.dtn_ops import dtn_doctor, dtn_enqueue, run_forward_sim
from skycache.nexus.mesh import MeshFabric, MeshLink, MeshPeer
from skycache.web.app import create_app


def test_payload_digest_stable():
    a = payload_digest({"z": 1, "a": "x"})
    b = payload_digest({"a": "x", "z": 1})
    assert a == b
    assert len(a) == 64
    assert a != payload_digest({"a": "y", "z": 1})


def test_ttl_expires_pending(tmp_path: Path):
    q = DtnQueue(tmp_path / "q.json")
    b = q.enqueue(
        kind=BundleKind.MESSAGE,
        priority_class=PriorityClass.HEALTH.value,
        origin_node="a",
        payload={"text": "stale"},
        ttl_sec=10,
    )
    b.created_at = time.time() - 100
    q.save()
    n = q.expire_stale()
    assert n >= 1
    assert q.pending() == []
    assert any(x.status == "expired" for x in q.bundles)


def test_mule_v2_rejects_tamper(tmp_path: Path):
    q = DtnQueue(tmp_path / "a.json")
    q.enqueue(
        kind=BundleKind.MESSAGE,
        priority_class="emergency",
        origin_node="hub",
        payload={"text": "boil water"},
        destination="clinic",
    )
    mule = q.export_mule(tmp_path / "mule", exporter_node="hub")
    assert verify_mule_file(mule)["ok"] is True

    data = json.loads(mule.read_text(encoding="utf-8"))
    data["bundles"][0]["payload"]["text"] = "tampered"
    mule.write_text(json.dumps(data), encoding="utf-8")
    v = verify_mule_file(mule)
    assert v["ok"] is False
    assert v["failed"] >= 1

    peer = DtnQueue(tmp_path / "b.json")
    rep = peer.import_mule_report(mule, "clinic")
    assert rep["imported"] == 0
    assert rep["rejected"]


def test_mule_v1_backfill_still_imports(tmp_path: Path):
    q = DtnQueue(tmp_path / "old.json")
    raw = {
        "format": DTN_FORMAT_V1,
        "bundles": [
            {
                "id": "legacy-1",
                "kind": "message",
                "priority_class": "health",
                "created_at": time.time(),
                "origin_node": "usb",
                "destination": "*",
                "payload": {"text": "legacy notice"},
                "size_bytes": 0,
                "delivered": False,
                "hops": ["usb"],
            }
        ],
    }
    path = tmp_path / "legacy-mule.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    n = q.import_mule(path, "node-b")
    assert n == 1
    got = q.bundles[0]
    assert got.payload_sha256
    assert got.verify()["ok"] is True


def test_hop_limit_stops_forward(tmp_path: Path):
    a_q = DtnQueue(tmp_path / "a.json")
    b_q = DtnQueue(tmp_path / "b.json")
    c_q = DtnQueue(tmp_path / "c.json")
    mesh_a = MeshFabric(data_dir=tmp_path / "a", node_id="node-1", mode="sim", band="sim")
    mesh_a.start()
    mesh_a.upsert_peer(MeshPeer(node_id="node-2", address="sim://node-2"))
    mesh_a.links.append(MeshLink(a="node-1", b="node-2"))
    mesh_b = MeshFabric(data_dir=tmp_path / "b", node_id="node-2", mode="sim", band="sim")
    mesh_b.start()
    mesh_b.upsert_peer(MeshPeer(node_id="node-1", address="sim://node-1"))
    mesh_b.upsert_peer(MeshPeer(node_id="node-3", address="sim://node-3"))
    mesh_b.links.append(MeshLink(a="node-2", b="node-3"))

    a_q.enqueue(
        kind=BundleKind.MESSAGE,
        priority_class="emergency",
        origin_node="node-1",
        payload={"text": "do not flood forever"},
        destination="node-3",
        hop_limit=1,
    )
    forward_round(
        local_node="node-1",
        local_queue=a_q,
        mesh=mesh_a,
        peer_queues={"node-2": b_q, "node-3": c_q},
    )
    assert b_q.bundles, "first hop should accept custody"
    forward_round(
        local_node="node-2",
        local_queue=b_q,
        mesh=mesh_b,
        peer_queues={"node-1": a_q, "node-3": c_q},
    )
    assert not c_q.bundles, "hop_limit=1 must not reach node-3"


def test_chain_unicast_and_gateway_request():
    sim = run_forward_sim(nodes=3, rounds=2)
    assert sim["ok"] is True
    assert sim["notice_reached_dest"] is True
    assert sim["notice_delivered_at_dest"] is True
    assert sim["request_reached_gateway"] is True
    assert "node-2" in sim["hops_at_dest"]
    assert "not commercial" in sim["banner"].lower() or "store-and-forward" in sim["banner"].lower()


def test_request_prefers_gateway_role(tmp_path: Path):
    mesh = MeshFabric(data_dir=tmp_path, node_id="leaf", mode="sim", band="sim")
    mesh.start()
    mesh.upsert_peer(MeshPeer(node_id="solar", address="a", battery_percent=99, solar=True, role="node"))
    mesh.upsert_peer(MeshPeer(node_id="gw", address="b", battery_percent=40, solar=False, role="gateway"))
    q = DtnQueue(tmp_path / "q.json")
    b = q.enqueue(
        kind=BundleKind.REQUEST,
        priority_class="health",
        origin_node="leaf",
        payload={"package_id": "health-ors-001"},
        destination="*",
    )
    hops = select_next_hops(
        bundle=b,
        local_node="leaf",
        mesh=mesh,
        peer_ids={"solar", "gw"},
    )
    assert hops == ["gw"]


def test_dtn_lite_usb_import_and_bridge(tmp_path: Path):
    store = DtnLiteStore(path=tmp_path / "outbox.json")
    store.load()
    msg = store.enqueue("nurse", "hours", "clinic 8-12", origin_node="hub")
    assert msg.payload_sha256
    usb = store.export_usb(tmp_path / "usb")
    peer = DtnLiteStore(path=tmp_path / "peer.json")
    peer.load()
    imp = peer.import_usb(usb, local_node="clinic")
    assert imp["imported"] == 1
    assert peer.list_pending()[0].payload_sha256 == msg.payload_sha256

    tampered = json.loads(usb.read_text(encoding="utf-8"))
    tampered["messages"][0]["body"] = "changed"
    bad = tmp_path / "usb-bad.json"
    bad.write_text(json.dumps(tampered), encoding="utf-8")
    other = DtnLiteStore(path=tmp_path / "other.json")
    other.load()
    bad_imp = other.import_usb(bad, local_node="x")
    assert bad_imp["imported"] == 0
    assert bad_imp["rejected"]

    nexus = DtnQueue(tmp_path / "nexus.json")
    ids = store.bridge_to_nexus(nexus, origin_node="hub", message=msg)
    assert ids
    assert nexus.pending()[0].kind == "message"
    assert nexus.pending()[0].payload["notice_id"] == msg.id


def test_dtn_doctor_and_cli_enqueue(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    doc = dtn_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.dtn.doctor.v1"
    assert doc["go_sim_dtn"] is True
    assert doc["score"] >= 70

    enq = dtn_enqueue(
        data_dir=settings.data_dir,
        kind="message",
        priority_class="health",
        destination="*",
        text="ors mix 1L",
    )
    assert enq["ok"] is True
    assert enq["payload_sha256"]


def test_api_dtn_and_messages(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True, admin_pin="2468")
    settings.ensure_dirs()
    client = TestClient(create_app(settings))

    r = client.get("/api/dtn/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_sim_dtn") is True

    r2 = client.post(
        "/api/dtn/enqueue",
        json={"kind": "message", "text": "school closed friday", "priority": "education"},
    )
    assert r2.status_code == 200
    assert r2.json().get("ok") is True

    r3 = client.post(
        "/api/dtn/enqueue",
        json={"kind": "request", "package_id": "health-ors-001", "priority": "health"},
    )
    assert r3.status_code == 401

    r4 = client.post(
        "/api/dtn/enqueue",
        json={
            "kind": "request",
            "package_id": "health-ors-001",
            "priority": "health",
            "admin_pin": "2468",
        },
    )
    assert r4.status_code == 200
    assert r4.json().get("ok") is True

    r5 = client.post(
        "/api/messages",
        json={"author": "teacher", "subject": "notice", "body": "bring water"},
    )
    assert r5.status_code == 200
    msg = r5.json()
    assert msg.get("payload_sha256")
    assert msg.get("nexus_bundle_id")

    listed = client.get("/api/messages")
    assert listed.status_code == 200
    assert any(m.get("id") == msg["id"] for m in listed.json())

    r6 = client.post("/api/dtn/export-mule", json={})
    assert r6.status_code == 200
    mule_path = r6.json().get("path")
    assert mule_path and Path(mule_path).is_file()

    r7 = client.post("/api/dtn/verify", json={"path": mule_path})
    assert r7.status_code == 200
    assert r7.json().get("ok") is True
