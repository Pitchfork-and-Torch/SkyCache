"""Known legal free-to-air RX recipes for SatDump / field ops.

Frequencies and bird status change - operators must verify current transmission
status before investing a pass. Never decrypt commercial broadband.
"""

from __future__ import annotations

from typing import Any

# Real-world amateur/weather FTA recipes used with RTL-SDR + SatDump.
# pipeline names align with common SatDump CLI ids (verify with local SatDump version).
RECIPES: dict[str, dict[str, Any]] = {
    "noaa_apt": {
        "id": "noaa_apt",
        "title": "NOAA APT (137 MHz class)",
        "legal": "fta_public",
        "band": "VHF",
        "freq_mhz": 137.5,
        "freq_note": "NOAA-15/18/19 APT channels near 137.1 / 137.62 / 137.9125 MHz - verify active birds",
        "hardware": ["rtl-sdr", "V-dipole or QFH ~137 MHz"],
        "satdump_pipeline": "noaa_apt",
        "satdump_aliases": ["NOAA_APT", "noaa_apt"],
        "priority_class": "weather",
        "honest": "APT service is aging; check which NOAA craft still transmit in your region.",
    },
    "meteor_lrpt": {
        "id": "meteor_lrpt",
        "title": "Meteor-M LRPT",
        "legal": "fta_public",
        "band": "VHF",
        "freq_mhz": 137.9,
        "freq_note": "Meteor-M LRPT ~137.9 MHz class - verify active spacecraft",
        "hardware": ["rtl-sdr", "V-dipole or QFH ~137 MHz"],
        "satdump_pipeline": "meteor_m2-x_lrpt",
        "satdump_aliases": ["meteor_m2-x_lrpt", "METEOR_M2_LRPT"],
        "priority_class": "weather",
        "honest": "Spacecraft fail; re-check status before field days.",
    },
    "goes_hrit": {
        "id": "goes_hrit",
        "title": "GOES HRIT (L-band dish path)",
        "legal": "fta_public",
        "band": "L-band",
        "freq_mhz": 1694.1,
        "freq_note": "GOES HRIT ~1.694 GHz - needs dish + LNA + filter, geography-dependent",
        "hardware": ["SDR capable of L-band", "dish", "LNA", "filter"],
        "satdump_pipeline": "goes_hrit",
        "satdump_aliases": ["goes_hrit", "GOES_HRIT"],
        "priority_class": "weather",
        "honest": "Not a starter path; advanced station only.",
    },
    "open_amsat": {
        "id": "open_amsat",
        "title": "Open amateur / CubeSat telemetry (gr-satellites)",
        "legal": "amateur_open",
        "band": "VHF/UHF",
        "freq_mhz": None,
        "freq_note": "Satellite-specific; only open amateur downlinks",
        "hardware": ["rtl-sdr", "appropriate antenna"],
        "satdump_pipeline": None,
        "plugin": "gr_satellites",
        "priority_class": "telemetry",
        "honest": "Educational telemetry only - not broadband.",
    },
    "product_import": {
        "id": "product_import",
        "title": "Import already-decoded FTA product (PNG/JPG/dir)",
        "legal": "fta_public",
        "band": "n/a",
        "freq_mhz": None,
        "freq_note": "Use after SatDump GUI/CLI produced images on disk",
        "hardware": [],
        "satdump_pipeline": "import",
        "plugin": "satdump_weather",
        "priority_class": "weather",
        "honest": "Primary real-world day-one path: decode outside, ingest here.",
    },
}


def list_recipes() -> list[dict[str, Any]]:
    return [dict(v) for v in RECIPES.values()]


def get_recipe(recipe_id: str) -> dict[str, Any] | None:
    key = (recipe_id or "").strip().lower().replace("-", "_")
    if key in RECIPES:
        return dict(RECIPES[key])
    for r in RECIPES.values():
        aliases = [str(a).lower() for a in (r.get("satdump_aliases") or [])]
        if key in aliases or key == str(r.get("satdump_pipeline") or "").lower():
            return dict(r)
    return None
