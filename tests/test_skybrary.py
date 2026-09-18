"""Skybrary S1: license gate, integrity, sample corpus packs."""

from __future__ import annotations

from pathlib import Path

import pytest

from skycache.skybrary.integrity import sha256_text, verify_file
from skycache.skybrary.license_gate import assert_license_allowed, license_allowed
from skycache.skybrary.sample_corpus import build_sample_packages


def test_license_gate():
    assert license_allowed("public domain")
    assert license_allowed("CC-BY-4.0")
    assert license_allowed("Project Gutenberg")
    assert not license_allowed("unknown")
    assert not license_allowed("All Rights Reserved commercial ebook")
    with pytest.raises(ValueError):
        assert_license_allowed("piracy dump")


def test_integrity_and_samples(tmp_path: Path):
    paths = build_sample_packages(tmp_path / "skybrary")
    assert len(paths) >= 3
    for p in paths:
        assert (p / "manifest.json").is_file()
        assert (p / "work.txt").is_file()
        assert (p / "index.html").is_file()
        # Hash file bytes (Windows may normalize newlines on write)
        from skycache.skybrary.integrity import sha256_file

        digest = sha256_file(p / "work.txt")
        assert len(digest) == 64
        assert verify_file(p / "work.txt", digest)
        # Text helper still stable for pure unicode strings
        assert len(sha256_text("hello")) == 64
