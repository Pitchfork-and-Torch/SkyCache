"""Local ops snapshot: disk, power, peers, pack freshness (E4).

Default: local only. Fleet heartbeat remains opt-in and OFF.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _disk(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        u = shutil.disk_usage(path)
        return {
            "path": str(path),
            "total_bytes": u.total,
            "used_bytes": u.used,
            "free_bytes": u.free,
            "used_pct": round(100.0 * u.used / u.total, 2) if u.total else None,
        }
    except OSError as exc:
        return {"path": str(path), "error": str(exc)}


def _pack_freshness(content_dir: Path, *, limit: int = 50) -> dict[str, Any]:
    content_dir = Path(content_dir)
    if not content_dir.is_dir():
        return {"packages": 0, "newest_mtime": None, "oldest_mtime": None}
    mtimes: list[float] = []
    count = 0
    for child in content_dir.iterdir():
        if not child.is_dir() or not (child / "manifest.json").is_file():
            continue
        count += 1
        try:
            mtimes.append((child / "manifest.json").stat().st_mtime)
        except OSError:
            continue
        if count >= 10_000:
            break
    if not mtimes:
        return {"packages": count, "newest_mtime": None, "oldest_mtime": None}
    newest = max(mtimes)
    oldest = min(mtimes)
    return {
        "packages": count,
        "newest_mtime": datetime.fromtimestamp(newest, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "oldest_mtime": datetime.fromtimestamp(oldest, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "sample_limit_note": f"scanned up to {limit}+ package dirs",
    }


def local_ops_snapshot(
    settings: Any,
    *,
    mesh: Any | None = None,
    sky_count: int | None = None,
) -> dict[str, Any]:
    """Privacy-preserving local metrics for admin / doctor."""
    data_dir = Path(settings.data_dir)
    content_dir = Path(settings.content_dir)
    battery = None
    power_mode = None
    try:
        from skycache.health.power import get_power_provider, mode_from_soc

        provider = get_power_provider(
            getattr(settings, "power_provider", "mock"),
            getattr(settings, "mock_battery_percent", 100.0),
        )
        battery = provider.battery_percent()
        power_mode = mode_from_soc(battery).value
        on_ac = provider.is_on_ac()
    except Exception as exc:  # noqa: BLE001
        battery = None
        power_mode = None
        on_ac = None
        power_error = str(exc)
    else:
        power_error = None

    peers = 0
    disaster = False
    if mesh is not None:
        try:
            st = mesh.status() if hasattr(mesh, "status") else {}
            peers = int(st.get("peer_count") or len(st.get("peers") or []) or 0)
            disaster = bool(st.get("disaster_mode"))
        except Exception:  # noqa: BLE001
            peers = 0

    from skycache.health.bitrot_schedule import schedule_status

    return {
        "schema": "skycache.ops.local.v1",
        "node_id": getattr(settings, "node_id", None) or "",
        "sim_mode": bool(getattr(settings, "sim_mode", False)),
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "disk": _disk(data_dir),
        "content": _pack_freshness(content_dir),
        "power": {
            "battery_percent": battery,
            "mode": power_mode,
            "on_ac": on_ac,
            "error": power_error,
        },
        "mesh": {"peer_count": peers, "disaster_mode": disaster},
        "skybrary_works": sky_count,
        "bitrot": schedule_status(data_dir),
        "fleet_heartbeat": {
            "enabled": False,
            "note": "Default OFF. No cloud telemetry without explicit operator opt-in.",
        },
        "legal": "Local metrics only - no personal data harvest",
    }
