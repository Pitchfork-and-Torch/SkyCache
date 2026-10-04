"""Signal quality tracking hooks (filled by live pipelines)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SignalSnapshot:
    quality: float | None = None  # 0.0 - 1.0
    snr_db: float | None = None
    last_pass_at: datetime | None = None
    last_plugin: str | None = None
    message: str = "No live reception yet (simulation or idle)"


@dataclass
class SignalMonitor:
    snapshot: SignalSnapshot = field(default_factory=SignalSnapshot)

    def update(
        self,
        quality: float | None = None,
        snr_db: float | None = None,
        plugin: str | None = None,
        message: str | None = None,
    ) -> None:
        if quality is not None:
            self.snapshot.quality = max(0.0, min(1.0, quality))
        if snr_db is not None:
            self.snapshot.snr_db = snr_db
        if plugin:
            self.snapshot.last_plugin = plugin
        if message:
            self.snapshot.message = message
        self.snapshot.last_pass_at = datetime.now(timezone.utc)
