# External decoder plugins

Drop-in plugins (Phase 2+) can live here. Built-in plugins ship inside `skycache/pipelines/plugins/`.

## Built-in (Nexus)

| Plugin | Role |
|--------|------|
| `sim_file` | Sample packages / demos |
| `satdump_weather` | FTA weather via SatDump |
| `gr_satellites` | Open amateur / CubeSat wrappers |
| `package_import` | Folder / ZIM / USB pack import |
| `bulk_open_pack` | Bulk open offline pack trees |
| `open_data_hint` | Operator catalog of lawful open hooks |
| `community_board` | Scaffold village-authored HTML packs |

## Contract

A plugin is a Python object with:

| Attribute / method | Meaning |
|--------------------|---------|
| `name` | Unique id (`my_wx`) |
| `description` | Human-readable |
| `legal_profile` | `fta_public` \| `amateur_open` \| `file_import_only` |
| `requires_hardware` | bool |
| `can_handle(source)` | bool |
| `run(source, workdir)` | returns `CaptureResult` |

## Hard rules

1. **No commercial decryption.** Plugins that target Starlink, OneWeb, or encrypted VSAT will be rejected.
2. Prefer wrapping mature tools (**SatDump**, **gr-satellites**) over reimplementing demodulators.
3. Document frequency, modulation, and legal basis in the plugin docstring.
4. Produce a `ContentPackage` via `CaptureResult.suggested_package` or a `manifest.json` tree.

See `docs/content-packaging.md` and `skycache/pipelines/base.py`.
