# Disaster mode drill playbook

**Audience:** Local maintainers, NGO field leads, civil protection partners.  
**Goal:** Prove that a SkyCache Nexus fabric can **elevate emergency/health content**, **move it by mule**, and **restore a second node** - without claiming free commercial broadband or illegal RF.

**Honest model (say this first):**

> Disaster mode prioritizes **emergency and health** packages on the **local mesh** and store-and-forward path. It is **not** free Starlink, unlimited cellular, or satellite uplink. Mesh RF stays on **unlicensed Wi-Fi / regional ISM** only (operator verifies national rules).

Related: [`mesh-deployment.md`](mesh-deployment.md)  |  [`mesh-field-checklist.md`](mesh-field-checklist.md)  |  [`village-nexus-playbook.md`](village-nexus-playbook.md)  |  [`legal-ethics.md`](legal-ethics.md)

---

## What disaster mode actually does

| On | Off / never |
|----|-------------|
| Elevates **emergency** and **health** replication first | Does **not** open the public internet |
| Enqueues a coordination message on the DTN queue | Does **not** enable satellite TX |
| Floods high-priority packages across mesh peers (or sim) | Does **not** decrypt commercial services |
| Works with USB/phone **handoff mule** when mesh is down | Does **not** replace professional emergency services |

Admin toggle: `/admin` -> **Disaster mode ON/OFF** (`POST /api/admin/disaster` with admin PIN).  
Lab sim: `python -m skycache nexus sim --nodes 3 --disaster`

---

## Prerequisites (before any drill)

1. **Legal RF mode** set and documented:
   ```bash
   export SKYCACHE_LEGAL_RF_MODE=ism_mesh   # typical village mesh
   # or receive_only if radios are off and you only test USB mule
   skycache capabilities
   skycache nexus doctor
   ```
2. At least **one healthy node** with samples or real open packs:
   ```bash
   skycache init --load-samples
   skycache status
   ```
3. Admin PIN **changed** from default; written in the site logbook (not on public posters).
4. Optional second node (hardware or laptop with separate `data/` dir) for restore.
5. USB stick or phone storage for handoff (FAT32/exFAT is fine for package folders).
6. Paper logbook: date, operators, legal mode, pass/fail per step.

**Never during a drill:** jamming, pirate cellular BTS, commercial decrypt keywords, satellite uplink, or promising "free internet restored."

---

## Lab path (no radios) - 15 minutes

Use this on a laptop before any partner field drill.

```bash
# From the SkyCache repo / install root
python -m skycache nexus sim --nodes 3 --disaster
python -m pytest tests/test_nexus.py -q
```

**Pass criteria:**

- [ ] Command exits 0  
- [ ] Package counts converge (e.g. multiple nodes share packages after gossip rounds)  
- [ ] Stderr shows disaster mode enabled when `--disaster` is passed  
- [ ] `skycache nexus doctor` still reports legal rails intact  

Optional helper: `deploy/disaster-drill-sim.sh` (runs the sim + reminds operators to turn disaster **off** after real drills).

---

## Field path - full scripted drill

Run as a **tabletop + hands-on** exercise with two operators (Node A lead, Node B / mule runner). Time box: **45 - 90 minutes**.

### Step 0 - Brief partners (5 min)

Read aloud:

1. We serve **local knowledge** (checklists, health, maps, education) over community Wi-Fi.  
2. Disaster mode **prioritizes life-safety packs**; it does not create internet.  
3. If mesh fails, we use **USB or phone handoff** (data mule).  
4. All content must be **open / authorized**; no pirate streams.  
5. After the drill, disaster mode goes **OFF** unless a real emergency continues.

### Step 1 - Baseline on Node A

```bash
export SKYCACHE_NODE_ID=clinic-west   # or school-hub, etc.
export SKYCACHE_LEGAL_RF_MODE=ism_mesh
export SKYCACHE_MESH_MODE=batman      # or sim if radios not ready
skycache nexus doctor
skycache mesh status --compliance
skycache status
```

Phone test: join SSID -> open portal -> confirm Emergency / Health categories visible.

**Pass:** doctor OK, portal loads, at least one emergency-class package present (e.g. sample `emergency-checklist-001`).

### Step 2 - Disaster mode ON

**UI:** Admin (`/admin`) -> enter PIN -> **Disaster mode ON**.

**API (optional):**

```bash
curl -s -X POST "http://127.0.0.1:8080/api/admin/disaster" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Pin: YOUR_PIN" \
  -d '{"enabled": true}'
```

**Pass:**

- [ ] Admin shows disaster ON  
- [ ] Portal / nexus status reflects disaster (banner or mesh status)  
- [ ] Operators understand this is **priority flood**, not internet  

### Step 3 - Emergency flood (mesh or sim)

**With mesh peers up:** wait one fabric gossip cycle (or trigger peer activity). Emergency/health packages should be requested/replicated before general/entertainment.

**Without second radio peer:** still exercise prioritization by confirming the node **has** emergency packs ready for mule (next step). Optionally run:

```bash
python -m skycache nexus sim --nodes 3 --disaster
```

on a laptop as the "virtual flood" demo for partners.

**Pass:**

- [ ] Emergency/health packages present on Node A  
- [ ] DTN / nexus status shows activity or elevated disaster flag  
- [ ] No attempt to enable forbidden RF modes  

### Step 4 - Mule / handoff export (Node A -> USB or phone)

Export a handoff bundle (packages + DTN mule JSON):

```bash
# Prefer emergency packs first when naming ids
skycache handoff --out /media/usb/handoff \
  --packages emergency-checklist-001,health-ors-001 \
  --limit 20

# Or default: first N packages under data/content
skycache handoff --out /media/usb/handoff --limit 20
```

Safely eject the USB. Optionally copy the `skycache-handoff-*` folder to a phone over USB file transfer (user-consented; not "tethering the village to 4G").

**Pass:**

- [ ] Bundle folder exists with `handoff.json` and `packages/`  
- [ ] `handoff.json` lists copied package ids  
- [ ] Legal note in meta understood by operators  

### Step 5 - Second node restore (Node B)

On Node B (fresh or intentionally empty content):

```bash
export SKYCACHE_NODE_ID=school-east
export SKYCACHE_LEGAL_RF_MODE=ism_mesh
skycache init   # if not already
# Copy package dirs from the handoff stick into drop or ingest path:
skycache ingest /media/usb/handoff/skycache-handoff-*/packages/emergency-checklist-001
# Or bulk: point ingest at the packages folder / each package dir
skycache ingest /media/usb/handoff/skycache-handoff-XXXX/packages
skycache watch --once   # if using drop/incoming workflow
skycache verify data/content
skycache status
```

Start portal if needed: `skycache serve --host 0.0.0.0 --port 8080`.

Phone on Node B SSID: open emergency checklist and health sheet offline.

**Pass:**

- [ ] Package ids appear in Node B catalog  
- [ ] Portal serves emergency content without uplink  
- [ ] `skycache verify` reports OK (or documented bit-rot follow-up)  

### Step 6 - Mesh rejoin (if two radios available)

1. Bring both nodes onto the same unlicensed mesh (see [`mesh-deployment.md`](mesh-deployment.md)).  
2. Confirm peers: `skycache mesh status` on each.  
3. Leave disaster ON only for the exercise window; confirm additional missing emergency packs prefer flood order.  
4. Document peer count and battery % in logbook.

**Pass:** both nodes list each other (or sim peers); content stays available if one radio drops (mule already proved).

### Step 7 - Disaster mode OFF + debrief

```bash
# Admin UI: Disaster OFF
# or:
curl -s -X POST "http://127.0.0.1:8080/api/admin/disaster" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Pin: YOUR_PIN" \
  -d '{"enabled": false}'
```

**Debrief questions:**

1. Who can turn disaster mode on without calling HQ?  
2. Where is the spare USB mule stored?  
3. What do we **tell the community** this system is / is not?  
4. Any RF or power issue found? Log and schedule fix.  
5. License inventory still complete for every pack moved?

---

## Partner checklist (civil protection / NGO)

Copy or print this section for after-action reports.

### Legal & messaging

- [ ] Staff can state: **local mesh + store-and-forward**, not free commercial satellite internet  
- [ ] `SKYCACHE_LEGAL_RF_MODE` recorded (`receive_only` | `ism_mesh` | `ism_lora_control` | `hybrid_gateway` | `amateur_operator`)  
- [ ] National Wi-Fi/ISM rules checked (name + date in logbook)  
- [ ] No satellite TX, jamming, or commercial decrypt attempted  
- [ ] Admin PIN not default; access limited to trained maintainers  

### Technical proof points

- [ ] Disaster mode ON demonstrated  
- [ ] Emergency/health content prioritized or present for flood  
- [ ] Handoff mule exported to removable media  
- [ ] Second node restored and serves packs offline  
- [ ] Integrity check run (`skycache verify`)  
- [ ] Disaster mode OFF after drill (unless real incident)  

### Ops readiness

- [ ] Local maintainer completed [`training-local-maintainer.md`](training-local-maintainer.md) modules  
- [ ] Spare USB labeled "SkyCache mule - emergency first"  
- [ ] Solar/battery plan survives a multi-hour outage drill  
- [ ] Content licenses inventoried for all packs used  
- [ ] Next drill date scheduled (recommend quarterly)  

### Explicit non-goals (sign-off)

- [ ] Partners agree the system **does not** replace ambulance, fire, or official public warning systems  
- [ ] Partners agree gateway pulls (if any) stay on **open/authorized** content with **daily quota**  
- [ ] Partners will not request illegal RF features from maintainers  

**Drill lead:** _________________ **Date:** ________ **Site:** _________________  
**Legal mode:** _________________ **Result:** PASS / PARTIAL / FAIL  
**Notes:** ________________________________________________________________

---

## Failure modes during drills (quick map)

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Admin rejects disaster toggle | Wrong PIN / no admin header | Reset PIN process; use trained operator only |
| Handoff folder empty packages | Wrong `--packages` ids / empty content | `ls data/content`; `skycache init --load-samples` |
| Second node portal empty | Ingest path wrong | Ingest package **dirs** with `manifest.json`; run `watch --once` |
| Mesh peers zero | Radios/sim mode mismatch | See [`mesh-field-checklist.md`](mesh-field-checklist.md); fall back to USB mule |
| Doctor fails legal mode | Forbidden keyword or amateur without affirmation | Fix `SKYCACHE_LEGAL_RF_MODE`; never force illegal modes |
| Battery critical mid-drill | Undersized solar / ECO mode | Pause RF stress; complete mule-only path |

Full mesh failures: [`mesh-deployment.md`](mesh-deployment.md) § Failure modes.

---

## Frequency & governance

| Cadence | Activity |
|---------|----------|
| After install | Lab sim + one full field drill |
| Quarterly | Steps 2 - 5 (ON -> mule -> restore -> OFF) |
| After content kit change | Re-export mule; verify emergency packs still first |
| Real incident | Disaster ON by authority of site lead; OFF when stable; paper log of times |

---

## Related commands (cheat sheet)

```text
skycache nexus doctor
skycache capabilities
skycache mesh status --compliance
skycache nexus sim --nodes 3 --disaster
skycache handoff --out data/handoff --packages emergency-checklist-001 --limit 20
skycache ingest <package-or-tree>
skycache verify data/content
skycache status
# Admin: /admin disaster ON|OFF
```
