"""Seal Ops (v1.20.0): doctor, status, printable board, kit for golden Pi fleets.

Operator-hosted sealed .img.xz only. No multi-GB images in git.
Not free commercial broadband. Never default PIN 2468.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.deploy_pi import (
    HONEST as PI_HONEST,
    bake_plan,
    pi_image_doctor,
    write_bake_artifacts,
    write_seal_checklist,
)

HONEST = (
    "Seal ops: golden village node flash + optional sealed image discipline. "
    "Kit path works on Windows; Linux host for dd/xz seal. "
    "Never multi-GB .img in git. Never default PIN 2468. Not free commercial broadband."
)

DOCTOR_SCHEMA = "skycache.seal.doctor.v1"
STATUS_SCHEMA = "skycache.seal.status.v1"
EXPORT_SCHEMA = "skycache.seal.export.v1"
KIT_SCHEMA = "skycache.seal.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seal_doctor() -> dict[str, Any]:
    """Host readiness for kit bake vs Linux seal."""
    base = pi_image_doctor()
    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": base.get("score"),
        "go_kit_path": base.get("go_kit_path"),
        "go_seal_path": base.get("go_seal_path"),
        "host_probe": base.get("host_probe"),
        "checks": base.get("checks"),
        "banner": HONEST,
        "next_steps": list(base.get("next_steps") or [])
        + [
            "skycache seal status",
            "skycache seal export --out data/ops/seal-board.html",
            "skycache seal kit --out data/seal-kit",
        ],
        "legal": base.get("legal") or PI_HONEST,
        "pi_doctor_schema": base.get("schema"),
    }


def seal_status() -> dict[str, Any]:
    """Snapshot: host probe + bake plan summary (no secrets)."""
    doc = seal_doctor()
    plan = bake_plan()
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "go_kit_path": doc.get("go_kit_path"),
        "go_seal_path": doc.get("go_seal_path"),
        "host_probe": doc.get("host_probe"),
        "plan_summary": {
            "schema": plan.get("schema"),
            "hostname": plan.get("hostname"),
            "ssid": plan.get("ssid"),
            "legal_rf_mode": plan.get("legal_rf_mode"),
            "mesh_mode": plan.get("mesh_mode"),
            "step_count": len(plan.get("steps") or []),
            "forbidden_pins": plan.get("forbidden_pins"),
            "hosted_paths": plan.get("hosted_paths") or plan.get("download"),
        },
        "legal": "Operator flashes SD; sealed .img.xz stays operator-hosted; never default PIN",
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_seal_html(out_path: Path) -> dict[str, Any]:
    """Printable seal/flash board for fleet maintainers."""
    doc = seal_doctor()
    st = seal_status()
    probe = st.get("host_probe") or {}
    plan = st.get("plan_summary") or {}
    check_rows = []
    for c in doc.get("checks") or []:
        mark = "OK" if c.get("ok") else "FAIL"
        check_rows.append(
            f"<tr><td>{_esc(mark)}</td><td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('detail'))}</td></tr>"
        )
    checks_body = "\n".join(check_rows) or "<tr><td colspan='3'>(none)</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache seal / golden node board</title>
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
<h1>Seal / golden node board</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score {doc.get('score')} · go_kit_path={doc.get('go_kit_path')}
 · go_seal_path={doc.get('go_seal_path')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<h2>Host probe</h2>
<table>
<thead><tr><th>Key</th><th>Value</th></tr></thead>
<tbody>
<tr><td>system</td><td>{_esc(probe.get('system'))}</td></tr>
<tr><td>machine</td><td>{_esc(probe.get('machine'))}</td></tr>
<tr><td>python3</td><td>{_esc(probe.get('python3'))}</td></tr>
<tr><td>dd</td><td>{_esc(probe.get('dd'))}</td></tr>
<tr><td>xz</td><td>{_esc(probe.get('xz'))}</td></tr>
<tr><td>rpi_imager</td><td>{_esc(probe.get('rpi_imager'))}</td></tr>
<tr><td>can_flash_here</td><td>{_esc(probe.get('can_flash_here'))}</td></tr>
</tbody>
</table>
<h2>Plan summary</h2>
<table>
<thead><tr><th>Key</th><th>Value</th></tr></thead>
<tbody>
<tr><td>hostname</td><td>{_esc(plan.get('hostname'))}</td></tr>
<tr><td>ssid</td><td>{_esc(plan.get('ssid'))}</td></tr>
<tr><td>legal_rf_mode</td><td>{_esc(plan.get('legal_rf_mode'))}</td></tr>
<tr><td>mesh_mode</td><td>{_esc(plan.get('mesh_mode'))}</td></tr>
<tr><td>step_count</td><td>{_esc(plan.get('step_count'))}</td></tr>
<tr><td>forbidden_pins</td><td>{_esc(plan.get('forbidden_pins'))}</td></tr>
</tbody>
</table>
<h2>Doctor checks</h2>
<table>
<thead><tr><th>OK</th><th>ID</th><th>Detail</th></tr></thead>
<tbody>
{checks_body}
</tbody>
</table>
<p class="meta">Sealed multi-GB .img.xz: operator-built and operator-hosted only. Register with pi-image sealed-manifest.</p>
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
        "go_kit_path": doc.get("go_kit_path"),
        "banner": HONEST,
    }


def write_seal_kit(
    out_dir: Path,
    *,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Kit: doctor, board, bake artifacts, seal checklist, zip."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = seal_doctor()
    (out_dir / "seal-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = seal_status()
    (out_dir / "seal-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_seal_html(out_dir / "seal-board.html")

    plan = bake_plan()
    bake_meta = write_bake_artifacts(out_dir / "bake", plan)
    seal_meta = write_seal_checklist(out_dir / "seal", plan=plan)

    (out_dir / "README.md").write_text(
        f"""# Seal kit

{HONEST}

## Commands

```text
skycache seal doctor
skycache seal status
skycache seal export --out data/ops/seal-board.html
skycache seal kit --out data/seal-kit
skycache pi-image bundle --out data/pi-download
skycache pi-image sealed-manifest --url HTTPS_URL --sha256 HEX
```

## Paths

- Kit flash: Windows/macOS/Linux OK with Pi Imager + golden SD kit
- Seal clone: Linux host with dd (+ xz optional)
- Never commit multi-GB images

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Seal field checklist

{HONEST}

- [ ] seal doctor go_kit_path true
- [ ] PIN not 2468/0000/1234/1111/9999
- [ ] partner readiness go_sim_pilot before cloning
- [ ] SEAL-CHECKLIST.md walked on Linux seal host
- [ ] sealed-manifest registered (url + sha256 only)
- [ ] no .img.xz in git
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
                "download_hint": "/downloads/skycache-seal-kit.zip",
                "golden_sd_kit": "/downloads/skycache-golden-sd-kit.zip",
                "bake": bake_meta,
                "seal_checklist": seal_meta,
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
        "go_kit_path": doc.get("go_kit_path"),
        "go_seal_path": doc.get("go_seal_path"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
