"""Fabric power / SOC map from mesh peers + local power provider."""

from __future__ import annotations

from typing import Any

from skycache.health.power import PowerMode, mode_from_soc
from skycache.nexus.mesh import MeshFabric


def fabric_power_map(
    mesh: MeshFabric,
    *,
    local_battery: float | None,
    local_solar: bool = False,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    local_mode = mode_from_soc(local_battery) if local_battery is not None else PowerMode.NORMAL
    nodes.append(
        {
            "node_id": mesh.node_id,
            "role": "self",
            "battery_percent": local_battery,
            "solar": local_solar,
            "mode": local_mode.value,
            "package_count": None,
        }
    )
    for p in mesh.peers.values():
        pct = p.battery_percent
        mode = mode_from_soc(pct) if pct is not None else PowerMode.NORMAL
        nodes.append(
            {
                "node_id": p.node_id,
                "role": p.role,
                "battery_percent": pct,
                "solar": p.solar,
                "mode": mode.value,
                "package_count": p.package_count,
                "link_quality": p.link_quality,
                "hop_count": p.hop_count,
            }
        )

    critical = [n for n in nodes if n.get("mode") in ("critical", "emergency")]
    eco = [n for n in nodes if n.get("mode") == "eco"]
    return {
        "nodes": nodes,
        "preferred_routes": mesh.prefer_power_route(),
        "critical_count": len(critical),
        "eco_count": len(eco),
        "recommendation": (
            "Prefer solar/high-SOC peers for gateway and mule."
            if any(n.get("solar") for n in nodes)
            else "No solar peers advertised; conserve storage and radio."
        ),
    }
