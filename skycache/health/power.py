"""Power monitoring and graceful degradation modes."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from skycache.models import PowerMode

log = logging.getLogger("skycache.power")


class PowerProvider(ABC):
    @abstractmethod
    def battery_percent(self) -> float | None:
        """Return 0-100 SOC or None if unknown."""

    @abstractmethod
    def is_on_ac(self) -> bool | None:
        """True if AC/solar charging known; None if unknown."""


class MockPowerProvider(PowerProvider):
    def __init__(self, percent: float = 85.0, on_ac: bool = True) -> None:
        self.percent = percent
        self.on_ac = on_ac

    def battery_percent(self) -> float | None:
        return self.percent

    def is_on_ac(self) -> bool | None:
        return self.on_ac


class SysfsBatteryProvider(PowerProvider):
    """Read Linux power_supply sysfs when available (laptops / some SBCs)."""

    def __init__(self, root: Path = Path("/sys/class/power_supply")) -> None:
        self.root = root

    def _find(self, suffix: str) -> Path | None:
        if not self.root.is_dir():
            return None
        for p in self.root.iterdir():
            cand = p / suffix
            if cand.is_file():
                return cand
        return None

    def battery_percent(self) -> float | None:
        cap = self._find("capacity")
        if not cap:
            return None
        try:
            return float(cap.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def is_on_ac(self) -> bool | None:
        status = self._find("status")
        if not status:
            return None
        try:
            val = status.read_text(encoding="utf-8").strip().lower()
            if val in {"charging", "full"}:
                return True
            if val == "discharging":
                return False
        except OSError:
            return None
        return None


class Ina219PowerProvider(PowerProvider):
    """Placeholder for INA219 I2C current sensors (Phase 3 wiring)."""

    def battery_percent(self) -> float | None:
        log.debug("INA219 provider not configured; returning None")
        return None

    def is_on_ac(self) -> bool | None:
        return None


def mode_from_soc(percent: float | None) -> PowerMode:
    if percent is None:
        return PowerMode.NORMAL
    if percent < 10:
        return PowerMode.EMERGENCY
    if percent < 20:
        return PowerMode.CRITICAL
    if percent < 40:
        return PowerMode.ECO
    return PowerMode.NORMAL


def should_run_live_rx(mode: PowerMode) -> bool:
    return mode == PowerMode.NORMAL


def should_serve_wifi(mode: PowerMode) -> bool:
    return True  # Keep portal up as long as the board is on


def get_power_provider(name: str, mock_percent: float = 85.0) -> PowerProvider:
    name = (name or "mock").lower()
    if name == "sysfs":
        return SysfsBatteryProvider()
    if name == "ina219":
        return Ina219PowerProvider()
    return MockPowerProvider(percent=mock_percent)
