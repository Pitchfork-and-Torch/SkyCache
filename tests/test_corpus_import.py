"""Wave 2.B2: legal corpus folder import + open-URL packaging (no live bulk download)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest import mock

import pytest

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.pipelines.runner import PipelineRunner
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.corpus_import import (
    build_work_package,
    extract_text_from_epub,
    import_folder,
    import_open_url,
    register_packages_to_skybrary,
)
from skycache.skybrary.license_gate import assert_license_allowed


def _write_minimal_epub(path: Path, title: str, body: str) -> Path:
    """Synthetic EPUB-like ZIP (valid enough for our extractor)."""
    path = Path(path)
    xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body><h1>{title}</h1><p>{body}</p></body>
</html>
"""
    container = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.xhtml"
      media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("OEBPS/content.xhtml", xhtml)
    return path


def test_license_required_fail_closed(tmp_path: Path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.txt").write_text("hello open world", encoding="utf-8")
    with pytest.raises(ValueError):
        import_folder(src, tmp_path / "out", license_name="")
    with pytest.raises(ValueError):
        import_folder(src, tmp_path / "out", license_name="all rights reserved commercial")


def test_import_folder_txt_and_epub(tmp_path: Path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "fox-and-grapes.txt").write_text(
        "A fox longed for grapes hanging high on the vine. Public domain sample.",
        encoding="utf-8",
    )
    _write_minimal_epub(
        src / "tiny-essay.epub",
        "Tiny Essay",
        "This is a synthetic open essay body for Skybrary corpus tests.",
    )
    # Unsupported extension ignored
    (src / "notes.pdf").write_bytes(b"%PDF-not-really")

    report = import_folder(
        src,
        tmp_path / "out",
        license_name="public domain",
        subjects=["literacy", "corpus_import"],
        creators=["Test Curator"],
    )
    assert report["ok"]
    assert report["imported"] == 2
    assert report["total_candidates"] == 2
    packages = [Path(p) for p in report["packages"]]
    assert len(packages) == 2
    for p in packages:
        assert (p / "manifest.json").is_file()
        assert (p / "work.txt").is_file()
        assert (p / "index.html").is_file()
        man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        assert man["license"] == "public domain"
        assert man["source"]["type"] == "corpus_import"
        assert "work" in man["source"]["extra"]

    epub_pkg = next(p for p in packages if "essay" in p.name or "tiny" in p.name)
    # EPUB binary retained
    assert any(f.suffix.lower() == ".epub" for f in epub_pkg.iterdir() if f.is_file())


def test_extract_text_from_epub(tmp_path: Path):
    epub = _write_minimal_epub(
        tmp_path / "x.epub",
        "Hello Title",
        "UniquePhraseCorpusTest42 appears here.",
    )
    text = extract_text_from_epub(epub)
    assert "UniquePhraseCorpusTest42" in text
    assert "Hello Title" in text


def test_register_into_skybrary_and_content(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    src = tmp_path / "in"
    src.mkdir()
    (src / "gettysburg-snippet.txt").write_text(
        "Four score and seven years ago our fathers brought forth liberty.",
        encoding="utf-8",
    )
    report = import_folder(src, tmp_path / "built", license_name="public domain")
    ids = register_packages_to_skybrary(
        [Path(p) for p in report["packages"]],
        settings=settings,
        register_content=True,
    )
    assert len(ids) == 1
    cat = Catalog(settings.db_path)
    assert cat.count() >= 1
    cat.close()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    hits = sky.search("liberty")
    assert any("gettysburg" in h["work_id"] or "liberty" in json.dumps(h).lower() for h in hits)
    assert sky.count() >= 1
    sky.close()


def test_plugin_corpus_folder_import(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    src = tmp_path / "in"
    src.mkdir()
    (src / "aesop-fox.txt").write_text(
        "The fox and the grapes. Sour grapes fable for test.",
        encoding="utf-8",
    )
    cat = Catalog(settings.db_path)
    content = ContentManager(settings, cat)
    runner = PipelineRunner(settings, content)
    names = {p["name"] for p in runner.list_plugins()}
    assert "corpus_folder_import" in names

    # Fail closed without license
    bad = runner.run(SourceSpec(plugin="corpus_folder_import", uri=str(src), options={}))
    assert not bad.success

    ok = runner.run(
        SourceSpec(
            plugin="corpus_folder_import",
            uri=str(src),
            options={"license": "public domain", "subjects": "literacy,fable"},
        )
    )
    assert ok.success
    assert ok.metadata.get("imported") == 1
    assert cat.count() >= 1
    cat.close()


def test_import_open_url_mocked(tmp_path: Path):
    """No live network: mock open_fetch after allowlist validation."""
    body = b"Project Gutenberg sample text. The fox jumped over the moon.\n"
    url = "https://www.gutenberg.org/files/99999/99999-0.txt"

    def fake_fetch(u, dest, **kwargs):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return {"url": u, "path": str(dest), "bytes": len(body), "content_type": "text/plain"}

    with mock.patch(
        "skycache.skybrary.corpus_import.fetch_open_url",
        side_effect=fake_fetch,
    ):
        report = import_open_url(
            url,
            tmp_path / "open-out",
            license_name="project gutenberg",
            title="Mock PG work",
            work_id="open-pg-mock-001",
        )
    assert report["ok"]
    pkg = Path(report["package"])
    assert (pkg / "work.txt").is_file()
    assert "fox jumped" in (pkg / "work.txt").read_text(encoding="utf-8")
    man = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert man["id"] == "open-pg-mock-001"
    assert "gutenberg" in man["license"]
    assert man["source"]["extra"]["provenance"]["url"] == url


def test_import_open_url_blocks_bad_host():
    with pytest.raises(ValueError):
        import_open_url(
            "https://evil-pirate-books.example/dump.epub",
            Path("/tmp/nope"),
            license_name="public domain",
        )


def test_import_open_url_requires_license(tmp_path: Path):
    with pytest.raises(ValueError):
        assert_license_allowed("")
    with pytest.raises(ValueError):
        import_open_url(
            "https://www.gutenberg.org/files/1/1-0.txt",
            tmp_path / "x",
            license_name="unknown",
        )


def test_build_work_package_roundtrip(tmp_path: Path):
    p = build_work_package(
        tmp_path / "pkg",
        work_id="corpus-demo-1",
        title="Demo",
        body="Hello skybrary corpus.",
        license_name="CC-BY-4.0",
        subjects=["test"],
    )
    man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
    assert man["kind"] == "skybrary_text"
    assert man["source"]["extra"]["work"]["work_id"] == "corpus-demo-1"
