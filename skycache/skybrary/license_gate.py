"""Fail-closed license gate for Skybrary ingest."""

from __future__ import annotations

ALLOWED_LICENSE_MARKERS: frozenset[str] = frozenset(
    {
        "public domain",
        "public-domain",
        "public_domain",
        "pd",
        "cc0",
        "cc0-1.0",
        "cc-by",
        "cc-by-4.0",
        "cc-by-sa",
        "cc-by-sa-4.0",
        "cc-by-nc",  # allowed only with operator redistribution review note
        "gutenberg",
        "project gutenberg",
        "operator_supplied",
        "moh-open",
        "open-access",
        "apache-2.0",
        "mit",
        "odbl",
        "odbl-1.0",
        "open data commons",
        "open database license",
    }
)

FORBIDDEN_MARKERS: frozenset[str] = frozenset(
    {
        "all rights reserved",
        "copyrighted commercial",
        "kindle unlimited",
        "piracy",
        "warez",
        "starlink",
        "decrypt",
    }
)


def normalize_license(raw: str) -> str:
    return (raw or "").strip().lower()


def license_allowed(raw: str) -> bool:
    lic = normalize_license(raw)
    if not lic or lic == "unknown":
        return False
    for bad in FORBIDDEN_MARKERS:
        if bad in lic:
            return False
    for good in ALLOWED_LICENSE_MARKERS:
        if good in lic:
            return True
    return False


def assert_license_allowed(raw: str) -> str:
    if not license_allowed(raw):
        raise ValueError(
            f"Skybrary refusing license '{raw}': only public domain / open / "
            "explicitly authorized materials. Track provenance."
        )
    return normalize_license(raw)
