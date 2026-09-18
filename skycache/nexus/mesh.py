"""Mesh fabric: peer discovery, topology, batman-adv hooks + simulation.

Physical path (Linux): batman-adv over ad-hoc / mesh Wi-Fi interfaces.
Simulation path: in-process peer graph with configurable link quality.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from skycache.nexus.identity import load_or_create_node_id
from skycache.nexus.spectrum import validate_band, validate_mesh_mode

log = logging.getLogger("skycache.nexus.mesh")


@dataclass
class MeshPeer:
    node_id: str
    address: str
    last_seen: float = 0.0
    link_quality: float = 1.0  # 0..1
    hop_count: int = 1
    battery_percent: float | None = None
    solar: bool = False
    package_count: int = 0
    role: str = "node"  # node | gateway | relay


@dataclass
class MeshLink:
    a: str
    b: str
    quality: float = 1.0
    bandwidth_mbps: float = 50.0


@dataclass
class MeshFabric:
    """Orchestrates mesh state for one node."""

    data_dir: Path
    node_id: str = ""
    enabled: bool = False
    mode: str = "sim"  # sim | batman | hybrid
    band: str = "sim"
    peers: dict[str, MeshPeer] = field(default_factory=dict)
    links: list[MeshLink] = field(default_factory=list)
    client_count: int = 0
    disaster_mode: bool = False

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        if not self.node_id:
            self.node_id = load_or_create_node_id(self.data_dir)
        validate_mesh_mode(self.mode)
        validate_band(self.band)

    @property
    def state_path(self) -> Path:
        return self.data_dir / "nexus" / "mesh-state.json"

    def ensure(self) -> None:
        (self.data_dir / "nexus").mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        self.ensure()
        validate_mesh_mode(self.mode)
        if self.mode == "sim":
            self.enabled = True
            log.info("Mesh fabric SIM mode for node %s", self.node_id)
            return
        if self.mode == "batman":
            self.enabled = self._try_batman()
            return
        # hybrid: sim discovery + optional batman
        self.enabled = True
        self._try_batman()

    def _try_batman(self) -> bool:
        batctl = shutil.which("batctl")
        if not batctl:
            log.warning("batctl not found - batman-adv not active; sim peers still work")
            return False
        try:
            subprocess.run(
                [batctl, "n"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            log.info("batman-adv present (batctl). Wire interfaces per mesh-deployment.md")
            return True
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("batman probe failed: %s", exc)
            return False

    def upsert_peer(self, peer: MeshPeer) -> None:
        peer.last_seen = time.time()
        self.peers[peer.node_id] = peer

    def remove_stale(self, max_age_sec: float = 300.0) -> int:
        now = time.time()
        dead = [k for k, p in self.peers.items() if now - p.last_seen > max_age_sec]
        for k in dead:
            del self.peers[k]
        return len(dead)

    def prefer_power_route(self) -> list[str]:
        """Order peer ids: solar + high SOC first (for gateway/mule preference)."""
        def key(p: MeshPeer) -> tuple:
            soc = p.battery_percent if p.battery_percent is not None else 50.0
            return (0 if p.solar else 1, -soc, -p.link_quality, p.hop_count)

        return [p.node_id for p in sorted(self.peers.values(), key=key)]

    def topology(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "enabled": self.enabled,
            "mode": self.mode,
            "band": self.band,
            "disaster_mode": self.disaster_mode,
            "client_count": self.client_count,
            "peers": [asdict(p) for p in self.peers.values()],
            "links": [asdict(link) for link in self.links],
            "preferred_route_order": self.prefer_power_route(),
            "legal": (
                "Mesh RF: unlicensed Wi-Fi/ISM only. No satellite uplink. "
                "Store-and-forward + community mesh - not free commercial broadband."
            ),
        }

    def save(self) -> None:
        self.ensure()
        self.state_path.write_text(
            json.dumps(self.topology(), indent=2),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.state_path.is_file():
            return
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.enabled = bool(data.get("enabled", self.enabled))
        self.mode = str(data.get("mode", self.mode))
        self.band = str(data.get("band", self.band))
        self.disaster_mode = bool(data.get("disaster_mode", False))
        self.client_count = int(data.get("client_count") or 0)
        self.peers = {}
        for raw in data.get("peers") or []:
            p = MeshPeer(**raw)
            self.peers[p.node_id] = p

    def status(self) -> dict[str, Any]:
        self.remove_stale()
        return self.topology()
