# SkyCache / Skybrary threat model (one-pager)

**Audience:** maintainers, NGO partners, auditors.  
**Scope:** village hub + Skybrary dual-access + unlicensed mesh.  
**Not a complete security certification.**

## What we protect

| Asset | Why it matters |
|-------|----------------|
| Open written knowledge on the node | Offline dignity when networks fail |
| Integrity of packs (SHA-256 trees) | Silent bit-rot is worse than a small honest library |
| Operator control of the hub | Local ownership; no cloud landlord |
| Privacy of village users | No personal-data harvest by design |
| Legal posture | Public domain / open licenses only; receive-only RF |

## What we refuse (by product design)

- Decrypting commercial satellite broadband (Starlink, OneWeb, paid VSAT, DRM)
- Satellite uplink features by default
- Hoarding copyrighted commercial ebooks "for the library"
- Always-on cloud accounts or third-party analytics
- Unlicensed spectrum abuse beyond ISM/Wi-Fi as documented

## Threats and responses

| Threat | Impact | Response |
|--------|--------|----------|
| Bit-rot / silent disk errors | Corrupt library | `skybrary doctor --verify --record`; weekly timer; blob store for large objects |
| Malicious pack drop | Bad content on hub | License gate fail-closed; signed pack manifests; operator PIN admin |
| Compromised shared gateway | Quota abuse / bad pulls | Daily gateway quota + local pull receipts; open-mirror presets only |
| Mesh peer spoof (local) | Wrong packages | Prefer fingerprint + admin review; unlicensed mesh is not global PKI |
| Over-claiming marketing | Partner distrust | Honest banners: store-and-forward, not free Starlink |
| Legal / regulatory RF risk | Fines, confiscation | Capability matrix; legal_rf_mode; operator must check local law |
| Power loss | Dark school/clinic | Power modes ECO/CRITICAL; solar notes; printable maintainer sheet |
| Supply-chain / USB mule | Altered kits | Verify content tree; partner kits with license passports |

## Trust boundaries

```text
[SDR / FTA sky RX] --receive only--> [decoder plugins]
[USB / SD / BT mule] --------------> [ingest + license gate]
[Unlicensed Wi-Fi mesh peers] -----> [Nexus fabric + works_manifest]
[Optional metered open gateway] ---> [quota + receipts; no commercial decrypt]
[Admin PIN browser] ---------------> [local PWA only]
```

No third-party SaaS is required for core offline service.

## Residual risks (honest)

- Real batman-adv dual-radio still needs field validation per board (docs + sim are green).
- Metadata-only works federation does not move multi-GB bodies without packs/handoff.
- Golden SD kit is scripts + plan; multi-GB `.img.xz` is operator-hosted, not in git.
- Health content is educational, not clinical diagnosis.

## Related docs

- [`legal-ethics.md`](legal-ethics.md)
- [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md)
- [`VISION-SKYBRARY.md`](VISION-SKYBRARY.md)
- Capability matrix: `skycache capabilities`
