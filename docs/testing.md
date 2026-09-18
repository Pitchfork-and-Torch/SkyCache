# Testing strategy

## Automated (CI)

```bash
python -m pip install -e ".[dev]"
python scripts/make_sample_package.py
pytest -q
ruff check skycache tests
```

| Suite | Covers |
|-------|--------|
| `test_prioritizer.py` | Class weights, freshness, eviction never drops emergency/pinned |
| `test_catalog.py` | SQLite upsert/list |
| `test_ingest.py` | Sample load + forbidden source keywords |
| `test_sim_pipeline.py` | `sim_file` batch path |
| `test_api.py` | Health, packages, admin PIN, portal HTML |
| `test_power.py` | SOC -> mode mapping |

CI runs on Ubuntu with Python 3.11/3.12 (see `.github/workflows/ci.yml`). No SDR hardware required.

## Simulation / offline RF

- Default demo uses `samples/packages/` (no IQ).  
- Optional: drop authorized recordings under `samples/iq/` (gitignored binaries).  
- Decode with SatDump first, then ingest images/packages.

## Hardware checklist (manual)

- [ ] `skycache doctor` shows Python OK  
- [ ] `rtl_test` or SoapySDR sees dongle (Phase 2)  
- [ ] hostapd AP associates a phone  
- [ ] Captive redirect opens portal  
- [ ] Admin shows disk free and package count  
- [ ] Power: mock gauge in sim; sysfs on supported boards  
- [ ] After a weather pass: new package appears with age chip  

## Signal quality

`SignalMonitor` holds last quality/SNR/message. Live plugins should call `update()` when available (Phase 2 wiring).
