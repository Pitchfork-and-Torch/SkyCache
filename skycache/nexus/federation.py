"""Works-manifest federation helpers (Wave 3.B6 production surface).

Builds on ContentFabric.gossip_payload / sync_with_peer_manifest.
Sim-first multi-node delta sync of high-tier open works metadata + packages.
"""

from __future__ import annotations

from typing import Any

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.nexus.dtn import DtnQueue
from skycache.nexus.fabric import ContentFabric
from skycache.nexus.mesh import MeshFabric
from skycache.skybrary.catalog import SkybraryCatalog


def build_fabric(settings: Settings, *, sky: SkybraryCatalog | None = None) -> ContentFabric:
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    mesh = MeshFabric(
        data_dir=settings.data_dir,
        node_id=settings.node_id or "node",
        enabled=True,
        mode=settings.mesh_mode,
        band=settings.mesh_band,
    )
    mesh.load()
    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    sky_cat = sky or SkybraryCatalog(settings.skybrary_db_path)
    return ContentFabric(
        node_id=settings.node_id or "node",
        catalog=catalog,
        content=content,
        mesh=mesh,
        dtn=dtn,
        content_dir=settings.content_dir,
        skybrary=sky_cat,
    )


def multi_node_sim_sync(
    nodes: list[Settings],
    *,
    rounds: int = 1,
) -> dict[str, Any]:
    """
    In-process multi-node works + package federation for CI.

    Each round: every ordered pair (i,j) i!=j runs j.sync_with_peer_manifest(i.gossip).
    """
    if len(nodes) < 2:
        raise ValueError("need at least 2 nodes for federation sim")
    fabrics = [build_fabric(s) for s in nodes]
    history: list[dict[str, Any]] = []
    for r in range(max(1, int(rounds))):
        round_pulls = 0
        round_works = 0
        for i, fa in enumerate(fabrics):
            gossip = fa.gossip_payload()
            for j, fb in enumerate(fabrics):
                if i == j:
                    continue
                peer_root = nodes[i].content_dir
                rep = fb.sync_with_peer_manifest(gossip, peer_content_root=peer_root)
                round_pulls += len(rep.get("pulled") or [])
                round_works += int(rep.get("works_imported") or 0)
                history.append({"round": r, "from": nodes[i].node_id, "to": nodes[j].node_id, **rep})
        # no-op keep variables used
        _ = (round_pulls, round_works)

    snapshots = []
    for s, f in zip(nodes, fabrics, strict=True):
        sky = f.skybrary
        snapshots.append(
            {
                "node_id": s.node_id,
                "packages": len(f.local_manifest()),
                "works": sky.count() if sky is not None else 0,
            }
        )
    return {
        "schema": "skycache.nexus.federation.sim.v1",
        "nodes": len(nodes),
        "rounds": max(1, int(rounds)),
        "snapshots": snapshots,
        "exchanges": history,
        "legal": "Open/PD works and packages only - unlicensed mesh sim",
        "honest": "Sim filesystem copy; real batman-adv still operator-validated on hardware",
    }


def high_tier_works_delta(
    local: ContentFabric,
    remote_gossip: dict[str, Any],
    *,
    max_tier: int = 2,
    max_items: int = 40,
) -> list[dict[str, Any]]:
    """Missing remote works with civilizational_tier <= max_tier (foundational first)."""
    wm = remote_gossip.get("works_manifest") or {}
    missing = local.missing_works_from(wm, max_items=max_items * 3)
    out = []
    for w in missing:
        tier = int(w.get("civilizational_tier") or 5)
        if tier <= max_tier:
            out.append(w)
        if len(out) >= max_items:
            break
    return out


# Priority-class order for survival-first federation (lower index = pull first)
PRIORITY_FEDERATION_ORDER = (
    "emergency",
    "health",
    "education",
    "agriculture",
    "weather",
    "maps",
    "general",
    "telemetry_raw",
)


def priority_works_delta(
    local: ContentFabric,
    remote_gossip: dict[str, Any],
    *,
    prefer_classes: tuple[str, ...] | list[str] | None = None,
    max_items: int = 40,
) -> list[dict[str, Any]]:
    """Missing remote works ordered by survival priority class then tier.

    Prefer emergency/health first so multi-village gossip replicates survival
    content efficiently under mesh/USB bandwidth limits. Open/PD works only.
    """
    prefer = list(prefer_classes) if prefer_classes else list(PRIORITY_FEDERATION_ORDER[:3])
    prefer_set = {str(c).lower() for c in prefer}
    rank = {c: i for i, c in enumerate(PRIORITY_FEDERATION_ORDER)}
    wm = remote_gossip.get("works_manifest") or {}
    missing = local.missing_works_from(wm, max_items=max(max_items * 5, 80))

    def _sort_key(w: dict[str, Any]) -> tuple[int, int, int, str]:
        pc = str(w.get("priority_class") or w.get("class") or "general").lower()
        tier = int(w.get("civilizational_tier") or 5)
        # Prefer listed classes first, then global order, then tier
        in_prefer = 0 if pc in prefer_set else 1
        return (in_prefer, rank.get(pc, 50), tier, str(w.get("work_id") or ""))

    ordered = sorted(missing, key=_sort_key)
    return ordered[:max_items]
