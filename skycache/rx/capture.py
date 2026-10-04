"""Wrap SatDump for offline IQ/baseband decode; primary live path remains product watch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.pipelines.runner import PipelineRunner
from skycache.rx.recipes import get_recipe


def capture_to_catalog(
    settings: Settings,
    *,
    recipe_id: str,
    input_path: str,
    force_live: bool = False,
) -> dict[str, Any]:
    """
    Run satdump_weather (or gr_satellites) plugin and ingest into catalog.

    input_path: decoded image OR baseband/IQ file for SatDump CLI.
    """
    recipe = get_recipe(recipe_id) or get_recipe("product_import")
    assert recipe is not None
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    runner = PipelineRunner(settings, content)

    plugin = str(recipe.get("plugin") or "satdump_weather")
    pipeline = recipe.get("satdump_pipeline") or "import"
    options: dict[str, Any] = {
        "pipeline": pipeline,
        "kind": "weather",
        "force_live": bool(force_live),
    }
    if plugin == "gr_satellites":
        options["wav"] = input_path
        options["satellite"] = recipe_id

    source = SourceSpec(
        plugin=plugin,
        uri=str(input_path),
        options=options,
    )
    result = runner.run(source)
    catalog.close()
    pkg_id = result.suggested_package.id if result.suggested_package else None
    return {
        "ok": bool(result.success),
        "message": result.message,
        "plugin": plugin,
        "recipe": recipe.get("id"),
        "package_id": pkg_id,
        "artifacts": list(result.artifacts or []),
        "legal": recipe.get("legal"),
        "honest": recipe.get("honest"),
    }


def import_directory_products(
    settings: Settings,
    directory: Path,
    *,
    recipe_id: str = "product_import",
    satellite: str = "",
) -> dict[str, Any]:
    from skycache.rx.product_watch import watch_once

    return watch_once(
        Path(directory),
        settings,
        recipe=recipe_id,
        satellite=satellite,
        max_new=50,
    )
