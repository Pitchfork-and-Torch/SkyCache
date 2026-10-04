"""Delay-tolerant networking queues for Nexus.

Lightweight bundle store (not full Bundle Protocol RFC 9171) with:
  - priority classes matching content prioritizer
  - content package transfer, update requests, community messages
  - payload SHA-256 integrity
  - TTL / hop-limit / custody
  - USB / file mule import-export with verify
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any

from skycache.models import PriorityClass

log = logging.getLogger("skycache.nexus.dtn")

DTN_FORMAT_V1 = "skycache-dtn-v1"
DTN_FORMAT_V2 = "skycache-dtn-v2"
DEFAULT_TTL_SEC = 7 * 24 * 3600
DEFAULT_HOP_LIMIT = 8
LEGAL_MULE = (
    "Store-and-forward mule. Open/FTA notices and package requests only. "
    "Not commercial broadband or satellite uplink."
)


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


def payload_digest(payload: dict[str, Any] | None) -> str:
    blob = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
    payload_sha256: str = ""
    ttl_sec: int = DEFAULT_TTL_SEC
    hop_limit: int = DEFAULT_HOP_LIMIT
    custody_node: str = ""
    status: str = "pending"  # pending | forwarded | delivered | expired | rejected
    reject_reason: str = ""

    @property
    def rank(self) -> int:
        return TRAFFIC_CLASS_RANK.get(self.priority_class, 5)

    def is_expired(self, now: float | None = None) -> bool:
        t = now if now is not None else time.time()
        ttl = int(self.ttl_sec or DEFAULT_TTL_SEC)
        return (t - float(self.created_at or 0)) > ttl

    def hop_count(self) -> int:
        return len(self.hops or [])

    def verify(self, *, now: float | None = None, require_hash: bool = False) -> dict[str, Any]:
        reasons: list[str] = []
        expected = payload_digest(self.payload if isinstance(self.payload, dict) else {})
        if self.payload_sha256:
            if self.payload_sha256 != expected:
                reasons.append("payload_sha256_mismatch")
        elif require_hash:
            reasons.append("payload_sha256_missing")
        limit = int(self.hop_limit or DEFAULT_HOP_LIMIT)
        if self.hop_count() > limit:
            reasons.append("hop_limit_exceeded")
        if self.is_expired(now):
            reasons.append("expired")
        if not self.id:
            reasons.append("missing_id")
        return {
            "ok": not reasons,
            "reasons": reasons,
            "expected_sha256": expected,
            "id": self.id,
        }


_BUNDLE_FIELD_NAMES = {f.name for f in fields(Bundle)}


def bundle_from_dict(raw: dict[str, Any], *, backfill_hash: bool = True) -> Bundle:
    """Load a bundle, ignoring unknown keys so v1 mule files still import."""
    filtered = {k: v for k, v in (raw or {}).items() if k in _BUNDLE_FIELD_NAMES}
    hops = filtered.get("hops")
    if hops is None:
        filtered["hops"] = []
    elif not isinstance(hops, list):
        filtered["hops"] = list(hops)
    payload = filtered.get("payload")
    if not isinstance(payload, dict):
        filtered["payload"] = {}
    b = Bundle(**filtered)
    if backfill_hash and not b.payload_sha256:
        b.payload_sha256 = payload_digest(b.payload)
    if not b.custody_node:
        b.custody_node = b.origin_node
    if b.delivered and b.status == "pending":
        b.status = "delivered"
    return b


class DtnQueue:
    """Persistent priority queue of bundles."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.bundles: list[Bundle] = []
        self.load()

    def load(self) -> None:
        """Load queue from disk. Corrupt or non-object JSON starts empty.

        Nexus constructs DtnQueue on boot. A truncated or hand-edited queue
        must not take down the node with JSONDecodeError / TypeError.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("DTN queue unreadable at %s: %s; starting empty", self.path, exc)
            self.bundles = []
            return
        if not isinstance(data, dict):
            log.warning("DTN queue root is not an object at %s; starting empty", self.path)
            self.bundles = []
            return
        bundles: list[Bundle] = []
        for raw in data.get("bundles") or []:
            if not isinstance(raw, dict):
                log.warning("Skipping non-object DTN bundle in %s", self.path)
                continue
            try:
                bundles.append(bundle_from_dict(raw))
            except TypeError as exc:
                log.warning("Skipping corrupt DTN bundle in %s: %s", self.path, exc)
        self.bundles = bundles

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": DTN_FORMAT_V2,
            "bundles": [asdict(b) for b in self.bundles],
        }
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
        ttl_sec: int = DEFAULT_TTL_SEC,
        hop_limit: int = DEFAULT_HOP_LIMIT,
    ) -> Bundle:
        payload = dict(payload or {})
        digest = payload_digest(payload)
        b = Bundle(
            id=str(uuid.uuid4()),
            kind=kind.value if isinstance(kind, BundleKind) else str(kind),
            priority_class=priority_class,
            created_at=time.time(),
            origin_node=origin_node,
            destination=destination or "*",
            payload=payload,
            size_bytes=size_bytes or int(payload.get("size_bytes") or 0),
            hops=[origin_node],
            payload_sha256=digest,
            ttl_sec=int(ttl_sec or DEFAULT_TTL_SEC),
            hop_limit=int(hop_limit or DEFAULT_HOP_LIMIT),
            custody_node=origin_node,
            status="pending",
        )
        self.bundles.append(b)
        self.save()
        log.info("DTN enqueued %s kind=%s class=%s", b.id[:8], b.kind, b.priority_class)
        return b

    def pending(self, include_delivered: bool = False) -> list[Bundle]:
        now = time.time()
        if include_delivered:
            items = list(self.bundles)
        else:
            items = [
                b
                for b in self.bundles
                if (not b.delivered)
                and b.status in ("pending", "in_custody", "")
                and not b.is_expired(now)
            ]
        return sorted(items, key=lambda b: (b.rank, b.created_at))

    def mark_delivered(self, bundle_id: str) -> bool:
        for b in self.bundles:
            if b.id == bundle_id:
                b.delivered = True
                b.status = "delivered"
                self.save()
                return True
        return False

    def mark_status(self, bundle_id: str, status: str, *, reason: str = "") -> bool:
        for b in self.bundles:
            if b.id == bundle_id:
                b.status = status
                if reason:
                    b.reject_reason = reason
                if status in ("delivered", "forwarded", "expired", "rejected"):
                    b.delivered = True
                self.save()
                return True
        return False

    def accept_custody(self, bundle_id: str, node_id: str) -> bool:
        for b in self.bundles:
            if b.id == bundle_id:
                b.custody_node = node_id
                if node_id not in b.hops:
                    b.hops = list(b.hops) + [node_id]
                if b.status == "pending":
                    b.status = "in_custody"
                self.save()
                return True
        return False

    def expire_stale(self, now: float | None = None) -> int:
        t = now if now is not None else time.time()
        n = 0
        for b in self.bundles:
            if b.status in ("expired", "rejected", "delivered"):
                continue
            if b.is_expired(t):
                b.status = "expired"
                b.delivered = True
                b.reject_reason = "expired"
                n += 1
        if n:
            self.save()
        return n

    def pop_next(self, max_bytes: int | None = None) -> Bundle | None:
        self.expire_stale()
        for b in self.pending():
            if max_bytes is not None and b.size_bytes > max_bytes:
                continue
            return b
        return None

    def has_id(self, bundle_id: str) -> bool:
        return any(b.id == bundle_id for b in self.bundles)

    def export_mule(
        self,
        dest_dir: Path,
        limit: int = 50,
        *,
        exporter_node: str = "",
    ) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        self.expire_stale()
        pending = [asdict(b) for b in self.pending()[:limit]]
        out = dest_dir / f"skycache-mule-{int(time.time())}.json"
        body = {
            "format": DTN_FORMAT_V2,
            "exporter_node": exporter_node,
            "exported_at": time.time(),
            "legal": LEGAL_MULE,
            "bundles": pending,
        }
        out.write_text(json.dumps(body, indent=2), encoding="utf-8")
        return out

    def import_mule(self, path: Path, local_node: str) -> int:
        report = self.import_mule_report(path, local_node)
        return int(report.get("imported") or 0)

    def import_mule_report(self, path: Path, local_node: str) -> dict[str, Any]:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        fmt = str(data.get("format") or DTN_FORMAT_V1)
        strict = fmt == DTN_FORMAT_V2
        now = time.time()
        imported = 0
        skipped = 0
        rejected: list[dict[str, Any]] = []
        for raw in data.get("bundles") or []:
            bid = str(raw.get("id") or "")
            if bid and self.has_id(bid):
                skipped += 1
                continue
            b = bundle_from_dict(raw, backfill_hash=not strict)
            check = b.verify(now=now, require_hash=strict)
            dest = b.destination or "*"
            loop = local_node in (b.hops or []) and dest not in (local_node, "*")
            if loop:
                check = {
                    "ok": False,
                    "reasons": list(check.get("reasons") or []) + ["hop_loop"],
                    "expected_sha256": check.get("expected_sha256"),
                    "id": b.id,
                }
            if not check["ok"]:
                rejected.append({"id": b.id, "reasons": check["reasons"]})
                continue
            if local_node not in b.hops:
                b.hops = list(b.hops) + [local_node]
            b.custody_node = local_node
            if dest == local_node:
                b.status = "delivered"
                b.delivered = True
            else:
                b.status = "pending"
                b.delivered = False
            self.bundles.append(b)
            imported += 1
        if imported:
            self.save()
        return {
            "ok": not rejected,
            "format": fmt,
            "imported": imported,
            "skipped": skipped,
            "rejected": rejected,
            "path": str(path),
        }

    def stats(self) -> dict[str, Any]:
        self.expire_stale()
        pend = self.pending()
        by_class: dict[str, int] = {}
        for b in pend:
            by_class[b.priority_class] = by_class.get(b.priority_class, 0) + 1
        by_status: dict[str, int] = {}
        for b in self.bundles:
            st = b.status or ("delivered" if b.delivered else "pending")
            by_status[st] = by_status.get(st, 0) + 1
        nxt = pend[0] if pend else None
        next_row = None
        if nxt:
            next_row = {
                "id": nxt.id,
                "kind": nxt.kind,
                "priority_class": nxt.priority_class,
                "destination": nxt.destination,
                "custody_node": nxt.custody_node,
                "hops": list(nxt.hops),
                "size_bytes": nxt.size_bytes,
            }
        return {
            "pending": len(pend),
            "total": len(self.bundles),
            "by_class": by_class,
            "by_status": by_status,
            "next": next_row,
            "format": DTN_FORMAT_V2,
        }


def verify_mule_file(path: Path, *, now: float | None = None) -> dict[str, Any]:
    """Integrity check a mule JSON without importing it."""
    path = Path(path)
    t = now if now is not None else time.time()
    if not path.is_file():
        return {"ok": False, "error": "mule file not found", "path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}
    fmt = str(data.get("format") or DTN_FORMAT_V1)
    strict = fmt == DTN_FORMAT_V2
    bundles = list(data.get("bundles") or [])
    checks: list[dict[str, Any]] = []
    bad = 0
    for raw in bundles:
        b = bundle_from_dict(raw, backfill_hash=not strict)
        row = b.verify(now=t, require_hash=strict)
        checks.append(row)
        if not row["ok"]:
            bad += 1
    return {
        "ok": bad == 0,
        "format": fmt,
        "path": str(path),
        "bundle_count": len(bundles),
        "failed": bad,
        "legal": data.get("legal") or LEGAL_MULE,
        "checks": checks[:50],
    }
