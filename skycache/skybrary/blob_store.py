"""Content-addressed blob store for large open archives (v0.9.1).

Files are stored under data/blobs/ab/cd/<sha256> with optional .json sidecars
for media type and provenance. Packages may reference blobs by hash without
duplicating multi-MB payloads on every USB kit.

Legal: integrity and dedup of open packages only  -  not DRM defeat.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.skybrary.integrity import sha256_file


def blob_rel_path(digest: str) -> Path:
    d = digest.lower().strip()
    if len(d) < 4 or any(c not in "0123456789abcdef" for c in d):
        raise ValueError(f"Invalid sha256 digest: {digest!r}")
    return Path(d[:2]) / d[2:4] / d


class BlobStore:
    """SHA-256 content-addressed store under root (usually data/blobs)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        return self.root / blob_rel_path(digest)

    def meta_path_for(self, digest: str) -> Path:
        return self.path_for(digest).with_suffix(self.path_for(digest).suffix + ".json") if False else (
            self.path_for(digest).parent / f"{digest.lower()}.meta.json"
        )

    def has(self, digest: str) -> bool:
        return self.path_for(digest).is_file()

    def put_file(
        self,
        src: Path,
        *,
        media_type: str = "application/octet-stream",
        provenance: dict[str, Any] | None = None,
        copy: bool = True,
    ) -> dict[str, Any]:
        """Store file by content hash. Returns digest + path metadata."""
        src = Path(src)
        if not src.is_file():
            raise FileNotFoundError(src)
        digest = sha256_file(src)
        dest = self.path_for(digest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.is_file():
            if copy:
                shutil.copy2(src, dest)
            else:
                shutil.move(str(src), str(dest))
        meta = {
            "schema": "skycache.blob.v1",
            "sha256": digest,
            "size_bytes": dest.stat().st_size,
            "media_type": media_type,
            "stored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "provenance": provenance or {},
            "legal": "Open/authorized content only; blob store is integrity/dedup, not piracy.",
        }
        meta_path = dest.parent / f"{digest}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return {
            "ok": True,
            "sha256": digest,
            "path": str(dest),
            "meta_path": str(meta_path),
            "size_bytes": meta["size_bytes"],
            "deduped": dest.stat().st_size == src.stat().st_size and True,
        }

    def get(self, digest: str) -> Path | None:
        p = self.path_for(digest)
        return p if p.is_file() else None

    def verify(self, digest: str) -> dict[str, Any]:
        p = self.path_for(digest)
        if not p.is_file():
            return {"ok": False, "sha256": digest, "error": "missing"}
        actual = sha256_file(p)
        match = actual.lower() == digest.lower()
        return {
            "ok": match,
            "sha256": digest,
            "actual": actual,
            "size_bytes": p.stat().st_size,
            "path": str(p),
        }

    def link_into_package(
        self,
        digest: str,
        package_dir: Path,
        rel_name: str,
        *,
        hardlink: bool = False,
    ) -> Path:
        """Place a blob into a package directory (copy or hardlink)."""
        src = self.get(digest)
        if src is None:
            raise FileNotFoundError(f"Blob {digest} not in store")
        package_dir = Path(package_dir)
        package_dir.mkdir(parents=True, exist_ok=True)
        dest = package_dir / Path(rel_name).name
        if dest.exists():
            dest.unlink()
        if hardlink:
            try:
                dest.hardlink_to(src)
                return dest
            except OSError:
                pass
        shutil.copy2(src, dest)
        return dest

    def stats(self) -> dict[str, Any]:
        count = 0
        total = 0
        for p in self.root.rglob("*"):
            if p.is_file() and not p.name.endswith(".meta.json"):
                count += 1
                total += p.stat().st_size
        return {
            "blob_count": count,
            "total_bytes": total,
            "root": str(self.root),
            "schema": "skycache.blob.v1",
        }

    def ingest_content_tree(self, content_dir: Path) -> dict[str, Any]:
        """Hash large files from content packages into the blob store (dedup)."""
        content_dir = Path(content_dir)
        stored: list[str] = []
        if not content_dir.is_dir():
            return {"ok": False, "error": "content dir missing", "stored": []}
        for pkg in sorted(content_dir.iterdir()):
            if not pkg.is_dir():
                continue
            for f in pkg.rglob("*"):
                if not f.is_file():
                    continue
                if f.name in {"manifest.json", "index.html"} and f.stat().st_size < 50_000:
                    continue
                if f.stat().st_size < 4096:
                    continue
                meta = self.put_file(
                    f,
                    media_type=_guess_media(f),
                    provenance={"package": pkg.name, "path": str(f.relative_to(pkg))},
                )
                stored.append(meta["sha256"])
        return {
            "ok": True,
            "stored_count": len(stored),
            "unique": len(set(stored)),
            "digests": list(dict.fromkeys(stored))[:50],
            **self.stats(),
        }


def _guess_media(path: Path) -> str:
    suf = path.suffix.lower()
    return {
        ".txt": "text/plain",
        ".html": "text/html",
        ".htm": "text/html",
        ".epub": "application/epub+zip",
        ".pdf": "application/pdf",
        ".mbtiles": "application/x-sqlite3",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".zip": "application/zip",
    }.get(suf, "application/octet-stream")
