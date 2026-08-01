"""Decoder plugin protocol for SkyCache pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from skycache.models import CaptureResult, SourceSpec

LegalProfileName = Literal["fta_public", "amateur_open", "file_import_only"]


@runtime_checkable
class DecoderPlugin(Protocol):
    name: str
    description: str
    legal_profile: LegalProfileName
    requires_hardware: bool

    def can_handle(self, source: SourceSpec) -> bool: ...

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult: ...
