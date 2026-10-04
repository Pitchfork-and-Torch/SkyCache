"""Create and validate SkyCache content packages (Phase 1)."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from skycache.models import ContentFile, ContentPackage, PriorityClass, SourceInfo

_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")


def validate_package_dir(path: Path) -> list[str]:
    """Return a list of validation errors (empty = OK)."""
    path = Path(path)
    errors: list[str] = []
    if not path.is_dir():
        return [f"Not a directory: {path}"]
    manifest = path / "manifest.json"
    if not manifest.is_file():
        return ["Missing manifest.json"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        pkg = ContentPackage.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        return [f"Invalid manifest: {exc}"]

    if not _ID_RE.match(pkg.id):
        errors.append(f"Unsafe or empty package id: {pkg.id!r}")
    if not pkg.title:
        errors.append("title must include at least one language key")
    if not pkg.files:
        errors.append("files list is empty")
    for f in pkg.files:
        fp = path / f.path
        if ".." in Path(f.path).parts or f.path.startswith(("/", "\\")):
            errors.append(f"Unsafe file path: {f.path}")
            continue
        if not fp.is_file():
            errors.append(f"Missing file: {f.path}")
    # Legal gate: source type string
    lowered = (pkg.source.type + " " + (pkg.source.plugin or "")).lower()
    for bad in ("starlink", "oneweb", "decrypt-commercial"):
        if bad in lowered:
            errors.append(f"Forbidden source keyword: {bad}")
    return errors


def create_package(
    out_dir: Path,
    *,
    package_id: str,
    title: str,
    priority_class: str = "education",
    summary: str = "",
    language: str = "en",
    source_files: list[Path] | None = None,
    html_body: str | None = None,
    license_name: str = "operator_supplied",
    tags: list[str] | None = None,
) -> Path:
    """
    Scaffold a package directory with manifest.json and optional HTML / copied files.

    Returns the package directory path.
    """
    if not _ID_RE.match(package_id):
        raise ValueError(f"Invalid package id: {package_id}")
    pclass = PriorityClass(priority_class)
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    files: list[ContentFile] = []
    total = 0

    if html_body is not None:
        index = out_dir / "index.html"
        index.write_text(html_body, encoding="utf-8")
        size = index.stat().st_size
        total += size
        files.append(ContentFile(path="index.html", mime="text/html", size_bytes=size))

    for src in source_files or []:
        src = Path(src)
        if not src.is_file():
            raise FileNotFoundError(src)
        dest_name = src.name
        dest = out_dir / dest_name
        shutil.copy2(src, dest)
        size = dest.stat().st_size
        total += size
        mime = "text/html" if dest.suffix.lower() in {".html", ".htm"} else "application/octet-stream"
        if dest.suffix.lower() == ".png":
            mime = "image/png"
        elif dest.suffix.lower() in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        elif dest.suffix.lower() == ".pdf":
            mime = "application/pdf"
        files.append(ContentFile(path=dest_name, mime=mime, size_bytes=size))

    if not files:
        # Minimal stub page
        stub = (
            f"<!DOCTYPE html><html lang='{language}'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{title}</title></head><body><h1>{title}</h1>"
            f"<p>{summary or 'SkyCache package'}</p></body></html>"
        )
        index = out_dir / "index.html"
        index.write_text(stub, encoding="utf-8")
        size = index.stat().st_size
        total += size
        files.append(ContentFile(path="index.html", mime="text/html", size_bytes=size))

    pkg = ContentPackage(
        id=package_id,
        kind="html_pack",
        priority_class=pclass,
        title={language: title, "en": title} if language != "en" else {"en": title},
        summary={language: summary or title, "en": summary or title}
        if language != "en"
        else {"en": summary or title},
        languages=[language] if language == "en" else [language, "en"],
        received_at=datetime.now(timezone.utc),
        freshness_hours=24 * 180,
        size_bytes=total,
        license=license_name,
        source=SourceInfo(
            type="package_create",
            legal_note="Operator-supplied package; ensure redistribution rights",
            plugin="package_import",
        ),
        files=files,
        tags=tags or [pclass.value],
        icon=pclass.value,
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(pkg.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    errs = validate_package_dir(out_dir)
    if errs:
        raise ValueError("Created package failed validation: " + "; ".join(errs))
    return out_dir
