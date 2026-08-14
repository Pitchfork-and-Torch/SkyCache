# Skybrary phased roadmap

Honest milestones. North star is maximal *feasible* open written heritage - never "everything ever written."

---

## Phase legend

| Code | Name | Status |
|------|------|--------|
| **S0** | Mission & architecture docs | **Done** |
| **S1** | Scaffold + sample open-text packs | **Done** |
| **S2** | Works catalog + FTS5 + facets | **Done (0.5)** |
| **S3** | Pack profiles + offline kits | **Partial (0.6)** - deepen in Wave 1 |
| **S4** | Online catalog portal UX | **Done (0.9 Skybrary Live)** |
| **S5** | Corpus pipelines at scale | **Partial (Wave 2.B2)** - folder + Gutenberg-style open import |
| **S6** | Integrity, verify, federation | Partial verify; federation next |
| **S7** | Open satellite RX deltas (subset) | Long-horizon |
| **0.6** | Full legal capability surface | **Live** |
| **N*** | SkyCache Nexus fabric | **Live** |

Unified next-step map: [`NEXT-STEPS.md`](NEXT-STEPS.md).

---

## S0 - Mission lock (current)

- [x] Map SkyCache as-built (architecture, legal, packaging, Nexus, community 0.4)  
- [x] `VISION-SKYBRARY.md`  
- [x] `skybrary-architecture.md`  
- [x] This roadmap  
- [x] `AGENTS.md` mission rules  
- [x] Website plan page + infographics  

**Exit:** Contributors share one mission language and legal rails.

---

## S1 - Scaffold + first open texts

**Goal:** Prove end-to-end *open text* -> package -> node portal without over-claiming scale.

Deliverables:

1. `skycache/skybrary/` package skeleton (models, license gate, integrity helpers)  
2. Sample **public-domain** mini-corpus packs (e.g. short Gutenberg-class works or curated PD excerpts with clear provenance)  
3. CLI: `skycache skybrary doctor` / `import-sample`  
4. Tests for license gate + checksum  
5. Docs: how to add a PD work  

**Exit:** `serve --sim` shows Skybrary sample texts; licenses inventory lists them.

---

## S2 - Works catalog + search

**Goal:** Work/Edition schema + SQLite FTS5 + faceted browse API.

- [x] `skybrary.db` works / editions / FTS5  
- [x] `/api/skybrary/works`, `/api/skybrary/facets`, `/api/skybrary/status`  
- [x] PWA **Library** tab + subject facets  
- [x] CLI `skycache skybrary search`  
- [x] Map editions to content packages  

**Exit:** Search returns PD sample works offline. **Met in 0.5.0.**

---

## S3 - Pack profiles for constrained nodes

**Goal:** Build size-bounded kits for villages (100 MB / 1 GB / 8 GB profiles).

- YAML pack profiles  
- Builder emits SkyCache packages  
- Priority integration so Emergency/Health still win disk pressure  

**Exit:** One-command literacy kit for a Pi node.

---

## S4 - Online portal (dual access)

**Goal:** Global web experience for connected users; same open content story.

- Expand skycache.jonbailey.xyz Skybrary section -> catalog browse (static or API-backed)  
- Download open packs  
- SEO/AEO for mission (without over-claim)  

**Exit:** Visitor understands Skybrary + can fetch a legal starter kit.

---

## S5 - Corpus pipelines

**Goal:** Repeatable, legal bulk ingest.

- [x] EPUB/TXT folder importer (`skybrary import-folder`, plugin `corpus_folder_import`) - license required  
- [x] Gutenberg-style open URL helper (`skybrary import-open` via open_fetch allowlist)  
- [x] Docs: `skybrary-corpus-import.md` (legal checklist; never pirate mirrors)  
- [x] Gutenberg open *catalog* adapter (batch from index; still operator-run)  
- [ ] Open-access science subset (arXiv/PMC where license permits)  
- [x] Provenance report generator for every batch  

**Exit:** Documented path to 10k+ open works on a server-class archive host (not on every Pi).

---

## S6 - Preservation & federation

**Goal:** Durability and multi-node archive health.

- Checksum verify CLI + doctor  
- Dedup by SHA-256  
- Federation of catalogs over Nexus gossip (manifest of works)  
- Disaster drill playbook (USB + mesh restore)  

**Exit:** Documented recovery of a node library from mule + peer without internet.

---

## S7 - Open satellite subsets (long horizon)

**Goal:** Where **legal and technical**, receive prioritized archive deltas via **existing receive-only** open paths - never commercial decrypt, never claim full-sky "everything."

Depends on: real open broadcast opportunities + size realism.

**Exit:** One demonstrated open RX path updating a small high-value subset (if/when available).

---

## Dependency on live SkyCache Nexus

Do not regress:

- Mesh / DTN / gateway / disaster mode  
- Community boards, ratings, license inventory (0.4)  
- Legal validators and honest banners  

Skybrary **rides** Nexus distribution; it is not a parallel network stack.

---

## Resource notes

| Host class | Expected content |
|------------|------------------|
| Village Pi (32 - 128 GB) | Profiles only (literacy + health + local) |
| Regional archive PC | Large open subsets |
| Online portal | Metadata + pack downloads; not necessarily full binary host |

---

## Communication discipline

| Say | Do not say |
|-----|------------|
| Open written knowledge archive | Complete archive of all books |
| Offline-first dual access | Free Starlink / free internet |
| Public domain & open licenses | "We host everything" |
| Aspirational north star | Shipped complete civilization dump |
