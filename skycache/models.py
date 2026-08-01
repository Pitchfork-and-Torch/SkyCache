"""Domain models for SkyCache content packages and runtime status."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PriorityClass(str, Enum):
    """Higher weight = more valuable when storage is constrained."""

    EMERGENCY = "emergency"
    HEALTH = "health"
    EDUCATION = "education"
    AGRICULTURE = "agriculture"
    WEATHER = "weather"
    MAPS = "maps"
    GENERAL = "general"
    TELEMETRY_RAW = "telemetry_raw"


# Default class weights used by the prioritizer (higher = keep longer).
CLASS_WEIGHTS: dict[PriorityClass, float] = {
    PriorityClass.EMERGENCY: 1000.0,
    PriorityClass.HEALTH: 800.0,
    PriorityClass.EDUCATION: 700.0,
    PriorityClass.AGRICULTURE: 600.0,
    PriorityClass.WEATHER: 500.0,
    PriorityClass.MAPS: 400.0,
    PriorityClass.GENERAL: 200.0,
    PriorityClass.TELEMETRY_RAW: 50.0,
}


class LegalProfile(str, Enum):
    FTA_PUBLIC = "fta_public"
    AMATEUR_OPEN = "amateur_open"
    FILE_IMPORT_ONLY = "file_import_only"


class PowerMode(str, Enum):
    NORMAL = "normal"
    ECO = "eco"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ContentFile(BaseModel):
    path: str
    mime: str = "application/octet-stream"
    size_bytes: int = 0
    role: str = "payload"  # payload | thumbnail | index


class SourceInfo(BaseModel):
    type: str
    legal_note: str = "unencrypted public or openly licensed content"
    plugin: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ContentPackage(BaseModel):
    """Normalized content unit stored on disk + indexed in SQLite."""

    id: str
    kind: str
    priority_class: PriorityClass
    title: dict[str, str] = Field(default_factory=dict)
    summary: dict[str, str] = Field(default_factory=dict)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness_hours: int = 72
    size_bytes: int = 0
    license: str = "unknown"
    source: SourceInfo
    files: list[ContentFile] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    icon: str | None = None

    @field_validator("id")
    @classmethod
    def id_safe(cls, v: str) -> str:
        if not v or any(c in v for c in ("/", "\\", "..")):
            raise ValueError("package id must be a simple safe identifier")
        return v

    def title_for(self, lang: str = "en") -> str:
        return self.title.get(lang) or self.title.get("en") or self.id

    def summary_for(self, lang: str = "en") -> str:
        return self.summary.get(lang) or self.summary.get("en") or ""


class CaptureResult(BaseModel):
    """Output of a decoder plugin before normalization."""

    plugin: str
    success: bool
    message: str = ""
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    suggested_package: ContentPackage | None = None


class SourceSpec(BaseModel):
    """Input description for a pipeline run."""

    uri: str = ""
    plugin: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class PackageRecord(BaseModel):
    """Catalog row returned by the API."""

    package: ContentPackage
    score: float = 0.0
    path: str = ""
    age_hours: float = 0.0
    is_stale: bool = False


class SystemStatus(BaseModel):
    version: str
    sim_mode: bool
    power_mode: PowerMode
    battery_percent: float | None = None
    disk_free_bytes: int
    disk_total_bytes: int
    package_count: int
    last_ingest: datetime | None = None
    signal_quality: float | None = None
    legal_banner: str = (
        "Receive-only. Unencrypted / free-to-air / open content only. "
        "Check local spectrum and WiFi regulations before deployment."
    )
