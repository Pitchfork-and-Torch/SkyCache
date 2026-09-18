"""Node Report Ops (v1.18.0): doctor rollup, status, printable passport, kit.

One partner-facing readiness passport across ops surfaces.
Not free commercial broadband. Fleet heartbeat remains default OFF.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from skycache import __version__

HONEST = (
    "Node report ops: one printable readiness passport for partners and maintainers. "
    "Rolls up local ops, capabilities, licenses, power, integrity, RX, mesh-adjacent gates. "
    "Fleet heartbeat remains default OFF. Not free commercial broadband."
)

DOCTOR_SCHEMA = "skycache.report.doctor.v1"
STATUS_SCHEMA = "skycache.report.status.v1"
EXPORT_SCHEMA = "skycache.report.export.v1"
KIT_SCHEMA = "skycache.report.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _safe(fn: Callable[[], dict[str, Any]], label: str) -> dict[str, Any]:
    try:
        return {"ok": True, "label": label, "report": fn()}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "label": label, "error": str(exc), "report": {}}


def _collect(data_dir: Path) -> dict[str, dict[str, Any]]:
    """Run sibling doctors; never raise out."""
    out: dict[str, dict[str, Any]] = {}

    def add(key: str, label: str, fn: Callable[[], dict[str, Any]]) -> None:
        out[key] = _safe(fn, label)

    add(
        "local",
        "Local ops",
        lambda: __import__("skycache.ops.local_ops", fromlist=["ops_doctor"]).ops_doctor(
            data_dir=data_dir
        ),
    )
    add(
        "capabilities",
        "Capabilities",
        lambda: __import__(
            "skycache.ops.capabilities_ops", fromlist=["capabilities_doctor"]
        ).capabilities_doctor(data_dir=data_dir, sim=True),
    )
    add(
        "licenses",
        "Licenses",
        lambda: __import__(
            "skycache.ops.licenses_ops", fromlist=["licenses_doctor"]
        ).licenses_doctor(data_dir=data_dir),
    )
    add(
        "power",
        "Power",
        lambda: __import__("skycache.ops.power_ops", fromlist=["power_doctor"]).power_doctor(
            data_dir=data_dir
        ),
    )
    add(
        "integrity",
        "Integrity",
        lambda: __import__(
            "skycache.ops.integrity_ops", fromlist=["integrity_doctor"]
        ).integrity_doctor(data_dir=data_dir),
    )
    add(
        "rx",
        "RX",
        lambda: __import__("skycache.ops.rx_ops", fromlist=["rx_ops_doctor"]).rx_ops_doctor(
            data_dir=data_dir
        ),
    )
    add(
        "disaster",
        "Disaster",
        lambda: __import__(
            "skycache.ops.disaster_ops", fromlist=["disaster_doctor"]
        ).disaster_doctor(data_dir=data_dir),
    )
    add(
        "village_day",
        "Village day",
        lambda: __import__(
            "skycache.ops.village_day_ops", fromlist=["village_day_doctor"]
        ).village_day_doctor(data_dir=data_dir),
    )
    return out


def _gate(key: str, rep: dict[str, Any], field: str) -> bool | None:
    if not rep.get("ok"):
        return None
    r = rep.get("report") or {}
    if field not in r:
        return None
    return bool(r.get(field))


def report_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    settings = _settings(data_dir)
    surfaces = _collect(settings.data_dir)
    gates: list[dict[str, Any]] = []
    mapping = [
        ("local", "go_local_lab", "Local lab metrics (fleet OFF)"),
        ("capabilities", "go_capabilities_onboard", "Legal capabilities onboard"),
        ("licenses", "go_licenses_inventory", "License inventory present"),
        ("power", "go_power_lab", "Power guidance path"),
        ("integrity", "go_integrity_sim", "Integrity verify path"),
        ("rx", "go_rx_lab", "RX product-import path"),
        ("disaster", "go_lab_drill", "Disaster lab drill path"),
        ("village_day", "go_weekend_sim", "Village-day weekend sim"),
    ]
    for key, field, title in mapping:
        g = _gate(key, surfaces[key], field)
        gates.append(
            {
                "surface": key,
                "title": title,
                "field": field,
                "go": g,
                "available": surfaces[key].get("ok"),
                "score": (surfaces[key].get("report") or {}).get("score"),
            }
        )

    known = [g for g in gates if g["go"] is not None]
    go_n = sum(1 for g in known if g["go"])
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "gates": gates,
        "summary": {
            "gates_total": len(known),
            "gates_go": go_n,
            "gates_no": len(known) - go_n,
            "surfaces_ok": sum(1 for s in surfaces.values() if s.get("ok")),
            "surfaces_total": len(surfaces),
        },
        "surfaces": {
            k: {
                "ok": v.get("ok"),
                "error": v.get("error"),
                "score": (v.get("report") or {}).get("score"),
                "schema": (v.get("report") or {}).get("schema"),
            }
            for k, v in surfaces.items()
        },
        "legal": "Receive-only satellite; unlicensed mesh TX; open content; fleet heartbeat OFF by default",
    }


def report_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    settings = _settings(data_dir)
    st = report_status(data_dir=settings.data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    summary = st.get("summary") or {}
    for g in st.get("gates") or []:
        go = g.get("go")
        # Missing optional surface does not fail hard; soft pass when unavailable
        ok = True if go is None else bool(go)
        add(
            f"gate_{g.get('surface')}",
            ok,
            f"{g.get('field')}={go} score={g.get('score')}",
            12 if g.get("surface") in {"local", "capabilities", "rx"} else 8,
        )

    add(
        "rollup_built",
        int(summary.get("surfaces_ok") or 0) >= 4,
        f"surfaces_ok={summary.get('surfaces_ok')}/{summary.get('surfaces_total')}",
        14,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))

    # Core lab readiness: local + capabilities + rx lab (product import)
    core_keys = {"local", "capabilities", "rx"}
    core_ok = True
    for g in st.get("gates") or []:
        if g.get("surface") in core_keys and g.get("go") is False:
            core_ok = False
    go_partner_review = core_ok and int(summary.get("gates_go") or 0) >= 4
    go_field_pack = go_partner_review and score >= 75

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_partner_review": go_partner_review,
        "go_field_pack": go_field_pack,
        "summary": summary,
        "gates": st.get("gates"),
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache report doctor",
            "skycache report status",
            "skycache report export --out data/ops/node-report.html",
            "skycache report kit --out data/report-kit",
            "Fix failing gates with surface doctors (ops / capabilities / rx / ...)",
        ],
        "legal": st.get("legal"),
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_report_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    settings = _settings(data_dir)
    doc = report_doctor(data_dir=settings.data_dir)
    st = report_status(data_dir=settings.data_dir)
    rows = []
    for g in st.get("gates") or []:
        go = g.get("go")
        mark = "n/a" if go is None else ("GO" if go else "NO")
        rows.append(
            "<tr>"
            f"<td>{_esc(mark)}</td>"
            f"<td>{_esc(g.get('title'))}</td>"
            f"<td><code>{_esc(g.get('field'))}</code></td>"
            f"<td>{_esc(g.get('score'))}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='4'>(empty)</td></tr>"
    summary = st.get("summary") or {}

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache node readiness report</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:48rem;margin:1.25rem auto;padding:0 1rem;line-height:1.4;color:#0f172a}}
.banner{{background:#ecfeff;border:1px solid #a5f3fc;padding:.75rem;border-radius:8px;font-size:.9rem;margin-bottom:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.85rem;margin:.75rem 0}}
th,td{{border:1px solid #cbd5e1;padding:.35rem .45rem;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}}
.meta{{color:#64748b;font-size:.85rem}}
@media print{{.noprint{{display:none}}}}
</style>
</head>
<body>
<div class="banner">{_esc(HONEST)}</div>
<h1>Node readiness report</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score <strong>{doc.get('score')}</strong>
 · go_partner_review={doc.get('go_partner_review')}
 · go_field_pack={doc.get('go_field_pack')}</p>
<p class="meta">Gates GO {summary.get('gates_go')}/{summary.get('gates_total')}
 · surfaces OK {summary.get('surfaces_ok')}/{summary.get('surfaces_total')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<table>
<thead><tr><th>Gate</th><th>Surface</th><th>Field</th><th>Score</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
<p class="meta">Legal: {_esc(st.get('legal'))}</p>
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
        "score": doc.get("score"),
        "go_partner_review": doc.get("go_partner_review"),
        "banner": HONEST,
    }


def write_report_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = report_doctor(data_dir=settings.data_dir)
    (out_dir / "report-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = report_status(data_dir=settings.data_dir)
    (out_dir / "report-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_report_html(out_dir / "node-report.html", data_dir=settings.data_dir)

    (out_dir / "README.md").write_text(
        f"""# Node report kit

{HONEST}

## Commands

```text
skycache report doctor
skycache report status
skycache report export --out data/ops/node-report.html
skycache report kit --out data/report-kit
```

## Partner use

Print node-report.html (browser Save as PDF) before pilot files or ministry demos.

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Node report field checklist

{HONEST}

- [ ] report doctor go_partner_review true
- [ ] core gates: local, capabilities, rx lab
- [ ] licenses inventory if packs will leave the building
- [ ] fleet heartbeat still OFF
- [ ] PDF archived with partner pilot files
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
                "download_hint": "/downloads/skycache-report-kit.zip",
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
        "go_partner_review": doc.get("go_partner_review"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
