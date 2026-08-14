"""Runtime configuration for SkyCache."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Blocked plugin/source keywords - commercial encrypted services are out of scope.
FORBIDDEN_SOURCE_KEYWORDS: frozenset[str] = frozenset(
    {
        "starlink",
        "oneweb",
        "commercial-vsat",
        "decrypt-commercial",
        "piracy-stream",
        "iridium-commercial-voice",
        "satellite-uplink",
        "vsat-tx",
        "ku-band-tx",
        "ka-band-tx",
        "paid-constellation",
        "decrypt-drm",
        "card-sharing",
    }
)

NEXUS_HONEST_BANNER = (
    "SkyCache Nexus: store-and-forward knowledge + community mesh on unlicensed "
    "Wi-Fi/ISM. Receive-only for satellite. Not free commercial broadband or Starlink."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SKYCACHE_",
        env_file=".env",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("data"))
    host: str = "0.0.0.0"
    port: int = 8080
    sim_mode: bool = False
    admin_pin: str = "2468"
    hotspot_ssid: str = "SkyCache-Local"
    preferred_languages: list[str] = Field(
        default_factory=lambda: ["en", "fr", "es", "ar", "sw", "hi", "pt"]
    )
    # Keep at least this many free bytes on the content volume.
    disk_reserve_bytes: int = 500 * 1024 * 1024
    # Soft max content store (0 = unlimited aside from reserve).
    max_content_bytes: int = 0
    power_provider: str = "mock"  # mock | sysfs | ina219
    mock_battery_percent: float = 85.0
    log_level: str = "INFO"
    # Nexus fabric
    node_id: str = ""
    nexus_enabled: bool = True
    mesh_mode: str = "sim"  # sim | batman | hybrid
    mesh_band: str = "sim"  # sim | wifi_2g | wifi_5g | wifi_6g | lora_ism
    gateway_daily_quota_mb: int = 500
    disaster_mode: bool = False
    # Legal capability mode (see docs/legal-pathways-rf-and-content.md)
    legal_rf_mode: str = "ism_mesh"  # receive_only | ism_mesh | ism_lora_control | hybrid_gateway | amateur_operator
    amateur_license_affirmed: bool = False
    open_fetch_hosts_file: str = ""  # optional JSON allowlist extension

    @property
    def content_dir(self) -> Path:
        return self.data_dir / "content"

    @property
    def work_dir(self) -> Path:
        return self.data_dir / "work"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "skycache.db"

    @property
    def nexus_dir(self) -> Path:
        return self.data_dir / "nexus"

    @property
    def skybrary_db_path(self) -> Path:
        return self.data_dir / "skybrary.db"

    @property
    def handoff_dir(self) -> Path:
        """Phone/USB handoff mule export directory (file bridge, not live BLE)."""
        return self.data_dir / "handoff"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.nexus_dir.mkdir(parents=True, exist_ok=True)
        self.handoff_dir.mkdir(parents=True, exist_ok=True)

    def validate_source_name(self, name: str) -> None:
        lowered = name.lower()
        for bad in FORBIDDEN_SOURCE_KEYWORDS:
            if bad in lowered:
                raise ValueError(
                    f"Refusing source/plugin '{name}': matches forbidden keyword "
                    f"'{bad}'. SkyCache only processes unencrypted free-to-air "
                    "or openly licensed content. Nexus never enables commercial "
                    "decrypt or satellite uplink."
                )

    def validate_nexus(self) -> None:
        from skycache.capabilities.modes import validate_legal_rf_mode
        from skycache.nexus.spectrum import validate_band, validate_mesh_mode

        validate_mesh_mode(self.mesh_mode)
        validate_band(self.mesh_band)
        validate_legal_rf_mode(
            self.legal_rf_mode,
            amateur_license_affirmed=self.amateur_license_affirmed,
        )


def default_settings(**overrides: object) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def package_root() -> Path:
    """Repository root (parent of the skycache package)."""
    return Path(__file__).resolve().parent.parent


def samples_dir() -> Path:
    return package_root() / "samples"


def webui_dir() -> Path:
    return package_root() / "webui"
