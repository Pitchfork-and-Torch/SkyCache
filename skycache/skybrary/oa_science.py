"""Open-access science bulk import (arXiv / PMC-style)  -  operator-run, license-gated.

Only packaging paths that are explicitly open-access / CC / public domain.
Never pirate mirrors. Rate-limited. Fail closed on license.

v0.9.1: catalog-driven batch from local snapshot (JSON/CSV), fixture-friendly for sim/CI.
Live host allowlist extended for arxiv.org, ncbi.nlm.nih.gov, europepmc.org.
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
from skycache.skybrary.corpus_import import (
    build_work_package,
    import_open_url,
    register_packages_to_skybrary,
)
from skycache.skybrary.license_gate import assert_license_allowed
from skycache.skybrary.provenance import build_provenance_report, write_provenance_report

log = logging.getLogger("skycache.skybrary.oa_science")

# Hosts already or newly allowed for OA science (open_fetch must also allow)
OA_SCIENCE_HOST_HINTS: tuple[str, ...] = (
    "arxiv.org",
    "export.arxiv.org",
    "ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "europepmc.org",
    "www.europepmc.org",
    "plos.org",
    "journals.plos.org",
)

DEFAULT_LICENSE = "open-access"
DEFAULT_MAX = 20
DEFAULT_DELAY = 2.0
DEFAULT_MAX_BYTES = 80 * 1024 * 1024

# Licenses acceptable for OA science packaging (subset of license_gate + OA wording)
_OA_OK = (
    "open-access",
    "open access",
    "cc-by",
    "cc0",
    "public domain",
    "public-domain",
    "cc-by-sa",
    "apache-2.0",
    "mit",
)


def license_ok_for_oa(raw: str) -> bool:
    lic = (raw or "").strip().lower()
    if not lic:
        return False
    return any(m in lic for m in _OA_OK)


def load_oa_catalog(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return list(data.get("works") or data.get("entries") or data.get("items") or [])
    reader = csv.DictReader(text.splitlines())
    return [dict(r) for r in reader]


def _norm(raw: dict[str, Any]) -> dict[str, Any] | None:
    url = (
        raw.get("text_url")
        or raw.get("url")
        or raw.get("pdf_url")
        or raw.get("fulltext_url")
        or ""
    ).strip()
    if not url:
        return None
    license_name = str(raw.get("license") or DEFAULT_LICENSE)
    if not license_ok_for_oa(license_name):
        return None
    oid = str(raw.get("id") or raw.get("arxiv_id") or raw.get("pmc_id") or Path(urlparse(url).path).stem)
    title = str(raw.get("title") or oid)
    authors = raw.get("authors") or raw.get("creators") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(";") if a.strip()]
    subjects = raw.get("subjects") or ["science", "stem", "open_access"]
    if isinstance(subjects, str):
        subjects = [s.strip() for s in subjects.split(",") if s.strip()]
    return {
        "id": oid,
        "title": title,
        "authors": [str(a) for a in authors],
        "license": license_name,
        "subjects": [str(s) for s in subjects] or ["science", "stem"],
        "language": str(raw.get("language") or "en"),
        "url": url,
        "source": str(raw.get("source") or "oa_catalog"),
    }


def import_oa_science_catalog(
    catalog_path: Path,
    out_dir: Path,
    *,
    max_works: int = DEFAULT_MAX,
    max_bytes_total: int = DEFAULT_MAX_BYTES,
    delay_s: float = DEFAULT_DELAY,
    dry_run: bool = False,
    allow_local_file: bool = False,
    settings: Any | None = None,
    ingest: bool = False,
    default_license: str = DEFAULT_LICENSE,
) -> dict[str, Any]:
    """Batch-import open-access science entries from a catalog snapshot."""
    assert_license_allowed(default_license)
    catalog_path = Path(catalog_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected: list[dict[str, Any]] = []
    skipped_license = 0
    for raw in load_oa_catalog(catalog_path):
        n = _norm(raw)
        if n is None:
            if (raw.get("url") or raw.get("text_url")) and not license_ok_for_oa(
                str(raw.get("license") or "")
            ):
                skipped_license += 1
            continue
        selected.append(n)
        if len(selected) >= max_works:
            break

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "selected": len(selected),
            "skipped_license": skipped_license,
            "entries": selected,
            "legal": "OA / CC / PD only  -  never pirate mirrors",
        }

    packages: list[str] = []
    package_dirs: list[Path] = []
    errors: list[str] = []
    prov_items: list[dict[str, Any]] = []
    bytes_total = 0

    for i, entry in enumerate(selected):
        if bytes_total >= max_bytes_total:
            errors.append("max_bytes_total reached")
            break
        work_id = f"oa-{entry['id']}".replace("/", "-").replace(" ", "-")[:64]
        url = entry["url"]
        lic = assert_license_allowed(entry["license"] or default_license)
        try:
            if allow_local_file and not url.lower().startswith(("http://", "https://")):
                local = Path(url)
                if not local.is_file():
                    local = catalog_path.parent / url
                if not local.is_file():
                    raise FileNotFoundError(url)
                body = local.read_text(encoding="utf-8", errors="replace")
                # Soft cap body for FTS
                if len(body) > 500_000:
                    body = body[:500_000] + "\n\n[Truncated for local FTS; full file retained if payload.]"
                pkg = build_work_package(
                    out_dir / work_id,
                    work_id=work_id,
                    title=entry["title"],
                    body=body,
                    license_name=lic,
                    creators=entry["authors"] or ["Open-access author"],
                    subjects=entry["subjects"],
                    language=entry["language"],
                    provenance={
                        "source": entry["source"],
                        "url": str(local.resolve()),
                        "note": "OA science fixture/local import; operator verified license",
                    },
                    priority_class="education",
                )
                result = {"package": str(pkg), "work_id": work_id}
            else:
                validate_open_url(url)
                result = import_open_url(
                    url,
                    out_dir,
                    license_name=lic,
                    title=entry["title"],
                    work_id=work_id,
                    language=entry["language"],
                    subjects=entry["subjects"],
                    creators=entry["authors"] or ["Open-access author"],
                )
            pkg_dir = Path(result.get("package") or out_dir / work_id)
            package_dirs.append(pkg_dir)
            packages.append(work_id)
            size = sum(f.stat().st_size for f in pkg_dir.rglob("*") if f.is_file())
            bytes_total += size
            prov_items.append(
                {
                    "id": work_id,
                    "title": entry["title"],
                    "license": lic,
                    "provenance_url": url,
                    "redistribute": "review",
                    "notes": "OA science catalog import; confirm CC/OA terms before redistribute.",
                }
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("OA skip %s: %s", entry.get("id"), exc)
            errors.append(f"{entry.get('id')}: {exc}")
        if i < len(selected) - 1 and delay_s > 0 and not allow_local_file:
            time.sleep(float(delay_s))

    ingested: list[str] = []
    if ingest and settings is not None and package_dirs:
        ingested = register_packages_to_skybrary(package_dirs, settings=settings)

    report = build_provenance_report(
        prov_items,
        batch_id=f"oa-science-{catalog_path.stem}",
        operator_note="Open-access science batch; license-gated; not a complete OA dump.",
    )
    report_path = out_dir / "provenance-oa-science-batch.json"
    write_provenance_report(report, report_path)

    return {
        "ok": True,
        "imported": len(packages),
        "packages": packages,
        "package_dirs": [str(p) for p in package_dirs],
        "bytes_total": bytes_total,
        "errors": errors[:30],
        "skipped_license": skipped_license,
        "ingested": ingested,
        "provenance_report": str(report_path),
        "legal": (
            "Open-access / CC / PD science only. Operator confirms each license. "
            "Not a complete arXiv/PMC mirror. Never pirate sites."
        ),
    }
