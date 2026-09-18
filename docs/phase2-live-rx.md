# Phase 2 - Live free-to-air weather RX (production runbook)

**Status (v1.2.0):** real operator loop + **Pass Autopilot** - station config, pass planning, recipe-bound schedule, arm/duty board, SatDump CLI sketches, product **watch/auto-ingest**, auto field-log when armed, RX doctor, recipes, capture wrap.

Goal: after a satellite pass, at least one **real** weather product appears in the SkyCache portal using **SatDump** + RTL-SDR (or SoapySDR). Simulation remains available for demos without hardware.

## Legal (non-negotiable)

- Receive-only, **unencrypted free-to-air** weather only.
- Open amateur/CubeSat telemetry (gr-satellites) is educational only.
- **No** commercial constellation decryption (Starlink, OneWeb, paid VSAT).
- Confirm local spectrum / outdoor antenna rules.
- See `legal-ethics.md` and `threat-model.md`.

## Real-world day-one path (recommended)

Do **not** require SkyCache to own the live USB session. Proven path used by operators:

```text
[RTL-SDR + antenna] -> SatDump (GUI/CLI) -> product folder (PNG/JPG)
                                              |
                                              v
                         skycache rx watch --dir PRODUCT_DIR --once
                                              |
                                              v
                              Local portal Weather category
```

### 1. Doctor

```bash
skycache rx doctor
# wants: satdump and/or product import path; rtl_test/Soapy when doing live RX
```

### 2. Station

```bash
skycache rx station --lat 40.7128 --lon -74.0060 --alt-m 20 \
  --name "school-roof" --antenna "V-dipole 137 MHz"
```

### 3. Pass plan

```bash
# Optional real geometry:
pip install sgp4
# Import TLEs you are allowed to use (Celestrak etc. under their terms - no scrape in SkyCache)
skycache rx tle-import my-weather-tles.txt
skycache rx passes --hours 24 --min-elev 20
```

Without `sgp4`, `rx passes` returns a **fixture** schedule and tells you to install sgp4 - CI-safe, not a fake claim of perfect tracking.

### 4. Capture the pass with SatDump

```bash
# Example offline IQ path after recording (pipeline names vary by SatDump version)
skycache rx recipes   # see noaa_apt, meteor_lrpt, goes_hrit
satdump <pipeline> /path/to/baseband /path/to/products
# Or use SatDump GUI live during the pass.
```

### 5. Ingest into SkyCache

```bash
# One-shot after the pass
skycache rx watch --dir /path/to/products --once --satellite "NOAA 18"

# Or single file
skycache rx import /path/to/products/image.png --satellite "NOAA 18"

# Or decode+ingest via plugin wrap
skycache rx capture --recipe product_import --input /path/to/image.png
```

### 6. Field log (required for real ops)

```bash
skycache rx log --satellite "NOAA 18" --elevation 42 --quality good \
  --recipe noaa_apt --notes "clear south, V-dipole" --package-id wx-...
skycache rx log --list
```

### 7. Always-on village node

**Linux (systemd):**

```bash
# deploy/rx/skycache-rx-watch.service
sudo systemctl enable --now skycache-rx-watch.service
```

**Windows (this machine / lab PC):**

```powershell
cd $env:USERPROFILE\SkyCache

# Install SatDump (winget) + rtl-sdr CLI tools + User PATH
powershell -ExecutionPolicy Bypass -File .\scripts\Install-RxTools-Windows.ps1

# One-time setup: sgp4, TLEs, station, products folder
powershell -ExecutionPolicy Bypass -File .\scripts\Setup-RxStation.ps1 -Lat YOUR_LAT -Lon YOUR_LON -RefreshTle

# Verify stack (satdump + rtl_test on PATH; rtl_device_seen needs a dongle)
py -3 -m skycache rx doctor --data-dir data

# Point SatDump product output at:
#   data\satdump-products\

# After a pass (or test file drop):
powershell -ExecutionPolicy Bypass -File .\scripts\Start-RxWatch.ps1 -Once

# Continuous poll in a terminal:
powershell -ExecutionPolicy Bypass -File .\scripts\Start-RxWatch.ps1

# Optional: Scheduled Task every 5 minutes
powershell -ExecutionPolicy Bypass -File .\scripts\Install-RxWatch-Task.ps1

# Pass Autopilot (v1.2.0): bind passes to recipes, arm station, print SatDump sketch
py -3 -m skycache rx schedule --data-dir data --hours 24
py -3 -m skycache rx arm --data-dir data --hours 12
py -3 -m skycache rx cmd --data-dir data --next-pass
py -3 -m skycache rx duty --data-dir data
# After products land with arm active, watch auto-appends field-log rows
```

Refresh TLEs (do not hammer Celestrak):

```powershell
py -3 .\scripts\refresh_fta_tles.py --out data\tle-fta-priority.txt
py -3 -m skycache rx tle-import data\tle-fta-priority.txt --data-dir data
```

## Hardware (minimum VHF path)

- RTL-SDR Blog V3/V4 (or quality clone) recognized by the OS
- V-dipole or QFH for ~137 MHz, outdoor with clear sky view
- Short low-loss coax + correct adapters
- SBC or laptop powered stably (prefer AC while learning)
- Optional: ground the mast; keep water out of connectors

L-band GOES HRIT needs dish + LNA + filter - advanced only (`goes_hrit` recipe).

## Software install

```bash
sudo apt-get update
sudo apt-get install -y rtl-sdr soapysdr-tools
# SatDump: https://www.satdump.org/ or https://github.com/SatDump/SatDump
pip install sgp4   # optional, for real pass geometry
python -m skycache rx doctor
```

## API (portal / admin tools)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/rx/status` | Doctor + station + signal snapshot |
| `GET /api/rx/recipes` | Legal FTA recipes |
| `GET /api/rx/passes` | Upcoming passes (needs station) |
| `GET /api/rx/schedule` | Pass Autopilot: passes + recipe binding + SatDump sketches |
| `GET /api/rx/duty` | Duty board: arm + next pass countdown |
| `GET /api/rx/arm` | Current arm state |
| `POST /api/rx/arm` | Arm (`hours`, `auto_field_log`) or `{ "disarm": true }` |
| `GET /api/rx/field-log` | Recent field notes |
| `POST /api/rx/import` | Ingest product path |

## Acceptance criteria (Phase 2 live)

1. `skycache rx doctor` runs on the field laptop/Pi.
2. At least one **live-derived** weather image appears in the portal after a real pass (not only sim samples).
3. Field log entry exists for that pass (satellite, elevation, quality, date).
4. Legal banners unchanged; no commercial broadband claims.
5. Product watch can run as a systemd service on the village node.
6. `skycache rx schedule` binds passes to recipes; `rx arm` + `rx watch` can auto field-log (v1.2.0).

## Explicit non-goals

- Decrypting commercial satellite internet
- Guaranteeing SatDump pipeline names across all SatDump versions (aliases listed; verify locally)
- Replacing SatDump's demodulators inside SkyCache
