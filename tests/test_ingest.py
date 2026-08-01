import runpy

from skycache.config import Settings, package_root, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager


def _ensure_samples() -> None:
    samples = samples_dir() / "packages"
    if not samples.is_dir() or not any(samples.iterdir()):
        runpy.run_path(str(package_root() / "scripts" / "make_sample_package.py"), run_name="__main__")


def test_load_samples(tmp_path):
    _ensure_samples()

    settings = Settings(data_dir=tmp_path / "data")
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    cm = ContentManager(settings, catalog)
    pkgs = cm.load_samples(samples_dir())
    assert len(pkgs) >= 6
    assert catalog.count() >= 6
    rec = catalog.get("emergency-checklist-001")
    assert rec is not None
    assert rec.package.pinned is True
    catalog.close()


def test_forbidden_source_rejected(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    try:
        settings.validate_source_name("starlink-decoder")
        raised = False
    except ValueError:
        raised = True
    assert raised
