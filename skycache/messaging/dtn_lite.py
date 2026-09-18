"""Lightweight store-and-forward messaging (Phase 3 stub).

Not full Bundle Protocol. Local queue for:
  - Community notices (operator approved)
  - Delayed upload when a courier device or intermittent uplink appears
  - USB sneakernet export/import of the outbox
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("skycache.dtn")


@dataclass
class DelayedMessage:
    id: str
    created_at: str
    author: str
    subject: str
    body: str
    destination: str = "local-community"
    delivered: bool = False


@dataclass
class DtnLiteStore:
    path: Path
    messages: list[DelayedMessage] = field(default_factory=list)

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.messages = [DelayedMessage(**m) for m in data.get("messages", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"messages": [asdict(m) for m in self.messages]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def enqueue(self, author: str, subject: str, body: str) -> DelayedMessage:
        msg = DelayedMessage(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            author=author[:80],
            subject=subject[:200],
            body=body[:4000],
        )
        self.messages.append(msg)
        self.save()
        log.info("DTN-lite enqueued message %s", msg.id)
        return msg

    def list_pending(self) -> list[DelayedMessage]:
        return [m for m in self.messages if not m.delivered]

    def export_usb(self, dest_dir: Path) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / "skycache-outbox.json"
        pending = [asdict(m) for m in self.list_pending()]
        out.write_text(json.dumps({"messages": pending}, indent=2), encoding="utf-8")
        return out
