# First-boot wizard - village node in under 2 hours

**Audience:** technical volunteers on **Debian / Raspberry Pi OS** (and sim on any laptop).  
**Goal:** portal up, demo content loaded, admin PIN set, legal RF mode chosen, capabilities green.

> **Legal (always):** SkyCache is **receive-only** for satellite. Mesh uses **unlicensed/ISM** only.  
> It is **not** free Starlink / commercial broadband, and it will **not** decrypt paid services.  
> See [`legal-ethics.md`](legal-ethics.md) and [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md).

---

## Golden path (recommended)

### 0. Hardware checklist (demo)

| Item | Notes |
|------|--------|
| Pi 4/5 or Debian x86 box | 2 GB+ RAM, 16 GB+ storage |
| Ethernet or known Wi-Fi | Internet only needed for `apt` + `pip` |
| Optional: USB Wi-Fi AP dongle | For real hotspot later |
| Optional: RTL-SDR | Live weather later - **not** required for demo |

Time budget: ~30 - 90 min install + 15 min wizard + browse.

**Phone check (no cell plan):** After the portal is up, join the hub SSID from a phone with **mobile data off**, open the portal, tap **Save demos to this phone**. See [`phone-offline-demo.md`](phone-offline-demo.md).

### 1. Get the software on the device

```bash
# Option A - clone
sudo git clone https://github.com/Pitchfork-and-Torch/SkyCache.git /opt/skycache
cd /opt/skycache

# Option B - copy from USB
# sudo rsync -a /media/usb/SkyCache/ /opt/skycache/
```

### 2. One installer (village fabric)

```bash
cd /opt/skycache   # or your checkout
sudo bash deploy/install-village-fabric.sh
```

What it does:

1. Creates venv, installs SkyCache  
2. Creates `skycache` system user + `/var/lib/skycache`  
3. Installs/enables `skycache.service` with `EnvironmentFile`  
4. Runs **first-boot wizard** when possible (TTY or scripted PIN)  
5. Starts the portal on port **8080**

**Scripted / CI-style (no prompts):**

```bash
export SKYCACHE_ADMIN_PIN='738291'          # 4 - 8 digits, NOT 2468
export SKYCACHE_HOTSPOT_SSID='SkyCache-Demo'
export SKYCACHE_LEGAL_RF_MODE='receive_only' # safest default
export SKYCACHE_FIRST_BOOT_YES=1
sudo -E bash deploy/install-village-fabric.sh
```

### 3. First-boot wizard alone (if deferred)

```bash
sudo bash /opt/skycache/deploy/first-boot-wizard.sh
```

Non-interactive:

```bash
export SKYCACHE_ADMIN_PIN='738291'
export SKYCACHE_HOTSPOT_SSID='SkyCache-Village'
export SKYCACHE_LEGAL_RF_MODE='ism_mesh'   # only after checking local spectrum rules
export SKYCACHE_FIRST_BOOT_YES=1
sudo -E bash /opt/skycache/deploy/first-boot-wizard.sh --non-interactive
```

### 4. What the wizard asks / sets

| Choice | Purpose |
|--------|---------|
| **Admin PIN** | Protects `/admin` APIs (must change from default `2468`) |
| **SSID hint** | Printed in PWA onboarding; match hostapd when you enable AP |
| **legal_rf_mode** | Capability matrix rail (see table below) |
| **Sample packages** | Emergency / health / education demo packs |
| **Skybrary samples** | Short public-domain literacy texts (Library tab) |

Then it writes:

- `$DATA_DIR/skycache.env` (mode 600) - PIN, SSID, modes for systemd  
- `$DATA_DIR/first_boot.json` - completion marker  

...and prints a **capabilities summary** (ON/off + banned list).

### 5. Verify

```bash
sudo -u skycache /opt/skycache/.venv/bin/python -m skycache doctor --data-dir /var/lib/skycache
sudo -u skycache /opt/skycache/.venv/bin/python -m skycache capabilities --data-dir /var/lib/skycache
curl -s http://127.0.0.1:8080/api/status | head
# Open on phone or laptop:
# http://<device-ip>:8080/
```

PWA first visit: legal banner -> SSID coach -> categories -> Library (Skybrary samples) -> boards.

---

## legal_rf_mode choices

| Mode | When to use |
|------|-------------|
| `receive_only` | **Default first-boot.** Portal + USB; no mesh TX claim. |
| `ism_mesh` | After you confirm unlicensed Wi-Fi mesh is OK locally. |
| `ism_lora_control` | + low-BW LoRa/ISM control (regional limits apply). |
| `hybrid_gateway` | Mesh + fair-share **legal** client uplink for open pulls. |
| `amateur_operator` | Only with a real national amateur license + affirmation. |

**Never accepted:** starlink, sat uplink, commercial decrypt, jamming, etc.

Env: `SKYCACHE_LEGAL_RF_MODE`, `SKYCACHE_AMATEUR_LICENSE_AFFIRMED=true`.

---

## Laptop simulation (no Pi)

```bash
cd SkyCache
python3 -m pip install -e ".[dev]"
python3 -m skycache first-boot --data-dir data --yes --pin 739184 --ssid SkyCache-Sim \
  --legal-rf-mode receive_only --sim
python3 -m skycache serve --sim --host 127.0.0.1 --port 8080 --data-dir data
```

Windows PowerShell:

```powershell
cd $env:USERPROFILE\SkyCache
py -3 -m pip install -e ".[dev]"
py -3 -m skycache first-boot --data-dir data --yes --pin 739184 --ssid SkyCache-Sim --legal-rf-mode receive_only --sim
py -3 -m skycache serve --sim --host 127.0.0.1 --port 8080 --data-dir data
```

---

## CLI reference

```text
skycache first-boot [options]

  --data-dir PATH       default: data (Pi install uses /var/lib/skycache)
  --pin NNNN            required for --yes (not 2468)
  --ssid NAME           hotspot SSID hint
  --legal-rf-mode MODE  see table above
  --amateur-affirmed    with amateur_operator only
  --lang en|fr|es|...   language hint
  --env-file PATH       default: DATA/skycache.env
  --no-samples          skip demo packages
  --no-skybrary         skip PD literacy samples
  --sim                 capabilities report in sim mode
  --force               redo after first_boot.json exists
  --yes / --non-interactive
  --json                machine-readable result
```

Shell wrapper: `deploy/first-boot-wizard.sh`  
Installer: `deploy/install-village-fabric.sh`  
Classic single-node: `deploy/install-debian.sh` (then run wizard)

---

## Optional Wi-Fi hotspot (after first-boot)

1. Copy `deploy/hotspot/hostapd.conf.example` -> `/etc/hostapd/hostapd.conf`  
2. Set `ssid=` to the **same string** as the wizard SSID hint  
3. Static IP `10.0.0.1/24` on AP interface; enable `hostapd` + `dnsmasq`  
4. Check **local regulations** before enabling AP  

Details: [`installation.md`](installation.md), [`mesh-deployment.md`](mesh-deployment.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Wizard refuses PIN | Must be 4 - 8 digits and **not** `2468` |
| `first-boot already completed` | `--force` or delete `$DATA_DIR/first_boot.json` |
| Empty portal | Re-run wizard or `skycache init --load-samples` |
| Admin 401 | Header `X-Admin-Pin` must match env PIN |
| amateur_operator rejected | Pass `--amateur-affirmed` / `SKYCACHE_AMATEUR_LICENSE_AFFIRMED=true` |
| Forbidden mode error | You asked for sat-uplink / starlink / decrypt - refused by design |
| systemd ignores PIN | Confirm `EnvironmentFile=-/var/lib/skycache/skycache.env` in unit; `daemon-reload` + restart |

---

## Time box: demo in &lt;2 hours

| Step | ~Minutes |
|------|----------|
| Flash OS / SSH / apt | 20 - 40 |
| Clone + install-village-fabric | 15 - 30 |
| First-boot wizard | 5 - 10 |
| Browse portal + Library + boards | 15 |
| Optional hostapd SSID | 15 - 30 |
| **Total** | **~1 - 2 h** |

Mesh (batman-adv), live SDR, and gateway pulls are **later** - see village playbook. Demo success = portal + samples + honest legal banner + PIN changed + `capabilities` readable.

---

## v0.8.0 aftercare (Village Ready)

Once the portal is up:

1. **Admin -> Power maintainer sheet** - print for the wall (`/api/power/maintainer-sheet`)
2. **Admin -> License inventory** - print / Save as PDF for partners
3. **Build USB kit** - profile `literacy-1gb` or `emergency-health` (signed manifest)
4. **Export handoff** - QR on same Wi-Fi for phone copy
5. **Mesh acceptance (lab):** `skycache nexus validate --nodes 2`
6. Partner scaffolding: [`partner-kits.md`](partner-kits.md)

Upgrade from 0.7.x: reinstall package only; existing `data/` needs no migration.
