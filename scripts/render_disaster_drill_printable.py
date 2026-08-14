"""Render docs/disaster-drill.md to a partner-printable HTML page."""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "disaster-drill.md"


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_code = False
    for line in lines:
        if line.startswith("```"):
            if not in_code:
                out.append("<pre><code>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("> "):
            out.append(f"<blockquote>{html.escape(line[2:])}</blockquote>")
        elif line.startswith("- [ ] "):
            out.append(f'<li class="chk">&#9744; {html.escape(line[6:])}</li>')
        elif line.startswith("- "):
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.strip() == "---":
            out.append("<hr/>")
        elif line.strip() == "":
            out.append("")
        elif line.startswith("|"):
            out.append(f'<pre class="tbl">{html.escape(line)}</pre>')
        else:
            t = html.escape(line)
            t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
            t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
            out.append(f"<p>{t}</p>")
    return "\n".join(out)


def main() -> None:
    md = MD.read_text(encoding="utf-8")
    body = md_to_html(md)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SkyCache disaster mode drill playbook</title>
<meta name="description" content="Partner printable: SkyCache disaster mode drill. Local mesh and mule - not free commercial broadband."/>
<style>
body {{ font-family: system-ui, Segoe UI, sans-serif; max-width: 44rem; margin: 0 auto; padding: 1.5rem; line-height: 1.5; }}
h1 {{ font-size: 1.6rem; }}
h2 {{ margin-top: 1.6rem; border-top: 1px solid #8883; padding-top: 0.8rem; }}
pre, pre.tbl {{ background: #1113; padding: 0.75rem; overflow-x: auto; font-size: 0.85rem; }}
blockquote {{ border-left: 4px solid #0d9488; margin: 1rem 0; padding: 0.25rem 0.75rem; }}
li.chk {{ list-style: none; margin-left: 0; }}
.banner {{ background: #0f766e22; border: 1px solid #0d9488; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1.25rem; }}
@media print {{
  body {{ max-width: none; font-size: 11pt; }}
  .noprint {{ display: none; }}
  a {{ color: inherit; text-decoration: none; }}
}}
</style>
</head>
<body>
<p class="noprint"><a href="https://skycache.jonbailey.xyz/disaster/">Disaster page</a>
 · <a href="https://skycache.jonbailey.xyz/partners/">Partners</a>
 · <a href="#" onclick="window.print();return false;">Print</a></p>
<div class="banner"><strong>Partner printable drill</strong> - SkyCache disaster mode elevates emergency/health on local mesh + mule. Not free Starlink. Not medical advice. Not a complete archive.</div>
{body}
<p class="noprint" style="margin-top:2rem;opacity:.7">Source: SkyCache docs/disaster-drill.md · https://skycache.jonbailey.xyz/</p>
</body>
</html>
"""
    dests = [
        ROOT / "docs" / "disaster-drill-printable.html",
        Path.home() / "skycache-web" / "public" / "downloads" / "disaster-drill-printable.html",
    ]
    for d in dests:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(page, encoding="utf-8")
        print("wrote", d, d.stat().st_size)


if __name__ == "__main__":
    main()
