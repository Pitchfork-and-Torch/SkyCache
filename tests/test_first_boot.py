"""First-boot wizard pure helpers + CLI smoke (Wave 1.A1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.first_boot import (
    DEFAULT_PIN,
    FirstBootConfig,
    apply_first_boot,
    format_capabilities_text,
    interactive_prompts,
    is_first_boot_done,
    render_env_file,
    validate_first_boot_config,
    validate_pin,
    validate_ssid,
)
from skycache.web.app import create_app


def test_validate_pin_and_ssid():
    assert validate_pin("739184") == "739184"
    with pytest.raises(ValueError):
        validate_pin(DEFAULT_PIN)
    with pytest.raises(ValueError):
        validate_pin("12")  # too short
    with pytest.raises(ValueError):
        validate_pin("abcd")
    assert validate_pin(DEFAULT_PIN, allow_default=True) == DEFAULT_PIN
    assert validate_ssid("SkyCache-Village") == "SkyCache-Village"
    with pytest.raises(ValueError):
        validate_ssid("")
    with pytest.raises(ValueError):
        validate_ssid("x" * 40)


def test_validate_config_rejects_forbidden_mode():
    with pytest.raises(ValueError):
        validate_first_boot_config(
            FirstBootConfig(admin_pin="739184", legal_rf_mode="starlink-tx")
        )
    with pytest.raises(ValueError):
        validate_first_boot_config(
            FirstBootConfig(
                admin_pin="739184",
                legal_rf_mode="amateur_operator",
                amateur_license_affirmed=False,
            )
        )
    ok = validate_first_boot_config(
        FirstBootConfig(
            admin_pin="739184",
            legal_rf_mode="amateur_operator",
            amateur_license_affirmed=True,
        )
    )
    assert ok.legal_rf_mode == "amateur_operator"


def test_render_env_and_apply(tmp_path: Path):
    data = tmp_path / "data"
    cfg = FirstBootConfig(
        admin_pin="918273",
        hotspot_ssid="SkyCache-Test",
        legal_rf_mode="receive_only",
        load_samples=True,
        load_skybrary=True,
        language_hint="en",
    )
    text = render_env_file(cfg, data_dir=data)
    assert "SKYCACHE_ADMIN_PIN=918273" in text
    assert "SKYCACHE_HOTSPOT_SSID=SkyCache-Test" in text
    assert "SKYCACHE_LEGAL_RF_MODE=receive_only" in text
    assert "commercial" in text.lower() or "Starlink" in text or "LEGAL" in text

    result = apply_first_boot(data, cfg, force=False, sim_mode=True)
    assert result.ok is True
    assert result.pin_changed is True
    assert result.packages_loaded >= 1
    assert result.skybrary_works >= 1
    assert is_first_boot_done(data)
    env = Path(result.env_path)
    assert env.is_file()
    assert "918273" in env.read_text(encoding="utf-8")
    state = json.loads((data / "first_boot.json").read_text(encoding="utf-8"))
    assert state["completed"] is True
    assert state["legal_rf_mode"] == "receive_only"
    assert "enabled_ids" in result.capabilities_summary
    text_cap = format_capabilities_text(result.capabilities_summary)
    assert "legal_rf_mode=receive_only" in text_cap
    assert "BANNED" in text_cap

    # Second run without force fails closed
    again = apply_first_boot(data, cfg, force=False, sim_mode=True)
    assert again.ok is False

    # Force redo
    cfg2 = FirstBootConfig(
        admin_pin="555666",
        hotspot_ssid="SkyCache-Test2",
        legal_rf_mode="ism_mesh",
        load_samples=False,
        load_skybrary=False,
    )
    redone = apply_first_boot(data, cfg2, force=True, sim_mode=True)
    assert redone.ok is True
    assert redone.legal_rf_mode == "ism_mesh"


def test_interactive_prompts_injectable():
    answers = iter(
        [
            "445566",  # pin
            "MyHub",  # ssid
            "receive_only",  # mode
            "fr",  # lang
            "Y",  # samples
            "n",  # skybrary
        ]
    )
    out: list[str] = []
    cfg = interactive_prompts(input_fn=lambda _p: next(answers), print_fn=out.append)
    assert cfg.admin_pin == "445566"
    assert cfg.hotspot_ssid == "MyHub"
    assert cfg.legal_rf_mode == "receive_only"
    assert cfg.language_hint == "fr"
    assert cfg.load_samples is True
    assert cfg.load_skybrary is False


def test_onboarding_api_includes_capabilities(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        legal_rf_mode="receive_only",
        hotspot_ssid="Hub-SSID",
    )
    settings.ensure_dirs()
    client = TestClient(create_app(settings))
    r = client.get("/api/onboarding")
    assert r.status_code == 200
    body = r.json()
    ids = [s["id"] for s in body["steps"]]
    assert "legal" in ids
    assert "capabilities" in ids
    assert "library" in ids
    assert body["hotspot_ssid"] == "Hub-SSID"
    assert body["legal_rf_mode"] == "receive_only"
    assert "capabilities_summary" in body
    assert body["capabilities_summary"]["total"] >= 1
