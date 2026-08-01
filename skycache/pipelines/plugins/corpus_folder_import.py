"""Bulk import a folder of open .txt/.md/.html/.epub into content packages.

Legal: license option REQUIRED (fail closed). Public domain / open licenses only.
Never pirate mirrors or commercial decrypt.
"""

from __future__ import annotations

from pathlib import Path

from skycache.models import CaptureResult, SourceSpec
from skycache.skybrary.corpus_import import import_folder
from skycache.skybrary.license_gate import assert_license_allowed


class CorpusFolderImportPlugin:
    name = "corpus_folder_import"
    description = (
        "Import directory of .epub/.txt/.md/.html as Skybrary packages "
        "(license option required; fail closed)"
    )
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        if source.plugin == self.name:
            return True
        if source.plugin:
            return False
        if not source.uri:
            return False
        p = Path(source.uri)
        return p.is_dir() and bool(source.options.get("license"))

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        opts = source.options or {}
        license_name = str(opts.get("license") or "").strip()
        try:
            assert_license_allowed(license_name)
        except ValueError as exc:
            return CaptureResult(plugin=self.name, success=False, message=str(exc))

        root = Path(source.uri or opts.get("path") or "")
        if not root.is_dir():
            return CaptureResult(
                plugin=self.name,
                success=False,
                message=f"Directory required: {root}",
            )

        subjects = opts.get("subjects")
        if isinstance(subjects, str):
            subjects = [s.strip() for s in subjects.split(",") if s.strip()]
        creators = opts.get("creators")
        if isinstance(creators, str):
            creators = [c.strip() for c in creators.split(",") if c.strip()]

        try:
            report = import_folder(
                root,
                Path(workdir) / "corpus-out",
                license_name=license_name,
                language=str(opts.get("language") or opts.get("lang") or "en"),
                subjects=subjects,
                creators=creators,
                recursive=bool(opts.get("recursive")),
                max_files=int(opts.get("max_files") or 200),
                id_prefix=str(opts.get("id_prefix") or "corpus"),
            )
        except (ValueError, FileNotFoundError) as exc:
            return CaptureResult(plugin=self.name, success=False, message=str(exc))

        artifacts = [str(Path(p) / "manifest.json") for p in report.get("packages") or []]
        return CaptureResult(
            plugin=self.name,
            success=bool(report.get("ok")),
            message=(
                f"Corpus folder import: {report.get('imported', 0)}/"
                f"{report.get('total_candidates', 0)} packages "
                f"(license={report.get('license')})"
            ),
            artifacts=artifacts,
            metadata={
                "batch": True,
                "imported": report.get("imported", 0),
                "total": report.get("total_candidates", 0),
                "errors": report.get("errors") or [],
                "packages": report.get("packages") or [],
                "legal": report.get("legal"),
            },
        )
