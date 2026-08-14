"""SDR / SatDump environment doctor for live FTA ops."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _which(names: list[str]) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def _windows_extra_dirs() -> list[Path]:
    """Common install locations when tools are not yet on PATH."""
    dirs: list[Path] = []
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    home = Path.home()
    for base in (
        Path(pf) / "SatDump" / "bin",
        Path(pf) / "SatDump",
        Path(pfx86) / "SatDump" / "bin",
        Path(pfx86) / "SatDump",
        Path(local) / "Programs" / "SatDump" / "bin" if local else None,
        Path(local) / "Programs" / "SatDump" if local else None,
        Path(r"C:\SatDump\bin"),
        Path(r"C:\SatDump"),
        home / "SkyCache" / "tools" / "rx-windows" / "rtlsdr",
        home / "SkyCache" / "tools" / "rx-windows",
        Path.cwd() / "tools" / "rx-windows" / "rtlsdr",
        Path.cwd() / "tools" / "rx-windows",
    ):
        if base is not None:
            dirs.append(base)
    env_extra = os.environ.get("SKYCACHE_RX_TOOLS", "").strip()
    if env_extra:
        for part in env_extra.split(os.pathsep):
            p = part.strip()
            if p:
                dirs.append(Path(p))
    return dirs


def _resolve(names: list[str], *, extra_dirs: list[Path] | None = None) -> str | None:
    hit = _which(names)
    if hit:
        return hit
    for d in extra_dirs or []:
        if not d.is_dir():
            continue
        for n in names:
            for cand in (d / n, d / f"{n}.exe", d / "bin" / n, d / "bin" / f"{n}.exe"):
                if cand.is_file():
                    return str(cand.resolve())
    return None


def _run(cmd: list[str], *, timeout: float = 8.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:2000],
            "stderr": (proc.stderr or "")[:1000],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _satdump_probe(path: str) -> dict[str, Any]:
    """SatDump prints usage to stderr and often exits non-zero without args."""
    raw = _run([path], timeout=6.0)
    blob = f"{raw.get('stdout') or ''}{raw.get('stderr') or ''}{raw.get('error') or ''}"
    looks_like = any(
        token in blob.lower()
        for token in ("pipeline", "satdump", "usage", "samplerate", "baseband")
    )
    raw["runs"] = looks_like or "error" not in raw
    raw["ok"] = bool(looks_like)
    return raw


def rx_doctor_report(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Inventory RX tools and devices. Never claims commercial broadband capability."""
    extra = _windows_extra_dirs() if os.name == "nt" else [
        Path.cwd() / "tools" / "rx-windows" / "rtlsdr",
        Path.home() / "SkyCache" / "tools" / "rx-windows" / "rtlsdr",
    ]
    env_extra = os.environ.get("SKYCACHE_RX_TOOLS", "").strip()
    if env_extra:
        for part in env_extra.split(os.pathsep):
            p = part.strip()
            if p:
                extra.append(Path(p))

    tools = {
        "satdump": _resolve(["satdump", "satdump_cli"], extra_dirs=extra),
        "rtl_test": _resolve(["rtl_test"], extra_dirs=extra),
        "rtl_fm": _resolve(["rtl_fm"], extra_dirs=extra),
        "rtl_sdr": _resolve(["rtl_sdr"], extra_dirs=extra),
        "SoapySDRUtil": _resolve(["SoapySDRUtil"], extra_dirs=extra),
        "gr_satellites": _resolve(["gr_satellites", "gr-satellites"], extra_dirs=extra),
        "gqrx": _resolve(["gqrx"], extra_dirs=extra),
    }
    probes: dict[str, Any] = {}
    if tools["rtl_test"]:
        probes["rtl_test"] = _run([tools["rtl_test"], "-t"], timeout=6.0)
    if tools["SoapySDRUtil"]:
        probes["soapy_find"] = _run([tools["SoapySDRUtil"], "--find"], timeout=10.0)
    if tools["satdump"]:
        probes["satdump"] = _satdump_probe(tools["satdump"])

    # Decode path: SatDump present (built-in RTL/Soapy drivers). Hardware probe is optional.
    ready_decode = bool(tools["satdump"])
    # Full live stack helpers: SatDump + at least one RTL/Soapy CLI for device checks.
    ready_live = bool(
        tools["satdump"]
        and (tools["rtl_test"] or tools["SoapySDRUtil"] or tools["rtl_sdr"])
    )
    device_seen = False
    rtl_probe = probes.get("rtl_test") or {}
    blob = f"{rtl_probe.get('stdout') or ''}{rtl_probe.get('stderr') or ''}".lower()
    if tools["rtl_test"] and "no supported devices" not in blob and "error" not in rtl_probe:
        if rtl_probe.get("ok") or "found" in blob or "sn:" in blob:
            device_seen = True
    ready_import = True  # always can import products without SDR

    station = None
    if data_dir:
        sp = Path(data_dir) / "rx" / "station.json"
        if sp.is_file():
            try:
                station = json.loads(sp.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                station = {"error": "unreadable station.json"}

    next_steps: list[str] = []
    if not tools["satdump"]:
        next_steps.append(
            "Install SatDump: powershell -File scripts/Install-RxTools-Windows.ps1"
        )
    if not (tools["rtl_test"] or tools["rtl_sdr"]):
        next_steps.append(
            "Install rtl-sdr CLI tools (same Install-RxTools-Windows.ps1) or radioconda"
        )
    if tools["satdump"] and not device_seen:
        next_steps.append(
            "Plug in RTL-SDR (Zadig WinUSB if Windows lists Bulk-In, Interface 0)"
        )
    next_steps.extend(
        [
            "skycache rx station --lat LAT --lon LON --alt-m ALT",
            "Point SatDump products to data/satdump-products then: "
            "skycache rx watch --dir data/satdump-products --once",
            "skycache rx log --satellite NOAA-18 --elevation 42 --quality good",
        ]
    )

    return {
        "schema": "skycache.rx.doctor.v1",
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "tools": tools,
        "probes": probes,
        "ready": {
            "product_import": ready_import,
            "live_decode_path": ready_decode,
            "live_hardware_path": ready_live,
            "rtl_device_seen": device_seen,
            "amsat_path": bool(tools["gr_satellites"]),
        },
        "station": station,
        "legal": {
            "mode": "receive_only",
            "allowed": "unencrypted free-to-air weather + open amateur telemetry",
            "forbidden": "commercial constellation decryption / Starlink-class broadband clients",
        },
        "next_steps": next_steps,
        "honest": (
            "SkyCache orchestrates legal open RX products; SatDump/gr-satellites do demodulation. "
            "No commercial broadband claims. rtl_device_seen requires a physical RTL-SDR."
        ),
    }
