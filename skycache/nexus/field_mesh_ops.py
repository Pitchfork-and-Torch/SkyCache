"""Field Mesh Ops (v1.6.0): doctor, readiness, disaster drill receipt, field kit zip.

Unifies sim mesh validation, day-one batman plan, dual-radio pack, and disaster
drill into an operator surface. Unlicensed Wi-Fi/ISM only. No satellite TX.
Not free commercial broadband.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.nexus.mesh_day_one import day_one_plan, detect_mesh_environment
from skycache.nexus.mesh_validate import validate_mesh_sim

HONEST = (
    "Field mesh: unlicensed Wi-Fi/ISM only. Receive-only satellite. "
    "Not free commercial broadband or Starlink. Sim validates fabric without RF."
)

DOCTOR_SCHEMA = "skycache.mesh.doctor.v1"
READINESS_SCHEMA = "skycache.mesh.readiness.v1"
DRILL_SCHEMA = "skycache.mesh.disaster_drill.v1"
KIT_SCHEMA = "skycache.mesh.field_kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mesh_doctor(*, data_dir: Path | None = None, repo_root: Path | None = None) -> dict[str, Any]:
    """Host + docs readiness for field mesh (non-destructive)."""
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    env = detect_mesh_environment()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    add("sim_path", True, "nexus validate sim always available", 15)
    add(
        "linux",
        bool(env.get("is_linux")),
        "Linux host for batman-adv" if env.get("is_linux") else f"OS={env.get('system')} (sim only here)",
        12,
    )
    add("batctl", bool(env.get("batctl")), env.get("batctl") or "batctl not on PATH", 12)
    add(
        "batman_module",
        bool(env.get("batman_module_loaded")),
        "batman_adv module loaded" if env.get("batman_module_loaded") else "module not loaded (ok until field day)",
        8,
    )
    add("iw", bool(env.get("iw")), env.get("iw") or "iw optional", 5)
    add("ip", bool(env.get("ip")), env.get("ip") or "ip optional", 5)

    docs = {
        "mesh-deployment.md": repo_root / "docs" / "mesh-deployment.md",
        "mesh-field-checklist.md": repo_root / "docs" / "mesh-field-checklist.md",
        "disaster-drill.md": repo_root / "docs" / "disaster-drill.md",
        "batman-day-one.sh": repo_root / "deploy" / "mesh" / "batman-day-one.sh",
    }
    for name, p in docs.items():
        add(f"doc_{name.split('.')[0][:12]}", p.is_file(), str(p) if p.is_file() else f"missing {name}", 6)

    dual = repo_root / "media" / "dual-radio-validation"
    dual_ok = (dual / "board-matrix.json").is_file() or (dual / "storyboard.html").is_file()
    add(
        "dual_radio_pack",
        dual_ok,
        "dual-radio validation media present" if dual_ok else "run mesh dual-radio-pack",
        8,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_sim = True
    go_field = bool(env.get("hardware_oob_ready"))

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_mesh": go_sim,
        "go_field_mesh": go_field,
        "environment": env,
        "checks": checks,
        "banner": HONEST,
        "next_steps": _doctor_next(go_field, env),
        "legal": "Unlicensed mesh TX only after spectrum check; no satellite uplink",
    }


def _doctor_next(go_field: bool, env: dict[str, Any]) -> list[str]:
    steps = [
        "skycache nexus validate --nodes 2",
        "skycache nexus validate --nodes 3 --disaster",
        "skycache mesh day-one --write",
        "skycache mesh readiness",
    ]
    if not go_field:
        steps.append("Field day needs Linux + batctl + dual radios; keep sim green until then")
    else:
        steps.append("docs/mesh-field-checklist.md then optional: mesh day-one --apply --yes")
    steps.append("skycache mesh disaster-drill --nodes 3")
    return steps


def mesh_readiness(
    *,
    data_dir: Path | None = None,
    nodes: int = 2,
    run_sim: bool = True,
) -> dict[str, Any]:
    """go_sim_mesh / go_field_mesh score with optional live sim validation."""
    data_dir = Path(data_dir) if data_dir else Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    doc = mesh_doctor(data_dir=data_dir)
    sim_report: dict[str, Any] | None = None
    if run_sim:
        sim_report = validate_mesh_sim(
            nodes=max(2, int(nodes)),
            base_dir=data_dir / "mesh-readiness-sim",
            disaster=False,
            keep=False,
        )
    sim_ok = bool(sim_report and sim_report.get("ok")) if run_sim else True
    go_sim = sim_ok and bool(doc.get("go_sim_mesh"))
    go_field = bool(doc.get("go_field_mesh")) and go_sim

    # Weighted score blends doctor + sim
    doc_score = int(doc.get("score") or 0)
    sim_score = 100 if sim_ok else 40
    score = int(round(0.55 * doc_score + 0.45 * sim_score)) if run_sim else doc_score

    out = {
        "schema": READINESS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_mesh": go_sim,
        "go_field_mesh": go_field,
        "doctor": doc,
        "sim_validate": sim_report,
        "banner": HONEST,
        "legal": "Sim green does not authorize RF; spectrum check still required",
    }
    path = data_dir / "nexus" / "mesh-readiness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    out["written"] = str(path)
    return out


def run_disaster_drill(
    *,
    nodes: int = 3,
    data_dir: Path | None = None,
    keep: bool = False,
) -> dict[str, Any]:
    """Lab disaster priority flood + receipt JSON (no RF)."""
    data_dir = Path(data_dir) if data_dir else Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    base = data_dir / "disaster-drill-sim"
    report = validate_mesh_sim(
        nodes=max(2, int(nodes)),
        base_dir=base,
        disaster=True,
        keep=keep,
    )
    receipt = {
        "schema": DRILL_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "ok": bool(report.get("ok")),
        "nodes": int(nodes),
        "disaster": True,
        "sim": report,
        "banner": HONEST,
        "field_note": (
            "Lab sim only. Real field drills: docs/disaster-drill.md - "
            "turn Disaster mode OFF after exercise."
        ),
        "checklist_ref": "docs/disaster-drill.md",
        "partner_closeout": [
            "Fill partner pilot-report if institutional drill",
            "skycache partner report validate pilot-report.json",
            "Disable disaster mode on live nodes",
        ],
    }
    path = data_dir / "ops" / "disaster-drill-last.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt["written"] = str(path)
    return receipt


def build_field_mesh_kit(
    out_dir: Path,
    *,
    repo_root: Path | None = None,
    make_zip: bool = True,
) -> dict[str, Any]:
    """Operator field-mesh kit: checklists, day-one plan, dual-radio refs."""
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    out_dir = Path(out_dir)
    if out_dir.exists():
        for child in list(out_dir.iterdir()):
            if child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir() and child.name in ("docs", "deploy", "media"):
                shutil.rmtree(child, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = day_one_plan(data_dir=None)
    doc = mesh_doctor(repo_root=repo_root)
    (out_dir / "mesh-day-one-plan.json").write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "mesh-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )

    copy_map = {
        "docs/mesh-deployment.md": repo_root / "docs" / "mesh-deployment.md",
        "docs/mesh-field-checklist.md": repo_root / "docs" / "mesh-field-checklist.md",
        "docs/mesh-dual-radio-validation.md": repo_root / "docs" / "mesh-dual-radio-validation.md",
        "docs/disaster-drill.md": repo_root / "docs" / "disaster-drill.md",
        "deploy/mesh/batman-day-one.sh": repo_root / "deploy" / "mesh" / "batman-day-one.sh",
        "deploy/mesh/README.md": repo_root / "deploy" / "mesh" / "README.md",
        "deploy/disaster-drill-sim.sh": repo_root / "deploy" / "disaster-drill-sim.sh",
    }
    included: list[str] = []
    for rel, src in copy_map.items():
        if not src.is_file():
            continue
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        included.append(rel)

    # Lightweight dual-radio board matrix if present
    matrix = repo_root / "media" / "dual-radio-validation" / "board-matrix.json"
    if matrix.is_file():
        dest = out_dir / "media" / "dual-radio-validation" / "board-matrix.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(matrix, dest)
        included.append("media/dual-radio-validation/board-matrix.json")
    story = repo_root / "media" / "dual-radio-validation" / "storyboard.html"
    if story.is_file():
        dest = out_dir / "media" / "dual-radio-validation" / "storyboard.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(story, dest)
        included.append("media/dual-radio-validation/storyboard.html")

    readme = f"""# SkyCache field mesh kit v{__version__}

{HONEST}

## Lab first (required)

1. skycache mesh doctor
2. skycache mesh readiness --nodes 2
3. skycache mesh disaster-drill --nodes 3
4. skycache nexus validate --nodes 2

## Field day

1. Spectrum check (national unlicensed rules)
2. Dual radios: MESH_IF vs CLIENT_IF
3. Follow docs/mesh-field-checklist.md
4. skycache mesh day-one --write  (optional --apply --yes on Linux+root)
5. After drill: disable disaster mode

## Legal

- Mesh TX: unlicensed Wi-Fi/ISM only
- Satellite: receive-only FTA
- Not free Starlink
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        """# Field mesh checklist (kit copy)

- [ ] Spectrum / legal RF mode ism_mesh affirmed
- [ ] Lab sim green: mesh readiness go_sim_mesh
- [ ] Two radios identified (mesh vs client AP)
- [ ] batman day-one plan written
- [ ] 2-node physical checklist complete
- [ ] Phones join client SSID without cell data
- [ ] Disaster drill walked (sim or field)
- [ ] Disaster mode OFF after exercise
- [ ] No free-broadband claims in partner briefings
""",
        encoding="utf-8",
    )

    hosting = {
        "schema": KIT_SCHEMA,
        "software_version": __version__,
        "built_at": _iso_now(),
        "banner": HONEST,
        "site_path": "/downloads/field-mesh-kit/",
        "files": included,
        "cli": [
            "skycache mesh doctor",
            "skycache mesh readiness --nodes 2",
            "skycache mesh disaster-drill --nodes 3",
            "skycache mesh day-one --write",
            "skycache mesh dual-radio-pack --out media/dual-radio-validation",
        ],
    }
    (out_dir / "HOSTING.json").write_text(
        json.dumps(hosting, indent=2) + "\n", encoding="utf-8"
    )

    zip_path: str | None = None
    if make_zip:
        zp = out_dir.parent / "skycache-field-mesh-kit.zip"
        if zp.is_file():
            zp.unlink()
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=f"skycache-field-mesh-kit/{f.relative_to(out_dir).as_posix()}")
        zip_path = str(zp)

    return {
        "ok": True,
        "out_dir": str(out_dir),
        "zip": zip_path,
        "hosting": hosting,
        "software_version": __version__,
        "banner": HONEST,
    }
