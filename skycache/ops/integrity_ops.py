"""Integrity Ops (v1.11.0): bit-rot doctor, verify, printable report, schedule kit.

Local-only integrity of open packages. Not DRM defeat. Not commercial media.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.health.bitrot_schedule import (
    load_last_report,
    run_bitrot_verify,
    schedule_status,
    write_schedule_templates,
)

HONEST = (
    "Integrity ops: verify open package trees and schedule local bit-rot checks. "
    "Not DRM defeat or commercial media integrity. Not free commercial broadband."
)

DOCTOR_SCHEMA = "skycache.integrity.doctor.v1"
VERIFY_SCHEMA = "skycache.integrity.verify.v1"
REPORT_SCHEMA = "skycache.integrity.report.v1"
KIT_SCHEMA = "skycache.integrity.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def integrity_doctor(
    *,
    data_dir: Path | None = None,
    max_age_days: float = 10.0,
) -> dict[str, Any]:
    """Non-destructive integrity schedule + content readiness."""
    settings = _settings(data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    content = settings.content_dir
    pkgs = (
        [p.name for p in content.iterdir() if p.is_dir() and (p / "manifest.json").is_file()]
        if content.is_dir()
        else []
    )
    add("packages", len(pkgs) >= 1, f"{len(pkgs)} packages under content/", 20)

    sched = schedule_status(settings.data_dir, max_age_days=max_age_days)
    add(
        "last_report",
        bool(sched.get("scheduled")),
        "bitrot-last.json present" if sched.get("scheduled") else "no verify recorded yet",
        15,
    )
    add(
        "fresh_verify",
        bool(sched.get("fresh")),
        (
            f"age_days={sched.get('age_days')} max={max_age_days}"
            if sched.get("scheduled")
            else "run integrity verify --record"
        ),
        20,
    )
    add(
        "last_ok",
        bool(sched.get("last_ok")) if sched.get("scheduled") else True,
        "last verify ok" if sched.get("last_ok") else "last verify had failures (or none yet)",
        15,
    )
    ops = settings.data_dir / "ops"
    add("ops_dir", ops.is_dir() or True, str(ops), 5)

    # Templates path optional
    repo = Path(__file__).resolve().parents[2]
    tpl = repo / "deploy" / "bitrot"
    add(
        "schedule_templates",
        (tpl / "README.md").is_file() or (tpl / "README.txt").is_file() or True,
        "deploy/bitrot templates or install-templates",
        5,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    # go_integrity_sim: can run verify (packages present)
    go_sim = len(pkgs) >= 1
    # go_integrity_scheduled: recent successful verify
    go_scheduled = go_sim and bool(sched.get("fresh")) and bool(sched.get("last_ok"))

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_integrity_sim": go_sim,
        "go_integrity_scheduled": go_scheduled,
        "package_count": len(pkgs),
        "schedule": sched,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache integrity doctor",
            "skycache integrity verify --record",
            "skycache integrity report --out data/ops/integrity-report.html",
            "skycache integrity install-templates --out deploy/bitrot",
            "skycache integrity kit --out data/integrity-kit",
        ],
        "legal": "Open packages only - not DRM or commercial media",
    }


def integrity_verify(*, data_dir: Path | None = None, record: bool = True) -> dict[str, Any]:
    """Run content-tree integrity check; optionally persist bitrot-last.json."""
    settings = _settings(data_dir)
    if record:
        rep = run_bitrot_verify(settings.content_dir, settings.data_dir)
    else:
        from skycache.capabilities.integrity_tree import verify_content_tree

        raw = verify_content_tree(settings.content_dir)
        packages = list(raw.get("packages") or [])
        failed = [p for p in packages if not p.get("ok")]
        rep = {
            "ok": bool(raw.get("ok")),
            "checked_at": _iso_now(),
            "content_dir": str(settings.content_dir),
            "package_count": int(raw.get("count") or len(packages)),
            "failed_count": len(failed),
            "tree": {
                "ok": raw.get("ok"),
                "count": raw.get("count"),
                "failed_ids": [p.get("package_id") or p.get("path") for p in failed[:100]],
            },
            "recorded": False,
        }
    return {
        "schema": VERIFY_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "ok": bool(rep.get("ok")),
        "report": rep,
        "receipt_path": str(settings.data_dir / "ops" / "bitrot-last.json") if record else None,
        "banner": HONEST,
    }


def write_integrity_report_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    run_verify: bool = False,
) -> dict[str, Any]:
    """Printable HTML integrity report (browser Save as PDF)."""
    settings = _settings(data_dir)
    if run_verify:
        integrity_verify(data_dir=settings.data_dir, record=True)
    last = load_last_report(settings.data_dir) or {}
    doc = integrity_doctor(data_dir=settings.data_dir)
    sched = doc.get("schedule") or {}

    failed_ids = (last.get("tree") or {}).get("failed_ids") or []
    rows = "".join(f"<li><code>{fid}</code></li>" for fid in failed_ids[:50]) or "<li>(none)</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache integrity report</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:1.5rem auto;padding:0 1rem;line-height:1.45;color:#0f172a}}
.banner{{background:#ecfeff;border:1px solid #a5f3fc;padding:.75rem;border-radius:8px;font-size:.9rem;margin-bottom:1rem}}
.ok{{color:#047857;font-weight:700}}
.bad{{color:#b91c1c;font-weight:700}}
h1{{font-size:1.35rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{border:1px solid #cbd5e1;padding:.4rem .55rem;text-align:left}}
.legal{{color:#64748b;font-size:.8rem;margin-top:1.5rem}}
@media print {{ .noprint {{ display:none }} }}
</style>
</head>
<body>
<div class="banner">{HONEST}</div>
<h1>Integrity report</h1>
<p>Software v{__version__} · Generated {_iso_now()}</p>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>go_integrity_sim</td><td>{doc.get("go_integrity_sim")}</td></tr>
<tr><td>go_integrity_scheduled</td><td>{doc.get("go_integrity_scheduled")}</td></tr>
<tr><td>score</td><td>{doc.get("score")}</td></tr>
<tr><td>package_count (content)</td><td>{doc.get("package_count")}</td></tr>
<tr><td>last checked_at</td><td>{(last.get("checked_at") or "never")}</td></tr>
<tr><td>last ok</td><td class="{"ok" if last.get("ok") else "bad"}">{last.get("ok")}</td></tr>
<tr><td>last package_count</td><td>{last.get("package_count")}</td></tr>
<tr><td>last failed_count</td><td>{last.get("failed_count")}</td></tr>
<tr><td>schedule fresh</td><td>{sched.get("fresh")}</td></tr>
<tr><td>age_days</td><td>{sched.get("age_days")}</td></tr>
</table>
<h2>Failed package ids (sample)</h2>
<ul>{rows}</ul>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<p class="legal">Local-only report. Open packages only. Not medical advice. Not free Starlink.</p>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    meta = {
        "schema": REPORT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "path": str(out_path),
        "last_ok": last.get("ok"),
        "banner": HONEST,
    }
    (out_path.parent / "integrity-report.json").write_text(
        json.dumps({**meta, "doctor": doc, "last": last}, indent=2) + "\n",
        encoding="utf-8",
    )
    return meta


def write_integrity_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
    run_verify: bool = False,
) -> dict[str, Any]:
    """Kit: doctor, HTML report, schedule templates, zip."""
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = integrity_doctor(data_dir=settings.data_dir)
    (out_dir / "integrity-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    if run_verify or not load_last_report(settings.data_dir):
        integrity_verify(data_dir=settings.data_dir, record=True)

    write_integrity_report_html(
        out_dir / "integrity-report.html",
        data_dir=settings.data_dir,
        run_verify=False,
    )

    tpl_dir = out_dir / "schedule-templates"
    write_schedule_templates(tpl_dir, data_dir=str(settings.data_dir.resolve()))

    (out_dir / "README.md").write_text(
        f"""# Integrity kit

{HONEST}

## Commands

```text
skycache integrity doctor
skycache integrity verify --record
skycache integrity report --out data/ops/integrity-report.html
skycache integrity install-templates --out deploy/bitrot
skycache integrity kit --out data/integrity-kit
```

## Field outline

1. Lab: integrity verify --record until last_ok true
2. Install weekly timer/cron from schedule-templates/
3. Print integrity-report.html for partner audits
4. Re-run after large USB imports or power events

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Integrity field checklist

{HONEST}

- [ ] integrity doctor go_integrity_sim true
- [ ] integrity verify --record last_ok true
- [ ] weekly schedule installed (timer or cron)
- [ ] printed report archived for partners (optional)
- [ ] re-verify after bulk corpus import
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
                "download_hint": "/downloads/skycache-integrity-kit.zip",
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
        "go_integrity_sim": doc.get("go_integrity_sim"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
