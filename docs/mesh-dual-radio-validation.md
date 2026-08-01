# Dual-radio validation (all board models)

**v0.9.2**  -  Shared day-one proof for batman-adv + client AP topologies.

Legal: unlicensed Wi-Fi/ISM only. Receive-only satellite. Not free commercial broadband.

## Generate the validation pack

```bash
skycache mesh dual-radio-pack --out media/dual-radio-validation
# Opens as HTML storyboard; optional FFmpeg slideshow if ffmpeg installed
```

Outputs:

| File | Role |
|------|------|
| `board-matrix.json` | Pi 4/5, 3B+, Orange Pi, OpenWrt pair, sim laptop |
| `storyboard.html` | Frame-by-frame dual-radio procedure (all models) |
| `frames/*.svg` | 1280×720 slides for video tooling |
| `render-slideshow.sh` | Optional FFmpeg render |
| `dual-radio-validation.mp4` | Produced when ffmpeg available |

## Shared steps (every board)

1. Spectrum / legal check for outdoor EIRP  
2. Identify `MESH_IF` vs `CLIENT_IF` (`ip link`, `iw dev`)  
3. `DRY_RUN=1 bash deploy/mesh/batman-day-one.sh`  
4. Root apply: `sudo MESH_IF=... CLIENT_IF=... bash deploy/mesh/batman-day-one.sh`  
5. `batctl n` (or OpenWrt equivalent) shows peer  
6. Phone joins client SSID -> portal Library  
7. Always: `skycache nexus validate --nodes 2` (sim, zero RF)

## Board matrix (summary)

| Board | Status |
|-------|--------|
| Raspberry Pi 4 (2 - 4 GB) | primary_supported |
| Raspberry Pi 5 | primary_supported |
| Raspberry Pi 3B+ | supported_limited |
| Orange Pi 5 / RK3588 | community |
| OpenWrt AP pair + Pi Ethernet | recommended_field |
| Laptop / CI sim | always_green |

Full notes: `media/dual-radio-validation/board-matrix.json` after generate.

## Honest scope

We do **not** claim a filmed lab session on every PCB revision. We **do** ship one shared validation storyboard + per-board notes so operators can prove dual-radio day-one on the hardware they have.
