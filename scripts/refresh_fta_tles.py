"""Refresh free-to-air weather bird TLEs from Celestrak (public GP API).

Operator-run only. Respect Celestrak terms of use; do not hammer the API.
Outputs a text file suitable for: skycache rx tle-import FILE
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

UA = "SkyCache-RX-setup/1.1 (open-source station; https://skycache.jonbailey.xyz)"
# Classic APT-class birds + catalog fetch
NOAA_CATNR = (25338, 28654, 33591)  # NOAA 15, 18, 19


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/tle-fta-priority.txt")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = []
    for catnr in NOAA_CATNR:
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=tle"
        try:
            text = fetch(url).strip()
            if "1 " in text:
                blocks.append(text)
                print(f"ok CATNR {catnr}")
            else:
                print(f"empty CATNR {catnr}")
        except Exception as exc:  # noqa: BLE001
            print(f"fail CATNR {catnr}: {exc}")

    # Meteor-M and other weather birds (filter names)
    try:
        weather = fetch(
            "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle"
        )
        lines = [ln.rstrip() for ln in weather.splitlines() if ln.strip()]
        i = 0
        while i < len(lines):
            if (
                i + 2 < len(lines)
                and lines[i + 1].startswith("1 ")
                and lines[i + 2].startswith("2 ")
            ):
                name = lines[i].strip()
                if "METEOR" in name.upper():
                    blocks.append("\n".join(lines[i : i + 3]))
                    print(f"ok {name}")
                i += 3
                continue
            i += 1
    except Exception as exc:  # noqa: BLE001
        print(f"weather group fail: {exc}")

    if not blocks:
        print("No TLEs fetched")
        return 1

    body = "\n\n".join(blocks) + "\n"
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out} ({len(body)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
