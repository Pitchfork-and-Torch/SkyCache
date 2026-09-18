"""Spectrum compliance helpers for Nexus mesh (unlicensed/ISM only).

SkyCache mesh transmit is restricted to unlicensed / ISM-class links:
  - 2.4 / 5 / 6 GHz Wi-Fi (hostapd / batman-adv / mesh APs)
  - Regional LoRa / Meshtastic-class ISM (control plane / low-BW DTN only)

Operators MUST verify national rules (EIRP, duty cycle, outdoor use, DFS).
This module never enables illegal bands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MeshBand = Literal["wifi_2g", "wifi_5g", "wifi_6g", "lora_ism", "sim"]

# Hard deny - never used by Nexus mesh orchestration
FORBIDDEN_MESH_KEYWORDS: frozenset[str] = frozenset(
    {
        "starlink",
        "oneweb",
        "vsat-tx",
        "satellite-uplink",
        "licensed-microwave",
        "cellular-base-station",
        "jamming",
        "gps-spoof",
    }
)

ALLOWED_BANDS: dict[MeshBand, dict[str, object]] = {
    "wifi_2g": {
        "label": "Wi-Fi 2.4 GHz",
        "typical_use": "batman-adv mesh + client AP",
        "notes": "Check national EIRP and outdoor channel rules",
    },
    "wifi_5g": {
        "label": "Wi-Fi 5 GHz",
        "typical_use": "high-throughput mesh backhaul",
        "notes": "DFS / weather-radar channels may be restricted outdoors",
    },
    "wifi_6g": {
        "label": "Wi-Fi 6 GHz (where legal)",
        "typical_use": "high-capacity indoor/outdoor where authorized",
        "notes": "Not available in all countries; verify LPI/SP rules",
    },
    "lora_ism": {
        "label": "Regional LoRa / ISM",
        "typical_use": "low-bandwidth DTN / emergency control plane",
        "notes": "Duty-cycle and power limits vary by region",
    },
    "sim": {
        "label": "Simulation (no RF)",
        "typical_use": "multi-node software simulation",
        "notes": "No radio emissions",
    },
}


@dataclass(frozen=True)
class SpectrumPolicy:
    """Operator-facing compliance snapshot."""

    allowed_bands: tuple[MeshBand, ...]
    satellite_tx_allowed: bool = False
    commercial_decrypt_allowed: bool = False
    banner: str = (
        "Nexus mesh: unlicensed Wi-Fi/ISM only. Receive-only for satellite. "
        "Not free commercial broadband. Verify local spectrum and hotspot laws."
    )


DEFAULT_POLICY = SpectrumPolicy(
    allowed_bands=("wifi_2g", "wifi_5g", "wifi_6g", "lora_ism", "sim"),
)


def validate_mesh_mode(mode: str) -> None:
    lowered = (mode or "").lower().replace(" ", "-")
    for bad in FORBIDDEN_MESH_KEYWORDS:
        if bad in lowered:
            raise ValueError(
                f"Refusing mesh mode '{mode}': matches forbidden keyword '{bad}'. "
                "Nexus never enables satellite uplink or commercial RF bypass."
            )
    if lowered in {"sat-tx", "uplink", "starlink-dish"}:
        raise ValueError("Satellite transmit modes are forbidden in SkyCache Nexus.")


def validate_band(band: str) -> MeshBand:
    validate_mesh_mode(band)
    if band not in ALLOWED_BANDS:
        raise ValueError(
            f"Unknown or disallowed mesh band '{band}'. "
            f"Allowed: {', '.join(ALLOWED_BANDS)}"
        )
    return band  # type: ignore[return-value]


def compliance_report() -> dict[str, object]:
    return {
        "policy": DEFAULT_POLICY.banner,
        "satellite_tx_allowed": False,
        "commercial_decrypt_allowed": False,
        "allowed_bands": {
            k: v for k, v in ALLOWED_BANDS.items()
        },
        "operator_duty": (
            "Before enabling any mesh radio: confirm national unlicensed-band rules, "
            "AP registration if required, and power limits. Prefer Wi-Fi mesh for "
            "community broadband experience; LoRa only for sparse control/DTN."
        ),
    }
