"""v1.33 Open Resilience Wave: corpus, prioritizer, open_fta_sim, pack budgets."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.models import SourceSpec
from skycache.nexus.federation import PRIORITY_FEDERATION_ORDER, priority_works_delta
from skycache.ops.library_ops import pack_budget_report
from skycache.pipelines.plugins.open_fta_sim import OpenFtaSimPlugin
from skycache.pipelines.runner import PipelineRunner
from skycache.skybrary.pack_profile import BUILTIN_PROFILES
from skycache.skybrary.sample_corpus import SAMPLES
from skycache.skybrary.sample_corpus_stem import STEM_SAMPLES
from skycache.web.app import create_app


def test_stem_wave_and_sample_count():
    assert len(STEM_SAMPLES) >= 10
    assert len(SAMPLES) >= 78
    ids = {s["work_id"] for s in SAMPLES}
    for s in STEM_SAMPLES:
        assert s["work_id"] in ids
        assert len(s["body"]) > 80


def test_archive_pack_profiles_exist():
    assert "archive-100mb" in BUILTIN_PROFILES
    assert "archive-1gb" in BUILTIN_PROFILES
    assert BUILTIN_PROFILES["archive-100mb"]["max_bytes"] == 100 * 1024 * 1024
    assert "stem-lite" in BUILTIN_PROFILES


def test_pack_budget_report():
    rep = pack_budget_report(profiles=["archive-100mb", "literacy-starter", "emergency-health"])
    assert rep["schema"] == "skycache.library.pack_budgets.v1"
    assert len(rep["profiles"]) == 3
    assert all(p.get("ok") for p in rep["profiles"])
    assert rep["profiles"][0]["curated_sample_count"] >= 78


def test_open_fta_sim_plugin(tmp_path: Path):
    plug = OpenFtaSimPlugin()
    src = SourceSpec(plugin="open_fta_sim", uri="open-fta-sim", options={"sim": True})
    assert plug.can_handle(src)
    result = plug.run(src, tmp_path / "run")
    assert result.success is True
    assert result.suggested_package is not None
    assert result.suggested_package.license.lower().find("public") >= 0
    assert (tmp_path / "run").exists()
    # Forbidden commercial hint
    bad = SourceSpec(plugin="open_fta_sim", uri="starlink-decrypt-demo")
    assert plug.can_handle(bad) is False
    bad2 = SourceSpec(plugin="open_fta_sim", uri="open-fta-sim", options={"note": "oneweb"})
    res_bad = plug.run(bad2, tmp_path / "bad")
    assert res_bad.success is False


def test_open_fta_sim_via_runner(tmp_path: Path):
    from skycache.db.catalog import Catalog
    from skycache.ingest.normalizer import ContentManager

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    runner = PipelineRunner(settings, content)
    names = {p["name"] for p in runner.list_plugins()}
    assert "open_fta_sim" in names
    src = SourceSpec(plugin="open_fta_sim", uri="fta-sim")
    result = runner.run(src)
    assert result.success is True


def test_priority_works_delta_orders_survival():
    class _FakeFabric:
        def missing_works_from(self, _wm, max_items=40):
            return [
                {"work_id": "g1", "priority_class": "general", "civilizational_tier": 1},
                {"work_id": "e1", "priority_class": "emergency", "civilizational_tier": 3},
                {"work_id": "h1", "priority_class": "health", "civilizational_tier": 2},
                {"work_id": "ed1", "priority_class": "education", "civilizational_tier": 1},
            ][:max_items]

    out = priority_works_delta(_FakeFabric(), {"works_manifest": {"works": []}}, max_items=10)
    assert out[0]["work_id"] == "e1"
    assert out[1]["work_id"] == "h1"
    assert PRIORITY_FEDERATION_ORDER[0] == "emergency"


def test_library_pack_budgets_cli_schema():
    # Smoke: function already covers; ensure API not required
    rep = pack_budget_report()
    assert "archive-100mb" in {p["id"] for p in rep["profiles"] if p.get("ok")}
