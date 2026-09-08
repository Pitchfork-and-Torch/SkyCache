"""Operator-selectable legal RF / distribution modes (fail-closed)."""

from __future__ import annotations

from enum import Enum


class LegalRfMode(str, Enum):
    """What this node is allowed to do. Satellite TX is never a mode."""

    RECEIVE_ONLY = "receive_only"  # SDR RX + local AP only (default safest)
    ISM_MESH = "ism_mesh"  # + unlicensed Wi-Fi/ISM mesh TX
    ISM_LORA_CONTROL = "ism_lora_control"  # + low-BW LoRa/ISM control plane
    HYBRID_GATEWAY = "hybrid_gateway"  # + opportunistic legal uplink as client
    AMATEUR_OPERATOR = "amateur_operator"  # requires explicit license affirmation


ALLOWED_MODES = {m.value for m in LegalRfMode}

# Modes that must never be accepted
FORBIDDEN_MODE_KEYWORDS = frozenset(
    {
        "satellite-uplink",
        "sat-tx",
        "starlink",
        "oneweb",
        "vsat-tx",
        "jamming",
        "gps-spoof",
        "pirate-bts",
        "commercial-decrypt",
    }
)


def satellite_receive_only_ok(mode: str) -> tuple[bool, str]:
    """Fail-closed: satellite RF stays receive-only.

    Allowed legal_rf_mode values may enable unlicensed ISM mesh TX. None of them
    enable satellite uplink or commercial constellation clients. Unknown or
    forbidden mode strings fail (including empty).
    """
    lowered = (mode or "").strip().lower().replace(" ", "_")
    if not lowered:
        return False, "legal_rf_mode unset"
    for bad in FORBIDDEN_MODE_KEYWORDS:
        if bad in lowered:
            return False, f"forbidden satellite/commercial mode keyword '{bad}'"
    try:
        from skycache.config import FORBIDDEN_SOURCE_KEYWORDS
    except Exception:  # noqa: BLE001
        FORBIDDEN_SOURCE_KEYWORDS = frozenset()
    for bad in FORBIDDEN_SOURCE_KEYWORDS:
        if bad in lowered:
            return False, f"forbidden source/uplink keyword '{bad}'"
    if lowered not in ALLOWED_MODES:
        return False, (
            f"unknown legal_rf_mode '{mode}' "
            "(not an allowed satellite receive-only mode)"
        )
    return True, f"mode={lowered}; satellite TX never enabled"


def validate_legal_rf_mode(mode: str, *, amateur_license_affirmed: bool = False) -> LegalRfMode:
    lowered = (mode or "").strip().lower().replace(" ", "_")
    for bad in FORBIDDEN_MODE_KEYWORDS:
        if bad in lowered:
            raise ValueError(
                f"Refusing RF mode '{mode}': forbidden keyword '{bad}'. "
                "SkyCache never enables commercial decrypt or satellite uplink by default."
            )
    if lowered not in ALLOWED_MODES:
        raise ValueError(
            f"Unknown legal_rf_mode '{mode}'. Allowed: {', '.join(sorted(ALLOWED_MODES))}"
        )
    m = LegalRfMode(lowered)
    if m == LegalRfMode.AMATEUR_OPERATOR and not amateur_license_affirmed:
        raise ValueError(
            "AMATEUR_OPERATOR mode requires SKYCACHE_AMATEUR_LICENSE_AFFIRMED=true "
            "and a valid national amateur license held by the operator. "
            "Software still does not ship automatic satellite uplink."
        )
    return m
