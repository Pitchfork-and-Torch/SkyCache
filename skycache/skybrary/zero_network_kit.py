"""Zero-network phone kit - no Wi-Fi and no cell required to *read*.

Physics: a device with zero radios cannot *download* anything in the field.
It can still *use* the three demo texts if they were placed on storage by:

  - USB cable / OTG (hub or PC -> phone)
  - microSD / shared drive
  - Bluetooth file send from a peer that already has the kit
  - Factory / pre-deploy copy onto the device before departure

This module builds a self-contained kit:
  - READ-OFFLINE.html  - single file, works offline (file://), large type reader
  - texts/*.txt        - plain files for any reader app
  - README.txt         - how to load without Wi-Fi or cell

Legal: public-domain curated samples only. Not free commercial broadband.
Not a complete archive.
"""

from __future__ import annotations

import html
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.skybrary.sample_corpus import SAMPLES

KIT_FORMAT = "skycache-zero-network-kit-v1"
KIT_ZIP_NAME = "skycache-zero-network-demo-kit.zip"
HTML_NAME = "READ-OFFLINE.html"


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def build_offline_reader_html(
    *,
    generated_at: str | None = None,
) -> str:
    """Single-file offline reader with all demo texts embedded (no network)."""
    stamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    works_js: list[str] = []
    nav_buttons: list[str] = []
    articles: list[str] = []

    for i, s in enumerate(SAMPLES):
        wid = s["work_id"]
        title = s["title"].get("en", wid)
        creators = ", ".join(s.get("creators") or [])
        body = s["body"]
        works_js.append(
            "{"
            f"id:{json.dumps(wid)},"
            f"title:{json.dumps(title)},"
            f"creators:{json.dumps(creators)}"
            "}"
        )
        nav_buttons.append(
            f'<button type="button" class="nav-btn" data-i="{i}" id="nav{i}">'
            f"{_esc(title)}</button>"
        )
        articles.append(
            f'<article class="work" id="work{i}" hidden>'
            f"<h1>{_esc(title)}</h1>"
            f'<p class="meta">{_esc(creators)}  |  public domain sample  |  {_esc(wid)}</p>'
            f'<pre class="body">{_esc(body)}</pre>'
            f"</article>"
        )

    nav = "\n".join(nav_buttons)
    arts = "\n".join(articles)
    works_arr = ",".join(works_js)

    # Self-contained: no external CSS/JS URLs
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="color-scheme" content="dark light" />
<meta name="description" content="SkyCache zero-network demo reader - no Wi-Fi or cell required" />
<title>SkyCache  |  Offline demos (no Wi-Fi / no cell)</title>
<style>
:root {{
  --bg: #0b1220; --card: #121a2b; --text: #f1f5f9; --muted: #94a3b8;
  --accent: #5eead4; --border: #1e293b; --touch: 48px;
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5;
}}
body {{ max-width: 40rem; margin: 0 auto; padding: 0 0 3rem; }}
header {{
  position: sticky; top: 0; z-index: 5;
  background: rgba(11,18,32,0.95); border-bottom: 1px solid var(--border);
  padding: 0.75rem 1rem;
}}
header h1 {{ margin: 0; font-size: 1.1rem; color: var(--accent); }}
header p {{ margin: 0.35rem 0 0; font-size: 0.85rem; color: var(--muted); }}
.banner {{
  margin: 0.75rem 1rem; padding: 0.75rem 1rem; border-radius: 12px;
  background: #0c4a6e; border: 1px solid #0e7490; font-size: 0.9rem;
}}
.nav {{
  display: flex; flex-direction: column; gap: 0.5rem;
  padding: 0 1rem 1rem;
}}
.nav-btn {{
  min-height: var(--touch); text-align: left; padding: 0.75rem 1rem;
  border-radius: 12px; border: 1px solid var(--border);
  background: var(--card); color: var(--text); font-size: 1rem; cursor: pointer;
}}
.nav-btn.active, .nav-btn:focus {{ border-color: var(--accent); outline: none; }}
.toolbar {{
  display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0 1rem 0.75rem;
  position: sticky; top: 4.5rem; background: var(--bg); z-index: 4;
}}
.toolbar button {{
  min-height: var(--touch); min-width: var(--touch); padding: 0 0.85rem;
  border-radius: 10px; border: 1px solid var(--border);
  background: var(--card); color: var(--text); font-size: 1rem; cursor: pointer;
}}
.work {{ padding: 0 1rem 2rem; }}
.work h1 {{ font-size: 1.35rem; margin: 0 0 0.35rem; color: var(--accent); }}
.work .meta {{ color: var(--muted); font-size: 0.85rem; margin: 0 0 1rem; }}
.work .body {{
  white-space: pre-wrap; word-wrap: break-word;
  font-family: Georgia, "Times New Roman", serif;
  font-size: var(--fs, 1.2rem); line-height: 1.55;
  margin: 0; background: var(--card); padding: 1rem; border-radius: 12px;
  border: 1px solid var(--border);
}}
footer {{
  padding: 1rem; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border);
}}
</style>
</head>
<body>
<header>
  <h1>SkyCache  |  Offline demos</h1>
  <p>No Wi-Fi  |  No cell  |  Public-domain samples only</p>
</header>
<div class="banner" role="note">
  This file works with <strong>zero network</strong>. Open it from Files / Downloads
  (or after USB / Bluetooth / SD copy). Not free commercial satellite broadband.
  Not a complete archive. Generated { _esc(stamp) }.
</div>
<div class="nav" id="nav" role="navigation" aria-label="Works">
{nav}
</div>
<div class="toolbar" id="toolbar" hidden>
  <button type="button" id="btnBack" aria-label="Back to list">← List</button>
  <button type="button" id="btnSmaller" aria-label="Smaller text">A−</button>
  <button type="button" id="btnLarger" aria-label="Larger text">A+</button>
</div>
{arts}
<footer>
  SkyCache zero-network kit ({KIT_FORMAT}). Legal: receive-only satellite in the full product;
  this kit is local files only. https://github.com/Pitchfork-and-Torch/SkyCache
</footer>
<script>
(function () {{
  var works = [{works_arr}];
  var fs = 1.2;
  var current = -1;
  function $(id) {{ return document.getElementById(id); }}
  function showList() {{
    current = -1;
    $("toolbar").hidden = true;
    works.forEach(function (_, i) {{
      var el = $("work" + i);
      if (el) el.hidden = true;
      var b = $("nav" + i);
      if (b) b.classList.remove("active");
    }});
    $("nav").hidden = false;
    window.scrollTo(0, 0);
  }}
  function showWork(i) {{
    if (i < 0 || i >= works.length) return;
    current = i;
    $("nav").hidden = true;
    $("toolbar").hidden = false;
    works.forEach(function (_, j) {{
      var el = $("work" + j);
      if (el) el.hidden = j !== i;
    }});
    window.scrollTo(0, 0);
  }}
  function applyFs() {{
    document.documentElement.style.setProperty("--fs", fs + "rem");
  }}
  works.forEach(function (_, i) {{
    var b = $("nav" + i);
    if (b) b.addEventListener("click", function () {{ showWork(i); }});
  }});
  $("btnBack").addEventListener("click", showList);
  $("btnSmaller").addEventListener("click", function () {{
    fs = Math.max(0.9, fs - 0.125); applyFs();
  }});
  $("btnLarger").addEventListener("click", function () {{
    fs = Math.min(2.0, fs + 0.125); applyFs();
  }});
  applyFs();
}})();
</script>
</body>
</html>
"""


def kit_readme() -> str:
    return f"""SkyCache zero-network demo kit
===============================
Format: {KIT_FORMAT}

GOAL
----
Read the curated public-domain sample set on a phone that has
  - NO Wi-Fi
  - NO cell / mobile data

HOW (physics)
-------------
You cannot download over the air without a radio. This kit is
**local files**. Put them on the phone by any of:

  1. USB / OTG cable from a PC or SkyCache hub
  2. microSD card (if the phone has a slot)
  3. Bluetooth file send from another device that already has the kit
  4. Copy before you leave town (pre-deploy)

Then open READ-OFFLINE.html in the phone browser or a file viewer.
Airplane mode is fine. No network is used.

CONTENTS
--------
  READ-OFFLINE.html     All-in-one offline reader (open this first)
  texts/*.txt           Plain text of each work
  kit-manifest.json     Integrity / inventory
  README.txt            This file

WORKS
-----
This kit embeds the full curated public-domain sample set (see kit-manifest.json
work_count). Titles appear in READ-OFFLINE.html and under texts/*.txt.

LEGAL
-----
Public domain / educational samples only. Not medical advice.
Not a complete archive of written knowledge.
Not free Starlink or commercial satellite broadband.

Hub software: https://github.com/Pitchfork-and-Torch/SkyCache
Build kit:    skycache library zero-network --out ./kit
              skycache skybrary zero-network-kit --out ./kit
"""


def write_zero_network_kit(out_dir: Path) -> dict[str, Any]:
    """Write kit directory; return manifest dict."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = out_dir / "texts"
    texts.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    html_body = build_offline_reader_html(generated_at=stamp)
    (out_dir / HTML_NAME).write_text(html_body, encoding="utf-8", newline="\n")
    (out_dir / "README.txt").write_text(kit_readme(), encoding="utf-8", newline="\n")

    files: list[dict[str, Any]] = [
        {"path": HTML_NAME, "role": "offline_reader"},
        {"path": "README.txt", "role": "instructions"},
    ]
    for s in SAMPLES:
        wid = s["work_id"]
        rel = f"texts/{wid}.txt"
        body = s["body"]
        # binary-stable newlines for hashing consistency across OS
        (texts / f"{wid}.txt").write_bytes(body.replace("\r\n", "\n").encode("utf-8"))
        files.append(
            {
                "path": rel,
                "work_id": wid,
                "title": s["title"].get("en", wid),
                "bytes": len(body.encode("utf-8")),
                "role": "work_text",
            }
        )

    manifest = {
        "format": KIT_FORMAT,
        "generated_at": stamp,
        "work_count": len(SAMPLES),
        "works": [
            {
                "work_id": s["work_id"],
                "title": s["title"].get("en", s["work_id"]),
                "creators": s.get("creators") or [],
                "license": "public domain",
            }
            for s in SAMPLES
        ],
        "files": files,
        "how_to_load": [
            "USB/OTG: copy this folder to phone storage, open READ-OFFLINE.html",
            "microSD: copy folder to card, open from Files app",
            "Bluetooth: send READ-OFFLINE.html (or whole zip) from a peer device",
            "Pre-deploy: copy before leaving connectivity",
        ],
        "honest": (
            "Zero network to read. Transfer requires USB, SD, Bluetooth, or prior copy. "
            "Not free commercial broadband. Curated PD samples only."
        ),
    }
    (out_dir / "kit-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    files.append({"path": "kit-manifest.json", "role": "manifest"})
    manifest["files"] = files
    # rewrite with complete files list
    (out_dir / "kit-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def build_zero_network_zip_bytes() -> tuple[bytes, dict[str, Any]]:
    """Build kit in memory zip (for API download / USB prep on a hub that has power)."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="skycache-zn-") as tmp:
        root = Path(tmp) / "skycache-zero-network-demo-kit"
        meta = write_zero_network_kit(root)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in root.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(root.parent)).replace("\\", "/"))
        return buf.getvalue(), meta


def ensure_repo_sample_kit(repo_samples: Path) -> Path:
    """Write/update samples/phone-zero-network for offline distribution in the repo."""
    dest = Path(repo_samples) / "phone-zero-network"
    write_zero_network_kit(dest)
    return dest
