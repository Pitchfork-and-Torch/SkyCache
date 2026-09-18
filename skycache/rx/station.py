"""Ground station configuration (lat/lon/alt + antenna notes)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def station_path(data_dir: Path) -> Path:
    return Path(data_dir) / "rx" / "station.json"


def load_station(data_dir: Path) -> dict[str, Any] | None:
    p = station_path(data_dir)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_station(
    data_dir: Path,
    *,
    lat: float,
    lon: float,
    alt_m: float = 0.0,
    name: str = "village-station",
    antenna: str = "",
    notes: str = "",
) -> dict[str, Any]:
    if not (-90.0 <= float(lat) <= 90.0):
        raise ValueError("lat must be between -90 and 90")
    if not (-180.0 <= float(lon) <= 180.0):
        raise ValueError("lon must be between -180 and 180")
    payload = {
        "schema": "skycache.rx.station.v1",
        "name": name or "village-station",
        "lat": float(lat),
        "lon": float(lon),
        "alt_m": float(alt_m),
        "antenna": antenna or "",
        "notes": notes or "",
        "updated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "legal": "Receive-only station metadata - no uplink configuration",
    }
    path = station_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
