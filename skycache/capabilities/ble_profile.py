"""SkyCache phone-handoff BLE GATT profile (software complete, radio residual).

Physical Bluetooth radios stay operator-owned. This module ships the wire
profile, ATT-style framing, and a deterministic sim exchange so a node can
prove the handoff mule without claiming a live BLE stack.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Documented SkyCache handoff service (not Bluetooth SIG assigned).
SERVICE_UUID = "a1c5c4ce-5c11-4e0a-9b01-5c11c4ce0001"
CHAR_JOIN_UUID = "a1c5c4ce-5c11-4e0a-9b01-5c11c4ce0002"
CHAR_MULE_META_UUID = "a1c5c4ce-5c11-4e0a-9b01-5c11c4ce0003"
CHAR_CHUNK_UUID = "a1c5c4ce-5c11-4e0a-9b01-5c11c4ce0004"
ATT_MTU = 20
PROFILE_SCHEMA = "skycache.handoff.ble_profile.v1"
HONEST = (
    "BLE profile is a local file-bridge contract plus a simulated ATT exchange. "
    "Not a live Bluetooth stack. Not commercial tethering. Not free broadband."
)


def ble_profile() -> dict[str, Any]:
    return {
        "schema": PROFILE_SCHEMA,
        "service_uuid": SERVICE_UUID,
        "characteristics": {
            "join": CHAR_JOIN_UUID,
            "mule_meta": CHAR_MULE_META_UUID,
            "chunk": CHAR_CHUNK_UUID,
        },
        "att_mtu": ATT_MTU,
        "transport": "sim",
        "live_radio": False,
        "banner": HONEST,
    }


def _frames_for(payload: bytes, *, char_uuid: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    total = max(1, (len(payload) + ATT_MTU - 1) // ATT_MTU)
    for i in range(total):
        chunk = payload[i * ATT_MTU : (i + 1) * ATT_MTU]
        frames.append(
            {
                "seq": i,
                "of": total,
                "char": char_uuid,
                "hex": chunk.hex(),
            }
        )
    return frames


def encode_att_frames(obj: dict[str, Any], *, char_uuid: str = CHAR_MULE_META_UUID) -> list[dict[str, Any]]:
    raw = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _frames_for(raw, char_uuid=char_uuid)


def decode_att_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(frames, key=lambda f: int(f.get("seq") or 0))
    raw = b"".join(bytes.fromhex(str(f.get("hex") or "")) for f in ordered)
    return json.loads(raw.decode("utf-8"))


def simulate_ble_exchange(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Round-trip a mule meta payload through simulated ATT frames."""
    body = dict(payload or {})
    body.setdefault("format", "skycache-handoff-v1")
    body.setdefault("legal", HONEST)
    frames = encode_att_frames(body)
    restored = decode_att_frames(frames)
    digest = hashlib.sha256(
        json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    ok = restored == body and len(frames) >= 1
    return {
        "schema": "skycache.handoff.ble_sim.v1",
        "ok": ok,
        "profile": ble_profile(),
        "frame_count": len(frames),
        "sha256": digest,
        "restored": restored,
        "live_radio": False,
        "banner": HONEST,
    }
