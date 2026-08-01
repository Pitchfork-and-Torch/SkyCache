# Hardware bill of materials (BOM)

Approximate **2026 USD** street prices - verify locally. Prefer repairable parts.

## MVP kit (demo + portal + future VHF weather)

| Item | Qty | Approx. USD | Notes |
|------|-----|-------------|--------|
| Raspberry Pi 4/5 2 - 4 GB **or** used x86 mini PC | 1 | 35 - 80 | Used laptops often win on price/availability |
| MicroSD 64 - 128 GB (A2) or USB SSD | 1 | 10 - 25 | Keep a clone image on a second card |
| RTL-SDR Blog V3/V4 or quality clone | 1 | 25 - 40 | SoapySDR / rtl-sdr compatible |
| V-dipole or QFH for ~137 MHz | 1 | 5 - 30 DIY | Copper wire + PVC; many FOSS plans |
| Coax + adapters (SMA/MCX as needed) | 1 set | 5 - 15 | Keep runs short |
| 5 V supply ≥3 A (or power bank for demos) | 1 | 10 - 20 | Official Pi PSU preferred |
| Optional USB WiFi AP dongle | 1 | 10 - 20 | If onboard WiFi AP is unreliable |
| Weatherproof box / dust cover | 1 | 10 - 25 | Critical outdoors |
| **MVP subtotal** | | **~$90 - 180** | Without solar |

## Solar village option

| Item | Qty | Approx. USD | Notes |
|------|-----|-------------|--------|
| Solar panel 40 - 100 W | 1 | 30 - 80 | Tilt toward sun; theft-resistant mount |
| MPPT or PWM charge controller | 1 | 15 - 40 | Match panel voltage |
| LiFePO4 12 V 20 - 50 Ah | 1 | 80 - 180 | Safer chemistry than random packs |
| 12 V->5 V buck converter | 1 | 8 - 20 | Sized for SBC + SDR peak |
| Fuses, wiring, MC4, grounding | 1 set | 15 - 30 | Fuse near battery |
| **Solar add-on** | | **~$150 - 300** | |

## Advanced L-band weather (GOES HRIT region-dependent)

| Item | Approx. USD | Notes |
|------|-------------|--------|
| Dish + L-band feed / patch | 40 - 120 | Aiming required |
| LNA + filter ~1.69 GHz | 30 - 80 | Huge impact on SNR |
| Extra cabling / mount | 20 - 40 | |

Only pursue if your geography and training support it. VHF LEO weather or **file/USB content** already delivers value.

## Sourcing notes (developing regions)

- Check **local computer markets** for used SBCs/laptops before importing Pis.  
- RTL-SDR: prefer known resellers to avoid silent serial failures.  
- NGOs: bulk buy SD cards + identical enclosures for maintainability.  
- Document serial numbers and a photo of the wiring for remote support.

## What you do **not** need

- Starlink kit  
- Expensive spectrum analyzers  
- Always-on internet for the hub to serve clients  
