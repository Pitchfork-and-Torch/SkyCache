# Zero-network phone - no Wi-Fi, no cell

**Goal:** A person whose phone has **neither Wi-Fi nor cellular service** can still **read the three demo texts**.

## Physics (honest)

| Situation | Can they *download* in the field? | Can they *read*? |
|-----------|-------------------------------------|------------------|
| No Wi-Fi, no cell, no prior files | **No** | **No** |
| No Wi-Fi, no cell, kit already on storage | N/A | **Yes** |
| USB / SD / Bluetooth just loaded the kit | Transfer was physical | **Yes** |
| Hub Wi-Fi only (no cell) | Yes, over local Wi-Fi | Yes |

You cannot move bits through empty air without a radio. SkyCache does **not** claim magic.  
We claim: **once the files are on the phone, zero network is required to read them.**

## Product path

```text
[Somewhere with a cable / card / BT peer / pre-deploy]
        USB  |  OTG  |  microSD  |  Bluetooth  |  factory copy
                    ▼
        Phone storage: READ-OFFLINE.html + texts/
                    ▼
        Middle of nowhere, airplane mode, no radios
                    ▼
        Open READ-OFFLINE.html -> read all 3 demos
```

## Build / get the kit

```bash
# CLI (any laptop; no internet needed after SkyCache is installed)
skycache skybrary zero-network-kit --out ./kit --zip

# Or from a running hub (operator may use Wi-Fi *once* to prepare a stick)
# GET /api/demo/zero-network-kit.zip
# GET /api/demo/READ-OFFLINE.html
```

Repo sample (shipped in git for USB copy without installing):

```text
samples/phone-zero-network/READ-OFFLINE.html
samples/phone-zero-network/texts/*.txt
samples/phone-zero-network/README.txt
```

## Load onto the phone

1. **USB / OTG** - connect phone to PC or hub; copy the kit folder (or unzip) into Downloads/Documents.  
2. **microSD** - copy kit to card; insert; open Files.  
3. **Bluetooth** - from a second device that already has `READ-OFFLINE.html`, send the file.  
4. **Pre-deploy** - copy before the trip (clinic inventory, school tablets, etc.).

Then open **`READ-OFFLINE.html`** in the browser or HTML viewer. Large-type reader; A+/A−; works offline forever.

## Related tiers

| Tier | Doc |
|------|-----|
| Zero network (this) | `docs/zero-network-phone.md` |
| No cell, but hub Wi-Fi | `docs/phone-offline-demo.md` |
| Village hub install | `docs/first-boot.md` |

## Legal

Public-domain curated samples only. Not medical advice. Not a complete archive.  
Not free Starlink / commercial broadband.
