# Phone offline demos - no cell plan required

**Goal:** A person with a **phone and no cellular plan**, in the middle of nowhere, can still **download the three Skybrary demo texts** - by joining a local SkyCache hub Wi-Fi only.

**No Wi-Fi *and* no cell?** That is a different tier: physical USB / SD / Bluetooth or pre-deploy. See [`zero-network-phone.md`](zero-network-phone.md).

This is **not** free Starlink, not commercial broadband, and not a complete archive. It is local store-and-forward knowledge over unlicensed Wi-Fi.

---

## Architecture (honest)

```text
[Middle of nowhere]
        |
   Phone (no SIM / no data)
        |  Wi-Fi only
        v
  SkyCache hub  (Pi / laptop / village box)
   - hostapd SSID e.g. SkyCache-Village
   - portal :8080
   - 3 PD demos on local disk
        |
   Optional later: mesh peer / USB mule / FTA RX
```

**The phone never needs the public internet.**  
**Someone** must have provisioned the hub earlier (install + demos, or USB image). The hub is the offline library.

---

## End-user path (phone)

1. Turn on Wi-Fi. Join the hub SSID (printed on the box / first-boot wizard), e.g. `SkyCache-Village`.
2. Accept captive portal or open `http://192.168.4.1:8080/` (or the address shown on the hub sticker).
3. On the home screen: **Save demos to this phone** - downloads `skycache-skybrary-demo-3texts.zip`.
4. Or open **Library**, read each work, tap **Save file**.

Files land in the phone's Downloads / Files app. After that, the texts stay on the phone even if Wi-Fi drops.

---

## Operator path (hub)

### A. Field / Pi (recommended)

```bash
sudo bash deploy/install-village-fabric.sh
# first-boot loads samples + skybrary demos
# enable hotspot when ready:
sudo bash deploy/enable-hotspot.sh   # SSID from first-boot
```

### B. Laptop sim (demo today without hostapd)

```bash
pip install -e .
# bind all interfaces so phone on same LAN / phone-as-hotspot can reach you
skycache serve --sim --host 0.0.0.0 --port 8080
```

On Windows: turn on **Mobile hotspot**, connect the demo phone to that hotspot, open  
`http://<laptop-lan-ip>:8080/` - same PWA buttons.

Console should print:

```text
Phone demos ready: 3/3 - GET /api/demo/pack.zip over hub Wi-Fi (no cell plan).
Phone path: join hub Wi-Fi -> Library -> Save demos to this phone
```

### C. API (for automation / QA)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/demo` | Status of 3 demos |
| GET | `/api/demo?ensure=1` | Status + ensure load |
| GET | `/api/demo/pack.zip` | Zip attachment for phones |
| GET | `/content/{id}/work.txt?download=1` | Single-file Save |

---

## The three demos

| ID | Text |
|----|------|
| `skybrary-pd-aesop-001` | Aesop - Fox and the Grapes |
| `skybrary-pd-gettysburg-001` | Gettysburg Address |
| `skybrary-pd-hippocratic-001` | Hippocratic Oath (PD excerpt) |

Public domain / educational samples only. Not medical advice.

---

## What this does **not** solve yet

- Blank phone + **no hub nearby** -> still no content (physics).
- Automatic satellite delivery of these texts without a ground node.
- Full literacy corpora (use pack profiles + corpus import for scale).

Next steps toward denser coverage: more preloaded packs on the hub, mesh between hubs, USB mule refresh, lawful FTA plugins.

---

## Related

- [`first-boot.md`](first-boot.md) - village node &lt;2 hours  
- [`mesh-field-checklist.md`](mesh-field-checklist.md)  
- [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md)  
