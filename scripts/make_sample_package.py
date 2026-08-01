#!/usr/bin/env python3
"""Generate demo content packages under samples/packages/."""

from __future__ import annotations

import json
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "samples" / "packages"


def write_png(path: Path, w: int = 320, h: int = 200, rgb: tuple[int, int, int] = (70, 130, 180)) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    r, g, b = rgb
    row = bytes([0] + [r, g, b] * w)
    raw = row * h
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def write_pkg(pkg: dict, html: str | None = None, png: bool = False) -> None:
    d = ROOT / pkg["id"]
    d.mkdir(parents=True, exist_ok=True)
    if html:
        (d / "index.html").write_text(html, encoding="utf-8")
    if png:
        write_png(d / "map.png", 320, 200, (30, 90, 160))
    total = 0
    files = []
    for f in pkg["files"]:
        fp = d / f["path"]
        size = fp.stat().st_size if fp.is_file() else 0
        total += size
        files.append({**f, "size_bytes": size})
    pkg["files"] = files
    pkg["size_bytes"] = total
    (d / "manifest.json").write_text(
        json.dumps(pkg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("wrote", pkg["id"])


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    write_pkg(
        {
            "id": "emergency-checklist-001",
            "kind": "html_pack",
            "priority_class": "emergency",
            "title": {
                "en": "Emergency checklist",
                "fr": "Liste d'urgence",
                "es": "Lista de emergencia",
                "sw": "Orodha ya dharura",
                "ar": "قائمة الطوارئ",
                "hi": "आपातकालीन सूची",
                "pt": "Lista de emergência",
            },
            "summary": {
                "en": "What to do first in a community emergency. Not a substitute for local authorities.",
                "fr": "Gestes prioritaires en urgence communautaire.",
            },
            "languages": ["en", "fr", "es", "sw", "ar", "hi", "pt"],
            "received_at": now,
            "freshness_hours": 8760,
            "license": "CC-BY-4.0",
            "source": {
                "type": "sample",
                "legal_note": "Sample open content for demo",
                "plugin": "sim_file",
            },
            "files": [{"path": "index.html", "mime": "text/html", "role": "payload"}],
            "tags": ["emergency", "safety"],
            "pinned": True,
            "icon": "emergency",
        },
        html="""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Emergency</title>
<style>body{font-family:system-ui,sans-serif;margin:1.2rem;line-height:1.5;max-width:40rem}h1{color:#b91c1c}li{margin:.5rem 0}</style>
</head><body>
<h1>Emergency checklist</h1>
<ol>
<li>Ensure people are safe. Move away from immediate danger.</li>
<li>Contact local authorities / clinic / community leaders.</li>
<li>Conserve phone battery; use SkyCache offline guides.</li>
<li>Boil or treat water if supply is uncertain.</li>
<li>Share verified information only - stop rumors.</li>
</ol>
<p><small>Demo content. Adapt to local emergency plans.</small></p>
</body></html>
""",
    )

    write_pkg(
        {
            "id": "health-ors-001",
            "kind": "html_pack",
            "priority_class": "health",
            "title": {
                "en": "Oral rehydration (ORS)",
                "fr": "Réhydratation orale",
                "es": "Rehidratación oral",
                "sw": "Maji ya chumvi na sukari",
                "hi": "ओआरएस",
                "pt": "Reidratação oral",
                "ar": "محلول الجفاف",
            },
            "summary": {
                "en": "Basic ORS education flyer. Not medical diagnosis.",
                "fr": "Fiche éducative SRO - pas un diagnostic médical.",
            },
            "languages": ["en", "fr", "es", "sw", "hi", "pt", "ar"],
            "received_at": now,
            "freshness_hours": 8760,
            "license": "CC-BY-4.0",
            "source": {
                "type": "sample",
                "legal_note": "Educational sample",
                "plugin": "sim_file",
            },
            "files": [{"path": "index.html", "mime": "text/html"}],
            "tags": ["health", "water"],
            "icon": "health",
        },
        html="""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ORS</title>
<style>body{font-family:system-ui,sans-serif;margin:1.2rem;line-height:1.5;max-width:40rem}h1{color:#047857}</style>
</head><body>
<h1>Oral rehydration</h1>
<p>When someone has diarrhea, fluids are critical. Seek clinic care for infants, blood in stool, or high fever.</p>
<ul>
<li>Use ORS sachets if available, mixed with safe water as directed.</li>
<li>If no sachet: follow local Ministry of Health guidance.</li>
<li>Continue breastfeeding for infants when recommended by a health worker.</li>
</ul>
<p><strong>This is general education, not a diagnosis or prescription.</strong></p>
</body></html>
""",
    )

    write_pkg(
        {
            "id": "education-reading-001",
            "kind": "html_pack",
            "priority_class": "education",
            "title": {
                "en": "Reading corner",
                "fr": "Coin lecture",
                "es": "Rincón de lectura",
                "sw": "Kona ya kusoma",
                "hi": "पठन कोना",
                "pt": "Canto de leitura",
                "ar": "ركن القراءة",
            },
            "summary": {
                "en": "Short literacy demo. Replace with Kiwix ZIM packs in production.",
            },
            "languages": ["en", "fr", "es", "sw"],
            "received_at": now,
            "freshness_hours": 8760,
            "license": "CC-BY-4.0",
            "source": {
                "type": "sample",
                "legal_note": "Sample open content",
                "plugin": "sim_file",
            },
            "files": [{"path": "index.html", "mime": "text/html"}],
            "tags": ["education", "literacy"],
            "icon": "education",
        },
        html="""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reading</title>
<style>body{font-family:Georgia,serif;margin:1.2rem;line-height:1.6;max-width:36rem}h1{font-family:system-ui}</style>
</head><body>
<h1>The well and the school</h1>
<p>Every morning, Amina walked past the well to the school. The radio said the weather would be dry this week.</p>
<p>Her teacher said: knowledge is a well that does not run dry when we share it.</p>
<p><em>Demo story. Load Wikipedia ZIM via Kiwix for real libraries.</em></p>
</body></html>
""",
    )

    write_pkg(
        {
            "id": "agriculture-soil-001",
            "kind": "html_pack",
            "priority_class": "agriculture",
            "title": {
                "en": "Soil cover tips",
                "fr": "Couverture du sol",
                "es": "Cobertura del suelo",
                "sw": "Kufunika udongo",
                "pt": "Cobertura do solo",
                "hi": "मिट्टी ढकना",
            },
            "summary": {
                "en": "Simple mulching and soil-cover tips for smallholders.",
            },
            "languages": ["en", "fr", "es", "sw", "pt", "hi"],
            "received_at": now,
            "freshness_hours": 8760,
            "license": "CC-BY-4.0",
            "source": {
                "type": "sample",
                "legal_note": "Sample open content",
                "plugin": "sim_file",
            },
            "files": [{"path": "index.html", "mime": "text/html"}],
            "tags": ["agriculture", "soil"],
            "icon": "agriculture",
        },
        html="""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Soil</title>
<style>body{font-family:system-ui,sans-serif;margin:1.2rem;line-height:1.5;max-width:40rem}h1{color:#854d0e}</style>
</head><body>
<h1>Keep the soil covered</h1>
<ul>
<li>Mulch with dry leaves or crop residue to reduce evaporation.</li>
<li>Intercrop where local practice supports it.</li>
<li>Watch SkyCache weather images before planting after dry spells.</li>
<li>Ask extension officers for crop varieties suited to your region.</li>
</ul>
</body></html>
""",
    )

    write_pkg(
        {
            "id": "weather-demo-001",
            "kind": "weather_image",
            "priority_class": "weather",
            "title": {
                "en": "Demo weather map",
                "fr": "Carte météo démo",
                "es": "Mapa del tiempo (demo)",
                "sw": "Ramani ya hali ya hewa",
                "pt": "Mapa do tempo (demo)",
            },
            "summary": {
                "en": "Placeholder weather image. Live systems use SatDump APT/LRPT/HRIT products.",
            },
            "languages": ["en", "fr", "es", "sw", "pt"],
            "received_at": now,
            "freshness_hours": 12,
            "license": "CC-BY-4.0",
            "source": {
                "type": "sample",
                "legal_note": "Synthetic demo image, not a real satellite pass",
                "plugin": "sim_file",
            },
            "files": [
                {"path": "map.png", "mime": "image/png"},
                {"path": "index.html", "mime": "text/html"},
            ],
            "tags": ["weather", "demo"],
            "icon": "weather",
        },
        html="""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weather</title>
<style>body{font-family:system-ui,sans-serif;margin:1rem;text-align:center}img{max-width:100%;height:auto;border-radius:12px}</style>
</head><body>
<h1>Demo weather</h1>
<img src="map.png" alt="Demo weather map">
<p>Live hubs replace this with SatDump output.</p>
</body></html>
""",
        png=True,
    )

    write_pkg(
        {
            "id": "maps-local-001",
            "kind": "html_pack",
            "priority_class": "maps",
            "title": {
                "en": "Community map notes",
                "fr": "Notes de carte",
                "es": "Notas del mapa",
                "sw": "Maelezo ya ramani",
                "pt": "Notas do mapa",
            },
            "summary": {
                "en": "Placeholder for offline maps (OSM extracts / MBTiles in production).",
            },
            "languages": ["en", "fr", "es", "sw", "pt"],
            "received_at": now,
            "freshness_hours": 8760,
            "license": "CC-BY-4.0",
            "source": {
                "type": "sample",
                "legal_note": "Sample open content",
                "plugin": "sim_file",
            },
            "files": [{"path": "index.html", "mime": "text/html"}],
            "tags": ["maps"],
            "icon": "maps",
        },
        html="""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maps</title>
<style>body{font-family:system-ui,sans-serif;margin:1.2rem;line-height:1.5;max-width:40rem}</style>
</head><body>
<h1>Maps</h1>
<p>Production nodes can host offline map tiles and community POIs (clinic, school, water points).</p>
<p>This demo page marks the category for the portal UI.</p>
</body></html>
""",
    )

    print("done")


if __name__ == "__main__":
    main()
