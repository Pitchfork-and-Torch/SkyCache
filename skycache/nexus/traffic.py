"""Traffic-class monitor for DTN + gateway fair-share."""

from __future__ import annotations

from typing import Any

from skycache.nexus.dtn import DtnQueue, TRAFFIC_CLASS_RANK
from skycache.nexus.gateway import GatewayManager


def traffic_monitor(dtn: DtnQueue, gateway: GatewayManager) -> dict[str, Any]:
    stats = dtn.stats()
    by = dict(stats.get("by_class") or {})
    classes = sorted(
        by.keys(),
        key=lambda c: TRAFFIC_CLASS_RANK.get(c, 99),
    )
    queue_preview = []
    for b in dtn.pending()[:15]:
        queue_preview.append(
            {
                "id": b.id[:8],
                "kind": b.kind,
                "priority_class": b.priority_class,
                "rank": b.rank,
                "size_bytes": b.size_bytes,
            }
        )
    gw = gateway.snapshot()
    return {
        "priority_order": [
            "emergency",
            "health",
            "education",
            "agriculture",
            "maps",
            "weather",
            "general",
        ],
        "pending_by_class": by,
        "classes_present": classes,
        "queue_preview": queue_preview,
        "gateway_remaining_quota": gw.get("remaining_quota"),
        "gateway_present": gw.get("present"),
        "note": (
            "Emergency and health always schedule before general/entertainment. "
            "Shared uplinks use ethical daily quotas."
        ),
    }
