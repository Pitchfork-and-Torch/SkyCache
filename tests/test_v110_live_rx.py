"""v1.1.0 Live FTA RX ops - real-world product watch, station, field log, passes."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.rx.capture import capture_to_catalog
from skycache.rx.doctor import rx_doctor_report
from skycache.rx.field_log import append_field_log, list_field_log
from skycache.rx.pass_plan import import_tle_text, predict_passes
from skycache.rx.product_watch import discover_products, ingest_product, watch_once
from skycache.rx.recipes import get_recipe, list_recipes
from skycache.rx.station import load_station, save_station
from skycache.web.app import create_app


def _write_tiny_png(path: Path) -> None:
    """Write a minimal valid 1x1 PNG without Pillow."""
    path.parent.mkdir(parents=True, exist_ok=True)
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
        b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(png)


def test_recipes_include_fta_weather():
    ids = {r["id"] for r in list_recipes()}
    assert "noaa_apt" in ids
    assert "product_import" in ids
    r = get_recipe("NOAA_APT")
    assert r is not None
    assert r["legal"] == "fta_public"


def test_station_and_passes_fixture(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "rx", sim_mode=True)
    settings.ensure_dirs()
    st = save_station(settings.data_dir, lat=40.7, lon=-74.0, alt_m=10.0, name="lab")
    assert load_station(settings.data_dir)["lat"] == 40.7
    rep = predict_passes(
        lat=st["lat"], lon=st["lon"], hours=24, data_dir=settings.data_dir
    )
    assert rep["schema"] == "skycache.rx.passes.v1"
    assert rep["count"] >= 1
    assert rep["engine"] in ("fixture", "sgp4")


def test_tle_import(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "tle", sim_mode=True)
    settings.ensure_dirs()
    text = "\n".join(
        [
            "NOAA 18",
            "1 28654U 05018A   24101.51234567  .00000000  00000-0  00000-0 0  9991",
            "2 28654  99.0000 130.0000 0012000 100.0000 260.0000 14.12000000123457",
        ]
    )
    rep = import_tle_text(settings.data_dir, text)
    assert rep["ok"] is True
    assert rep["count"] == 1


def test_product_watch_ingests_image(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "node", sim_mode=True)
    settings.ensure_dirs()
    products = tmp_path / "satdump_out"
    img = products / "pass1" / "channel_a.png"
    _write_tiny_png(img)
    # discover
    found = discover_products(products)
    assert any(p.suffix.lower() == ".png" for p in found if p.is_file() or True)
    rep = watch_once(products, settings, recipe="product_import", satellite="NOAA 18")
    assert rep["new"] >= 1
    assert any(r.get("ok") for r in rep["results"])
    # second scan: no duplicates
    rep2 = watch_once(products, settings)
    assert rep2["new"] == 0


def test_ingest_product_direct(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "n2", sim_mode=True)
    settings.ensure_dirs()
    img = tmp_path / "wx.png"
    _write_tiny_png(img)
    rep = ingest_product(img, settings, recipe="product_import", satellite="NOAA 15")
    assert rep["ok"] is True
    assert rep.get("package_id")


def test_field_log(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "log", sim_mode=True)
    settings.ensure_dirs()
    e = append_field_log(
        settings.data_dir,
        satellite="NOAA 18",
        elevation_deg=41.5,
        quality="good",
        recipe="noaa_apt",
        notes="V-dipole clear south",
    )
    assert e["satellite"] == "NOAA 18"
    rows = list_field_log(settings.data_dir)
    assert len(rows) == 1


def test_capture_image_recipe(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "cap", sim_mode=True)
    settings.ensure_dirs()
    img = tmp_path / "apt.png"
    _write_tiny_png(img)
    rep = capture_to_catalog(
        settings, recipe_id="product_import", input_path=str(img)
    )
    assert rep["ok"] is True


def test_rx_doctor_and_api(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "web", sim_mode=True, mesh_mode="sim", mesh_band="sim"
    )
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=51.5, lon=-0.12, name="london-lab")
    doc = rx_doctor_report(data_dir=settings.data_dir)
    assert doc["ready"]["product_import"] is True
    assert "tools" in doc

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/rx/status")
    assert r.status_code == 200
    assert r.json()["schema"] == "skycache.rx.doctor.v1"
    r2 = client.get("/api/rx/recipes")
    assert r2.status_code == 200
    assert len(r2.json()) >= 3
    r3 = client.get("/api/rx/passes")
    assert r3.status_code == 200
    assert r3.json()["count"] >= 1

    img = tmp_path / "live.png"
    _write_tiny_png(img)
    r4 = client.post("/api/rx/import", json={"path": str(img), "satellite": "NOAA 19"})
    assert r4.status_code == 200
    assert r4.json().get("ok") is True


def test_cli_rx_import(tmp_path: Path):
    from skycache.__main__ import build_parser

    settings_dir = tmp_path / "cli"
    img = tmp_path / "cli.png"
    _write_tiny_png(img)
    parser = build_parser()
    args = parser.parse_args(
        [
            "rx",
            "import",
            str(img),
            "--data-dir",
            str(settings_dir),
            "--sim",
            "--satellite",
            "NOAA 18",
        ]
    )
    assert args.func(args) == 0
