# How to deploy a village Nexus fabric

**One-page field recipe.** Full detail: [`mesh-deployment.md`](mesh-deployment.md) and [`legal-ethics.md`](legal-ethics.md).  
**Day-of 2-node list:** [`mesh-field-checklist.md`](mesh-field-checklist.md)  |  **Disaster drill:** [`disaster-drill.md`](disaster-drill.md)

## Promise (say this out loud)

> SkyCache Nexus is a **community knowledge network**. Phones get a fast local library, maps, health sheets, and village notes over Wi-Fi mesh. When a shared modem or USB pack is available, the system updates **open** materials. It is **not** free Starlink or unlimited internet.

## Day 0 - prepare (office / workshop)

1. Flash 2 - 4 identical SD images (Pi / Orange Pi class).
2. Install via golden path: `sudo bash deploy/install-village-fabric.sh` then first-boot wizard
   ([`first-boot.md`](first-boot.md)) - PIN, SSID hint, `legal_rf_mode`, samples + Skybrary.
3. Label nodes: `school`, `clinic`, `market`, `hub`.
4. Print license inventory for every content pack.
5. Run `skycache nexus doctor` and `skycache nexus sim --nodes 3` on a laptop.
6. Lab disaster flood once: `python -m skycache nexus sim --nodes 3 --disaster` (or `deploy/disaster-drill-sim.sh`).
7. Choose `SKYCACHE_LEGAL_RF_MODE` (demo default `receive_only`; field mesh often `ism_mesh`); record in logbook.

## Day 1 - site survey

1. Walk buildings; mark line-of-sight for Wi-Fi.
2. Confirm solar / AC / battery plan; never run batteries to death daily.
3. Check **national Wi-Fi / ISM** rules with a local partner (write name + date).
4. Choose one node that may host the optional **receive-only** SDR.

## Day 2 - install fabric

1. Mount nodes high, weather-protected, grounded.
2. Configure **unlicensed Wi-Fi mesh** (batman-adv or same-SSID AP chain) - no satellite TX.
3. On each node:
   ```bash
   export SKYCACHE_NODE_ID=clinic
   export SKYCACHE_MESH_MODE=batman   # or sim until radios ready
   export SKYCACHE_MESH_BAND=wifi_2g
   systemctl enable --now skycache   # if unit installed
   ```
4. Phone test: join SSID -> captive -> portal categories load at "local broadband" speed.
5. Copy USB education / health packs via `skycache watch --once` or drop folder.

## Day 3 - train maintainers

Use [`training-local-maintainer.md`](training-local-maintainer.md). Must-know:

| Task | How |
|------|-----|
| Is the portal up? | Phone + `skycache status` |
| Add content | USB -> drop/incoming |
| Mesh OK? | Admin -> mesh peers / `skycache mesh status` |
| Disaster flood | Admin disaster mode ON - full script: [`disaster-drill.md`](disaster-drill.md) |
| Mule / restore | `skycache handoff` -> USB -> second node `ingest` |
| Outside update | Authorized modem -> `skycache gateway --pull` (quota!) |
| 2-node check | [`mesh-field-checklist.md`](mesh-field-checklist.md) |
| Never | Promise free commercial satellite internet; decrypt paid services; leave default PIN |

## Opportunistic updates

When a teacher brings a phone hotspot or the clinic has a metered modem:

1. Connect **only the gateway node**.
2. Run scheduled open pulls with daily quota.
3. Let mesh **replicate** Emergency -> Health -> Education first.
4. Disconnect uplink when done - mesh keeps serving offline.

## Weekly care

- Check free disk and battery %.
- Purge general/entertainment packs if disk pressure (prioritizer helps).
- Re-verify content licenses for anything new.
- Test disaster mode in a drill (then turn off) - steps in [`disaster-drill.md`](disaster-drill.md).

## Success criteria

- [ ] Two+ nodes serve the same prioritized library  
- [ ] Phones roam or at least reconnect without technical staff  
- [ ] Legal banner visible; staff can explain honest limits  
- [ ] Local maintainer restarts service and loads USB without remote help  
- [ ] 2-node field checklist signed once ([`mesh-field-checklist.md`](mesh-field-checklist.md))  
- [ ] Disaster drill run at install + on a quarterly cadence  

