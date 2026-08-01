# Changelog

## 1.33.0 - Open Resilience Wave

Four workstreams: corpus expansion, offline resilience/federation, modular open FTA plugin scaffolding, dual-access size-budget packaging. **Not medical advice.** Not a complete archive. Not free commercial broadband.

### 1. Corpus
- `sample_corpus_stem.py` - 10 STEM / civics / heritage / agriculture / weather literacy samples
- Curated samples: 68 -> **78**
- Per-sample license override at package build (fail closed)

### 2. Resilience and federation
- Prioritizer `disaster_mode` / `power_critical` protect emergency + health under disk pressure
- `priority_works_delta()` - survival-first multi-village works gossip ordering
- Local ops continues privacy-preserving bit-rot status (no cloud by default)

### 3. Open decoding plugins
- `open_fta_sim` plugin - simulated open FTA educational bulletin (zero RF)
- `docs/plugin-extension-open-fta.md` contributor extension guide
- Commercial decrypt name hints refused

### 4. Dual-access packaging
- Pack profiles `archive-100mb`, `archive-1gb`
- Default pack-kits: literacy + clinic + stem-lite + archive-100mb
- `skycache library pack-budgets` size-gate planner
- Docs: `docs/OPEN-RESILIENCE-WAVE.md`

### Upgrade from 1.32.x
1. pip install -e .
2. skycache skybrary samples --out samples/skybrary
3. skycache library pack-budgets
4. skycache library sync --skip-zero-network --with-packs --apply-web
5. Deploy skycache-web

---

## 1.32.0 - Zero-Network 68 Parity + Zip Guard

Rebuilds the zero-network phone kit so `work_count` matches the full curated sample set (**68**), restoring library doctor score 100. Hardens `library zero-network` zip packaging so a kit zip written under `kit/` can never self-include (rglob bomb). Not medical advice. Not a complete archive. Not free commercial broadband.

### Surface
- `skycache library zero-network` parity with `len(SAMPLES)` (68)
- Zip always built outside `out_dir`, then copied in; `.zip` files skipped during pack
- Hosted: `/downloads/skycache-zero-network-demo-kit.zip` (68 works)

### Upgrade from 1.31.x
1. pip install -e .
2. skycache library zero-network --out phone-zero-network
3. skycache library sync --with-packs --apply-web
4. Deploy skycache-web

---

## 1.31.0 - Health Corpus Expand

Adds ten curated educational public-domain health/emergency literacy samples (hand hygiene, water/sanitation, ORS literacy framing, germ theory history, quarantine literacy, heat/cold, food hygiene, mosquito literacy, wound literacy, helper stress). Clinic pack kits (emergency-health / health-priority) grow from ~3 to ~13 packages. **Not medical advice.** Not a complete archive. Not free commercial broadband.

### Corpus
- `skycache/skybrary/sample_corpus_health.py` (HEALTH_SAMPLES)
- Total curated samples: 58 -> 68

### Upgrade from 1.30.x
1. pip install -e .
2. skycache library pack-kits --out data/library-pack-kits
3. skycache library sync --skip-zero-network --with-packs --apply-web
4. Deploy skycache-web

---

## 1.30.0 - Clinic Pack Kits (emergency + health)

Default `library pack-kits` now also builds **emergency-health** and **health-priority** USB pack zips for clinic/disaster demos. Library status lists pack profiles + public download URLs. Not medical advice. Not free commercial broadband. Not a complete archive.

### Surface
- Default pack-kits profiles: multilingual-literacy, literacy-starter, emergency-health, health-priority
- Hosted: `/downloads/skycache-pack-emergency-health.zip`, `/downloads/skycache-pack-health-priority.zip`
- `library status` includes `pack_profiles` + `downloads` map

### Upgrade from 1.29.x
1. pip install -e .
2. skycache library pack-kits --out data/library-pack-kits
3. skycache library sync --skip-zero-network --with-packs --apply-web
4. Deploy skycache-web

---

## 1.29.0 - Library Pack Kits

Build downloadable USB pack zips for marketing (`multilingual-literacy`, `literacy-starter`) via `library pack-kits`, and optional `--with-packs` on `library sync`. Not a complete archive. Not free commercial broadband.

### Surface
- `skycache library pack-kits --out data/library-pack-kits`
- `skycache library sync --with-packs --apply-web`
- Hosted: `/downloads/skycache-pack-multilingual-literacy.zip`

### Upgrade from 1.28.x
1. pip install -e .
2. skycache library pack-kits --out data/library-pack-kits
3. skycache library sync --skip-zero-network --with-packs --apply-web
4. npm run deploy in skycache-web

---

## 1.28.0 - Library Sync Apply-Web + Multilingual Pack

`library sync --apply-web` copies staged catalog/kits into `~/skycache-web/public` and rewrites sitemap work URLs. New pack profile `multilingual-literacy` for USB multilingual PD kits. Not a complete archive. Not free commercial broadband.

### Surface
- `skycache library sync --apply-web [--web-public PATH] [--skip-zero-network]`
- `skycache skybrary pack --profile multilingual-literacy`
- Sitemap writer for marketing public/

### Upgrade from 1.27.x
1. pip install -e .
2. skycache library sync --out data/library-sync --skip-zero-network --apply-web
3. cd ~/skycache-web ; npm run deploy

---

## 1.27.0 - Library Sync (marketing one-shot)

One command prepares dual-access marketing assets: catalog JSON, library ops kit zip, optional zero-network phone kit, and a copy checklist for skycache-web. Not a complete archive. Not free commercial broadband.

### Surface
- `skycache library sync --out data/library-sync [--skip-zero-network] [--skip-kit]`
- Staging: `public/skybrary-catalog.json`, `public/downloads/*.zip`, `COPY-TO-SKYCACHE-WEB.md`

### Tests
- sync path in library ops tests

### Upgrade from 1.26.x
1. pip install -e .
2. skycache library sync --out data/library-sync
3. Copy staging public/ into skycache-web/public/ and redeploy

---

## 1.26.0 - Zero-Network Kit Parity

Zero-network phone kit tracks the full curated dual-access sample set (not a 3-work demo). `library zero-network` rebuilds READ-OFFLINE.html + texts + zip; library doctor checks kit parity. Marketing hosts the kit zip. Not a complete archive. Not free commercial broadband.

### Surface
- `skycache library zero-network --out phone-zero-network [--no-zip]`
- Doctor check: `zero_network_kit_parity`
- Regenerated `phone-zero-network/`, `kit/`, samples mirror
- Public download: `/downloads/skycache-zero-network-demo-kit.zip`

### Honest rails
- Zero network to *read*; transfer still needs USB/SD/BT/pre-deploy
- Curated PD samples only; not free Starlink

### Tests
- zero-network parity in `tests/test_v1240_library_ops.py`

### Upgrade from 1.25.x
1. pip install -e .
2. skycache library zero-network --out phone-zero-network
3. skycache library doctor
4. Copy kit zip to marketing public/downloads/ and redeploy

---

## 1.25.0 - Library Publish + Multilingual Wave 2

Marketing-ready **library publish** command (catalog JSON without full node ingest) plus six more curated multilingual public-domain / traditional works (ar, sw, hi, ja, yo, bn). Catalog 52 -> 58 works. Not a complete archive. Not free commercial broadband.

### Library publish
- `skycache library publish --out DIR [--site-base URL] [--no-samples]`
- Writes `skybrary-catalog.json` + `catalog.json` + HOSTING for skycache-web/public/
- Optional sample package rebuild under samples/skybrary

### Multilingual wave 2
- `skycache/skybrary/sample_corpus_ml2.py` (ML2_SAMPLES)
- Locales: ar (Kalila tradition EN), sw, hi (Kabir translit), ja (Basho romaji), yo, bn (Tagore PD EN)

### Tests
- publish path in `tests/test_v1240_library_ops.py`

### Upgrade from 1.24.x
1. pip install -e .
2. skycache library publish --out data/catalog-publish
3. Copy skybrary-catalog.json to marketing public/ and redeploy
4. skycache library kit --out data/library-kit

---

## 1.24.0 - Library Ops + Multilingual PD Wave

Dual-access Skybrary **Library Ops** product surface (doctor / status / printable board / kit zip / API) plus eight curated multilingual public-domain works (fr/es/it/de/pt/la/ru-translit/zh-en). Catalog expands 44 -> 52 works. Not a complete archive. Not free commercial broadband.

### Library Ops surface
- `skycache library doctor|status|export|kit`
- `GET /api/library/status`
- Public site `/library/` + `/downloads/skycache-library-kit.zip`
- `skycache/ops/library_ops.py`

### Multilingual corpus
- `skycache/skybrary/sample_corpus_ml.py` (ML_SAMPLES wave 3)
- Languages: fr, es, it, de, pt, la, ru (ASCII translit), en+zh heritage
- Sample packages honor per-work `languages` field

### Honest rails
- Public domain / traditional only
- Curated packs, not a full national literature dump
- Not free commercial broadband

### Tests
- `tests/test_v1240_library_ops.py`

### Upgrade from 1.23.x
1. pip install -e .
2. skycache library doctor
3. skycache skybrary samples --out samples/skybrary
4. skycache skybrary export-catalog --out data/catalog-export --starter-kits
5. skycache library kit --out data/library-kit
6. Copy catalog JSON + library kit to marketing site and redeploy

---

## 1.23.0 - Skybrary PD Corpus Expand

Fattens the curated public-domain Skybrary dual-access library from 18 to 44 works: full short poems/fables plus substantial classic openings (literature, civics, STEM, heritage, health history). Regenerated sample packages + marketing `/library/` catalog. Not a complete archive. Not free commercial broadband. No pirate mirrors.

### Corpus surface
- skycache/skybrary/sample_corpus_more.py (MORE_SAMPLES wave 2, +26 works)
- skycache skybrary samples [--ingest]
- skycache skybrary export-catalog --out DIR [--starter-kits]
- Public site /library/ + skybrary-catalog.json work_count 44

### Honest rails
- Public domain / traditional PD translations only
- Curated packs, not Gutenberg dump
- Not every book ever written

### Tests
- sample count >= 40; existing dual-access + zero-network kit still pass

### Upgrade from 1.22.x
1. pip install -e .
2. skycache skybrary samples --out samples/skybrary
3. skycache skybrary samples --ingest --data-dir data
4. skycache skybrary export-catalog --out data/catalog-export --starter-kits
5. Copy catalog JSON to marketing site public/ and redeploy

---

## 1.22.0 - Dual Radio Ops

Village mesh dual-radio product surface: doctor (go_sim_validation / go_field_soak), status, printable board, ops kit zip with validation pack (board matrix + storyboard). Elevates dual-radio-pack into full ops surface. Unlicensed Wi-Fi/ISM only. Not free commercial broadband.

### Dual Radio Ops surface
- skycache dual-radio doctor|status|export|kit
- Legacy: skycache mesh dual-radio-pack
- API: GET /api/dual-radio/status
- Public site /mesh/ + /downloads/skycache-dual-radio-kit.zip

### Honest rails
- Sim path always green (matrix + storyboard + nexus validate)
- Field soak optional after spectrum check + dual radios + batctl
- Not free commercial broadband or Starlink

### Tests
- tests/test_v1220_dual_radio_ops.py

### Upgrade from 1.21.x
1. pip install -e .
2. skycache dual-radio doctor
3. skycache dual-radio export --out data/ops/dual-radio-board.html
4. skycache dual-radio kit --out data/dual-radio-kit
5. Redeploy site with dual-radio kit

---

## 1.21.0 - Partner Ops

Institutional pilot product surface: doctor (go_sim_pilot / go_field_rf), status, printable board, partner ops-kit zip. Builds on NGO/university/civil-protection kits and pilot-report validation. Not free commercial broadband.

### Partner Ops surface
- skycache partner doctor|status|export|ops-kit
- Legacy: partner kit|package-all|report validate|readiness
- API: GET /api/partner/status
- Public site /partners/ + /downloads/skycache-partner-ops-kit.zip

### Honest rails
- Sim pilots first; field RF optional
- Pilot reports require honest_scope_briefed
- Store-and-forward only; not free Starlink

### Tests
- tests/test_v1210_partner_ops.py

### Upgrade from 1.20.x
1. pip install -e .
2. skycache partner doctor
3. skycache partner export --out data/ops/partner-board.html
4. skycache partner ops-kit --out data/partner-ops-kit
5. Redeploy site with partner ops kit

---

## 1.20.0 - Seal Ops

Golden Pi fleet product surface: doctor (go_kit_path / go_seal_path), status, printable seal board, seal kit zip. Operator-hosted multi-GB .img.xz only. Never default PIN 2468. Not free commercial broadband.

### Seal Ops surface
- skycache seal doctor|status|export|kit
- Legacy: skycache pi-image doctor|plan|bundle|seal-checklist|hash|sealed-manifest
- API: GET /api/seal/status
- Public site /install/ + /downloads/skycache-seal-kit.zip (alongside golden SD kit)

### Honest rails
- Kit path OK on Windows; Linux host for dd/xz seal
- No multi-GB images in git
- Never ship default PIN 2468 / 0000 / 1234

### Tests
- tests/test_v1200_seal_ops.py

### Upgrade from 1.19.x
1. pip install -e .
2. skycache seal doctor
3. skycache seal export --out data/ops/seal-board.html
4. skycache seal kit --out data/seal-kit
5. Redeploy site with seal kit

---

## 1.19.0 - Corpus Ops

Legal bulk open corpus product surface: doctor, status, printable board export, corpus kit zip (plus existing batch/sample-manifest). Fail-closed licenses. Not a complete archive. Not free commercial broadband. Never pirate mirrors.

### Corpus Ops surface
- skycache corpus doctor|status|export|kit (top-level product CLI)
- skycache skybrary corpus ... (same surface under skybrary; export/kit added)
- skycache corpus sample-manifest / batch (offline fixtures + legal adapters)
- API: GET /api/corpus/status
- Public site /corpus/ kit + /downloads/skycache-corpus-kit.zip

### Honest rails
- Operator-run legal open content only
- Not every book ever written
- No pirate mirrors; fail-closed license gate

### Tests
- tests/test_v1190_corpus_ops.py (plus test_v150_bulk_corpus_ops.py)

### Upgrade from 1.18.x
1. pip install -e .
2. skycache corpus doctor
3. skycache corpus export --out data/ops/corpus-board.html
4. skycache corpus kit --out data/corpus-kit
5. Redeploy site with corpus kit

---

## 1.18.0 - Node Report Ops

Partner-facing readiness passport: rolls up local ops, capabilities, licenses, power, integrity, RX, disaster, and village-day gates into one doctor, status table, printable HTML, and kit zip. Not free commercial broadband. Fleet heartbeat remains default OFF.

### Node Report Ops surface
- skycache report doctor - go_partner_review / go_field_pack
- skycache report status - gate table across ops surfaces
- skycache report export --out PATH - printable node-report.html
- skycache report kit --out DIR - doctor + board + checklist + zip
- API: GET /api/report/status
- Public site /report/ + /downloads/skycache-report-kit.zip

### Honest rails
- Local rollup only; no cloud telemetry by default
- Receive-only FTA; unlicensed mesh TX; open content
- Not free commercial broadband

### Tests
- tests/test_v1180_report_ops.py

### Upgrade from 1.17.x
1. pip install -e .
2. skycache report doctor
3. skycache report export --out data/ops/node-report.html
4. skycache report kit --out data/report-kit
5. Redeploy site with /report/

---

## 1.17.0 - RX Ops

Live free-to-air receive-only station surface: doctor (go_rx_lab / go_rx_live), status, printable station board, RX kit zip. Wraps SatDump/RTL tooling and Pass Autopilot. Never commercial constellation decrypt. Not free commercial broadband.

### RX Ops surface
- skycache rx doctor - go_rx_lab / go_rx_live (+ tools inventory)
- skycache rx status - station + duty + ready snapshot
- skycache rx export --out PATH - printable station board HTML
- skycache rx kit --out DIR - doctor + board + checklist + zip
- Legacy: skycache rx doctor --legacy, watch/schedule/arm/duty unchanged
- API: GET /api/rx/ops (plus existing /api/rx/status and Pass Autopilot routes)
- Public site /rx/ + /downloads/skycache-rx-kit.zip

### Honest rails
- Receive-only FTA weather + open amateur telemetry
- Never commercial constellation decrypt or Starlink-class clients
- Product import works without physical SDR (lab path)

### Tests
- tests/test_v1170_rx_ops.py

### Upgrade from 1.16.x
1. pip install -e .
2. skycache rx doctor
3. skycache rx station --lat LAT --lon LON
4. skycache rx export --out data/ops/rx-station-board.html
5. skycache rx kit --out data/rx-kit
6. Redeploy site with /rx/

---

## 1.16.0 - Local Ops

Privacy-preserving node health board: doctor, status, printable HTML export, ops kit zip. Disk, power, peers, pack freshness, bit-rot schedule. Fleet heartbeat remains default OFF. Not free commercial broadband.

### Local Ops surface
- skycache ops doctor - go_local_lab / go_local_field
- skycache ops status - snapshot + fleet_heartbeat_enabled
- skycache ops export --out PATH - printable wall board HTML
- skycache ops kit --out DIR - doctor + board + checklist + zip
- Legacy: skycache ops status still works (enriched schema)
- API: GET /api/ops/status (plus existing /api/ops/local)
- Public site /ops/ + /downloads/skycache-ops-kit.zip

### Honest rails
- Local metrics only; no personal data harvest
- Fleet heartbeat default OFF (no cloud telemetry without opt-in)
- Not free commercial broadband

### Tests
- tests/test_v1160_local_ops.py

### Upgrade from 1.15.x
1. pip install -e .
2. skycache ops doctor
3. skycache ops export --out data/ops/local-ops-board.html
4. skycache ops kit --out data/ops-kit
5. Redeploy site with /ops/

---

## 1.15.0 - Capabilities Ops

First-run and partner legal self-audit surface for what this node may do: doctor, matrix status, printable HTML export, capabilities kit zip - open decode/corpora/unlicensed mesh only; never commercial constellation piracy or free Starlink.

### Capabilities Ops surface
- skycache capabilities doctor - go_capabilities_onboard / go_capabilities_field
- skycache capabilities status - full legal matrix + banned list
- skycache capabilities export --out PATH - printable HTML matrix
- skycache capabilities kit --out DIR - doctor + matrix + checklist + zip
- Legacy: bare skycache capabilities / --json still prints the matrix
- API: GET /api/capabilities/status (plus existing /api/capabilities)
- Public site /capabilities/ + /downloads/skycache-capabilities-kit.zip

### Honest rails
- Receive-only satellite; unlicensed mesh TX only; open content only
- Not free commercial broadband; never commercial constellation decrypt
- Field gate requires non-default admin PIN

### Tests
- tests/test_v1150_capabilities_ops.py

### Upgrade from 1.14.x
1. pip install -e .
2. skycache capabilities doctor
3. skycache capabilities export --out data/ops/capabilities-matrix.html
4. skycache capabilities kit --out data/capabilities-kit
5. Redeploy site with /capabilities/

---

## 1.14.0 - Licenses Ops

Partner/regulator license inventory surface: doctor, status, printable HTML export, licenses kit zip - operator confirms redistribution rights; not legal advice; not free commercial broadband.

### Licenses Ops surface
- skycache licenses doctor - go_licenses_inventory / go_partner_export
- skycache licenses status - package_count + by_license + unknown_or_blank
- skycache licenses export --out PATH - printable HTML inventory
- skycache licenses kit --out DIR - inventory + checklist + zip
- Legacy: skycache licenses --html PATH / --summary still work
- API: GET /api/licenses/status (plus existing /api/licenses and /api/licenses/export)
- Public site /licenses/ + /downloads/skycache-licenses-kit.zip

### Honest rails
- Operator duty: confirm terms for every pack (Kiwix/ZIM, MoH, etc.)
- Not legal advice; open/FTA/operator-authored content only

### Tests
- tests/test_v1140_licenses_ops.py

### Upgrade from 1.13.x
1. pip install -e .
2. skycache licenses doctor
3. skycache licenses export --out data/ops/licenses-inventory.html
4. skycache licenses kit --out data/licenses-kit
5. Redeploy site with /licenses/

---

## 1.13.0 - Power Ops

Solar/battery maintainer surface: power doctor, SOC/mode guidance status, printable wall sheet, power kit zip - rough estimates only, not free commercial broadband.

### Power Ops surface
- skycache power doctor - go_power_lab / go_power_field
- skycache power status - SOC, mode, hours-until-ECO guidance
- skycache power sheet --out PATH - printable maintainer HTML
- skycache power kit --out DIR - sheet + solar notes + zip
- API: GET /api/power/status (plus existing /api/power/guidance and maintainer-sheet)
- Public site /power/ + /downloads/skycache-power-kit.zip

### Honest rails
- Estimates are order-of-magnitude; calibrate battery_wh per site
- Not electrical code compliance; not free broadband

### Tests
- tests/test_v1130_power_ops.py

### Upgrade from 1.12.x
1. pip install -e .
2. skycache power doctor
3. skycache power sheet --out data/ops/power-sheet.html
4. skycache power kit --out data/power-kit
5. Redeploy site with /power/

---

## 1.12.0 - Disaster Drill Ops

Partner-ready disaster drill surface: doctor, lab run (priority flood + receipt), printable HTML report, closeout (disaster mode OFF), kit zip - local mesh/mule only, not free commercial broadband.

### Disaster Drill Ops surface
- skycache disaster doctor - go_lab_drill / go_partner_drill
- skycache disaster run --nodes N - lab sim + ops/disaster-drill-last.json
- skycache disaster report --out PATH [--run] - printable HTML
- skycache disaster closeout - mode OFF + receipt check
- skycache disaster kit --out DIR - playbook docs + report + zip
- Legacy: skycache mesh disaster-drill still works
- API: GET /api/disaster/status, POST /api/disaster/run, POST /api/disaster/closeout
- Public site /disaster/ + /downloads/skycache-disaster-kit.zip

### Honest rails
- Elevates emergency/health on local fabric only
- Not free Starlink; not satellite TX; turn disaster mode OFF after
- Lab sim is not a field RF authorization

### Tests
- tests/test_v1120_disaster_ops.py

### Upgrade from 1.11.x
1. pip install -e .
2. skycache disaster doctor
3. skycache disaster run --nodes 3
4. skycache disaster closeout
5. skycache disaster kit --out data/disaster-kit
6. Redeploy site with /disaster/

---

## 1.11.0 - Integrity Ops

Local bit-rot / package integrity operator surface: doctor, verify+record, printable HTML report, schedule templates, integrity kit zip - open packages only, not DRM defeat, not free commercial broadband.

### Integrity Ops surface
- skycache integrity doctor - go_integrity_sim / go_integrity_scheduled
- skycache integrity verify [--no-record] - content tree verify + bitrot-last.json
- skycache integrity report --out PATH [--verify] - printable HTML
- skycache integrity install-templates - systemd/cron (same as bitrot install-templates)
- skycache integrity kit --out DIR - report + templates + zip
- API: GET /api/integrity/status, POST /api/integrity/verify
- Public site /integrity/ + /downloads/skycache-integrity-kit.zip

### Honest rails
- Open packages only; not commercial media integrity
- Local-only reports; no cloud telemetry
- Not free commercial broadband

### Tests
- tests/test_v1110_integrity_ops.py

### Upgrade from 1.10.x
1. pip install -e .
2. skycache integrity doctor
3. skycache integrity verify --record
4. skycache integrity kit --out data/integrity-kit
5. Redeploy site with /integrity/

---

## 1.10.0 - Federation Ops

Multi-village works/package gossip operator surface: doctor, local status, export/import gossip JSON, multi-node sim with receipt, federation kit zip - open content only, sim-first, not free commercial broadband.

### Federation Ops surface
- skycache federation doctor - go_sim_federation readiness
- skycache federation status - local gossip snapshot stats
- skycache federation export-gossip --out PATH [--compact|--full]
- skycache federation import-gossip PATH [--peer-content DIR]
- skycache federation sim --nodes N --rounds R - receipt under data/ops/
- skycache federation kit --out DIR - checklist + sample gossip + zip
- Legacy: skycache nexus federation still works (delegates to federation sim)
- API: GET /api/federation/status, POST /api/federation/export-gossip
- Public site /federation/ + /downloads/skycache-federation-kit.zip

### Honest rails
- Open/PD works and packages only
- Sim filesystem copy is not hardware mesh proof
- Field still needs unlicensed mesh day-one + spectrum check

### Tests
- tests/test_v1100_federation_ops.py

### Upgrade from 1.9.x
1. pip install -e .
2. skycache federation doctor
3. skycache federation sim --nodes 2
4. skycache federation kit --out data/federation-kit
5. Redeploy site with /federation/

---

## 1.9.0 - Village Day Ops

One weekend stand-up surface: aggregate doctor (handoff + mesh + gateway + partner/RX + demos + disk), go/no-go readiness receipt, printable RUNBOOK.md, field checklist kit zip - sim path without RF; field path still spectrum-gated.

### Village Day Ops surface
- skycache village-day doctor - go_weekend_sim / go_weekend_field + blockers
- skycache village-day readiness - write data/ops/village-day-last.json
- skycache village-day runbook --out DIR - RUNBOOK.md + doctor JSON
- skycache village-day kit --out DIR - checklist + docs + zip
- API: GET /api/village-day/status, POST /api/village-day/readiness
- Public site /village-day/ + /downloads/skycache-village-day-kit.zip

### Honest rails
- Sim weekend green is not RF authorization
- Receive-only satellite; unlicensed mesh TX; open content only
- Not free commercial broadband

### Tests
- tests/test_v190_village_day_ops.py

### Upgrade from 1.8.x
1. pip install -e .
2. skycache village-day doctor
3. skycache village-day readiness
4. skycache village-day kit --out data/village-day-kit
5. Redeploy site with /village-day/

---

## 1.8.0 - Gateway Ops

Production opportunistic uplink surface: gateway doctor, open-mirror presets, one-shot preset pull with license passport + local receipt, ethics kit zip - open-content allowlist and fair-share quota only, never commercial decrypt or automatic mesh-to-internet bridge.

### Gateway Ops surface
- skycache gateway doctor - go_sim_gateway / go_live_gateway readiness
- skycache gateway status - uplink + quota + presets snapshot
- skycache gateway presets - list open-mirror presets
- skycache gateway pull-preset ID [--dry-run|--sim] - open-fetch + pull-passport.json + receipt
- skycache gateway receipts - local audit trail
- skycache gateway ethics-kit --out DIR - ETHICS.md + presets + doctor + zip
- Legacy flags still work: --presets --receipts --pull --request --quota-mb --sim
- API: GET /api/gateway/status|presets|receipts, POST /api/gateway/pull-preset
- Public site /gateway/ + /downloads/skycache-gateway-ethics-kit.zip

### Honest rails
- Allowlisted open hosts only; operator verifies each work license
- Daily fair-share quota is social ethics, not product entitlement
- No commercial constellation decrypt; not free broadband

### Tests
- tests/test_v180_gateway_ops.py

### Upgrade from 1.7.x
1. pip install -e .
2. skycache gateway doctor
3. skycache gateway pull-preset gutenberg-sample --dry-run
4. skycache gateway pull-preset gutenberg-sample --sim
5. skycache gateway ethics-kit --out data/gateway-ethics-kit
6. Redeploy site with /gateway/

---

## 1.7.0 - Phone Handoff Ops

Production phone path: handoff doctor, offline join card + SVG QR, one-shot mule export (zip + packages), import, hub API - local hub Wi-Fi / USB / SD only, never commercial broadband tethering.

### Phone Handoff Ops surface
- skycache handoff doctor - go_phone_path readiness (packages + demos + QR engine)
- skycache handoff join-card --portal-url URL --ssid SSID - join.html + join-qr.svg + join.json
- skycache handoff export [--limit N] [--out DIR] - mule packages + join card + zip under data/handoff
- skycache handoff import PATH - import bundle dir or zip into this node
- Legacy: skycache handoff --out DIR still exports (same as export)
- API: GET /api/handoff/status, POST /api/handoff/join-card, POST /api/handoff/export
- Optional dep: qrcode (pure modules -> SVG, no PIL required for QR)
- Public site /handoff/

### Honest rails
- Local hub Wi-Fi, USB, or SD only - not free Starlink or commercial tethering
- Open content / public-domain demos; not medical advice
- QR is offline SVG matrix; no cloud mule

### Tests
- tests/test_v170_phone_handoff_ops.py

### Upgrade from 1.6.x
1. pip install -e .
2. skycache handoff doctor
3. skycache handoff join-card --portal-url http://10.42.0.1:8080/ --ssid SkyCache-Village
4. skycache handoff export --limit 10
5. Redeploy site with /handoff/

---

## 1.6.0 - Field Mesh Ops

Production mesh operator surface: doctor, readiness (sim validate), disaster-drill receipt, field-kit zip - unlicensed Wi-Fi/ISM only, sim-first, no free broadband claims.

### Field Mesh Ops surface
- skycache mesh doctor - host + docs readiness (go_sim_mesh / go_field_mesh)
- skycache mesh readiness [--nodes N] - score + nexus validate sim + JSON receipt
- skycache mesh disaster-drill [--nodes N] - lab disaster flood + ops/disaster-drill-last.json
- skycache mesh field-kit --out DIR - checklists + day-one plan + dual-radio refs + zip
- Public site /mesh/ + /downloads/skycache-field-mesh-kit.zip

### Honest rails
- Sim green does not authorize RF; spectrum check still required
- Mesh TX unlicensed/ISM only; satellite remains receive-only
- Not free commercial broadband

### Tests
- tests/test_v160_field_mesh_ops.py

### Upgrade from 1.5.x
1. pip install -e .
2. skycache mesh doctor
3. skycache mesh readiness --nodes 2
4. skycache mesh disaster-drill --nodes 3
5. skycache mesh field-kit --out data/field-mesh-kit
6. Redeploy site with /mesh/

---

## 1.5.0 - Bulk Open Corpus Ops

Legal bulk corpus scale surface: corpus doctor, local status snapshot, batch manifests that drive folder / Gutenberg / OA science / open-URL jobs, offline sample batch, always-on provenance write - never pirate mirrors, never a complete-archive claim.

### Bulk Open Corpus Ops surface
- skycache skybrary corpus doctor - fixtures + license gate + samples readiness
- skycache skybrary corpus status - local package/license/passport snapshot
- skycache skybrary corpus sample-manifest --out PATH - offline demo batch JSON
- skycache skybrary corpus batch --manifest PATH [--allow-local] [--ingest] [--dry-run]
- Job types: folder, gutenberg_catalog, oa_science, open_url
- Batch writes data/ops/corpus-batch-provenance.json

### Honest rails
- License fail-closed (assert_license_allowed)
- Offline fixtures only unless operator supplies legal catalogs/URLs
- Status counts this node only - not world literature completeness

### Tests
- tests/test_v150_bulk_corpus_ops.py

### Upgrade from 1.4.x
1. pip install -e .
2. skycache skybrary corpus doctor
3. skycache skybrary corpus sample-manifest --out data/corpus-batch-demo.json
4. skycache skybrary corpus batch --manifest data/corpus-batch-demo.json --allow-local --ingest
5. Redeploy marketing site with /corpus/

---

## 1.4.0 - Golden Node Bake Ops

Production golden-path for village Pi nodes: bake plan v2, host doctor, seal checklist, sealed-image manifest (URL+sha256 only), kit zip v2 - multi-GB .img never in git.

### Golden Node Bake Ops surface
- skycache pi-image doctor - host readiness (kit path vs seal path)
- skycache pi-image plan/write - bake plan schema v2 (readiness + RX optional + seal steps)
- skycache pi-image seal-checklist - fleet clone discipline (forbidden PINs)
- skycache pi-image hash PATH - SHA-256 local sealed image
- skycache pi-image sealed-manifest --url --sha256 - register operator-hosted .img.xz metadata
- skycache pi-image bundle - download kit v2 (seal checklist, partner/RX docs)
- Public site /install/ golden path

### Honest rails
- Never ship PIN 2468 / 0000 / 1234 on sealed images
- Raw .img.xz stays operator-hosted; git only holds plans + kit scripts
- Not free commercial broadband

### Tests
- tests/test_v140_golden_node_bake.py

### Upgrade from 1.3.x
1. pip install -e .
2. skycache pi-image doctor
3. skycache pi-image bundle --out data/pi-download
4. Copy zip to site /downloads/
5. Redeploy marketing site with /install/

---

## 1.3.0 - Partner Pilot Ops

Institutional pilot track: production partner kits with zips, pilot-report validation, local readiness scoring, and public /partners/ site surface.

### Partner Pilot Ops surface
- skycache partner kit --type ngo|university|civil-protection [--zip]
- skycache partner package-all --out data/partner-kits (all kits + HOSTING.json)
- skycache partner report validate PATH (fail-closed honesty + license fields)
- skycache partner readiness [--data-dir] (go_sim_pilot / go_field_rf scores)
- Kits include FIELD-DAY.md, Pass Autopilot CLI, threat-model + phase2-live-rx docs
- partner-manifest schema v2

### Honest rails
- Readiness never claims free broadband; product-import path OK without RTL dongle
- Pilot reports require license_review_ok + honest_scope_briefed

### Tests
- tests/test_v130_partner_pilot_ops.py

### Upgrade from 1.2.x
1. pip install -e .
2. skycache partner readiness
3. skycache partner package-all --out data/partner-kits
4. skycache partner kit --type ngo --zip
5. Redeploy marketing site with /partners/ + kit downloads

---

## 1.2.0 - Pass Autopilot (station duty cycle)

Closes the operator gap between "I know when the pass is" and "the station is armed for it": schedule binding, arm state, SatDump CLI sketches, auto field-log on product watch.

### Pass Autopilot surface
- skycache rx schedule - upcoming FTA passes bound to recipes (NOAA APT, Meteor LRPT, GOES HRIT, product import) + SatDump command sketches + operator steps
- skycache rx arm / --disarm / --status / --show - persist arm-state.json; enables auto field-log on rx watch
- skycache rx cmd - print SatDump CLI sketch for a recipe or next scheduled pass
- skycache rx duty - duty board (arm + next pass countdown)
- GET /api/rx/schedule, GET /api/rx/duty, GET|POST /api/rx/arm
- Product watch auto-appends field-log rows when station is armed (operator=autopilot)

### Honest rails
- Arming does not start RF TX or claim free commercial broadband
- SatDump still owns demodulation; SkyCache owns duty cycle + ingest + field notes
- Recipe binding is best-effort by satellite name; operators verify active birds

### Tests
- tests/test_v120_pass_autopilot.py

### Upgrade from 1.1.x
1. pip install -e .
2. skycache rx station --lat LAT --lon LON  (if not set)
3. skycache rx schedule
4. skycache rx arm --hours 12
5. After SatDump products land: skycache rx watch --dir PRODUCTS --once
6. skycache rx duty
7. Redeploy marketing site with 1.2.0 status

---

## 1.1.2 - SatDump/RTL PATH doctor + Install-RxTools-Windows

### Operator tooling
- scripts/Install-RxTools-Windows.ps1 - winget SatDump + librtlsdr w64 CLI (rtl_test/rtl_sdr) with correct release URLs, User PATH wiring
- rx doctor: Windows well-known path discovery (Program Files\SatDump\bin, tools/rx-windows), honest satdump usage probe, ready.live_decode_path + rtl_device_seen
- SKYCACHE_RX_TOOLS env for extra search dirs

### Honest rails
- live_hardware_path = SatDump + rtl_test/rtl_sdr/Soapy present (software stack)
- rtl_device_seen only when rtl_test finds a dongle (no fake hardware claims)

### Upgrade
1. pull / reinstall
2. powershell -File scripts/Install-RxTools-Windows.ps1
3. skycache rx doctor --data-dir data

---

## 1.1.1 - Windows RX station setup helpers

### Operator tooling
- scripts/Setup-RxStation.ps1 - sgp4, Celestrak TLE refresh, station, products folder
- scripts/Start-RxWatch.ps1 - one-shot or continuous product watch
- scripts/Install-RxWatch-Task.ps1 - 5-minute Scheduled Task poller
- scripts/refresh_fta_tles.py - NOAA 15/18/19 + Meteor-M TLEs (operator-run)
- docs/phase2-live-rx.md Windows section

### Upgrade
1. pull / reinstall
2. powershell -File scripts/Setup-RxStation.ps1 -Lat LAT -Lon LON -RefreshTle

---

## 1.1.0 - Live FTA RX Ops (real-world satellite path)

Closes the Phase 2 gap between SatDump field work and the village portal with a production operator loop - not theoretical broadband.

### Real-world RX surface
- skycache rx doctor - SatDump/RTL/Soapy/gr-satellites inventory + station
- skycache rx recipes - legal FTA recipes (NOAA APT, Meteor LRPT, GOES HRIT advanced, product import)
- skycache rx station / passes / tle-import - ground station + pass plan (sgp4 optional extra)
- skycache rx watch|import|capture - SatDump product auto-ingest + plugin wrap
- skycache rx log - append-only field journal for real passes
- GET /api/rx/* status, recipes, passes, field-log, import
- deploy/rx/skycache-rx-watch.service for always-on product watch
- docs/phase2-live-rx.md rewritten as production runbook

### Honest rails
- Receive-only; unencrypted FTA / open amateur only
- Without sgp4: fixture pass tables + clear install hint (CI-safe)
- Does not reimplement SatDump demodulators or claim free Starlink

### Tests
- tests/test_v110_live_rx.py

### Upgrade from 1.0.x
1. pip install -e .
2. Optional: pip install sgp4
3. skycache rx doctor
4. skycache rx station --lat LAT --lon LON
5. After a pass: skycache rx watch --dir PRODUCTS --once
6. Redeploy marketing site with 1.1.0 status

---

## 1.0.1 - Compact works gossip + locale parity

### Federation bandwidth
- works_manifest(compact=True) for large catalogs (auto when >200 works on gossip)
- Tier-first ordering + max_tier filter; stub edition import from primary_* fields
- ContentFabric.gossip_payload accepts works_compact / works_max / works_max_tier

### Site
- All skycache-web locale packs status/village/hero keys synced to 1.0 product language

### Tests
- test_compact_works_manifest_and_import

### Upgrade from 1.0.0
1. pip install -e .
2. No data migration
3. Redeploy site for locale parity

---

## 1.0.0 - Skybrary Resilience Fabric

First major: village multi-node open works federation that feels like infrastructure, scheduled bit-rot integrity, local ops metrics, and a threat-model one-pager - still honest store-and-forward, not free commercial broadband.

### Integrity & bit-rot (B5)
- skycache skybrary doctor --verify --record -> data/ops/bitrot-last.json
- skycache bitrot install-templates (systemd timer + cron examples under deploy/bitrot/)
- doctor prints schedule freshness; GET /api/integrity/last

### Works federation (B6 production surface)
- skycache nexus federation --nodes N multi-node sim (works_manifest gossip + package pull)
- skycache/nexus/federation.py; fabric attaches Skybrary in serve
- High-tier works delta helper for foundational catalogs first

### Local ops without surveillance (E4)
- skycache ops status + GET /api/ops/local (disk, power, peers, pack freshness, bit-rot)
- fleet heartbeat remains default OFF

### Trust (D3)
- docs/threat-model.md one-pager

### Site
- skycache.jonbailey.xyz status/phases/docs for 1.0.0

### Tests
- tests/test_v100_resilience_fabric.py

### Upgrade from 0.9.2
1. pip install -e .
2. Optional: skycache bitrot install-templates --out /etc path or deploy/bitrot
3. skycache skybrary doctor --verify --record
4. skycache nexus federation --nodes 2 (sim acceptance)
5. Redeploy site with 1.0.0 banner

---

## 0.9.2  -  Downloadable SD kit, dual-radio validation media, MBTiles blobs, EPUB pagination

Closes the four post-0.9.1 honest gaps with production paths (no multi-GB binaries in git).

### Downloadable pre-built SD image hosting
- skycache pi-image bundle -> skycache-golden-sd-kit.zip (scripts + bake plan + mesh day-one + docs)
- Hosted at site /downloads/skycache-golden-sd-kit.zip and GitHub Release asset path
- HOSTING.json inside kit documents optional raw .img.xz attach for operators who seal with dd/pi-gen
- Not a multi-GB .img in the monorepo (by design)

### Dual-radio validation (all board models)
- Board matrix: Pi 4/5/3B+, Orange Pi, OpenWrt pair, sim laptop
- skycache mesh dual-radio-pack -> storyboard HTML + SVG frames + optional MP4 + docs/mesh-dual-radio-validation.md
- Shared day-one procedure; per-board notes in matrix JSON

### Multi-GB regional MBTiles (operator + blob store)
- Tiny sample MBTiles fixture in samples/packages/maps-local-001/
- skycache maps sample / skycache maps import with blob store put
- ODbL allowed in license gate; maps-offline profile remains
- Regional multi-GB extracts stay operator-supplied  -  never committed to git

### Full EPUB / long-text CSS pagination
- PWA **Pages** mode: CSS multi-column paginated view, Pg−/Pg+, page indicator
- Works with chapter API + EPUB spine text path
- Preference stored in localStorage only

### Tests
- 	ests/test_v092_remaining_depth.py

### Upgrade from 0.9.1
1. pip install -e .
2. skycache pi-image bundle --out data/pi-download then copy zip to site downloads
3. skycache mesh dual-radio-pack --out media/dual-radio-validation
4. Optional: skycache maps sample / maps import path.mbtiles

---

## 0.9.1  -  Field depth (Pi bake, mesh OOB, OA science, reader, blobs, partners)

Ships the major remaining field and archive depth items after Skybrary Live 0.9.0  -  still honest about hardware-dependent steps.

### Golden Raspberry Pi SD image
- skycache pi-image plan|write bake plan JSON + verify script
- deploy/pi-image/README.md + ake-golden.sh (requires SKYCACHE_ADMIN_PIN non-default)
- Uses existing install-village-fabric.sh + first-boot rails

### batman-adv day-one hardware OOB
- deploy/mesh/batman-day-one.sh (DRY_RUN=1 safe; real bring-up on Linux root)
- skycache mesh day-one --write plan; --apply --yes only when host ready
- skycache/nexus/mesh_day_one.py environment probe (sim-safe on Windows/CI)

### Open-access science bulk
- skycache skybrary import-oa-science catalog adapter (arXiv/PMC-style hosts allowlisted)
- License-gated (OA/CC/PD only); fixtures under 	ests/fixtures/oa_science/
- Provenance batch on every import

### EPUB + multi-file chapter nav
- skycache/skybrary/chapters.py + APIs .../chapters and .../chapters/{i}
- PWA reader: chapter chips, Ch−/Ch+, EPUB spine best-effort

### Content-addressed blobs + maps pack
- skycache blobs put|verify|stats|ingest-content (data/blobs/)
- Pack profile maps-offline; maps sample package is operator guide for MBTiles/OSM (license passport required for real tiles)

### Partner field pilots
- skycache partner kit --type ngo|university|civil-protection
- Checklist MD/HTML, legal one-pager, training agenda, pilot-report template, optional docs copy

### Tests
- `tests/test_v091_field_depth.py`

### Upgrade from 0.9.0
1. pip install -e .
2. No data migration
3. Optional: skycache pi-image write --out data/pi-bake
4. Optional: skycache mesh day-one --write
5. Optional: skycache partner kit --type ngo --out data/partner-kit

### Superseded by 0.9.2
Downloadable SD kit hosting, dual-radio validation media (all boards), MBTiles+blob path, CSS pagination  -  see **0.9.2** above.

---

## 0.9.0  -  Skybrary Live (Dual-Access Portal Complete)

Heavy-duty dual-access release: online Skybrary portal is production-grade, corpus has real substance, public site ships with software, same works offline and online.

### Dual-access portal (S4 complete)
- **Catalog export v2** (skycache.skybrary.catalog.v2): unified schema with creators, summary, passport, pack_profiles, facets, starter kits  -  one export feeds site /library/ and static HTML
- **Starter kits with license passports:** export-catalog --starter-kits -> literacy-starter + emergency-health-sample zips + passport JSON + license HTML
- **API:** GET /api/skybrary/catalog.json (v2 parity), GET /api/skybrary/kits
- **Public site:** mobile-first search + language/subject/license facets, work detail pages with license passport, kit downloads, CTAs
- **Same work IDs** online (static catalog) and offline (node FTS + packs)

### Corpus substance (B2 advance)
- **Curated PD corpus:** ~18 public-domain works (literacy, civics, STEM, historical health education)  -  real bodies, manifests, sha256
- **Gutenberg-style catalog adapter:** skycache skybrary import-gutenberg-catalog  -  operator-run, rate-limited, license-gated, provenance batch; fixture path for sim/CI (--allow-local)
- **Pack profile:** literacy-starter (~8 MB dual-access demo kit)
- Automated provenance reports on catalog batch import

### Capabilities and hygiene
- Matrix: skybrary_gutenberg_catalog, skybrary_dual_access_export
- Version **0.9.0**; RF modes and legal gate unchanged or stronger surface
- Tests: `tests/test_v090_skybrary_live.py` + fixture catalog under `tests/fixtures/gutenberg/`
- Site skycache.jonbailey.xyz updated to Skybrary Live status (redeploy with software)

### Upgrade from 0.8.0
1. pip install -e . (or pull + reinstall)
2. Existing data/ compatible  -  no migration
3. Optional: skycache skybrary samples --ingest to load expanded corpus
4. skycache skybrary export-catalog --out data/catalog-export --starter-kits then copy skybrary-catalog.json + packs/ to marketing site
5. Site: redeploy skycache.jonbailey.xyz with 0.9.0 status string

### Later releases
Field depth, partner kits, downloadable SD kit, dual-radio media, MBTiles/blobs, pagination  -  see **0.9.1** and **0.9.2**.

---

## 0.8.0 - Village Ready + Skybrary Dual-Access

Highest-leverage field + archive release: untrained volunteers can ship a village node in a weekend; dual-access catalog foundations are real; pack kits and gateway ethics are operator-ready.

### Field product (Theme A + C)
- **Pack profiles 2.0 complete:** `emergency-health`, `literacy-1gb`, `stem-2gb`, `stem-lite`, `local-heritage`, `language-<code>` (dynamic), size-aware **reserve** so literature never starves emergency/health on small disks
- **Signed pack manifests:** `profile-manifest.json` + `profile-manifest.sha256` with content-tree `root_sha256`; `verify_pack_manifest()`
- **Power UX:** `GET /api/power/guidance` (hours until ECO/CRITICAL), `GET /api/power/maintainer-sheet` printable HTML; doctor prints rough time-to-ECO
- **Gateway ethics:** open-mirror presets (Gutenberg / Kiwix / Archive PD / WHO-hint), local pull **receipts**, daily quota API (`POST /api/admin/gateway/quota`), CLI `--presets --receipts --quota-mb`
- **Mesh validate:** `skycache nexus validate --nodes 2|3` (sim acceptance) + field checklist stub
- Admin: power sheet, license inventory print, quota + receipts UI (handoff QR already present)

### Skybrary dual-access (Theme B)
- **Static catalog export:** `skycache skybrary export-catalog` -> `catalog.json` + `index.html` for site `/library/`
- **Provenance batch:** `skycache skybrary provenance` (partner/regulator report)
- License inventory **printable HTML** (`skycache licenses --html`  |  `GET /api/licenses/export` -> browser Save as PDF)

### Engineering
- New modules: `health/power_guidance.py`, `nexus/gateway_presets.py`, `nexus/mesh_validate.py`, `skybrary/catalog_export.py`, `skybrary/provenance.py`
- Tests: `tests/test_v080_village_ready.py` (pack sign, power, gateway, mesh 2/3-node, export, APIs)
- Docs: partner kits, architecture notes, NEXT-STEPS progress, upgrade notes below

### Upgrade from 0.7.x
1. `pip install -e .` (or pull + reinstall)
2. Existing `data/` is compatible - no migration required
3. Optional: `skycache skybrary export-catalog --out data/catalog-export` then copy to marketing `/library/`
4. Optional: set gateway quota in Admin; print license inventory for partners
5. Re-run `skycache first-boot --force` only if reconfiguring PIN/SSID/mode
6. Site: redeploy skycache.jonbailey.xyz with 0.8.0 status string

### Explicitly still later
- Full golden Raspberry Pi SD image bake
- Gutenberg batch catalog adapter + open-access science subset pipelines
- Content-addressed blob store for multi-GB archives
- Light EPUB in-PWA reader path; deeper chapter nav
- Partner field pilots with civil protection (playbooks ready)

---

## 0.7.2 - Zero-network phone kit (no Wi-Fi, no cell)

**Physics-honest path:** a phone with **no Wi-Fi and no cell** cannot download over the air; it can still **read** demos if files are on storage.

- `skycache skybrary zero-network-kit` -> `READ-OFFLINE.html` + `texts/*.txt` + README
- `GET /api/demo/zero-network`  |  `/api/demo/zero-network-kit.zip`  |  `/api/demo/READ-OFFLINE.html`
- Shipped sample: `samples/phone-zero-network/` (USB/BT/SD/pre-deploy)
- PWA: **Zero-network kit** + **Offline reader HTML** buttons
- Docs: `docs/zero-network-phone.md`

## 0.7.1 - Phone offline demos (no cell plan)

**End-goal path:** a phone with no cellular plan can download the three PD demo texts over **local hub Wi-Fi only**.

- `GET /api/demo` + `GET /api/demo/pack.zip` - one-tap zip of Aesop / Gettysburg / Hippocratic samples
- Auto-ensure demos on every `serve` / app start (`skycache.skybrary.phone_demo`)
- PWA home + Library: **Save demos to this phone**; reader **Save file** (`?download=1`)
- Onboarding step `phone_demo`; docs: `docs/phone-offline-demo.md`
- Honest: requires a provisioned hub nearby - not free commercial broadband

## Unreleased

### Wave 1.A1 golden path first-boot
- **First-boot wizard:** `skycache first-boot` + `deploy/first-boot-wizard.sh`
  - Sets admin PIN (rejects default `2468`), SSID hint, `legal_rf_mode`
  - Loads demo packages + Skybrary public-domain samples
  - Writes `data/skycache.env` + `data/first_boot.json`; prints capabilities summary
- **Installer:** `deploy/install-village-fabric.sh` runs wizard when TTY or `SKYCACHE_ADMIN_PIN` set
- **Docs:** `docs/first-boot.md` (Debian/Pi volunteer path &lt;2 hours)
- **PWA onboarding:** capabilities + Library steps via `/api/onboarding`
- Legal rails unchanged: receive-only sat, no commercial decrypt, honest banners

### Wave 1.B3 pack profiles 2.0
- Profiles: `emergency-health`, `literacy-1gb`, `stem-lite`, `all-open-small` (+ kept `literacy-100mb`, `health-priority`)
- Emergency/Health packages preferred via `include_priority_classes` + sort order
- Admin `POST /api/admin/skybrary/pack` (PIN) builds kits under `data/packs/`
- Admin UI **Build USB kit** button shows result JSON

### Wave 1.A2 in-PWA reader
- PWA **Skybrary reader**: large-type view for `work.txt` / package `index.html` via `/content/...`
- Library tab opens the reader (raw file link still available)
- Local-only scroll bookmark (`localStorage`) - no cloud PII
- Prev/next across current Library results; A+/A− font size
- Service worker caches `/content/` after first read for offline re-read

### Wave 2.D1 - License passport
- `GET /api/packages/{id}/passport` and `GET /api/skybrary/works/{id}/passport`
- Fields: license, provenance, retrieval_date, sha256, redistribute yes/no/review + note
- Optional `?verify=true` runs on-disk integrity for the package
- PWA: Passport chip on package + Library cards; bottom sheet detail

### Wave 3.B5 - Bit-rot doctor
- `skycache skybrary doctor --verify` runs content-tree integrity (`capabilities/integrity_tree.py`)
- Docs: weekly cron example for `skycache verify data/content`

### Wave 2.B2 - Corpus pipelines (legal bulk)
- `skycache/skybrary/corpus_import.py` - folder `.txt`/`.md`/`.html`/`.epub` + allowlisted open URL packaging
- Plugin `corpus_folder_import` (license required; fail closed)
- CLI: `skybrary import-folder`  |  `skybrary import-open` (optional `--ingest` -> content + FTS)
- Pipeline `--option KEY=VALUE`
- Capability `skybrary_corpus_import`
- Docs: `docs/skybrary-corpus-import.md` (never pirate mirrors)

## 0.7.0 - Parallel wave ship (village weekend + dual access foundations)

Nine parallel workstreams merged: first-boot golden path, PWA reader, pack kits, handoff UI, online catalog, corpus import, license passport, federation E2E, disaster/mesh field docs.

### Field (Wave 1)
- `skycache first-boot` + `deploy/first-boot-wizard.sh` + `docs/first-boot.md`
- In-PWA Skybrary reader (bookmarks, large type, prev/next)
- Pack profiles 2.0 + admin **Build USB kit** (`POST /api/admin/skybrary/pack`)
- Admin **Export handoff bundle** (`POST /api/admin/handoff`)
- Disaster drill + mesh field checklist docs

### Archive / dual access (Wave 2 - 3 foundations)
- Corpus folder/EPUB + open-URL import (`skybrary import-folder|import-open`)
- License passport APIs + PWA chips; `skybrary doctor --verify`
- Works-manifest export/import + fabric gossip hook; E2E fabric test
- Marketing `/library/` static catalog (deploy with site)

## 0.6.0 - Full legal capability surface (worldwide)

Implement **all lawful pathways** as productized software: capability matrix, open HTTPS allowlist fetch, pack profiles, integrity verify, handoff mule, legal RF modes.

### Capabilities
- `skycache capabilities` - ON/off matrix with legal basis for every feature
- `legal_rf_mode`: receive_only | ism_mesh | ism_lora_control | hybrid_gateway | amateur_operator (affirmed)
- Open allowlisted HTTPS fetch (`open-fetch`, plugin `open_http_import`, admin API)
- Package integrity verify (`skycache verify`)
- Phone/USB handoff bundles (`skycache handoff`)
- Skybrary pack profiles S3 (`skybrary pack --profile literacy-1gb`)
- API `/api/capabilities`, `/api/skybrary/profiles`, admin open-fetch
- Admin panel loads legal capability matrix

### Explicitly NOT implemented
- Commercial constellation decryption
- Default satellite uplink
- Unrestricted URL scraping / piracy mirrors

## 0.5.0 - Skybrary S2 + legal pathways

### Skybrary S2
- Works/editions SQLite catalog with **FTS5** full-text search
- Faceted browse (language, subject, license)
- API: `/api/skybrary/works|facets|status`
- PWA **Library** tab
- CLI: `skycache skybrary search`
- Ingest path: packages -> content catalog + works FTS

### Legal brainstorms (docs only - no piracy tools)
- `docs/legal-pathways-rf-and-content.md`: lawful decode/demod/authorized decrypt vs commercial bypass; lawful RX+TX (Wi-Fi/ISM, licensed amateur)

## 0.4.1 - Skybrary (Sky Library) mission lock + S1 scaffold

- **Skybrary** branding: dual-access open written knowledge on SkyCache foundation
- Docs: `VISION-SKYBRARY.md`, `skybrary-architecture.md`, `skybrary-roadmap.md`, `AGENTS.md`
- Code: `skycache/skybrary/` models, license gate, integrity, PD sample corpus
- CLI: `skycache skybrary doctor|samples`
- Website plan page + Desktop infographics (operator ship)

## 0.4.0 - Community broadband experience

Local services that feel like "internet" on the village fabric - still honest store-and-forward + mesh.

### Added
- **Search** across the full catalog (`/api/search`, `skycache search`)
- **Village boards** (school, clinic, emergency, farm, announcements)
- **Package ratings** (anonymous local tokens; no third-party analytics)
- **License inventory** (`/api/licenses`, `skycache licenses`)
- **Power map** + **traffic-class monitor** (admin + nexus status)
- **Control plane** stub (LoRa/ISM low-BW alerts; sim-friendly)
- **Fabric delta** compare API for fingerprint-based sync planning
- **Onboarding** steps API + first-visit PWA coach
- Training sample pack `training-maintainer-001`
- PWA: search bar, boards, rate buttons, mesh/traffic panel

### Constraints preserved
Receive-only satellite  |  unlicensed mesh  |  no commercial decrypt  |  Apache-2.0

## 0.3.2 - Content request UX + physical mesh templates

- PWA **Request** tab: queue open-content pulls + mesh/gateway status panel
- `deploy/mesh/` batman-adv + dual-radio hostapd examples
- Marketing/dev docs aligned with Nexus field deploy

## 0.3.1 - Promo + open-pack plugins

- Cinematic brand still on README (`docs/assets/skycache-promo-cinematic.jpg`) + OG crop
- Plugins: `bulk_open_pack`, `open_data_hint`, `community_board`
- Village fabric installer: `deploy/install-village-fabric.sh`

## 0.3.0 - SkyCache Nexus (Phase 4)

Community Knowledge & Connectivity Fabric: multi-node mesh, DTN, distributed content, opportunistic legal gateway - still receive-only for satellite and unlicensed/ISM mesh only.

### Added

- **`skycache.nexus`** package:
  - Mesh fabric (sim + batman-adv probe, topology, power-prefer routes)
  - DTN priority queues + USB data-mule import/export
  - Content fabric gossip / prioritized replication / disaster flood
  - Opportunistic gateway manager with fair-share scheduler and daily quotas
  - Spectrum compliance helpers and honest product banner
  - Multi-node `NexusSimulator` (no RF hardware)
- **CLI:** `skycache mesh status`, `skycache gateway`, `skycache nexus doctor|sim|status`
- **API:** `/api/nexus/status|mesh|gateway|fabric`, `/api/nexus/request`, admin disaster + gateway pull
- **Docs:** `docs/mesh-deployment.md`, `docs/village-nexus-playbook.md`, architecture + legal updates
- **Tests:** `tests/test_nexus.py`, `tests/test_nexus_api.py`
- **Deploy notes:** multi-node / village fabric units and playbooks

### Strengthened

- Forbidden source keywords expanded (uplink / DRM / card-sharing)
- Config `validate_nexus()` for mesh mode and band
- UI/admin legal language: store-and-forward + community mesh, not free commercial broadband / Starlink

### Constraints preserved

- Satellite receive-only by default
- No commercial decryption
- Mesh TX unlicensed/ISM only
- Apache-2.0, solar-friendly, sim-first

## 0.2.0

Phase 1 file ingest, package tools, USB drop watch, portal PWA, sample packages, public release baseline.
