"""Dual Radio Ops (v1.22.0): doctor, status, printable board, validation kit.

Elevates dual-radio mesh validation matrix + storyboard into a product surface.
Unlicensed Wi-Fi/ISM only. Sim path always green. Not free commercial broadband.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.nexus.dual_radio_validation import (
    BOARD_MODELS,
    STORYBOARD_FRAMES,
    board_matrix,
    write_validation_pack,
)
from skycache.nexus.mesh_day_one import detect_mesh_environment

HONEST = (
    "Dual-radio ops: village mesh day-one proof across board models. "
    "Unlicensed Wi-Fi/ISM only. Receive-only satellite. "
    "Sim path always available. Not free commercial broadband or Starlink."
)

DOCTOR_SCHEMA = "skycache.dual_radio.doctor.v1"
STATUS_SCHEMA = "skycache.dual_radio.status.v1"
EXPORT_SCHEMA = "skycache.dual_radio.export.v1"
KIT_SCHEMA = "skycache.dual_radio.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root(repo_root: Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root)
    return Path(__file__).resolve().parents[2]


def dual_radio_doctor(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Readiness for dual-radio validation pack + sim vs field soak."""
    root = _repo_root(repo_root)
    env = detect_mesh_environment()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    add("board_matrix", True, f"{len(BOARD_MODELS)} board models in matrix", 15)
    add("storyboard_frames", True, f"{len(STORYBOARD_FRAMES)} storyboard frames", 12)

    doc_path = root / "docs" / "mesh-dual-radio-validation.md"
    add(
        "doc_dual_radio",
        doc_path.is_file(),
        str(doc_path) if doc_path.is_file() else "missing docs/mesh-dual-radio-validation.md",
        10,
    )
    day_one = root / "deploy" / "mesh" / "batman-day-one.sh"
    add(
        "batman_day_one",
        day_one.is_file(),
        str(day_one) if day_one.is_file() else "missing deploy/mesh/batman-day-one.sh",
        10,
    )
    checklist = root / "docs" / "mesh-field-checklist.md"
    add(
        "field_checklist",
        checklist.is_file(),
        str(checklist) if checklist.is_file() else "missing mesh-field-checklist.md",
        8,
    )

    media = root / "media" / "dual-radio-validation"
    pack_present = (media / "board-matrix.json").is_file() or (
        media / "storyboard.html"
    ).is_file()
    add(
        "validation_pack",
        pack_present,
        "media/dual-radio-validation present"
        if pack_present
        else "run dual-radio kit (or mesh dual-radio-pack)",
        10,
    )

    add("sim_path", True, "skycache nexus validate --nodes 2 always available", 12)
    add(
        "linux_host",
        bool(env.get("is_linux")),
        "Linux host for batman-adv field soak"
        if env.get("is_linux")
        else f"OS={env.get('system')} (sim + storyboard only here)",
        8,
    )
    add(
        "batctl",
        bool(env.get("batctl")),
        env.get("batctl") or "batctl not on PATH (ok until field soak)",
        6,
    )

    if data_dir is not None:
        data_dir = Path(data_dir)
        ops_note = data_dir / "ops" / "dual-radio-last.json"
        add(
            "ops_snapshot",
            ops_note.is_file() or True,
            "optional dual-radio-last.json under data/ops",
            4,
        )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))

    go_sim = True
    go_field = bool(env.get("hardware_oob_ready")) and pack_present

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_validation": go_sim,
        "go_field_soak": go_field,
        "board_count": len(BOARD_MODELS),
        "frame_count": len(STORYBOARD_FRAMES),
        "pack_present": pack_present,
        "environment": {
            "system": env.get("system"),
            "is_linux": env.get("is_linux"),
            "batctl": bool(env.get("batctl")),
            "hardware_oob_ready": bool(env.get("hardware_oob_ready")),
        },
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache dual-radio status",
            "skycache dual-radio export --out data/ops/dual-radio-board.html",
            "skycache dual-radio kit --out data/dual-radio-kit",
            "skycache nexus validate --nodes 2",
            "On Linux field: MESH_IF=... CLIENT_IF=... bash deploy/mesh/batman-day-one.sh",
        ],
        "legal": (
            "Unlicensed mesh TX only after spectrum check; no satellite uplink; "
            "not free commercial broadband"
        ),
    }


def dual_radio_status(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    doc = dual_radio_doctor(data_dir=data_dir, repo_root=repo_root)
    matrix = board_matrix()
    boards = [
        {
            "id": b.get("id"),
            "name": b.get("name"),
            "status": b.get("status"),
            "mesh_radio": b.get("mesh_radio"),
        }
        for b in (matrix.get("boards") or BOARD_MODELS)
    ]
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "score": doc.get("score"),
        "go_sim_validation": doc.get("go_sim_validation"),
        "go_field_soak": doc.get("go_field_soak"),
        "board_count": doc.get("board_count"),
        "frame_count": doc.get("frame_count"),
        "pack_present": doc.get("pack_present"),
        "boards": boards,
        "shared_validation": matrix.get("shared_validation"),
        "legal": doc.get("legal"),
        "environment": doc.get("environment"),
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_dual_radio_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Printable dual-radio validation readiness board."""
    doc = dual_radio_doctor(data_dir=data_dir, repo_root=repo_root)
    st = dual_radio_status(data_dir=data_dir, repo_root=repo_root)
    check_rows = []
    for c in doc.get("checks") or []:
        mark = "OK" if c.get("ok") else "FAIL"
        check_rows.append(
            f"<tr><td>{_esc(mark)}</td><td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('detail'))}</td></tr>"
        )
    checks_body = "\n".join(check_rows) or "<tr><td colspan='3'>(none)</td></tr>"

    board_rows = []
    for b in st.get("boards") or []:
        board_rows.append(
            f"<tr><td>{_esc(b.get('name'))}</td><td>{_esc(b.get('status'))}</td>"
            f"<td>{_esc(b.get('mesh_radio'))}</td></tr>"
        )
    boards_body = "\n".join(board_rows) or "<tr><td colspan='3'>(none)</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache dual-radio board</title>
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
<h1>Dual-radio validation board</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score <strong>{doc.get('score')}</strong>
 · go_sim_validation={doc.get('go_sim_validation')}
 · go_field_soak={doc.get('go_field_soak')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<p class="meta">Boards: {doc.get('board_count')} · frames: {doc.get('frame_count')} · pack_present={doc.get('pack_present')}</p>
<h2>Board matrix (summary)</h2>
<table>
<thead><tr><th>Board</th><th>Status</th><th>Mesh radio</th></tr></thead>
<tbody>
{boards_body}
</tbody>
</table>
<h2>Checks</h2>
<table>
<thead><tr><th>OK</th><th>ID</th><th>Detail</th></tr></thead>
<tbody>
{checks_body}
</tbody>
</table>
<p class="meta">Sim: skycache nexus validate --nodes 2. Field: dual radios + spectrum check + batman-day-one.</p>
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
        "go_sim_validation": doc.get("go_sim_validation"),
        "banner": HONEST,
    }


def write_dual_radio_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
    include_validation_pack: bool = True,
) -> dict[str, Any]:
    """Ops kit: doctor, board, checklist, validation pack (matrix + storyboard)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = _repo_root(repo_root)

    doc = dual_radio_doctor(data_dir=data_dir, repo_root=root)
    (out_dir / "dual-radio-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = dual_radio_status(data_dir=data_dir, repo_root=root)
    (out_dir / "dual-radio-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_dual_radio_html(
        out_dir / "dual-radio-board.html",
        data_dir=data_dir,
        repo_root=root,
    )

    pack_meta: dict[str, Any] | None = None
    if include_validation_pack:
        pack_dir = out_dir / "validation-pack"
        pack_meta = write_validation_pack(pack_dir)

    (out_dir / "README.md").write_text(
        f"""# Dual-radio ops kit

{HONEST}

## Commands

```text
skycache dual-radio doctor
skycache dual-radio status
skycache dual-radio export --out data/ops/dual-radio-board.html
skycache dual-radio kit --out data/dual-radio-kit
skycache mesh dual-radio-pack --out media/dual-radio-validation
skycache nexus validate --nodes 2
skycache mesh day-one --write
```

## Field order

1. go_sim_validation true (always for matrix/storyboard path)
2. Open validation-pack/storyboard.html
3. Spectrum check; legal_rf_mode=ism_mesh
4. Identify MESH_IF vs CLIENT_IF
5. Optional go_field_soak on Linux with batctl + dual radios

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Dual-radio field soak checklist

{HONEST}

- [ ] dual-radio doctor go_sim_validation true
- [ ] storyboard + board matrix reviewed
- [ ] national spectrum check done
- [ ] two radios labeled MESH vs CLIENT
- [ ] DRY_RUN=1 bash deploy/mesh/batman-day-one.sh
- [ ] batctl n shows neighbor (2-node)
- [ ] phones join client SSID; portal Library works offline
- [ ] no free-Starlink claims in training notes
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
                "download_hint": "/downloads/skycache-dual-radio-kit.zip",
                "storyboard_hint": "/downloads/dual-radio-validation.html",
                "field_mesh_kit": "/downloads/skycache-field-mesh-kit.zip",
                "validation_pack": pack_meta,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Copy doc if present for offline USB
    src_doc = root / "docs" / "mesh-dual-radio-validation.md"
    if src_doc.is_file():
        shutil.copy2(src_doc, out_dir / "mesh-dual-radio-validation.md")

    zip_path: str | None = None
    if zip_bundle:
        zp = out_dir.parent / f"{out_dir.name}.zip"
        if zp.is_file():
            zp.unlink()
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.rglob("*")):
                if f.is_file():
                    zf.write(
                        f,
                        arcname=f"{out_dir.name}/{f.relative_to(out_dir).as_posix()}",
                    )
        zip_path = str(zp)

    return {
        "schema": KIT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "zip": zip_path,
        "go_sim_validation": doc.get("go_sim_validation"),
        "score": doc.get("score"),
        "banner": HONEST,
        "validation_pack": pack_meta,
    }
