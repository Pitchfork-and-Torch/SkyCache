# SkyCache - PROGRESS / STATE

**Last cycle:** 2026-07-28  
**Software version:** 0.8.0 (Village Ready + Skybrary Dual-Access)  
**Public site:** https://skycache.jonbailey.xyz/  
**Repo:** https://github.com/Pitchfork-and-Torch/SkyCache

---

## State assessment (this cycle)

| Layer | Strength | Gap |
|-------|----------|-----|
| Legal rails | Strong matrix + validators | Multi-lang operator education |
| Offline node | First-boot, packs 2.0, PWA | Golden Pi SD image |
| Nexus fabric | Sim multi-node + validate | Real batman-adv day-one |
| Skybrary | S0 - S2 + S3 profiles + export | Searchable online catalog polish (in progress), bulk corpora |
| Dual access | `export-catalog` foundation | Site `/library/` ship + R2 packs |
| Ops | Rich CLI | Privacy-preserving fleet (opt-in only) |

Legal rails non-negotiable: receive-only, FTA/open only, ISM mesh TX, no commercial decrypt, no false free-Starlink claims.

---

## Work performed this cycle

1. **B1 online catalog UX:** `skybrary/catalog_export.py` `_catalog_html` now ships a **searchable** dual-access page:
   - Client-side search (title/author/subject/id)
   - Language + license filters
   - Works embedded as `application/json` (no third-party JS CDN)
   - Dark-mode friendly, honest legal banner
2. Tests: `test_catalog_export_and_provenance` asserts search UI + works-data + legal copy (pass).
3. Dual-project autonomous loop state files created (`PROGRESS.md`).

---

## Next cycle intent (execute immediately)

Priority order (highest leverage, legal):

1. **Ship catalog to marketing site** - run `skycache skybrary export-catalog --out ...` and publish under `skycache-web` `/library/` (or static copy); redeploy site.
2. **Gutenberg open catalog adapter** (operator-run batch index; robots/terms respect; license gate).
3. **Partner-kit PDF / printable disaster drill pack** (D4).
4. Mesh field: document OpenWrt dual-radio proof checklist video path.

```powershell
cd $env:USERPROFILE\SkyCache
py -3 -m pytest tests/test_v080_village_ready.py -q
py -3 -m skycache skybrary samples
py -3 -m skycache skybrary export-catalog --out data/catalog-export
# then copy index.html+catalog.json into skycache-web public/library and deploy
```

---

## Version note

Catalog search HTML is compatible with 0.8.0 export API - no version bump required until site ship or corpora pipeline lands. Recommend **0.8.1** when `/library/` goes live on skycache.jonbailey.xyz.
