# Mesh field checklist (2-node day)

**Printable companion** to [`mesh-deployment.md`](mesh-deployment.md).  
Use on site when validating **two nodes** before inviting the community.

**Honest banner:** store-and-forward community knowledge mesh - **not** free Starlink / unlimited internet. RF = **unlicensed Wi-Fi / regional ISM only** (verify national law).

Disaster exercise: [`disaster-drill.md`](disaster-drill.md). Village recipe: [`village-nexus-playbook.md`](village-nexus-playbook.md).

---

## 0. Legal RF mode (do this first)

| Mode (`SKYCACHE_LEGAL_RF_MODE`) | When to use |
|---------------------------------|-------------|
| `receive_only` | SDR RX + local AP; **no mesh TX** yet |
| `ism_mesh` | **Default village fabric** - Wi-Fi mesh / AP chain |
| `ism_lora_control` | + low-BW LoRa/ISM **control/alerts only** (not bulk media) |
| `hybrid_gateway` | + one node may pull open content via **authorized** modem/Ethernet |
| `amateur_operator` | Only with valid license **and** `SKYCACHE_AMATEUR_LICENSE_AFFIRMED=true` |

**Forbidden (software refuses):** starlink, sat-uplink, commercial-decrypt, jamming, gps-spoof, pirate-bts.

```bash
export SKYCACHE_LEGAL_RF_MODE=ism_mesh
export SKYCACHE_MESH_MODE=batman    # or sim until radios ready
export SKYCACHE_MESH_BAND=wifi_2g
skycache capabilities
skycache nexus doctor
skycache mesh status --compliance
```

Logbook: who verified national EIRP/outdoor/DFS rules: **Name ________ Date ________**

---

## 1. Two-node validation checklist

### Node A and Node B prep

- [ ] Unique `SKYCACHE_NODE_ID` on each (`clinic-west`, `school-east`, ...)  
- [ ] `skycache init` done; samples or real open packs loaded on at least Node A  
- [ ] Admin PIN changed on both  
- [ ] Same portal version / install path where practical  
- [ ] Power plan: AC or solar; neither node starts the day at critical SOC  

### L2 / RF (physical)

- [ ] Mesh path is **Wi-Fi ISM** (or lab Ethernet simulating mesh) - no satellite TX gear "for the mesh"  
- [ ] Radios at legal power; outdoor antennas only if rules allow  
- [ ] Optional: batman-adv template `deploy/mesh/batman-setup.example.sh` (customize IFs)  
- [ ] Optional second radio / AP: phone SSID (`deploy/mesh/hostapd-client-ap.example.conf`)  
- [ ] IP plan documented (e.g. `10.42.0.10` / `10.42.0.11`)  

### Software fabric

On each node:

```bash
export SKYCACHE_NODE_ID=...          # unique
export SKYCACHE_LEGAL_RF_MODE=ism_mesh
export SKYCACHE_MESH_MODE=batman     # or sim
skycache serve --host 0.0.0.0 --port 8080
skycache mesh status
skycache nexus status
```

- [ ] Both portals open from a phone on each SSID/AP  
- [ ] Mesh status shows peer(s) **or** documented sim mode for indoor lab  
- [ ] Package present on A appears on B after gossip **or** after USB mule (honest either path)  
- [ ] Emergency > Health > Education ordering understood by maintainer  

### Captive / UX

- [ ] Phone joins SSID without technician  
- [ ] Captive or bookmark reaches portal  
- [ ] Legal/honest limit language visible or explained  
- [ ] Categories load at "local broadband" speed (LAN, not WAN)  

### Pass bar (2-node day)

| # | Check | Pass? |
|---|-------|-------|
| 1 | Legal mode + doctor green on both | |
| 2 | Two portals serve content offline | |
| 3 | Peer visible **or** mule transfer documented | |
| 4 | Maintainer can restart service alone | |
| 5 | Staff can say "not free satellite internet" | |

---

## 2. Failure modes (field)

| Symptom | Likely cause | Mitigation |
|---------|--------------|------------|
| Zero mesh peers | Wrong band/mode, radio down, firewall, different subnets | Fall back to **USB handoff**; fix RF later |
| Phones associate, no portal | DHCP/DNS/captive misconfig, service down | `skycache status`; static `http://NODE_IP:8080/` |
| One-way content | Gossip not running; disk full on receiver | Free disk; check prioritizer; mule missing packs |
| Node dies at night | Battery / solar undersized | ECO/CRITICAL power modes; reduce AP power; schedule |
| Gateway quota exhausted | Metered modem overused | Stop pulls; emergency packs via USB only |
| Doctor rejects mode | Illegal keyword or amateur without affirmation | Correct env; **do not** bypass |
| Split-brain PINs | Each node different admin PIN lost | Logbook + sealed envelope procedure |
| Stale emergency packs | No mule/gateway for weeks | Quarterly [`disaster-drill.md`](disaster-drill.md) |

**Priority when everything fails:** serve **local packages already on disk** -> USB mule -> legal gateway pull -> rebuild mesh. Never escalate to illegal RF.

---

## 3. Day-of sequence (2 hours)

1. Legal + doctor (15 min)  
2. Power + mount nodes (30 min)  
3. Bring up mesh or sim + portals (30 min)  
4. Phone walk-test both buildings (20 min)  
5. Optional mini disaster drill: ON -> handoff -> OFF (20 min) - full script in [`disaster-drill.md`](disaster-drill.md)  
6. Train one local maintainer on restart + USB ingest (15 min)  

---

## 4. Sign-off

**Site:** _______________ **Date:** ________  
**Node A id:** _______________ **Node B id:** _______________  
**legal_rf_mode:** _______________  
**Mesh path:** batman / AP-chain / sim / other: _______________  
**Result:** PASS / PARTIAL / FAIL  
**Follow-ups:** _______________________________________________
