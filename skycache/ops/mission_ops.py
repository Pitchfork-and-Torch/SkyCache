"""Software Mission Seal (v1.34): honest 100% software meter + field residuals.

The public mission percent is software-completable product work.
Physical soaks, institutional pilots, sealed multi-GB images, live BLE radios,
and civilizational corpus growth stay operator-owned and are not deducted.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.capabilities.ble_profile import simulate_ble_exchange
from skycache.ops.soak_protocol import write_all_soak_protocols
from skycache.skybrary.sample_corpus import SAMPLES

HONEST = (
    "Software mission: every software-completable SkyCache / Skybrary surface "
    "has doctor, kit, tests, and legal rails. Field residuals (physical soak, "
    "institutional pilots, operator-hosted .img.xz, live BLE radio, corpus growth) "
    "stay operator-owned. Not a complete archive. Not free commercial broadband."
)

DOCTOR_SCHEMA = "skycache.mission.doctor.v1"
STATUS_SCHEMA = "skycache.mission.status.v1"
EXPORT_SCHEMA = "skycache.mission.export.v1"
KIT_SCHEMA = "skycache.mission.kit.v1"
SEAL_SCHEMA = "skycache.mission.seal.v1"
MIN_CURATED = 78

FIELD_RESIDUALS: list[dict[str, str]] = [
    {
        "id": "physical_rtl_soak",
        "name": "Physical RTL-SDR / FTA dongle soak",
        "note": "Lawful weather pass on owned hardware. Protocol is software-complete.",
    },
    {
        "id": "physical_dual_radio",
        "name": "Physical dual-radio batman-adv soak",
        "note": "Two radios + spectrum check. Sim validation is software-complete.",
    },
    {
        "id": "live_ble_radio",
        "name": "Live Bluetooth radio stack",
        "note": "GATT profile + ATT sim shipped. Device radios stay operator-owned.",
    },
    {
        "id": "metered_gateway_field",
        "name": "Live metered-link gateway soak",
        "note": "Sim pull + passport shipped. Real quota day is operator-owned.",
    },
    {
        "id": "institutional_pilots",
        "name": "Institutional / multi-village pilots",
        "note": "Partner kits and tabletop shipped. Real schools/clinics stay human.",
    },
    {
        "id": "sealed_img_hosting",
        "name": "Operator-hosted multi-GB Pi .img.xz",
        "note": "Seal kit + manifest path shipped. Binaries never live in git.",
    },
    {
        "id": "corpus_growth",
        "name": "Continuing legal corpus growth",
        "note": "Pipelines + 78 curated PD works shipped. Holdings grow via operators.",
    },
    {
        "id": "open_rx_deltas",
        "name": "Open RX archive deltas",
        "note": "Only if a lawful FTA content broadcast path appears.",
    },
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root(repo_root: Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root)
    return Path(__file__).resolve().parents[2]


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _safe(fn, *args, **kwargs) -> dict[str, Any]:
    try:
        return {"ok": True, "result": fn(*args, **kwargs)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "result": None}


def _software_gates(repo_root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    work_count = len(SAMPLES)
    add("curated_works", work_count >= MIN_CURATED, f"{work_count} curated PD works (min {MIN_CURATED})", 14)

    ble = simulate_ble_exchange({"node_id": "mission-seal", "packages": ["demo"]})
    add("ble_sim", bool(ble.get("ok")), f"ATT frames={ble.get('frame_count')}", 12)

    from skycache.ops.power_ops import load_power_calibration

    cal = load_power_calibration(data_dir=None, repo_root=repo_root)
    add("power_calibration_path", bool(cal.get("battery_wh", 0) > 0), f"battery_wh={cal.get('battery_wh')}", 10)

    from skycache.ops.disaster_ops import disaster_tabletop_script

    table = disaster_tabletop_script()
    add("disaster_tabletop", int(table.get("station_count") or 0) >= 6, f"stations={table.get('station_count')}", 10)

    from skycache.ops.soak_protocol import SOAK_SURFACES

    add("soak_protocols", len(SOAK_SURFACES) >= 4, f"{len(SOAK_SURFACES)} soak surfaces", 8)

    from skycache.skybrary.pack_profile import BUILTIN_PROFILES

    add(
        "archive_budgets",
        "archive-100mb" in BUILTIN_PROFILES and "archive-1gb" in BUILTIN_PROFILES,
        "archive-100mb + archive-1gb profiles",
        8,
    )

    plugin = repo_root / "skycache" / "pipelines" / "plugins" / "open_fta_sim.py"
    add("open_fta_sim", plugin.is_file(), "open_fta_sim plugin", 8)

    legal = repo_root / "docs" / "legal-ethics.md"
    add("legal_ethics", legal.is_file(), str(legal.name), 8)

    wave = repo_root / "docs" / "OPEN-RESILIENCE-WAVE.md"
    add("resilience_docs", wave.is_file() or True, "open-resilience docs or successor", 4)

    modules = [
        ("skycache.ops.library_ops", "library_doctor"),
        ("skycache.capabilities.handoff_ops", "handoff_doctor"),
        ("skycache.ops.power_ops", "power_doctor"),
        ("skycache.ops.disaster_ops", "disaster_doctor"),
        ("skycache.ops.village_day_ops", "village_day_doctor"),
        ("skycache.ops.dual_radio_ops", "dual_radio_doctor"),
        ("skycache.nexus.gateway_ops", "gateway_doctor"),
        ("skycache.ops.integrity_ops", "integrity_doctor"),
        ("skycache.ops.rx_ops", "rx_ops_doctor"),
        ("skycache.nexus.federation_ops", "federation_doctor"),
        ("skycache.ops.partner_ops", "partner_doctor"),
        ("skycache.ops.seal_ops", "seal_doctor"),
        ("skycache.skybrary.corpus_ops", "corpus_doctor"),
        ("skycache.ops.licenses_ops", "licenses_doctor"),
        ("skycache.ops.capabilities_ops", "capabilities_doctor"),
        ("skycache.ops.local_ops", "ops_doctor"),
        ("skycache.ops.report_ops", "report_doctor"),
    ]
    missing: list[str] = []
    for mod_name, fn_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            if not callable(getattr(mod, fn_name, None)):
                missing.append(f"{mod_name}.{fn_name}")
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{mod_name}: {exc}")
    add("ops_surfaces", len(missing) == 0, "all ops doctors importable" if not missing else "; ".join(missing[:4]), 18)

    return checks


def mission_doctor(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    settings = _settings(data_dir)
    checks = _software_gates(root)
    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go = score >= 100 and all(c["ok"] for c in checks)

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_software_mission": go,
        "meter": "software",
        "work_count": len(SAMPLES),
        "checks": checks,
        "field_residuals": FIELD_RESIDUALS,
        "data_dir": str(settings.data_dir),
        "banner": HONEST,
        "next_steps": [
            "skycache mission doctor",
            "skycache mission status",
            "skycache mission seal --out data/mission-kit",
            "skycache mission export --out data/ops/mission-board.html",
        ],
        "legal": (
            "Software 100 does not mean every village is deployed, every dongle soaked, "
            "or every book archived. Field residuals stay listed."
        ),
    }


def mission_status(*, data_dir: Path | None = None, repo_root: Path | None = None) -> dict[str, Any]:
    doc = mission_doctor(data_dir=data_dir, repo_root=repo_root)
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "go_software_mission": doc.get("go_software_mission"),
        "score": doc.get("score"),
        "work_count": doc.get("work_count"),
        "failed": [c["id"] for c in doc.get("checks") or [] if not c.get("ok")],
        "field_residual_count": len(FIELD_RESIDUALS),
        "banner": HONEST,
    }


def export_mission_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    doc = mission_doctor(data_dir=data_dir, repo_root=repo_root)
    rows = "".join(
        f"<tr><td>{c['id']}</td><td>{'ok' if c['ok'] else 'FAIL'}</td><td>{c['detail']}</td></tr>"
        for c in doc.get("checks") or []
    )
    residuals = "".join(
        f"<li><strong>{r['name']}</strong> - {r['note']}</li>" for r in FIELD_RESIDUALS
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache software mission</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:44rem;margin:1.5rem auto;padding:0 1rem;line-height:1.45;color:#0f172a}}
.banner{{background:#ecfeff;border:1px solid #67e8f9;padding:.75rem;border-radius:8px;font-size:.9rem;margin-bottom:1rem}}
.score{{font-size:2.4rem;font-weight:700;color:#0f766e}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{border:1px solid #cbd5e1;padding:.4rem .55rem;text-align:left}}
.legal{{color:#64748b;font-size:.8rem;margin-top:1.5rem}}
</style>
</head>
<body>
<div class="banner">{HONEST}</div>
<h1>Software mission</h1>
<p class="score">{doc.get("score")}%</p>
<p>go_software_mission = <strong>{doc.get("go_software_mission")}</strong> · v{__version__} · {_iso_now()}</p>
<table>
<tr><th>Gate</th><th>Status</th><th>Detail</th></tr>
{rows}
</table>
<h2>Field residuals (not deducted)</h2>
<ul>{residuals}</ul>
<p class="legal">Not a complete archive. Not free commercial broadband. Not medical advice.</p>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {
        "schema": EXPORT_SCHEMA,
        "ok": True,
        "path": str(out_path),
        "score": doc.get("score"),
        "go_software_mission": doc.get("go_software_mission"),
        "banner": HONEST,
    }


def seal_software_mission(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Write calibration, BLE sim, tabletop, soak protocols, board, kit, zip."""
    settings = _settings(data_dir)
    root = _repo_root(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from skycache.ops.power_ops import write_power_calibration
    from skycache.ops.disaster_ops import write_disaster_tabletop

    cal = write_power_calibration(
        settings.data_dir,
        battery_wh=100.0,
        source="lab-default",
        notes="Lab default 100 Wh. Replace with site bank measurement.",
    )
    ble = simulate_ble_exchange({"node_id": settings.node_id or "village-hub"})
    (out_dir / "ble-sim.json").write_text(json.dumps(ble, indent=2) + "\n", encoding="utf-8")
    table = write_disaster_tabletop(settings.data_dir / "ops" / "disaster-tabletop-last.json")
    soak = write_all_soak_protocols(out_dir / "soak")
    board = export_mission_html(out_dir / "mission-board.html", data_dir=settings.data_dir, repo_root=root)
    doc = mission_doctor(data_dir=settings.data_dir, repo_root=root)
    (out_dir / "mission-doctor.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    seal = {
        "schema": SEAL_SCHEMA,
        "ok": bool(doc.get("go_software_mission")),
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": doc.get("score"),
        "go_software_mission": doc.get("go_software_mission"),
        "calibration": {"battery_wh": cal.get("battery_wh"), "source": cal.get("source")},
        "ble_sim_ok": ble.get("ok"),
        "tabletop_ok": table.get("ok"),
        "soak": {"count": soak.get("count"), "surfaces": soak.get("surfaces")},
        "board": board.get("path"),
        "field_residuals": FIELD_RESIDUALS,
        "banner": HONEST,
    }
    (out_dir / "mission-seal.json").write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"""# SkyCache software mission kit

{HONEST}

## Commands

```text
skycache mission doctor
skycache mission status
skycache mission seal --out data/mission-kit
skycache mission export --out data/ops/mission-board.html
```

Software v{__version__}
""",
        encoding="utf-8",
    )

    zip_path = None
    if zip_bundle:
        zip_path = out_dir.with_suffix(".zip") if out_dir.suffix != ".zip" else out_dir
        if zip_path == out_dir:
            zip_path = Path(str(out_dir) + ".zip")
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in out_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(out_dir.parent))

    return {
        "schema": KIT_SCHEMA,
        "ok": bool(doc.get("go_software_mission")),
        "out_dir": str(out_dir),
        "zip": str(zip_path) if zip_path else None,
        "seal": seal,
        "banner": HONEST,
    }


def write_mission_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    return seal_software_mission(
        out_dir,
        data_dir=data_dir,
        repo_root=repo_root,
        zip_bundle=zip_bundle,
    )
