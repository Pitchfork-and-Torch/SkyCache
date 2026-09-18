"""Import offline packages: SkyCache folders, ZIM metadata stubs, USB drops."""

from __future__ import annotations

import json
import shutil
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


class PackageImportPlugin:
    name = "package_import"
    description = "Import USB/offline SkyCache packages, HTML packs, or ZIM file metadata"
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        if source.plugin and source.plugin not in (self.name, None, ""):
            return source.plugin == self.name
        if not source.uri:
            return False
        p = Path(source.uri)
        return p.exists()

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        src = Path(source.uri)
        if not src.exists():
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"Path not found: {src}",
            )

        if src.is_dir() and (src / "manifest.json").is_file():
            dest = workdir / src.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            pkg = ContentPackage.model_validate(data)
            return CaptureResult(
                plugin=self.name,
                success=True,
                message=f"Imported package {pkg.id}",
                artifacts=[str(dest / "manifest.json")],
                suggested_package=pkg,
            )

        if src.suffix.lower() == ".zim":
            return self._zim_stub(src, workdir)

        if src.is_dir():
            # Treat directory of HTML/files as general education pack
            return self._folder_pack(src, workdir, source)

        return CaptureResult(
            plugin=self.name,
            success=False,
            message=f"Unsupported import path: {src}",
        )

    def _zim_stub(self, zim: Path, workdir: Path) -> CaptureResult:
        stamp = datetime.now(timezone.utc)
        pkg_id = f"zim-{zim.stem}"[:80]
        dest = workdir / pkg_id
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / zim.name
        shutil.copy2(zim, target)
        size = target.stat().st_size
        pkg = ContentPackage(
            id=pkg_id,
            kind="zim",
            priority_class=PriorityClass.EDUCATION,
            title={
                "en": f"Kiwix library: {zim.stem}",
                "fr": f"Bibliothèque Kiwix: {zim.stem}",
                "sw": f"Maktaba ya Kiwix: {zim.stem}",
            },
            summary={
                "en": (
                    "Offline ZIM package. Serve with kiwix-serve alongside SkyCache "
                    "or open with Kiwix on a connected device."
                ),
            },
            languages=["en"],
            received_at=stamp,
            freshness_hours=24 * 365,
            size_bytes=size,
            license="see_zim_metadata",
            source=SourceInfo(
                type="zim_import",
                legal_note="Only import ZIM files you are licensed to redistribute offline",
                plugin=self.name,
            ),
            files=[
                ContentFile(
                    path=zim.name,
                    mime="application/octet-stream",
                    size_bytes=size,
                    role="payload",
                )
            ],
            tags=["education", "kiwix", "zim", "offline"],
            icon="education",
        )
        readme = dest / "README.txt"
        readme.write_text(
            "This is a Kiwix ZIM file. Install kiwix-tools and run:\n"
            f"  kiwix-serve --port 8081 {zim.name}\n"
            "Or open with the Kiwix app after copying the file.\n",
            encoding="utf-8",
        )
        (dest / "manifest.json").write_text(
            json.dumps(pkg.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Registered ZIM {zim.name}",
            artifacts=[str(dest / "manifest.json")],
            suggested_package=pkg,
        )

    def _folder_pack(
        self, src: Path, workdir: Path, source: SourceSpec
    ) -> CaptureResult:
        stamp = datetime.now(timezone.utc)
        name = source.options.get("id") or f"pack-{src.name}"
        dest = workdir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        files: list[ContentFile] = []
        total = 0
        for fp in dest.rglob("*"):
            if fp.is_file() and fp.name != "manifest.json":
                rel = str(fp.relative_to(dest)).replace("\\", "/")
                size = fp.stat().st_size
                total += size
                mime = "text/html" if fp.suffix.lower() in {".html", ".htm"} else "application/octet-stream"
                files.append(ContentFile(path=rel, mime=mime, size_bytes=size))
        pclass = PriorityClass(source.options.get("priority_class", "education"))
        pkg = ContentPackage(
            id=name,
            kind=source.options.get("kind", "html_pack"),
            priority_class=pclass,
            title={"en": source.options.get("title", src.name)},
            summary={"en": source.options.get("summary", "Imported offline package")},
            languages=list(source.options.get("languages") or ["en"]),
            received_at=stamp,
            freshness_hours=int(source.options.get("freshness_hours", 24 * 180)),
            size_bytes=total,
            license=str(source.options.get("license", "operator_supplied")),
            source=SourceInfo(
                type="folder_import",
                legal_note="Operator-supplied offline package; ensure redistribution rights",
                plugin=self.name,
            ),
            files=files,
            tags=list(source.options.get("tags") or ["import"]),
            icon=source.options.get("icon", "education"),
        )
        (dest / "manifest.json").write_text(
            json.dumps(pkg.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Imported folder pack {name}",
            artifacts=[str(dest / "manifest.json")],
            suggested_package=pkg,
        )
