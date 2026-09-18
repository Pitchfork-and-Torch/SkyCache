# Golden Raspberry Pi SD image (v1.4 Golden Node Bake Ops)

**Goal:** A volunteer can flash one microSD, boot a Pi, and have a village-ready SkyCache node with samples, first-boot rails, partner readiness, and optional mesh/RX hooks.

**Legal:** Receive-only satellite. Unlicensed mesh only after spectrum check. **Never** ship default admin PIN `2468` on field images. Not free commercial broadband.

**Honest about images:** This repo ships a **kit** (scripts + plan). Multi-GB sealed `.img.xz` files are built by operators on Linux and hosted elsewhere; register with `skycache pi-image sealed-manifest`.

## CLI

| Command | Role |
|---------|------|
| `skycache pi-image doctor` | Host readiness: kit path vs seal path |
| `skycache pi-image plan` | JSON bake plan v2 (works on Windows/CI) |
| `skycache pi-image write --out DIR` | Plan + verify script + SEAL-CHECKLIST.md |
| `skycache pi-image seal-checklist --out DIR` | Seal checklist only |
| `skycache pi-image bundle --out DIR` | Public golden-SD kit zip |
| `skycache pi-image hash PATH` | SHA-256 a local sealed image |
| `skycache pi-image sealed-manifest --url HTTPS --sha256 HEX` | Register operator-hosted image metadata |

## Recommended bake (on the Pi)

1. **Flash** Raspberry Pi OS **Lite 64-bit** with [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
   - Enable SSH, set hostname `skycache-village`, set user
2. Boot Pi on Ethernet/LAN
3. Clone or copy SkyCache tree (or the golden kit zip)
4. Run:

```bash
export SKYCACHE_ADMIN_PIN='your-strong-pin'   # never 2468
sudo bash deploy/pi-image/bake-golden.sh
# or stepwise:
sudo bash deploy/install-village-fabric.sh
sudo -u skycache /opt/skycache/.venv/bin/skycache first-boot \
  --yes --pin "$SKYCACHE_ADMIN_PIN" \
  --ssid SkyCache-Village \
  --legal-rf-mode receive_only --sim
sudo systemctl enable --now skycache.service
bash bake/golden-pi-verify.sh   # or path from pi-image write
skycache partner readiness
```

5. **Optional mesh day-one** (dual radio + spectrum OK):

```bash
sudo MESH_IF=wlan0 CLIENT_IF=wlan1 bash deploy/mesh/batman-day-one.sh
```

6. **Optional seal** for fleet clones (Linux host with SD reader):

```bash
# power off Pi; identify device carefully
sudo dd if=/dev/sdX bs=4M status=progress | xz -T0 > skycache-village-pi.img.xz
skycache pi-image hash skycache-village-pi.img.xz
skycache pi-image sealed-manifest \
  --url https://YOUR_HOST/skycache-village-pi.img.xz \
  --path skycache-village-pi.img.xz \
  --out data/pi-download/sealed-manifest.json
```

After each clone: **change admin PIN** and re-run readiness.

## CI / Windows

```bash
skycache pi-image doctor
skycache pi-image plan
skycache pi-image write --out data/pi-bake
skycache pi-image bundle --out data/pi-download
```

Does **not** write a raw `.img` on Windows.

## Public download

```bash
skycache pi-image bundle --out data/pi-download
# Copy data/pi-download/skycache-golden-sd-kit.zip to:
#   skycache-web/public/downloads/
```

Live kit: https://skycache.jonbailey.xyz/downloads/skycache-golden-sd-kit.zip  
Install guide: https://skycache.jonbailey.xyz/install/

## Acceptance

- [ ] `curl http://<pi>:8080/api/health` -> ok
- [ ] Library shows Skybrary samples
- [ ] Admin PIN is not 2468 / 0000 / 1234
- [ ] `skycache partner readiness` go_sim_pilot true
- [ ] `skycache capabilities` lists legal matrix
- [ ] License inventory printable
