# Legal pathways brainstorm - content "decrypt" & RF receive/transmit

**Purpose:** Expand SkyCache / Skybrary *within the law*.  
**Not a substitute for legal advice.** Operators must verify national rules.  
**Hard no:** commercial constellation piracy, DRM circumvention for paid services, unauthorized uplink, jamming, surveillance of third parties.

This document brainstorms **lawful** practices that sound adjacent to "decryption" or "transmit" so contributors do not confuse them with forbidden paths.

---

## A. "Decryption" practices that can be legal

In radio and archives, "decrypt" is often misused. Legal activity is usually **demodulation / decoding of open signals** or **decrypting content you are authorized to access**.

| Pathway | What it is | Why it can be legal | SkyCache / Skybrary fit |
|---------|------------|---------------------|-------------------------|
| **FTA demodulation** | Demod FM/APT/LRPT/HRIT of free-to-air weather | Unencrypted public broadcasts; receive-only | `satdump_weather` plugin |
| **Amateur satellite decode** | gr-satellites / SatNOGS-class open telemetry | Amateur service rules; open designs | `gr_satellites` plugin |
| **Open digital modes** | AX.25, APRS, FT8 *decode* of amateur signals | Licensed operators / open monitoring where lawful | Future plugins; education |
| **Cleartext "cipher" teaching** | Caesar/Vigenère labs, CTF crypto courses | Educational crypto, not service bypass | Training packs only |
| **TLS as a *client*** | HTTPS pull of open content you may download | Normal web use with authorization | Opportunistic gateway (open packs only) |
| **Your own encrypted backups** | Decrypt LUKS/BitLocker volumes **you own** | Owner control of own data | Operator IT, not product feature |
| **Authorized DRM** | Play purchased content with **licensed** players | License permits use, not reverse-engineering | Out of scope; never ship breakers |
| **Open encrypted formats with keys** | e.g. public test vectors, RFC examples with published keys | Keys are public by design | Spec education packs |
| **Password managers / age/gpg** | Decrypt messages with keys you hold | Consent + key possession | Local maintainer ops |
| **ZIM / compressed archives** | Decompress open offline packs | Not encryption bypass | `package_import` |
| **Signed open packages** | Verify signatures then open payload | Integrity, not DRM defeat | Skybrary integrity (S2+) |
| **Public keyserver / transparency logs** | Fetch certs/logs for research | Public data | Research, not default product |

### Explicitly **not** "legal decryption" for this project

- Decrypting Starlink / OneWeb / commercial VSAT / paid DTH CAS  
- Card-sharing, control-word sharing, pirate CAM  
- Circumventing ebook/store DRM to redistribute  
- Breaking device attestation to steal paid streams  

SkyCache config already **refuses** forbidden source keywords (`starlink`, `decrypt-commercial`, `card-sharing`, ...).

### Design rule

Prefer the word **decode / demodulate / decompress / verify** for open paths. Reserve "decrypt" for **authorized key possession** only, and document the authority.

---

## B. Receive-and-transmit capabilities that can be legal

SkyCache **defaults to satellite receive-only**. Transmit is allowed only in narrow, regulated classes.

### B1. Unlicensed / lightly regulated (operator still verifies country)

| Capability | Band / tech | Typical use | Product stance |
|------------|-------------|-------------|----------------|
| **Wi-Fi AP** | 2.4/5/6 GHz | Captive portal, local library | **Core** (`hostapd`) |
| **Wi-Fi mesh** | Same | Village fabric (batman-adv) | **Nexus** |
| **Bluetooth LE** | 2.4 GHz | Phone↔node handoff / mule assist | Optional future |
| **Regional LoRa / Meshtastic-class ISM** | Region-specific ISM | Low-BW alerts, DTN control | **Control plane stub**; duty-cycle limits |
| **RFID/NFC** | Short range | Inventory tags for packs (local) | Out of band accessory |

### B2. Licensed amateur / land-mobile (human license required)

| Capability | Notes | Product stance |
|------------|-------|----------------|
| **Amateur radio TX** | Valid callsign, band plan, power limits | **Outside default**; docs only |
| **Amateur satellite uplink** | Where allowed to licensed hams | **Never default** in SkyCache binary |
| **APRS / packet radio** | Licensed | Educational wrappers only if operator licensed |
| **GMRS / PMR446 / etc.** | Country-specific | Not productized; local law |
| **Part 15 / equivalent intentional radiators** | Power/mask limited | Prefer Wi-Fi/LoRa helpers that stay within norms |

### B3. Receive-only (preferred expansion)

| Capability | Notes |
|------------|-------|
| RTL-SDR / SoapySDR weather & open sats | Core mission |
| NOAA weather radio (where free) | Future plugin candidate |
| DAB+/FM broadcast (public radio, where allowed) | Content rights still apply for redistribution |
| Open GNSS **observation** (not spoofing) | Education only; never jam/spoof |

### B4. Wired / non-RF "transmit"

| Capability | Notes |
|------------|-------|
| Ethernet / USB gadget | Always preferred when available |
| USB data mule export/import | **Core Nexus DTN** |
| Opportunistic cellular **modem as client** | Operator-paid, authorized SIM; pull open content only; quotas |

### Hard no (transmit / RF abuse)

- Satellite uplink "to get free Starlink-like service"  
- Jamming, GPS spoofing, pirate cellular base stations  
- Unauthorized interception of private communications  

---

## C. How this shapes the next upgrades

1. **Skybrary S2** - text catalog/search expands *legal content*, not RF attack surface.  
2. **Plugins** - bias toward FTA decode, open telemetry, open corpus import.  
3. **Mesh / LoRa** - stay unlicensed-ISM + documented power/duty cycle.  
4. **Gateway** - HTTPS client to open mirrors; never commercial decrypt.  
5. **Docs / UI banners** - use precise language: decode FTA, not "decrypt the sky."

---

## D. Software entry points (0.6+)

| Capability | CLI / API |
|------------|-----------|
| Full matrix | `skycache capabilities`  |  `GET /api/capabilities` |
| Legal RF mode | `SKYCACHE_LEGAL_RF_MODE=ism_mesh` (etc.) |
| Open HTTPS fetch | `skycache open-fetch URL --out file`  |  plugin `open_http_import` |
| Corpus folder / Gutenberg-style | `skybrary import-folder`  |  `import-open`  |  plugin `corpus_folder_import` (license required) |
| Integrity | `skycache verify data/content` |
| Handoff mule | `skycache handoff --out data/handoff` |
| Pack kits | `skycache skybrary pack --profile literacy-1gb` |
| FTA / amateur decode | `pipeline --plugin satdump_weather|gr_satellites` |
| Mesh | `skycache mesh status`  |  `legal_rf_mode=ism_mesh` |
| LoRa control | `legal_rf_mode=ism_lora_control`  |  control API |
| Gateway | `legal_rf_mode=hybrid_gateway`  |  `skycache gateway --pull` |

## E. Operator checklist before any new RF feature

1. Is content **open or authorized**?  
2. Is RF path **receive-only**, or **unlicensed**, or **operator-licensed**?  
3. Does UI still disclaim free commercial broadband?  
4. Can a local maintainer explain the legal basis in one paragraph?  
5. Does CI/`doctor` refuse forbidden keywords?  

If any answer is no, do not ship.
