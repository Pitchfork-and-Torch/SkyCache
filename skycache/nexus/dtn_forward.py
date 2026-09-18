"""Hop-by-hop DTN forwarding over the village mesh (sim-friendly).

Custody moves with the bundle. Same bundle id is preserved so peers
dedupe. Not live satellite internet. Not full Bundle Protocol.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from skycache.nexus.dtn import Bundle, DtnQueue, bundle_from_dict
from skycache.nexus.mesh import MeshFabric

HONEST = (
    "DTN hop-forward is store-and-forward over village mesh or USB mule. "
    "Unlicensed Wi-Fi/ISM only. Not commercial broadband or satellite uplink."
)


def select_next_hops(
    *,
    bundle: Bundle,
    local_node: str,
    mesh: MeshFabric,
    peer_ids: set[str],
    max_flood: int = 3,
) -> list[str]:
    """Pick next custody holders. Unicast to dest when it is a neighbor."""
    already = set(bundle.hops or []) | {local_node}
    dest = bundle.destination or "*"
    neighbor_ids = {p for p in mesh.peers.keys() if p != local_node}
    ranked = [
        p
        for p in mesh.prefer_power_route()
        if p in peer_ids and p in neighbor_ids and p not in already
    ]

    if dest != "*" and dest not in already:
        if dest in neighbor_ids and dest in peer_ids:
            return [dest]
        if ranked:
            return ranked[:1]
        return []

    if bundle.kind == "request":
        gateways = [
            p.node_id
            for p in mesh.peers.values()
            if p.role == "gateway"
            and p.node_id in peer_ids
            and p.node_id in neighbor_ids
            and p.node_id not in already
        ]
        if gateways:
            return gateways[:1]

    return ranked[: max(1, int(max_flood))]


def _clone_for_peer(bundle: Bundle, local_node: str, next_node: str) -> Bundle:
    raw = asdict(bundle)
    hops = list(bundle.hops or [])
    if local_node not in hops:
        hops.append(local_node)
    raw["hops"] = hops
    raw["custody_node"] = next_node
    raw["delivered"] = False
    raw["status"] = "pending"
    raw["reject_reason"] = ""
    return bundle_from_dict(raw, backfill_hash=False)


def forward_round(
    *,
    local_node: str,
    local_queue: DtnQueue,
    mesh: MeshFabric,
    peer_queues: dict[str, DtnQueue],
    max_bundles: int = 20,
    max_flood: int = 3,
) -> dict[str, Any]:
    """Forward pending bundles to mesh neighbors (in-process / sim)."""
    expired = local_queue.expire_stale()
    peer_ids = set(peer_queues.keys())
    forwarded: list[dict[str, Any]] = []
    delivered_local: list[str] = []
    dropped: list[dict[str, Any]] = []
    processed = 0

    for b in list(local_queue.pending()):
        if processed >= max_bundles:
            break
        check = b.verify()
        if not check["ok"]:
            local_queue.mark_status(b.id, "rejected", reason=",".join(check["reasons"]))
            dropped.append({"id": b.id, "reasons": check["reasons"]})
            processed += 1
            continue

        dest = b.destination or "*"
        if dest == local_node:
            if b.kind == "request":
                # Arrived at the intended node; keep pending for gateway pulls.
                processed += 1
                continue
            local_queue.mark_delivered(b.id)
            delivered_local.append(b.id)
            processed += 1
            continue

        hops = select_next_hops(
            bundle=b,
            local_node=local_node,
            mesh=mesh,
            peer_ids=peer_ids,
            max_flood=max_flood,
        )
        if not hops:
            if dest == "*" and b.kind != "request":
                # Flood complete: every known peer already has a hop record.
                local_queue.mark_delivered(b.id)
                delivered_local.append(b.id)
            processed += 1
            continue

        sent = 0
        for nxt in hops:
            q = peer_queues.get(nxt)
            if q is None:
                continue
            if q.has_id(b.id):
                continue
            clone = _clone_for_peer(b, local_node, nxt)
            limit = int(clone.hop_limit or 0)
            if clone.hop_count() > limit:
                dropped.append({"id": b.id, "reasons": ["hop_limit_exceeded"], "peer": nxt})
                continue
            q.bundles.append(clone)
            q.save()
            sent += 1

        if sent:
            local_queue.mark_status(b.id, "forwarded")
            forwarded.append({"id": b.id, "to": hops, "kind": b.kind, "dest": dest})
        processed += 1

    return {
        "node": local_node,
        "processed": processed,
        "forwarded": forwarded,
        "delivered_local": delivered_local,
        "dropped": dropped,
        "expired": expired,
        "pending_after": len(local_queue.pending()),
        "legal": HONEST,
    }
