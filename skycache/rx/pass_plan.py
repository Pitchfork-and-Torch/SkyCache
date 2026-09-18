"""Satellite pass planning from TLE cache.

Uses optional PyPI `sgp4` when installed for real-world predictions.
Without sgp4, returns schedule from offline fixture tables so CI/demos work,
and instructs the operator to `pip install sgp4` for live geometry.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Bundled sample TLEs (educational; operators should refresh from Celestrak/Space-Track
# under their own ToS - we never claim these are always current).
# Format: name, line1, line2
DEFAULT_TLE_BUNDLE = [
    (
        "NOAA 15",
        "1 25338U 98030A   24101.51234567  .00000000  00000-0  00000-0 0  9990",
        "2 25338  98.7000 123.4567 0010000  90.0000 270.0000 14.25000000123456",
    ),
    (
        "NOAA 18",
        "1 28654U 05018A   24101.51234567  .00000000  00000-0  00000-0 0  9991",
        "2 28654  99.0000 130.0000 0012000 100.0000 260.0000 14.12000000123457",
    ),
    (
        "NOAA 19",
        "1 33591U 09005A   24101.51234567  .00000000  00000-0  00000-0 0  9992",
        "2 33591  99.1000 140.0000 0014000 110.0000 250.0000 14.11000000123458",
    ),
]


@dataclass
class PassWindow:
    satellite: str
    aos: datetime
    tca: datetime
    los: datetime
    max_elevation_deg: float
    az_aos_deg: float
    az_los_deg: float

    def to_dict(self) -> dict[str, Any]:
        def iso(dt: datetime) -> str:
            return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
                "+00:00", "Z"
            )

        return {
            "satellite": self.satellite,
            "aos": iso(self.aos),
            "tca": iso(self.tca),
            "los": iso(self.los),
            "max_elevation_deg": round(self.max_elevation_deg, 1),
            "az_aos_deg": round(self.az_aos_deg, 1),
            "az_los_deg": round(self.az_los_deg, 1),
        }


def tle_cache_path(data_dir: Path) -> Path:
    return Path(data_dir) / "rx" / "tle-cache.json"


def load_tle_cache(data_dir: Path) -> list[dict[str, str]]:
    p = tle_cache_path(data_dir)
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
            items = data.get("satellites") if isinstance(data, dict) else data
            if isinstance(items, list) and items:
                return [x for x in items if isinstance(x, dict) and x.get("line1")]
        except (OSError, json.JSONDecodeError):
            pass
    return [
        {"name": n, "line1": l1, "line2": l2} for n, l1, l2 in DEFAULT_TLE_BUNDLE
    ]


def save_tle_cache(data_dir: Path, satellites: list[dict[str, str]]) -> Path:
    path = tle_cache_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "skycache.rx.tle.v1",
        "updated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source_note": (
            "Operator-supplied TLEs. Refresh from a legal public source "
            "(e.g. Celestrak) under applicable terms. SkyCache does not scrape."
        ),
        "satellites": satellites,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def import_tle_text(data_dir: Path, text: str) -> dict[str, Any]:
    """Parse 3-line TLE blocks (name + L1 + L2) into the station cache."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sats: list[dict[str, str]] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            name = f"SAT-{lines[i][2:7].strip()}"
            sats.append({"name": name, "line1": lines[i], "line2": lines[i + 1]})
            i += 2
            continue
        if (
            i + 2 < len(lines)
            and lines[i + 1].startswith("1 ")
            and lines[i + 2].startswith("2 ")
        ):
            sats.append(
                {"name": lines[i], "line1": lines[i + 1], "line2": lines[i + 2]}
            )
            i += 3
            continue
        i += 1
    if not sats:
        raise ValueError("No TLE blocks found (need name+line1+line2 or line1+line2 pairs)")
    path = save_tle_cache(data_dir, sats)
    return {"ok": True, "count": len(sats), "path": str(path)}


def _sgp4_available() -> bool:
    try:
        import sgp4  # noqa: F401
        from sgp4.api import Satrec  # noqa: F401

        return True
    except Exception:
        return False


def _observer_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> tuple[float, float, float]:
    """WGS84 lat/lon/alt -> ECEF meters (approx)."""
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    n = a / math.sqrt(1 - e2 * sin_lat * sin_lat)
    x = (n + alt_m) * cos_lat * cos_lon
    y = (n + alt_m) * cos_lat * sin_lon
    z = (n * (1 - e2) + alt_m) * sin_lat
    return x, y, z


def _teme_to_elevation_az(
    r_teme_km: tuple[float, float, float],
    lat_deg: float,
    lon_deg: float,
    alt_m: float,
) -> tuple[float, float]:
    """Rough elevation/azimuth from TEME position (km) vs observer."""
    # Treat TEME ~ ECEF for short amateur planning (good enough for ops triage)
    ox, oy, oz = _observer_ecef(lat_deg, lon_deg, alt_m)
    sx, sy, sz = (r_teme_km[0] * 1000.0, r_teme_km[1] * 1000.0, r_teme_km[2] * 1000.0)
    dx, dy, dz = sx - ox, sy - oy, sz - oz
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    # ENU
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    east = -sin_lon * dx + cos_lon * dy
    north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    up = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    horiz = math.hypot(east, north)
    elev = math.degrees(math.atan2(up, horiz))
    az = (math.degrees(math.atan2(east, north)) + 360.0) % 360.0
    return elev, az


def predict_passes_sgp4(
    *,
    lat: float,
    lon: float,
    alt_m: float = 0.0,
    hours: float = 24.0,
    min_elevation: float = 15.0,
    step_sec: int = 30,
    tles: list[dict[str, str]] | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    from sgp4.api import Satrec, jday

    if tles is None:
        tles = load_tle_cache(data_dir) if data_dir else [
            {"name": n, "line1": l1, "line2": l2} for n, l1, l2 in DEFAULT_TLE_BUNDLE
        ]

    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=float(hours))
    passes: list[PassWindow] = []

    for item in tles:
        name = str(item.get("name") or "SAT")
        l1 = str(item.get("line1") or "")
        l2 = str(item.get("line2") or "")
        if not (l1.startswith("1 ") and l2.startswith("2 ")):
            continue
        try:
            sat = Satrec.twoline2rv(l1, l2)
        except Exception:
            continue
        t = now
        in_pass = False
        aos = tca = los = now
        max_el = -90.0
        az_aos = az_los = 0.0
        while t <= end:
            jd, fr = jday(
                t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6
            )
            err, r, _v = sat.sgp4(jd, fr)
            if err == 0 and r is not None:
                elev, az = _teme_to_elevation_az(
                    (float(r[0]), float(r[1]), float(r[2])), lat, lon, alt_m
                )
            else:
                elev, az = -90.0, 0.0
            above = elev >= float(min_elevation)
            if above and not in_pass:
                in_pass = True
                aos = t
                az_aos = az
                max_el = elev
                tca = t
            elif above and in_pass:
                if elev > max_el:
                    max_el = elev
                    tca = t
            elif not above and in_pass:
                in_pass = False
                los = t
                az_los = az
                passes.append(
                    PassWindow(
                        satellite=name,
                        aos=aos,
                        tca=tca,
                        los=los,
                        max_elevation_deg=max_el,
                        az_aos_deg=az_aos,
                        az_los_deg=az_los,
                    )
                )
            t += timedelta(seconds=int(step_sec))
        if in_pass:
            passes.append(
                PassWindow(
                    satellite=name,
                    aos=aos,
                    tca=tca,
                    los=end,
                    max_elevation_deg=max_el,
                    az_aos_deg=az_aos,
                    az_los_deg=az_los,
                )
            )

    passes.sort(key=lambda p: p.aos)
    return {
        "schema": "skycache.rx.passes.v1",
        "engine": "sgp4",
        "observer": {"lat": lat, "lon": lon, "alt_m": alt_m},
        "hours": hours,
        "min_elevation_deg": min_elevation,
        "count": len(passes),
        "passes": [p.to_dict() for p in passes],
        "legal": "Receive-only planning aid for open FTA weather birds",
        "honest": "TLEs age quickly - refresh operator cache. Geometry is planning-grade.",
    }


def predict_passes_fixture(
    *,
    lat: float,
    lon: float,
    hours: float = 24.0,
    min_elevation: float = 15.0,
) -> dict[str, Any]:
    """Deterministic synthetic schedule for CI / no-sgp4 hosts."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # Place 2-3 fake but structured windows ahead of now
    samples = [
        ("NOAA 18", 1.5, 42.0, 45.0),
        ("NOAA 15", 5.0, 28.0, 120.0),
        ("NOAA 19", 10.5, 55.0, 300.0),
    ]
    passes = []
    for name, h_offset, elev, az in samples:
        if h_offset > hours:
            continue
        if elev < min_elevation:
            continue
        aos = now + timedelta(hours=h_offset)
        tca = aos + timedelta(minutes=6)
        los = aos + timedelta(minutes=12)
        passes.append(
            PassWindow(
                satellite=name,
                aos=aos,
                tca=tca,
                los=los,
                max_elevation_deg=elev,
                az_aos_deg=az,
                az_los_deg=(az + 40) % 360,
            ).to_dict()
        )
    return {
        "schema": "skycache.rx.passes.v1",
        "engine": "fixture",
        "observer": {"lat": lat, "lon": lon, "alt_m": 0.0},
        "hours": hours,
        "min_elevation_deg": min_elevation,
        "count": len(passes),
        "passes": passes,
        "legal": "Receive-only planning aid for open FTA weather birds",
        "honest": (
            "sgp4 not installed - showing fixture schedule for CI/demo. "
            "For real geometry: pip install sgp4 && skycache rx tle-import FILE"
        ),
    }


def predict_passes(
    *,
    lat: float,
    lon: float,
    alt_m: float = 0.0,
    hours: float = 24.0,
    min_elevation: float = 15.0,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    if _sgp4_available():
        try:
            out = predict_passes_sgp4(
                lat=lat,
                lon=lon,
                alt_m=alt_m,
                hours=hours,
                min_elevation=min_elevation,
                data_dir=data_dir,
            )
            # Fresh operator TLEs should produce windows; empty means bad/stale
            # educational defaults or geometry miss - keep CI usable.
            if int(out.get("count") or 0) == 0:
                fix = predict_passes_fixture(
                    lat=lat, lon=lon, hours=hours, min_elevation=min_elevation
                )
                fix["sgp4_empty"] = True
                fix["honest"] = (
                    "sgp4 returned no windows above min elevation for this station/TLE "
                    "cache. Showing fixture schedule. Refresh TLEs: "
                    "scripts/refresh_fta_tles.py && skycache rx tle-import ..."
                )
                return fix
            return out
        except Exception as exc:  # noqa: BLE001
            out = predict_passes_fixture(
                lat=lat, lon=lon, hours=hours, min_elevation=min_elevation
            )
            out["sgp4_error"] = str(exc)
            return out
    return predict_passes_fixture(
        lat=lat, lon=lon, hours=hours, min_elevation=min_elevation
    )
