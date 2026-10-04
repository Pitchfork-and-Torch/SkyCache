# v0.9.0 Skybrary Live  -  success criteria evidence

| Criterion | Evidence |
|-----------|----------|
| Dual-access catalog schema unified | `skycache.skybrary.catalog.v2` in `catalog_export.py`; site loads `skybrary-catalog.json` |
| Connected browse/search + facets | Site `/library/` + export `index.html`; language/subject/license filters |
| Work detail + license passport | `/library/works/[workId]/` static pages; passport panel |
| Starter kits with license pages | `export-catalog --starter-kits` -> `packs/*.zip` + passport + license HTML |
| Same works offline | `skybrary samples --ingest` / first-boot; FTS; pack profiles; sim |
| Curated corpus substance | ~18 PD works in `sample_corpus.py`; `tests/test_v090_skybrary_live.py` |
| Gutenberg catalog adapter | `gutenberg_catalog.py` + CLI; fixture CI path `--allow-local` |
| API parity | `GET /api/skybrary/catalog.json`, `/api/skybrary/kits` |
| Legal matrix | `skybrary_gutenberg_catalog`, `skybrary_dual_access_export` |
| Tests green | `pytest -q` (88+ tests) |
| Version 0.9.0 | `__init__.py`, `pyproject.toml`, CHANGELOG, site `SITE.softwareVersion` |
| Site overhaul | Homepage CTAs, phase 0.9, llms.txt, library UX |
| Upgrade from 0.8.0 | No data migration; additive packages |
| Honest remaining gaps | Pi image, batman OOB, OA science bulk, EPUB reader  -  CHANGELOG / NEXT-STEPS |

## Commands

```bash
pytest -q
python -m skycache skybrary samples --ingest --data-dir data
python -m skycache skybrary export-catalog --out data/catalog-export --starter-kits
python -m skycache skybrary import-gutenberg-catalog --catalog tests/fixtures/gutenberg/catalog.json --allow-local --dry-run
python -m skycache serve --sim --host 127.0.0.1 --port 8080
```

## Site redeploy

```powershell
cd $env:USERPROFILE\skycache-web
# ensure public/skybrary-catalog.json + public/library/packs/ from software export
npm run build
npx wrangler pages deploy out --project-name=skycache-jonbailey --commit-dirty=true
```
