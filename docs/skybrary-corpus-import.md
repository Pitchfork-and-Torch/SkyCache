# Skybrary corpus import (legal bulk, operator-run)

Wave **2.B2** / roadmap **S5**: repeatable paths to import open text into SkyCache packages and the Skybrary works catalog.

**Status (v1.5.0 Bulk Open Corpus Ops):** unified `skybrary corpus` doctor/status/batch surface on top of folder, Gutenberg-catalog, OA science, and open-URL importers.

This is **not** a pirate downloader. SkyCache refuses unknown licenses, blocked hosts, and forbidden markers (warez, commercial decrypt, etc.).

---

## Corpus ops (v1.5.0) - preferred scale path

```bash
# Readiness (fixtures + license gate + samples)
skycache skybrary corpus doctor --data-dir data

# Local holdings snapshot (packages, licenses, passport gaps)
skycache skybrary corpus status --data-dir data

# Offline demo batch (samples + test fixtures only)
skycache skybrary corpus sample-manifest --out data/corpus-batch-demo.json
skycache skybrary corpus batch \
  --manifest data/corpus-batch-demo.json \
  --allow-local \
  --ingest \
  --data-dir data

# Dry-run a real operator catalog later
skycache skybrary corpus batch --manifest my-legal-batch.json --dry-run
```

Batch JSON schema: `skycache.corpus.batch.v1` with `jobs[]` of type
`folder` | `gutenberg_catalog` | `oa_science` | `open_url`.

Public site: https://skycache.jonbailey.xyz/corpus/

---

## Legal checklist (do this every batch)

1. **Confirm the work is open** - public domain, CC0, CC-BY / CC-BY-SA, Project Gutenberg license terms, government open access, or operator-authorized pack.  
2. **Never use pirate mirrors** - no libgen clones, warez, "free ebook" crack sites, commercial DRM dumps, or Kindle Unlimited rips.  
3. **Prefer primary hosts** on the open-fetch allowlist (e.g. `gutenberg.org`, `archive.org` open items, Wikimedia, Kiwix).  
4. **Pass `--license` explicitly** - every import command fails closed without it.  
5. **Respect robots / site terms** - operator-run, rate-limited, no bulk scrape of blocked hosts.  
6. **Record provenance** - packages store source path or URL + license in `manifest.json`.  
7. **Redistribution** - you are responsible for local law and license conditions (attribution for CC-BY, etc.).  
8. **Do not claim completeness** - bulk import builds a *legal subset*, not "every book ever written."

Allowed license markers (see `skycache/skybrary/license_gate.py`):  
`public domain`, `cc0`, `cc-by`, `cc-by-sa`, `project gutenberg`, `operator_supplied`, `open-access`, `mit`, `apache-2.0`, ...

Forbidden examples: `all rights reserved` commercial, `piracy`, `warez`, `kindle unlimited`, `decrypt`.

---

## Folder import (TXT / Markdown / HTML / EPUB)

Import a directory of files you already legally hold (USB stick, offline dump you prepared yourself, partner MoH pack, etc.).

```bash
# Build packages only
skycache skybrary import-folder ./my-open-texts \
  --license "public domain" \
  --out data/skybrary-build/corpus

# Build + register content catalog + Skybrary FTS
skycache skybrary import-folder ./my-open-texts \
  --license "public domain" \
  --subjects "literacy,literature_pd" \
  --creators "Various (public domain)" \
  --ingest \
  --data-dir data
```

Supported suffixes: `.txt`, `.md`, `.html`, `.htm`, `.epub`  
EPUB is treated as ZIP; plain text is extracted best-effort for FTS; the original `.epub` is kept in the package when present.

### Pipeline plugin

```bash
skycache pipeline --plugin corpus_folder_import \
  --uri ./my-open-texts \
  --option "license=public domain" \
  --option language=en \
  --data-dir data --sim
```

License option is **required**. Missing or forbidden licenses fail closed.

---

## Open URL import (Gutenberg-style, allowlisted)

Fetches **one** URL via the existing open-fetch allowlist (`skycache/capabilities/open_fetch.py`), then builds a Skybrary package.

```bash
# Example pattern only - use a URL you may legally download
skycache skybrary import-open \
  "https://www.gutenberg.org/files/XXXX/XXXX-0.txt" \
  --license "project gutenberg" \
  --title "Example PD work" \
  --id open-pg-xxxx \
  --ingest \
  --data-dir data
```

Rules:

- Host must be on the open allowlist (or operator extra hosts file).  
- HTTPS required for remote hosts.  
- Still requires `--license` (allowlist ≠ automatic redistributable).  
- Soft size cap (`--max-mb`, default 20).  
- **Never** point this at pirate mirrors; forbidden URL markers are refused.

Low-level fetch without packaging:

```bash
skycache open-fetch "https://www.gutenberg.org/..." --out /tmp/work.txt
```

---

## After import

```bash
skycache skybrary search liberty --data-dir data
skycache skybrary doctor --data-dir data
skycache licenses --summary --data-dir data
skycache skybrary pack --profile literacy-1gb --out data/packs/lit --data-dir data
```

PWA **Library** tab and `/api/skybrary/works` use the same FTS catalog.

---

## What this will not do

| Action | Status |
|--------|--------|
| Scrape pirate ebook sites | Refused |
| Download multi-GB corpora in one shot | Soft caps; operator must batch deliberately |
| Bypass DRM / commercial constellations | Out of scope forever |
| Auto-trust any URL on the internet | Allowlist only |
| Claim a complete world library | Forbidden messaging |

---

## Files

| Path | Role |
|------|------|
| `skycache/skybrary/corpus_import.py` | Folder + open-URL builders, Skybrary register |
| `skycache/skybrary/gutenberg_catalog.py` | Batch Gutenberg-style catalog adapter (v0.9) |
| `skycache/pipelines/plugins/corpus_folder_import.py` | Pipeline plugin |
| `skycache/skybrary/license_gate.py` | Fail-closed license check |
| `skycache/capabilities/open_fetch.py` | Allowlisted HTTPS fetch |

## Gutenberg open catalog adapter (batch, operator-run)  -  v0.9.0

Import many works from a **local catalog snapshot** (JSON/CSV), not an unrestricted scrape.

```bash
# Dry-run selection only
skycache skybrary import-gutenberg-catalog \
  --catalog ./my-pg-catalog.json \
  --max 25 --dry-run

# Sim/CI fixture (local text files, no network)
skycache skybrary import-gutenberg-catalog \
  --catalog tests/fixtures/gutenberg/catalog.json \
  --allow-local --max 5 --delay 0 \
  --out data/skybrary-build/gutenberg --ingest --data-dir data

# Live allowlisted hosts (rate-limited; respect robots/terms)
skycache skybrary import-gutenberg-catalog \
  --catalog ./pg-subset.json \
  --license "project gutenberg" \
  --lang en --max 20 --delay 1.5 \
  --out data/skybrary-build/gutenberg --ingest
```

JSON entry shape: `id`, `title`, `authors`, `language`, `subjects`, `text_url` (HTTPS on open-fetch allowlist, or local path with `--allow-local`).

Rules:

1. License still required (default `project gutenberg`)  -  fail closed.  
2. Remote URLs must pass open-fetch allowlist.  
3. Default delay between fetches; soft caps on max works and total bytes.  
4. Writes `provenance-gutenberg-batch.json` under the out directory.  
5. Never pirate mirrors. Not a complete Gutenberg dump claim.

Capability: `skybrary_gutenberg_catalog` in `skycache capabilities`.

See also: [`legal-ethics.md`](legal-ethics.md), [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md), [`open-sources.md`](open-sources.md), [`VISION-SKYBRARY.md`](VISION-SKYBRARY.md).

## Open-access science catalog (arXiv / PMC-style)  -  v0.9.1

`ash
skycache skybrary import-oa-science --catalog ./oa-catalog.json --dry-run
skycache skybrary import-oa-science --catalog tests/fixtures/oa_science/catalog.json --allow-local --ingest --data-dir data
`

Only rows with open-access / CC / public-domain licenses are imported. Hosts on open-fetch allowlist include arxiv.org, ncbi.nlm.nih.gov, europepmc.org. Never pirate mirrors.
