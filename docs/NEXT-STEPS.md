# SkyCache + Skybrary - next great updates

**One project.** Field runtime (SkyCache / Nexus) + civilizational open archive (Skybrary) share one repo, one legal spine, one site.

**As of v1.33.0 (Open Resilience Wave):** curated dual-access corpus **78** works (STEM/civics/health waves); disaster/power-critical prioritizer protects emergency+health; `open_fta_sim` + plugin extension docs; `archive-100mb`/`archive-1gb` + `library pack-budgets`; survival-first `priority_works_delta` federation. See `docs/OPEN-RESILIENCE-WAVE.md`.

**As of v1.0.0 (Skybrary Resilience Fabric):** scheduled bit-rot doctor (`--verify --record` + systemd/cron templates), multi-node works federation sim (`nexus federation`), local ops metrics (no cloud), threat-model one-pager. **As of v0.9.2:** downloadable golden-SD kit hosted path, dual-radio validation pack (all board models), MBTiles via blob store (no multi-GB in git), CSS pagination reader. **As of v0.9.1 (field depth):** Pi bake plan, batman day-one OOB, OA science import, EPUB/chapter reader, blob store, maps-offline profile, partner kits. **As of v0.9.0 (Skybrary Live):** Wave 2 dual-access portal complete + corpus substance advanced.  
Online /library/ portal (search, facets, work detail + license passports, starter kit downloads), catalog export v2, curated PD corpus, Gutenberg catalog adapter (operator-run), literacy-starter packs, APIs for catalog.json + kits.  
Village Ready field stack from 0.8 remains. **Site:** always redeploy https://skycache.jonbailey.xyz with big software ships.

---

## Where we are (honest)

| Layer | Strength | Gap |
|-------|----------|-----|
| Legal rails | Strong validators + capability matrix | Operator education in more languages |
| Offline node | Solid sim + packages + PWA | One-click Pi image still thin |
| Nexus fabric | Sim multi-node proven | Real batman-adv "works out of box" |
| Skybrary | S0 - S2 + basic S3 profiles | Real corpora, online catalog, federation |
| Online dual access | Marketing + plan page | Live browseable global catalog |
| Ops | CLI rich | Telemetry/fleet of villages (privacy-preserving) |

---

## Theme A - Make a village node irresistible (field product)

### A1. Golden path installer (highest leverage) - **shipped in 0.6.1**
- `install-village-fabric.sh` + `first-boot-wizard.sh` + `skycache first-boot`: portal up, samples + Skybrary loaded, PIN required (not default), legal mode, capabilities print.
- Docs: `docs/first-boot.md`. Hostapd AP still manual (SSID hint from wizard).
- **Remaining:** single SD image / golden Raspberry Pi image bake.
- **Why:** Most impact is adoption, not features.

### A2. Reading experience for texts
- **Done (txt/html baseline):** In-PWA reader opens `work.txt` / `index.html` from Library; large type; local scroll bookmark; prev/next; SW content cache.
- Still open: light epub path if needed; longer-form chapter nav for multi-file packs.
- **Why:** Library tab finds works; readers need a book UX.

### A3. Maps + health offline depth
- Offline maps pack profile (OpenStreetMap extracts / MBTiles where license OK).
- Curated MoH/WHO-open health pack pipeline (license inventory automatic).
- **Why:** Emergency/Health still outrank literature when life is on the line.

### A4. Solar / power UX polish - **shipped in 0.8.0**
- `GET /api/power/guidance` + printable maintainer sheet; doctor shows rough hours until ECO.
- **Remaining:** site-specific Wh calibration UI; INA219 field wiring guide polish.
- **Why:** Nodes die from power ignorance, not software.

### A5. Disaster mode drills - **docs shipped**
- Scripted drill: disaster ON -> emergency flood -> mule export -> second node restore -> partner checklist.
- **Playbook:** [`disaster-drill.md`](disaster-drill.md)  |  lab helper `deploy/disaster-drill-sim.sh`
- **Why:** Trust with NGOs is demonstrated, not claimed.
- **Still open:** printable PDF export / partner-kit packaging (D4).

---

## Theme B - Skybrary as a real library (archive product)

### B1. Online dual-access portal (S4) - **foundation shipped in 0.8.0; search UI 2026-07-28**
- `skycache skybrary export-catalog` -> static `catalog.json` + `index.html` for `/library/`.
- **2026-07-28:** export `index.html` is now **searchable** (client-side query + language/license filters; no third-party JS).
- **Remaining:** publish export onto skycache.jonbailey.xyz `/library/`, R2 pack downloads with license pages, library subdomain.
- **Why:** Dual access is incomplete without a great connected experience.

### B2. Corpus pipelines (S5) - legal bulk
- [x] EPUB/TXT folder importer -> Work/Edition + FTS (`import-folder`, `corpus_folder_import`).
- [x] Gutenberg-style single open-URL helper (`import-open` + open_fetch allowlist).
- [x] Docs: `docs/skybrary-corpus-import.md`.
- [ ] Gutenberg open *catalog* adapter (batch index; respect robots/terms; operator-run).
- [ ] Open-access science subset (arXiv/PMC *where license permits packaging*).
- [ ] Provenance report generator for every batch.
- **Why:** Samples prove the path; pipelines create civilizational scale.

### B3. Pack profiles 2.0 - **shipped in 0.8.0**
- Profiles: `emergency-health`, `literacy-1gb`, `stem-2gb`, `local-heritage`, `language-<code>`.
- Priority integration: `reserve_fraction` so literature never starves emergency packs on small disks.
- Signed profile manifests (`root_sha256` + sidecar).
- **Why:** Villages need "one USB = one curriculum," not 10k loose files.

### B4. Multilingual works
- Prefer works with multiple languages; UI already multi-lang - align catalog subjects i18n.
- Partner translations (CC) for health + literacy first.
- **Why:** Most of humanity does not read English first.

### B5. Integrity & bit-rot (S6) - **shipped in 1.0.0 (schedule surface)**
- `skybrary doctor --verify --record` persists `data/ops/bitrot-last.json`; schedule freshness in doctor/ops.
- systemd timer + cron templates: `skycache bitrot install-templates` / `deploy/bitrot/`.
- Content-addressed blobs: **shipped in 0.9.1** (`skycache blobs`).
- **Remaining:** operator Wh calibration UI; hardware field soak reports.
- **Why:** A library that silently corrupts is worse than a small honest one.

### B6. Federation of catalogs (S6) - **sim production surface in 1.0.0**
- Gossip works manifests over Nexus (not only package ids) - fabric + `nexus federation` multi-node sim.
- Delta sync of high-tier works across village mesh (metadata + package pull when peer content root present).
- **Remaining:** bandwidth-aware partial gossip for huge catalogs; hardware mesh soak.
- **Why:** One clinic's download becomes the school's library overnight.

---

## Theme C - Distribution fabric that feels like infrastructure

### C1. Real mesh day-one - **docs shipped (hardware video still open)**
- Field playbook: 2-node validation, `legal_rf_mode`, failure modes in [`mesh-deployment.md`](mesh-deployment.md) + printable [`mesh-field-checklist.md`](mesh-field-checklist.md).
- OpenWrt + Pi dual-radio **on-device** proof + video/GIF for maintainers still open.
- Captive portal + seamless SSID across buildings (examples under `deploy/`).
- **Why:** Nexus sim is green; field mesh is the product.

### C2. Gateway ethics automation - **shipped in 0.8.0**
- Open-mirror presets + admin daily quota + local pull receipts.
- **Remaining:** preset -> open-fetch one-click with license passport auto-fill.
- **Why:** Shared metered links need social trust.

### C3. Handoff that non-geeks use
- QR code on node: "Copy library to phone."
- Handoff bundle already exists - wrap with one button in admin.
- **Why:** USB is powerful only if discoverable.

### C4. Open RX deltas (S7, long)
- If/when a lawful free-to-air content broadcast path exists: receive prioritized *small* archive deltas only.
- **Why:** Completes "sky" in Skybrary without commercial uplink fantasies.

---

## Theme D - Trust, law, and global adoption

### D1. License passport - **0.8.0 printable export**
- Passport APIs + PWA chips (prior); inventory printable HTML -> browser Save as PDF (`licenses --html`, `/api/licenses/export`); provenance batch CLI.
- **Why:** Opens doors with ministries and universities.

### D2. Capability matrix as onboarding
- First-run: show capabilities ON/OFF in local language; link to legal pathways doc.
- **Why:** Operators self-audit before RF goes live.

### D3. Threat model one-pager - **shipped in 1.0.0**
- [`threat-model.md`](threat-model.md): assets, refuse list, trust boundaries, residual risks.
- **Why:** Clear enemies of the mission reduce bad PRs.

### D4. Partner kits
- NGO pilot kit: BOM + training half-day + sample content + legal one-pager.
- University kit: contribute PD corpus + student maintainer course.
- **Why:** Growth is institutional, not viral app-store.

### D5. Site always ships with software
- Standing rule: every major version updates skycache.jonbailey.xyz (already in skill + AGENTS.md).
- Changelog + Skybrary plan page stay current.
- **Why:** Public understanding lags private commits otherwise.

---

## Theme E - Engineering quality (keeps the cathedral standing)

### E1. Unified product naming in UI
- "SkyCache" node chrome + "Skybrary" library section (already) - tighten copy so users feel one product.
- Optional brand mark: SkyCache powered by / includes Skybrary.

### E2. Performance on Pi
- Memory budgets, lazy FTS, limit concurrent gateway pulls.
- **Why:** 0.6 features must fit 2 - 4 GB RAM devices.

### E3. Test matrix growth
- E2E: samples -> FTS -> pack -> handoff -> second node ingest.
- Sim fabric + skybrary in one pytest scenario.
- **Why:** One project = one regression net.

### E4. Observability without surveillance - **local surface in 1.0.0**
- Local-only metrics: disk, SOC, peer count, pack freshness (`ops status`, `/api/ops/local`).
- Optional anonymized fleet heartbeat remains default **off**.
- **Why:** Privacy rails are part of the mission.

---

## Prioritized next steps (recommended order)

### Wave 1 - "Ship a village in a weekend" (1 - 2 sprints)

1. **A1 Golden installer** + first-boot wizard  
2. **A2 In-PWA reader** for Skybrary texts - **baseline shipped** (txt/html; epub optional later)  

3. **B3 Pack profiles 2.0** + admin "Build USB kit" button  
4. **C3 Handoff one-button** in admin  
5. **A5 Disaster drill playbook** - [`disaster-drill.md`](disaster-drill.md) ✅ docs  
6. **Site** release notes 0.6+ and "Get started" path  

**Exit:** Untrained volunteer builds a demo node from docs in <2 hours.

### Wave 2 - "Dual access feels real" (2 - 4 sprints)

1. **B1 Online catalog** on skycache.jonbailey.xyz (or library subdomain)  
2. **B2 Gutenberg/EPUB pipeline** (operator-run, legal)  
3. **C1 Field mesh playbook** - docs ✅ ([`mesh-deployment.md`](mesh-deployment.md), [`mesh-field-checklist.md`](mesh-field-checklist.md)); hardware/video still open  
4. **D1 License passport** in PWA + export  
5. **E3 E2E federation test** (mule + mesh)  

**Exit:** Connected user downloads a literacy kit; offline node serves same works.

### Wave 3 - "Civilizational scale without lies" (ongoing)

1. **B5 Bit-rot doctor** scheduled - **1.0.0**  
2. **B6 Catalog federation** over Nexus - **1.0.0 sim surface**  
3. **A3 Health/maps deep packs** (maps-offline + MBTiles path exist; deeper MoH pipelines open)  
4. **A5 Disaster drill** with partners (playbook ready - run with civil protection)  
5. **C4 Open RX deltas** only if lawful path appears  
6. **D4 Partner kits** with real pilots  
7. **C1** On-device dual-radio video proof per board  

**Exit:** Multi-village mesh shares high-tier open works; public story remains honest.

---

## Decision filters (use on every idea)

| Question | Required answer |
|----------|-----------------|
| Legal open or authorized? | Yes |
| Helps offline dignity? | Yes |
| Works on Pi-class + solar? | Yes or graceful degrade |
| Over-claims completeness or free internet? | Must be No |
| Local maintainer can operate after we leave? | Yes |
| Site/docs updated when we ship? | Yes |

---

## Explicit backlog "not now"

- Commercial constellation decrypt or sat uplink productization  
- Full internet proxy for villages  
- Cloud-required accounts  
- Hoarding copyrighted commercial ebooks "for the library"  
- Global user tracking  

---

## North star (unchanged)

**Protect the future of humanity by building the Sky Library** - dual access, legal open knowledge, catastrophe-aware distribution - on SkyCache's field-proven, honest, offline-first foundation.
