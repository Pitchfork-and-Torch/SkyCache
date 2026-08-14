"""New Nexus-era plugins: bulk open pack, open data hints, community board."""

from __future__ import annotations

from pathlib import Path

from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.pipelines.runner import PipelineRunner


def test_open_data_hint_and_community_board(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    cat = Catalog(settings.db_path)
    content = ContentManager(settings, cat)
    runner = PipelineRunner(settings, content)

    names = {p["name"] for p in runner.list_plugins()}
    assert "bulk_open_pack" in names
    assert "open_data_hint" in names
    assert "community_board" in names

    r = runner.run(SourceSpec(plugin="open_data_hint"))
    assert r.success
    assert cat.count() >= 1

    r2 = runner.run(
        SourceSpec(
            plugin="community_board",
            options={
                "title": "Clinic hours",
                "body": "Open Mon - Fri 9 - 15",
                "priority": "health",
                "id": "clinic-hours-demo",
            },
        )
    )
    assert r2.success
    assert cat.get("clinic-hours-demo") is not None
    cat.close()


def test_bulk_open_pack_from_samples(tmp_path: Path):
    packs = samples_dir() / "packages"
    if not packs.is_dir():
        return
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    cat = Catalog(settings.db_path)
    content = ContentManager(settings, cat)
    runner = PipelineRunner(settings, content)
    r = runner.run(SourceSpec(plugin="bulk_open_pack", uri=str(packs)))
    assert r.success
    assert cat.count() >= 3
    cat.close()
