"""v1.2.0 Pass Autopilot: schedule, arm, satdump cmd, auto field-log, APIs."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.rx.field_log import list_field_log
from skycache.rx.product_watch import watch_once
from skycache.rx.schedule import (
    build_schedule,
    clear_arm,
    duty_status,
    load_arm,
    maybe_auto_field_log,
    recipe_for_satellite,
    satdump_command,
    save_arm,
)
from skycache.rx.station import save_station
from skycache.web.app import create_app


def _write_tiny_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
        b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(png)


def test_recipe_for_satellite_binding():
    assert recipe_for_satellite("NOAA 18") == "noaa_apt"
    assert recipe_for_satellite("METEOR-M2 3") == "meteor_lrpt"
    assert recipe_for_satellite("GOES-16") == "goes_hrit"
    assert recipe_for_satellite("mystery bird") == "product_import"


def test_satdump_command_pipeline_and_import():
    cmd = satdump_command(recipe_id="noaa_apt", products_dir="/tmp/prod")
    assert cmd["mode"] == "pipeline"
    assert cmd["pipeline"] == "noaa_apt"
    assert "noaa_apt" in (cmd.get("command_iq") or "")
    imp = satdump_command(recipe_id="product_import", products_dir="/tmp/prod")
    assert imp["mode"] == "product_import"
    assert imp["command"] is None
    assert "watch" in (imp.get("guidance") or "")


def test_schedule_and_arm(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "node", sim_mode=True)
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=40.7, lon=-74.0, alt_m=10.0, name="lab")
    sched = build_schedule(settings.data_dir, hours=24.0, min_elevation=10.0)
    assert sched["ok"] is True
    assert sched["schema"] == "skycache.rx.schedule.v1"
    assert sched["count"] >= 1
    slot = sched["slots"][0]
    assert "recipe_id" in slot
    assert "satdump" in slot
    assert "operator_steps" in slot

    arm = save_arm(settings.data_dir, hours=12.0, products_dir=tmp_path / "products")
    assert arm["armed"] is True
    assert load_arm(settings.data_dir) is not None
    duty = duty_status(settings.data_dir)
    assert duty["armed"] is True
    assert duty["schema"] == "skycache.rx.duty.v1"
    assert clear_arm(settings.data_dir)["armed"] is False
    assert load_arm(settings.data_dir) is None


def test_watch_auto_field_log_when_armed(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "node2", sim_mode=True)
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=40.7, lon=-74.0, alt_m=10.0, name="lab")
    products = tmp_path / "satdump_out"
    img = products / "pass1" / "channel_a.png"
    _write_tiny_png(img)

    save_arm(
        settings.data_dir,
        hours=24.0,
        products_dir=products,
        auto_field_log=True,
    )
    rep = watch_once(
        products,
        settings,
        recipe="product_import",
        satellite="NOAA 18",
    )
    assert rep["new"] >= 1
    ok_rows = [r for r in rep["results"] if r.get("ok")]
    assert ok_rows
    # auto field log should fire for armed station
    assert any(r.get("field_log_auto") for r in ok_rows) or list_field_log(
        settings.data_dir, limit=10
    )
    logs = list_field_log(settings.data_dir, limit=20)
    assert any(e.get("operator") == "autopilot" for e in logs)


def test_maybe_auto_field_log_respects_disarm(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "node3", sim_mode=True)
    settings.ensure_dirs()
    assert maybe_auto_field_log(settings.data_dir, package_id="x", satellite="NOAA 18") is None


def test_api_schedule_duty_arm(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "api", sim_mode=True)
    settings.ensure_dirs()
    save_station(settings.data_dir, lat=41.0, lon=-73.0, alt_m=5.0, name="api-lab")
    app = create_app(settings)
    client = TestClient(app)

    r = client.get("/api/rx/schedule", params={"hours": 12, "min_elev": 10})
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("count", 0) >= 1

    r2 = client.post(
        "/api/rx/arm",
        json={"hours": 12, "min_elev": 10, "auto_field_log": True},
    )
    assert r2.status_code == 200
    assert r2.json().get("armed") is True

    r3 = client.get("/api/rx/duty")
    assert r3.status_code == 200
    assert r3.json().get("armed") is True

    r4 = client.get("/api/rx/arm")
    assert r4.status_code == 200
    assert r4.json().get("armed") is True

    r5 = client.post("/api/rx/arm", json={"disarm": True})
    assert r5.status_code == 200
    assert r5.json().get("armed") is False
