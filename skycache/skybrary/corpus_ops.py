"""Bulk Open Corpus Ops (v1.5.0 + v1.19 product surface): doctor, status, export, kit, batch.

Unifies folder / Gutenberg-catalog / OA science / open-URL import behind a legal
batch file. Fail-closed licenses. Never pirate mirrors. Not a complete archive.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.skybrary.license_gate import assert_license_allowed
from skycache.skybrary.provenance import (
    provenance_report_from_content_dir,
    write_provenance_report,
)

BATCH_SCHEMA = "skycache.corpus.batch.v1"
STATUS_SCHEMA = "skycache.corpus.status.v1"
DOCTOR_SCHEMA = "skycache.corpus.doctor.v1"
EXPORT_SCHEMA = "skycache.corpus.export.v1"
KIT_SCHEMA = "skycache.corpus.kit.v1"
JOB_TYPES = frozenset(
    {"folder", "gutenberg_catalog", "oa_science", "open_url", "sample_folder"}
)

HONEST = (
    "Bulk open corpus ops build a legal subset only. "
    "Not every book ever written. Not free commercial broadband. "
    "No pirate mirrors."
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def corpus_doctor(*, data_dir: Path | None = None, repo_root: Path | None = None) -> dict[str, Any]:
    """Local corpus pipeline readiness (no personal data, no live scrape required)."""
    from skycache.config import Settings
    from skycache.skybrary.catalog import SkybraryCatalog

    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    # License gate present
    try:
        assert_license_allowed("public domain")
        add("license_gate", True, "license_gate accepts public domain", 12)
    except Exception as exc:  # noqa: BLE001
        add("license_gate", False, f"license_gate failed: {exc}", 12)

    # Fixtures for CI / offline batch
    gut = repo_root / "tests" / "fixtures" / "gutenberg" / "catalog.json"
    oa = repo_root / "tests" / "fixtures" / "oa_science" / "catalog.json"
    samples = repo_root / "samples" / "skybrary"
    add("fixture_gutenberg", gut.is_file(), str(gut) if gut.is_file() else "missing gutenberg fixture", 10)
    add("fixture_oa", oa.is_file(), str(oa) if oa.is_file() else "missing oa_science fixture", 8)
    sample_n = len(list(samples.glob("*/work.txt"))) if samples.is_dir() else 0
    add("sample_corpus", sample_n >= 3, f"{sample_n} sample works under samples/skybrary", 12)

    # Content + skybrary
    content = settings.content_dir
    pkg_n = 0
    if content.is_dir():
        pkg_n = sum(1 for d in content.iterdir() if d.is_dir() and (d / "manifest.json").is_file())
    add("content_packages", pkg_n >= 1, f"{pkg_n} packages in content/", 15)

    sky_count = 0
    try:
        sky = SkybraryCatalog(settings.skybrary_db_path)
        sky_count = int(sky.count())
        sky.close()
        add("skybrary_fts", sky_count >= 1, f"{sky_count} works in skybrary.db", 15)
    except Exception as exc:  # noqa: BLE001
        add("skybrary_fts", False, f"skybrary unavailable: {exc}", 15)

    prov = provenance_report_from_content_dir(content)
    incomplete = int(prov.get("incomplete_passport_count") or 0)
    add(
        "provenance_quality",
        incomplete == 0 or pkg_n == 0,
        f"incomplete passports={incomplete} of {prov.get('item_count', 0)}",
        10,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_offline = all(
        next(c for c in checks if c["id"] == i)["ok"]
        for i in ("license_gate", "fixture_gutenberg", "sample_corpus")
    )

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_offline_batch": go_offline,
        "go_ingest_ready": go_offline,
        "checks": checks,
        "skybrary_works": sky_count,
        "content_packages": pkg_n,
        "banner": HONEST,
        "next_steps": _doctor_next(checks, go_offline),
        "legal": "Operator-run legal open content only - fail-closed licenses",
    }


def _doctor_next(checks: list[dict[str, Any]], go_offline: bool) -> list[str]:
    failed = {c["id"] for c in checks if not c["ok"]}
    steps: list[str] = []
    if "sample_corpus" in failed:
        steps.append("skycache skybrary samples --ingest")
    if "skybrary_fts" in failed:
        steps.append("skycache skybrary samples --ingest")
    if go_offline:
        steps.append("skycache skybrary corpus sample-manifest --out data/corpus-batch-demo.json")
        steps.append("skycache skybrary corpus batch --manifest data/corpus-batch-demo.json --allow-local --ingest")
    steps.append("skycache skybrary provenance --data-dir data")
    steps.append("Never point batch jobs at pirate mirrors")
    return steps


def corpus_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Scale snapshot: package counts, licenses, passport gaps."""
    from skycache.config import Settings
    from skycache.skybrary.catalog import SkybraryCatalog

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    content = settings.content_dir
    prov = provenance_report_from_content_dir(content)
    licenses: dict[str, int] = {}
    for it in prov.get("items") or []:
        lic = str(it.get("license") or "unknown").lower()
        licenses[lic] = licenses.get(lic, 0) + 1

    sky_count = 0
    try:
        sky = SkybraryCatalog(settings.skybrary_db_path)
        sky_count = int(sky.count())
        sky.close()
    except Exception:  # noqa: BLE001
        sky_count = 0

    item_count = int(prov.get("item_count") or 0)
    incomplete = int(prov.get("incomplete_passport_count") or 0)
    passport_pct = (
        int(round(100.0 * (item_count - incomplete) / item_count)) if item_count else 100
    )

    return {
        "schema": STATUS_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "content_packages": item_count,
        "skybrary_works": sky_count,
        "licenses": dict(sorted(licenses.items(), key=lambda x: (-x[1], x[0]))),
        "incomplete_passport_count": incomplete,
        "passport_complete_pct": passport_pct,
        "banner": HONEST,
        "legal": "Counts reflect this node only - not a global archive claim",
        "honest": (
            "Civilizational scale is ongoing operator work. "
            "Adapters exist; this status measures local legal holdings."
        ),
    }


def load_batch_manifest(path: Path) -> dict[str, Any]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("batch manifest must be a JSON object")
    jobs = data.get("jobs") or data.get("batch") or []
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("batch manifest needs a non-empty jobs list")
    return data


def write_sample_batch_manifest(
    out_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Write a CI-safe offline batch using local fixtures + sample texts."""
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gut = repo_root / "tests" / "fixtures" / "gutenberg" / "catalog.json"
    oa = repo_root / "tests" / "fixtures" / "oa_science" / "catalog.json"
    samples = repo_root / "samples" / "skybrary"
    jobs: list[dict[str, Any]] = []
    if samples.is_dir():
        jobs.append(
            {
                "type": "folder",
                "path": str(samples),
                "license": "public domain",
                "id_prefix": "sample-pd",
                "subjects": "literacy,literature_pd,sample",
                "recursive": True,
                "max_files": 12,
            }
        )
    if gut.is_file():
        jobs.append(
            {
                "type": "gutenberg_catalog",
                "catalog": str(gut),
                "license": "project gutenberg",
                "max": 5,
                "allow_local": True,
                "lang": "en",
            }
        )
    if oa.is_file():
        jobs.append(
            {
                "type": "oa_science",
                "catalog": str(oa),
                "license": "open-access",
                "max": 5,
                "allow_local": True,
            }
        )
    payload = {
        "schema": BATCH_SCHEMA,
        "software_version": __version__,
        "built_at": _iso_now(),
        "banner": HONEST,
        "note": "Offline demo batch - fixtures + samples only. Operator replaces with legal catalogs.",
        "jobs": jobs,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(out_path), "job_count": len(jobs), "schema": BATCH_SCHEMA}


def run_corpus_batch(
    manifest_path: Path,
    *,
    data_dir: Path | None = None,
    out_root: Path | None = None,
    ingest: bool = False,
    dry_run: bool = False,
    allow_local: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute a legal corpus batch manifest (folder / catalogs / open URL)."""
    from skycache.config import Settings
    from skycache.skybrary.corpus_import import import_folder, import_open_url, register_packages_to_skybrary
    from skycache.skybrary.gutenberg_catalog import import_gutenberg_catalog
    from skycache.skybrary.oa_science import import_oa_science_catalog

    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    out_root = Path(out_root) if out_root else settings.data_dir / "skybrary-build" / "batch"
    out_root.mkdir(parents=True, exist_ok=True)

    raw = load_batch_manifest(manifest_path)
    jobs = list(raw.get("jobs") or [])
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    packages_total = 0

    for idx, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"job[{idx}] not an object")
            continue
        jtype = str(job.get("type") or "").strip().lower()
        job_id = str(job.get("id") or f"job-{idx}")
        entry: dict[str, Any] = {"id": job_id, "type": jtype, "ok": False}

        try:
            if jtype not in JOB_TYPES:
                raise ValueError(f"unknown job type {jtype!r}; expected one of {sorted(JOB_TYPES)}")

            if jtype in {"folder", "sample_folder"}:
                path = Path(str(job.get("path") or ""))
                if not path.is_absolute():
                    # try relative to manifest, then repo
                    cand = Path(manifest_path).parent / path
                    path = cand if cand.exists() else (repo_root / path)
                lic = str(job.get("license") or "")
                if dry_run:
                    entry.update({"ok": True, "dry_run": True, "path": str(path), "license": lic})
                    results.append(entry)
                    continue
                meta = import_folder(
                    path,
                    Path(out_root) / job_id,
                    license_name=lic,
                    language=str(job.get("lang") or "en"),
                    subjects=[
                        s.strip()
                        for s in str(job.get("subjects") or "corpus_import").split(",")
                        if s.strip()
                    ],
                    creators=[
                        c.strip()
                        for c in str(job.get("creators") or "").split(";")
                        if c.strip()
                    ]
                    or None,
                    id_prefix=str(job.get("id_prefix") or "corpus"),
                    recursive=bool(job.get("recursive")),
                    max_files=int(job.get("max_files") or 50),
                )
                if ingest and meta.get("packages"):
                    dirs = [Path(p) for p in (meta.get("packages") or [])]
                    register_packages_to_skybrary(
                        dirs, settings=settings, register_content=True
                    )
                packages_total += int(
                    meta.get("imported") or len(meta.get("packages") or []) or 0
                )
                entry.update({"ok": bool(meta.get("ok", True)), "result": meta})

            elif jtype == "gutenberg_catalog":
                cat = Path(str(job.get("catalog") or ""))
                if not cat.is_absolute():
                    cand = Path(manifest_path).parent / cat
                    cat = cand if cand.is_file() else (repo_root / cat)
                if dry_run:
                    entry.update({"ok": True, "dry_run": True, "catalog": str(cat)})
                    results.append(entry)
                    continue
                use_local = bool(allow_local or job.get("allow_local"))
                meta = import_gutenberg_catalog(
                    cat,
                    Path(out_root) / job_id,
                    license_name=str(job.get("license") or "project gutenberg"),
                    language=job.get("lang") if job.get("lang") is not None else "en",
                    subject_contains=str(job.get("subject") or "") or None,
                    max_works=int(job.get("max") or 25),
                    max_bytes_total=int(job.get("max_bytes") or 50 * 1024 * 1024),
                    delay_s=float(
                        job.get("delay")
                        if job.get("delay") is not None
                        else (0.0 if use_local else 1.5)
                    ),
                    dry_run=False,
                    settings=settings if ingest else None,
                    ingest=bool(ingest),
                    allow_local_file=use_local,
                )
                packages_total += int(
                    meta.get("imported") or meta.get("count") or len(meta.get("packages") or []) or 0
                )
                entry.update({"ok": bool(meta.get("ok", True)), "result": meta})

            elif jtype == "oa_science":
                cat = Path(str(job.get("catalog") or ""))
                if not cat.is_absolute():
                    cand = Path(manifest_path).parent / cat
                    cat = cand if cand.is_file() else (repo_root / cat)
                if dry_run:
                    entry.update({"ok": True, "dry_run": True, "catalog": str(cat)})
                    results.append(entry)
                    continue
                use_local = bool(allow_local or job.get("allow_local"))
                meta = import_oa_science_catalog(
                    cat,
                    Path(out_root) / job_id,
                    max_works=int(job.get("max") or 20),
                    max_bytes_total=int(job.get("max_bytes") or 80 * 1024 * 1024),
                    delay_s=float(job.get("delay") if job.get("delay") is not None else (0.0 if use_local else 2.0)),
                    dry_run=False,
                    allow_local_file=use_local,
                    settings=settings if ingest else None,
                    ingest=bool(ingest),
                    default_license=str(job.get("license") or "open-access"),
                )
                packages_total += int(
                    meta.get("imported") or meta.get("count") or len(meta.get("packages") or []) or 0
                )
                entry.update({"ok": bool(meta.get("ok", True)), "result": meta})

            elif jtype == "open_url":
                url = str(job.get("url") or "").strip()
                lic = str(job.get("license") or "")
                if dry_run:
                    entry.update({"ok": True, "dry_run": True, "url": url, "license": lic})
                    results.append(entry)
                    continue
                meta = import_open_url(
                    url,
                    Path(out_root) / job_id,
                    license_name=lic,
                    title=str(job.get("title") or "") or None,
                    work_id=str(job.get("work_id") or "") or None,
                    language=str(job.get("lang") or "en"),
                    subjects=[
                        s.strip()
                        for s in str(job.get("subjects") or "corpus_import,open_http").split(",")
                        if s.strip()
                    ],
                    max_bytes=int(job.get("max_mb") or 20) * 1024 * 1024,
                )
                if ingest and meta.get("package"):
                    register_packages_to_skybrary(
                        [Path(meta["package"])],
                        settings=settings,
                        register_content=True,
                    )
                packages_total += 1 if meta.get("package") else 0
                entry.update({"ok": bool(meta.get("package")), "result": meta})

        except Exception as exc:  # noqa: BLE001
            entry["ok"] = False
            entry["error"] = str(exc)
            errors.append(f"{job_id}: {exc}")

        results.append(entry)

    # Always write provenance snapshot after batch when content exists
    prov = provenance_report_from_content_dir(settings.content_dir)
    prov_path = settings.data_dir / "ops" / "corpus-batch-provenance.json"
    write_provenance_report(prov, prov_path)

    ok = all(r.get("ok") for r in results) if results else False
    return {
        "schema": "skycache.corpus.batch_result.v1",
        "ok": ok and not errors,
        "software_version": __version__,
        "manifest": str(manifest_path),
        "generated_at": _iso_now(),
        "dry_run": dry_run,
        "ingest": ingest,
        "job_count": len(results),
        "packages_total": packages_total,
        "jobs": results,
        "errors": errors,
        "provenance_report": str(prov_path),
        "status": corpus_status(data_dir=settings.data_dir),
        "banner": HONEST,
        "legal": "Batch complete does not imply completeness of world literature",
    }


def _esc(s: Any) -> str:
    t = str(s if s is not None else "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_corpus_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Printable corpus scale / legal readiness board for partners."""
    doc = corpus_doctor(data_dir=data_dir, repo_root=repo_root)
    st = corpus_status(data_dir=data_dir)
    check_rows = []
    for c in doc.get("checks") or []:
        mark = "OK" if c.get("ok") else "FAIL"
        check_rows.append(
            f"<tr><td>{_esc(mark)}</td><td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('detail'))}</td></tr>"
        )
    checks_body = "\n".join(check_rows) or "<tr><td colspan='3'>(none)</td></tr>"
    lic_rows = []
    for lic, n in (st.get("licenses") or {}).items():
        lic_rows.append(f"<tr><td>{_esc(lic)}</td><td>{_esc(n)}</td></tr>")
    lic_body = "\n".join(lic_rows) or "<tr><td colspan='2'>(no packages)</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache corpus board</title>
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
<h1>Bulk open corpus board</h1>
<p class="meta">Software v{__version__} · {_iso_now()}
 · score {doc.get('score')} · go_offline_batch={doc.get('go_offline_batch')}
 · packages {st.get('content_packages')} · skybrary {st.get('skybrary_works')}
 · passports complete {st.get('passport_complete_pct')}%</p>
<p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
<h2>Scale snapshot (this node only)</h2>
<table>
<thead><tr><th>Metric</th><th>Value</th></tr></thead>
<tbody>
<tr><td>content packages</td><td>{_esc(st.get('content_packages'))}</td></tr>
<tr><td>skybrary works</td><td>{_esc(st.get('skybrary_works'))}</td></tr>
<tr><td>incomplete passports</td><td>{_esc(st.get('incomplete_passport_count'))}</td></tr>
<tr><td>passport complete %</td><td>{_esc(st.get('passport_complete_pct'))}</td></tr>
</tbody>
</table>
<h2>Licenses (local holdings)</h2>
<table>
<thead><tr><th>License</th><th>Count</th></tr></thead>
<tbody>
{lic_body}
</tbody>
</table>
<h2>Doctor checks</h2>
<table>
<thead><tr><th>OK</th><th>ID</th><th>Detail</th></tr></thead>
<tbody>
{checks_body}
</tbody>
</table>
<p class="meta">{_esc(st.get('honest'))}</p>
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
        "go_offline_batch": doc.get("go_offline_batch"),
        "banner": HONEST,
    }


def write_corpus_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    repo_root: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Kit: doctor, status, sample manifest, board HTML, checklist, zip."""
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]

    doc = corpus_doctor(data_dir=settings.data_dir, repo_root=repo_root)
    (out_dir / "corpus-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    st = corpus_status(data_dir=settings.data_dir)
    (out_dir / "corpus-status.json").write_text(
        json.dumps(st, indent=2) + "\n", encoding="utf-8"
    )
    export_corpus_html(
        out_dir / "corpus-board.html",
        data_dir=settings.data_dir,
        repo_root=repo_root,
    )
    sample = write_sample_batch_manifest(
        out_dir / "corpus-batch-demo.json",
        repo_root=repo_root,
    )

    (out_dir / "README.md").write_text(
        f"""# Corpus kit

{HONEST}

## Commands

```text
skycache corpus doctor
skycache corpus status
skycache corpus export --out data/ops/corpus-board.html
skycache corpus kit --out data/corpus-kit
skycache skybrary corpus sample-manifest --out data/corpus-batch-demo.json
skycache skybrary corpus batch --manifest data/corpus-batch-demo.json --allow-local --ingest
```

## Legal

Fail-closed licenses. Operator-run only. Never pirate mirrors.

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Corpus field checklist

{HONEST}

- [ ] corpus doctor go_offline_batch true
- [ ] sample-manifest written for offline demo
- [ ] batch --allow-local for fixtures only in lab
- [ ] incomplete passports driven toward zero before partner share
- [ ] never point batch at pirate mirrors
- [ ] board PDF archived with pilot files
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
                "download_hint": "/downloads/skycache-corpus-kit.zip",
                "sample_manifest": sample,
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
        "go_offline_batch": doc.get("go_offline_batch"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
