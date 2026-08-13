"""Load SkyCache content packages from disk (manifest.json + files)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from skycache.models import ContentFile, ContentPackage


def load_manifest(path: Path) -> ContentPackage:
    """Load package from a directory containing manifest.json."""
    path = Path(path)
    manifest = path / "manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"No manifest.json in {path}")
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    pkg = ContentPackage.model_validate(data)
    # Refresh file sizes from disk when possible
    files: list[ContentFile] = []
    total = 0
    for f in pkg.files:
        fp = path / f.path
        size = f.size_bytes
        if fp.is_file():
            size = fp.stat().st_size
        total += size
        files.append(ContentFile(path=f.path, mime=f.mime, size_bytes=size, role=f.role))
    if total and (pkg.size_bytes == 0 or abs(pkg.size_bytes - total) > 0):
        pkg = pkg.model_copy(update={"files": files, "size_bytes": total})
    else:
        pkg = pkg.model_copy(update={"files": files})
    return pkg


def copy_package_tree(src: Path, dest: Path) -> Path:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def discover_packages(root: Path) -> list[Path]:
    """Find package directories under root (immediate children with manifest.json)."""
    root = Path(root)
    if not root.is_dir():
        return []
    found: list[Path] = []
    # Direct package
    if (root / "manifest.json").is_file():
        found.append(root)
        return found
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "manifest.json").is_file():
            found.append(child)
    return found
