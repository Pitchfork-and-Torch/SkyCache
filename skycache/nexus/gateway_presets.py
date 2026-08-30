"""Open-mirror presets and pull receipt log for ethical gateway use.

Only allowlisted open sources. Never commercial decrypt. Operator-run pulls.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# Presets are *hints* for operators - actual fetch still goes through open_fetch
# allowlist / open_http_import legal gates.
OPEN_MIRROR_PRESETS: dict[str, dict[str, Any]] = {
    "gutenberg-sample": {
        "id": "gutenberg-sample",
        "label": "Project Gutenberg (sample open text)",
        "kind": "open_text",
        "example_url": "https://www.gutenberg.org/files/11/11-0.txt",
        "notes": (
            "Operator must respect gutenberg.org robots/terms. Prefer bulk legal "
            "mirrors they authorize. Public-domain texts only."
        ),
        "priority_class": "education",
        "license_hint": "public-domain (varies by work/jurisdiction)",
    },
    "kiwix-open": {
        "id": "kiwix-open",
        "label": "Kiwix open ZIM catalogs",
        "kind": "zim_catalog",
        "example_url": "https://library.kiwix.org/",
        "notes": (
            "Download ZIM files only where redistribution terms allow for your "
            "deployment. Store as packages with license passport."
        ),
        "priority_class": "education",
        "license_hint": "varies per ZIM - check Kiwix / content license",
    },
    "archive-pd": {
        "id": "archive-pd",
        "label": "Internet Archive public-domain texts",
        "kind": "open_text",
        "example_url": "https://archive.org/details/texts",
        "notes": (
            "Only texts marked public domain / CC with clear redistribute rights. "
            "No commercial ebook piracy."
        ),
        "priority_class": "education",
        "license_hint": "public-domain or CC (check item page)",
    },
    "who-open-hint": {
        "id": "who-open-hint",
        "label": "WHO / MoH open health (operator curated)",
        "kind": "health",
        "example_url": "",
        "notes": (
            "Use only materials your ministry / WHO open licenses clearly permit "
            "to package offline. Prefer MoH-supplied USB packs when available."
        ),
        "priority_class": "health",
        "license_hint": "moh-open / check source",
    },
}


def list_presets() -> list[dict[str, Any]]:
    return list(OPEN_MIRROR_PRESETS.values())


def get_preset(preset_id: str) -> dict[str, Any]:
    if preset_id not in OPEN_MIRROR_PRESETS:
        raise ValueError(
            f"Unknown preset '{preset_id}'. Known: {', '.join(sorted(OPEN_MIRROR_PRESETS))}"
        )
    return dict(OPEN_MIRROR_PRESETS[preset_id])


class PullReceiptLog:
    """Append-only local receipt log: what the gateway pulled (no PII, no cloud)."""

    def __init__(self, path: Path, *, max_entries: int = 500) -> None:
        self.path = Path(path)
        self.max_entries = max_entries
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("receipts"), list):
            return list(data["receipts"])
        return []

    def _save(self, entries: list[dict[str, Any]]) -> None:
        trimmed = entries[-self.max_entries :]
        payload = {
            "receipts": trimmed,
            "count": len(trimmed),
            "legal": (
                "Local-only pull receipts. Open content only. No commercial decrypt. "
                "Not exported off-node by default."
            ),
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        row = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **entry,
        }
        entries = self._load()
        entries.append(row)
        self._save(entries)
        return row

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        entries = self._load()
        return entries[-max(1, limit) :]

    def summary(self) -> dict[str, Any]:
        entries = self._load()
        total_bytes = sum(int(e.get("bytes") or 0) for e in entries)
        ok_n = sum(1 for e in entries if e.get("ok"))
        return {
            "count": len(entries),
            "ok_count": ok_n,
            "total_bytes": total_bytes,
            "path": str(self.path),
            "recent": entries[-10:],
            "legal": (
                "Local receipts only. Operator audit trail for fair-share gateway pulls."
            ),
        }
