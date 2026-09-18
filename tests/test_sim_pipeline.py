import runpy

from skycache.config import Settings, package_root, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.pipelines.runner import PipelineRunner


def test_sim_pipeline_batch(tmp_path):
    samples = samples_dir() / "packages"
    if not samples.is_dir() or not any(samples.iterdir()):
        runpy.run_path(str(package_root() / "scripts" / "make_sample_package.py"), run_name="__main__")

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    runner = PipelineRunner(settings, content)
    result = runner.run(
        SourceSpec(plugin="sim_file", uri=str(samples_dir() / "packages"), options={"all": True})
    )
    assert result.success
    assert catalog.count() >= 1
    catalog.close()
