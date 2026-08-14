"""Append-only field log for real satellite passes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def log_path(data_dir: Path) -> Path:
    return Path(data_dir) / "rx" / "field-log.jsonl"


def append_field_log(
    data_dir: Path,
    *,
    satellite: str,
    elevation_deg: float | None = None,
    quality: str = "",
    snr_db: float | None = None,
    recipe: str = "",
    package_id: str = "",
    notes: str = "",
    operator: str = "",
) -> dict[str, Any]:
    sat = (satellite or "").strip()
    if not sat:
        raise ValueError("satellite required")
    entry = {
        "id": str(uuid4()),
        "ts": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "satellite": sat,
        "elevation_deg": elevation_deg,
        "quality": (quality or "").strip(),
        "snr_db": snr_db,
        "recipe": (recipe or "").strip(),
        "package_id": (package_id or "").strip(),
        "notes": (notes or "").strip(),
        "operator": (operator or "").strip(),
        "legal": "FTA / open RX field note only",
    }
    path = log_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def list_field_log(data_dir: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    path = log_path(data_dir)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return []
    for line in lines[-max(1, int(limit)) :]:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows
