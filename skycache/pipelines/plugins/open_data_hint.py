"""Future open-data stream hooks (metadata-only / documentation stubs).

Registers lawful public open-data sources operators may wire later
(e.g. public weather product catalogs, MoH open leaflets). Does not download
commercial APIs or decrypt anything. In sim mode, writes a small education pack
describing how to attach open streams.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from skycache.models import (
    CaptureResult,
    ContentFile,
    ContentPackage,
    PriorityClass,
    SourceInfo,
    SourceSpec,
)

# Curated *hints* only - URLs are public documentation, not auto-fetch of paywalled data.
OPEN_HINTS: list[dict[str, str]] = [
    {
        "id": "kiwix-library",
        "title": "Kiwix ZIM offline encyclopedia packs",
        "note": "Import .zim via package_import; respect Kiwix redistribution terms.",
        "priority": "education",
    },
    {
        "id": "noaa-apt-open",
        "title": "NOAA APT / open weather imagery (receive-only)",
        "note": "Use SatDump / open tools; no commercial constellation.",
        "priority": "weather",
    },
    {
        "id": "moh-open-leaflets",
        "title": "Ministry of Health open leaflets",
        "note": "Operator must confirm local redistribution rights.",
        "priority": "health",
    },
    {
        "id": "community-authored",
        "title": "Village-authored guides",
        "note": "Create with skycache package create; license inventory required.",
        "priority": "education",
    },
]


class OpenDataHintPlugin:
    name = "open_data_hint"
    description = (
        "Emit open-data source catalog hints for operators (sim-friendly). "
        "Does not fetch commercial streams."
    )
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        return source.plugin == self.name or (
            not source.plugin and (source.uri or "").lower() in ("open-hints", "open_data", "")
            and source.options.get("hints")
        )

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        workdir = Path(workdir)
        pkg_id = "open-data-hints-001"
        dest = workdir / pkg_id
        dest.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc)

        lines = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Open data hooks</title>",
            "<style>body{font-family:system-ui;max-width:40rem;margin:1.5rem auto;padding:0 1rem;",
            "background:#0b1220;color:#f1f5f9} a{color:#38bdf8} li{margin:.5rem 0}</style></head><body>",
            "<h1>Open data &amp; offline pack hooks</h1>",
            "<p>SkyCache Nexus only attaches <strong>lawful open</strong> sources. "
            "Never commercial decrypt. Never satellite uplink.</p><ul>",
        ]
        for h in OPEN_HINTS:
            lines.append(
                f"<li><strong>{h['title']}</strong> "
                f"[{h['priority']}] - {h['note']}</li>"
            )
        lines.append(
            "</ul><p>Import packs: <code>skycache pipeline --plugin bulk_open_pack "
            "--uri /path/to/packs</code></p>"
            "<p>Legal: store-and-forward knowledge + community mesh - not free Starlink.</p>"
            "</body></html>"
        )
        index = dest / "index.html"
        index.write_text("\n".join(lines), encoding="utf-8")
        (dest / "hints.json").write_text(
            json.dumps({"hints": OPEN_HINTS, "generated_at": stamp.isoformat()}, indent=2),
            encoding="utf-8",
        )

        pkg = ContentPackage(
            id=pkg_id,
            kind="catalog",
            priority_class=PriorityClass.EDUCATION,
            title={"en": "Open data source hooks"},
            summary={
                "en": "Operator catalog of lawful offline and open-data attachment points."
            },
            languages=["en"],
            received_at=stamp,
            freshness_hours=24 * 30,
            size_bytes=index.stat().st_size,
            license="CC0-1.0",
            source=SourceInfo(
                type="operator_catalog",
                legal_note="hints only; no commercial streams",
                plugin=self.name,
            ),
            files=[
                ContentFile(path="index.html", mime="text/html", size_bytes=index.stat().st_size),
                ContentFile(
                    path="hints.json",
                    mime="application/json",
                    size_bytes=(dest / "hints.json").stat().st_size,
                    role="payload",
                ),
            ],
            tags=["open-data", "operator", "nexus"],
            icon="education",
        )
        (dest / "manifest.json").write_text(
            pkg.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Wrote open-data hints pack {pkg_id}",
            artifacts=[str(dest / "manifest.json")],
            suggested_package=pkg,
            metadata={"quality": 1.0},
        )
