"""Amateur / CubeSat open telemetry via gr-satellites (optional Phase 2+)."""

from __future__ import annotations

import json
import shutil
import subprocess
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


class GrSatellitesPlugin:
    name = "gr_satellites"
    description = "Decode open amateur/CubeSat telemetry with gr-satellites (not commercial services)"
    legal_profile = "amateur_open"
    requires_hardware = True

    def can_handle(self, source: SourceSpec) -> bool:
        return source.plugin == self.name

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        binary = shutil.which("gr_satellites") or shutil.which("gr-satellites")
        if not binary:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=(
                    "gr_satellites not found. Install gr-satellites "
                    "(https://github.com/daniestevez/gr-satellites). "
                    "Only use for open amateur/CubeSat downlinks."
                ),
            )

        sat_name = source.options.get("satellite") or source.uri
        if not sat_name:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message="Provide options.satellite (or uri) with the satellite name supported by gr-satellites",
            )

        wav = source.options.get("wav") or source.options.get("input")
        if not wav:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message="Provide options.wav path to a recorded audio/IQ input for offline decode",
            )

        out_txt = workdir / "telemetry.txt"
        cmd = [binary, str(sat_name), "--wavfile", str(wav)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=int(source.options.get("timeout", 300)),
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"gr_satellites failed: {exc}",
            )

        out_txt.write_text(
            (proc.stdout or "") + "\n" + (proc.stderr or ""),
            encoding="utf-8",
            errors="replace",
        )
        stamp = datetime.now(timezone.utc)
        pkg_id = f"amsat-{stamp.strftime('%Y%m%dT%H%M%SZ')}"
        dest = workdir / pkg_id
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_txt, dest / "telemetry.txt")
        size = (dest / "telemetry.txt").stat().st_size
        pkg = ContentPackage(
            id=pkg_id,
            kind="telemetry",
            priority_class=PriorityClass.TELEMETRY_RAW,
            title={
                "en": f"Open telemetry: {sat_name}",
                "fr": f"Télémétrie ouverte: {sat_name}",
            },
            summary={
                "en": "Amateur/CubeSat open telemetry (educational). Not broadband.",
            },
            languages=["en"],
            received_at=stamp,
            freshness_hours=48,
            size_bytes=size,
            license="open_telemetry",
            source=SourceInfo(
                type="amateur_open",
                legal_note="Open amateur satellite telemetry only",
                plugin=self.name,
                extra={"satellite": sat_name},
            ),
            files=[ContentFile(path="telemetry.txt", mime="text/plain", size_bytes=size)],
            tags=["amateur", "cubesat", "telemetry", "education"],
            icon="education",
        )
        (dest / "manifest.json").write_text(
            json.dumps(pkg.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        ok = proc.returncode == 0 or size > 0
        return CaptureResult(
            plugin=self.name,
            success=ok,
            message="Telemetry capture stored" if ok else f"exit {proc.returncode}",
            artifacts=[str(dest / "manifest.json")],
            suggested_package=pkg if ok else None,
        )
