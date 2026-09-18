"""v1.19.0 Corpus Ops product surface: export, kit, API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.skybrary.corpus_ops import (
    corpus_doctor,
    export_corpus_html,
    write_corpus_kit,
)
from skycache.web.app import create_app


def test_corpus_export_and_kit(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()

    doc = corpus_doctor(data_dir=settings.data_dir)
    assert doc["go_offline_batch"] is True

    exp = export_corpus_html(tmp_path / "board.html", data_dir=settings.data_dir)
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "corpus" in html
    assert "legal" in html or "public" in html or "pirate" in html

    kit = write_corpus_kit(tmp_path / "corpus-kit", data_dir=settings.data_dir)
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (tmp_path / "corpus-kit" / "corpus-batch-demo.json").is_file()


def test_corpus_api(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/corpus/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_offline_batch") is True
    assert "passport_complete_pct" in body or "content_packages" in body
