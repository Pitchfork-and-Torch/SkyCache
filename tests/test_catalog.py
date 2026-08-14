from datetime import datetime, timezone

from skycache.db.catalog import Catalog
from skycache.models import ContentFile, ContentPackage, PriorityClass, SourceInfo


def test_upsert_and_list(tmp_path):
    cat = Catalog(tmp_path / "t.db")
    pkg = ContentPackage(
        id="p1",
        kind="html_pack",
        priority_class=PriorityClass.HEALTH,
        title={"en": "Hello"},
        received_at=datetime.now(timezone.utc),
        size_bytes=10,
        source=SourceInfo(type="test"),
        files=[ContentFile(path="index.html", mime="text/html", size_bytes=10)],
    )
    cat.upsert_package(pkg, tmp_path / "p1", score=100)
    rows = cat.list_packages()
    assert len(rows) == 1
    assert rows[0].package.id == "p1"
    assert cat.count() == 1
    cat.close()
