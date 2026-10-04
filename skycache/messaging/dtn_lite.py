"""Lightweight store-and-forward community notices.

Local outbox for:
  - Community notices (operator approved)
  - Delayed upload when a courier device or intermittent uplink appears
  - USB sneakernet export/import of the outbox

Not full Bundle Protocol. Integrity is SHA-256 of author/subject/body.
Bridges into Nexus DTN as MESSAGE bundles when asked.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("skycache.dtn")

DEFAULT_TTL_SEC = 7 * 24 * 3600
_MSG_FIELDS: set[str] = set()


def notice_digest(author: str, subject: str, body: str) -> str:
    blob = f"{author}\n{subject}\n{body}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class DelayedMessage:
    id: str
    created_at: str
    author: str
    subject: str
    body: str
    destination: str = "local-community"
    delivered: bool = False
    payload_sha256: str = ""
    ttl_sec: int = DEFAULT_TTL_SEC
    hops: list[str] = field(default_factory=list)


_MSG_FIELDS = {f.name for f in fields(DelayedMessage)}


def message_from_dict(raw: dict[str, Any]) -> DelayedMessage:
    filtered = {k: v for k, v in (raw or {}).items() if k in _MSG_FIELDS}
    hops = filtered.get("hops")
    if hops is None:
        filtered["hops"] = []
    elif not isinstance(hops, list):
        filtered["hops"] = list(hops)
    msg = DelayedMessage(**filtered)
    if not msg.payload_sha256:
        msg.payload_sha256 = notice_digest(msg.author, msg.subject, msg.body)
    return msg


@dataclass
class DtnLiteStore:
    path: Path
    messages: list[DelayedMessage] = field(default_factory=list)

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.messages = [message_from_dict(m) for m in data.get("messages", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"format": "skycache-dtn-lite-v2", "messages": [asdict(m) for m in self.messages]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def enqueue(
        self,
        author: str,
        subject: str,
        body: str,
        *,
        destination: str = "local-community",
        ttl_sec: int = DEFAULT_TTL_SEC,
        origin_node: str = "",
    ) -> DelayedMessage:
        author = author[:80]
        subject = subject[:200]
        body = body[:4000]
        hops = [origin_node] if origin_node else []
        msg = DelayedMessage(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            author=author,
            subject=subject,
            body=body,
            destination=destination or "local-community",
            payload_sha256=notice_digest(author, subject, body),
            ttl_sec=int(ttl_sec or DEFAULT_TTL_SEC),
            hops=hops,
        )
        self.messages.append(msg)
        self.save()
        log.info("DTN-lite enqueued message %s", msg.id)
        return msg

    def list_pending(self) -> list[DelayedMessage]:
        return [m for m in self.messages if not m.delivered]

    def mark_delivered(self, message_id: str) -> bool:
        for m in self.messages:
            if m.id == message_id:
                m.delivered = True
                self.save()
                return True
        return False

    def export_usb(self, dest_dir: Path) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / "skycache-outbox.json"
        pending = [asdict(m) for m in self.list_pending()]
        out.write_text(
            json.dumps(
                {
                    "format": "skycache-dtn-lite-v2",
                    "messages": pending,
                    "legal": (
                        "Community notice sneakernet. Open/local notices only. "
                        "Not commercial broadband."
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return out

    def import_usb(self, path: Path, *, local_node: str = "") -> dict[str, Any]:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        imported = 0
        skipped = 0
        rejected: list[dict[str, Any]] = []
        known = {m.id for m in self.messages}
        for raw in data.get("messages") or []:
            msg = message_from_dict(raw)
            expect = notice_digest(msg.author, msg.subject, msg.body)
            if msg.payload_sha256 and msg.payload_sha256 != expect:
                rejected.append({"id": msg.id, "reason": "payload_sha256_mismatch"})
                continue
            if msg.id in known:
                skipped += 1
                continue
            if local_node and local_node not in msg.hops:
                msg.hops = list(msg.hops) + [local_node]
            if not msg.payload_sha256:
                msg.payload_sha256 = expect
            self.messages.append(msg)
            known.add(msg.id)
            imported += 1
        if imported:
            self.save()
        return {
            "ok": not rejected,
            "imported": imported,
            "skipped": skipped,
            "rejected": rejected,
            "path": str(path),
        }

    def bridge_to_nexus(
        self,
        nexus_queue: Any,
        *,
        origin_node: str,
        message: DelayedMessage | None = None,
    ) -> list[str]:
        """Copy pending (or one) community notices into the Nexus DTN queue."""
        from skycache.nexus.dtn import BundleKind

        ids: list[str] = []
        batch = [message] if message is not None else self.list_pending()
        for m in batch:
            b = nexus_queue.enqueue(
                kind=BundleKind.MESSAGE,
                priority_class="message",
                origin_node=origin_node,
                payload={
                    "notice_id": m.id,
                    "author": m.author,
                    "subject": m.subject,
                    "body": m.body,
                    "lite_sha256": m.payload_sha256,
                },
                destination=m.destination if m.destination != "local-community" else "*",
                ttl_sec=int(m.ttl_sec or DEFAULT_TTL_SEC),
            )
            ids.append(b.id)
        return ids
