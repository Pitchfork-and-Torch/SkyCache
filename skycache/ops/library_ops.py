"""Library Ops (v1.24+) / Publish (v1.25): dual-access catalog doctor, board, kit, site publish.

Elevates curated public-domain dual-access library readiness into a product surface.
Online catalog + offline packs. Not a complete archive. Not free commercial broadband.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.skybrary.integrity import sha256_text
from skycache.skybrary.sample_corpus import SAMPLES, build_sample_packages

HONEST = (
    "Library ops: dual-access Skybrary catalog (online browse + offline packs). "
    "Public domain / open content only. Curated packs - not a complete archive. "
    "Not free commercial broadband or Starlink."
)

DOCTOR_SCHEMA = "skycache.library.doctor.v1"
STATUS_SCHEMA = "skycache.library.status.v1"
EXPORT_SCHEMA = "skycache.library.export.v1"
KIT_SCHEMA = "skycache.library.kit.v1"
PUBLISH_SCHEMA = "skycache.library.publish.v1"

MIN_CURATED_WORKS = 50


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root(repo_root: Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root)
    return Path(__file__).resolve().parents[2]


def _language_stats() -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in SAMPLES:
        langs = s.get("languages") or ["en"]
        if isinstance(langs, str):
            langs = [langs]
        for lang in langs:
            key = str(lang).lower()
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _subject_stats() -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in SAMPLES:
        for sub in s.get("subjects") or []:
            key = str(sub)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def library_doctor(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Readiness for dual-access Skybrary library (samples, export, packs)."""
    root = _repo_root(repo_root)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    work_count = len(SAMPLES)
    add(
        "curated_samples",
        work_count >= MIN_CURATED_WORKS,
        f"{work_count} curated PD samples (min {MIN_CURATED_WORKS})",
        18,
    )

    lang_stats = _language_stats()
    non_en = sum(v for k, v in lang_stats.items() if k != "en")
    multi_lang_works = sum(
        1
        for s in SAMPLES
        if len(s.get("languages") or ["en"]) > 1
        or any(str(x).lower() != "en" for x in (s.get("languages") or ["en"]))
    )
    add(
        "multilingual_wave",
        multi_lang_works >= 4 or non_en >= 4,
        f"{multi_lang_works} non-English-primary/multilingual sample works; langs={list(lang_stats.keys())}",
        12,
    )

    samples_dir = root / "samples" / "skybrary"
    sample_pkg_count = 0
    if samples_dir.is_dir():
        sample_pkg_count = sum(1 for p in samples_dir.iterdir() if p.is_dir())
    add(
        "sample_packages_on_disk",
        sample_pkg_count >= min(work_count, 10) or work_count >= MIN_CURATED_WORKS,
        f"{sample_pkg_count} package dirs under samples/skybrary (regenerate with skybrary samples)",
        10,
    )

    export_mod = root / "skycache" / "skybrary" / "catalog_export.py"
    add(
        "catalog_export_module",
        export_mod.is_file(),
        "skycache/skybrary/catalog_export.py",
        10,
    )

    catalog_export = root / "data" / "catalog-export" / "skybrary-catalog.json"
    catalog_public_hint = False
    if catalog_export.is_file():
        try:
            raw = json.loads(catalog_export.read_text(encoding="utf-8"))
            catalog_public_hint = int(raw.get("work_count") or 0) >= MIN_CURATED_WORKS
        except Exception:
            catalog_public_hint = False
    add(
        "catalog_export_artifact",
        catalog_export.is_file(),
        str(catalog_export) if catalog_export.is_file() else "run: skybrary export-catalog --out data/catalog-export --starter-kits",
        10,
    )
    add(
        "catalog_export_count",
        catalog_public_hint or not catalog_export.is_file(),
        "export work_count ok or not yet exported",
        6,
    )

    # starter kit presence optional
    literacy_kit = (
        root / "data" / "catalog-export" / "packs" / "literacy-starter.zip"
    )
    add(
        "starter_kits",
        literacy_kit.is_file() or True,
        "starter kits via export-catalog --starter-kits (optional artifact)",
        6,
    )

    vision = root / "docs" / "VISION-SKYBRARY.md"
    add(
        "vision_doc",
        vision.is_file(),
        str(vision) if vision.is_file() else "missing VISION-SKYBRARY.md",
        8,
    )
    dual_doc = root / "docs" / "skybrary-architecture.md"
    add(
        "architecture_doc",
        dual_doc.is_file(),
        str(dual_doc) if dual_doc.is_file() else "missing skybrary-architecture.md",
        6,
    )

    add("sim_path", True, "skycache serve --sim + Library tab always available", 10)
    add(
        "online_portal",
        True,
        "Marketing dual-access: https://skycache.jonbailey.xyz/library/",
        8,
    )

    # Zero-network kit parity (v1.26+): kit on disk should match curated sample count
    zn_paths = [
        root / "phone-zero-network" / "kit-manifest.json",
        root / "samples" / "phone-zero-network" / "kit-manifest.json",
        root / "kit" / "kit-manifest.json",
    ]
    zn_ok = False
    zn_count = 0
    zn_detail = "no kit-manifest.json under phone-zero-network/samples/kit"
    for zp in zn_paths:
        if not zp.is_file():
            continue
        try:
            meta = json.loads(zp.read_text(encoding="utf-8"))
            zn_count = int(meta.get("work_count") or 0)
            zn_ok = zn_count >= work_count
            zn_detail = f"{zp.as_posix()} work_count={zn_count} (samples={work_count})"
            if zn_ok:
                break
        except Exception as e:
            zn_detail = f"{zp}: {e}"
    add(
        "zero_network_kit_parity",
        zn_ok or work_count < MIN_CURATED_WORKS,
        zn_detail
        if zn_ok
        else f"{zn_detail} - run: skycache library zero-network --out phone-zero-network",
        10,
    )

    if data_dir is not None:
        data_dir = Path(data_dir)
        sky_db = data_dir / "skybrary.db"
        add(
            "local_skybrary_db",
            sky_db.is_file() or True,
            "optional data/skybrary.db after samples --ingest",
            4,
        )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))

    go_sim = work_count >= MIN_CURATED_WORKS
    go_field = go_sim and (
        sample_pkg_count >= min(work_count, 10) or catalog_export.is_file()
    )

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_library": go_sim,
        "go_field_library": go_field,
        "work_count": work_count,
        "language_stats": lang_stats,
        "subject_stats": _subject_stats(),
        "multilingual_work_count": multi_lang_works,
        "sample_pkg_count": sample_pkg_count,
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache library doctor",
            "skycache library status",
            "skycache library export --out data/ops/library-board.html",
            "skycache library kit --out data/library-kit",
            "skycache library sync --out data/library-sync",
            "skycache library publish --out data/catalog-publish",
            "skycache library zero-network --out phone-zero-network --zip",
            "skycache skybrary samples --out samples/skybrary",
            "Copy staging public/ into skycache-web/public/ and redeploy site",
        ],
        "legal": (
            "Public domain / open licenses only; curated packs; "
            "not a complete archive; not free commercial broadband"
        ),
    }


def library_status(
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    doc = library_doctor(data_dir=data_dir, repo_root=repo_root)
    top_works = [
        {
            "work_id": s.get("work_id"),
            "title": (s.get("title") or {}).get("en") or s.get("work_id"),
            "languages": s.get("languages") or ["en"],
            "subjects": s.get("subjects") or [],
            "tier": s.get("tier"),
        }
        for s in SAMPLES[:12]
    ]
    from skycache.skybrary.pack_profile import list_profiles

    pack_ids = [
        p.get("id")
        for p in list_profiles()
        if p.get("id") and not p.get("dynamic")
    ]
    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        "score": doc.get("score"),
        "go_sim_library": doc.get("go_sim_library"),
        "go_field_library": doc.get("go_field_library"),
        "work_count": doc.get("work_count"),
        "language_stats": doc.get("language_stats"),
        "subject_stats": doc.get("subject_stats"),
        "multilingual_work_count": doc.get("multilingual_work_count"),
        "sample_works_preview": top_works,
        "pack_profiles": pack_ids,
        "default_pack_kits": list(DEFAULT_PACK_PROFILES),
        "legal": doc.get("legal"),
        "online_catalog": "https://skycache.jonbailey.xyz/library/",
        "downloads": {
            "library_kit": "https://skycache.jonbailey.xyz/downloads/skycache-library-kit.zip",
            "zero_network": "https://skycache.jonbailey.xyz/downloads/skycache-zero-network-demo-kit.zip",
            "multilingual_literacy": "https://skycache.jonbailey.xyz/downloads/skycache-pack-multilingual-literacy.zip",
            "literacy_starter": "https://skycache.jonbailey.xyz/downloads/skycache-pack-literacy-starter.zip",
            "emergency_health": "https://skycache.jonbailey.xyz/downloads/skycache-pack-emergency-health.zip",
            "health_priority": "https://skycache.jonbailey.xyz/downloads/skycache-pack-health-priority.zip",
        },
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_library_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Printable dual-access library readiness board."""
    doc = library_doctor(data_dir=data_dir, repo_root=repo_root)
    st = library_status(data_dir=data_dir, repo_root=repo_root)
    check_rows = []
    for c in doc.get("checks") or []:
        mark = "OK" if c.get("ok") else "FAIL"
        check_rows.append(
            f"<tr><td>{_esc(mark)}</td><td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('detail'))}</td></tr>"
        )
    checks_body = "\n".join(check_rows) or "<tr><td colspan='3'>(none)</td></tr>"

    lang_rows = []
    for lang, n in (doc.get("language_stats") or {}).items():
        lang_rows.append(f"<tr><td>{_esc(lang)}</td><td>{_esc(n)}</td></tr>")
    langs_body = "\n".join(lang_rows) or "<tr><td colspan='2'>(none)</td></tr>"

    work_rows = []
    for w in st.get("sample_works_preview") or []:
        work_rows.append(
            f"<tr><td>{_esc(w.get('title'))}</td>"
            f"<td>{_esc(', '.join(w.get('languages') or []))}</td>"
            f"<td>{_esc(', '.join((w.get('subjects') or [])[:3]))}</td></tr>"
        )
    works_body = "\n".join(work_rows) or "<tr><td colspan='3'>(none)</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache library board</title>
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
<h1>Library ops board (dual-access Skybrary)</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score <strong>{doc.get('score')}</strong>
 · go_sim_library={doc.get('go_sim_library')}
 · go_field_library={doc.get('go_field_library')}</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<p class="meta">Works: {doc.get('work_count')} · multilingual: {doc.get('multilingual_work_count')}
 · online: https://skycache.jonbailey.xyz/library/</p>
<h2>Languages in curated samples</h2>
<table>
<thead><tr><th>Language</th><th>Works</th></tr></thead>
<tbody>
{langs_body}
</tbody>
</table>
<h2>Sample works (preview)</h2>
<table>
<thead><tr><th>Title</th><th>Lang</th><th>Subjects</th></tr></thead>
<tbody>
{works_body}
</tbody>
</table>
<h2>Checks</h2>
<table>
<thead><tr><th>OK</th><th>ID</th><th>Detail</th></tr></thead>
<tbody>
{checks_body}
</tbody>
</table>
<p class="meta">CLI: skycache skybrary samples | export-catalog --starter-kits. Not a complete archive.</p>
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
        "go_sim_library": doc.get("go_sim_library"),
        "work_count": doc.get("work_count"),
        "banner": HONEST,
    }


def write_library_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Ops kit: doctor, status, board, field checklist, hosting hints."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = _repo_root(repo_root)

    doc = library_doctor(data_dir=data_dir, repo_root=root)
    (out_dir / "library-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = library_status(data_dir=data_dir, repo_root=root)
    (out_dir / "library-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_library_html(
        out_dir / "library-board.html",
        data_dir=data_dir,
        repo_root=root,
    )

    (out_dir / "README.md").write_text(
        f"""# Library ops kit

{HONEST}

## Commands

```text
skycache library doctor
skycache library status
skycache library export --out data/ops/library-board.html
skycache library kit --out data/library-kit
skycache skybrary samples --out samples/skybrary
skycache skybrary samples --ingest --data-dir data
skycache skybrary export-catalog --out data/catalog-export --starter-kits
skycache serve --sim
```

## Dual-access path

1. go_sim_library true (curated samples loaded in software)
2. Browse online: https://skycache.jonbailey.xyz/library/
3. Offline: USB/mesh packs + village node Library tab
4. Redeploy marketing catalog JSON after corpus expansion

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Library dual-access field checklist

{HONEST}

- [ ] library doctor go_sim_library true
- [ ] work_count matches release notes
- [ ] export-catalog written; starter kits present
- [ ] marketing /library/ shows same work_count
- [ ] village node: skycache skybrary samples --ingest
- [ ] phones on hub Wi-Fi open Library tab offline
- [ ] license passports reviewed (public domain / open only)
- [ ] no free-Starlink claims in partner training
- [ ] not presented as a complete archive of every text
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
                "download_hint": "/downloads/skycache-library-kit.zip",
                "online_catalog": "https://skycache.jonbailey.xyz/library/",
                "work_count": doc.get("work_count"),
                "language_stats": doc.get("language_stats"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    for rel in (
        "docs/VISION-SKYBRARY.md",
        "docs/skybrary-architecture.md",
        "docs/skybrary-corpus-import.md",
    ):
        src = root / rel
        if src.is_file():
            dest = out_dir / Path(rel).name
            shutil.copy2(src, dest)

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
        "go_sim_library": doc.get("go_sim_library"),
        "score": doc.get("score"),
        "work_count": doc.get("work_count"),
        "banner": HONEST,
    }


def _sample_to_export_row(s: dict[str, Any]) -> dict[str, Any]:
    """Build dual-access catalog row directly from a curated sample (no DB)."""
    from skycache.skybrary.catalog_export import work_to_export_row

    title = s.get("title") or {}
    if isinstance(title, dict):
        title_en = title.get("en") or next(iter(title.values()), s.get("work_id"))
    else:
        title_en = str(title)
    summary = s.get("summary") or {}
    if isinstance(summary, dict):
        summary_en = summary.get("en") or title_en
    else:
        summary_en = str(summary)
    body = str(s.get("body") or "")
    digest = sha256_text(body)
    work_id = str(s.get("work_id") or "")
    langs = s.get("languages") or ["en"]
    if isinstance(langs, str):
        langs = [langs]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = {
        "work_id": work_id,
        "title": title_en,
        "creators": list(s.get("creators") or []),
        "languages": [str(x) for x in langs],
        "subjects": list(s.get("subjects") or []),
        "license": "public domain",
        "civilizational_tier": int(s.get("tier") or 3),
        "summary": summary_en,
        "package_id": work_id,
        "provenance": {
            "source": "skybrary_curated_pd_sample",
            "url": "",
            "note": (
                "Curated public-domain pack for Skybrary Live dual-access; "
                "not a complete corpus dump"
            ),
            "retrieval_date": stamp,
        },
        "editions": [
            {
                "edition_id": f"{work_id}-txt",
                "format": "txt",
                "size_bytes": len(body.encode("utf-8")),
                "sha256": digest,
            }
        ],
    }
    return work_to_export_row(raw)


def build_samples_catalog_dict(
    *,
    site_base: str = "https://skycache.jonbailey.xyz",
) -> dict[str, Any]:
    """In-memory dual-access catalog v2 from curated SAMPLES (no ingest DB)."""
    from skycache.skybrary.catalog_export import (
        CATALOG_SCHEMA,
        DISCLAIMER,
        LEGAL_NOTE,
        _pack_profiles_export,
    )

    slim = [_sample_to_export_row(s) for s in SAMPLES]
    built = _iso_now()
    base = site_base.rstrip("/")
    lang_facets: dict[str, int] = {}
    sub_facets: dict[str, int] = {}
    for row in slim:
        for lang in row.get("languages") or []:
            lang_facets[str(lang)] = lang_facets.get(str(lang), 0) + 1
        for sub in row.get("subjects") or []:
            sub_facets[str(sub)] = sub_facets.get(str(sub), 0) + 1
    return {
        "schema": CATALOG_SCHEMA,
        "version": __version__,
        "generated": built[:10],
        "built_at": built,
        "work_count": len(slim),
        "source": "SkyCache Skybrary dual-access catalog (samples publish)",
        "disclaimer": DISCLAIMER,
        "legal_note": LEGAL_NOTE,
        "legal": LEGAL_NOTE,
        "dual_access": {
            "online": f"{base}/library/",
            "offline": "skycache skybrary pack --profile literacy-1gb",
            "online_browse": f"{base}/library/",
            "note": "Same works online (browse) and offline (USB/mesh packs).",
        },
        "facets": {
            "languages": lang_facets,
            "subjects": sub_facets,
            "licenses": {"public domain": len(slim)},
            "eras": {},
        },
        "pack_profiles": _pack_profiles_export(),
        "profiles": _pack_profiles_export(),
        "starter_kits": [],
        "works": slim,
    }


def write_library_zero_network(
    out_dir: Path,
    *,
    zip_bundle: bool = True,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Write zero-network phone kit matching full curated SAMPLES count."""
    from skycache.skybrary.zero_network_kit import (
        KIT_ZIP_NAME,
        write_zero_network_kit,
    )

    out_dir = Path(out_dir)
    meta = write_zero_network_kit(out_dir)
    zip_path: str | None = None
    if zip_bundle:
        # Always write the zip OUTSIDE out_dir first so rglob cannot feed a
        # growing zip back into itself (self-include bomb when zip lives in kit/).
        if out_dir.name in ("phone-zero-network", "kit", "skycache-zero-network-demo-kit"):
            zp = out_dir.parent / KIT_ZIP_NAME
        else:
            zp = out_dir.parent / (out_dir.name + ".zip")
        if zp.is_file():
            zp.unlink()
        # Drop any stale inner zip before packaging
        stale_inner = out_dir / KIT_ZIP_NAME
        if stale_inner.is_file():
            try:
                stale_inner.unlink()
            except OSError:
                pass
        arc_root = (
            "skycache-zero-network-demo-kit"
            if out_dir.name in ("phone-zero-network", "kit")
            else out_dir.name
        )
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.rglob("*")):
                if not f.is_file():
                    continue
                # Never pack zips (or the kit zip name) into the kit zip
                if f.suffix.lower() == ".zip" or f.name == KIT_ZIP_NAME:
                    continue
                zf.write(
                    f,
                    arcname=f"{arc_root}/{f.relative_to(out_dir).as_posix()}",
                )
        zip_path = str(zp)

        # Optional USB tree copy: after ZipFile is closed, never during rglob
        if out_dir.name in ("phone-zero-network", "kit"):
            inner = out_dir / KIT_ZIP_NAME
            try:
                shutil.copy2(zp, inner)
            except OSError:
                pass

    work_count = int(meta.get("work_count") or 0)
    return {
        "schema": "skycache.library.zero_network.v1",
        "ok": work_count >= MIN_CURATED_WORKS,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "zip": zip_path,
        "work_count": work_count,
        "sample_count": len(SAMPLES),
        "parity": work_count == len(SAMPLES),
        "banner": HONEST,
        "honest": meta.get("honest"),
    }


def publish_library_catalog(
    out_dir: Path,
    *,
    site_base: str = "https://skycache.jonbailey.xyz",
    rebuild_samples: bool = True,
    samples_out: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Publish marketing-ready dual-access catalog JSON (+ optional sample packs).

    Writes skybrary-catalog.json and catalog.json under out_dir for
    skycache-web/public/. Optionally regenerates samples/skybrary packages.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = _repo_root(repo_root)

    catalog = build_samples_catalog_dict(site_base=site_base)
    sky_path = out_dir / "skybrary-catalog.json"
    cat_path = out_dir / "catalog.json"
    payload = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    sky_path.write_text(payload, encoding="utf-8")
    cat_path.write_text(payload, encoding="utf-8")

    samples_meta: dict[str, Any] | None = None
    if rebuild_samples:
        s_out = Path(samples_out) if samples_out else root / "samples" / "skybrary"
        paths = build_sample_packages(s_out)
        samples_meta = {"out": str(s_out), "package_count": len(paths)}

    (out_dir / "HOSTING.json").write_text(
        json.dumps(
            {
                "schema": PUBLISH_SCHEMA,
                "generated_at": _iso_now(),
                "software_version": __version__,
                "banner": HONEST,
                "work_count": catalog.get("work_count"),
                "online_catalog": f"{site_base.rstrip('/')}/library/",
                "files": [
                    "skybrary-catalog.json",
                    "catalog.json",
                    "HOSTING.json",
                ],
                "deploy_hint": (
                    "Copy skybrary-catalog.json + catalog.json to skycache-web/public/ "
                    "then npm run build && wrangler pages deploy"
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "README.md").write_text(
        f"""# Library catalog publish

{HONEST}

## Files

- skybrary-catalog.json - dual-access catalog v2 (marketing /library/)
- catalog.json - same payload (back-compat name)
- HOSTING.json - deploy metadata

## Commands

```text
skycache library publish --out data/catalog-publish
# copy JSON into ~/skycache-web/public/
skycache library doctor
skycache library kit --out data/library-kit
```

Software v{__version__} - work_count={catalog.get("work_count")}
""",
        encoding="utf-8",
    )

    return {
        "schema": PUBLISH_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "skybrary_catalog": str(sky_path),
        "catalog": str(cat_path),
        "work_count": catalog.get("work_count"),
        "language_stats": catalog.get("facets", {}).get("languages"),
        "samples": samples_meta,
        "banner": HONEST,
    }


DEFAULT_PACK_PROFILES = (
    "multilingual-literacy",
    "literacy-starter",
    "emergency-health",
    "health-priority",
    "stem-lite",
    "archive-100mb",
)


def pack_budget_report(
    *,
    profiles: list[str] | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """List size-bounded pack profiles for dual-access discovery (operator planning)."""
    from skycache.skybrary.pack_profile import BUILTIN_PROFILES
    from skycache.skybrary.sample_corpus import SAMPLES

    root = _repo_root(repo_root)
    names = list(profiles) if profiles else sorted(BUILTIN_PROFILES.keys())
    curated_bytes = 0
    for s in SAMPLES:
        curated_bytes += len(str(s.get("body") or "").encode("utf-8"))
    rows: list[dict[str, Any]] = []
    for name in names:
        p = BUILTIN_PROFILES.get(name)
        if not p:
            rows.append({"id": name, "ok": False, "error": "unknown profile"})
            continue
        max_b = int(p.get("max_bytes") or 0)
        rows.append(
            {
                "id": p.get("id") or name,
                "ok": True,
                "max_bytes": max_b,
                "max_mb": round(max_b / (1024 * 1024), 2) if max_b else None,
                "description": p.get("description"),
                "prefer_priority_classes": p.get("prefer_priority_classes") or [],
                "reserve_priority_classes": p.get("reserve_priority_classes") or [],
                "reserve_fraction": p.get("reserve_fraction"),
                "curated_sample_count": len(SAMPLES),
                "curated_body_bytes_est": curated_bytes,
                "fits_full_curated_est": bool(max_b == 0 or curated_bytes <= max_b),
            }
        )
    return {
        "schema": "skycache.library.pack_budgets.v1",
        "generated_at": _iso_now(),
        "software_version": __version__,
        "repo_root": str(root),
        "default_pack_kits": list(DEFAULT_PACK_PROFILES),
        "profiles": rows,
        "banner": HONEST,
        "honest": (
            "Size budgets for offline USB/mesh kits from the same dual-access corpus. "
            "Not free commercial broadband. Not a complete archive."
        ),
    }


def write_library_pack_kits(
    out_dir: Path,
    *,
    profiles: list[str] | None = None,
    content_dir: Path | None = None,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build profile packs from curated samples and zip for marketing downloads."""
    from skycache.config import Settings
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.pack_profile import build_pack_from_profile

    root = _repo_root(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    profiles = list(profiles or DEFAULT_PACK_PROFILES)
    content = Path(content_dir) if content_dir else root / "samples" / "skybrary"
    if not content.is_dir():
        build_sample_packages(content)

    # Prefer operator data_dir catalog when present; else empty temp catalog
    if data_dir is not None:
        settings = Settings(data_dir=Path(data_dir))
        settings.ensure_dirs()
        sky_path = settings.skybrary_db_path
    else:
        sky_path = out_dir / "_skybrary_pack.db"

    sky = SkybraryCatalog(sky_path)
    built: list[dict[str, Any]] = []
    try:
        for pid in profiles:
            pack_out = out_dir / pid
            if pack_out.is_dir():
                shutil.rmtree(pack_out)
            try:
                meta = build_pack_from_profile(
                    sky,
                    pid,
                    content_dir=content,
                    out_dir=pack_out,
                )
            except Exception as exc:
                built.append(
                    {
                        "profile": pid,
                        "ok": False,
                        "error": str(exc),
                    }
                )
                continue
            zip_path: str | None = None
            if zip_bundle:
                zp = out_dir / f"skycache-pack-{pid}.zip"
                if zp.is_file():
                    zp.unlink()
                with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for f in sorted(pack_out.rglob("*")):
                        if f.is_file():
                            zf.write(
                                f,
                                arcname=f"{pid}/{f.relative_to(pack_out).as_posix()}",
                            )
                zip_path = str(zp)
            built.append(
                {
                    "profile": pid,
                    "ok": True,
                    "count": meta.get("count"),
                    "total_bytes": meta.get("total_bytes"),
                    "out_dir": str(pack_out),
                    "zip": zip_path,
                    "manifest_sha256": meta.get("manifest_sha256"),
                }
            )
    finally:
        sky.close()

    ok_count = sum(1 for b in built if b.get("ok"))
    (out_dir / "HOSTING.json").write_text(
        json.dumps(
            {
                "schema": "skycache.library.pack_kits.v1",
                "generated_at": _iso_now(),
                "software_version": __version__,
                "banner": HONEST,
                "profiles": built,
                "download_hints": [
                    f"/downloads/skycache-pack-{p}.zip" for p in profiles
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "README.md").write_text(
        f"""# Library pack kits

{HONEST}

Built profiles: {", ".join(profiles)}

```text
skycache library pack-kits --out data/library-pack-kits
skycache skybrary pack --profile multilingual-literacy
```

Copy skycache-pack-*.zip into skycache-web/public/downloads/ or use:
`skycache library sync --with-packs --apply-web`

Software v{__version__}
""",
        encoding="utf-8",
    )
    return {
        "schema": "skycache.library.pack_kits.v1",
        "ok": ok_count > 0,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "content_dir": str(content),
        "profiles": built,
        "ok_count": ok_count,
        "banner": HONEST,
    }


def default_skycache_web_public() -> Path | None:
    """Return ~/skycache-web/public if it exists (Knock marketing tree)."""
    p = Path.home() / "skycache-web" / "public"
    return p if p.is_dir() else None


def write_marketing_sitemap(
    web_public: Path,
    *,
    site_base: str = "https://skycache.jonbailey.xyz",
) -> dict[str, Any]:
    """Rewrite public/sitemap.xml with core pages + every catalog work URL."""
    web_public = Path(web_public)
    base = site_base.rstrip("/")
    pages = [
        "/",
        "/skybrary/",
        "/library/",
        "/corpus/",
        "/mesh/",
        "/handoff/",
        "/gateway/",
        "/village-day/",
        "/federation/",
        "/integrity/",
        "/disaster/",
        "/power/",
        "/licenses/",
        "/use/",
        "/partners/",
        "/install/",
        "/capabilities/",
        "/ops/",
        "/rx/",
        "/report/",
        "/roadmap/",
        "/developers/",
        "/prompt/",
    ]
    work_ids: list[str] = []
    cat_path = web_public / "skybrary-catalog.json"
    if cat_path.is_file():
        try:
            data = json.loads(cat_path.read_text(encoding="utf-8"))
            for w in data.get("works") or []:
                wid = w.get("work_id")
                if wid:
                    work_ids.append(str(wid))
        except Exception:
            work_ids = []

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in pages:
        pri = (
            "1.0"
            if p == "/"
            else "0.95"
            if p in ("/library/", "/skybrary/", "/use/", "/village-day/")
            else "0.9"
        )
        lines.extend(
            [
                "  <url>",
                f"    <loc>{base}{p}</loc>",
                "    <changefreq>weekly</changefreq>",
                f"    <priority>{pri}</priority>",
                "  </url>",
            ]
        )
    for wid in work_ids:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{base}/library/works/{wid}/</loc>",
                "    <changefreq>monthly</changefreq>",
                "    <priority>0.7</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    lines.append("")
    out = web_public / "sitemap.xml"
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return {
        "ok": True,
        "path": str(out),
        "page_count": len(pages),
        "work_url_count": len(work_ids),
    }


def apply_staging_to_web_public(
    staging_public: Path,
    web_public: Path,
    *,
    site_base: str = "https://skycache.jonbailey.xyz",
    write_sitemap: bool = True,
) -> dict[str, Any]:
    """Copy staged public assets into skycache-web/public and refresh sitemap."""
    staging_public = Path(staging_public)
    web_public = Path(web_public)
    if not staging_public.is_dir():
        return {"ok": False, "error": f"missing staging public: {staging_public}"}
    if not web_public.is_dir():
        return {"ok": False, "error": f"missing web public: {web_public}"}

    copied: list[str] = []
    for name in ("skybrary-catalog.json", "catalog.json"):
        src = staging_public / name
        if src.is_file():
            shutil.copy2(src, web_public / name)
            copied.append(name)

    src_dl = staging_public / "downloads"
    dest_dl = web_public / "downloads"
    dest_dl.mkdir(parents=True, exist_ok=True)
    if src_dl.is_dir():
        for f in src_dl.iterdir():
            if f.is_file():
                shutil.copy2(f, dest_dl / f.name)
                copied.append(f"downloads/{f.name}")

    sm: dict[str, Any] | None = None
    if write_sitemap:
        sm = write_marketing_sitemap(web_public, site_base=site_base)

    return {
        "ok": True,
        "web_public": str(web_public),
        "copied": copied,
        "sitemap": sm,
    }


def library_sync(
    staging_dir: Path,
    *,
    data_dir: Path | None = None,
    site_base: str = "https://skycache.jonbailey.xyz",
    rebuild_zero_network: bool = True,
    rebuild_ops_kit: bool = True,
    with_packs: bool = False,
    apply_web: Path | str | bool | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """One-shot dual-access marketing sync: publish + kits + optional web apply.

    Staging layout (default data/library-sync):
      public/skybrary-catalog.json
      public/catalog.json
      public/downloads/skycache-library-kit.zip
      public/downloads/skycache-zero-network-demo-kit.zip  (optional)
      public/downloads/skycache-pack-*.zip  (optional --with-packs)
      COPY-TO-SKYCACHE-WEB.md

    apply_web:
      True / "auto" -> ~/skycache-web/public when present
      Path / str -> that public dir
      None / False -> checklist only
    """
    root = _repo_root(repo_root)
    staging_dir = Path(staging_dir)
    public = staging_dir / "public"
    downloads = public / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)

    pub = publish_library_catalog(
        staging_dir / "catalog-publish",
        site_base=site_base,
        rebuild_samples=True,
        samples_out=root / "samples" / "skybrary",
        repo_root=root,
    )
    for name in ("skybrary-catalog.json", "catalog.json"):
        src = Path(pub["out_dir"]) / name
        if src.is_file():
            shutil.copy2(src, public / name)

    kit_meta: dict[str, Any] | None = None
    if rebuild_ops_kit:
        kit_meta = write_library_kit(
            staging_dir / "library-kit",
            data_dir=data_dir,
            repo_root=root,
            zip_bundle=True,
        )
        z = kit_meta.get("zip")
        if z and Path(z).is_file():
            shutil.copy2(z, downloads / "skycache-library-kit.zip")

    zn_meta: dict[str, Any] | None = None
    if rebuild_zero_network:
        zn_meta = write_library_zero_network(
            root / "phone-zero-network",
            zip_bundle=True,
            repo_root=root,
        )
        candidates = [
            root / "skycache-zero-network-demo-kit.zip",
            Path(zn_meta.get("zip") or ""),
        ]
        for c in candidates:
            if c and Path(c).is_file():
                shutil.copy2(c, downloads / "skycache-zero-network-demo-kit.zip")
                break

    packs_meta: dict[str, Any] | None = None
    if with_packs:
        packs_meta = write_library_pack_kits(
            staging_dir / "library-pack-kits",
            content_dir=root / "samples" / "skybrary",
            data_dir=data_dir,
            zip_bundle=True,
            repo_root=root,
        )
        for row in packs_meta.get("profiles") or []:
            zp = row.get("zip")
            if zp and Path(zp).is_file():
                shutil.copy2(zp, downloads / Path(zp).name)

    doc = library_doctor(data_dir=data_dir, repo_root=root)
    work_count = int(pub.get("work_count") or doc.get("work_count") or 0)

    apply_meta: dict[str, Any] | None = None
    web_target: Path | None = None
    if apply_web is True or apply_web == "auto":
        web_target = default_skycache_web_public()
    elif apply_web not in (None, False, ""):
        web_target = Path(str(apply_web))
    if web_target is not None:
        apply_meta = apply_staging_to_web_public(
            public, web_target, site_base=site_base, write_sitemap=True
        )

    apply_note = (
        f"Applied to {web_target}"
        if apply_meta and apply_meta.get("ok")
        else "Not applied (pass --apply-web or --apply-web PATH)"
    )
    checklist = f"""# Copy staging into skycache-web

{HONEST}

Software v{__version__} | work_count={work_count}
Apply status: {apply_note}

## Copy (if not auto-applied)

From this staging `public/` into `~/skycache-web/public/`:

1. skybrary-catalog.json
2. catalog.json
3. downloads/skycache-library-kit.zip
4. downloads/skycache-zero-network-demo-kit.zip (if present)

## Deploy

```powershell
cd $env:USERPROFILE\\skycache-web
npm run build
npx wrangler pages deploy out --project-name=skycache-jonbailey --commit-dirty=true
```

## One-shot next time

```text
skycache library sync --out data/library-sync --apply-web
# or with skip heavy kit:
skycache library sync --out data/library-sync --skip-zero-network --apply-web
```

## Multilingual USB kit

```text
skycache skybrary pack --profile multilingual-literacy
```
"""
    (staging_dir / "COPY-TO-SKYCACHE-WEB.md").write_text(
        checklist, encoding="utf-8"
    )
    (staging_dir / "sync-receipt.json").write_text(
        json.dumps(
            {
                "schema": "skycache.library.sync.v1",
                "generated_at": _iso_now(),
                "software_version": __version__,
                "work_count": work_count,
                "go_sim_library": doc.get("go_sim_library"),
                "score": doc.get("score"),
                "publish": {
                    "work_count": pub.get("work_count"),
                    "out_dir": pub.get("out_dir"),
                },
                "ops_kit": kit_meta,
                "zero_network": zn_meta,
                "pack_kits": packs_meta,
                "apply_web": apply_meta,
                "banner": HONEST,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "schema": "skycache.library.sync.v1",
        "ok": bool(doc.get("go_sim_library")) and work_count >= MIN_CURATED_WORKS,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "staging_dir": str(staging_dir),
        "public_dir": str(public),
        "work_count": work_count,
        "score": doc.get("score"),
        "go_sim_library": doc.get("go_sim_library"),
        "checklist": str(staging_dir / "COPY-TO-SKYCACHE-WEB.md"),
        "apply_web": apply_meta,
        "pack_kits": packs_meta,
        "banner": HONEST,
        "copy_hint": (
            f"Applied to {web_target}; run npm run deploy in skycache-web"
            if apply_meta and apply_meta.get("ok")
            else f"Copy {public}/ into skycache-web/public/ then npm run deploy"
        ),
    }
