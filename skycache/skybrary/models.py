"""Skybrary work/edition models (Phase S1 scaffold)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Work(BaseModel):
    """A conceptual written work (book, essay, article)."""

    work_id: str
    title: dict[str, str] = Field(default_factory=dict)
    creators: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    subjects: list[str] = Field(default_factory=list)
    era: str | None = None
    license: str = "unknown"
    provenance: dict[str, Any] = Field(default_factory=dict)
    civilizational_tier: int = Field(default=3, ge=1, le=5)
    summary: dict[str, str] = Field(default_factory=dict)


class Edition(BaseModel):
    """A concrete file/format instance of a Work."""

    edition_id: str
    work_id: str
    format: str = "txt"  # txt | epub | pdf | md | html
    path: str = ""
    size_bytes: int = 0
    sha256: str = ""
    priority_class: str = "education"
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PackProfile(BaseModel):
    """Size-bounded selection of works for constrained nodes."""

    id: str
    max_bytes: int
    languages: list[str] = Field(default_factory=list)
    include_subjects: list[str] = Field(default_factory=list)
    prefer_formats: list[str] = Field(default_factory=lambda: ["epub", "txt", "html"])
    description: str = ""
