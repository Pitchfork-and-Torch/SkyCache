"""Dual-access catalog export for online portal + offline parity (v0.9.0).

Produces catalog.json (+ optional HTML) and optional starter kit packs for
skycache.jonbailey.xyz/library/. Metadata-first; binaries only as small
operator-built starter zips with license passports.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.pack_profile import list_profiles

CATALOG_SCHEMA = "skycache.skybrary.catalog.v2"

DISCLAIMER = (
    "OPEN CATALOG (Skybrary Live) - public-domain and openly licensed educational "
    "works only. Not a complete archive of written knowledge, not a full Project "
    "Gutenberg dump, and not free commercial satellite broadband or Starlink. "
    "Browse online; full FTS, packs, and village kits run on a local SkyCache node."
)

LEGAL_NOTE = (
    "Receive-only knowledge fabric + unlicensed community mesh. Confirm each "
    "license before redistribute. No commercial constellation decryption."
)


def _title_str(title: Any) -> str:
    if isinstance(title, dict):
        return str(title.get("en") or next(iter(title.values()), "") or "")
    return str(title or "")


def _summary_str(summary: Any) -> str:
    if isinstance(summary, dict):
        return str(summary.get("en") or next(iter(summary.values()), "") or "")
    return str(summary or "")


def _max_label(max_bytes: int | None) -> str:
    if not max_bytes:
        return "n/a"
    mb = max_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.0f} GB"
    if mb >= 1:
        return f"{mb:.0f} MB"
    return f"{max_bytes} B"


def work_to_export_row(w: dict[str, Any], *, site_base: str = "") -> dict[str, Any]:
    """Normalize a catalog work row into dual-access export shape."""
    editions = list(w.get("editions") or [])
    ed0 = editions[0] if editions else {}
    creators = list(w.get("creators") or w.get("authors") or [])
    title = _title_str(w.get("title"))
    summary = _summary_str(w.get("summary")) or title
    license_name = str(w.get("license") or "unknown")
    work_id = str(w.get("work_id") or "")
    package_id = w.get("package_id") or work_id
    fmt = str(ed0.get("format") or "txt")
    size_bytes = int(ed0.get("size_bytes") or 0)
    sha256 = str(ed0.get("sha256") or "")
    edition_id = str(ed0.get("edition_id") or (f"{work_id}-{fmt}" if work_id else ""))
    prov_raw = w.get("provenance") or {}
    if not isinstance(prov_raw, dict):
        prov_raw = {"note": str(prov_raw)}
    provenance = {
        "source": prov_raw.get("source") or "skybrary",
        "url": prov_raw.get("url") or prov_raw.get("provenance_url") or "",
        "note": prov_raw.get("note") or "",
        "retrieval_date": prov_raw.get("retrieval_date") or "",
    }
    passport = {
        "license": license_name,
        "provenance": provenance,
        "sha256": sha256,
        "redistribute": "yes" if "public domain" in license_name.lower() or "cc0" in license_name.lower() else "review",
        "note": "Confirm local law and license conditions before redistribute.",
    }
    return {
        "work_id": work_id,
        "title": title,
        "creators": creators,
        "authors": creators,  # back-compat for export HTML
        "languages": list(w.get("languages") or []),
        "subjects": list(w.get("subjects") or []),
        "license": license_name,
        "civilizational_tier": int(w.get("civilizational_tier") or 3),
        "summary": summary,
        "format": fmt,
        "edition_id": edition_id,
        "package_id": package_id,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "provenance": provenance,
        "passport": passport,
        "download": {
            "type": "node_or_cli",
            "cli_hint": f"python -m skycache skybrary search {work_id.split('-')[-1] if work_id else 'open'}",
            "path": "",
        },
        "cli_hint": f"python -m skycache skybrary search {title.split()[0].lower() if title else 'skybrary'}",
        "detail_path": f"/library/works/{work_id}/" if work_id else "/library/",
    }


def _pack_profiles_export() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in list_profiles():
        if p.get("dynamic") and p.get("id") != "language-xx":
            continue
        max_b = int(p.get("max_bytes") or 0)
        rows.append(
            {
                "id": p["id"],
                "max_bytes": max_b,
                "max_label": _max_label(max_b),
                "languages": list(p.get("languages") or []),
                "include_subjects": list(p.get("include_subjects") or []),
                "prefer_formats": list(p.get("prefer_formats") or []),
                "description": p.get("description") or "",
            }
        )
    return rows


def build_catalog_dict(
    sky: SkybraryCatalog,
    *,
    limit: int = 5000,
    site_base: str = "https://skycache.jonbailey.xyz",
    starter_kits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build in-memory dual-access catalog v2 (does not write files)."""
    # Raise search limit cap via list_works for full export
    works_raw = sky.list_works(limit=limit)
    slim = [work_to_export_row(w, site_base=site_base) for w in works_raw]
    facets = sky.facets()
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    built_day = built[:10]
    base = site_base.rstrip("/")

    return {
        "schema": CATALOG_SCHEMA,
        "version": __version__,
        "generated": built_day,
        "built_at": built,
        "work_count": len(slim),
        "source": "SkyCache Skybrary dual-access catalog (Skybrary Live)",
        "disclaimer": DISCLAIMER,
        "legal_note": LEGAL_NOTE,
        "legal": LEGAL_NOTE,
        "dual_access": {
            "online": f"{base}/library/",
            "offline": "skycache skybrary pack --profile literacy-1gb",
            "online_browse": f"{base}/library/",
            "note": "Same works online (browse) and offline (USB/mesh packs).",
        },
        "facets": {
            "languages": facets.get("languages") or {},
            "subjects": facets.get("subjects") or {},
            "licenses": facets.get("licenses") or {},
            "eras": facets.get("eras") or {},
        },
        "pack_profiles": _pack_profiles_export(),
        "profiles": _pack_profiles_export(),  # back-compat
        "starter_kits": starter_kits or [],
        "works": slim,
    }


def export_works_catalog(
    sky: SkybraryCatalog,
    out_dir: Path,
    *,
    limit: int = 5000,
    include_html: bool = True,
    site_base: str = "https://skycache.jonbailey.xyz",
    content_dir: Path | None = None,
    include_starter_kits: bool = False,
) -> dict[str, Any]:
    """Write catalog.json (+ optional index.html + starter kits) under out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    kits: list[dict[str, Any]] = []
    if include_starter_kits and content_dir:
        kits = export_starter_kits(content_dir, out_dir / "packs", sky=sky)

    catalog = build_catalog_dict(
        sky, limit=limit, site_base=site_base, starter_kits=kits
    )

    cat_path = out_dir / "catalog.json"
    cat_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # Site alias used by Next static site
    site_alias = out_dir / "skybrary-catalog.json"
    site_alias.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    html_path = None
    if include_html:
        html_path = out_dir / "index.html"
        html_path.write_text(
            _catalog_html(catalog, site_base=site_base), encoding="utf-8"
        )

    return {
        "ok": True,
        "out_dir": str(out_dir),
        "catalog_json": str(cat_path),
        "site_catalog_json": str(site_alias),
        "index_html": str(html_path) if html_path else None,
        "work_count": catalog["work_count"],
        "built_at": catalog["built_at"],
        "schema": CATALOG_SCHEMA,
        "starter_kits": kits,
    }


def export_starter_kits(
    content_dir: Path,
    packs_out: Path,
    *,
    sky: SkybraryCatalog | None = None,
) -> list[dict[str, Any]]:
    """Zip curated packages into small dual-access starter kits with passports."""
    content_dir = Path(content_dir)
    packs_out = Path(packs_out)
    packs_out.mkdir(parents=True, exist_ok=True)

    # id -> subject keywords to include
    kit_defs = [
        {
            "id": "literacy-starter",
            "title": "Literacy starter kit",
            "description": (
                "Public-domain literacy and civics samples for dual-access demo. "
                "Not a complete curriculum archive."
            ),
            "subjects_any": {
                "literacy",
                "literature_pd",
                "civics",
                "history_pd",
                "fable",
            },
            "max_packages": 8,
        },
        {
            "id": "emergency-health-sample",
            "title": "Emergency / health sample kit",
            "description": (
                "Educational historical health and emergency open samples only - "
                "not medical advice or diagnosis."
            ),
            "subjects_any": {
                "health_edu",
                "emergency",
                "medicine",
                "safety",
                "health",
            },
            "max_packages": 6,
        },
    ]

    # Index package dirs by id
    pkg_dirs: dict[str, Path] = {}
    if content_dir.is_dir():
        for d in content_dir.iterdir():
            if d.is_dir() and (d / "manifest.json").is_file():
                pkg_dirs[d.name] = d

    # Optional subject filter from skybrary catalog
    work_subjects: dict[str, set[str]] = {}
    if sky is not None:
        for w in sky.list_works(limit=5000):
            wid = w.get("work_id") or ""
            work_subjects[str(wid)] = set(w.get("subjects") or [])

    kits: list[dict[str, Any]] = []
    for kd in kit_defs:
        selected: list[Path] = []
        for pid, pdir in sorted(pkg_dirs.items()):
            subs = work_subjects.get(pid)
            if subs is None:
                # Fall back to manifest tags
                try:
                    man = json.loads((pdir / "manifest.json").read_text(encoding="utf-8-sig"))
                    tags = set(man.get("tags") or [])
                    # also subjects from work extra
                    extra = (man.get("source") or {}).get("extra") or {}
                    work = extra.get("work") or {}
                    tags |= set(work.get("subjects") or [])
                    subs = tags
                except (OSError, json.JSONDecodeError):
                    subs = set()
            if subs & kd["subjects_any"]:
                selected.append(pdir)
            if len(selected) >= int(kd["max_packages"]):
                break

        if not selected:
            continue

        zip_name = f"{kd['id']}.zip"
        zip_path = packs_out / zip_name
        passports: list[dict[str, Any]] = []
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for pdir in selected:
                for f in pdir.rglob("*"):
                    if f.is_file():
                        arc = f"{pdir.name}/{f.relative_to(pdir).as_posix()}"
                        zf.write(f, arcname=arc)
                try:
                    man = json.loads((pdir / "manifest.json").read_text(encoding="utf-8-sig"))
                    extra = (man.get("source") or {}).get("extra") or {}
                    passports.append(
                        {
                            "id": man.get("id") or pdir.name,
                            "title": _title_str(man.get("title")),
                            "license": man.get("license") or "public domain",
                            "sha256": (extra.get("sha256") or ""),
                            "provenance": {
                                "source": (man.get("source") or {}).get("type") or "skybrary",
                                "note": (man.get("source") or {}).get("legal_note") or "",
                            },
                            "redistribute": "yes",
                        }
                    )
                except (OSError, json.JSONDecodeError):
                    passports.append({"id": pdir.name, "license": "public domain"})

        passport_path = packs_out / f"{kd['id']}.passport.json"
        passport_doc = {
            "schema": "skycache.pack.passport.v1",
            "kit_id": kd["id"],
            "title": kd["title"],
            "description": kd["description"],
            "license_summary": "Public domain / open educational samples only",
            "package_count": len(selected),
            "packages": passports,
            "legal": (
                "Not medical advice. Not a complete archive. Confirm license before "
                "redistribute. Not free commercial broadband."
            ),
        }
        passport_path.write_text(
            json.dumps(passport_doc, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        license_html = packs_out / f"{kd['id']}-license.html"
        license_html.write_text(
            _kit_license_html(kd, passport_doc), encoding="utf-8"
        )
        size_bytes = zip_path.stat().st_size
        kits.append(
            {
                "id": kd["id"],
                "title": kd["title"],
                "description": kd["description"],
                "package_count": len(selected),
                "size_bytes": size_bytes,
                "download_path": f"/library/packs/{zip_name}",
                "passport_path": f"/library/packs/{kd['id']}.passport.json",
                "license_page": f"/library/packs/{kd['id']}-license.html",
                "cli_hint": f"skycache skybrary pack --profile {kd['id'] if kd['id'] != 'emergency-health-sample' else 'emergency-health'}",
            }
        )
    return kits


def _kit_license_html(kd: dict[str, Any], passport: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{_esc(p.get('id'))}</td><td>{_esc(p.get('title'))}</td>"
        f"<td>{_esc(p.get('license'))}</td></tr>"
        for p in (passport.get("packages") or [])
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>License passport - {_esc(kd.get("title"))}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:1.5rem auto;padding:0 1rem;line-height:1.5}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{border-bottom:1px solid #cbd5e1;padding:.4rem;text-align:left}}
.banner{{background:#eff6ff;border:1px solid #bfdbfe;padding:.75rem;border-radius:8px}}
</style></head><body>
<h1>{_esc(kd.get("title"))}</h1>
<div class="banner"><strong>License passport</strong> - open / public-domain educational samples only.
Not medical advice. Not a complete archive. Not free commercial broadband.</div>
<p>{_esc(kd.get("description"))}</p>
<table><thead><tr><th>Package</th><th>Title</th><th>License</th></tr></thead>
<tbody>{rows}</tbody></table>
<p style="color:#64748b;font-size:.85rem">{_esc(passport.get("legal"))}</p>
</body></html>
"""


def _esc(s: Any) -> str:
    return (
        str(s if s is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _catalog_html(catalog: dict[str, Any], *, site_base: str) -> str:
    """Searchable dual-access catalog HTML (client-side filter; no third-party JS)."""
    works = catalog.get("works") or []
    works_json = json.dumps(works, ensure_ascii=False)
    works_json_safe = works_json.replace("</", "<\\/").replace("<!--", "<\\!--")
    lang_opts: set[str] = set()
    lic_opts: set[str] = set()
    sub_opts: set[str] = set()
    for w in works:
        for lang in w.get("languages") or []:
            if lang:
                lang_opts.add(str(lang))
        lic = w.get("license")
        if lic:
            lic_opts.add(str(lic))
        for sub in w.get("subjects") or []:
            if sub:
                sub_opts.add(str(sub))
    lang_options = "\n".join(
        f'<option value="{_esc(x)}">{_esc(x)}</option>' for x in sorted(lang_opts)
    )
    lic_options = "\n".join(
        f'<option value="{_esc(x)}">{_esc(x)}</option>' for x in sorted(lic_opts)
    )
    sub_options = "\n".join(
        f'<option value="{_esc(x)}">{_esc(x)}</option>' for x in sorted(sub_opts)
    )
    ver = _esc(catalog.get("version") or "")
    built = _esc(catalog.get("built_at") or catalog.get("generated") or "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="description" content="Skybrary open works catalog - dual-access browse. Not complete. Not free commercial internet."/>
<title>Skybrary open catalog (v{ver})</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, sans-serif; margin: 1.25rem; color: #0f172a;
         max-width: 60rem; line-height: 1.45; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e2e8f0; background: #0b1220; }}
    th {{ background: #111827 !important; }}
    th, td {{ border-color: #1f2937 !important; }}
    .banner {{ background: #0f172a !important; border-color: #1e3a5f !important; }}
    input, select {{ background: #111827; color: #e2e8f0; border-color: #334155; }}
  }}
  h1 {{ font-size: 1.45rem; margin: 0 0 0.75rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th, td {{ border-bottom: 1px solid #e2e8f0; padding: 0.45rem 0.5rem; text-align: left;
            vertical-align: top; }}
  th {{ background: #f8fafc; position: sticky; top: 0; }}
  .banner {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 0.75rem 1rem;
             border-radius: 8px; margin-bottom: 1rem; font-size: 0.9rem; }}
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; margin: 0 0 1rem;
              align-items: end; }}
  .toolbar label {{ display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.75rem;
                    font-weight: 600; letter-spacing: 0.02em; color: #64748b; }}
  input[type="search"], select {{ min-height: 2.5rem; min-width: 8rem; padding: 0.35rem 0.55rem;
                                  border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }}
  input[type="search"] {{ min-width: 14rem; flex: 1; }}
  .meta {{ color: #64748b; font-size: 0.85rem; margin: 0 0 0.75rem; }}
  code {{ font-size: 0.8rem; }}
  .empty {{ color: #64748b; font-size: 0.9rem; padding: 0.75rem 0; }}
</style>
</head>
<body>
  <h1>Skybrary - open works catalog</h1>
  <div class="banner">
    Dual-access catalog v{ver}  |  built {built}.
    Not a complete library. Not free commercial internet.
    Live product: <a href="{_esc(site_base)}">{_esc(site_base)}</a>
  </div>
  <p class="meta">Offline packs: literacy-1gb, emergency-health, stem-2gb, language-xx via
    <code>skycache skybrary pack</code>. Same works online (browse) and offline (USB/mesh).</p>
  <div class="toolbar" role="search">
    <label>Search
      <input id="q" type="search" placeholder="Title, author, subject, work id..."
             autocomplete="off" enterkeyhint="search"/>
    </label>
    <label>Language
      <select id="lang"><option value="">All</option>
{lang_options}
      </select>
    </label>
    <label>Subject
      <select id="sub"><option value="">All</option>
{sub_options}
      </select>
    </label>
    <label>License
      <select id="lic"><option value="">All</option>
{lic_options}
      </select>
    </label>
  </div>
  <p class="meta" id="count" aria-live="polite"></p>
  <table>
    <thead><tr><th>Title</th><th>Languages</th><th>License</th><th>Work ID</th></tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <p id="empty" class="empty" hidden>No works match these filters.</p>
  <p style="color:#64748b;font-size:0.85rem;margin-top:1.5rem">
    {_esc(catalog.get("legal") or catalog.get("legal_note"))}
  </p>
  <script id="works-data" type="application/json">{works_json_safe}</script>
  <script>
  (function () {{
    var raw = document.getElementById('works-data').textContent;
    var works = [];
    try {{ works = JSON.parse(raw); }} catch (e) {{ works = []; }}
    var tbody = document.getElementById('rows');
    var qEl = document.getElementById('q');
    var langEl = document.getElementById('lang');
    var licEl = document.getElementById('lic');
    var subEl = document.getElementById('sub');
    var countEl = document.getElementById('count');
    var emptyEl = document.getElementById('empty');

    function esc(s) {{
      return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }}

    function render() {{
      var q = (qEl.value || '').trim().toLowerCase();
      var lang = langEl.value || '';
      var lic = licEl.value || '';
      var sub = subEl.value || '';
      var html = [];
      var shown = 0;
      for (var i = 0; i < works.length; i++) {{
        var w = works[i] || {{}};
        var title = w.title || w.work_id || '';
        var authors = (w.creators || w.authors || []).join(' ');
        var subjects = (w.subjects || []).join(' ');
        var langs = (w.languages || []).join(', ');
        var license = w.license || '';
        var wid = w.work_id || '';
        var hay = (title + ' ' + authors + ' ' + subjects + ' ' + wid + ' ' + langs + ' ' + license).toLowerCase();
        if (q && hay.indexOf(q) === -1) continue;
        if (lang && (w.languages || []).indexOf(lang) === -1) continue;
        if (lic && license !== lic) continue;
        if (sub && (w.subjects || []).indexOf(sub) === -1) continue;
        shown++;
        html.push('<tr><td>' + esc(title) + '</td><td>' + esc(langs) + '</td><td>' +
          esc(license) + '</td><td><code>' + esc(wid) + '</code></td></tr>');
      }}
      tbody.innerHTML = html.join('') || '';
      countEl.textContent = shown + ' of ' + works.length + ' works shown';
      emptyEl.hidden = shown > 0 || works.length === 0;
      if (works.length === 0) {{
        countEl.textContent = '0 works exported';
        emptyEl.hidden = true;
      }}
    }}
    qEl.addEventListener('input', render);
    langEl.addEventListener('change', render);
    licEl.addEventListener('change', render);
    subEl.addEventListener('change', render);
    render();
  }})();
  </script>
</body>
</html>
"""
