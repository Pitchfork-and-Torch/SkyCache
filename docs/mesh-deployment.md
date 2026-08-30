# Mesh deployment guide - SkyCache Nexus

**Honest model:** SkyCache Nexus creates a **local community mesh** that feels like broadband for *local* knowledge, messaging, and services. It is **store-and-forward + unlicensed Wi-Fi mesh**, **not** free commercial satellite internet (not Starlink / OneWeb / VSAT uplink).

Read [`legal-ethics.md`](legal-ethics.md) before any RF or AP deploy.

---

## What you are building

```text
[Pi node A] <--Wi-Fi mesh (batman-adv)--> [Pi node B] <--mesh--> [cheap AP]
     |                                        |
  content + PWA                          content + PWA
     |                                        |
  phones / tablets  (roam across fabric, same L2 where possible)
```

Optional:

- **RTL-SDR** on one node for receive-only weather / FTA open content
- **LoRa / Meshtastic-class ISM** only for low-bandwidth control, alerts, DTN (not bulk media)
- **Opportunistic gateway** on one node when a *legal* USB modem / community Wi-Fi / Ethernet is available - pulls open content under daily quotas

---

## Spectrum rules (non-negotiable)

| Allowed mesh TX | Forbidden by default |
|-----------------|----------------------|
| 2.4 / 5 / 6 GHz Wi-Fi (where legal) | Satellite uplink of any kind |
| Regional LoRa / ISM (control plane) | Licensed microwave without authorization |
| Simulation (`mesh_mode=sim`) | Jamming, GPS spoof, commercial decrypt |

**Operator checklist before radio on:**

1. Confirm national **unlicensed / ISM** rules (EIRP, outdoor channels, DFS).
2. Confirm **hotspot / community network** registration if required.
3. Set realistic AP power; do not overdrive antennas.
4. Prefer **Wi-Fi mesh** for user "broadband experience"; keep LoRa sparse.
5. Document who verified local law (name + date) in the site logbook.

CLI: `skycache mesh status --compliance` and `skycache nexus doctor`.

---

## Legal RF mode (`SKYCACHE_LEGAL_RF_MODE`)

Software **fail-closed** modes. Set explicitly on every node; confirm with `skycache capabilities`.

| Mode | Allows | Does not allow |
|------|--------|----------------|
| `receive_only` | Local AP + optional SDR RX | Mesh TX, LoRa control, gateway pull productization |
| `ism_mesh` | + unlicensed Wi-Fi/ISM mesh fabric | Satellite TX, commercial decrypt |
| `ism_lora_control` | + low-BW LoRa/ISM **control/alerts** | Bulk media over LoRa |
| `hybrid_gateway` | + opportunistic **client** uplink for open pulls | Transparent full-mesh NAT "free internet" |
| `amateur_operator` | Licensed human operator path (affirmation required) | Automatic sat uplink in product binary |

```bash
export SKYCACHE_LEGAL_RF_MODE=ism_mesh
# amateur only when lawful:
# export SKYCACHE_LEGAL_RF_MODE=amateur_operator
# export SKYCACHE_AMATEUR_LICENSE_AFFIRMED=true
skycache capabilities
skycache nexus doctor
```

**Refused keywords (examples):** `starlink`, `sat-uplink`, `commercial-decrypt`, `jamming`, `gps-spoof`.  
Full matrix: [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md).

Printable day-of list: [`mesh-field-checklist.md`](mesh-field-checklist.md).

---

## Hardware (village fabric)

| Role | Example | Notes |
|------|---------|--------|
| Core node | Raspberry Pi 4/5 or Orange Pi, 4 GB+, 64 - 256 GB storage | Solar-aware preferred |
| Mesh radio | USB Wi-Fi that supports AP/mesh on Linux, or dual radio | One radio mesh, one client AP is common |
| Edge AP | Commodity OpenWrt or hostapd AP | Same SSID/password for seamless feel |
| Optional SDR | RTL-SDR Blog V3 + V-dipole | **Receive only** |
| Optional long-range | LoRa module on regional ISM | Control / emergency only |
| Power | LiFePO4 + solar + charge controller | ECO/CRITICAL modes in software |

BOM baseline still applies: see [`hardware-bom.md`](hardware-bom.md).

---

## Software setup (Linux)

### 1. Install SkyCache on each node

```bash
sudo ./deploy/install-debian.sh   # or pip install -e ".[dev]"
skycache init --load-samples
# Set unique node identity
export SKYCACHE_NODE_ID=clinic-west
export SKYCACHE_MESH_MODE=batman   # or sim for lab
export SKYCACHE_MESH_BAND=wifi_2g
skycache nexus doctor
skycache serve --host 0.0.0.0 --port 8080
```

### 2. batman-adv sketch (physical multi-node)

This is an **operator-facing outline**, not a one-size script for every distro:

```bash
# Install tools (Debian/Ubuntu example)
sudo apt install batctl bridge-utils wireless-tools

# Load module
sudo modprobe batman-adv

# Put mesh interface into ad-hoc / mesh mode (device-specific; OpenWrt often easier)
# Then:
sudo ip link set bat0 up
sudo batctl if add wlan0
sudo ip addr add 10.42.0.N/24 dev bat0   # unique N per node
```

Run the same SkyCache portal on each node (or one "library" node + thin edge APs). Clients should get DHCP from a designated gateway node or per-node captive setup coordinated so they always land on a portal.

Deploy helpers:

- `deploy/hotspot/` - hostapd / dnsmasq examples  
- `deploy/nexus-mesh.service` - optional systemd unit notes  
- `deploy/village-playbook.md` - day-of install steps  

### 3. Simulation (no hardware)

```bash
python -m skycache nexus sim --nodes 3 --disaster
python -m pytest tests/test_nexus.py -q
```

---

## Content fabric behaviour

1. Nodes **gossip** package manifests over the mesh (or sim links).
2. Missing **Emergency > Health > Education** packages replicate first.
3. Large ZIMs / media copy peer-to-peer when paths are reachable; otherwise DTN **requests** wait for a mule or gateway.
4. **Disaster mode** (admin API / CLI) floods emergency/health and elevates coordination messages.

---

## Opportunistic gateway ethics

When a shared uplink appears:

- Pull **open / FTA / licensed** updates only (Kiwix, MoH, weather open data, operator packs).
- Respect **daily quota** (`SKYCACHE_GATEWAY_DAILY_QUOTA_MB`, default 500).
- Fair-share scheduler never lets entertainment starve emergency/health/education.
- Do **not** transparently NAT the whole mesh to the public internet by default - that invites abuse and legal risk. Prefer scheduled content pulls + messaging.

```bash
skycache gateway --sim --request health-ors-001 --priority health --pull
```

---

## Power-aware routing

Mesh status prefers peers that are **solar** and **high SOC** for mule / gateway preference. Under ECO/CRITICAL power modes, live SDR RX is already reduced by the core power policy; mesh should similarly prefer not to stress low-battery nodes.

---

## Verification

| Check | Command / action |
|-------|------------------|
| Legal rails | `skycache nexus doctor` |
| Legal RF mode | `skycache capabilities`  |  env `SKYCACHE_LEGAL_RF_MODE` |
| Mesh topology | `skycache mesh status`  |  `--compliance` |
| Multi-node sim | `skycache nexus sim --nodes 4` |
| Disaster lab | `skycache nexus sim --nodes 3 --disaster` or `deploy/disaster-drill-sim.sh` |
| Portal | Phones on SSID open `http://<node-ip>:8080/` |
| Admin | `/admin` PIN - mesh, gateway, disaster toggle |
| Mule | `skycache handoff --out data/handoff` then ingest on peer |

---

## 2-node validation checklist (day-one field)

Use this when the first **two** physical (or laptop) nodes go live. Expand with the printable [`mesh-field-checklist.md`](mesh-field-checklist.md).

### Before radios

- [ ] `SKYCACHE_LEGAL_RF_MODE` chosen and written in logbook (`ism_mesh` typical)  
- [ ] National unlicensed/ISM rules verified (name + date)  
- [ ] Unique `SKYCACHE_NODE_ID` per node  
- [ ] Admin PINs changed; not shared on public walls  
- [ ] Node A has open/authorized packages (`skycache init --load-samples` minimum)  

### Bring-up

- [ ] Both run `skycache nexus doctor` clean  
- [ ] Mesh mode set (`batman` or temporary `sim`) and band (`wifi_2g` / ...)  
- [ ] Portals reachable on each node IP:8080  
- [ ] Phone joins SSID and loads categories offline  

### Fabric proof (pick one path - both are honest)

**Path M - mesh gossip**

- [ ] `skycache mesh status` shows a peer on at least one node  
- [ ] Package present only on A appears on B after gossip / replication window  

**Path U - USB mule** (always valid fallback)

- [ ] `skycache handoff --out /media/usb/handoff` on A  
- [ ] `skycache ingest .../packages/<id>` (or drop watch) on B  
- [ ] B portal serves the pack with no uplink  

### Exit criteria

- [ ] Two portals serve prioritized library without public internet  
- [ ] Maintainer restarts service without remote help  
- [ ] Staff can explain: **not free commercial satellite internet**  
- [ ] Optional: mini disaster drill - see [`disaster-drill.md`](disaster-drill.md)  

---

## Failure modes

| Failure | Symptoms | Mitigation (legal only) |
|---------|----------|-------------------------|
| No mesh peers | Empty peer list; content never replicates | Check mode/band, batctl, power, antennas; **USB handoff** until RF fixed |
| Portal down, Wi-Fi up | Association OK, HTTP fails | Restart `skycache` / systemd unit; confirm port 8080; disk full? |
| Captive loop | Phone never lands on portal | DNS/dnsmasq examples in `deploy/hotspot/`; bookmark IP as backup |
| Split catalogs | Nodes diverge for days | Schedule mule runs; check prioritizer and free space on the lagging node |
| Gateway "feels broken" | Users expect full web | Re-train: quota + open pulls only; do not enable full-mesh NAT |
| Disaster left ON | Always emergency-first | Turn OFF after drill/incident; log times ([`disaster-drill.md`](disaster-drill.md)) |
| Illegal mode request | Someone asks for Starlink/jam | Refuse; `capabilities` / doctor will not enable; cite legal-ethics |
| Power collapse | Nodes reboot / ECO | Prefer solar peers for mule; reduce AP power; see solar notes |
| Bad pack / bit-rot | Verify fails | Re-copy from handoff; `skycache verify data/content` |
| PIN lockout | Admin unavailable | Local sealed recovery procedure; never ship default PIN in production |

**Escalation order:** local disk content -> USB/phone mule -> legal gateway pull -> repair mesh. Never "fix" connectivity with unauthorized RF.

---

## What success looks like

- Students and clinic staff open the **same PWA experience** from different buildings.
- Content stays available when the outside world is offline.
- One shared modem (when present) refreshes **priority** knowledge without pretending to be unlimited home broadband.
- Local maintainers can run doctor, reload packages from USB, and explain the honest limits in the local language.
- A 2-node day checklist is signed once; disaster drills run on a schedule without drama.

---

## Related docs

- [`architecture.md`](architecture.md) - Nexus layers  
- [`legal-ethics.md`](legal-ethics.md) - full policy  
- [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md) - RF/content capability map  
- [`community-playbook.md`](community-playbook.md) - NGO one-pager  
- [`training-local-maintainer.md`](training-local-maintainer.md) - field training  
- [`village-nexus-playbook.md`](village-nexus-playbook.md) - short deploy recipe  
- [`mesh-field-checklist.md`](mesh-field-checklist.md) - printable 2-node day list  
- [`disaster-drill.md`](disaster-drill.md) - disaster ON -> flood -> mule -> restore  

