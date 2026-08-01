# Open satellite data sources & related projects

SkyCache **builds on** existing open ecosystems rather than replacing them.

## Weather (free-to-air / public products)

| Source | Band / notes | Tooling |
|--------|----------------|---------|
| NOAA APT (legacy POES) | ~137 MHz FM APT | SatDump, classic APT decoders - availability has declined; check current status |
| Meteor-M LRPT | ~137 MHz digital | SatDump |
| GOES HRIT / EMWIN | L-band ~1.69 GHz | SatDump; needs dish/LNA/filter; Americas coverage |
| Other GEO LRIT/HRIT | Regional | SatDump pipelines |

Always confirm the satellite is still transmitting and that reception is lawful in your country.

## Amateur / educational telemetry

| Project | Role |
|---------|------|
| [gr-satellites](https://github.com/daniestevez/gr-satellites) | GNU Radio decoders for many amateur sats |
| [SatNOGS](https://satnogs.org/) | Global open ground-station network & DB |
| [TinyGS](https://tinygs.com/) | Ultra-low-cost LoRa ground stations |

Use for **education and open telemetry**, not commercial broadband.

## Offline education content

| Project | Role |
|---------|------|
| [Kiwix](https://kiwix.org/) / ZIM | Offline Wikipedia & many OERs |
| [Internet-in-a-Box](https://internet-in-a-box.org/) | Multi-service offline server |
| [RACHEL](https://rachel.worldpossible.org/) | Curated offline education packs |
| Kolibri | Learning platform often used offline |

## Historical inspiration (do not depend on live service)

| Project | Note |
|---------|------|
| Outernet / Othernet | Receive-only content broadcast concept; **service discontinued** (~2024 - 2025). Useful UX history only. |

## Hardware abstraction

| Project | Role |
|---------|------|
| SoapySDR | Vendor-neutral SDR API |
| RTL-SDR | Ultra-low-cost DVB-T dongles used as SDR |

## SkyCache integration stance

1. **Wrap** SatDump / gr-satellites via plugins.  
2. **Import** ZIM and HTML packs.  
3. **Serve** with a simple PWA hotspot.  
4. **Never** target encrypted commercial constellations.

## Legal pathway brainstorms

See [`legal-pathways-rf-and-content.md`](legal-pathways-rf-and-content.md) for:

- Lawful open **decode / demod / decompress / authorized decrypt** (vs piracy)  
- Lawful **receive + transmit** (Wi-Fi/ISM mesh, licensed amateur - never default sat uplink)
