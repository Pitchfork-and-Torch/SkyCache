SkyCache maps-offline sample
============================

This package does NOT include multi-GB tile data (keeps the git repo small).

To add real offline maps (operator-run):
1. Download an open OSM extract or build MBTiles you may legally redistribute.
2. Record license (often ODbL with attribution) in manifest.json.
3. skycache blobs put ./region.mbtiles --media-type application/x-sqlite3
4. skycache skybrary pack --profile maps-offline

Never claim complete world map coverage. Prefer regional extracts for village nodes.
Not free commercial map APIs. Not free Starlink.
