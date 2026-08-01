"""Captive portal redirect helpers for common OS connectivity checks."""

from __future__ import annotations

# Paths many OSes probe when joining a WiFi network.
CAPTIVE_PROBE_PATHS = frozenset(
    {
        "/generate_204",
        "/gen_204",
        "/hotspot-detect.html",
        "/library/test/success.html",
        "/ncsi.txt",
        "/connecttest.txt",
        "/success.txt",
        "/canonical.html",
        "/redirect",
    }
)


def is_captive_probe(path: str) -> bool:
    p = path.split("?")[0].rstrip("/") or "/"
    if p in CAPTIVE_PROBE_PATHS:
        return True
    # Android sometimes uses /generate_204 with host google.com
    if p.endswith("generate_204") or p.endswith("gen_204"):
        return True
    return False
