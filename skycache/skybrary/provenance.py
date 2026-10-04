"""Batch provenance reports for corpus imports (regulator / partner friendly)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_provenance_report(
    items: list[dict[str, Any]],
    *,
    batch_id: str = "",
    operator_note: str = "",
) -> dict[str, Any]:
    """Normalize per-item provenance into a batch report."""
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict[str, Any]] = []
    missing = 0
    for it in items:
        lic = (it.get("license") or "").strip()
        prov = (it.get("provenance_url") or it.get("source_url") or "").strip()
        redist = it.get("redistribute")
        if redist is None:
            redist = "review"
        row = {
            "id": it.get("id") or it.get("work_id") or it.get("package_id") or "",
            "title": it.get("title") or "",
            "license": lic or "unknown",
            "provenance_url": prov,
            "retrieval_date": it.get("retrieval_date") or it.get("retrieved_at") or built[:10],
            "sha256": it.get("sha256") or "",
            "redistribute": redist,
            "notes": it.get("notes") or "",
        }
        if not lic or lic.lower() in {"unknown", ""} or not prov:
            missing += 1
            row["flags"] = ["incomplete_passport"]
        else:
            row["flags"] = []
        rows.append(row)

    return {
        "schema": "skycache.provenance.batch.v1",
        "batch_id": batch_id or f"batch-{built.replace(':', '').replace('-', '')}",
        "built_at": built,
        "item_count": len(rows),
        "incomplete_passport_count": missing,
        "operator_note": operator_note,
        "items": rows,
        "legal": (
            "Provenance report does not grant rights. Operator must confirm each "
            "license allows offline redistribution. No commercial decrypt."
        ),
    }


def write_provenance_report(report: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path


def provenance_report_from_content_dir(content_dir: Path) -> dict[str, Any]:
    """Scan package manifests under content_dir into a provenance batch."""
    content_dir = Path(content_dir)
    items: list[dict[str, Any]] = []
    if not content_dir.is_dir():
        return build_provenance_report([], batch_id="empty")
    for d in sorted(content_dir.iterdir()):
        if not d.is_dir():
            continue
        man = d / "manifest.json"
        if not man.is_file():
            continue
        try:
            data = json.loads(man.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        src = data.get("source") or {}
        items.append(
            {
                "id": data.get("id") or d.name,
                "title": (data.get("title") or {}).get("en")
                if isinstance(data.get("title"), dict)
                else data.get("title"),
                "license": data.get("license"),
                "provenance_url": src.get("url") or data.get("provenance_url"),
                "retrieval_date": data.get("created") or data.get("retrieval_date"),
                "sha256": data.get("sha256") or (data.get("integrity") or {}).get("sha256"),
                "redistribute": data.get("redistribute", "review"),
                "notes": data.get("notes") or "",
            }
        )
    return build_provenance_report(items, batch_id=f"content-{content_dir.name}")
