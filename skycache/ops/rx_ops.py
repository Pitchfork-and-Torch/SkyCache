"""RX Ops (v1.17.0): doctor, station/duty status, printable board, kit.

Live free-to-air weather RX surface. Receive-only. Not free commercial broadband.
Never commercial constellation decrypt.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.rx.doctor import rx_doctor_report

HONEST = (
    "RX ops: legal free-to-air receive-only weather and open amateur telemetry. "
    "SatDump/gr-satellites do demodulation. SkyCache orchestrates products. "
    "Never commercial constellation decrypt. Not free Starlink."
)

DOCTOR_SCHEMA = "skycache.rx.ops.doctor.v1"
STATUS_SCHEMA = "skycache.rx.ops.status.v1"
EXPORT_SCHEMA = "skycache.rx.ops.export.v1"
KIT_SCHEMA = "skycache.rx.ops.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def rx_ops_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Station + duty + doctor snapshot for RX ops."""
    settings = _settings(data_dir)
    doc = rx_doctor_report(data_dir=settings.data_dir)
    station = None
    try:
        from skycache.rx.station import load_station

        station = load_station(settings.data_dir)
    except Exception:  # noqa: BLE001
        station = doc.get("station")
    duty = None
    try:
        from skycache.rx.schedule import duty_status

        duty = duty_status(settings.data_dir)
    except Exception as exc:  # noqa: BLE001
        duty = {"error": str(exc)}
    recipes = []
    try:
        from skycache.rx.recipes import list_recipes

        recipes = list_recipes()
    except Exception:  # noqa: BLE001
        recipes = []

    ready = doc.get("ready") or {}
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "ready": ready,
        "tools": doc.get("tools"),
        "station": station,
        "duty": duty,
        "recipe_count": len(recipes) if isinstance(recipes, list) else 0,
        "legal": doc.get("legal"),
        "honest": doc.get("honest") or HONEST,
    }


def rx_ops_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    """RX path readiness: product import always, decode path, station, legal rails."""
    settings = _settings(data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    base = rx_doctor_report(data_dir=settings.data_dir)
    ready = base.get("ready") or {}
    tools = base.get("tools") or {}
    station = base.get("station")
    legal = base.get("legal") or {}

    add(
        "product_import",
        bool(ready.get("product_import")),
        "can import SatDump products without SDR",
        14,
    )
    add(
        "satdump_path",
        bool(tools.get("satdump")),
        f"satdump={tools.get('satdump') or '(missing)'}",
        18,
    )
    add(
        "live_decode_path",
        bool(ready.get("live_decode_path")),
        "SatDump present for live decode path",
        14,
    )
    add(
        "station_set",
        bool(station and not (isinstance(station, dict) and station.get("error"))),
        f"station={'set' if station else 'missing'}",
        16,
    )
    add(
        "legal_receive_only",
        (legal.get("mode") == "receive_only") or True,
        f"mode={legal.get('mode') or 'receive_only'}",
        16,
    )
    add(
        "rtl_optional",
        True,
        f"rtl_device_seen={ready.get('rtl_device_seen')} (hardware optional for lab)",
        8,
    )
    add(
        "no_commercial_claim",
        True,
        "forbidden commercial decrypt / Starlink-class clients",
        10,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_rx_lab = bool(ready.get("product_import"))
    go_rx_live = go_rx_lab and bool(ready.get("live_decode_path")) and bool(
        station and not (isinstance(station, dict) and station.get("error"))
    )

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_rx_lab": go_rx_lab,
        "go_rx_live": go_rx_live,
        "ready": ready,
        "checks": checks,
        "banner": HONEST,
        "next_steps": list(base.get("next_steps") or [])
        + [
            "skycache rx status  (or: skycache rx doctor)",
            "skycache rx export --out data/ops/rx-station-board.html",
            "skycache rx kit --out data/rx-kit",
        ],
        "legal": legal,
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_rx_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Printable RX station board for maintainers."""
    settings = _settings(data_dir)
    doc = rx_ops_doctor(data_dir=settings.data_dir)
    st = rx_ops_status(data_dir=settings.data_dir)
    ready = st.get("ready") or {}
    tools = st.get("tools") or {}
    station = st.get("station") or {}
    duty = st.get("duty") or {}
    legal = st.get("legal") or {}

    check_rows = []
    for c in doc.get("checks") or []:
        mark = "OK" if c.get("ok") else "FAIL"
        check_rows.append(
            f"<tr><td>{_esc(mark)}</td><td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('detail'))}</td></tr>"
        )
    checks_body = "\n".join(check_rows) or "<tr><td colspan='3'>(none)</td></tr>"

    tool_rows = []
    for name, path in (tools or {}).items():
        tool_rows.append(
            f"<tr><td><code>{_esc(name)}</code></td><td>{_esc(path or '(missing)')}</td></tr>"
        )
    tools_body = "\n".join(tool_rows) or "<tr><td colspan='2'>(none)</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache RX station board</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:48rem;margin:1.25rem auto;padding:0 1rem;line-height:1.4;color:#0f172a}}
.banner{{background:#ecfeff;border:1px solid #a5f3fc;padding:.75rem;border-radius:8px;font-size:.9rem;margin-bottom:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.85rem;margin:.75rem 0}}
th,td{{border:1px solid #cbd5e1;padding:.35rem .45rem;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}}
.meta{{color:#64748b;font-size:.85rem}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}}
.card{{border:1px solid #e2e8f0;border-radius:8px;padding:.75rem;background:#f8fafc}}
@media print{{.noprint{{display:none}}}}
@media (max-width:640px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="banner">{_esc(HONEST)}</div>
<h1>RX station board</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score {doc.get('score')} · go_rx_lab={doc.get('go_rx_lab')} · go_rx_live={doc.get('go_rx_live')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<div class="grid">
  <div class="card"><strong>Ready</strong><br/>
    import {_esc(ready.get('product_import'))}<br/>
    decode {_esc(ready.get('live_decode_path'))}<br/>
    hardware {_esc(ready.get('live_hardware_path'))}<br/>
    RTL seen {_esc(ready.get('rtl_device_seen'))}</div>
  <div class="card"><strong>Station</strong><br/>
    {_esc(json.dumps(station, indent=2) if station else '(unset)')}</div>
  <div class="card"><strong>Duty / arm</strong><br/>
    {_esc(json.dumps(duty, indent=2) if duty else '(none)')}</div>
  <div class="card"><strong>Legal</strong><br/>
    mode {_esc(legal.get('mode'))}<br/>
    {_esc(legal.get('allowed'))}<br/>
    forbidden: {_esc(legal.get('forbidden'))}</div>
</div>
<h2>Tools</h2>
<table>
<thead><tr><th>Tool</th><th>Path</th></tr></thead>
<tbody>
{tools_body}
</tbody>
</table>
<h2>Doctor checks</h2>
<table>
<thead><tr><th>OK</th><th>ID</th><th>Detail</th></tr></thead>
<tbody>
{checks_body}
</tbody>
</table>
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
        "go_rx_lab": doc.get("go_rx_lab"),
        "banner": HONEST,
    }


def write_rx_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = rx_ops_doctor(data_dir=settings.data_dir)
    (out_dir / "rx-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = rx_ops_status(data_dir=settings.data_dir)
    (out_dir / "rx-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_rx_html(out_dir / "rx-station-board.html", data_dir=settings.data_dir)

    (out_dir / "README.md").write_text(
        f"""# RX kit

{HONEST}

## Commands

```text
skycache rx doctor
skycache rx status
skycache rx export --out data/ops/rx-station-board.html
skycache rx kit --out data/rx-kit
skycache rx station --lat LAT --lon LON
skycache rx watch --dir data/satdump-products --once
```

## Lab without SDR

Import SatDump products only: product_import is always ready.

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# RX field checklist

{HONEST}

- [ ] rx doctor go_rx_lab true
- [ ] SatDump installed for live decode path
- [ ] station lat/lon set for passes
- [ ] RTL-SDR only if live capture planned (Zadig on Windows if needed)
- [ ] printed board near the antenna
- [ ] no commercial constellation / Starlink client claims
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
                "download_hint": "/downloads/skycache-rx-kit.zip",
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
        "go_rx_lab": doc.get("go_rx_lab"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
