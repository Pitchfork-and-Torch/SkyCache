# Content packaging format

## Package directory

```
my-pack/
  manifest.json
  index.html          # optional
  images/...
  files/...
```

## manifest.json

```json
{
  "id": "health-ors-001",
  "kind": "html_pack",
  "priority_class": "health",
  "title": { "en": "Oral rehydration", "fr": "Réhydratation orale" },
  "summary": { "en": "Short educational flyer" },
  "languages": ["en", "fr"],
  "received_at": "2026-07-26T12:00:00+00:00",
  "freshness_hours": 8760,
  "size_bytes": 12345,
  "license": "CC-BY-4.0",
  "source": {
    "type": "operator_usb",
    "legal_note": "Open educational material",
    "plugin": "package_import"
  },
  "files": [
    { "path": "index.html", "mime": "text/html", "size_bytes": 1200, "role": "payload" }
  ],
  "tags": ["health"],
  "pinned": false,
  "icon": "health"
}
```

## priority_class values

`emergency` | `health` | `education` | `agriculture` | `weather` | `maps` | `general` | `telemetry_raw`

## Kiwix ZIM

Import registers the ZIM and documents serving via `kiwix-serve`. Full HTML extraction is not required for MVP.

## RACHEL / IIAB / Kolibri

Treat large trees as folder imports (`package_import`) or run those stacks **alongside** SkyCache on the same LAN and link them from a package `index.html`.

## Sample data

Generate demos:

```bash
python scripts/make_sample_package.py
```

Outputs under `samples/packages/`.
