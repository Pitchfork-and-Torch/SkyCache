"""First-boot wizard helpers - golden path for a demo village node.

Pure functions so install scripts and pytest can drive the same path without a TTY.
Legal rails stay fail-closed (validate_legal_rf_mode); default PIN must be changed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.capabilities.matrix import build_capability_matrix
from skycache.capabilities.modes import ALLOWED_MODES, LegalRfMode, validate_legal_rf_mode
from skycache.config import NEXUS_HONEST_BANNER, Settings, samples_dir
from skycache.db.catalog import Catalog
from skycache.ingest.drop_watch import DropWatcher
from skycache.ingest.normalizer import ContentManager

DEFAULT_PIN = "2468"
DEFAULT_SSID = "SkyCache-Local"
DEFAULT_LEGAL_RF_MODE = LegalRfMode.RECEIVE_ONLY.value  # safest first-boot default
STATE_FILENAME = "first_boot.json"
ENV_FILENAME = "skycache.env"

# Operator-facing mode blurbs (honest, short)
MODE_HELP: dict[str, str] = {
    LegalRfMode.RECEIVE_ONLY.value: (
        "Safest default: local portal + USB/drop only; optional SDR receive later. "
        "No mesh TX."
    ),
    LegalRfMode.ISM_MESH.value: (
        "Unlicensed Wi-Fi/ISM mesh TX allowed after you check local spectrum rules. "
        "Still receive-only for satellite."
    ),
    LegalRfMode.ISM_LORA_CONTROL.value: (
        "ISM mesh + low-bandwidth LoRa/ISM control plane. Operator must follow "
        "regional ISM limits."
    ),
    LegalRfMode.HYBRID_GATEWAY.value: (
        "Mesh + opportunistic legal uplink as a normal client (fair-share pulls). "
        "Not free commercial broadband."
    ),
    LegalRfMode.AMATEUR_OPERATOR.value: (
        "Requires a valid national amateur license AND explicit affirmation. "
        "Software still never enables commercial decrypt or default sat uplink."
    ),
}

_PIN_RE = re.compile(r"^\d{4,8}$")
_SSID_RE = re.compile(r"^[\w .:\-]{1,32}$", re.UNICODE)


@dataclass
class FirstBootConfig:
    """Operator choices collected by the wizard."""

    admin_pin: str = DEFAULT_PIN
    hotspot_ssid: str = DEFAULT_SSID
    legal_rf_mode: str = DEFAULT_LEGAL_RF_MODE
    amateur_license_affirmed: bool = False
    load_samples: bool = True
    load_skybrary: bool = True
    node_id: str = ""
    language_hint: str = "en"


@dataclass
class FirstBootResult:
    """Outcome of applying first-boot settings."""

    ok: bool
    data_dir: str
    env_path: str
    state_path: str
    packages_loaded: int = 0
    skybrary_works: int = 0
    legal_rf_mode: str = DEFAULT_LEGAL_RF_MODE
    hotspot_ssid: str = DEFAULT_SSID
    pin_changed: bool = False
    capabilities_summary: dict[str, Any] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def state_path(data_dir: Path) -> Path:
    return Path(data_dir) / STATE_FILENAME


def default_env_path(data_dir: Path) -> Path:
    return Path(data_dir) / ENV_FILENAME


def is_first_boot_done(data_dir: Path) -> bool:
    p = state_path(data_dir)
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(data.get("completed"))


def read_first_boot_state(data_dir: Path) -> dict[str, Any] | None:
    p = state_path(data_dir)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def validate_pin(pin: str, *, allow_default: bool = False) -> str:
    """Return cleaned PIN or raise ValueError."""
    cleaned = (pin or "").strip()
    if not _PIN_RE.match(cleaned):
        raise ValueError("Admin PIN must be 4 - 8 digits.")
    if cleaned == DEFAULT_PIN and not allow_default:
        raise ValueError(
            f"Refusing default PIN {DEFAULT_PIN}. Choose a new 4 - 8 digit PIN for this node."
        )
    return cleaned


def validate_ssid(ssid: str) -> str:
    cleaned = (ssid or "").strip()
    if not cleaned:
        raise ValueError("SSID cannot be empty.")
    if len(cleaned) > 32:
        raise ValueError("SSID must be 32 characters or fewer.")
    if not _SSID_RE.match(cleaned):
        raise ValueError(
            "SSID may only contain letters, numbers, spaces, . : - and underscore."
        )
    return cleaned


def validate_first_boot_config(cfg: FirstBootConfig) -> FirstBootConfig:
    """Validate and normalize config; raises ValueError on bad input."""
    pin = validate_pin(cfg.admin_pin, allow_default=False)
    ssid = validate_ssid(cfg.hotspot_ssid)
    mode = validate_legal_rf_mode(
        cfg.legal_rf_mode,
        amateur_license_affirmed=cfg.amateur_license_affirmed,
    )
    lang = (cfg.language_hint or "en").strip().lower()[:8] or "en"
    return FirstBootConfig(
        admin_pin=pin,
        hotspot_ssid=ssid,
        legal_rf_mode=mode.value,
        amateur_license_affirmed=bool(cfg.amateur_license_affirmed)
        and mode == LegalRfMode.AMATEUR_OPERATOR,
        load_samples=bool(cfg.load_samples),
        load_skybrary=bool(cfg.load_skybrary),
        node_id=(cfg.node_id or "").strip(),
        language_hint=lang,
    )


def render_env_file(
    cfg: FirstBootConfig,
    *,
    data_dir: Path,
    extra: dict[str, str] | None = None,
) -> str:
    """Render shell-style env file consumed by systemd EnvironmentFile=."""
    lines = [
        "# SkyCache first-boot env - generated by skycache first-boot",
        f"# {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "# LEGAL: receive-only satellite; no commercial decrypt; not free Starlink.",
        f"SKYCACHE_DATA_DIR={Path(data_dir).resolve()}",
        f"SKYCACHE_ADMIN_PIN={cfg.admin_pin}",
        f"SKYCACHE_HOTSPOT_SSID={cfg.hotspot_ssid}",
        f"SKYCACHE_LEGAL_RF_MODE={cfg.legal_rf_mode}",
        f"SKYCACHE_AMATEUR_LICENSE_AFFIRMED={'true' if cfg.amateur_license_affirmed else 'false'}",
    ]
    if cfg.node_id:
        lines.append(f"SKYCACHE_NODE_ID={cfg.node_id}")
    if cfg.language_hint:
        # Preferred languages is a list in Settings; single hint is enough for operators
        lines.append(f"SKYCACHE_LANGUAGE_HINT={cfg.language_hint}")
    if extra:
        for k, v in sorted(extra.items()):
            if not re.match(r"^[A-Z][A-Z0-9_]*$", k):
                continue
            lines.append(f"{k}={v}")
    lines.append("")
    return "\n".join(lines)


def write_env_file(path: Path, cfg: FirstBootConfig, *, data_dir: Path, extra: dict[str, str] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_env_file(cfg, data_dir=data_dir, extra=extra), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass  # Windows / non-posix FS
    return path


def write_state(data_dir: Path, cfg: FirstBootConfig, result: FirstBootResult) -> Path:
    p = state_path(data_dir)
    payload = {
        "completed": result.ok,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "legal_rf_mode": cfg.legal_rf_mode,
        "hotspot_ssid": cfg.hotspot_ssid,
        "pin_changed": result.pin_changed,
        "packages_loaded": result.packages_loaded,
        "skybrary_works": result.skybrary_works,
        "language_hint": cfg.language_hint,
        "banner": NEXUS_HONEST_BANNER,
        "version": "first_boot_v1",
    }
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p


def capabilities_summary_dict(
    *,
    legal_rf_mode: str,
    sim_mode: bool = True,
    amateur_license_affirmed: bool = False,
    skybrary_works: int = 0,
) -> dict[str, Any]:
    matrix = build_capability_matrix(
        legal_rf_mode=legal_rf_mode,
        sim_mode=sim_mode,
        amateur_license_affirmed=amateur_license_affirmed,
        nexus_enabled=True,
        skybrary_works=skybrary_works,
    )
    d = matrix.to_dict()
    enabled = [c for c in d["capabilities"] if c.get("enabled")]
    disabled = [c for c in d["capabilities"] if not c.get("enabled")]
    return {
        "legal_rf_mode": d["legal_rf_mode"],
        "banner": d["banner"],
        "honest_banner": NEXUS_HONEST_BANNER,
        "summary": d["summary"],
        "enabled_ids": [c["id"] for c in enabled],
        "disabled_ids": [c["id"] for c in disabled],
        "banned": d["banned"],
        "modes": sorted(ALLOWED_MODES),
        "mode_help": MODE_HELP.get(str(d["legal_rf_mode"]), ""),
    }


def format_capabilities_text(summary: dict[str, Any]) -> str:
    lines = [
        "=== SkyCache capabilities (legal rails) ===",
        summary.get("honest_banner") or NEXUS_HONEST_BANNER,
        f"legal_rf_mode={summary.get('legal_rf_mode')}",
    ]
    help_txt = summary.get("mode_help") or ""
    if help_txt:
        lines.append(f"  {help_txt}")
    s = summary.get("summary") or {}
    lines.append(f"Enabled {s.get('enabled', 0)} / {s.get('total', 0)} capabilities")
    for cid in summary.get("enabled_ids") or []:
        lines.append(f"  [ON ] {cid}")
    for cid in summary.get("disabled_ids") or []:
        lines.append(f"  [off] {cid}")
    lines.append("BANNED (never):")
    for b in summary.get("banned") or []:
        lines.append(f"  - {b}")
    lines.append("Docs: docs/legal-pathways-rf-and-content.md  |  docs/first-boot.md")
    return "\n".join(lines)


def apply_first_boot(
    data_dir: Path,
    cfg: FirstBootConfig,
    *,
    env_path: Path | None = None,
    force: bool = False,
    sim_mode: bool = True,
    samples_root: Path | None = None,
) -> FirstBootResult:
    """Initialize node: env file, sample packages, Skybrary PD samples, state marker.

    Does not start systemd or hostapd - shell wizard / install scripts own that.
    """
    data_dir = Path(data_dir)
    messages: list[str] = []
    errors: list[str] = []

    if is_first_boot_done(data_dir) and not force:
        return FirstBootResult(
            ok=False,
            data_dir=str(data_dir),
            env_path=str(env_path or default_env_path(data_dir)),
            state_path=str(state_path(data_dir)),
            errors=[
                "First-boot already completed. Re-run with force=True / --force to redo."
            ],
        )

    try:
        cfg = validate_first_boot_config(cfg)
    except ValueError as exc:
        return FirstBootResult(
            ok=False,
            data_dir=str(data_dir),
            env_path=str(env_path or default_env_path(data_dir)),
            state_path=str(state_path(data_dir)),
            errors=[str(exc)],
        )

    settings = Settings(
        data_dir=data_dir,
        admin_pin=cfg.admin_pin,
        hotspot_ssid=cfg.hotspot_ssid,
        legal_rf_mode=cfg.legal_rf_mode,
        amateur_license_affirmed=cfg.amateur_license_affirmed,
        sim_mode=sim_mode,
        node_id=cfg.node_id,
    )
    settings.ensure_dirs()
    DropWatcher(settings)

    packages_loaded = 0
    skybrary_works = 0

    if cfg.load_samples:
        catalog = Catalog(settings.db_path)
        content = ContentManager(settings, catalog)
        root = Path(samples_root) if samples_root else samples_dir()
        pkgs = content.load_samples(root)
        packages_loaded = len(pkgs)
        catalog.close()
        messages.append(f"Loaded {packages_loaded} sample packages from {root / 'packages'}")

    if cfg.load_skybrary:
        from skycache.skybrary.catalog import SkybraryCatalog
        from skycache.skybrary.ingest import bootstrap_samples_with_settings

        sky = SkybraryCatalog(settings.skybrary_db_path)
        ids = bootstrap_samples_with_settings(settings, sky)
        skybrary_works = len(ids)
        sky.close()
        messages.append(
            f"Skybrary: indexed {skybrary_works} public-domain sample works (not a full archive)"
        )

    env_out = write_env_file(
        env_path or default_env_path(data_dir),
        cfg,
        data_dir=data_dir,
    )
    messages.append(f"Wrote env file: {env_out} (mode 600 when supported)")

    cap = capabilities_summary_dict(
        legal_rf_mode=cfg.legal_rf_mode,
        sim_mode=sim_mode,
        amateur_license_affirmed=cfg.amateur_license_affirmed,
        skybrary_works=skybrary_works,
    )
    messages.append(format_capabilities_text(cap))

    result = FirstBootResult(
        ok=True,
        data_dir=str(data_dir.resolve()),
        env_path=str(env_out),
        state_path=str(state_path(data_dir)),
        packages_loaded=packages_loaded,
        skybrary_works=skybrary_works,
        legal_rf_mode=cfg.legal_rf_mode,
        hotspot_ssid=cfg.hotspot_ssid,
        pin_changed=cfg.admin_pin != DEFAULT_PIN,
        capabilities_summary=cap,
        messages=messages,
        errors=errors,
    )
    write_state(data_dir, cfg, result)
    result.state_path = str(state_path(data_dir))
    messages.append(f"First-boot state: {result.state_path}")
    return result


def interactive_prompts(
    *,
    defaults: FirstBootConfig | None = None,
    input_fn=input,
    print_fn=print,
) -> FirstBootConfig:
    """Collect config from a TTY. ``input_fn``/``print_fn`` injectable for tests."""
    base = defaults or FirstBootConfig()
    print_fn("")
    print_fn("SkyCache first-boot wizard")
    print_fn("=" * 40)
    print_fn(NEXUS_HONEST_BANNER)
    print_fn("")
    print_fn("Allowed legal_rf_mode values:")
    for m in sorted(ALLOWED_MODES):
        print_fn(f"  {m}")
        print_fn(f"      {MODE_HELP.get(m, '')}")
    print_fn("")

    pin = base.admin_pin
    while True:
        raw = input_fn(f"Admin PIN (4 - 8 digits, NOT {DEFAULT_PIN}) [{pin if pin != DEFAULT_PIN else 'required'}]: ").strip()
        candidate = raw or (pin if pin != DEFAULT_PIN else "")
        try:
            pin = validate_pin(candidate, allow_default=False)
            break
        except ValueError as exc:
            print_fn(f"  ! {exc}")

    ssid_default = base.hotspot_ssid or DEFAULT_SSID
    while True:
        raw = input_fn(f"Wi-Fi SSID hint for operators [{ssid_default}]: ").strip()
        try:
            ssid = validate_ssid(raw or ssid_default)
            break
        except ValueError as exc:
            print_fn(f"  ! {exc}")

    mode_default = base.legal_rf_mode or DEFAULT_LEGAL_RF_MODE
    amateur = base.amateur_license_affirmed
    while True:
        raw = input_fn(f"legal_rf_mode [{mode_default}]: ").strip().lower() or mode_default
        if raw == LegalRfMode.AMATEUR_OPERATOR.value:
            aff = input_fn("Affirm you hold a valid national amateur license? [y/N]: ").strip().lower()
            amateur = aff in ("y", "yes")
        else:
            amateur = False
        try:
            mode = validate_legal_rf_mode(raw, amateur_license_affirmed=amateur)
            break
        except ValueError as exc:
            print_fn(f"  ! {exc}")

    lang = input_fn(f"Preferred language hint (en/fr/es/ar/sw/hi/pt) [{base.language_hint}]: ").strip() or base.language_hint
    load_s = input_fn("Load demo sample packages? [Y/n]: ").strip().lower()
    load_sky = input_fn("Load Skybrary public-domain literacy samples? [Y/n]: ").strip().lower()

    return FirstBootConfig(
        admin_pin=pin,
        hotspot_ssid=ssid,
        legal_rf_mode=mode.value,
        amateur_license_affirmed=amateur,
        load_samples=load_s not in ("n", "no"),
        load_skybrary=load_sky not in ("n", "no"),
        node_id=base.node_id,
        language_hint=lang or "en",
    )
