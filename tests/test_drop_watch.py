from pathlib import Path
import shutil

from skycache.config import Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.drop_watch import DropWatcher


def test_drop_scan_ingests_package(tmp_path: Path):
    samples = samples_dir() / "packages" / "health-ors-001"
    assert samples.is_dir()

    settings = Settings(data_dir=tmp_path / "data")
    settings.ensure_dirs()
    watcher = DropWatcher(settings)
    dest = watcher.incoming / "health-ors-001"
    shutil.copytree(samples, dest)

    ids = watcher.scan_once()
    assert "health-ors-001" in ids
    assert not dest.exists()
    assert (watcher.done / "health-ors-001").is_dir()

    cat = Catalog(settings.db_path)
    assert cat.get("health-ors-001") is not None
    cat.close()
