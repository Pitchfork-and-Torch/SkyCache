"""Partner field pilot packaging + readiness (v1.3.0 Partner Pilot Ops).

Builds NGO / university / civil-protection pilot folders and zips for site hosting.
Validates pilot reports. Scores local lab readiness without claiming free broadband.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__

KIT_TYPES = ("ngo", "university", "civil-protection")
KIT_SCHEMA = "skycache.partner.kit.v2"
REPORT_SCHEMA = "skycache.partner.pilot_report.v1"
READINESS_SCHEMA = "skycache.partner.readiness.v1"
PACKAGE_SCHEMA = "skycache.partner.package_all.v1"

REQUIRED_REPORT_FIELDS = (
    "schema",
    "kit_type",
    "org",
    "location",
    "date",
    "nodes_deployed",
    "phones_served_estimate",
    "packs_used",
    "issues",
    "license_review_ok",
    "honest_scope_briefed",
    "notes",
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_partner_kit(
    out_dir: Path,
    *,
    kit_type: str = "ngo",
    include_docs_copy: bool = True,
    repo_root: Path | None = None,
    make_zip: bool = False,
) -> dict[str, Any]:
    """Write a self-contained partner pilot folder (docs + checklists + CLI hints)."""
    kit_type = (kit_type or "ngo").lower().strip()
    if kit_type not in KIT_TYPES:
        raise ValueError(f"kit_type must be one of {KIT_TYPES}")
    out_dir = Path(out_dir)
    if out_dir.exists():
        # rebuild cleanly when re-running package-all
        for child in list(out_dir.iterdir()):
            if child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir() and child.name in ("docs",):
                shutil.rmtree(child, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    built = _iso_now()
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]

    checklist = _checklist(kit_type)
    manifest = {
        "schema": KIT_SCHEMA,
        "kit_type": kit_type,
        "software_version": __version__,
        "built_at": built,
        "banner": (
            "Partner field pilot kit - store-and-forward knowledge + community mesh. "
            "Not free Starlink. Not a complete archive. Legal open content only."
        ),
        "contact": "skycache@jonbailey.xyz",
        "site": "https://skycache.jonbailey.xyz",
        "partners_page": "https://skycache.jonbailey.xyz/partners/",
        "checklist": checklist,
        "cli": [
            "skycache first-boot --yes --pin <PIN> --ssid SkyCache-Village --legal-rf-mode receive_only --sim",
            "skycache serve --sim",
            "skycache skybrary pack --profile emergency-health",
            "skycache skybrary pack --profile literacy-1gb",
            "skycache licenses --html licenses.html",
            "skycache nexus validate --nodes 2",
            "skycache mesh day-one --write",
            "skycache rx doctor",
            "skycache rx schedule --hours 24",
            "skycache rx arm --hours 12",
            "skycache partner readiness --data-dir data",
            "skycache partner report validate pilot-report.json",
        ],
        "success_criteria": [
            "Volunteer builds demo node from docs in <2 hours (lab/sim)",
            "Phone without cell plan reads demos over hub Wi-Fi",
            "License inventory printable for partner legal review",
            "Disaster drill playbook walked once (sim OK)",
            "Pass Autopilot schedule/arm understood (product import path OK without dongle)",
            "Pilot report validated (partner report validate)",
            "No claim of free broadband or complete archive",
        ],
    }
    (out_dir / "partner-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "CHECKLIST.md").write_text(_checklist_md(kit_type, checklist), encoding="utf-8")
    (out_dir / "LEGAL-ONE-PAGER.md").write_text(_legal_one_pager(), encoding="utf-8")
    (out_dir / "TRAINING-HALF-DAY.md").write_text(_training(kit_type), encoding="utf-8")
    (out_dir / "FIELD-DAY.md").write_text(_field_day(kit_type), encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"""# SkyCache partner pilot kit - {kit_type}

Software version: {__version__}
Built: {built}

1. Read LEGAL-ONE-PAGER.md with your legal/compliance contact
2. Walk CHECKLIST.md on a lab laptop (`serve --sim`) before field
3. TRAINING-HALF-DAY.md for volunteer agenda
4. FIELD-DAY.md for install + optional live FTA product path
5. After field: fill pilot-report.template.json then:
   `skycache partner report validate pilot-report.json`

Contact: skycache@jonbailey.xyz  |  subject `[{kit_type} pilot]`
Site: https://skycache.jonbailey.xyz/partners/
""",
        encoding="utf-8",
    )
    report_template = {
        "schema": REPORT_SCHEMA,
        "kit_type": kit_type,
        "org": "",
        "location": "",
        "date": "",
        "nodes_deployed": 0,
        "phones_served_estimate": 0,
        "packs_used": [],
        "issues": [],
        "license_review_ok": False,
        "honest_scope_briefed": False,
        "rx_path_used": False,
        "mesh_path_used": False,
        "notes": "",
    }
    (out_dir / "pilot-report.template.json").write_text(
        json.dumps(report_template, indent=2) + "\n", encoding="utf-8"
    )

    docs_copied: list[str] = []
    if include_docs_copy:
        doc_map = {
            "first-boot.md": repo_root / "docs" / "first-boot.md",
            "disaster-drill.md": repo_root / "docs" / "disaster-drill.md",
            "mesh-field-checklist.md": repo_root / "docs" / "mesh-field-checklist.md",
            "partner-kits.md": repo_root / "docs" / "partner-kits.md",
            "legal-ethics.md": repo_root / "docs" / "legal-ethics.md",
            "hardware-bom.md": repo_root / "docs" / "hardware-bom.md",
            "threat-model.md": repo_root / "docs" / "threat-model.md",
            "phase2-live-rx.md": repo_root / "docs" / "phase2-live-rx.md",
        }
        docs_dir = out_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        for name, src in doc_map.items():
            if src.is_file():
                shutil.copy2(src, docs_dir / name)
                docs_copied.append(name)

    (out_dir / "CHECKLIST.html").write_text(
        _checklist_html(kit_type, checklist, manifest["banner"]), encoding="utf-8"
    )

    zip_path: str | None = None
    if make_zip:
        zp = out_dir.with_suffix(".zip")
        if out_dir.name.startswith("skycache-partner-"):
            zp = out_dir.parent / f"{out_dir.name}.zip"
        else:
            zp = out_dir.parent / f"skycache-partner-{kit_type}-kit.zip"
        zip_path = str(_zip_dir(out_dir, zp))

    files = sorted(p.name for p in out_dir.rglob("*") if p.is_file())
    return {
        "ok": True,
        "out_dir": str(out_dir),
        "kit_type": kit_type,
        "schema": KIT_SCHEMA,
        "docs_copied": docs_copied,
        "files": files,
        "zip": zip_path,
        "software_version": __version__,
    }


def package_all_partner_kits(
    out_dir: Path,
    *,
    repo_root: Path | None = None,
    include_docs_copy: bool = True,
) -> dict[str, Any]:
    """Build all kit types + zips + HOSTING.json for site /downloads/partner-kits/."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    kits: list[dict[str, Any]] = []
    for kt in KIT_TYPES:
        kit_dir = out_dir / f"skycache-partner-{kt}-kit"
        meta = build_partner_kit(
            kit_dir,
            kit_type=kt,
            include_docs_copy=include_docs_copy,
            repo_root=repo_root,
            make_zip=True,
        )
        kits.append(meta)

    hosting = {
        "schema": "skycache.partner.hosting.v1",
        "software_version": __version__,
        "built_at": _iso_now(),
        "site_path": "/downloads/partner-kits/",
        "legal": (
            "Partner pilot materials only. Open content + receive-only RF. "
            "Not free commercial broadband."
        ),
        "kits": [
            {
                "kit_type": k["kit_type"],
                "zip": Path(k["zip"]).name if k.get("zip") else None,
                "folder": Path(k["out_dir"]).name,
            }
            for k in kits
        ],
    }
    (out_dir / "HOSTING.json").write_text(
        json.dumps(hosting, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(
        f"""# SkyCache partner pilot kits ({__version__})

Built: {hosting['built_at']}

| Type | Zip |
|------|-----|
"""
        + "\n".join(
            f"| {k['kit_type']} | `{Path(k['zip']).name if k.get('zip') else 'n/a'}` |"
            for k in kits
        )
        + """

Host under https://skycache.jonbailey.xyz/downloads/partner-kits/

Honest scope: store-and-forward knowledge for field pilots - not free Starlink.
""",
        encoding="utf-8",
    )
    return {
        "schema": PACKAGE_SCHEMA,
        "ok": True,
        "out_dir": str(out_dir),
        "kits": kits,
        "hosting": hosting,
        "software_version": __version__,
    }


def validate_pilot_report(path: Path) -> dict[str, Any]:
    """Validate a filled pilot report JSON (fail closed on missing honesty fields)."""
    path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return {
            "ok": False,
            "schema": REPORT_SCHEMA,
            "path": str(path),
            "errors": [f"file not found: {path}"],
            "warnings": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "schema": REPORT_SCHEMA,
            "path": str(path),
            "errors": [f"invalid JSON: {exc}"],
            "warnings": [],
        }
    if not isinstance(data, dict):
        return {
            "ok": False,
            "path": str(path),
            "errors": ["root must be a JSON object"],
            "warnings": [],
        }

    for key in REQUIRED_REPORT_FIELDS:
        if key not in data:
            errors.append(f"missing field: {key}")

    schema = str(data.get("schema") or "")
    if schema and schema != REPORT_SCHEMA:
        warnings.append(f"schema is {schema!r}; expected {REPORT_SCHEMA}")

    kt = str(data.get("kit_type") or "").lower().strip()
    if kt and kt not in KIT_TYPES:
        errors.append(f"kit_type must be one of {KIT_TYPES}")

    if not str(data.get("org") or "").strip():
        errors.append("org is empty")
    if not str(data.get("location") or "").strip():
        errors.append("location is empty")
    if not str(data.get("date") or "").strip():
        errors.append("date is empty")

    if data.get("license_review_ok") is not True:
        errors.append("license_review_ok must be true before pilot close-out")
    if data.get("honest_scope_briefed") is not True:
        errors.append("honest_scope_briefed must be true (no free-broadband claims)")

    try:
        nodes = int(data.get("nodes_deployed") or 0)
        if nodes < 0:
            errors.append("nodes_deployed must be >= 0")
    except (TypeError, ValueError):
        errors.append("nodes_deployed must be an integer")

    try:
        phones = int(data.get("phones_served_estimate") or 0)
        if phones < 0:
            errors.append("phones_served_estimate must be >= 0")
    except (TypeError, ValueError):
        errors.append("phones_served_estimate must be an integer")

    if not isinstance(data.get("packs_used"), list):
        errors.append("packs_used must be a list")
    if not isinstance(data.get("issues"), list):
        errors.append("issues must be a list")

    # soft quality signals
    if nodes == 0:
        warnings.append("nodes_deployed is 0 - lab-only report?")
    if not data.get("notes"):
        warnings.append("notes empty - consider field observations")

    return {
        "ok": len(errors) == 0,
        "schema": REPORT_SCHEMA,
        "path": str(path),
        "kit_type": kt or None,
        "errors": errors,
        "warnings": warnings,
        "score": max(0, 100 - 12 * len(errors) - 3 * len(warnings)),
        "legal": "Pilot only - does not authorize commercial satellite use",
    }


def partner_readiness(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Local lab readiness score for partner pilot go/no-go (no personal data)."""
    from skycache.config import Settings
    from skycache.rx.doctor import rx_doctor_report
    from skycache.rx.schedule import duty_status, load_arm
    from skycache.rx.station import load_station

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    # Sim / data dir present
    add("data_dir", settings.data_dir.is_dir(), f"data_dir={settings.data_dir}", 10)

    # Content samples or packages
    content = settings.content_dir
    has_content = content.is_dir() and any(content.iterdir())
    add("content", has_content, "content packages present" if has_content else "run first-boot --sim or load samples", 15)

    # Station (optional for pure sim pilots)
    st = load_station(settings.data_dir)
    add(
        "station",
        st is not None,
        "station.json set" if st else "optional for sim-only; set for live FTA",
        8,
    )

    # RX doctor
    doc = rx_doctor_report(data_dir=settings.data_dir)
    ready = doc.get("ready") or {}
    add(
        "product_import",
        bool(ready.get("product_import")),
        "product import path ready",
        12,
    )
    add(
        "live_decode_path",
        bool(ready.get("live_decode_path")),
        "SatDump/RTL software stack" if ready.get("live_decode_path") else "optional until field RF day",
        8,
    )
    add(
        "rtl_device",
        bool(ready.get("rtl_device_seen")),
        "RTL-SDR seen" if ready.get("rtl_device_seen") else "no dongle (product import still OK)",
        5,
    )

    arm = load_arm(settings.data_dir)
    add("armed", bool(arm and arm.get("armed")), "station armed for autopilot" if arm else "not armed (ok for sim kit)", 5)

    duty = duty_status(settings.data_dir)
    add(
        "schedule",
        bool(duty.get("schedule_ok")),
        f"pass engine={duty.get('engine')}" if duty.get("schedule_ok") else "schedule needs station",
        7,
    )

    # Skybrary DB
    sky = settings.skybrary_db_path
    add("skybrary_db", sky.is_file(), "skybrary.db present" if sky.is_file() else "run skybrary samples", 10)

    # Bit-rot last report optional
    bitrot = settings.data_dir / "ops" / "bitrot-last.json"
    add(
        "bitrot",
        bitrot.is_file(),
        "bit-rot record present" if bitrot.is_file() else "optional: skybrary doctor --verify --record",
        5,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    # Pilot go: sim path solid even without dongle
    go_sim = all(
        next(c for c in checks if c["id"] == i)["ok"]
        for i in ("data_dir", "content", "product_import")
    )
    go_field_rf = go_sim and bool(ready.get("live_decode_path")) and st is not None

    return {
        "schema": READINESS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_pilot": go_sim,
        "go_field_rf": go_field_rf,
        "checks": checks,
        "rx_ready": ready,
        "legal": "Receive-only open content readiness - not free commercial broadband",
        "honest": (
            "go_sim_pilot is enough for classroom/NGO lab demos. "
            "go_field_rf needs SatDump stack + station; rtl_device optional if product import only."
        ),
        "next_steps": _readiness_next(checks, go_sim, go_field_rf),
    }


def _readiness_next(
    checks: list[dict[str, Any]], go_sim: bool, go_field_rf: bool
) -> list[str]:
    steps: list[str] = []
    failed = {c["id"] for c in checks if not c["ok"]}
    if "content" in failed:
        steps.append("skycache first-boot --yes --pin <PIN> --sim  (or init --load-samples)")
    if "skybrary_db" in failed:
        steps.append("skycache skybrary samples --ingest")
    if "station" in failed:
        steps.append("skycache rx station --lat LAT --lon LON")
    if "live_decode_path" in failed:
        steps.append("Install SatDump + rtl tools (Windows: scripts/Install-RxTools-Windows.ps1)")
    if "armed" in failed and go_sim:
        steps.append("Optional: skycache rx arm --hours 12")
    if "bitrot" in failed:
        steps.append("Optional: skycache skybrary doctor --verify --record")
    if go_sim and not go_field_rf:
        steps.append("Lab demo green - schedule field RF day only if antenna/dongle available")
    if go_field_rf:
        steps.append("Field RF path ready: schedule -> arm -> SatDump -> watch")
    if go_sim:
        steps.append("Build kit: skycache partner kit --type ngo --zip")
    return steps


def _zip_dir(src: Path, zip_path: Path) -> Path:
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.is_file():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=str(Path(src.name) / f.relative_to(src)))
    return zip_path


def _checklist(kit_type: str) -> list[dict[str, str]]:
    base = [
        {"id": "legal", "item": "Legal one-pager signed / acknowledged by partner lead"},
        {"id": "sim", "item": "Laptop sim portal green (serve --sim + samples)"},
        {"id": "pin", "item": "Admin PIN changed from default; written offline only"},
        {"id": "packs", "item": "emergency-health + literacy pack built and verified"},
        {"id": "phone", "item": "Phone without cell plan opens portal over hub Wi-Fi"},
        {"id": "license", "item": "License inventory HTML printed / PDF saved"},
        {"id": "power", "item": "Power maintainer sheet reviewed for site Wh"},
        {"id": "disaster", "item": "Disaster drill walked once (sim OK)"},
        {
            "id": "rx_autopilot",
            "item": "Pass Autopilot understood: schedule/arm or product-import-only path (no free broadband claims)",
        },
        {"id": "readiness", "item": "skycache partner readiness score reviewed (go_sim_pilot true)"},
        {"id": "report", "item": "pilot-report filled + partner report validate OK"},
    ]
    if kit_type == "university":
        base.append(
            {"id": "corpus", "item": "Student PD/CC corpus import with provenance report"}
        )
        base.append({"id": "tests", "item": "pytest -q green on lab machine"})
    if kit_type == "civil-protection":
        base.append({"id": "mesh2", "item": "2-node mesh validate (sim or physical checklist)"})
        base.append({"id": "mule", "item": "USB mule handoff restore demonstrated"})
    if kit_type == "ngo":
        base.append({"id": "train", "item": "Half-day training completed with local maintainer"})
    return base


def _checklist_md(kit_type: str, checklist: list[dict[str, str]]) -> str:
    lines = [f"# Partner checklist - {kit_type}", "", "Mark each item before field sign-off.", ""]
    for c in checklist:
        lines.append(f"- [ ] **{c['id']}**: {c['item']}")
    lines.append("")
    lines.append("Honest scope: not free commercial broadband; open content only.")
    return "\n".join(lines) + "\n"


def _checklist_html(kit_type: str, checklist: list[dict[str, str]], banner: str) -> str:
    rows = "".join(
        f"<li><label><input type='checkbox'/> <strong>{c['id']}</strong> - {c['item']}</label></li>"
        for c in checklist
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Partner checklist - {kit_type}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:1.5rem auto;padding:0 1rem;line-height:1.5}}
.banner{{background:#eff6ff;border:1px solid #bfdbfe;padding:.75rem;border-radius:8px;font-size:.9rem}}
li{{margin:.4rem 0}}
</style></head><body>
<h1>Partner checklist - {kit_type}</h1>
<div class="banner">{banner}</div>
<ul>{rows}</ul>
<p style="color:#64748b;font-size:.85rem">Print -> Save as PDF. Contact skycache@jonbailey.xyz</p>
</body></html>
"""


def _legal_one_pager() -> str:
    return """# SkyCache legal one-pager (partners)

- **Receive-only** satellite / RF reception in the core product
- **No** commercial constellation decryption (Starlink, OneWeb, paid VSAT, DRM)
- Mesh transmit: **unlicensed/ISM Wi-Fi** only (optional regional LoRa control); operator checks national rules
- Content: **public domain / Creative Commons / open / operator-authorized** only - track provenance; fail closed
- Health materials are **educational**, not diagnosis or prescription
- Software: **Apache-2.0**; third-party corpora keep their licenses
- Privacy: **no** third-party analytics by default; no personal-data harvest
- Honest marketing: **not** free internet, **not** a complete archive of everything

Contact: skycache@jonbailey.xyz  |  https://skycache.jonbailey.xyz/partners/
"""


def _training(kit_type: str) -> str:
    return f"""# Training half-day - {kit_type}

| Block | Topic |
|-------|--------|
| 30m | Honest mission: store-and-forward, not free Starlink |
| 30m | Legal rails + capability matrix walkthrough |
| 45m | First-boot + portal + Skybrary Library reader |
| 30m | Pack profiles + USB handoff + license passport |
| 20m | Pass Autopilot overview (schedule/arm) + product import without dongle |
| 25m | Power modes + maintainer sheet |
| 25m | Disaster drill dry-run (sim OK) |
| 15m | Fill pilot-report.template.json plan + `partner report validate` |

Field day adds mesh day-one only after spectrum check.
"""


def _field_day(kit_type: str) -> str:
    return f"""# Field day runbook - {kit_type}

## Lab first (required)

1. `skycache partner readiness --data-dir data`  (want go_sim_pilot true)
2. `skycache serve --sim` and open portal on a phone without cell data
3. Build packs: emergency-health + literacy-1gb
4. Print licenses HTML

## Optional live FTA weather

1. Station: `skycache rx station --lat LAT --lon LON`
2. Tools: SatDump + rtl CLI (Windows: Install-RxTools-Windows.ps1)
3. `skycache rx schedule --hours 24` then `skycache rx arm --hours 12`
4. Capture with SatDump into products folder
5. `skycache rx watch --dir PRODUCTS --once`
6. Do **not** claim free commercial broadband

## Close-out

1. Fill pilot-report.template.json
2. `skycache partner report validate pilot-report.json`
3. Email report to skycache@jonbailey.xyz subject `[{kit_type} pilot]`
"""
