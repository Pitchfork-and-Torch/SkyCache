"""Capabilities Ops (v1.15.0): doctor, matrix status, printable export, kit.

First-run and partner legal self-audit of what this node may do.
Not free commercial broadband. Never commercial constellation decrypt.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.capabilities.matrix import build_capability_matrix
from skycache.capabilities.modes import LegalRfMode

HONEST = (
    "Capabilities ops: legal self-audit of what this node may do. "
    "Open decode, open corpora, unlicensed mesh, optional amateur by operator. "
    "Never commercial constellation piracy or default satellite uplink. Not free Starlink."
)

DOCTOR_SCHEMA = "skycache.capabilities.doctor.v1"
STATUS_SCHEMA = "skycache.capabilities.status.v1"
EXPORT_SCHEMA = "skycache.capabilities.export.v1"
KIT_SCHEMA = "skycache.capabilities.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _matrix(settings, *, sim: bool = False):
    works = 0
    try:
        from skycache.skybrary.catalog import SkybraryCatalog

        sky = SkybraryCatalog(settings.skybrary_db_path)
        try:
            works = sky.count()
        finally:
            sky.close()
    except Exception:  # noqa: BLE001
        works = 0
    return build_capability_matrix(
        legal_rf_mode=settings.legal_rf_mode,
        sim_mode=bool(settings.sim_mode or sim),
        amateur_license_affirmed=bool(settings.amateur_license_affirmed),
        nexus_enabled=bool(settings.nexus_enabled),
        skybrary_works=works,
    )


def capabilities_status(*, data_dir: Path | None = None, sim: bool = False) -> dict[str, Any]:
    settings = _settings(data_dir)
    matrix = _matrix(settings, sim=sim)
    d = matrix.to_dict()
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        **d,
    }


def capabilities_doctor(*, data_dir: Path | None = None, sim: bool = False) -> dict[str, Any]:
    """Legal onboarding readiness: mode set, matrix builds, banned list present."""
    settings = _settings(data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    mode_ok = False
    mode = settings.legal_rf_mode or ""
    try:
        LegalRfMode(str(mode))
        mode_ok = True
    except Exception:  # noqa: BLE001
        mode_ok = False
    add("legal_rf_mode", mode_ok, f"legal_rf_mode={mode}", 18)

    matrix = _matrix(settings, sim=sim)
    d = matrix.to_dict()
    enabled = int((d.get("summary") or {}).get("enabled") or 0)
    total = int((d.get("summary") or {}).get("total") or 0)
    add("matrix_built", total >= 5, f"{enabled}/{total} capabilities enabled", 20)
    add("banned_list", bool(d.get("banned")), f"{len(d.get('banned') or [])} banned items", 12)
    add(
        "nexus_flag",
        True,
        f"nexus_enabled={settings.nexus_enabled}",
        8,
    )
    add(
        "sim_aware",
        True,
        f"sim_mode={settings.sim_mode or sim}",
        6,
    )

    # First-boot PIN should not be default for field (soft check)
    pin = settings.admin_pin or ""
    add(
        "admin_pin_changed",
        pin not in {"", "2468", "0000", "1234"},
        "admin PIN non-default" if pin not in {"", "2468", "0000", "1234"} else "change default admin PIN before field",
        12,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_onboard = mode_ok and total >= 5
    go_field = go_onboard and pin not in {"", "2468", "0000", "1234"}

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_capabilities_onboard": go_onboard,
        "go_capabilities_field": go_field,
        "legal_rf_mode": mode,
        "summary": d.get("summary"),
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache capabilities doctor",
            "skycache capabilities status",
            "skycache capabilities export --out data/ops/capabilities-matrix.html",
            "skycache capabilities kit --out data/capabilities-kit",
            "Review banned list with local maintainer before RF day",
        ],
        "legal": "Receive-only satellite; unlicensed mesh TX only; open content only",
    }


def export_capabilities_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    sim: bool = False,
) -> dict[str, Any]:
    """Printable HTML capability matrix for onboarding wall / partners."""
    settings = _settings(data_dir)
    matrix = _matrix(settings, sim=sim)
    d = matrix.to_dict()
    rows = []
    for c in d.get("capabilities") or []:
        on = "ON" if c.get("enabled") else "off"
        rows.append(
            "<tr>"
            f"<td>{_esc(on)}</td>"
            f"<td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('title'))}</td>"
            f"<td>{_esc(c.get('status'))}</td>"
            f"<td>{_esc(c.get('legal_basis'))}</td>"
            f"<td>{_esc(c.get('how'))}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='6'>(empty)</td></tr>"
    banned = "".join(f"<li>{_esc(b)}</li>" for b in (d.get("banned") or [])) or "<li>(none listed)</li>"
    summary = d.get("summary") or {}
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache legal capabilities</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:52rem;margin:1.25rem auto;padding:0 1rem;line-height:1.4;color:#0f172a}}
.banner{{background:#ecfeff;border:1px solid #a5f3fc;padding:.75rem;border-radius:8px;font-size:.9rem;margin-bottom:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.8rem}}
th,td{{border:1px solid #cbd5e1;padding:.35rem .45rem;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}}
.meta{{color:#64748b;font-size:.85rem}}
@media print{{.noprint{{display:none}}}}
</style>
</head>
<body>
<div class="banner">{_esc(HONEST)}</div>
<h1>Legal capability matrix</h1>
<p class="meta">Software v{__version__} · {_iso_now()} · legal_rf_mode=<strong>{_esc(d.get('legal_rf_mode'))}</strong>
 · enabled {summary.get('enabled')}/{summary.get('total')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<table>
<thead><tr><th>On</th><th>ID</th><th>Title</th><th>Status</th><th>Legal basis</th><th>How</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
<h2>Banned / never</h2>
<ul>{banned}</ul>
<p class="meta">Modes: {", ".join(m.value for m in LegalRfMode)}</p>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {
        "schema": EXPORT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "path": str(out_path),
        "summary": summary,
        "banner": HONEST,
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_capabilities_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    sim: bool = False,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = capabilities_doctor(data_dir=settings.data_dir, sim=sim)
    (out_dir / "capabilities-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = capabilities_status(data_dir=settings.data_dir, sim=sim)
    (out_dir / "capabilities-matrix.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_capabilities_html(
        out_dir / "capabilities-matrix.html",
        data_dir=settings.data_dir,
        sim=sim,
    )

    (out_dir / "README.md").write_text(
        f"""# Capabilities kit

{HONEST}

## Commands

```text
skycache capabilities doctor
skycache capabilities status
skycache capabilities export --out data/ops/capabilities-matrix.html
skycache capabilities kit --out data/capabilities-kit
```

## First-run

1. Set legal_rf_mode (receive_only | ism_mesh | ...)
2. Review ON/off matrix with local maintainer
3. Change default admin PIN
4. Print capabilities-matrix.html for the wall

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Capabilities field checklist

{HONEST}

- [ ] legal_rf_mode documented for this site
- [ ] capabilities doctor go_capabilities_onboard true
- [ ] banned list read aloud to team
- [ ] admin PIN not 2468/0000/1234
- [ ] printed matrix posted near the node
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
                "download_hint": "/downloads/skycache-capabilities-kit.zip",
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
        "go_capabilities_onboard": doc.get("go_capabilities_onboard"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
