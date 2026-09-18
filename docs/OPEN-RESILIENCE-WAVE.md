# Open Resilience Wave (v1.33)

Four workstreams advancing SkyCache / Skybrary as dual-access open knowledge infrastructure. **Honest scope:** store-and-forward open knowledge + community mesh - not free commercial broadband.

## 1. Corpus expansion

- Wave 6 STEM / civics / heritage samples (`sample_corpus_stem.py`)
- Curated sample count: 68 → **78**
- License passports remain fail-closed (`assert_license_allowed`)
- Per-sample license override supported at package build time

### Operator

```text
skycache skybrary samples --out samples/skybrary
skycache library publish --out data/catalog-publish
skycache library pack-budgets
skycache library pack-kits --out data/library-pack-kits
skycache library sync --with-packs --apply-web
```

## 2. Offline resilience and federation

- Prioritizer `disaster_mode` / `power_critical` protect **emergency + health** under disk pressure
- Archive / telemetry evicted first; education still flows when space remains
- `priority_works_delta()` pulls missing peer works survival-first over mesh/USB gossip
- Local ops snapshot already includes bit-rot schedule status (no cloud telemetry by default)

## 3. Modular open decoding

- New plugin: `open_fta_sim` (zero-hardware open FTA educational bulletin)
- Extension guide: `docs/plugin-extension-open-fta.md`
- Forbidden commercial/decrypt hints fail closed

## 4. Dual-access packaging and discovery

- Pack profiles: `archive-100mb`, `archive-1gb` (plus existing literacy/clinic/STEM)
- Default pack-kits include stem-lite + archive-100mb
- `skycache library pack-budgets` lists size gates for operator planning
- Same corpus → online catalog JSON + offline USB zips

## Legal rails (non-negotiable)

See `docs/legal-ethics.md`. Receive-only. Open/FTA/PD/CC only. No commercial constellation decrypt.
