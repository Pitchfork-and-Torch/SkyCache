"""Power Ops (v1.13.0): doctor, guidance snapshot, maintainer sheet, kit.

Solar/battery village node guidance. Estimates are rough. Not free broadband.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.health.power import get_power_provider, mode_from_soc
from skycache.health.power_guidance import (
    DEFAULT_BATTERY_WH,
    maintainer_power_sheet_html,
    power_guidance,
)

HONEST = (
    "Power ops: rough solar/battery guidance for village nodes. "
    "Estimates are order-of-magnitude only. Nodes fail from power ignorance more often "
    "than from software. Not free commercial broadband."
)

DOCTOR_SCHEMA = "skycache.power.doctor.v1"
STATUS_SCHEMA = "skycache.power.status.v1"
SHEET_SCHEMA = "skycache.power.sheet.v1"
KIT_SCHEMA = "skycache.power.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _battery_wh(settings) -> float:
    return float(getattr(settings, "battery_wh", None) or DEFAULT_BATTERY_WH)


def power_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Current SOC/mode/guidance snapshot."""
    settings = _settings(data_dir)
    provider = get_power_provider(settings.power_provider, settings.mock_battery_percent)
    pct = provider.battery_percent()
    on_ac = provider.is_on_ac()
    mode = mode_from_soc(pct)
    g = power_guidance(pct, mode, on_ac=on_ac, battery_wh=_battery_wh(settings))
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "provider": settings.power_provider,
        "mock_battery_percent": settings.mock_battery_percent,
        "battery_wh": _battery_wh(settings),
        "guidance": g,
        "banner": HONEST,
    }


def power_doctor(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Power path readiness for village solar nodes."""
    settings = _settings(data_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    st = power_status(data_dir=settings.data_dir)
    g = st.get("guidance") or {}
    pct = g.get("percent")
    provider = settings.power_provider

    add(
        "provider_configured",
        bool(provider),
        f"power_provider={provider}",
        12,
    )
    add(
        "soc_readable",
        pct is not None,
        f"SOC={pct}" if pct is not None else "SOC unknown (mock/sysfs/ina219)",
        18,
    )
    add(
        "guidance_block",
        bool(g.get("hours_until_eco")),
        "hours_until_eco present",
        12,
    )
    add(
        "battery_wh",
        _battery_wh(settings) > 0,
        f"battery_wh={_battery_wh(settings)} (calibrate for site)",
        10,
    )

    notes = repo_root / "deploy" / "solar-power-notes.md"
    add("solar_docs", notes.is_file(), str(notes) if notes.is_file() else "missing solar notes", 10)

    # Sheet can always be generated in sim/mock
    add("sheet_path", True, "skycache power sheet always available", 8)

    # Lab path always works with mock
    go_lab = provider in {"mock", "sysfs", "ina219"} and True
    add("lab_path", go_lab, "mock provider OK for classroom demos", 10)

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_field = bool(pct is not None and notes.is_file())

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_power_lab": go_lab and (pct is not None or provider == "mock"),
        "go_power_field": go_field,
        "status": st,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache power doctor",
            "skycache power status",
            "skycache power sheet --out data/ops/power-sheet.html",
            "skycache power kit --out data/power-kit",
            "Calibrate battery_wh for site; prefer sysfs/INA219 over mock in field",
        ],
        "legal": "Guidance only - not electrical code compliance or free broadband",
    }


def write_power_sheet(
    out_path: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Write printable maintainer power sheet HTML to disk."""
    settings = _settings(data_dir)
    st = power_status(data_dir=settings.data_dir)
    g = st["guidance"]
    html = maintainer_power_sheet_html(
        g,
        node_id=settings.node_id or "village-hub",
        hotspot_ssid=settings.hotspot_ssid or "SkyCache-Local",
        version=__version__,
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    meta = {
        "schema": SHEET_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "path": str(out_path),
        "percent": g.get("percent"),
        "mode": g.get("mode"),
        "banner": HONEST,
    }
    (out_path.parent / "power-sheet.json").write_text(
        json.dumps({**meta, "status": st}, indent=2) + "\n", encoding="utf-8"
    )
    return meta


def write_power_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Kit: doctor, sheet, solar notes, zip."""
    settings = _settings(data_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = power_doctor(data_dir=settings.data_dir, repo_root=repo_root)
    (out_dir / "power-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    write_power_sheet(out_dir / "power-sheet.html", data_dir=settings.data_dir)

    notes = repo_root / "deploy" / "solar-power-notes.md"
    if notes.is_file():
        (out_dir / "solar-power-notes.md").write_text(
            notes.read_text(encoding="utf-8"), encoding="utf-8"
        )

    (out_dir / "README.md").write_text(
        f"""# Power kit

{HONEST}

## Commands

```text
skycache power doctor
skycache power status
skycache power sheet --out data/ops/power-sheet.html
skycache power kit --out data/power-kit
```

## Field

1. Calibrate battery_wh for your bank
2. Prefer SKYCACHE_POWER_PROVIDER=sysfs on Linux SBCs
3. Print power-sheet.html for wall mount
4. Weekly: clean panel, check fuse, confirm portal after power events

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Power field checklist

{HONEST}

- [ ] power doctor go_power_lab true
- [ ] SOC readable (mock OK for lab; sysfs/INA219 for field)
- [ ] battery_wh calibrated for site bank
- [ ] power-sheet.html printed and posted
- [ ] solar notes reviewed (fuse, polarity, ventilation)
- [ ] ECO/CRITICAL behavior understood by local maintainer
""",
        encoding="utf-8",
    )
    (out_dir / "HOSTING.json").write_text(
        json.dumps(
            {
                "schema": KIT_SCHEMA,
                "generated_at": _iso_now(),
                "software_version": __version__,
                "banner": HONEST,
                "download_hint": "/downloads/skycache-power-kit.zip",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    zip_path: str | None = None
    if zip_bundle:
        zp = out_dir.parent / f"{out_dir.name}.zip"
        if zp.is_file():
            zp.unlink()
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=f"{out_dir.name}/{f.relative_to(out_dir).as_posix()}")
        zip_path = str(zp)

    return {
        "schema": KIT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "zip": zip_path,
        "go_power_lab": doc.get("go_power_lab"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
