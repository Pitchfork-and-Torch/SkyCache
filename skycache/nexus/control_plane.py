"""Optional long-range control plane (LoRa / Meshtastic-class ISM).

Low-bandwidth only: emergency alerts, DTN control, admin pings.
Never bulk media. Simulation-friendly; no RF required.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from skycache.nexus.spectrum import validate_band

log = logging.getLogger("skycache.nexus.control_plane")


@dataclass
class ControlMessage:
    id: str
    kind: str  # alert | ping | dtn_hint | status
    priority: str  # emergency | health | control
    origin_node: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    hops: list[str] = field(default_factory=list)


class ControlPlane:
    """In-process + file-backed control messages (LoRa bridge stub)."""

    def __init__(
        self,
        data_dir: Path,
        node_id: str,
        *,
        enabled: bool = False,
        band: str = "sim",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.node_id = node_id
        self.enabled = enabled
        self.band = band
        if band != "sim":
            validate_band(band if band in ("lora_ism", "sim") else "lora_ism")
        self.messages: list[ControlMessage] = []
        self.load()

    @property
    def path(self) -> Path:
        return self.data_dir / "nexus" / "control-plane.json"

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.messages = [ControlMessage(**m) for m in data.get("messages", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "node_id": self.node_id,
                    "enabled": self.enabled,
                    "band": self.band,
                    "messages": [asdict(m) for m in self.messages[-200:]],
                    "legal": (
                        "LoRa/ISM control plane only - low bandwidth. "
                        "Not broadband. Unlicensed regional rules apply."
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def publish(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        priority: str = "control",
    ) -> ControlMessage:
        msg = ControlMessage(
            id=str(uuid.uuid4()),
            kind=kind,
            priority=priority,
            origin_node=self.node_id,
            payload=payload,
            created_at=time.time(),
            hops=[self.node_id],
        )
        self.messages.append(msg)
        self.save()
        log.info("Control plane %s kind=%s", msg.id[:8], kind)
        return msg

    def receive_sim(self, raw: dict[str, Any]) -> ControlMessage | None:
        """Import a peer control message (mesh/LoRa sim bridge)."""
        mid = raw.get("id")
        if mid and any(m.id == mid for m in self.messages):
            return None
        msg = ControlMessage(
            id=str(mid or uuid.uuid4()),
            kind=str(raw.get("kind") or "status"),
            priority=str(raw.get("priority") or "control"),
            origin_node=str(raw.get("origin_node") or "peer"),
            payload=dict(raw.get("payload") or {}),
            created_at=float(raw.get("created_at") or time.time()),
            hops=list(raw.get("hops") or []) + [self.node_id],
        )
        self.messages.append(msg)
        self.save()
        return msg

    def pending_alerts(self) -> list[dict[str, Any]]:
        return [
            asdict(m)
            for m in sorted(self.messages, key=lambda x: -x.created_at)
            if m.kind in ("alert", "emergency") or m.priority == "emergency"
        ][:20]

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "band": self.band,
            "message_count": len(self.messages),
            "recent_alerts": self.pending_alerts()[:5],
            "legal": (
                "Optional LoRa/Meshtastic-class ISM control plane. "
                "Duty-cycle/power limits vary by region. Never bulk media."
            ),
        }
