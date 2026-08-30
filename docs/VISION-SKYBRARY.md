# Skybrary - The Sky Library

**Working name:** Skybrary (SKY LIBRARY)  
**Foundation:** [SkyCache](https://github.com/Pitchfork-and-Torch/SkyCache) / [skycache.jonbailey.xyz](https://skycache.jonbailey.xyz)  
**License:** Apache-2.0  

---

## One sentence

**Protect the future of humanity by keeping the written knowledge of civilization enduringly accessible - online for those who can reach it, and offline everywhere else.**

---

## Why this exists

Knowledge is **civilizational infrastructure**. Centralized digital stores can be lost to war, censorship, infrastructure collapse, solar events, bit rot, or simple neglect. Communities with little or no reliable internet already live at the edge of that risk every day.

**Skybrary** evolves SkyCache from a community offline hub into a dual-access **catastrophe-resilient archive and distribution system** for the *written* record of humankind: literature, science, history, philosophy, technical knowledge, medicine, education, and cultural heritage.

We will **never** claim a literal "complete archive of every text ever written." That is the aspirational north star. What we build must be **honest, legal, durable, and useful at every intermediate milestone**.

---

## Relationship: SkyCache ↔ Skybrary

| Layer | Role |
|-------|------|
| **Skybrary** | Mission brand + archive architecture: corpus selection, catalog of *works*, online portal experience, long-horizon preservation |
| **SkyCache** | Proven field stack: receive-only RF, prioritizer, local PWA, mesh/DTN, USB mules, low-cost Pi nodes |
| **SkyCache Nexus** | Multi-node fabric already shipping (mesh, DTN, gateway, community UX 0.4) |

Skybrary **extends** SkyCache; it does not replace legal rails, offline-first design, or community ownership.

```text
                    ┌─────────────────────────────┐
                    │     SKYBRARY (north star)    │
                    │  Human written knowledge     │
                    │  dual access  |  long horizon  │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
     Online portal            Offline packs         Future open
     (global web PWA)         (SkyCache nodes)      satellite deltas
              │                    │                    │
              └────────────┬───────┴────────────────────┘
                           ▼
                 SkyCache runtime today
            (Python  |  FastAPI  |  SQLite  |  PWA  |  Nexus)
```

---

## Dual access model (non-negotiable)

1. **Online portal** - mobile-first PWA for people with connectivity: browse, search, read, download open packs.  
2. **Offline first-class** - prioritized packs for SkyCache nodes, USB data mules, mesh/DTN, low-resource devices.  

Neither mode is an afterthought. Constrained nodes always get **highest-value knowledge first**.

---

## What we will house (legal only)

Start with the richest **public-domain, Creative Commons, government, and openly licensed** corpora, for example:

- Project Gutenberg  
- Wikisource / Wikimedia free content (where redistribution terms allow)  
- Internet Archive public-domain collections (verified)  
- Open scientific literature (e.g. open-access journals, arXiv-style where license permits packaging)  
- National digital libraries' open subsets  
- Educational / MoH-style open materials  
- Operator-authored local heritage (with license inventory)

**Never:** copyrighted commercial ebooks without explicit authorization; commercial satellite decrypt; piracy mirrors.

---

## Non-negotiable constraints (carry forward + strengthen)

1. **Legal & ethical** - only PD / open / authorized content; full provenance and license tracking; never facilitate infringement.  
2. **Receive-only RF** - preserve SkyCache's satellite receive-only policy; no commercial constellation decryption; no "free broadband / free Starlink" claims.  
3. **Mesh TX** - unlicensed/ISM only; operator verifies national rules.  
4. **Open source** - Apache-2.0 software; respect third-party corpus licenses.  
5. **Offline-first & prioritization** - first-class on every design decision.  
6. **Honest capability framing** - intermediate milestones stated clearly; north star labeled aspirational.  
7. **Local ownership** - trained community maintainers can run nodes after volunteers leave.  
8. **Privacy** - no third-party analytics; local logs by default.  

Full field policy: [`legal-ethics.md`](legal-ethics.md).

---

## Success measures (civilizational, not vanity)

| Horizon | Success looks like |
|---------|-------------------|
| Near | Legal open-text packs ship; search + catalog work offline; license inventory clean |
| Mid | Village nodes carry multi-language high-value sets (health + literacy + science basics) |
| Long | Federated open archives + durable formats + catastrophe drills (USB/mesh/gateway) prove recovery paths |
| North star | Maximal *feasible* open written heritage reachable by the largest number of humans, online or offline |

---

## Brand language

- **Product name:** Skybrary (the Sky Library)  
- **Tagline options:**  
  - "Protect the future of humanity by building the Sky Library."  
  - "Written knowledge. Enduring access. Everywhere."  
- **Do not say:** "complete archive of everything," "free internet," "Starlink alternative."  

---

## Next documents

- [`skybrary-architecture.md`](skybrary-architecture.md) - system design  
- [`skybrary-roadmap.md`](skybrary-roadmap.md) - phased milestones  
- [`AGENTS.md`](../AGENTS.md) - agent/contributor rules for this mission  

---

*Knowledge is civilizational infrastructure. Skybrary exists so it does not vanish when the lights go out.*
