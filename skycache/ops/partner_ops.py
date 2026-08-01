"""Partner Ops (v1.21.0): doctor, status, printable board, ops kit.

Institutional pilot readiness on top of partner_kit readiness/kits.
Not free commercial broadband. Honest scope required on pilot reports.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.partner_kit import (
    build_partner_kit,
    partner_readiness,
)

HONEST = (
    "Partner ops: institutional pilot readiness for NGO, university, and civil protection. "
    "Sim pilots first; field RF optional. Store-and-forward knowledge only. "
    "Not free commercial broadband. Pilot reports must affirm honest_scope_briefed."
)

DOCTOR_SCHEMA = "skycache.partner.doctor.v1"
STATUS_SCHEMA = "skycache.partner.status.v1"
EXPORT_SCHEMA = "skycache.partner.export.v1"
KIT_SCHEMA = "skycache.partner.ops_kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def partner_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Partner pilot readiness (wraps partner_readiness)."""
    base = partner_readiness(data_dir=data_dir)
    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": base.get("score"),
        "go_sim_pilot": base.get("go_sim_pilot"),
        "go_field_rf": base.get("go_field_rf"),
        "checks": base.get("checks"),
        "rx_ready": base.get("rx_ready"),
        "banner": HONEST,
        "honest": base.get("honest"),
        "legal": base.get("legal"),
        "next_steps": list(base.get("next_steps") or [])
        + [
            "skycache partner status",
            "skycache partner export --out data/ops/partner-board.html",
            "skycache partner ops-kit --out data/partner-ops-kit",
            "skycache partner kit --type ngo --zip",
        ],
        "readiness_schema": base.get("schema"),
    }


def partner_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    doc = partner_doctor(data_dir=data_dir)
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "score": doc.get("score"),
        "go_sim_pilot": doc.get("go_sim_pilot"),
        "go_field_rf": doc.get("go_field_rf"),
        "checks": doc.get("checks"),
        "rx_ready": doc.get("rx_ready"),
        "kit_types": ["ngo", "university", "civil-protection"],
        "legal": doc.get("legal"),
        "honest": doc.get("honest"),
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_partner_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Printable partner pilot readiness board."""
    doc = partner_doctor(data_dir=data_dir)
    check_rows = []
    for c in doc.get("checks") or []:
        mark = "OK" if c.get("ok") else "FAIL"
        check_rows.append(
            f"<tr><td>{_esc(mark)}</td><td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('detail'))}</td></tr>"
        )
    checks_body = "\n".join(check_rows) or "<tr><td colspan='3'>(none)</td></tr>"
    ready = doc.get("rx_ready") or {}

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache partner pilot board</title>
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
<h1>Partner pilot readiness</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score <strong>{doc.get('score')}</strong>
 · go_sim_pilot={doc.get('go_sim_pilot')}
 · go_field_rf={doc.get('go_field_rf')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<p class="meta">{_esc(doc.get('honest'))}</p>
<h2>RX ready (optional for sim pilots)</h2>
<table>
<thead><tr><th>Key</th><th>Value</th></tr></thead>
<tbody>
<tr><td>product_import</td><td>{_esc(ready.get('product_import'))}</td></tr>
<tr><td>live_decode_path</td><td>{_esc(ready.get('live_decode_path'))}</td></tr>
<tr><td>rtl_device_seen</td><td>{_esc(ready.get('rtl_device_seen'))}</td></tr>
</tbody>
</table>
<h2>Checks</h2>
<table>
<thead><tr><th>OK</th><th>ID</th><th>Detail</th></tr></thead>
<tbody>
{checks_body}
</tbody>
</table>
<p class="meta">Kits: ngo · university · civil-protection. After field: pilot-report.json with honest_scope_briefed=true.</p>
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
        "go_sim_pilot": doc.get("go_sim_pilot"),
        "banner": HONEST,
    }


def write_partner_ops_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
    include_sample_ngo: bool = True,
) -> dict[str, Any]:
    """Ops kit: doctor, board, checklist, optional sample NGO kit folder."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = partner_doctor(data_dir=data_dir)
    (out_dir / "partner-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = partner_status(data_dir=data_dir)
    (out_dir / "partner-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_partner_html(out_dir / "partner-board.html", data_dir=data_dir)

    sample_meta = None
    if include_sample_ngo:
        sample_meta = build_partner_kit(
            out_dir / "sample-ngo-kit",
            kit_type="ngo",
            make_zip=False,
            include_docs_copy=False,
        )

    (out_dir / "README.md").write_text(
        f"""# Partner ops kit

{HONEST}

## Commands

```text
skycache partner doctor
skycache partner status
skycache partner export --out data/ops/partner-board.html
skycache partner ops-kit --out data/partner-ops-kit
skycache partner kit --type ngo --zip
skycache partner package-all --out data/partner-kits
skycache partner report validate pilot-report.json
```

## Pilot order

1. go_sim_pilot true (classroom)
2. Download type kit from /partners/
3. Field day + honest_scope_briefed
4. Optional go_field_rf after SatDump + station

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Partner pilot field checklist

{HONEST}

- [ ] partner doctor go_sim_pilot true
- [ ] LEGAL-ONE-PAGER + CHECKLIST walked with coordinator
- [ ] no free-Starlink claims in training
- [ ] pilot-report.json honest_scope_briefed true
- [ ] licenses inventory if packs leave the lab
- [ ] optional: go_field_rf only after station + SatDump
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
                "download_hint": "/downloads/skycache-partner-ops-kit.zip",
                "type_kits": {
                    "ngo": "/downloads/partner-kits/skycache-partner-ngo-kit.zip",
                    "university": "/downloads/partner-kits/skycache-partner-university-kit.zip",
                    "civil-protection": "/downloads/partner-kits/skycache-partner-civil-protection-kit.zip",
                },
                "sample_ngo": sample_meta,
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
        "go_sim_pilot": doc.get("go_sim_pilot"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
