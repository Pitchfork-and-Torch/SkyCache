"""Village Day Ops (v1.9.0): one weekend stand-up surface for a village node.

Aggregates phone handoff, mesh, gateway, partner/RX readiness, Skybrary samples,
and local ops into doctor + go/no-go readiness + printable runbook + kit zip.

Honest rails: receive-only satellite, unlicensed mesh TX, open content only,
not free commercial broadband. Sim green does not authorize RF.
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
    "Village day: stand up a local knowledge hub in a weekend. "
    "Receive-only satellite, unlicensed mesh TX, open content only. "
    "Not free commercial broadband or Starlink. Sim green is not RF authorization."
)

DOCTOR_SCHEMA = "skycache.village_day.doctor.v1"
READINESS_SCHEMA = "skycache.village_day.readiness.v1"
RUNBOOK_SCHEMA = "skycache.village_day.runbook.v1"
KIT_SCHEMA = "skycache.village_day.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _safe(call, *args, **kwargs) -> dict[str, Any]:
    try:
        return {"ok": True, "result": call(*args, **kwargs)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "result": None}


def village_day_doctor(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    sim: bool = True,
) -> dict[str, Any]:
    """Aggregate surface doctors into one weekend-stand-up report."""
    from skycache.capabilities.handoff_ops import handoff_doctor
    from skycache.nexus.field_mesh_ops import mesh_doctor
    from skycache.nexus.gateway_ops import gateway_doctor
    from skycache.partner_kit import partner_readiness
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.phone_demo import demos_ready, ensure_demo_texts

    settings = _settings(data_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    surfaces: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10, *, required: bool = False) -> None:
        checks.append(
            {
                "id": cid,
                "ok": bool(ok),
                "detail": detail,
                "weight": weight,
                "required": required,
            }
        )

    # Handoff
    h = _safe(handoff_doctor, data_dir=settings.data_dir)
    surfaces["handoff"] = h.get("result") if h["ok"] else {"error": h.get("error")}
    ho = h.get("result") or {}
    add(
        "handoff",
        bool(ho.get("go_phone_path")),
        f"score={ho.get('score')} go_phone={ho.get('go_phone_path')}" if h["ok"] else h.get("error", "fail"),
        14,
        required=True,
    )

    # Mesh
    m = _safe(mesh_doctor, data_dir=settings.data_dir, repo_root=repo_root)
    surfaces["mesh"] = m.get("result") if m["ok"] else {"error": m.get("error")}
    mo = m.get("result") or {}
    add(
        "mesh_sim",
        bool(mo.get("go_sim_mesh")),
        f"score={mo.get('score')} go_sim={mo.get('go_sim_mesh')}" if m["ok"] else m.get("error", "fail"),
        12,
        required=True,
    )
    add(
        "mesh_field",
        bool(mo.get("go_field_mesh")),
        "field mesh hardware ready" if mo.get("go_field_mesh") else "field mesh optional until spectrum day",
        6,
        required=False,
    )

    # Gateway
    g = _safe(gateway_doctor, data_dir=settings.data_dir, sim=sim)
    surfaces["gateway"] = g.get("result") if g["ok"] else {"error": g.get("error")}
    go = g.get("result") or {}
    add(
        "gateway",
        bool(go.get("go_sim_gateway")),
        f"score={go.get('score')} go_sim={go.get('go_sim_gateway')}" if g["ok"] else g.get("error", "fail"),
        12,
        required=True,
    )

    # Partner / RX readiness
    p = _safe(partner_readiness, data_dir=settings.data_dir)
    surfaces["partner"] = p.get("result") if p["ok"] else {"error": p.get("error")}
    po = p.get("result") or {}
    add(
        "partner_sim",
        bool(po.get("go_sim_pilot")),
        f"score={po.get('score')} go_sim_pilot={po.get('go_sim_pilot')}" if p["ok"] else p.get("error", "fail"),
        14,
        required=True,
    )
    add(
        "partner_rf",
        bool(po.get("go_field_rf")),
        "field RF path ready" if po.get("go_field_rf") else "RX field optional for classroom weekend",
        5,
        required=False,
    )

    # Content + demos
    content = settings.content_dir
    pkgs = (
        [x.name for x in content.iterdir() if x.is_dir() and (x / "manifest.json").is_file()]
        if content.is_dir()
        else []
    )
    add("content_packages", len(pkgs) >= 1, f"{len(pkgs)} packages", 12, required=True)

    demos = False
    sky_n = 0
    try:
        sky = SkybraryCatalog(settings.skybrary_db_path)
        try:
            ensure_demo_texts(settings, sky)
            demos = demos_ready(settings, sky)
            sky_n = sky.count()
        finally:
            sky.close()
    except Exception as exc:  # noqa: BLE001
        add("skybrary_demos", False, str(exc), 10, required=True)
    else:
        add(
            "skybrary_demos",
            demos,
            f"works={sky_n} demos_ready={demos}",
            10,
            required=True,
        )

    # Local ops snapshot
    local = local_ops_snapshot(settings, sky_count=sky_n)
    surfaces["local_ops"] = local
    free = (local.get("disk") or {}).get("free_bytes")
    disk_ok = free is None or int(free) > 200 * 1024 * 1024
    add(
        "disk_space",
        disk_ok,
        f"free_bytes={free}" if free is not None else "disk ok/unknown",
        8,
        required=True,
    )

    # Docs present
    docs = {
        "first-boot.md": repo_root / "docs" / "first-boot.md",
        "disaster-drill.md": repo_root / "docs" / "disaster-drill.md",
        "mesh-field-checklist.md": repo_root / "docs" / "mesh-field-checklist.md",
    }
    docs_ok = all(p.is_file() for p in docs.values())
    add("field_docs", docs_ok, "first-boot + disaster + mesh checklist" if docs_ok else "missing field docs", 7)

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    required_ok = all(c["ok"] for c in checks if c.get("required"))
    go_weekend_sim = required_ok and score >= 70
    go_weekend_field = go_weekend_sim and bool(mo.get("go_field_mesh")) and bool(po.get("go_field_rf"))

    blockers = [c["id"] for c in checks if c.get("required") and not c["ok"]]
    optional_gaps = [c["id"] for c in checks if not c.get("required") and not c["ok"]]

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_weekend_sim": go_weekend_sim,
        "go_weekend_field": go_weekend_field,
        "blockers": blockers,
        "optional_gaps": optional_gaps,
        "checks": checks,
        "surfaces": {
            "handoff_go": ho.get("go_phone_path"),
            "mesh_sim": mo.get("go_sim_mesh"),
            "mesh_field": mo.get("go_field_mesh"),
            "gateway_sim": go.get("go_sim_gateway"),
            "partner_sim": po.get("go_sim_pilot"),
            "partner_rf": po.get("go_field_rf"),
            "package_count": len(pkgs),
            "skybrary_works": sky_n,
        },
        "local_ops": local,
        "banner": HONEST,
        "next_steps": _next_steps(blockers, go_weekend_sim, go_weekend_field),
        "legal": (
            "Sim weekend path needs no RF. Field path still requires spectrum check, "
            "legal_rf_mode, and operator-hosted sealed images when cloning fleets."
        ),
    }


def _next_steps(blockers: list[str], go_sim: bool, go_field: bool) -> list[str]:
    steps: list[str] = []
    if "content_packages" in blockers or "skybrary_demos" in blockers:
        steps.append(
            "skycache first-boot --data-dir data --yes --pin 739184 --ssid SkyCache-Sim "
            "--legal-rf-mode receive_only --sim"
        )
        steps.append("skycache skybrary samples --ingest")
    if "handoff" in blockers:
        steps.append("skycache handoff doctor  # then handoff export after packages exist")
    if "mesh_sim" in blockers:
        steps.append("skycache mesh readiness --nodes 2")
    if "gateway" in blockers:
        steps.append("skycache gateway doctor")
    if "partner_sim" in blockers:
        steps.append("skycache partner readiness")
    if "disk_space" in blockers:
        steps.append("Free disk on data volume (need ~200MB+ free for packs)")
    if go_sim and not go_field:
        steps.append("Sim weekend green - schedule spectrum/RF day only when hardware ready")
    if go_sim:
        steps.append("skycache village-day runbook --out data/village-day")
        steps.append("skycache village-day kit --out data/village-day-kit")
        steps.append("python -m skycache serve --sim --host 127.0.0.1 --port 8080")
    if go_field:
        steps.append("Field weekend: mesh day-one after spectrum check + RX watch if dongle present")
    return steps


def village_day_readiness(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    sim: bool = True,
) -> dict[str, Any]:
    """Compact go/no-go receipt (writes data/ops/village-day-last.json)."""
    doc = village_day_doctor(data_dir=data_dir, repo_root=repo_root, sim=sim)
    settings = _settings(data_dir)
    receipt = {
        "schema": READINESS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": doc["score"],
        "go_weekend_sim": doc["go_weekend_sim"],
        "go_weekend_field": doc["go_weekend_field"],
        "blockers": doc["blockers"],
        "optional_gaps": doc["optional_gaps"],
        "surfaces": doc["surfaces"],
        "banner": HONEST,
        "next_steps": doc["next_steps"],
    }
    out = settings.data_dir / "ops" / "village-day-last.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(out)
    return receipt


def write_village_day_runbook(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Write RUNBOOK.md + doctor JSON for a weekend stand-up."""
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = village_day_doctor(data_dir=settings.data_dir, repo_root=repo_root, sim=True)
    ready = village_day_readiness(data_dir=settings.data_dir, repo_root=repo_root, sim=True)

    (out_dir / "village-day-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "village-day-readiness.json").write_text(
        json.dumps(ready, indent=2) + "\n", encoding="utf-8"
    )

    md = f"""# Village Day Runbook (SkyCache v{__version__})

{HONEST}

**Score:** {doc["score"]} / 100  
**go_weekend_sim:** {doc["go_weekend_sim"]}  
**go_weekend_field:** {doc["go_weekend_field"]}  
**Blockers:** {", ".join(doc["blockers"]) or "none"}

## Goal (one weekend)

Stand up a **local** knowledge hub: packages + Skybrary demos, phone join path, optional mesh/gateway/RX.
Do **not** promise free commercial satellite internet.

## Morning - lab (no RF required)

1. Install Python 3.11+ and this repo (`pip install -e ".[dev]"`).
2. First-boot sim:
   ```text
   python -m skycache first-boot --data-dir data --yes --pin 739184 \\
     --ssid SkyCache-Sim --legal-rf-mode receive_only --sim
   ```
3. Samples + demos:
   ```text
   python -m skycache skybrary samples --ingest
   python -m skycache village-day doctor
   ```
4. Want **go_weekend_sim true** before inviting visitors.

## Midday - phone path

1. `python -m skycache handoff join-card --portal-url http://10.42.0.1:8080/ --ssid SkyCache-Village`
2. `python -m skycache handoff export --limit 10`
3. `python -m skycache serve --sim --host 127.0.0.1 --port 8080`
4. Phone (or second laptop): open portal, Library → Save demos (no cell plan).

## Afternoon - optional fabric

1. Mesh lab: `python -m skycache mesh readiness --nodes 2` then `mesh disaster-drill --nodes 3` (disable disaster after).
2. Gateway ethics: `python -m skycache gateway pull-preset gutenberg-sample --dry-run` then `--sim`.
3. Partner kit: `python -m skycache partner kit --type ngo --zip`.

## Field day only (hardware)

1. Spectrum check; set `legal_rf_mode` appropriately (ISM mesh vs receive_only).
2. Pi golden path: `/install/` kit + non-default PIN (never 2468).
3. Mesh day-one after dual-radio plan; RX watch only with SatDump products you may legally keep.

## End of day

1. `python -m skycache village-day readiness` (receipt under data/ops/).
2. `python -m skycache village-day kit --out data/village-day-kit` for USB handoff to the next maintainer.
3. Print or share RUNBOOK.md; turn disaster mode OFF if used.

## Commands cheat sheet

```text
python -m skycache village-day doctor
python -m skycache village-day readiness
python -m skycache village-day runbook --out data/village-day
python -m skycache village-day kit --out data/village-day-kit
python -m skycache handoff export --limit 10
python -m skycache mesh readiness --nodes 2
python -m skycache gateway doctor
python -m skycache partner readiness
python -m skycache ops status
```

Generated: {doc["generated_at"]}
"""
    (out_dir / "RUNBOOK.md").write_text(md, encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# Village day pack\n\n{HONEST}\n\nSee RUNBOOK.md.\n",
        encoding="utf-8",
    )

    return {
        "schema": RUNBOOK_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "go_weekend_sim": doc["go_weekend_sim"],
        "score": doc["score"],
        "files": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
        "banner": HONEST,
    }


def write_village_day_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Full kit: runbook + copied field doc pointers + zip for site/USB."""
    settings = _settings(data_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rb = write_village_day_runbook(out_dir, data_dir=settings.data_dir, repo_root=repo_root)

    docs_dir = out_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    for name in (
        "first-boot.md",
        "disaster-drill.md",
        "mesh-field-checklist.md",
        "phone-offline-demo.md",
        "threat-model.md",
    ):
        src = repo_root / "docs" / name
        if src.is_file():
            (docs_dir / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Village Day Field Checklist

{HONEST}

- [ ] village-day doctor go_weekend_sim true
- [ ] first-boot done with non-default PIN
- [ ] handoff join card printed or displayed
- [ ] phones join hub SSID; demos saved offline
- [ ] (optional) mesh readiness sim green
- [ ] (optional) gateway dry-run + ethics reviewed
- [ ] (optional) partner kit zip on USB
- [ ] disaster mode OFF at end of day
- [ ] village-day readiness receipt saved
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
                "download_hint": "/downloads/skycache-village-day-kit.zip",
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
        "runbook": rb,
        "score": rb.get("score"),
        "go_weekend_sim": rb.get("go_weekend_sim"),
        "banner": HONEST,
    }
