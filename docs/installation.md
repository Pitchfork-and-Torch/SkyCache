# Installation & deployment

**Village demo in &lt;2 hours:** prefer the **golden path** in [`first-boot.md`](first-boot.md)  
(`deploy/install-village-fabric.sh` + first-boot wizard).

## A. Simulation mode (any laptop - start here)

**Windows (PowerShell):**

```powershell
cd $env:USERPROFILE\SkyCache
py -3 -m pip install -e ".[dev]"
py -3 scripts\make_sample_package.py
py -3 -m skycache first-boot --data-dir data --yes --pin 739184 --ssid SkyCache-Sim --legal-rf-mode receive_only --sim
# or classic: py -3 -m skycache init --load-samples
py -3 -m skycache serve --sim --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080/

**Linux / macOS:**

```bash
cd SkyCache
python3 -m pip install -e ".[dev]"
python3 scripts/make_sample_package.py
python3 -m skycache first-boot --data-dir data --yes --pin 739184 \
  --ssid SkyCache-Sim --legal-rf-mode receive_only --sim
python3 -m skycache serve --sim --host 127.0.0.1 --port 8080
```

Or: `bash scripts/run_sim_demo.sh`

### Checks

```bash
python -m skycache doctor
python -m skycache capabilities
python -m pytest -q
```

## B. Raspberry Pi / Debian hub (golden path)

1. Flash Raspberry Pi OS (Bookworm) 64-bit, enable SSH, set locale/timezone.  
2. Copy or clone SkyCache onto the Pi.  
3. Run the village fabric installer (includes first-boot when possible):

```bash
sudo bash deploy/install-village-fabric.sh
# If wizard deferred:
sudo bash deploy/first-boot-wizard.sh
```

Scripted PIN (no prompts):

```bash
export SKYCACHE_ADMIN_PIN='738291'   # not 2468
export SKYCACHE_FIRST_BOOT_YES=1
sudo -E bash deploy/install-village-fabric.sh
```

4. Browse to `http://<pi-ip>:8080/`.  
5. Confirm `skycache capabilities` and that admin PIN is **not** the default.

### Classic single-node installer

```bash
sudo bash deploy/install-debian.sh
sudo bash deploy/first-boot-wizard.sh   # set PIN + legal mode + samples
```

### Optional WiFi hotspot

1. Use a supported WiFi adapter in AP mode.  
2. Copy examples from `deploy/hotspot/`.  
3. Give the AP interface a static IP `10.0.0.1/24`.  
4. Enable `hostapd` and `dnsmasq`.  
5. Phones should captive-redirect to the portal (HTTP).  

**Verify local regulations** before operating an AP.

### Optional SatDump (live weather - Phase 2)

Install SatDump from upstream packages or source ([satdump.org](https://www.satdump.org) / GitHub `SatDump/SatDump`).  
Decode a pass, then:

```bash
python -m skycache pipeline --plugin satdump_weather --uri /path/to/image.png
# or package a folder with manifest.json and:
python -m skycache ingest /path/to/package_dir
```

## C. Solar

See `deploy/solar-power-notes.md` and `hardware-bom.md`.

## D. Ingest USB education content

```bash
# SkyCache package folder with manifest.json
python -m skycache ingest /media/usb/my-pack

# Or ZIM registration (serve with kiwix-serve separately)
python -m skycache pipeline --plugin package_import --uri /media/usb/wikipedia_en.zim
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Empty portal | `skycache first-boot --force ...` or `skycache init --load-samples` |
| Port in use | `--port 8081` |
| Admin 401 | Header `X-Admin-Pin` must match `SKYCACHE_ADMIN_PIN` (after first-boot, not default) |
| No SatDump | Expected in Phase 0; sim still works |
| Wizard refuses PIN | Must be 4 - 8 digits and **not** `2468` - see [`first-boot.md`](first-boot.md) |
