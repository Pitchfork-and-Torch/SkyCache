"""Pipeline runner: select plugin, execute, ingest results."""

from __future__ import annotations

import logging
from pathlib import Path

from skycache.config import Settings
from skycache.ingest.normalizer import ContentManager
from skycache.models import CaptureResult, SourceSpec
from skycache.pipelines.plugins import BUILTIN_PLUGINS

log = logging.getLogger("skycache.pipelines")


class PipelineRunner:
    def __init__(self, settings: Settings, content: ContentManager) -> None:
        self.settings = settings
        self.content = content
        self.plugins = list(BUILTIN_PLUGINS)

    def list_plugins(self) -> list[dict[str, object]]:
        return [
            {
                "name": p.name,
                "description": p.description,
                "legal_profile": p.legal_profile,
                "requires_hardware": p.requires_hardware,
            }
            for p in self.plugins
        ]

    def get_plugin(self, name: str):
        for p in self.plugins:
            if p.name == name:
                return p
        return None

    def run(self, source: SourceSpec) -> CaptureResult:
        self.settings.validate_source_name(source.plugin or source.uri or "unknown")
        plugin = None
        if source.plugin:
            plugin = self.get_plugin(source.plugin)
            if plugin is None:
                return CaptureResult(
                    plugin=source.plugin,
                    success=False,
                    message=f"Unknown plugin: {source.plugin}",
                )
        else:
            for p in self.plugins:
                if p.can_handle(source):
                    plugin = p
                    break
        if plugin is None:
            return CaptureResult(
                plugin="none",
                success=False,
                message="No plugin can handle this source",
            )

        if plugin.requires_hardware and self.settings.sim_mode and plugin.name != "sim_file":
            # Allow explicit override
            if not source.options.get("force_live"):
                log.info("Skipping hardware plugin %s in sim_mode", plugin.name)

        workdir = self.settings.work_dir / f"run-{plugin.name}"
        workdir.mkdir(parents=True, exist_ok=True)
        result = plugin.run(source, workdir)
        log.info("Plugin %s: success=%s %s", plugin.name, result.success, result.message)

        if not result.success:
            return result

        # Batch sim: multiple manifests
        if result.metadata.get("batch") and result.artifacts:
            for art in result.artifacts:
                try:
                    self.content.ingest_package_dir(Path(art).parent)
                except Exception as exc:  # noqa: BLE001
                    log.exception("Batch ingest failed for %s: %s", art, exc)
            return result

        if result.suggested_package is not None or result.artifacts:
            try:
                self.content.ingest_capture(result)
            except Exception as exc:  # noqa: BLE001
                log.exception("Ingest failed: %s", exc)
                result = result.model_copy(
                    update={"success": False, "message": f"Ingest failed: {exc}"}
                )
        return result
