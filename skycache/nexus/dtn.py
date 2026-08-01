"""Delay-tolerant networking queues for Nexus.

Lightweight bundle store (not full Bundle Protocol RFC 9171) with:
  - priority classes matching content prioritizer
  - content package transfer, update requests, community messages
  - USB / file mule import-export
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from skycache.models import PriorityClass

log = logging.getLogger("skycache.nexus.dtn")


class BundleKind(str, Enum):
    CONTENT = "content"  # package payload or manifest
    REQUEST = "request"  # ask mesh/gateway for a package
    MESSAGE = "message"  # community notice
    CONTROL = "control"  # mesh/admin control


# Lower number = higher urgency for fair-share scheduler
TRAFFIC_CLASS_RANK: dict[str, int] = {
    PriorityClass.EMERGENCY.value: 0,
    PriorityClass.HEALTH.value: 1,
    PriorityClass.EDUCATION.value: 2,
    PriorityClass.AGRICULTURE.value: 3,
    PriorityClass.MAPS.value: 3,
    PriorityClass.WEATHER.value: 4,
    PriorityClass.GENERAL.value: 5,
    PriorityClass.TELEMETRY_RAW.value: 6,
    "control": 0,
    "message": 4,
}


@dataclass
class Bundle:
    id: str
    kind: str
    priority_class: str
    created_at: float
    origin_node: str
    destination: str = "*"  # * = flood / any
    payload: dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0
    delivered: bool = False
    hops: list[str] = field(default_factory=list)

    @property
    def rank(self) -> int:
        return TRAFFIC_CLASS_RANK.get(self.priority_class, 5)


class DtnQueue:
    """Persistent priority queue of bundles."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.bundles: list[Bundle] = []
        self.load()

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.bundles = [Bundle(**b) for b in data.get("bundles", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"bundles": [asdict(b) for b in self.bundles]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def enqueue(
        self,
        *,
        kind: BundleKind | str,
        priority_class: str,
        origin_node: str,
        payload: dict[str, Any],
        destination: str = "*",
        size_bytes: int = 0,
    ) -> Bundle:
        b = Bundle(
            id=str(uuid.uuid4()),
            kind=kind.value if isinstance(kind, BundleKind) else str(kind),
            priority_class=priority_class,
            created_at=time.time(),
            origin_node=origin_node,
            destination=destination,
            payload=payload,
            size_bytes=size_bytes or int(payload.get("size_bytes") or 0),
        )
        self.bundles.append(b)
        self.save()
        log.info("DTN enqueued %s kind=%s class=%s", b.id[:8], b.kind, b.priority_class)
        return b

    def pending(self, include_delivered: bool = False) -> list[Bundle]:
        items = self.bundles if include_delivered else [b for b in self.bundles if not b.delivered]
        return sorted(items, key=lambda b: (b.rank, b.created_at))

    def mark_delivered(self, bundle_id: str) -> bool:
        for b in self.bundles:
            if b.id == bundle_id:
                b.delivered = True
                self.save()
                return True
        return False

    def pop_next(self, max_bytes: int | None = None) -> Bundle | None:
        for b in self.pending():
            if max_bytes is not None and b.size_bytes > max_bytes:
                continue
            return b
        return None

    def export_mule(self, dest_dir: Path, limit: int = 50) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / f"skycache-mule-{int(time.time())}.json"
        pending = [asdict(b) for b in self.pending()[:limit]]
        out.write_text(
            json.dumps({"format": "skycache-dtn-v1", "bundles": pending}, indent=2),
            encoding="utf-8",
        )
        return out

    def import_mule(self, path: Path, local_node: str) -> int:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        n = 0
        for raw in data.get("bundles") or []:
            bid = raw.get("id")
            if any(b.id == bid for b in self.bundles):
                continue
            b = Bundle(**raw)
            if local_node not in b.hops:
                b.hops = list(b.hops) + [local_node]
            self.bundles.append(b)
            n += 1
        if n:
            self.save()
        return n

    def stats(self) -> dict[str, Any]:
        pend = self.pending()
        by_class: dict[str, int] = {}
        for b in pend:
            by_class[b.priority_class] = by_class.get(b.priority_class, 0) + 1
        return {
            "pending": len(pend),
            "total": len(self.bundles),
            "by_class": by_class,
            "next": asdict(pend[0]) if pend else None,
        }
