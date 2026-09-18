"""Simulation plugin - no RF hardware required."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from skycache.config import samples_dir
from skycache.models import CaptureResult, ContentPackage, SourceSpec


class SimFilePlugin:
    name = "sim_file"
    description = "Load sample packages or local file trees (demo / offline mode)"
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        if source.plugin and source.plugin != self.name:
            return False
        return True

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        uri = source.uri or str(samples_dir() / "packages")
        src = Path(uri)
        if not src.exists():
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"Simulation source not found: {src}",
            )

        # Copy first package found (or whole tree if single package)
        if (src / "manifest.json").is_file():
            dest = workdir / src.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            pkg = ContentPackage.model_validate(data)
            return CaptureResult(
                plugin=self.name,
                success=True,
                message=f"Simulated capture of {pkg.id}",
                artifacts=[str(dest / "manifest.json")],
                metadata={"sim": True},
                suggested_package=pkg,
            )

        # Pick packages directory children
        children = [
            c for c in sorted(src.iterdir()) if c.is_dir() and (c / "manifest.json").is_file()
        ]
        if not children:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"No packages under {src}",
            )

        # Return multi-ingest signal via first + note count in metadata
        # Runner will ingest all when option all=true
        if source.options.get("all", True):
            for child in children:
                dest = workdir / child.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(child, dest)
            return CaptureResult(
                plugin=self.name,
                success=True,
                message=f"Simulated {len(children)} packages",
                artifacts=[str(workdir / c.name / "manifest.json") for c in children],
                metadata={"sim": True, "count": len(children), "batch": True},
                suggested_package=None,
            )

        child = children[0]
        dest = workdir / child.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(child, dest)
        data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        # Stamp received_at as now for demo freshness
        data["received_at"] = datetime.now(timezone.utc).isoformat()
        pkg = ContentPackage.model_validate(data)
        (dest / "manifest.json").write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Simulated capture of {pkg.id}",
            artifacts=[str(dest / "manifest.json")],
            metadata={"sim": True},
            suggested_package=pkg,
        )
