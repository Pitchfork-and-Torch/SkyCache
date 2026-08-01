"""Disaster Drill Ops (v1.12.0): doctor, lab run, printable report, closeout, kit.

Elevates emergency/health on local fabric. Not free Starlink. Not satellite TX.
Turn Disaster mode OFF after every real exercise.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.nexus.field_mesh_ops import run_disaster_drill

HONEST = (
    "Disaster drill: prioritizes emergency/health on local mesh and mule paths only. "
    "Not free Starlink, not satellite uplink, not commercial decrypt. "
    "Always turn Disaster mode OFF after the exercise."
)

DOCTOR_SCHEMA = "skycache.disaster.doctor.v1"
RUN_SCHEMA = "skycache.disaster.run.v1"
REPORT_SCHEMA = "skycache.disaster.report.v1"
CLOSEOUT_SCHEMA = "skycache.disaster.closeout.v1"
KIT_SCHEMA = "skycache.disaster.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def disaster_doctor(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Readiness for a lab or partner disaster drill (non-destructive)."""
    from skycache.capabilities.handoff_ops import handoff_doctor
    from skycache.nexus.field_mesh_ops import mesh_doctor

    settings = _settings(data_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    content = settings.content_dir
    pkgs = (
        [p.name for p in content.iterdir() if p.is_dir() and (p / "manifest.json").is_file()]
        if content.is_dir()
        else []
    )
    emerg = [p for p in pkgs if "emergency" in p.lower() or "health" in p.lower()]
    add("packages", len(pkgs) >= 1, f"{len(pkgs)} packages", 12)
    add(
        "priority_packs",
        len(emerg) >= 1 or len(pkgs) >= 1,
        f"{len(emerg)} emergency/health-named packs (samples OK)",
        10,
    )

    try:
        hd = handoff_doctor(data_dir=settings.data_dir)
        add("handoff", bool(hd.get("go_phone_path")), f"go_phone={hd.get('go_phone_path')}", 12)
    except Exception as exc:  # noqa: BLE001
        add("handoff", False, str(exc), 12)

    try:
        md = mesh_doctor(data_dir=settings.data_dir, repo_root=repo_root)
        add("mesh_sim", bool(md.get("go_sim_mesh")), f"go_sim_mesh={md.get('go_sim_mesh')}", 12)
    except Exception as exc:  # noqa: BLE001
        add("mesh_sim", False, str(exc), 12)

    drill_doc = repo_root / "docs" / "disaster-drill.md"
    add("playbook", drill_doc.is_file(), str(drill_doc) if drill_doc.is_file() else "missing docs", 10)

    last = settings.data_dir / "ops" / "disaster-drill-last.json"
    add(
        "prior_receipt",
        True,
        "prior lab receipt present" if last.is_file() else "no prior receipt (ok first run)",
        5,
    )

    # Disaster mode should be OFF between drills
    disaster_on = bool(getattr(settings, "disaster_mode", False))
    add(
        "disaster_off_default",
        not disaster_on,
        "disaster_mode OFF (good)" if not disaster_on else "disaster_mode ON - turn OFF after drills",
        12,
    )

    add("lab_sim_path", True, "skycache disaster run --nodes 3 always available", 10)

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_lab = len(pkgs) >= 1 and score >= 60
    go_partner = go_lab and drill_doc.is_file() and not disaster_on

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_lab_drill": go_lab,
        "go_partner_drill": go_partner,
        "package_count": len(pkgs),
        "disaster_mode_now": disaster_on,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache disaster doctor",
            "skycache disaster run --nodes 3",
            "skycache disaster report --out data/ops/disaster-report.html",
            "skycache disaster closeout",
            "skycache disaster kit --out data/disaster-kit",
            "Field: follow docs/disaster-drill.md; disable disaster mode after",
        ],
        "legal": (
            "Lab sim and local mesh/mule only. No satellite TX. No free commercial broadband claims."
        ),
    }


def disaster_run(
    *,
    data_dir: Path | None = None,
    nodes: int = 3,
    keep: bool = False,
) -> dict[str, Any]:
    """Lab disaster priority flood + receipt (wraps mesh disaster-drill)."""
    settings = _settings(data_dir)
    receipt = run_disaster_drill(nodes=nodes, data_dir=settings.data_dir, keep=keep)
    return {
        "schema": RUN_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "ok": bool(receipt.get("ok")),
        "receipt": receipt,
        "banner": HONEST,
        "reminder": "Lab only. After any real field drill: skycache disaster closeout",
    }


def write_disaster_report_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    run_lab: bool = False,
    nodes: int = 3,
) -> dict[str, Any]:
    """Printable HTML disaster drill report for partners."""
    settings = _settings(data_dir)
    if run_lab:
        disaster_run(data_dir=settings.data_dir, nodes=nodes)
    last_path = settings.data_dir / "ops" / "disaster-drill-last.json"
    last: dict[str, Any] = {}
    if last_path.is_file():
        try:
            last = json.loads(last_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            last = {}
    doc = disaster_doctor(data_dir=settings.data_dir)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache disaster drill report</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:42rem;margin:1.5rem auto;padding:0 1rem;line-height:1.45;color:#0f172a}}
.banner{{background:#fef3c7;border:1px solid #f59e0b;padding:.75rem;border-radius:8px;font-size:.9rem;margin-bottom:1rem}}
h1{{font-size:1.35rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{border:1px solid #cbd5e1;padding:.4rem .55rem;text-align:left}}
.ok{{color:#047857;font-weight:700}}
.legal{{color:#64748b;font-size:.8rem;margin-top:1.5rem}}
@media print {{ .noprint {{ display:none }} }}
</style>
</head>
<body>
<div class="banner">{HONEST}</div>
<h1>Disaster drill report</h1>
<p>Software v{__version__} · Generated {_iso_now()}</p>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>go_lab_drill</td><td>{doc.get("go_lab_drill")}</td></tr>
<tr><td>go_partner_drill</td><td>{doc.get("go_partner_drill")}</td></tr>
<tr><td>doctor score</td><td>{doc.get("score")}</td></tr>
<tr><td>lab receipt ok</td><td class="ok">{last.get("ok")}</td></tr>
<tr><td>lab nodes</td><td>{last.get("nodes")}</td></tr>
<tr><td>lab generated_at</td><td>{last.get("generated_at")}</td></tr>
<tr><td>disaster_mode_now</td><td>{doc.get("disaster_mode_now")}</td></tr>
</table>
<h2>Closeout (mandatory)</h2>
<ol>
<li>Confirm Disaster mode is <strong>OFF</strong> on every live node</li>
<li>Log date, operators, legal_rf_mode, pass/fail in site logbook</li>
<li>Optional: partner pilot-report validate</li>
<li>Store this HTML with the USB kit</li>
</ol>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<p class="legal">Local knowledge only. Not free commercial broadband. Not a substitute for professional emergency services.</p>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {
        "schema": REPORT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "path": str(out_path),
        "lab_ok": last.get("ok"),
        "banner": HONEST,
    }


def disaster_closeout(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Post-drill checks: receipt present, disaster mode should be OFF."""
    settings = _settings(data_dir)
    last_path = settings.data_dir / "ops" / "disaster-drill-last.json"
    last: dict[str, Any] | None = None
    if last_path.is_file():
        try:
            last = json.loads(last_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            last = None
    disaster_on = bool(getattr(settings, "disaster_mode", False))
    ok = (not disaster_on) and bool(last and last.get("ok"))
    receipt = {
        "schema": CLOSEOUT_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "ok": ok,
        "disaster_mode_off": not disaster_on,
        "lab_receipt_ok": bool(last and last.get("ok")),
        "lab_receipt_path": str(last_path) if last_path.is_file() else None,
        "actions": [
            "Disable disaster mode via admin or POST /api/admin/disaster {enabled:false}",
            "Confirm mesh peers back to normal priority",
            "Archive disaster-report.html with partner logs",
        ],
        "banner": HONEST,
    }
    out = settings.data_dir / "ops" / "disaster-closeout-last.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt["written"] = str(out)
    return receipt


def write_disaster_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
    run_lab: bool = False,
) -> dict[str, Any]:
    """Kit: doctor, report, playbook copy, checklist, zip."""
    settings = _settings(data_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = disaster_doctor(data_dir=settings.data_dir, repo_root=repo_root)
    (out_dir / "disaster-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    if run_lab or not (settings.data_dir / "ops" / "disaster-drill-last.json").is_file():
        disaster_run(data_dir=settings.data_dir, nodes=3)

    write_disaster_report_html(
        out_dir / "disaster-report.html",
        data_dir=settings.data_dir,
        run_lab=False,
    )
    close = disaster_closeout(data_dir=settings.data_dir)
    (out_dir / "disaster-closeout.json").write_text(
        json.dumps(close, indent=2) + "\n", encoding="utf-8"
    )

    docs_dir = out_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    for name in ("disaster-drill.md", "mesh-field-checklist.md", "threat-model.md"):
        src = repo_root / "docs" / name
        if src.is_file():
            (docs_dir / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    (out_dir / "README.md").write_text(
        f"""# Disaster drill kit

{HONEST}

## Commands

```text
skycache disaster doctor
skycache disaster run --nodes 3
skycache disaster report --out data/ops/disaster-report.html
skycache disaster closeout
skycache disaster kit --out data/disaster-kit
```

## Field

Follow docs/disaster-drill.md. Always disable disaster mode after.

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Disaster drill field checklist

{HONEST}

- [ ] Brief partners: local knowledge only, not free internet
- [ ] disaster doctor go_lab_drill true
- [ ] Lab: disaster run --nodes 3 (or field script)
- [ ] Mule/handoff path demonstrated if mesh down
- [ ] disaster closeout (mode OFF)
- [ ] Print disaster-report.html for partner file
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
                "download_hint": "/downloads/skycache-disaster-kit.zip",
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
        "go_lab_drill": doc.get("go_lab_drill"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
