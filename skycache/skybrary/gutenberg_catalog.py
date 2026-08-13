"""Project Gutenberg-style open catalog adapter (operator-run, legal bulk).

Rate-limited, license-gated, robots/terms respectful. Never pirate mirrors.
CI uses local fixtures only - no live network required for tests.

Catalog input formats:
- JSON list of objects with keys: id|gutenberg_id, title, authors|creators,
  language, subjects, text_url|url
- CSV with headers: id,title,authors,language,subjects,text_url

Each row is packaged via corpus_import.import_open_url (or local file:// for sim).
"""

from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from skycache.capabilities.open_fetch import validate_open_url
from skycache.skybrary.corpus_import import import_open_url, register_packages_to_skybrary
from skycache.skybrary.license_gate import assert_license_allowed
from skycache.skybrary.provenance import build_provenance_report, write_provenance_report

log = logging.getLogger("skycache.skybrary.gutenberg_catalog")

DEFAULT_DELAY_S = 1.5
DEFAULT_MAX_WORKS = 25
DEFAULT_MAX_BYTES_TOTAL = 50 * 1024 * 1024
DEFAULT_LICENSE = "project gutenberg"


def load_catalog_entries(path: Path) -> list[dict[str, Any]]:
    """Load catalog snapshot from JSON or CSV path."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Catalog not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".jsonl":
            rows: list[dict[str, Any]] = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            return rows
        data = json.loads(text)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            works = data.get("works") or data.get("entries") or data.get("items") or []
            return [x for x in works if isinstance(x, dict)]
        raise ValueError("JSON catalog must be a list or object with works/entries")
    # CSV
    reader = csv.DictReader(text.splitlines())
    return [dict(row) for row in reader]


def _normalize_entry(raw: dict[str, Any]) -> dict[str, Any] | None:
    url = (
        raw.get("text_url")
        or raw.get("url")
        or raw.get("plain_text_url")
        or raw.get("download_url")
        or ""
    ).strip()
    if not url:
        return None
    gid = str(
        raw.get("id")
        or raw.get("gutenberg_id")
        or raw.get("work_id")
        or Path(urlparse(url).path).stem
        or "pg-work"
    ).strip()
    title = str(raw.get("title") or gid).strip()
    authors = raw.get("authors") or raw.get("creators") or raw.get("author") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(";") if a.strip()]
    authors = [str(a) for a in authors]
    language = str(raw.get("language") or raw.get("lang") or "en").strip() or "en"
    subjects = raw.get("subjects") or raw.get("subject") or ["literature_pd", "gutenberg"]
    if isinstance(subjects, str):
        subjects = [s.strip() for s in subjects.replace("|", ",").split(",") if s.strip()]
    subjects = [str(s) for s in subjects] or ["literature_pd", "gutenberg"]
    return {
        "id": gid,
        "title": title,
        "authors": authors,
        "language": language,
        "subjects": subjects,
        "text_url": url,
    }


def filter_entries(
    entries: list[dict[str, Any]],
    *,
    language: str | None = None,
    subject_contains: str | None = None,
    max_works: int = DEFAULT_MAX_WORKS,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in entries:
        n = _normalize_entry(raw)
        if not n:
            continue
        if language and n["language"].lower() != language.lower():
            continue
        if subject_contains:
            hay = " ".join(n["subjects"]).lower()
            if subject_contains.lower() not in hay and subject_contains.lower() not in n["title"].lower():
                continue
        out.append(n)
        if len(out) >= max_works:
            break
    return out


def import_gutenberg_catalog(
    catalog_path: Path,
    out_dir: Path,
    *,
    license_name: str = DEFAULT_LICENSE,
    language: str | None = "en",
    subject_contains: str | None = None,
    max_works: int = DEFAULT_MAX_WORKS,
    max_bytes_total: int = DEFAULT_MAX_BYTES_TOTAL,
    delay_s: float = DEFAULT_DELAY_S,
    extra_hosts: list[str] | None = None,
    dry_run: bool = False,
    settings: Any | None = None,
    ingest: bool = False,
    allow_local_file: bool = False,
) -> dict[str, Any]:
    """Import up to max_works from a Gutenberg-style catalog snapshot.

    dry_run: validate and list only (no fetch).
    allow_local_file: permit file:// or absolute local paths for fixtures/sim.
    """
    lic = assert_license_allowed(license_name)
    catalog_path = Path(catalog_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_entries = load_catalog_entries(catalog_path)
    selected = filter_entries(
        raw_entries,
        language=language,
        subject_contains=subject_contains,
        max_works=max_works,
    )

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "catalog": str(catalog_path),
            "selected": len(selected),
            "entries": selected,
            "license": lic,
        }

    packages: list[str] = []
    package_dirs: list[Path] = []
    errors: list[str] = []
    provenance_items: list[dict[str, Any]] = []
    bytes_total = 0

    for i, entry in enumerate(selected):
        if bytes_total >= max_bytes_total:
            errors.append("max_bytes_total reached; stopping")
            break
        url = entry["text_url"]
        work_id = f"pg-{entry['id']}".replace(" ", "-")[:64]
        try:
            # Local fixture path support for sim/CI
            if allow_local_file and not url.lower().startswith(("http://", "https://")):
                local = Path(url)
                if not local.is_file():
                    # relative to catalog dir
                    local = catalog_path.parent / url
                if not local.is_file():
                    raise FileNotFoundError(f"Local fixture not found: {url}")
                from skycache.skybrary.corpus_import import build_work_package

                body = local.read_text(encoding="utf-8", errors="replace")
                pkg = build_work_package(
                    out_dir / work_id,
                    work_id=work_id,
                    title=entry["title"],
                    body=body,
                    license_name=lic,
                    language=entry["language"],
                    subjects=entry["subjects"],
                    creators=entry["authors"] or ["Project Gutenberg (open)"],
                    provenance={
                        "source": "gutenberg_catalog_fixture",
                        "url": str(local.resolve()),
                        "note": "Local fixture for sim/CI; operator-verified open text",
                    },
                    priority_class="education",
                )
                result = {
                    "ok": True,
                    "package_dir": str(pkg),
                    "work_id": work_id,
                    "sha256": "",
                }
            else:
                # Validate host allowlist (http local only for sim mirrors)
                if url.lower().startswith("file:"):
                    if not allow_local_file:
                        raise ValueError("file:// URLs require allow_local_file=True")
                else:
                    validate_open_url(url, extra_hosts)
                result = import_open_url(
                    url,
                    out_dir,
                    license_name=lic,
                    title=entry["title"],
                    work_id=work_id,
                    language=entry["language"],
                    subjects=entry["subjects"],
                    creators=entry["authors"] or ["Project Gutenberg (open)"],
                    extra_hosts=extra_hosts,
                )
            pkg_dir = Path(
                result.get("package_dir")
                or result.get("package")
                or out_dir / work_id
            )
            package_dirs.append(pkg_dir)
            packages.append(work_id)
            size = 0
            for f in pkg_dir.rglob("*"):
                if f.is_file():
                    size += f.stat().st_size
            bytes_total += size
            provenance_items.append(
                {
                    "id": work_id,
                    "title": entry["title"],
                    "license": lic,
                    "provenance_url": url,
                    "sha256": (result.get("sha256") or ""),
                    "redistribute": "review",
                    "notes": "Gutenberg catalog adapter batch; confirm PG terms.",
                }
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Skip %s: %s", entry.get("id"), exc)
            errors.append(f"{entry.get('id')}: {exc}")

        # Rate limit between remote fetches (skip after last)
        if i < len(selected) - 1 and delay_s > 0 and not allow_local_file:
            time.sleep(float(delay_s))

    ingested: list[str] = []
    if ingest and settings is not None and package_dirs:
        ingested = register_packages_to_skybrary(package_dirs, settings=settings)

    report = build_provenance_report(
        provenance_items,
        batch_id=f"gutenberg-catalog-{catalog_path.stem}",
        operator_note="Operator-run Gutenberg-style catalog import; legal PD/open only.",
    )
    report_path = out_dir / "provenance-gutenberg-batch.json"
    write_provenance_report(report, report_path)

    return {
        "ok": True,
        "catalog": str(catalog_path),
        "selected": len(selected),
        "imported": len(packages),
        "packages": packages,
        "package_dirs": [str(p) for p in package_dirs],
        "bytes_total": bytes_total,
        "errors": errors[:30],
        "ingested": ingested,
        "provenance_report": str(report_path),
        "license": lic,
        "legal": (
            "Operator must confirm Project Gutenberg / open-license terms for each work. "
            "Never pirate mirrors. Not a complete archive."
        ),
    }
