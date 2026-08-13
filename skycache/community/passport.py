"""License passport - provenance, integrity, redistribute posture for packages/works.

Wave 2.D1: every package and Skybrary work exposes a machine-readable passport
suitable for PWA chips, partner review, and operator compliance exports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skycache.models import ContentPackage, PackageRecord
from skycache.skybrary.license_gate import normalize_license

# Licenses generally OK for community redistribution when terms are followed
_REDISTribute_YES = frozenset(
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
        "moh-open",
        "open-access",
        "apache-2.0",
        "mit",
        "gutenberg",
        "project gutenberg",
    }
)


def redistribute_posture(license_raw: str) -> dict[str, Any]:
    """Return yes/no/review + operator-facing note for a license string."""
    lic = normalize_license(license_raw)
    if not lic:
        return {
            "redistribute": "no",
            "redistribute_note": "Missing license - do not redistribute until labeled.",
        }
    for marker in ("all rights reserved", "piracy", "warez", "kindle", "copyrighted commercial"):
        if marker in lic:
            return {
                "redistribute": "no",
                "redistribute_note": "License forbids open redistribution on this hub.",
            }
    # NC / operator-supplied / Kiwix / unknown - review before share (before CC-BY match)
    if (
        "nc" in lic
        or lic in {"operator_supplied", "kiwix", "unknown"}
        or "operator_supplied" in lic
        or "kiwix" in lic
    ):
        return {
            "redistribute": "review",
            "redistribute_note": (
                "Operator review required (NC, operator-supplied, Kiwix/ZIM terms, or unknown)."
            ),
        }
    for good in sorted(_REDISTribute_YES, key=len, reverse=True):
        if lic == good or good in lic:
            note = "Open / public-domain style license - redistribute with attribution where required."
            if "by-sa" in lic or "cc-by-sa" in lic:
                note = "CC-BY-SA: redistribute with attribution and share-alike."
            elif "cc0" in lic or "public domain" in lic or lic in {
                "pd",
                "public-domain",
                "public_domain",
            }:
                note = "Public domain / CC0 - free to redistribute; keep provenance for trust."
            elif "gutenberg" in lic:
                note = "Project Gutenberg terms apply; keep PG header/license notice when sharing."
            elif "by" in lic:
                note = "CC-BY: redistribute with attribution."
            return {"redistribute": "yes", "redistribute_note": note}
    return {
        "redistribute": "review",
        "redistribute_note": "Confirm redistribution rights before mesh/USB export.",
    }


def _provenance_url(source_type: str, extra: dict[str, Any], provenance: dict[str, Any]) -> str | None:
    for key in ("url", "uri", "provenance_url", "source_url", "homepage"):
        val = extra.get(key) or provenance.get(key)
        if val:
            return str(val)
    if source_type in {"sample", "skybrary_pd_sample"}:
        return None
    return None


def package_passport(
    package: ContentPackage,
    *,
    path: str | Path | None = None,
    include_integrity: bool = False,
) -> dict[str, Any]:
    """Build license passport for a content package."""
    src = package.source
    extra = dict(src.extra or {})
    work_meta = extra.get("work") if isinstance(extra.get("work"), dict) else {}
    provenance = dict(work_meta.get("provenance") or {})
    edition = extra.get("edition") if isinstance(extra.get("edition"), dict) else {}

    posture = redistribute_posture(package.license)
    sha256 = (
        (edition.get("sha256") if edition else None)
        or extra.get("sha256")
        or None
    )
    if sha256 is not None:
        sha256 = str(sha256)

    file_hashes: list[dict[str, Any]] = []
    for f in package.files:
        entry: dict[str, Any] = {"path": f.path, "size_bytes": f.size_bytes, "mime": f.mime}
        # Per-file hash only if present on ContentFile via future field; check raw dict path
        file_hashes.append(entry)

    integrity: dict[str, Any] | None = None
    if include_integrity and path:
        from skycache.capabilities.integrity_tree import verify_package_dir

        integrity = verify_package_dir(Path(path))
        if not sha256:
            for checked in integrity.get("files") or []:
                if checked.get("path") in ("work.txt", "index.html") and checked.get("sha256"):
                    sha256 = checked["sha256"]
                    break
            if not sha256:
                for checked in integrity.get("files") or []:
                    if checked.get("sha256"):
                        sha256 = checked["sha256"]
                        break

    title = package.title_for("en")
    return {
        "kind": "package",
        "id": package.id,
        "title": title,
        "license": package.license,
        "license_normalized": normalize_license(package.license),
        "redistribute": posture["redistribute"],
        "redistribute_note": posture["redistribute_note"],
        "provenance": {
            "url": _provenance_url(src.type, extra, provenance),
            "source_type": src.type,
            "plugin": src.plugin,
            "legal_note": src.legal_note,
            "detail": provenance or None,
        },
        "retrieval_date": package.received_at.isoformat() if package.received_at else None,
        "sha256": sha256,
        "files": file_hashes,
        "priority_class": package.priority_class.value
        if hasattr(package.priority_class, "value")
        else str(package.priority_class),
        "languages": list(package.languages or []),
        "integrity": integrity,
        "legal": (
            "SkyCache license passport: open/FTA/operator-authored content only. "
            "Not a copyright clearance for commercial reuse outside stated terms."
        ),
    }


def package_record_passport(
    rec: PackageRecord,
    *,
    include_integrity: bool = False,
) -> dict[str, Any]:
    return package_passport(
        rec.package,
        path=rec.path or None,
        include_integrity=include_integrity,
    )


def work_passport(
    work: dict[str, Any],
    *,
    package_path: str | Path | None = None,
    include_integrity: bool = False,
) -> dict[str, Any]:
    """Build license passport for a Skybrary work row (dict from catalog)."""
    license_raw = str(work.get("license") or "unknown")
    posture = redistribute_posture(license_raw)
    provenance = dict(work.get("provenance") or {})
    editions = list(work.get("editions") or [])

    sha256 = None
    retrieval = None
    for ed in editions:
        if ed.get("sha256") and not sha256:
            sha256 = str(ed["sha256"])
        if ed.get("received_at") and not retrieval:
            retrieval = ed["received_at"]

    title_map = work.get("title") or {}
    title = title_map.get("en") or next(iter(title_map.values()), work.get("work_id"))

    integrity: dict[str, Any] | None = None
    if include_integrity and package_path:
        from skycache.capabilities.integrity_tree import verify_package_dir

        integrity = verify_package_dir(Path(package_path))
        if integrity.get("ok") and not sha256:
            for checked in integrity.get("files") or []:
                if checked.get("sha256"):
                    sha256 = checked["sha256"]
                    break

    return {
        "kind": "work",
        "id": work.get("work_id"),
        "work_id": work.get("work_id"),
        "package_id": work.get("package_id"),
        "title": title,
        "creators": list(work.get("creators") or []),
        "license": license_raw,
        "license_normalized": normalize_license(license_raw),
        "redistribute": posture["redistribute"],
        "redistribute_note": posture["redistribute_note"],
        "provenance": {
            "url": _provenance_url(
                str(provenance.get("source") or ""),
                {},
                provenance,
            ),
            "source_type": provenance.get("source"),
            "note": provenance.get("note"),
            "detail": provenance or None,
        },
        "retrieval_date": retrieval,
        "sha256": sha256,
        "editions": [
            {
                "edition_id": e.get("edition_id"),
                "format": e.get("format"),
                "path": e.get("path"),
                "size_bytes": e.get("size_bytes"),
                "sha256": e.get("sha256") or None,
                "received_at": e.get("received_at"),
            }
            for e in editions
        ],
        "subjects": list(work.get("subjects") or []),
        "civilizational_tier": work.get("civilizational_tier"),
        "integrity": integrity,
        "legal": (
            "Skybrary license passport: public domain / open licenses only. "
            "Not a complete archive. Not free commercial broadband."
        ),
    }
