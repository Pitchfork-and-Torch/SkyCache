"""Pass Autopilot: bind upcoming FTA passes to recipes, arm the station, emit SatDump CLI.

Receive-only. Unencrypted free-to-air / open amateur only.
SatDump (or equivalent) still owns demodulation; SkyCache owns the duty cycle.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.rx.pass_plan import predict_passes
from skycache.rx.recipes import get_recipe
from skycache.rx.station import load_station

ARM_NAME = "arm-state.json"
SCHEDULE_SCHEMA = "skycache.rx.schedule.v1"
ARM_SCHEMA = "skycache.rx.arm.v1"
DUTY_SCHEMA = "skycache.rx.duty.v1"

# Name fragments (case-insensitive) -> default recipe id
_NAME_RECIPE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"goes|hrit|emwin", re.I), "goes_hrit"),
    (re.compile(r"meteor", re.I), "meteor_lrpt"),
    (re.compile(r"noaa|poes", re.I), "noaa_apt"),
    (re.compile(r"cubesat|amsat|amateur", re.I), "open_amsat"),
]


def arm_path(data_dir: Path) -> Path:
    return Path(data_dir) / "rx" / ARM_NAME


def recipe_for_satellite(name: str) -> str:
    """Best-effort recipe id for a satellite display name."""
    n = (name or "").strip()
    if not n:
        return "product_import"
    for pat, rid in _NAME_RECIPE_RULES:
        if pat.search(n):
            return rid
    return "product_import"


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        text = str(s).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def satdump_command(
    *,
    recipe_id: str,
    products_dir: str | Path,
    input_hint: str = "live",
    satdump_bin: str = "satdump",
) -> dict[str, Any]:
    """
    Build an honest SatDump CLI sketch for the operator.

    Live USB capture orchestration stays in SatDump GUI/CLI; we emit the
    pipeline + product directory contract operators need for SkyCache watch.
    """
    recipe = get_recipe(recipe_id) or get_recipe("product_import")
    assert recipe is not None
    pipeline = recipe.get("satdump_pipeline") or "import"
    out = Path(products_dir)
    # product_import has no live pipeline; guide operator to GUI + watch
    if recipe.get("id") == "product_import" or pipeline in (None, "import"):
        return {
            "mode": "product_import",
            "recipe": recipe.get("id"),
            "pipeline": None,
            "command": None,
            "guidance": (
                f"Run SatDump GUI/CLI for the pass; set product output to {out}. "
                f"Then: skycache rx watch --dir {out} --once"
            ),
            "products_dir": str(out),
            "legal": recipe.get("legal"),
            "honest": recipe.get("honest"),
        }
    # Offline IQ path: satdump <pipeline> <input_level> <input> <output_dir>
    cmd_iq = (
        f"{satdump_bin} {pipeline} baseband <iq_or_baseband_file> {out} "
        f"--samplerate <hz> --baseband_format <cf32|cs16|cs8|cu8>"
    )
    # Live path is SatDump GUI or `satdump live ...` (version-specific)
    cmd_live = (
        f"# Prefer SatDump GUI live decode for {recipe.get('title')}; "
        f"point product folder at {out}. "
        f"CLI live flags vary by SatDump version - verify with: {satdump_bin}"
    )
    return {
        "mode": "pipeline",
        "recipe": recipe.get("id"),
        "pipeline": pipeline,
        "freq_mhz": recipe.get("freq_mhz"),
        "freq_note": recipe.get("freq_note"),
        "command_iq": cmd_iq,
        "command_live_note": cmd_live,
        "command": cmd_iq if input_hint != "live" else None,
        "products_dir": str(out),
        "aliases": list(recipe.get("satdump_aliases") or []),
        "legal": recipe.get("legal"),
        "honest": recipe.get("honest"),
        "hardware": list(recipe.get("hardware") or []),
    }


def build_schedule(
    data_dir: Path,
    *,
    hours: float = 24.0,
    min_elevation: float = 15.0,
    products_dir: str | Path | None = None,
    lat: float | None = None,
    lon: float | None = None,
    alt_m: float | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    """Upcoming passes with recipe binding + SatDump command sketches."""
    data_dir = Path(data_dir)
    st = load_station(data_dir)
    if lat is None or lon is None:
        if not st:
            return {
                "schema": SCHEDULE_SCHEMA,
                "ok": False,
                "error": "Configure station first: skycache rx station --lat LAT --lon LON",
                "slots": [],
            }
        lat = float(st["lat"])
        lon = float(st["lon"])
        alt_m = float(st.get("alt_m") or 0.0) if alt_m is None else alt_m
    alt = float(alt_m or 0.0)
    prod = Path(products_dir) if products_dir else data_dir / "satdump-products"
    report = predict_passes(
        lat=float(lat),
        lon=float(lon),
        alt_m=alt,
        hours=float(hours),
        min_elevation=float(min_elevation),
        data_dir=data_dir,
    )
    slots: list[dict[str, Any]] = []
    for p in (report.get("passes") or [])[: max(1, int(limit))]:
        sat = str(p.get("satellite") or "")
        rid = recipe_for_satellite(sat)
        recipe = get_recipe(rid) or {}
        cmd = satdump_command(recipe_id=rid, products_dir=prod)
        slots.append(
            {
                **p,
                "recipe_id": rid,
                "recipe_title": recipe.get("title") or rid,
                "legal": recipe.get("legal") or "fta_public",
                "band": recipe.get("band"),
                "freq_mhz": recipe.get("freq_mhz"),
                "satdump": cmd,
                "operator_steps": [
                    f"Before AOS ({p.get('aos')}): open SatDump for recipe {rid}",
                    f"Product output directory: {prod}",
                    "After LOS: skycache rx watch --dir <products> --once "
                    f"--satellite \"{sat}\"",
                    "Optional: skycache rx log --satellite ... --elevation ... --quality good",
                ],
            }
        )
    next_slot = slots[0] if slots else None
    return {
        "schema": SCHEDULE_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "engine": report.get("engine"),
        "observer": report.get("observer"),
        "hours": float(hours),
        "min_elevation_deg": float(min_elevation),
        "products_dir": str(prod),
        "count": len(slots),
        "next": next_slot,
        "slots": slots,
        "legal": "Receive-only FTA / open amateur pass duty cycle - not commercial broadband",
        "honest": (
            "SkyCache binds passes to recipes and product watch; "
            "SatDump performs demodulation. Verify active birds before field day."
        ),
    }


def save_arm(
    data_dir: Path,
    *,
    hours: float = 12.0,
    min_elevation: float = 15.0,
    products_dir: str | Path | None = None,
    auto_field_log: bool = True,
    recipes: list[str] | None = None,
) -> dict[str, Any]:
    """Arm station for upcoming duty windows (persisted for watch auto-log)."""
    data_dir = Path(data_dir)
    sched = build_schedule(
        data_dir,
        hours=hours,
        min_elevation=min_elevation,
        products_dir=products_dir,
    )
    if not sched.get("ok"):
        return {**sched, "schema": ARM_SCHEMA, "armed": False}

    if recipes:
        filt = {r.strip().lower().replace("-", "_") for r in recipes if r.strip()}
        slots = [
            s
            for s in (sched.get("slots") or [])
            if str(s.get("recipe_id") or "").lower().replace("-", "_") in filt
        ]
    else:
        slots = list(sched.get("slots") or [])

    prod = str(sched.get("products_dir") or (data_dir / "satdump-products"))
    arm = {
        "schema": ARM_SCHEMA,
        "armed": True,
        "armed_at": _iso_now(),
        "hours": float(hours),
        "min_elevation_deg": float(min_elevation),
        "products_dir": prod,
        "auto_field_log": bool(auto_field_log),
        "recipe_filter": list(recipes or []),
        "slot_count": len(slots),
        "next": slots[0] if slots else None,
        "slots": slots,
        "watch_hint": f"skycache rx watch --dir {prod} --once",
        "legal": "Receive-only station arm - no uplink",
        "honest": (
            "Arming does not start RF TX. Operator still runs SatDump for the pass; "
            "SkyCache auto-ingests products and may append field-log rows."
        ),
    }
    path = arm_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(arm, indent=2) + "\n", encoding="utf-8")
    return arm


def load_arm(data_dir: Path) -> dict[str, Any] | None:
    path = arm_path(data_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and data.get("armed"):
            return data
    except (OSError, json.JSONDecodeError):
        return None
    return None


def clear_arm(data_dir: Path) -> dict[str, Any]:
    path = arm_path(data_dir)
    if path.is_file():
        try:
            path.unlink()
        except OSError as exc:
            return {"ok": False, "armed": False, "error": str(exc)}
    return {
        "ok": True,
        "armed": False,
        "disarmed_at": _iso_now(),
        "schema": ARM_SCHEMA,
    }


def duty_status(data_dir: Path) -> dict[str, Any]:
    """Compact station duty board: arm + next pass + countdown."""
    data_dir = Path(data_dir)
    st = load_station(data_dir)
    arm = load_arm(data_dir)
    sched = build_schedule(data_dir, hours=12.0, min_elevation=15.0)
    nxt = None
    if arm and arm.get("next"):
        nxt = arm.get("next")
    elif sched.get("next"):
        nxt = sched.get("next")

    countdown_sec: float | None = None
    aos = _parse_iso((nxt or {}).get("aos") if isinstance(nxt, dict) else None)
    if aos is not None:
        countdown_sec = (aos - datetime.now(timezone.utc)).total_seconds()

    return {
        "schema": DUTY_SCHEMA,
        "generated_at": _iso_now(),
        "station": st,
        "armed": bool(arm and arm.get("armed")),
        "arm": arm,
        "schedule_ok": bool(sched.get("ok")),
        "engine": sched.get("engine"),
        "next_pass": nxt,
        "countdown_sec": countdown_sec,
        "products_dir": (arm or {}).get("products_dir")
        or sched.get("products_dir")
        or str(data_dir / "satdump-products"),
        "legal": "Receive-only FTA duty board",
        "honest": "Not free commercial satellite internet.",
    }


def match_arm_slot(
    arm: dict[str, Any] | None,
    *,
    satellite: str = "",
    when: datetime | None = None,
) -> dict[str, Any] | None:
    """Find arm slot matching satellite name and/or current time window."""
    if not arm or not arm.get("armed"):
        return None
    slots = list(arm.get("slots") or [])
    if not slots:
        return None
    sat = (satellite or "").strip().lower()
    now = when or datetime.now(timezone.utc)

    # Prefer name match within AOS-10m .. LOS+30m
    for s in slots:
        s_name = str(s.get("satellite") or "").strip().lower()
        if sat and sat not in s_name and s_name not in sat:
            continue
        aos = _parse_iso(s.get("aos"))
        los = _parse_iso(s.get("los"))
        if aos and los:
            pad_before = 10 * 60
            pad_after = 30 * 60
            t0 = aos.timestamp() - pad_before
            t1 = los.timestamp() + pad_after
            if t0 <= now.timestamp() <= t1:
                return s
        elif sat:
            return s

    # Fall back: any name match
    if sat:
        for s in slots:
            s_name = str(s.get("satellite") or "").strip().lower()
            if sat in s_name or s_name in sat:
                return s

    # Fall back: currently active window regardless of name
    for s in slots:
        aos = _parse_iso(s.get("aos"))
        los = _parse_iso(s.get("los"))
        if aos and los:
            if aos.timestamp() - 600 <= now.timestamp() <= los.timestamp() + 1800:
                return s
    return None


def maybe_auto_field_log(
    data_dir: Path,
    *,
    package_id: str,
    satellite: str = "",
    recipe: str = "",
    quality: str = "auto",
) -> dict[str, Any] | None:
    """If station is armed with auto_field_log, append a field-log row for ingest."""
    arm = load_arm(data_dir)
    if not arm or not arm.get("auto_field_log"):
        return None
    slot = match_arm_slot(arm, satellite=satellite)
    sat = satellite or (slot or {}).get("satellite") or "unknown"
    elev = (slot or {}).get("max_elevation_deg")
    rid = recipe or (slot or {}).get("recipe_id") or "product_import"
    from skycache.rx.field_log import append_field_log

    try:
        return append_field_log(
            data_dir,
            satellite=str(sat),
            elevation_deg=float(elev) if elev is not None else None,
            quality=quality or "auto",
            recipe=str(rid),
            package_id=str(package_id or ""),
            notes="auto field-log from armed station product watch",
            operator="autopilot",
        )
    except ValueError:
        return None
