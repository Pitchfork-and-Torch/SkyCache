"""Verify package trees (checksums) - integrity, not DRM defeat."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skycache.skybrary.integrity import sha256_file


def verify_package_dir(pkg_dir: Path) -> dict[str, Any]:
    pkg_dir = Path(pkg_dir)
    manifest = pkg_dir / "manifest.json"
    if not manifest.is_file():
        return {"ok": False, "error": "missing manifest.json", "path": str(pkg_dir)}
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    files = data.get("files") or []
    checked: list[dict[str, Any]] = []
    ok = True
    for f in files:
        rel = f.get("path") or ""
        target = (pkg_dir / rel).resolve()
        if not str(target).startswith(str(pkg_dir.resolve())):
            checked.append({"path": rel, "ok": False, "error": "path traversal"})
            ok = False
            continue
        if not target.is_file():
            checked.append({"path": rel, "ok": False, "error": "missing"})
            ok = False
            continue
        digest = sha256_file(target)
        expected = None
        # Optional per-file sha256 in manifest extra
        extra = (data.get("source") or {}).get("extra") or {}
        if f.get("sha256"):
            expected = f["sha256"]
        elif rel in ("work.txt",) and extra.get("sha256"):
            expected = extra["sha256"]
        match = (expected is None) or (digest.lower() == str(expected).lower())
        if not match:
            ok = False
        checked.append(
            {
                "path": rel,
                "ok": match,
                "sha256": digest,
                "expected": expected,
                "size": target.stat().st_size,
            }
        )
    return {
        "ok": ok,
        "package_id": data.get("id"),
        "license": data.get("license"),
        "files": checked,
        "path": str(pkg_dir),
    }


def verify_content_tree(content_dir: Path) -> dict[str, Any]:
    content_dir = Path(content_dir)
    results = []
    if not content_dir.is_dir():
        return {"ok": False, "error": "content dir missing", "packages": []}
    for child in sorted(content_dir.iterdir()):
        if child.is_dir() and (child / "manifest.json").is_file():
            results.append(verify_package_dir(child))
    return {
        "ok": all(r.get("ok") for r in results) if results else True,
        "count": len(results),
        "packages": results,
        "legal": "Integrity verification of open packages only",
    }
