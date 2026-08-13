# Legal, safety, sustainability, and ethics

**Read this before any field deployment.**

SkyCache exists to improve **information access** for communities with little or no affordable internet. It is **not** a tool for stealing commercial satellite broadband or bypassing paid services.

---

## 1. Receive-only by default (satellite / long-haul RF)

- Default SkyCache configurations **do not transmit** on satellite uplinks.
- **SkyCache Nexus** mesh transmit is **only** on **unlicensed / ISM** class links (Wi-Fi 2.4/5/6 GHz where legal; optional regional LoRa for low-bandwidth control). Never satellite TX, never "Starlink-style" uplink features.
- Wi-Fi hotspot and mesh operation remain subject to **national law** (EIRP, outdoor channels, DFS, registration).
- Any amateur radio transmit beyond unlicensed mesh requires a **valid license** and is **outside** the default product scope.
- Software validators refuse forbidden mesh/source keywords (`satellite-uplink`, commercial decrypt names, etc.).

## 2. Allowed content and signals

SkyCache may process:

- Unencrypted **free-to-air** satellite broadcasts (e.g. public weather imagery paths supported by open tools).
- **Open amateur / CubeSat** telemetry where reception is lawful.
- Offline packages the operator is **licensed to redistribute** (CC, public domain, Kiwix ZIM redistribution terms, Ministry of Health leaflets, etc.).
- Operator-authored community materials.

SkyCache must **not** be used to:

- Decrypt or reverse-engineer **commercial encrypted** satellite internet (Starlink, OneWeb, commercial VSAT, paid TV CAS, etc.).
- Redistribute copyrighted material without rights.
- Conduct unauthorized surveillance of people.

Configuration validation **refuses** known-forbidden commercial decrypt source names.

## 3. Operator duties

Before turning on an antenna or hotspot, the local operator / NGO must:

1. Check **national spectrum** rules for satellite reception (usually receive-only is fine; confirm).
2. Check rules for **WiFi access points** (power limits, registration, encryption requirements).
3. Keep an inventory of content licenses on the hub.
4. Train staff not to promise "free Starlink" or medical diagnosis.

## 4. Privacy

- Default portal does **not** require login or harvest personal data for advertisers.
- Community notes are stored **locally**; treat them as sensitive.
- Logs stay on the device. Do not exfiltrate user traffic.
- Prefer no cameras, no device fingerprinting, no third-party analytics.

## 5. Safety

- Antenna masts: structural safety, lightning, grounding.
- Electrical: correct fusing, battery chemistry (prefer **LiFePO4**), fire extinguisher access.
- Health content: **educational only** - not diagnosis or prescription.
- Emergency content: align with **local** civil protection guidance.

## 6. Sustainability

- Buy repairable hardware; keep spare SD cards and a clone image.
- Train **local maintainers** (see `training-local-maintainer.md`).
- Plan e-waste: batteries and electronics disposal paths.
- Prefer solar sizing that avoids constant deep discharge.

## 7. Ethics / humanitarian framing

- Information access supports dignity, education, and health - not dependency on a foreign vendor's paid constellation.
- Community ownership: the hub should be operable when the volunteer leaves.
- Do not add covert monitoring "for security" without community consent and legal basis.
- Be honest about limits: **store-and-forward knowledge + community mesh**, not free commercial broadband.
- **Never misrepresent** Nexus as free Starlink / OneWeb / unlimited cellular. UI banners, README, and training materials must keep this language.

## 7b. Nexus mesh & opportunistic gateway

- Mesh RF: unlicensed Wi-Fi / regional ISM only; document power and duty-cycle limits; operator verifies national rules (`docs/mesh-deployment.md`).
- Gateway pulls: only open/FTA/CC/public-domain/Kiwix/MoH-style or operator-authored packs; **daily quotas** and priority classes (Emergency > Health > Education > ...).
- Do not enable transparent full-mesh NAT to the public internet by default.
- Data-mule (USB/phone handoff) is preferred when metered links are scarce.
- Disaster mode elevates emergency/health coordination traffic - still local mesh / store-and-forward, not "free internet."

## 8. Third-party tools

Wrapping SatDump, gr-satellites, Kiwix, etc. does not transfer their trademarks or change their licenses. Respect each project's license when redistributing binaries.

## 9. Skybrary (text archives)

- Skybrary may only ingest **public domain**, **openly licensed**, or **explicitly authorized** written works.
- Every work needs **provenance** (source corpus, retrieval note) and a **license inventory** entry.
- Never present Skybrary as a complete archive of all books ever written.
- Large corpora are **operator-hosted** packs - not dumped into the git repository.
- Health/history samples are **educational**, not professional advice.
- See `VISION-SKYBRARY.md` and `skybrary-architecture.md`.
