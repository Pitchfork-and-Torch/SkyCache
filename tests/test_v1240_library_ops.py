"""v1.24.0 Library Ops: doctor, status, export, kit, API + multilingual samples."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.ops.library_ops import (
    export_library_html,
    library_doctor,
    library_status,
    write_library_kit,
)
from skycache.skybrary.sample_corpus import SAMPLES
from skycache.web.app import create_app


def _seed(tmp: Path) -> Settings:
    settings = Settings(data_dir=tmp / "data", sim_mode=True)
    settings.ensure_dirs()
    return settings


def test_multilingual_samples_expand():
    assert len(SAMPLES) >= 75
    langs = set()
    for s in SAMPLES:
        for lang in s.get("languages") or ["en"]:
            langs.add(str(lang).lower())
    # English plus multilingual waves
    assert "en" in langs
    assert len(langs) >= 8
    for need in ("sw", "hi", "ar", "fr", "es"):
        assert need in langs
    non_en = [
        s
        for s in SAMPLES
        if any(str(x).lower() != "en" for x in (s.get("languages") or ["en"]))
    ]
    assert len(non_en) >= 12
    # STEM / civics wave (v1.33)
    stem_ids = {s["work_id"] for s in SAMPLES if "stem" in (s.get("subjects") or []) or "civics" in (s.get("subjects") or [])}
    assert len(stem_ids) >= 5


def test_library_doctor_export(tmp_path: Path):
    settings = _seed(tmp_path)
    doc = library_doctor(data_dir=settings.data_dir)
    assert doc["schema"] == "skycache.library.doctor.v1"
    assert doc["go_sim_library"] is True
    assert int(doc.get("work_count") or 0) >= 55

    st = library_status(data_dir=settings.data_dir)
    assert st["schema"] == "skycache.library.status.v1"
    assert isinstance(st.get("language_stats"), dict)
    assert isinstance(st.get("sample_works_preview"), list)

    exp = export_library_html(
        tmp_path / "board.html",
        data_dir=settings.data_dir,
    )
    assert exp["ok"] is True
    html = Path(exp["path"]).read_text(encoding="utf-8").lower()
    assert "library" in html
    assert "broadband" in html or "starlink" in html


def test_library_kit_and_api(tmp_path: Path):
    settings = _seed(tmp_path)
    kit = write_library_kit(
        tmp_path / "library-kit",
        data_dir=settings.data_dir,
    )
    assert kit["ok"] is True
    assert Path(kit["zip"]).is_file()
    assert (tmp_path / "library-kit" / "library-board.html").is_file()
    assert (tmp_path / "library-kit" / "HOSTING.json").is_file()

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/library/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("doctor", {}).get("go_sim_library") is True
    assert body.get("go_sim_library") is True
    assert int(body.get("work_count") or 0) >= 55


def test_library_publish(tmp_path: Path):
    from skycache.ops.library_ops import publish_library_catalog

    out = tmp_path / "publish"
    rep = publish_library_catalog(
        out,
        rebuild_samples=True,
        samples_out=tmp_path / "samples",
    )
    assert rep["ok"] is True
    assert int(rep.get("work_count") or 0) >= 55
    cat = out / "skybrary-catalog.json"
    assert cat.is_file()
    data = json.loads(cat.read_text(encoding="utf-8"))
    assert data["work_count"] == len(data["works"])
    assert data["work_count"] >= 55
    assert (tmp_path / "samples").is_dir()


def test_library_zero_network_parity(tmp_path: Path):
    from skycache.ops.library_ops import write_library_zero_network
    from skycache.skybrary.sample_corpus import SAMPLES

    out = tmp_path / "zn-kit"
    rep = write_library_zero_network(out, zip_bundle=True)
    assert rep["ok"] is True
    assert rep["parity"] is True
    assert int(rep["work_count"]) == len(SAMPLES)
    assert (out / "READ-OFFLINE.html").is_file()
    assert (out / "kit-manifest.json").is_file()
    texts = list((out / "texts").glob("*.txt"))
    assert len(texts) == len(SAMPLES)
    assert Path(rep["zip"]).is_file()


def test_library_sync_staging(tmp_path: Path):
    from skycache.ops.library_ops import library_sync
    from skycache.skybrary.pack_profile import get_profile

    # Skip heavy zero-network rebuild in unit test; still stage catalog + ops kit
    staging = tmp_path / "sync"
    rep = library_sync(
        staging,
        rebuild_zero_network=False,
        rebuild_ops_kit=True,
        repo_root=None,
    )
    assert rep["ok"] is True
    assert int(rep.get("work_count") or 0) >= 55
    assert (staging / "public" / "skybrary-catalog.json").is_file()
    assert (staging / "COPY-TO-SKYCACHE-WEB.md").is_file()
    assert (staging / "public" / "downloads" / "skycache-library-kit.zip").is_file()

    # apply-web into a fake marketing public tree
    web_public = tmp_path / "skycache-web" / "public"
    web_public.mkdir(parents=True)
    rep2 = library_sync(
        tmp_path / "sync2",
        rebuild_zero_network=False,
        rebuild_ops_kit=False,
        apply_web=web_public,
        repo_root=None,
    )
    assert rep2["ok"] is True
    assert (web_public / "skybrary-catalog.json").is_file()
    assert (web_public / "sitemap.xml").is_file()
    sm = (web_public / "sitemap.xml").read_text(encoding="utf-8")
    assert "library/works/" in sm
    assert get_profile("multilingual-literacy")["id"] == "multilingual-literacy"


def test_library_pack_kits(tmp_path: Path):
    from skycache.ops.library_ops import write_library_pack_kits
    from skycache.skybrary.sample_corpus import build_sample_packages

    samples = tmp_path / "samples"
    build_sample_packages(samples)
    out = tmp_path / "packs"
    rep = write_library_pack_kits(
        out,
        profiles=["multilingual-literacy", "emergency-health"],
        content_dir=samples,
        zip_bundle=True,
    )
    assert rep["ok"] is True
    assert len(rep.get("profiles") or []) == 2
    for row in rep["profiles"]:
        assert row.get("ok") is True
        assert int(row.get("count") or 0) >= 1
        assert Path(row["zip"]).is_file()


def test_library_status_downloads_map(tmp_path: Path):
    from skycache.config import Settings
    from skycache.ops.library_ops import library_status

    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    st = library_status(data_dir=settings.data_dir)
    assert "pack_profiles" in st
    assert "multilingual-literacy" in (st.get("pack_profiles") or [])
    assert "emergency-health" in (st.get("default_pack_kits") or [])
    assert "emergency_health" in (st.get("downloads") or {})


def test_health_corpus_wave():
    health = [
        s
        for s in SAMPLES
        if set(s.get("subjects") or [])
        & {"health_edu", "medicine", "emergency", "safety", "water"}
    ]
    assert len(health) >= 12
    assert any(s["work_id"].startswith("skybrary-pd-handwash") for s in health)
    assert any(s["work_id"].startswith("skybrary-pd-ors") for s in health)
