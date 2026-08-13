"""Field-soak protocols (software complete). Physical soak remains operator-owned.

Each surface gets a signed checklist receipt. Writing the protocol closes the
software track. Executing it on real radios/dongles is a field residual.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__

SCHEMA = "skycache.soak.protocol.v1"
HONEST = (
    "Soak protocol is a software checklist + receipt. "
    "Physical radio/dongle/village soak stays operator-owned. "
    "Not free commercial broadband."
)

SOAK_SURFACES: dict[str, dict[str, Any]] = {
    "rx": {
        "title": "Live FTA RX dongle soak",
        "legal": "Receive-only. Unencrypted FTA only. Never commercial decrypt.",
        "steps": [
            "Confirm legal_rf_mode is receive_only or hybrid_gateway with RX allowed",
            "skycache rx doctor (go_rx_lab true in sim)",
            "Optional field: attach RTL-SDR, run rx watch for one lawful weather pass",
            "Log sat name, freq, product files, and legal banner in site logbook",
            "Never point the station at a paid constellation",
        ],
    },
    "dual-radio": {
        "title": "Dual-radio mesh soak",
        "legal": "Unlicensed Wi-Fi/ISM only. Not free Starlink.",
        "steps": [
            "Identify MESH_IF vs CLIENT_IF",
            "skycache dual-radio doctor (go_sim_validation)",
            "Optional field: batman-adv day-one + hostapd client AP",
            "Confirm batctl neighbors and SkyCache-Village SSID",
            "Record spectrum check date and channel",
        ],
    },
    "gateway": {
        "title": "Metered-link gateway soak",
        "legal": "Open-mirror presets + quota only. Not automatic public internet.",
        "steps": [
            "skycache gateway doctor --sim",
            "skycache gateway pull-preset gutenberg-sample --sim",
            "Confirm pull receipt + license passport",
            "Optional field: run one metered-link pull under daily quota",
            "Never disable the allowlist",
        ],
    },
    "village-day": {
        "title": "Village-day weekend soak",
        "legal": "Sim green is not RF authorization.",
        "steps": [
            "skycache village-day doctor --sim",
            "skycache village-day readiness --sim",
            "Walk the printed RUNBOOK.md with two maintainers",
            "Optional field: one classroom weekend without claiming broadband",
            "Close disaster mode if it was used",
        ],
    },
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _digest(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_soak_protocol(surface: str) -> dict[str, Any]:
    key = surface.strip().lower()
    spec = SOAK_SURFACES.get(key)
    if spec is None:
        raise ValueError(f"unknown soak surface: {surface}")
    body = {
        "schema": SCHEMA,
        "surface": key,
        "title": spec["title"],
        "legal": spec["legal"],
        "steps": list(spec["steps"]),
        "physical_required": False,
        "software_complete": True,
        "field_residual": True,
        "software_version": __version__,
        "generated_at": _iso_now(),
        "banner": HONEST,
    }
    body["sha256"] = _digest({k: v for k, v in body.items() if k != "sha256"})
    return body


def write_soak_protocol(surface: str, out_dir: Path) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    proto = build_soak_protocol(surface)
    slug = proto["surface"]
    json_path = out_dir / f"soak-{slug}.json"
    md_path = out_dir / f"soak-{slug}.md"
    json_path.write_text(json.dumps(proto, indent=2) + "\n", encoding="utf-8")
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(proto["steps"], 1))
    md_path.write_text(
        f"# {proto['title']}\n\n{HONEST}\n\n{proto['legal']}\n\n{steps}\n\n"
        f"sha256: {proto['sha256']}\n",
        encoding="utf-8",
    )
    return {"ok": True, "surface": slug, "json": str(json_path), "md": str(md_path), **proto}


def write_all_soak_protocols(out_dir: Path) -> dict[str, Any]:
    written = [write_soak_protocol(name, out_dir) for name in SOAK_SURFACES]
    return {
        "schema": "skycache.soak.bundle.v1",
        "ok": all(w.get("ok") for w in written),
        "count": len(written),
        "surfaces": [w["surface"] for w in written],
        "out_dir": str(out_dir),
        "banner": HONEST,
    }
