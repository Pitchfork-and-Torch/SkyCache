"""USB / drop-folder ingest watcher (Phase 1).

Operators copy SkyCache package directories (with manifest.json) or .zim files into a
drop directory. SkyCache ingests them and moves processed items to ``done/`` or
``failed/`` subfolders.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.pipelines.runner import PipelineRunner

log = logging.getLogger("skycache.drop")


class DropWatcher:
    def __init__(self, settings: Settings, drop_dir: Path | None = None) -> None:
        self.settings = settings
        self.drop_dir = Path(drop_dir or (settings.data_dir / "drop"))
        self.incoming = self.drop_dir / "incoming"
        self.done = self.drop_dir / "done"
        self.failed = self.drop_dir / "failed"
        for d in (self.incoming, self.done, self.failed):
            d.mkdir(parents=True, exist_ok=True)

    def scan_once(self) -> list[str]:
        """Ingest everything currently in incoming/. Returns package/source ids processed."""
        catalog = Catalog(self.settings.db_path)
        content = ContentManager(self.settings, catalog)
        runner = PipelineRunner(self.settings, content)
        processed: list[str] = []

        items = sorted(self.incoming.iterdir(), key=lambda p: p.name)
        for item in items:
            if item.name.startswith("."):
                continue
            try:
                if item.is_dir() and (item / "manifest.json").is_file():
                    pkgs = content.ingest_path(item)
                    for p in pkgs:
                        processed.append(p.id)
                    self._move(item, self.done / item.name)
                elif item.is_file() and item.suffix.lower() == ".zim":
                    result = runner.run(
                        SourceSpec(plugin="package_import", uri=str(item))
                    )
                    if not result.success:
                        raise RuntimeError(result.message)
                    processed.append(result.suggested_package.id if result.suggested_package else item.name)
                    self._move(item, self.done / item.name)
                elif item.is_file() and item.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                    result = runner.run(
                        SourceSpec(plugin="satdump_weather", uri=str(item))
                    )
                    if not result.success:
                        raise RuntimeError(result.message)
                    processed.append(
                        result.suggested_package.id if result.suggested_package else item.name
                    )
                    self._move(item, self.done / item.name)
                else:
                    log.warning("Skipping unrecognized drop item: %s", item)
            except Exception as exc:  # noqa: BLE001
                log.exception("Drop ingest failed for %s: %s", item, exc)
                try:
                    self._move(item, self.failed / item.name)
                except OSError:
                    pass
                catalog.log_event("error", "drop", f"Failed {item.name}: {exc}")

        catalog.close()
        return processed

    def _move(self, src: Path, dest: Path) -> None:
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    def loop(self, interval_sec: float = 15.0) -> None:
        log.info("Watching drop folder %s every %.0fs", self.incoming, interval_sec)
        while True:
            ids = self.scan_once()
            if ids:
                log.info("Ingested from drop: %s", ", ".join(ids))
            time.sleep(interval_sec)
