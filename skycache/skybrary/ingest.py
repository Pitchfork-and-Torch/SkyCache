"""Ingest Skybrary package directories into the works catalog + content store."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.models import Edition, Work
from skycache.skybrary.sample_corpus import build_sample_packages

log = logging.getLogger("skycache.skybrary.ingest")


def ingest_package_dir_to_skybrary(
    pkg_dir: Path,
    *,
    sky: SkybraryCatalog,
    content: ContentManager | None = None,
) -> str:
    """Register a SkyCache package that carries work/edition metadata."""
    pkg_dir = Path(pkg_dir)
    manifest_path = pkg_dir / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    extra = (data.get("source") or {}).get("extra") or {}
    work_raw = extra.get("work") or {}
    edition_raw = extra.get("edition") or {}

    if work_raw:
        work = Work.model_validate(work_raw)
    else:
        work = Work(
            work_id=data["id"],
            title=data.get("title") or {"en": data["id"]},
            creators=[],
            languages=data.get("languages") or ["en"],
            subjects=data.get("tags") or [],
            license=data.get("license") or "unknown",
            provenance={"source": "package_manifest"},
            summary=data.get("summary") or {},
        )

    body = ""
    txt = pkg_dir / "work.txt"
    if txt.is_file():
        body = txt.read_text(encoding="utf-8")

    package_id = data["id"]
    if content is not None:
        pkg = content.ingest_package_dir(pkg_dir)
        package_id = pkg.id

    sky.upsert_work(work, package_id=package_id, body_text=body)

    if edition_raw:
        ed = Edition.model_validate(edition_raw)
        if not ed.path:
            ed.path = "work.txt"
        sky.upsert_edition(ed)
    elif body:
        sky.upsert_edition(
            Edition(
                edition_id=f"{work.work_id}-txt",
                work_id=work.work_id,
                format="txt",
                path="work.txt",
                size_bytes=len(body.encode("utf-8")),
                sha256=str(extra.get("sha256") or ""),
                priority_class=str(data.get("priority_class") or "education"),
            )
        )
    log.info("Skybrary ingested work %s", work.work_id)
    return work.work_id


def bootstrap_samples_with_settings(
    settings,
    sky: SkybraryCatalog,
    samples_out: Path | None = None,
) -> list[str]:
    """Build PD samples, ingest to content catalog + skybrary catalog."""
    out = Path(samples_out or (settings.data_dir / "skybrary-build"))
    paths = build_sample_packages(out)
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    ids: list[str] = []
    for p in paths:
        wid = ingest_package_dir_to_skybrary(p, sky=sky, content=content)
        ids.append(wid)
    catalog.close()
    return ids
