"""Mesh agent facade - delegates to Nexus MeshFabric (backward compatible)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from skycache.nexus.mesh import MeshFabric, MeshPeer

log = logging.getLogger("skycache.mesh")


class MeshAgent:
    """Compatibility wrapper around skycache.nexus.mesh.MeshFabric."""

    def __init__(
        self,
        enabled: bool = False,
        node_id: str = "skycache-local",
        data_dir: Path | str | None = None,
        mode: str = "sim",
        band: str = "sim",
    ) -> None:
        root = Path(data_dir or "data")
        self._fabric = MeshFabric(
            data_dir=root,
            node_id=node_id,
            enabled=enabled,
            mode=mode,
            band=band,
        )
        self.enabled = enabled
        self.node_id = self._fabric.node_id
        self.peers: list[MeshPeer] = []

    def start(self) -> None:
        self._fabric.start()
        self.enabled = self._fabric.enabled
        self.node_id = self._fabric.node_id
        log.info(
            "Mesh agent node=%s enabled=%s mode=%s",
            self.node_id,
            self.enabled,
            self._fabric.mode,
        )

    def stop(self) -> None:
        self._fabric.enabled = False
        log.info("Mesh agent stopped")

    def advertise_manifests(self, package_ids: list[str]) -> None:
        if not self._fabric.enabled:
            return
        log.debug(
            "Advertise %d packages from %s", len(package_ids), self._fabric.node_id
        )

    def status(self) -> dict[str, Any]:
        st = self._fabric.status()
        st["phase"] = 4
        st["product"] = "SkyCache Nexus"
        return st

    @property
    def fabric(self) -> MeshFabric:
        return self._fabric
