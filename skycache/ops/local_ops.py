"""Local Ops (v1.16.0): doctor, privacy snapshot status, printable board, kit.

Privacy-preserving node health board for maintainers.
Fleet heartbeat remains default OFF. Not free commercial broadband.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.ops.local_metrics import local_ops_snapshot

HONEST = (
    "Local ops: privacy-preserving node health (disk, power, peers, pack freshness, bit-rot). "
    "Fleet heartbeat remains default OFF. No personal data harvest. "
    "Not free commercial broadband."
)

DOCTOR_SCHEMA = "skycache.ops.doctor.v1"
STATUS_SCHEMA = "skycache.ops.status.v1"
EXPORT_SCHEMA = "skycache.ops.export.v1"
KIT_SCHEMA = "skycache.ops.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _snapshot(settings) -> dict[str, Any]:
    from skycache.nexus.mesh import MeshFabric
    from skycache.skybrary.catalog import SkybraryCatalog

    mesh = MeshFabric(
        data_dir=settings.data_dir,
        node_id=settings.node_id or "",
        enabled=True,
        mode=settings.mesh_mode,
        band=settings.mesh_band,
    )
    try:
        mesh.load()
    except Exception:  # noqa: BLE001
        pass
    sky_n = None
    try:
        sky = SkybraryCatalog(settings.skybrary_db_path)
        sky_n = sky.count()
        sky.close()
    except Exception:  # noqa: BLE001
        sky_n = None
    return local_ops_snapshot(settings, mesh=mesh, sky_count=sky_n)


def ops_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Local metrics snapshot with Local Ops status schema."""
    settings = _settings(data_dir)
    snap = _snapshot(settings)
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "snapshot": snap,
        "fleet_heartbeat_enabled": bool((snap.get("fleet_heartbeat") or {}).get("enabled")),
        "disk_free_bytes": ((snap.get("disk") or {}).get("free_bytes")),
        "packages": ((snap.get("content") or {}).get("packages")),
        "skybrary_works": snap.get("skybrary_works"),
        "battery_percent": ((snap.get("power") or {}).get("battery_percent")),
        "peer_count": ((snap.get("mesh") or {}).get("peer_count")),
        "legal": snap.get("legal") or "Local metrics only - no personal data harvest",
    }


def ops_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Local ops readiness: metrics readable, fleet OFF, disk not full."""
    settings = _settings(data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    st = ops_status(data_dir=settings.data_dir)
    snap = st.get("snapshot") or {}
    disk = snap.get("disk") or {}
    power = snap.get("power") or {}
    fleet = snap.get("fleet_heartbeat") or {}
    bitrot = snap.get("bitrot") or {}
    content = snap.get("content") or {}

    free = disk.get("free_bytes")
    used_pct = disk.get("used_pct")
    fleet_off = fleet.get("enabled") is False
    soc = power.get("battery_percent")

    add("snapshot_built", bool(snap.get("schema")), f"schema={snap.get('schema')}", 16)
    add(
        "disk_readable",
        free is not None and not disk.get("error"),
        f"free_bytes={free} used_pct={used_pct}" if free is not None else str(disk.get("error") or "disk unknown"),
        18,
    )
    add(
        "disk_headroom",
        free is None or int(free) > 100 * 1024 * 1024 or (used_pct is not None and float(used_pct) < 95),
        ">=100MB free or used_pct < 95" if free is not None else "disk free unknown (soft)",
        14,
    )
    add(
        "fleet_heartbeat_off",
        fleet_off,
        f"fleet_heartbeat.enabled={fleet.get('enabled')}",
        20,
    )
    add(
        "power_readable",
        soc is not None or power.get("error") is not None,
        f"SOC={soc}" if soc is not None else f"power note={power.get('error') or 'n/a'}",
        10,
    )
    add(
        "bitrot_schedule_surface",
        True,
        f"bitrot keys={list(bitrot.keys())[:6]}",
        8,
    )
    pkgs = int(content.get("packages") or 0)
    add(
        "content_scanned",
        True,
        f"packages={pkgs} skybrary_works={st.get('skybrary_works')}",
        8,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_local_lab = bool(snap.get("schema")) and fleet_off
    go_local_field = go_local_lab and (free is None or int(free) > 100 * 1024 * 1024)

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_local_lab": go_local_lab,
        "go_local_field": go_local_field,
        "fleet_heartbeat_enabled": not fleet_off,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache ops doctor",
            "skycache ops status",
            "skycache ops export --out data/ops/local-ops-board.html",
            "skycache ops kit --out data/ops-kit",
            "Keep fleet heartbeat OFF unless you explicitly opt in later",
        ],
        "legal": "Local metrics only - no personal data harvest; fleet default OFF",
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_ops_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Printable local ops wall board for maintainers."""
    settings = _settings(data_dir)
    st = ops_status(data_dir=settings.data_dir)
    doc = ops_doctor(data_dir=settings.data_dir)
    snap = st.get("snapshot") or {}
    disk = snap.get("disk") or {}
    power = snap.get("power") or {}
    mesh = snap.get("mesh") or {}
    content = snap.get("content") or {}
    bitrot = snap.get("bitrot") or {}
    fleet = snap.get("fleet_heartbeat") or {}

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
<title>SkyCache local ops board</title>
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
<h1>Local ops board</h1>
<p class="meta">Software v{__version__} · {_iso_now()} · node=<strong>{_esc(snap.get('node_id') or '(unset)')}</strong>
 · score {doc.get('score')} · go_local_lab={doc.get('go_local_lab')} · go_local_field={doc.get('go_local_field')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<div class="grid">
  <div class="card"><strong>Disk</strong><br/>free {_esc(disk.get('free_bytes'))} B<br/>used {_esc(disk.get('used_pct'))}%</div>
  <div class="card"><strong>Power</strong><br/>SOC {_esc(power.get('battery_percent'))}% · mode {_esc(power.get('mode'))}<br/>AC {_esc(power.get('on_ac'))}</div>
  <div class="card"><strong>Mesh</strong><br/>peers {_esc(mesh.get('peer_count'))}<br/>disaster {_esc(mesh.get('disaster_mode'))}</div>
  <div class="card"><strong>Content</strong><br/>packages {_esc(content.get('packages'))}<br/>skybrary {_esc(st.get('skybrary_works'))}</div>
</div>
<h2>Fleet heartbeat</h2>
<p>enabled=<strong>{_esc(fleet.get('enabled'))}</strong> · {_esc(fleet.get('note'))}</p>
<h2>Bit-rot schedule</h2>
<pre style="white-space:pre-wrap;font-size:.8rem;background:#f1f5f9;padding:.75rem;border-radius:8px">{_esc(json.dumps(bitrot, indent=2))}</pre>
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
        "go_local_lab": doc.get("go_local_lab"),
        "banner": HONEST,
    }


def write_ops_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = ops_doctor(data_dir=settings.data_dir)
    (out_dir / "ops-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = ops_status(data_dir=settings.data_dir)
    (out_dir / "ops-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_ops_html(out_dir / "local-ops-board.html", data_dir=settings.data_dir)

    (out_dir / "README.md").write_text(
        f"""# Local ops kit

{HONEST}

## Commands

```text
skycache ops doctor
skycache ops status
skycache ops export --out data/ops/local-ops-board.html
skycache ops kit --out data/ops-kit
```

## Privacy

Fleet heartbeat stays OFF unless you explicitly opt in later. Do not send personal data off-node.

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Local ops field checklist

{HONEST}

- [ ] ops doctor go_local_lab true
- [ ] fleet_heartbeat.enabled is false
- [ ] disk headroom (go_local_field or free space known)
- [ ] board printed for maintainer wall
- [ ] power doctor run separately for solar sites
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
                "download_hint": "/downloads/skycache-ops-kit.zip",
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
        "go_local_lab": doc.get("go_local_lab"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
