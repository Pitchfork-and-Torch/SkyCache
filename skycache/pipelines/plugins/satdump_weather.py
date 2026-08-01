"""Weather reception via external SatDump CLI (Phase 2).

Does not reimplement demodulation. When satdump is not installed,
returns a clear guidance message. Simulation-friendly via options.
"""

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


class SatDumpWeatherPlugin:
    name = "satdump_weather"
    description = "Decode free-to-air weather imagery via SatDump CLI (APT/LRPT/HRIT)"
    legal_profile = "fta_public"
    requires_hardware = True

    def can_handle(self, source: SourceSpec) -> bool:
        if source.plugin and source.plugin != self.name:
            return False
        return source.plugin == self.name or source.options.get("kind") == "weather"

    def _satdump_path(self) -> str | None:
        return shutil.which("satdump") or shutil.which("satdump_cli")

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        # File import path: treat existing image as weather product
        if source.uri and Path(source.uri).is_file():
            return self._from_file(Path(source.uri), workdir, source)

        satdump = self._satdump_path()
        if not satdump:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=(
                    "SatDump CLI not found on PATH. Install SatDump "
                    "(https://www.satdump.org / GitHub SatDump/SatDump) "
                    "for live weather decode, or pass a decoded image file URI."
                ),
            )

        pipeline = source.options.get("pipeline", "NOAA_APT")
        input_file = source.uri or source.options.get("input", "")
        if not input_file:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=(
                    "Provide source.uri as baseband/IQ path or set options.input. "
                    "Live USB SDR capture orchestration is Phase 2; "
                    "use satdump GUI/CLI for live RX then point SkyCache at outputs."
                ),
            )

        out_dir = workdir / "satdump_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            satdump,
            pipeline,
            str(input_file),
            str(out_dir),
        ]
        # Allow extra args
        extra = source.options.get("extra_args") or []
        if isinstance(extra, list):
            cmd.extend(str(x) for x in extra)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=int(source.options.get("timeout", 600)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message="SatDump timed out",
            )
        except OSError as exc:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"Failed to run SatDump: {exc}",
            )

        if proc.returncode != 0:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"SatDump exited {proc.returncode}: {proc.stderr[:500]}",
                metadata={"stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:]},
            )

        images = list(out_dir.rglob("*.png")) + list(out_dir.rglob("*.jpg"))
        if not images:
            return CaptureResult(
                plugin=self.name,
                success=False,
                message="SatDump finished but no images found in output",
                metadata={"stdout": proc.stdout[-1000:]},
            )

        return self._package_images(images, workdir, pipeline)

    def _from_file(self, path: Path, workdir: Path, source: SourceSpec) -> CaptureResult:
        dest = workdir / "weather_import"
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / path.name
        shutil.copy2(path, target)
        return self._package_images([target], workdir, source.options.get("pipeline", "import"))

    def _package_images(
        self, images: list[Path], workdir: Path, pipeline: str
    ) -> CaptureResult:
        stamp = datetime.now(timezone.utc)
        pkg_id = f"wx-{stamp.strftime('%Y%m%dT%H%M%SZ')}"
        dest = workdir / pkg_id
        dest.mkdir(parents=True, exist_ok=True)
        files: list[ContentFile] = []
        total = 0
        for img in images[:8]:
            name = img.name
            target = dest / name
            if img.resolve() != target.resolve():
                shutil.copy2(img, target)
            size = target.stat().st_size
            total += size
            mime = "image/png" if name.lower().endswith(".png") else "image/jpeg"
            files.append(ContentFile(path=name, mime=mime, size_bytes=size))

        pkg = ContentPackage(
            id=pkg_id,
            kind="weather_image",
            priority_class=PriorityClass.WEATHER,
            title={
                "en": f"Weather imagery ({pipeline})",
                "fr": f"Images météo ({pipeline})",
                "es": f"Imágenes meteorológicas ({pipeline})",
                "sw": f"Picha za hali ya hewa ({pipeline})",
            },
            summary={
                "en": "Free-to-air weather satellite product via SatDump.",
                "fr": "Produit météo libre via SatDump.",
            },
            languages=["en"],
            received_at=stamp,
            freshness_hours=12,
            size_bytes=total,
            license="public_domain_or_open",
            source=SourceInfo(
                type="weather_fta",
                legal_note="Unencrypted free-to-air weather broadcast / open product",
                plugin=self.name,
                extra={"pipeline": pipeline},
            ),
            files=files,
            tags=["weather", "satellite", "fta"],
            icon="weather",
        )
        (dest / "manifest.json").write_text(
            json.dumps(pkg.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Weather package {pkg_id} with {len(files)} images",
            artifacts=[str(dest / "manifest.json")],
            suggested_package=pkg,
        )
