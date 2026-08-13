# v0.8.0 success criteria - independent reviewer checklist

**Release:** Village Ready + Skybrary Dual-Access  
**Software:** `skycache 0.8.0`  
**Legal:** receive-only sat  |  open content  |  ISM mesh  |  no commercial decrypt  |  honest scope

## A. Automated (must pass)

```bash
cd SkyCache
python -m pip install -e ".[dev]"
python -m pytest -q
# Expect: 77+ passed

python -m skycache --version
# Expect: skycache 0.8.0

python -m skycache first-boot --data-dir /tmp/sc-demo --yes --pin 739184 --sim --force
python -m skycache nexus validate --nodes 2
python -m skycache nexus validate --nodes 3
python -m skycache skybrary pack --profile all-open-small --data-dir /tmp/sc-demo --out /tmp/sc-kit
python -m skycache skybrary export-catalog --data-dir /tmp/sc-demo --out /tmp/sc-cat
python -m skycache licenses --data-dir /tmp/sc-demo --html /tmp/licenses.html
python -m skycache gateway --data-dir /tmp/sc-demo --sim --presets
```

## B. Village in a weekend (lab / sim path)

- [ ] Volunteer follows `docs/first-boot.md` without prior SkyCache experience
- [ ] Portal serves samples + Skybrary Library after first-boot
- [ ] Admin PIN is not default `2468`
- [ ] `skycache capabilities` shows legal matrix; onboarding mentions mode
- [ ] Phone on hub Wi-Fi (cell data off) can open portal and save demos
- [ ] Admin **Build USB kit** or CLI pack produces `profile-manifest.json` + `.sha256`
- [ ] Admin **Export handoff** shows path + URL + QR canvas
- [ ] Power maintainer sheet loads and prints
- [ ] License inventory HTML loads and is printable
- [ ] No copy claims "free internet" or complete archive

## C. Dual-access foundations

- [ ] `export-catalog` writes `catalog.json` + `index.html` with work metadata
- [ ] Catalog legal banner present (not complete archive)
- [ ] Pack profile list includes `stem-2gb`, `local-heritage`, `language-xx`
- [ ] Provenance report generates for content tree

## D. Nexus / gateway ethics

- [ ] Gateway snapshot includes `open_mirror_presets` and `receipts`
- [ ] Admin can set daily quota (PIN)
- [ ] Mesh validate 2-node and 3-node sim OK
- [ ] Disaster drill doc still accurate (`docs/disaster-drill.md`)

## E. Site + docs

- [ ] CHANGELOG 0.8.0 entry complete
- [ ] `docs/partner-kits.md` present
- [ ] skycache.jonbailey.xyz status string references 0.8.0
- [ ] Upgrade notes from 0.7.x documented (no data migration)

## F. Explicit remaining (not failure for 0.8.0)

- Full golden SD image bake
- Gutenberg batch catalog adapter
- Content-addressed multi-GB blob store
- Field batman-adv video proof
- Partner civil-protection live drill

**Pass bar:** A green + B majority + C + D core + E. Honest gaps listed in F.
