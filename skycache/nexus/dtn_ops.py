"""DTN Ops: doctor, queue status, mule verify, hop-forward sim.

Store-and-forward only. Open/FTA notices and package requests.
Not free commercial broadband. Not RFC 9171 Bundle Protocol.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.nexus.dtn import (
    BundleKind,
    DtnQueue,
    LEGAL_MULE,
    verify_mule_file,
)
from skycache.nexus.dtn_forward import HONEST as FORWARD_HONEST
from skycache.nexus.dtn_forward import forward_round
from skycache.nexus.identity import load_or_create_node_id
from skycache.nexus.mesh import MeshFabric, MeshLink, MeshPeer

HONEST = (
    "DTN: village store-and-forward with payload SHA-256, TTL, hop-limit, and custody. "
    "USB mule or mesh hop-forward. Not Starlink. Not automatic public internet bridging."
)

DOCTOR_SCHEMA = "skycache.dtn.doctor.v1"
STATUS_SCHEMA = "skycache.dtn.status.v1"
SIM_SCHEMA = "skycache.dtn.forward_sim.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _queue(settings) -> tuple[str, DtnQueue]:
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    q = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    return node_id, q


def dtn_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    settings = _settings(data_dir)
    node_id, q = _queue(settings)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    add("queue_path", True, str(q.path), 8)
    q.expire_stale()
    stats = q.stats()
    add("load", True, f"total={stats['total']} pending={stats['pending']}", 10)

    bad = 0
    for b in q.bundles:
        if not b.verify()["ok"]:
            bad += 1
    add(
        "integrity",
        bad == 0,
        "all stored bundles verify" if bad == 0 else f"{bad} bundle(s) fail SHA-256/TTL/hop checks",
        15,
    )

    mule_dir = settings.nexus_dir / "dtn-mule-doctor"
    mule_dir.mkdir(parents=True, exist_ok=True)
    probe_q = DtnQueue(mule_dir / "probe-queue.json")
    probe_q.enqueue(
        kind=BundleKind.MESSAGE,
        priority_class="health",
        origin_node=node_id,
        payload={"probe": True, "text": "dtn doctor roundtrip", "banner": HONEST},
        destination="doctor-peer",
        ttl_sec=3600,
        hop_limit=4,
    )
    mule = probe_q.export_mule(mule_dir, exporter_node=node_id)
    v = verify_mule_file(mule)
    add("mule_export_verify", bool(v.get("ok")), f"verify ok={v.get('ok')} failed={v.get('failed')}", 12)

    peer = DtnQueue(mule_dir / "peer-queue.json")
    imp = peer.import_mule_report(mule, "doctor-peer")
    add(
        "mule_import",
        int(imp.get("imported") or 0) >= 1 and not imp.get("rejected"),
        f"imported={imp.get('imported')} rejected={len(imp.get('rejected') or [])}",
        15,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_sim = score >= 70 and bad == 0

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "node_id": node_id,
        "score": score,
        "go_sim_dtn": go_sim,
        "stats": stats,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache dtn doctor",
            "skycache dtn status",
            "skycache dtn enqueue --kind message --priority health --dest '*' --text 'clinic hours'",
            "skycache dtn export --out data/nexus/mule",
            "skycache dtn verify PATH",
            "skycache dtn import PATH",
            "skycache dtn forward-sim --nodes 3",
        ],
        "legal": LEGAL_MULE,
    }


def dtn_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    settings = _settings(data_dir)
    node_id, q = _queue(settings)
    q.expire_stale()
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "node_id": node_id,
        "queue": str(q.path),
        "stats": q.stats(),
        "pending_preview": [
            {
                "id": b.id,
                "kind": b.kind,
                "priority_class": b.priority_class,
                "destination": b.destination,
                "custody_node": b.custody_node,
                "hops": list(b.hops),
                "ttl_sec": b.ttl_sec,
                "payload_sha256": b.payload_sha256[:16],
            }
            for b in q.pending()[:20]
        ],
        "banner": HONEST,
    }


def dtn_enqueue(
    *,
    data_dir: Path | None = None,
    kind: str = "message",
    priority_class: str = "general",
    destination: str = "*",
    text: str = "",
    package_id: str = "",
    ttl_sec: int = 604800,
    hop_limit: int = 8,
) -> dict[str, Any]:
    settings = _settings(data_dir)
    node_id, q = _queue(settings)
    payload: dict[str, Any] = {}
    if text:
        payload["text"] = text[:4000]
    if package_id:
        payload["package_id"] = package_id
        payload["action"] = "fetch_open"
    if not payload:
        return {"ok": False, "error": "text or package_id required", "banner": HONEST}
    b = q.enqueue(
        kind=kind,
        priority_class=priority_class,
        origin_node=node_id,
        payload=payload,
        destination=destination,
        ttl_sec=ttl_sec,
        hop_limit=hop_limit,
    )
    return {
        "ok": True,
        "id": b.id,
        "kind": b.kind,
        "priority_class": b.priority_class,
        "destination": b.destination,
        "payload_sha256": b.payload_sha256,
        "hop_limit": b.hop_limit,
        "ttl_sec": b.ttl_sec,
        "banner": HONEST,
    }


def dtn_export(*, data_dir: Path | None = None, out_dir: Path | None = None, limit: int = 50) -> dict[str, Any]:
    settings = _settings(data_dir)
    node_id, q = _queue(settings)
    dest = Path(out_dir) if out_dir else settings.nexus_dir / "mule"
    path = q.export_mule(dest, limit=limit, exporter_node=node_id)
    v = verify_mule_file(path)
    return {
        "ok": bool(v.get("ok")),
        "path": str(path),
        "verify": v,
        "stats": q.stats(),
        "banner": HONEST,
    }


def dtn_import(*, path: Path, data_dir: Path | None = None) -> dict[str, Any]:
    settings = _settings(data_dir)
    node_id, q = _queue(settings)
    v = verify_mule_file(path)
    if not v.get("ok"):
        return {"ok": False, "error": "mule failed integrity verify", "verify": v, "banner": HONEST}
    rep = q.import_mule_report(path, node_id)
    return {"ok": bool(rep.get("ok")), **rep, "verify": v, "banner": HONEST}


def dtn_verify(*, path: Path | None = None, data_dir: Path | None = None) -> dict[str, Any]:
    if path:
        v = verify_mule_file(path)
        return {**v, "banner": HONEST}
    settings = _settings(data_dir)
    _node_id, q = _queue(settings)
    rows = [b.verify() for b in q.bundles]
    bad = [r for r in rows if not r["ok"]]
    return {
        "ok": not bad,
        "bundle_count": len(rows),
        "failed": len(bad),
        "checks": rows[:50],
        "banner": HONEST,
    }


def run_forward_sim(*, nodes: int = 3, rounds: int = 2) -> dict[str, Any]:
    """In-process  chain  node-1 -> ... -> node-N  unicast + gateway request."""
    n = max(2, min(int(nodes), 8))
    import tempfile

    tmp = tempfile.TemporaryDirectory(prefix="skycache-dtn-")
    base = Path(tmp.name)
    queues: dict[str, DtnQueue] = {}
    meshes: dict[str, MeshFabric] = {}
    try:
        names = [f"node-{i + 1}" for i in range(n)]
        for i, name in enumerate(names):
            root = base / name
            mesh = MeshFabric(data_dir=root / "data", node_id=name, mode="sim", band="sim")
            mesh.start()
            if i == 0:
                mesh.peers[name] = MeshPeer(
                    node_id=name, address=f"sim://{name}", role="gateway"
                )
            queues[name] = DtnQueue(root / "data" / "nexus" / "dtn-queue.json")
            meshes[name] = mesh

        for i, name in enumerate(names):
            mesh = meshes[name]
            if i > 0:
                left = names[i - 1]
                mesh.upsert_peer(
                    MeshPeer(
                        node_id=left,
                        address=f"sim://{left}",
                        hop_count=1,
                        role="gateway" if left == names[0] else "node",
                    )
                )
                mesh.links.append(MeshLink(a=name, b=left, quality=0.9))
            if i + 1 < n:
                right = names[i + 1]
                mesh.upsert_peer(
                    MeshPeer(node_id=right, address=f"sim://{right}", hop_count=1, role="node")
                )
                mesh.links.append(MeshLink(a=name, b=right, quality=0.9))

        src = names[0]
        dest = names[-1]
        notice = queues[src].enqueue(
            kind=BundleKind.MESSAGE,
            priority_class="emergency",
            origin_node=src,
            payload={"text": "clinic water safe", "alert": True},
            destination=dest,
            hop_limit=n + 1,
        )
        req = queues[dest].enqueue(
            kind=BundleKind.REQUEST,
            priority_class="health",
            origin_node=dest,
            payload={"package_id": "health-ors-001", "action": "fetch_open"},
            destination="*",
            hop_limit=n + 1,
        )

        round_reports: list[dict[str, Any]] = []
        for _ in range(max(1, int(rounds))):
            step = []
            for name in names:
                others = {k: v for k, v in queues.items() if k != name}
                step.append(
                    forward_round(
                        local_node=name,
                        local_queue=queues[name],
                        mesh=meshes[name],
                        peer_queues=others,
                    )
                )
            round_reports.append({"forwards": step})

        dest_has_notice = queues[dest].has_id(notice.id)
        gw_has_req = queues[src].has_id(req.id)
        dest_bundle = next((b for b in queues[dest].bundles if b.id == notice.id), None)
        notice_delivered = bool(dest_bundle and dest_bundle.status == "delivered")
        ok = dest_has_notice and notice_delivered and gw_has_req
        receipt = {
            "schema": SIM_SCHEMA,
            "ok": ok,
            "generated_at": _iso_now(),
            "software_version": __version__,
            "nodes": names,
            "notice_id": notice.id,
            "request_id": req.id,
            "notice_reached_dest": dest_has_notice,
            "notice_delivered_at_dest": notice_delivered,
            "request_reached_gateway": gw_has_req,
            "hops_at_dest": list(dest_bundle.hops) if dest_bundle else [],
            "rounds": round_reports,
            "banner": FORWARD_HONEST,
        }
        receipt_path = base / "forward-sim-receipt.json"
        # Copy receipt out of tmp before cleanup: caller gets the dict; file is ephemeral.
        (base / "forward-sim-receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        receipt["receipt_ephemeral"] = str(receipt_path)
        return receipt
    finally:
        try:
            tmp.cleanup()
        except (PermissionError, OSError):
            pass
