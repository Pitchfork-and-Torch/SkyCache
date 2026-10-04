"""Ingest CaptureResults and package directories into the catalog."""

from __future__ import annotations

import logging
from pathlib import Path

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.package_loader import copy_package_tree, discover_packages, load_manifest
from skycache.models import CaptureResult, ContentPackage
from skycache.policy.prioritizer import Prioritizer

log = logging.getLogger("skycache.ingest")


class ContentManager:
    def __init__(self, settings: Settings, catalog: Catalog) -> None:
        self.settings = settings
        self.catalog = catalog
        self.prioritizer = Prioritizer(
            content_dir=settings.content_dir,
            disk_reserve_bytes=settings.disk_reserve_bytes,
            max_content_bytes=settings.max_content_bytes,
            preferred_languages=settings.preferred_languages,
        )

    def _apply_eviction(self, need_bytes: int = 0) -> list[str]:
        if not self.prioritizer.pressure(self.catalog.total_size() + need_bytes):
            # Still check soft max
            if self.settings.max_content_bytes <= 0:
                return []
            if self.catalog.total_size() + need_bytes <= self.settings.max_content_bytes:
                return []
        candidates = [
            (rec.package, rec.score) for rec in self.catalog.candidates_for_eviction()
        ]
        to_remove = self.prioritizer.plan_evictions(
            candidates,
            catalog_total_size=self.catalog.total_size(),
            need_bytes=need_bytes,
        )
        for pid in to_remove:
            self.catalog.delete_package(pid, remove_files=True)
            log.info("Evicted package %s under storage pressure", pid)
        return to_remove

    def ingest_package_dir(self, src: Path) -> ContentPackage:
        src = Path(src)
        pkg = load_manifest(src)
        self.settings.validate_source_name(pkg.source.type)
        if pkg.source.plugin:
            self.settings.validate_source_name(pkg.source.plugin)

        self._apply_eviction(need_bytes=pkg.size_bytes)
        dest = self.settings.content_dir / pkg.id
        copy_package_tree(src, dest)
        score = self.prioritizer.score(pkg)
        self.catalog.upsert_package(pkg, dest, score=score)
        self.catalog.log_event(
            "info",
            "ingest",
            f"Ingested {pkg.id} ({pkg.priority_class.value})",
            {"score": score, "size": pkg.size_bytes},
        )
        log.info("Ingested package %s score=%.1f", pkg.id, score)
        return pkg

    def ingest_path(self, path: Path) -> list[ContentPackage]:
        path = Path(path)
        packages = discover_packages(path)
        if not packages and path.is_file() and path.name == "manifest.json":
            packages = [path.parent]
        if not packages:
            raise FileNotFoundError(f"No SkyCache packages found at {path}")
        return [self.ingest_package_dir(p) for p in packages]

    def ingest_capture(self, result: CaptureResult) -> ContentPackage | None:
        if not result.success:
            self.catalog.log_event("warning", "capture", result.message or "capture failed")
            return None
        if result.suggested_package is None:
            self.catalog.log_event(
                "warning",
                "capture",
                f"Plugin {result.plugin} succeeded but produced no package",
            )
            return None
        pkg = result.suggested_package
        # If artifacts exist, ensure package files are under a temp tree
        work = self.settings.work_dir / f"capture-{pkg.id}"
        work.mkdir(parents=True, exist_ok=True)
        # Package may already point at workdir files; re-ingest via directory
        # Prefer writing manifest next to first artifact parent
        if result.artifacts:
            base = Path(result.artifacts[0]).parent
            manifest_path = base / "manifest.json"
            if not manifest_path.exists():
                manifest_path.write_text(
                    pkg.model_dump_json(indent=2),
                    encoding="utf-8",
                )
            return self.ingest_package_dir(base)
        # Manifest-only package
        dest_src = work
        (dest_src / "manifest.json").write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
        return self.ingest_package_dir(dest_src)

    def load_samples(self, samples_root: Path) -> list[ContentPackage]:
        pkg_root = Path(samples_root) / "packages"
        if not pkg_root.is_dir():
            log.warning("No samples at %s", pkg_root)
            return []
        return self.ingest_path(pkg_root)
