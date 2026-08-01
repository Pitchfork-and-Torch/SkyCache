"""Checksum helpers for Skybrary preservation."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_file(path: Path, expected_sha256: str) -> bool:
    if not expected_sha256:
        return False
    return sha256_file(path).lower() == expected_sha256.lower()
