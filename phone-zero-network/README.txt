SkyCache zero-network demo kit
===============================
Format: skycache-zero-network-kit-v1

GOAL
----
Read the curated public-domain sample set on a phone that has
  - NO Wi-Fi
  - NO cell / mobile data

HOW (physics)
-------------
You cannot download over the air without a radio. This kit is
**local files**. Put them on the phone by any of:

  1. USB / OTG cable from a PC or SkyCache hub
  2. microSD card (if the phone has a slot)
  3. Bluetooth file send from another device that already has the kit
  4. Copy before you leave town (pre-deploy)

Then open READ-OFFLINE.html in the phone browser or a file viewer.
Airplane mode is fine. No network is used.

CONTENTS
--------
  READ-OFFLINE.html     All-in-one offline reader (open this first)
  texts/*.txt           Plain text of each work
  kit-manifest.json     Integrity / inventory
  README.txt            This file

WORKS
-----
This kit embeds the full curated public-domain sample set (see kit-manifest.json
work_count). Titles appear in READ-OFFLINE.html and under texts/*.txt.

LEGAL
-----
Public domain / educational samples only. Not medical advice.
Not a complete archive of written knowledge.
Not free Starlink or commercial satellite broadband.

Hub software: https://github.com/Pitchfork-and-Torch/SkyCache
Build kit:    skycache library zero-network --out ./kit
              skycache skybrary zero-network-kit --out ./kit
