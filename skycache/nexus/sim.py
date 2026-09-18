"""Multi-node Nexus simulation (no RF hardware).

Creates N virtual nodes with isolated data dirs, runs mesh gossip,
content replication, DTN mule transfer, and opportunistic gateway pulls.
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import PriorityClass
from skycache.nexus.dtn import BundleKind, DtnQueue
from skycache.nexus.fabric import ContentFabric
from skycache.nexus.gateway import GatewayManager
from skycache.nexus.mesh import MeshFabric, MeshLink, MeshPeer

log = logging.getLogger("skycache.nexus.sim")


@dataclass
class SimNode:
    name: str
    root: Path
    settings: Settings
    catalog: Catalog
    content: ContentManager
    mesh: MeshFabric
    dtn: DtnQueue
    fabric: ContentFabric
    gateway: GatewayManager


@dataclass
class NexusSimulator:
    base_dir: Path | None = None
    node_count: int = 3
    nodes: list[SimNode] = field(default_factory=list)
    _tmp: tempfile.TemporaryDirectory[str] | None = None

    def setup(self, load_samples_on: int = 1) -> None:
        """Create node_count isolated nodes. load_samples_on = first N get sample packs."""
        if self.base_dir is None:
            self._tmp = tempfile.TemporaryDirectory(prefix="skycache-nexus-")
            self.base_dir = Path(self._tmp.name)
        else:
            self.base_dir = Path(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)

        self.nodes = []
        for i in range(self.node_count):
            name = f"node-{i + 1}"
            root = self.base_dir / name
            settings = Settings(data_dir=root / "data", sim_mode=True)
            settings.ensure_dirs()
            catalog = Catalog(settings.db_path)
            content = ContentManager(settings, catalog)
            if i < load_samples_on:
                content.load_samples(samples_dir())
            mesh = MeshFabric(
                data_dir=settings.data_dir,
                node_id=name,
                enabled=True,
                mode="sim",
                band="sim",
            )
            mesh.start()
            dtn = DtnQueue(settings.data_dir / "nexus" / "dtn-queue.json")
            fabric = ContentFabric(
                node_id=name,
                catalog=catalog,
                content=content,
                mesh=mesh,
                dtn=dtn,
                content_dir=settings.content_dir,
            )
            gateway = GatewayManager(dtn=dtn, node_id=name, sim_uplink=(i == 0))
            # Power diversity
            mesh.upsert_peer(
                MeshPeer(
                    node_id=name,
                    address=f"10.42.0.{i + 1}",
                    battery_percent=90.0 - i * 15,
                    solar=(i % 2 == 0),
                    package_count=catalog.count(),
                )
            )
            self.nodes.append(
                SimNode(
                    name=name,
                    root=root,
                    settings=settings,
                    catalog=catalog,
                    content=content,
                    mesh=mesh,
                    dtn=dtn,
                    fabric=fabric,
                    gateway=gateway,
                )
            )

        # Full mesh links
        for a in self.nodes:
            for b in self.nodes:
                if a.name == b.name:
                    continue
                a.mesh.upsert_peer(
                    MeshPeer(
                        node_id=b.name,
                        address=f"sim://{b.name}",
                        link_quality=0.9,
                        hop_count=1,
                        battery_percent=80.0,
                        solar=True,
                        package_count=b.catalog.count(),
                    )
                )
                a.mesh.links.append(MeshLink(a=a.name, b=b.name, quality=0.9))

    def run_round(self) -> dict[str, Any]:
        """One gossip + replicate + gateway schedule round."""
        if not self.nodes:
            self.setup()
        reports: list[dict[str, Any]] = []

        # Node 0 floods an emergency request when disaster mode
        for n in self.nodes:
            gossip = n.fabric.gossip_payload()
            for other in self.nodes:
                if other.name == n.name:
                    continue
                rep = other.fabric.sync_with_peer_manifest(
                    gossip,
                    peer_content_root=n.settings.content_dir,
                )
                reports.append({"from": n.name, "to": other.name, **rep})

        gw_results = []
        for n in self.nodes:
            # Enqueue a sample request on non-gateway nodes
            if not n.gateway.sim_uplink and n.catalog.count() < 3:
                n.gateway.request_package(
                    "health-ors-001", PriorityClass.HEALTH.value
                )
            gw_results.append({"node": n.name, "pulls": n.gateway.schedule_pulls()})

        # USB mule: export from node-1, import to node-N
        mule_path = None
        if len(self.nodes) >= 2:
            mule_dir = self.base_dir / "mule"
            mule_path = str(self.nodes[0].dtn.export_mule(mule_dir))
            self.nodes[-1].dtn.import_mule(Path(mule_path), self.nodes[-1].name)

        return {
            "nodes": [
                {
                    "id": n.name,
                    "packages": n.catalog.count(),
                    "mesh_peers": len(n.mesh.peers),
                    "dtn": n.dtn.stats(),
                    "gateway": n.gateway.snapshot(),
                    "fabric": n.fabric.status(),
                }
                for n in self.nodes
            ],
            "sync_reports": reports,
            "gateway_results": gw_results,
            "mule": mule_path,
            "legal": (
                "Simulation only. Physical deploy: unlicensed Wi-Fi mesh + receive-only satellite. "
                "Not free commercial broadband."
            ),
        }

    def enable_disaster_mode(self) -> None:
        for n in self.nodes:
            n.mesh.disaster_mode = True
            # Inject emergency bundle
            n.dtn.enqueue(
                kind=BundleKind.MESSAGE,
                priority_class=PriorityClass.EMERGENCY.value,
                origin_node=n.name,
                payload={"alert": "disaster_mode", "text": "Coordinate via mesh"},
            )

    def teardown(self) -> None:
        for n in self.nodes:
            try:
                n.catalog.close()
            except Exception:  # noqa: BLE001
                pass
        self.nodes.clear()
        if self._tmp:
            try:
                self._tmp.cleanup()
            except (PermissionError, OSError):
                # Windows may briefly lock SQLite WAL files; ignore best-effort
                pass
            self._tmp = None

    def summary_json(self) -> str:
        return json.dumps(self.run_round(), indent=2)
