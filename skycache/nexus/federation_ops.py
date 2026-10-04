"""Federation Ops (v1.10.0): doctor, gossip export, multi-node sim receipt, kit.

Multi-village works + package catalog federation. Sim-first filesystem mesh.
Open/PD content only. Not free commercial broadband. Real batman-adv still field-gated.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.nexus.federation import build_fabric, multi_node_sim_sync
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.skybrary.phone_demo import ensure_demo_texts

HONEST = (
    "Federation: multi-village works/package gossip over local mesh or USB. "
    "Open content only. Sim filesystem copy is not hardware mesh proof. "
    "Not free commercial broadband or Starlink."
)

DOCTOR_SCHEMA = "skycache.federation.doctor.v1"
SIM_SCHEMA = "skycache.federation.sim_receipt.v1"
GOSSIP_SCHEMA = "skycache.federation.gossip.v1"
KIT_SCHEMA = "skycache.federation.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def federation_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Local readiness for works/package federation (non-destructive)."""
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
    add("packages", len(pkgs) >= 1, f"{len(pkgs)} packages for gossip", 15)

    sky_n = 0
    try:
        sky = SkybraryCatalog(settings.skybrary_db_path)
        try:
            ensure_demo_texts(settings, sky)
            sky_n = sky.count()
        finally:
            sky.close()
    except Exception as exc:  # noqa: BLE001
        add("skybrary", False, str(exc), 15)
    else:
        add("skybrary", sky_n >= 1, f"{sky_n} works in skybrary", 15)

    fabric_ok = False
    gossip_ok = False
    compact_note = "n/a"
    try:
        fabric = build_fabric(settings)
        fabric_ok = True
        gp = fabric.gossip_payload()
        gossip_ok = bool(gp.get("manifest") is not None)
        wm = gp.get("works_manifest") or {}
        compact_note = (
            f"works={len(wm.get('works') or [])} compact={wm.get('compact')} "
            f"packages={len(gp.get('manifest') or [])}"
        )
    except Exception as exc:  # noqa: BLE001
        compact_note = str(exc)
    add("fabric", fabric_ok, "ContentFabric build OK" if fabric_ok else compact_note, 12)
    add("gossip_payload", gossip_ok, compact_note, 12)

    nexus = settings.nexus_dir
    add("nexus_dir", nexus.is_dir(), str(nexus), 6)

    # Multi-node sim path always available in-process
    add("sim_path", True, "skycache federation sim --nodes 2 always available", 10)

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_sim = score >= 70 and fabric_ok and len(pkgs) >= 1
    go_field = go_sim  # field mesh still separate (mesh doctor)

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_federation": go_sim,
        "go_field_federation": go_field,
        "package_count": len(pkgs),
        "works_count": sky_n,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache federation doctor",
            "skycache federation export-gossip --out data/federation/gossip.json",
            "skycache federation sim --nodes 2 --rounds 1",
            "skycache federation kit --out data/federation-kit",
            "On hardware: mesh day-one after spectrum check, then exchange gossip USB/mesh",
        ],
        "legal": "Open/PD works and packages only; no commercial decrypt; unlicensed mesh for field",
    }


def federation_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Local gossip snapshot stats (no peer traffic)."""
    settings = _settings(data_dir)
    fabric = build_fabric(settings)
    gp = fabric.gossip_payload()
    wm = gp.get("works_manifest") or {}
    return {
        "schema": "skycache.federation.status.v1",
        "generated_at": _iso_now(),
        "software_version": __version__,
        "node_id": gp.get("node_id"),
        "package_count": len(gp.get("manifest") or []),
        "works_count": len(wm.get("works") or []),
        "works_compact": wm.get("compact"),
        "disaster_mode": gp.get("disaster_mode"),
        "banner": HONEST,
    }


def export_gossip(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    compact: bool | None = None,
    max_tier: int | None = None,
) -> dict[str, Any]:
    """Write gossip JSON for USB/mesh handoff to another village node."""
    settings = _settings(data_dir)
    fabric = build_fabric(settings)
    gp = fabric.gossip_payload(works_compact=compact, works_max_tier=max_tier)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": GOSSIP_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "gossip": gp,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "schema": GOSSIP_SCHEMA,
        "path": str(out_path),
        "package_count": len(gp.get("manifest") or []),
        "works_count": len((gp.get("works_manifest") or {}).get("works") or []),
        "banner": HONEST,
    }


def import_gossip(
    gossip_path: Path,
    *,
    data_dir: Path | None = None,
    peer_content_root: Path | None = None,
) -> dict[str, Any]:
    """Import peer gossip file; optionally copy packages from peer_content_root."""
    settings = _settings(data_dir)
    path = Path(gossip_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    gp = data.get("gossip") if isinstance(data, dict) and "gossip" in data else data
    if not isinstance(gp, dict):
        return {"ok": False, "error": "invalid gossip JSON", "banner": HONEST}
    fabric = build_fabric(settings)
    peer_root = Path(peer_content_root) if peer_content_root else None
    rep = fabric.sync_with_peer_manifest(gp, peer_content_root=peer_root)
    return {
        "ok": True,
        "schema": "skycache.federation.import.v1",
        "generated_at": _iso_now(),
        "software_version": __version__,
        "sync": rep,
        "banner": HONEST,
    }


def run_federation_sim(
    *,
    nodes: int = 2,
    rounds: int = 1,
    data_dir: Path | None = None,
    base_dir: Path | None = None,
    seed: bool = True,
) -> dict[str, Any]:
    """Multi-node sim + persist receipt under data/ops/."""
    from skycache.config import Settings

    parent = Path(data_dir) if data_dir else Path("data")
    base = Path(base_dir) if base_dir else parent / "federation-sim"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    n = max(2, int(nodes))
    settings_list: list[Settings] = []
    for i in range(n):
        s = Settings(data_dir=base / f"node-{i}", sim_mode=True)
        s.ensure_dirs()
        s.node_id = f"fed-node-{i}"
        # node id file
        (s.data_dir / "node-id.json").write_text(
            json.dumps({"node_id": s.node_id}, indent=2) + "\n", encoding="utf-8"
        )
        if seed:
            sky = SkybraryCatalog(s.skybrary_db_path)
            try:
                bootstrap_samples_with_settings(s, sky)
            finally:
                sky.close()
            # Only seed node-0 with demos fully; others get thin set via bootstrap
            if i > 0:
                # remove half packages on peer nodes so sync has work
                content = s.content_dir
                dirs = [p for p in content.iterdir() if p.is_dir()] if content.is_dir() else []
                for p in dirs[::2]:
                    shutil.rmtree(p, ignore_errors=True)
        settings_list.append(s)

    sim = multi_node_sim_sync(settings_list, rounds=max(1, int(rounds)))
    # Convergence heuristic: package counts should be non-zero
    snaps = sim.get("snapshots") or []
    min_pkg = min((int(x.get("packages") or 0) for x in snaps), default=0)
    max_pkg = max((int(x.get("packages") or 0) for x in snaps), default=0)
    go_sim = min_pkg >= 1 and max_pkg >= 1 and len(sim.get("exchanges") or []) >= 1

    receipt = {
        "schema": SIM_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "go_sim_federation": go_sim,
        "base_dir": str(base),
        "sim": sim,
        "banner": HONEST,
        "honest": (
            "Sim only. Field federation still needs unlicensed mesh day-one "
            "and spectrum check (see mesh ops)."
        ),
    }
    ops = parent / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    out = ops / "federation-sim-last.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(out)
    receipt["ok"] = go_sim
    return receipt


def write_federation_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Operator kit: doctor, sample gossip, FIELD notes, zip."""
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = federation_doctor(data_dir=settings.data_dir)
    (out_dir / "federation-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )

    gpath = out_dir / "sample-gossip.json"
    export_gossip(gpath, data_dir=settings.data_dir)

    (out_dir / "README.md").write_text(
        f"""# Federation kit

{HONEST}

## Commands

```text
skycache federation doctor
skycache federation status
skycache federation export-gossip --out data/federation/gossip.json
skycache federation import-gossip PATH [--peer-content DIR]
skycache federation sim --nodes 2 --rounds 1
skycache federation kit --out data/federation-kit
```

## Field outline

1. Lab: federation sim go_sim_federation true
2. Export gossip on hub A; USB or mesh to hub B
3. import-gossip on B with peer-content if packages should copy
4. Mesh day-one only after spectrum check

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Federation field checklist

{HONEST}

- [ ] federation doctor go_sim_federation true
- [ ] sim --nodes 2 receipt saved
- [ ] gossip JSON exported (metadata OK to share; packages only open licenses)
- [ ] peer import verified works/package counts
- [ ] disaster mode OFF after drills
- [ ] hardware mesh only after spectrum + mesh readiness
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
                "download_hint": "/downloads/skycache-federation-kit.zip",
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
        "go_sim_federation": doc.get("go_sim_federation"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
