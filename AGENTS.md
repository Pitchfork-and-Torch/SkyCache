# AGENTS.md - SkyCache / Skybrary

Rules for human and AI contributors working in this repository.

---

## Mission

**Skybrary (the Sky Library)** is the long-horizon mission: resilient, legal, dual-access (online + offline) preservation and distribution of humanity's *open* written knowledge.

**SkyCache** is the field runtime: receive-only community hub, prioritizer, local PWA, Nexus mesh/DTN, low-cost hardware.

Do not invent a second product that abandons offline nodes or legal rails.

Canonical vision: [`docs/VISION-SKYBRARY.md`](docs/VISION-SKYBRARY.md)  
Architecture: [`docs/skybrary-architecture.md`](docs/skybrary-architecture.md)  
Roadmap: [`docs/skybrary-roadmap.md`](docs/skybrary-roadmap.md)

---

## Non-negotiable

1. **Legal content only** - public domain, Creative Commons / open licenses, government open materials, or operator-authorized packs. Track provenance. Never facilitate copyright infringement.  
2. **Receive-only satellite RF** - no uplink features by default; no commercial constellation decryption (Starlink, OneWeb, paid VSAT, DRM bypass).  
3. **Honest framing** - never claim free commercial broadband or a complete archive of every text ever written.  
4. **Mesh TX** - unlicensed/ISM only; document spectrum duty.  
5. **Offline-first** - prioritization and pack profiles remain first-class.  
6. **Apache-2.0** software; respect third-party licenses for tools and corpora.  
7. **Privacy** - no third-party analytics; no personal-data harvest.  
8. **Local ownership** - features must be operable by trained community maintainers.  

Details: [`docs/legal-ethics.md`](docs/legal-ethics.md).

---

## Stack continuity

- Python 3.11+, FastAPI, SQLite, static multi-language PWA  
- Prefer extending plugins / packages over rewrites  
- Simulation mode (`--sim`, Nexus sim) required for CI  
- Hardware target: Raspberry Pi class + optional RTL-SDR + commodity Wi-Fi  

---

## Coding practice

- Modular, testable packages under `skycache/`  
- Skybrary code under `skycache/skybrary/`  
- Tests in `tests/`; run `pytest -q` before claiming done  
- UTF-8 without BOM for JSON/manifests  
- Public GitHub: Pitchfork-and-Torch hygiene (single-commit product main, secret scan, Apache-2.0)  

---

## Documentation practice

When changing mission scope or architecture:

1. Update VISION / architecture / roadmap as needed  
2. Keep README honest about **current** vs **planned**  
3. Never remove legal banners from UI/docs  

---

## Agent checklist (each session)

- [ ] Did this change strengthen legal rails or leave them intact?  
- [ ] Does offline still work without cloud?  
- [ ] Are new corpora license-checked?  
- [ ] Did we avoid over-claiming completeness or "free internet"?  
- [ ] Tests + docs updated?  
- [ ] **Big feature/version ship?** Also update and redeploy https://skycache.jonbailey.xyz (`~/skycache-web`) - standing practice, do not leave the marketing site stale  

Marketing ops skill: `skycache-network-ops` (section *big software ship -> always update the marketing site*).
