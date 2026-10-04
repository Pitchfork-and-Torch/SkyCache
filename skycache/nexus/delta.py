"""Delta / fingerprint helpers for fabric sync (lightweight CRDT-ish inventory)."""

from __future__ import annotations

from typing import Any

from skycache.nexus.fabric import ContentFabric


def delta_against_remote(
    fabric: ContentFabric,
    remote_manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare local vs remote fingerprints - what to pull / offer."""
    local = {m.package_id: m for m in fabric.local_manifest()}
    remote = {str(m.get("package_id")): m for m in remote_manifest if m.get("package_id")}

    only_remote = []
    only_local = []
    fingerprint_mismatch = []

    for pid, rm in remote.items():
        if pid not in local:
            only_remote.append(rm)
        elif local[pid].fingerprint != rm.get("fingerprint"):
            fingerprint_mismatch.append(
                {
                    "package_id": pid,
                    "local_fp": local[pid].fingerprint,
                    "remote_fp": rm.get("fingerprint"),
                    "priority_class": local[pid].priority_class,
                }
            )

    for pid, lm in local.items():
        if pid not in remote:
            only_local.append(lm.to_dict())

    # Prioritize pulls
    want = fabric.missing_from(list(remote.values()), max_items=50)
    return {
        "local_count": len(local),
        "remote_count": len(remote),
        "pull_candidates": want,
        "offer_to_peer": only_local[:50],
        "fingerprint_mismatch": fingerprint_mismatch,
        "only_on_remote": len(only_remote),
        "only_on_local": len(only_local),
    }
