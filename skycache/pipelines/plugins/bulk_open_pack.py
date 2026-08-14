"""Bulk importer for open/offline content trees (education, health, MoH-style).

Accepts a directory of SkyCache packages, loose HTML folders, or a JSON inventory
of openly licensed packs. Enforces legal source validation - never commercial
decrypt or paid constellation sources.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from skycache.models import CaptureResult, SourceSpec
from skycache.pipelines.plugins.package_import import PackageImportPlugin

log = logging.getLogger("skycache.plugins.bulk_open_pack")


class BulkOpenPackPlugin:
    name = "bulk_open_pack"
    description = (
        "Bulk-import open offline packs (package dirs, HTML folders, inventory JSON). "
        "Openly licensed / operator-authored only."
    )
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        if source.plugin == self.name:
            return True
        if source.plugin:
            return False
        if not source.uri:
            return False
        p = Path(source.uri)
        if p.is_file() and p.suffix.lower() == ".json" and "inventory" in p.name.lower():
            return True
        if p.is_dir() and (p / "inventory.json").is_file():
            return True
        return False

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        root = Path(source.uri)
        if not root.exists():
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"Path not found: {root}",
            )

        targets: list[Path] = []
        inv_path: Path | None = None
        if root.is_file() and root.suffix.lower() == ".json":
            inv_path = root
        elif root.is_dir() and (root / "inventory.json").is_file():
            inv_path = root / "inventory.json"
            root = root

        if inv_path:
            data = json.loads(inv_path.read_text(encoding="utf-8"))
            for entry in data.get("packages") or data.get("items") or []:
                rel = entry.get("path") or entry.get("id")
                if not rel:
                    continue
                p = (inv_path.parent / rel).resolve()
                if p.exists():
                    targets.append(p)
        else:
            # Every subdirectory with manifest.json
            for child in sorted(root.iterdir()):
                if child.is_dir() and (child / "manifest.json").is_file():
                    targets.append(child)

        if not targets:
            # Fallback: import root as single folder pack
            targets = [root]

        importer = PackageImportPlugin()
        artifacts: list[str] = []
        messages: list[str] = []
        ok = 0
        for t in targets:
            sub = SourceSpec(uri=str(t), plugin="package_import", options=dict(source.options))
            r = importer.run(sub, workdir / t.name)
            if r.success:
                ok += 1
                artifacts.extend(r.artifacts)
                messages.append(r.message)
            else:
                messages.append(f"FAIL {t.name}: {r.message}")
                log.warning("bulk skip %s: %s", t, r.message)

        return CaptureResult(
            plugin=self.name,
            success=ok > 0,
            message=f"Bulk open pack: {ok}/{len(targets)} imported. " + "; ".join(messages[:8]),
            artifacts=artifacts,
            metadata={
                "batch": True,
                "imported": ok,
                "total": len(targets),
                "legal": "open/operator packs only - no commercial decrypt",
            },
        )
