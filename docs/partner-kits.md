# Partner kits (NGO pilot + university contribution)

Scaffolding for institutional adoption. Software is Apache-2.0; content remains subject to each package license passport.

**Status (v1.3.0 Partner Pilot Ops):** zip packaging, package-all for site hosting, pilot-report validation, local readiness score, public site `/partners/`.

## Generate a pilot kit folder

```bash
skycache partner kit --type ngo --out data/partner-kit-ngo --zip
skycache partner kit --type university --out data/partner-kit-uni --zip
skycache partner kit --type civil-protection --out data/partner-kit-cp --zip

# All three + HOSTING.json (for skycache.jonbailey.xyz/downloads/partner-kits/)
skycache partner package-all --out data/partner-kits

# Lab go/no-go
skycache partner readiness --data-dir data

# After field day
skycache partner report validate pilot-report.json
```

Each kit includes `CHECKLIST.md` / `CHECKLIST.html`, `LEGAL-ONE-PAGER.md`,
`TRAINING-HALF-DAY.md`, `FIELD-DAY.md`, `pilot-report.template.json`, and copies of key docs
(including threat-model + phase2-live-rx when present).

## NGO pilot kit (half-day + weekend install)

### Hardware (see also `hardware-bom.md`)
- 1 - 3× Raspberry Pi 4/5 or Orange Pi (2 - 4 GB RAM) + 32 - 128 GB microSD
- USB Ethernet or built-in; optional second radio for mesh
- Commodity AP or hostapd on-board Wi-Fi
- Small solar + battery (document Wh for power sheet accuracy)
- USB sticks for mule handoff

### Software path (weekend demo)
1. Flash Debian/Raspberry Pi OS (lite OK)
2. `sudo bash deploy/install-village-fabric.sh` (or pip install + first-boot)
3. `skycache first-boot --yes --pin <new> --ssid SkyCache-Village --legal-rf-mode receive_only --sim` for lab; field mesh -> `ism_mesh` after spectrum check
4. `skycache serve --sim` (lab) or systemd unit from deploy/
5. Phone: join SSID -> portal onboarding -> Library -> Save demos
6. Admin: Build USB kit (`emergency-health` or `literacy-1gb`), Export handoff, print license inventory + power sheet
7. Optional: `skycache nexus validate --nodes 2` then physical 2-node checklist (`mesh-field-checklist.md`)

### Training half-day outline
| Block | Topic |
|-------|--------|
| 30m | Honest mission: store-and-forward, not free Starlink |
| 30m | Legal rails + capability matrix walkthrough |
| 45m | First-boot + portal + Skybrary Library |
| 30m | Pack profiles + USB handoff + QR |
| 30m | Power modes + maintainer sheet |
| 30m | Disaster drill dry-run (`disaster-drill.md`) |

### Legal one-pager for partners
- Receive-only satellite; no commercial decrypt
- Mesh TX unlicensed/ISM only (unless amateur affirmed)
- Every pack has license + provenance; unknown licenses need review
- No personal-data harvesting; no cloud accounts required
- Contact: skycache@jonbailey.xyz  |  https://skycache.jonbailey.xyz

---

## University contribution kit

### Goals
- Students contribute **public-domain / open-license** corpora with passports
- Optional: maintain a lab multi-node sim; write tests; improve i18n

### Contribution path
1. Fork / clone SkyCache (Apache-2.0)
2. Add texts only with clear redistribute rights
3. Use `skycache skybrary import-folder --license ...` and `skybrary provenance`
4. Never commit pirate mirrors or commercial satellite tooling
5. Open PR with passport completeness and tests

### Course-friendly labs
- Lab A: first-boot + 70+ pytest green on laptop
- Lab B: pack profile build + signed manifest verify
- Lab C: 3-node `nexus sim` + disaster flood
- Lab D: dual-access `export-catalog` and review honest copy

### Contact for pilots
skycache@jonbailey.xyz - subject line `[NGO pilot]` or `[University kit]`.

---

## Success criteria (shared)

- [ ] Volunteer builds demo node from docs in &lt;2 hours (lab/sim)
- [ ] Phone without cell plan reads demos over hub Wi-Fi
- [ ] License inventory printable for partner legal review
- [ ] Disaster drill playbook walked once (sim OK)
- [ ] No claim of free broadband or complete archive
