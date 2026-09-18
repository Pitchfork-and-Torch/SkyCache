"""Distributed content fabric: manifest gossip + prioritized replication.

Sim-friendly: nodes exchange package manifests and copy missing high-priority
packages from peers (filesystem copy in sim; HTTP/mesh in production).
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import PriorityClass
from skycache.nexus.dtn import BundleKind, DtnQueue
from skycache.nexus.identity import content_fingerprint
from skycache.nexus.mesh import MeshFabric
from skycache.models import CLASS_WEIGHTS
from skycache.policy.prioritizer import compute_score

log = logging.getLogger("skycache.nexus.fabric")


@dataclass
class ManifestEntry:
    package_id: str
    priority_class: str
    size_bytes: int
    score: float
    fingerprint: str
    node_id: str
    title_en: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "priority_class": self.priority_class,
            "size_bytes": self.size_bytes,
            "score": self.score,
            "fingerprint": self.fingerprint,
            "node_id": self.node_id,
            "title_en": self.title_en,
        }


class ContentFabric:
    def __init__(
        self,
        *,
        node_id: str,
        catalog: Catalog,
        content: ContentManager,
        mesh: MeshFabric,
        dtn: DtnQueue,
        content_dir: Path,
        skybrary: Any | None = None,
    ) -> None:
        self.node_id = node_id
        self.catalog = catalog
        self.content = content
        self.mesh = mesh
        self.dtn = dtn
        self.content_dir = Path(content_dir)
        # Optional SkybraryCatalog for works-manifest federation (Wave 3.B6)
        self.skybrary = skybrary

    def attach_skybrary(self, sky: Any) -> None:
        """Attach or replace Skybrary catalog for works_manifest gossip."""
        self.skybrary = sky

    def local_manifest(self) -> list[ManifestEntry]:
        out: list[ManifestEntry] = []
        for rec in self.catalog.list_packages(limit=10_000):
            p = rec.package
            fp = content_fingerprint(
                p.id, p.size_bytes, p.received_at.isoformat()
            )
            out.append(
                ManifestEntry(
                    package_id=p.id,
                    priority_class=p.priority_class.value,
                    size_bytes=p.size_bytes,
                    score=rec.score or compute_score(p),
                    fingerprint=fp,
                    node_id=self.node_id,
                    title_en=p.title_for("en"),
                )
            )
        return out

    def works_manifest(
        self,
        *,
        max_works: int = 10_000,
        compact: bool | None = None,
        max_tier: int | None = None,
    ) -> dict[str, Any] | None:
        """Skybrary works metadata for catalog federation (None if no sky attached).

        compact auto-enables when catalog is large (>200 works) unless overridden.
        """
        if self.skybrary is None:
            return None
        count = 0
        try:
            count = int(self.skybrary.count())
        except Exception:  # noqa: BLE001
            count = 0
        use_compact = bool(compact) if compact is not None else count > 200
        # Cap wire size for large village catalogs (Pi RAM / mesh fairness)
        cap = max_works
        if use_compact:
            cap = min(max_works, 2_000)
        return self.skybrary.works_manifest(
            node_id=self.node_id,
            max_works=cap,
            compact=use_compact,
            max_tier=max_tier,
        )

    def missing_works_from(
        self,
        remote_works: list[dict[str, Any]] | dict[str, Any],
        *,
        max_items: int = 50,
    ) -> list[dict[str, Any]]:
        """Works present in remote works_manifest but not in local skybrary."""
        if self.skybrary is None:
            return []
        if isinstance(remote_works, dict):
            remote_list = list(remote_works.get("works") or [])
        else:
            remote_list = list(remote_works or [])
        local_ids = {w["work_id"] for w in self.skybrary.list_works(limit=50_000)}
        missing = [w for w in remote_list if w.get("work_id") not in local_ids]
        # Prefer lower civilizational_tier (foundational first)
        missing.sort(
            key=lambda w: (
                int(w.get("civilizational_tier") or 5),
                str(w.get("work_id") or ""),
            )
        )
        return missing[: max(1, int(max_items))]

    def gossip_payload(
        self,
        *,
        works_compact: bool | None = None,
        works_max: int = 10_000,
        works_max_tier: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "node_id": self.node_id,
            "ts": time.time(),
            "disaster_mode": self.mesh.disaster_mode,
            "manifest": [m.to_dict() for m in self.local_manifest()],
            "legal": "open/FTA content replication only",
        }
        wm = self.works_manifest(
            max_works=works_max,
            compact=works_compact,
            max_tier=works_max_tier,
        )
        if wm is not None:
            # Full for small catalogs; compact auto for large (bandwidth-aware)
            payload["works_manifest"] = wm
        return payload

    def missing_from(
        self,
        remote_manifest: list[dict[str, Any]],
        *,
        max_items: int = 20,
    ) -> list[dict[str, Any]]:
        local_ids = {m.package_id for m in self.local_manifest()}
        candidates = [m for m in remote_manifest if m.get("package_id") not in local_ids]
        # Prefer emergency/health/education and high score
        def rank(m: dict[str, Any]) -> tuple:
            pc = str(m.get("priority_class") or "general")
            try:
                pclass = PriorityClass(pc)
            except ValueError:
                pclass = PriorityClass.GENERAL
            weight = CLASS_WEIGHTS.get(pclass, 100.0)
            return (-weight, -float(m.get("score") or 0))

        candidates.sort(key=rank)
        if self.mesh.disaster_mode:
            # Emergency flood: only emergency/health first
            em = [
                m
                for m in candidates
                if m.get("priority_class") in ("emergency", "health")
            ]
            if em:
                candidates = em + [m for m in candidates if m not in em]
        return candidates[:max_items]

    def replicate_from_path(
        self,
        package_dir: Path,
        *,
        source_node: str,
    ) -> str | None:
        """Ingest a package directory received from a peer or mule."""
        package_dir = Path(package_dir)
        if not (package_dir / "manifest.json").is_file():
            return None
        pkg = self.content.ingest_package_dir(package_dir)
        self.dtn.enqueue(
            kind=BundleKind.CONTROL,
            priority_class=pkg.priority_class.value,
            origin_node=source_node,
            payload={"event": "replicated", "package_id": pkg.id},
        )
        log.info("Fabric replicated %s from %s", pkg.id, source_node)
        return pkg.id

    def export_package_for_peer(self, package_id: str, dest_dir: Path) -> Path | None:
        rec = self.catalog.get(package_id)
        if not rec or not rec.path:
            return None
        src = Path(rec.path)
        if not src.is_dir():
            return None
        dest = Path(dest_dir) / package_id
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return dest

    def sync_with_peer_manifest(
        self,
        remote: dict[str, Any],
        peer_content_root: Path | None = None,
    ) -> dict[str, Any]:
        """
        Compare remote gossip manifest; copy missing packages if peer_content_root set.
        In production, peer_content_root would be NFS/HTTP cache; in sim it is another node's content dir.
        Also merges works_manifest metadata when skybrary is attached (Wave 3.B6).
        """
        remote_node = str(remote.get("node_id") or "peer")
        manifest = list(remote.get("manifest") or [])
        want = self.missing_from(manifest)
        pulled: list[str] = []
        queued: list[str] = []

        for m in want:
            pid = str(m["package_id"])
            if peer_content_root and (Path(peer_content_root) / pid).is_dir():
                try:
                    got = self.replicate_from_path(
                        Path(peer_content_root) / pid, source_node=remote_node
                    )
                    if got:
                        pulled.append(got)
                        continue
                except Exception as exc:  # noqa: BLE001
                    log.warning("replicate failed %s: %s", pid, exc)
            # Queue DTN request for gateway/mule
            b = self.dtn.enqueue(
                kind=BundleKind.REQUEST,
                priority_class=str(m.get("priority_class") or "education"),
                origin_node=self.node_id,
                payload={
                    "package_id": pid,
                    "from_node": remote_node,
                    "fingerprint": m.get("fingerprint"),
                },
                size_bytes=int(m.get("size_bytes") or 0),
            )
            queued.append(b.id)

        works_imported = 0
        works_missing = 0
        remote_wm = remote.get("works_manifest")
        if remote_wm and self.skybrary is not None:
            try:
                rep = self.skybrary.import_works_manifest(remote_wm)
                works_imported = int(rep.get("imported") or 0)
                works_missing = len(self.missing_works_from(remote_wm))
            except Exception as exc:  # noqa: BLE001
                log.warning("works_manifest import failed from %s: %s", remote_node, exc)

        return {
            "remote_node": remote_node,
            "pulled": pulled,
            "queued_requests": queued,
            "remote_count": len(manifest),
            "local_count": len(self.local_manifest()),
            "works_imported": works_imported,
            "works_still_missing": works_missing,
        }

    def status(self) -> dict[str, Any]:
        man = self.local_manifest()
        by: dict[str, int] = {}
        for m in man:
            by[m.priority_class] = by.get(m.priority_class, 0) + 1
        return {
            "node_id": self.node_id,
            "packages": len(man),
            "by_class": by,
            "disaster_mode": self.mesh.disaster_mode,
        }
