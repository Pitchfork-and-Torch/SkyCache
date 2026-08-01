"""Licenses Ops (v1.14.0): doctor, inventory status, printable export, kit.

Operator compliance inventory for open packages. Not legal advice.
Not free commercial broadband. No commercial decrypt.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.community.licenses import LicenseInventory
from skycache.db.catalog import Catalog

HONEST = (
    "Licenses ops: local inventory of package licenses for partners and regulators. "
    "Operator confirms redistribution rights for every pack. "
    "Not legal advice. Not free commercial broadband. No commercial decrypt."
)

DOCTOR_SCHEMA = "skycache.licenses.doctor.v1"
STATUS_SCHEMA = "skycache.licenses.status.v1"
EXPORT_SCHEMA = "skycache.licenses.export.v1"
KIT_SCHEMA = "skycache.licenses.kit.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _inventory(settings) -> tuple[LicenseInventory, Catalog, dict[str, Any]]:
    catalog = Catalog(settings.db_path)
    inv = LicenseInventory(catalog)
    rep = inv.report()
    return inv, catalog, rep


def licenses_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    """License inventory snapshot (closes catalog)."""
    settings = _settings(data_dir)
    inv, catalog, rep = _inventory(settings)
    try:
        return {
            "schema": STATUS_SCHEMA,
            "generated_at": _iso_now(),
            "software_version": __version__,
            "package_count": rep.get("package_count"),
            "by_license": rep.get("by_license"),
            "unknown_or_blank": rep.get("unknown_or_blank"),
            "operator_duty": rep.get("operator_duty"),
            "legal": rep.get("legal"),
            "banner": HONEST,
        }
    finally:
        catalog.close()


def licenses_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Compliance readiness for partner/regulator license inventory."""
    settings = _settings(data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    inv, catalog, rep = _inventory(settings)
    try:
        n = int(rep.get("package_count") or 0)
        unknown = int(rep.get("unknown_or_blank") or 0)
        add("packages", n >= 1, f"{n} packages inventoried", 20)
        add(
            "unknown_rate",
            unknown == 0 or (n > 0 and unknown / n < 0.5),
            f"unknown_or_blank={unknown} of {n}",
            18,
        )
        add("report_api", True, "skycache licenses status / export available", 10)
        add(
            "by_license",
            bool(rep.get("by_license")),
            f"license buckets={len(rep.get('by_license') or {})}",
            12,
        )
        # Content dir may have packages not yet in catalog
        content = settings.content_dir
        disk_pkgs = (
            sum(1 for p in content.iterdir() if p.is_dir() and (p / "manifest.json").is_file())
            if content.is_dir()
            else 0
        )
        add(
            "catalog_vs_disk",
            disk_pkgs == 0 or n >= max(1, disk_pkgs // 2),
            f"catalog={n} disk_content_dirs={disk_pkgs}",
            10,
        )

        total_w = sum(c["weight"] for c in checks) or 1
        earned = sum(c["weight"] for c in checks if c["ok"])
        score = int(round(100.0 * earned / total_w))
        go_inventory = n >= 1
        go_partner = go_inventory and unknown == 0

        return {
            "schema": DOCTOR_SCHEMA,
            "generated_at": _iso_now(),
            "software_version": __version__,
            "score": score,
            "go_licenses_inventory": go_inventory,
            "go_partner_export": go_partner,
            "package_count": n,
            "unknown_or_blank": unknown,
            "by_license": rep.get("by_license"),
            "checks": checks,
            "banner": HONEST,
            "next_steps": [
                "skycache licenses doctor",
                "skycache licenses status",
                "skycache licenses export --out data/ops/licenses-inventory.html",
                "skycache licenses kit --out data/licenses-kit",
                "Label unknown licenses before partner pilot",
            ],
            "legal": rep.get("legal"),
        }
    finally:
        catalog.close()


def export_licenses_html(
    out_path: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Write printable license inventory HTML."""
    settings = _settings(data_dir)
    inv, catalog, rep = _inventory(settings)
    try:
        html = inv.report_html(
            node_id=settings.node_id or "village-hub",
            version=__version__,
        )
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        summary = {
            "schema": EXPORT_SCHEMA,
            "ok": True,
            "generated_at": _iso_now(),
            "software_version": __version__,
            "path": str(out_path),
            "package_count": rep.get("package_count"),
            "unknown_or_blank": rep.get("unknown_or_blank"),
            "banner": HONEST,
        }
        (out_path.parent / "licenses-export.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        return summary
    finally:
        catalog.close()


def write_licenses_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """Kit: doctor, HTML inventory, checklist, zip."""
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = licenses_doctor(data_dir=settings.data_dir)
    (out_dir / "licenses-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    export_licenses_html(out_dir / "licenses-inventory.html", data_dir=settings.data_dir)

    (out_dir / "README.md").write_text(
        f"""# Licenses kit

{HONEST}

## Commands

```text
skycache licenses doctor
skycache licenses status
skycache licenses export --out data/ops/licenses-inventory.html
skycache licenses kit --out data/licenses-kit
```

## Partner use

Print licenses-inventory.html (browser Save as PDF) before NGO/university pilots.

Software v{__version__}
""",
        encoding="utf-8",
    )
    (out_dir / "FIELD-CHECKLIST.md").write_text(
        f"""# Licenses field checklist

{HONEST}

- [ ] licenses doctor go_licenses_inventory true
- [ ] unknown_or_blank is 0 (or documented exceptions)
- [ ] printable inventory exported
- [ ] Kiwix/ZIM and MoH packs reviewed under their own terms
- [ ] inventory re-run after bulk corpus import
""",
        encoding="utf-8",
    )
    (out_dir / "HOSTING.json").write_text(
        json.dumps(
            {
                "schema": KIT_SCHEMA,
                "generated_at": _iso_now(),
                "software_version": __version__,
                "banner": HONEST,
                "download_hint": "/downloads/skycache-licenses-kit.zip",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    zip_path: str | None = None
    if zip_bundle:
        zp = out_dir.parent / f"{out_dir.name}.zip"
        if zp.is_file():
            zp.unlink()
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=f"{out_dir.name}/{f.relative_to(out_dir).as_posix()}")
        zip_path = str(zp)

    return {
        "schema": KIT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "zip": zip_path,
        "go_licenses_inventory": doc.get("go_licenses_inventory"),
        "score": doc.get("score"),
        "banner": HONEST,
    }
