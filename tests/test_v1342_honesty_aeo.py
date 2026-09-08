"""v1.34.2 Honesty / AEO: advertised version lockstep, no Mbps fiction."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from skycache import __version__
from skycache.aeo import (
    CURATED_WORK_COUNT,
    aeo_text_is_honest,
    honesty_claims,
    render_llms_txt,
    render_robots_txt,
    write_aeo_files,
)
from skycache.skybrary.sample_corpus import SAMPLES
from skycache.capabilities.modes import satellite_receive_only_ok
from skycache.config import Settings
from skycache.ops.library_ops import apply_staging_to_web_public, write_marketing_sitemap
from skycache.ops.rx_ops import rx_ops_doctor
from skycache.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]
THROUGHPUT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:[Mm]bps|[Mm]bit|[Gg]bit)")
DISH_MBPS_RE = re.compile(r"dish.{0,40}\d+(?:\.\d+)?\s*(?:[Mm]bps|[Mm]bit)", re.I)


def test_curated_work_count_matches_samples():
    assert CURATED_WORK_COUNT == len(SAMPLES)
    assert str(CURATED_WORK_COUNT) in render_llms_txt()


def test_version_is_1342_or_newer():
    parts = [int(x) for x in __version__.split(".")[:3]]
    assert parts >= [1, 34, 2]


def test_advertised_versions_match_package():
    init_txt = (ROOT / "skycache" / "__init__.py").read_text(encoding="utf-8")
    assert f'__version__ = "{__version__}"' in init_txt

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in pyproject

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.splitlines()[2].startswith(f"## {__version__}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"version-{__version__}" in readme
    assert f"**{__version__.rsplit('.', 1)[0]} Honesty" in readme or f"**{__version__}" in readme

    progress = (ROOT / "PROGRESS.md").read_text(encoding="utf-8")
    assert f"**Software version:** {__version__}" in progress

    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert f"- Latest: v{__version__}" in llms
    assert f"- Version: software {__version__}" in llms


def test_committed_aeo_matches_renderer():
    committed = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert committed == render_llms_txt()
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    assert robots == render_robots_txt()
    assert "llms.txt" in robots


def test_aeo_copy_has_no_invented_mbps():
    surfaces = [
        ROOT / "llms.txt",
        ROOT / "robots.txt",
        ROOT / "README.md",
        ROOT / "docs" / "AEO.md",
        ROOT / "PROGRESS.md",
    ]
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        ok, hits = aeo_text_is_honest(text)
        assert ok, f"{path}: forbidden throughput phrases {hits}"
        assert not THROUGHPUT_RE.search(text), f"{path}: numeric Mbps/Mbit claim"
        assert not DISH_MBPS_RE.search(text), f"{path}: dish Mbps claim"
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8").lower()
    assert "not free commercial satellite broadband" in llms
    assert "fail-closed" in llms
    assert "receive-only" in llms


def test_honesty_claims_and_rx_fail_closed_still_true():
    claims = honesty_claims()
    assert claims["receive_only"] is True
    assert claims["commercial_broadband"] is False
    assert claims["rx_legal_fail_closed"] is True
    assert claims["invented_mbps"] is False
    assert claims["dish_mbps"] is False
    ok, _ = satellite_receive_only_ok("starlink-tx")
    assert ok is False
    ok2, _ = satellite_receive_only_ok("receive_only")
    assert ok2 is True


def test_rx_ops_doctor_still_fail_closed_on_uplink(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    doc = rx_ops_doctor(data_dir=settings.data_dir, legal_rf_mode="satellite-uplink")
    legal = [c for c in doc["checks"] if c["id"] == "legal_receive_only"]
    assert legal and legal[0]["ok"] is False
    assert doc["go_rx_live"] is False


def test_portal_serves_llms_robots_and_health_honesty(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    client = TestClient(create_app(settings))

    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["version"] == __version__
    assert body["receive_only"] is True
    assert body["commercial_broadband"] is False
    assert body["rx_legal_fail_closed"] is True
    assert body["invented_mbps"] is False

    llms = client.get("/llms.txt")
    assert llms.status_code == 200
    assert "text/plain" in llms.headers.get("content-type", "")
    assert f"Latest: v{__version__}" in llms.text
    assert "NOT free commercial satellite broadband" in llms.text

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "llms.txt" in robots.text

    nexus = client.get("/api/nexus/status")
    assert nexus.status_code == 200
    assert __version__ in nexus.json().get("edition", "")


def test_apply_web_copies_llms_and_sitemap_lists_it(tmp_path: Path):
    staging = tmp_path / "staging" / "public"
    write_aeo_files(staging)
    (staging / "skybrary-catalog.json").write_text(
        '{"works":[]}\n', encoding="utf-8"
    )
    web_public = tmp_path / "skycache-web" / "public"
    web_public.mkdir(parents=True)
    rep = apply_staging_to_web_public(staging, web_public)
    assert rep["ok"] is True
    assert (web_public / "llms.txt").is_file()
    assert (web_public / "robots.txt").is_file()
    sm = (web_public / "sitemap.xml").read_text(encoding="utf-8")
    assert "/llms.txt" in sm
    write_marketing_sitemap(web_public)
    sm2 = (web_public / "sitemap.xml").read_text(encoding="utf-8")
    assert "/llms.txt" in sm2
