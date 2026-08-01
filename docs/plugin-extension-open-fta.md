# Extending SkyCache with open free-to-air (FTA) plugins

**Legal spine:** `docs/legal-ethics.md`. Receive-only. Unencrypted free-to-air or openly licensed content only. Never commercial encrypted satellite systems (Starlink, OneWeb, paid VSAT, CAS decryption).

## Goals

- Make new *true open* sources easy to add without touching commercial systems.
- Keep every plugin fully testable with `--sim` and zero RF hardware.
- Fail closed on forbidden keywords and missing licenses.

## Plugin contract

See `skycache/pipelines/base.py` (`DecoderPlugin` protocol):

| Field / method | Meaning |
|----------------|---------|
| `name` | CLI / SourceSpec plugin id |
| `description` | Operator-facing one-liner |
| `legal_profile` | `fta_public` \| `amateur_open` \| `file_import_only` |
| `requires_hardware` | If true, skipped automatically in `sim_mode` (except sim plugins) |
| `can_handle(source)` | Match plugin name / open URI only |
| `run(source, workdir)` | Write artifacts + optional `ContentPackage` |

Register instances in `skycache/pipelines/plugins/__init__.py` → `BUILTIN_PLUGINS`.

## Example: open FTA simulation (shipped)

```text
skycache pipeline --plugin open_fta_sim --uri open-fta-sim
# or SourceSpec(plugin="open_fta_sim")
```

Module: `skycache/pipelines/plugins/open_fta_sim.py`

- Produces a weather/education bulletin package + `license-passport.json`
- Refuses URIs/options containing commercial decrypt hints
- `requires_hardware = False` so CI and village demos work offline

## Adding a real open decoder (pattern)

1. Copy `open_fta_sim.py` → `my_open_source.py`.
2. Set `legal_profile = "fta_public"` (or `amateur_open` for lawful amateur telemetry).
3. In `run()`, call only open tools (SatDump wrappers already exist for weather).
4. Write `manifest.json` via `ContentPackage` with honest `source.legal_note`.
5. Always attach a license passport for redistribute flags.
6. Add pytest with `Settings(sim_mode=True)` and assert forbidden names fail.
7. Document national spectrum notes for operators (receive-only is usually fine; confirm).

## What never belongs in a plugin

- Commercial constellation decrypt, reverse-engineering, or uplink.
- Silent fetch of paywalled catalogs.
- Claims of free Starlink / unlimited cellular.

## Related

- `docs/legal-pathways-rf-and-content.md`
- `docs/phase2-live-rx.md`
- `skycache/pipelines/plugins/satdump_weather.py`
- `skycache/pipelines/plugins/gr_satellites_wrapper.py`
