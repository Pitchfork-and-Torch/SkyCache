"""Open free-to-air educational broadcast *simulation* plugin.

Receive-only framing for open weather / educational bulletin products.
Fully testable with zero RF hardware (sim mode). Never commercial encrypted
constellations (Starlink, OneWeb, paid VSAT, CAS). Fail closed on forbidden names.

Extension pattern for contributors:
  1. Subclass or copy this plugin; set name/description/legal_profile.
  2. can_handle() match only open/FTA URIs or explicit plugin= name.
  3. run() write a ContentPackage with license passport fields in metadata.
  4. Register in skycache.pipelines.plugins.BUILTIN_PLUGINS.
  5. Add pytest with SourceSpec(plugin=..., options={sim: true}).

See docs/plugin-extension-open-fta.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from skycache.models import (
    CaptureResult,
    ContentFile,
    ContentPackage,
    PriorityClass,
    SourceInfo,
    SourceSpec,
)

FORBIDDEN_HINTS = (
    "starlink",
    "oneweb",
    "vsat-paid",
    "decrypt",
    "cas",
    "widevine",
    "commercial-broadband",
)

SAMPLE_BULLETIN = """Open FTA educational weather bulletin (SIMULATION)

This is a simulated free-to-air style product for SkyCache pipeline tests.
It is NOT a live satellite decode and NOT commercial broadband.

Observation literacy (educational):
- Sky condition: partly cloudy (sim)
- Wind: light (sim)
- Note: real FTA weather imagery uses open tools (e.g. SatDump) on lawful signals only.

Legal: unencrypted open educational content. Receive-only. No uplink.
"""


class OpenFtaSimPlugin:
    """Simulated open FTA educational product (no RF hardware)."""

    name = "open_fta_sim"
    description = (
        "Simulate an open free-to-air educational bulletin package (weather/STEM literacy). "
        "Zero hardware; receive-only framing; never commercial decrypt."
    )
    legal_profile = "fta_public"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        if source.plugin and source.plugin != self.name:
            return False
        uri = (source.uri or "").lower()
        for bad in FORBIDDEN_HINTS:
            if bad in uri:
                return False
        if source.plugin == self.name:
            return True
        return uri in ("open-fta-sim", "fta-sim", "open_fta", "sim://open-fta")

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        uri = (source.uri or "").lower()
        for bad in FORBIDDEN_HINTS:
            if bad in uri or bad in json.dumps(source.options or {}).lower():
                return CaptureResult(
                    plugin=self.name,
                    success=False,
                    message=(
                        f"Refused: forbidden commercial/decrypt hint '{bad}'. "
                        "Open FTA educational sources only."
                    ),
                )

        stamp = datetime.now(timezone.utc)
        pkg_id = f"open-fta-sim-bulletin-{stamp.strftime('%Y%m%d%H%M%S')}"
        dest = workdir / pkg_id
        dest.mkdir(parents=True, exist_ok=True)
        body_path = dest / "bulletin.txt"
        body_path.write_text(SAMPLE_BULLETIN, encoding="utf-8", newline="\n")
        html_path = dest / "index.html"
        html_path.write_text(
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>Open FTA sim bulletin</title></head><body>"
            "<h1>Open FTA educational bulletin (sim)</h1>"
            f"<pre>{SAMPLE_BULLETIN}</pre>"
            "<p>Receive-only. Not commercial broadband.</p></body></html>",
            encoding="utf-8",
            newline="\n",
        )
        size = body_path.stat().st_size + html_path.stat().st_size
        pkg = ContentPackage(
            id=pkg_id,
            kind="open_fta_bulletin",
            priority_class=PriorityClass.WEATHER,
            title={"en": "Open FTA educational weather bulletin (sim)"},
            summary={
                "en": "Simulated free-to-air educational product for pipeline tests."
            },
            languages=["en"],
            received_at=stamp,
            freshness_hours=24,
            size_bytes=size,
            license="public domain",
            source=SourceInfo(
                type="fta_public_sim",
                legal_note="Simulated unencrypted open educational bulletin; receive-only",
                plugin=self.name,
                extra={
                    "sim": True,
                    "hardware": False,
                    "commercial_constellation": False,
                },
            ),
            files=[
                ContentFile(
                    path="bulletin.txt",
                    mime="text/plain",
                    size_bytes=body_path.stat().st_size,
                    role="payload",
                ),
                ContentFile(
                    path="index.html",
                    mime="text/html",
                    size_bytes=html_path.stat().st_size,
                    role="index",
                ),
            ],
            tags=["sim", "fta_public", "weather", "education", "open"],
            pinned=False,
        )
        (dest / "manifest.json").write_text(
            pkg.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        passport = {
            "schema": "skycache.license_passport.v1",
            "work_id": pkg_id,
            "license": "public domain",
            "spdx": "CC0-1.0",
            "redistribute": True,
            "provenance": "SkyCache open_fta_sim plugin (no RF)",
            "sha256_note": "verify files after field capture with skycache verify",
            "honest": "Sim only. Not commercial broadband. Not encrypted constellation.",
        }
        (dest / "license-passport.json").write_text(
            json.dumps(passport, indent=2) + "\n",
            encoding="utf-8",
        )
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Simulated open FTA bulletin package {pkg_id}",
            artifacts=[str(dest / "manifest.json"), str(body_path)],
            metadata={
                "sim": True,
                "legal_profile": self.legal_profile,
                "requires_hardware": False,
            },
            suggested_package=pkg,
        )
