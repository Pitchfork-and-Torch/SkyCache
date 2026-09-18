# Phase 1 - File ingest & local portal

Phase 1 makes SkyCache useful **without live RF**: operators load education packs, images, and ZIM files; the hub serves them on WiFi.

## Create a package

```bash
python -m skycache package create \
  --id health-handwash-001 \
  --title "Hand washing guide" \
  --priority health \
  --summary "Clinic poster for students" \
  --out /tmp/health-handwash-001 \
  --file ./poster.html \
  --ingest
```

Validate before sharing USB sticks:

```bash
python -m skycache package validate /path/to/package-dir
```

## Ingest paths

```bash
# Single package directory (manifest.json required)
python -m skycache ingest /media/usb/my-pack

# ZIM (registers file + README for kiwix-serve)
python -m skycache pipeline --plugin package_import --uri /media/usb/wikipedia_en.zim

# Weather PNG already decoded by SatDump
python -m skycache pipeline --plugin satdump_weather --uri /tmp/goes.png
```

## USB / drop folder

After `skycache init`, packages can be copied to:

```text
<data-dir>/drop/incoming/
```

Then:

```bash
# One-shot
python -m skycache watch --once

# Continuous (every 15s)
python -m skycache watch --interval 15
```

Processed items move to `drop/done/` or `drop/failed/`.

Supported drop items:

| Item | Action |
|------|--------|
| Directory with `manifest.json` | Full package ingest |
| `*.zim` | package_import plugin |
| `*.png` / `*.jpg` | satdump_weather file import |

Admin API (PIN header `X-Admin-Pin`):

```http
POST /api/admin/drop-scan
POST /api/admin/pipeline   {"plugin":"sim_file","uri":""}
POST /api/admin/ingest?path=/path
```

## Hotspot (Pi / Debian)

```bash
sudo bash deploy/install-debian.sh
sudo bash deploy/enable-hotspot.sh
# optional: SKYCACHE_WIFI_IFACE=wlan1 SKYCACHE_SSID=SkyCache-School
```

Confirm local regulations before enabling an AP.

## Phase 1 acceptance

- [ ] Create + validate + ingest a custom package without RF  
- [ ] Drop-folder one-shot works from a USB path  
- [ ] Portal shows new content with correct priority class  
- [ ] Hotspot script associates a phone (lab)  
- [ ] Admin drop-scan returns processed ids  
