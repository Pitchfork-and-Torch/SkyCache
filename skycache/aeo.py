"""Answer-engine / AEO surfaces: llms.txt, robots.txt, honesty claims.

Canonical advertised version lives in `skycache.__version__`. Generated text
must stay lockstep with README badges, CHANGELOG, and the marketing site.
Never invent Mbps. Never claim dish throughput. Never claim free commercial
satellite broadband. RX doctor remain fail-closed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from skycache import __version__

# Keep a local copy so `python -m skycache.aeo` does not import pydantic Settings.
# Curated dual-access count (must match len(SAMPLES); locked by tests).
CURATED_WORK_COUNT = 78
HONEST_BANNER = (
    "SkyCache Nexus: store-and-forward knowledge + community mesh on unlicensed "
    "Wi-Fi/ISM. Receive-only for satellite. Not free commercial broadband or Starlink."
)

SITE = "https://skycache.jonbailey.xyz"
REPO = "https://github.com/Pitchfork-and-Torch/SkyCache"
EDITION = "Honesty / AEO consistency"
HONEST_ONE_LINER = (
    "SkyCache is receive-only for satellite RF and is NOT free commercial "
    "satellite broadband (not Starlink, OneWeb, or paid VSAT)."
)

# Invented numeric throughput - denials like "no invented Mbps" are allowed.
NUMERIC_THROUGHPUT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:[Mm]bps|[Mm]bit|[Gg]bit)")
DISH_THROUGHPUT_RE = re.compile(
    r"dish.{0,40}\d+(?:\.\d+)?\s*(?:[Mm]bps|[Mm]bit)",
    re.I,
)


def honesty_claims() -> dict[str, Any]:
    """Machine-readable scope a stranger can GET from /api/health."""
    return {
        "receive_only": True,
        "commercial_broadband": False,
        "rx_legal_fail_closed": True,
        "complete_archive": False,
        "medical_advice": False,
        "invented_mbps": False,
        "dish_mbps": False,
        "banner": HONEST_BANNER,
    }


def render_llms_txt() -> str:
    """Answer-engine brief. Version is the package version. No Mbps claims."""
    works = CURATED_WORK_COUNT
    claims = honesty_claims()
    lines = [
        "# SkyCache Nexus  |  Skybrary",
        "",
        "> Open-source community knowledge fabric + Skybrary dual-access library. "
        "Receive-only satellite, unlicensed mesh, open content only - never free "
        "commercial satellite broadband.",
        "",
        f"- Site: {SITE}/",
        f"- How to use: {SITE}/use/",
        f"- Roadmap tracker: {SITE}/roadmap/",
        f"- Library: {SITE}/library/",
        f"- Mission: {SITE}/mission/",
        f"- RX: {SITE}/rx/",
        f"- Developers: {SITE}/developers/",
        f"- Software: {REPO}",
        f"- Latest: v{__version__}",
        f"- Version: software {__version__}",
        f"- Status: {EDITION} - {works} curated PD works; RX doctor "
        "legal_receive_only is fail-closed; not medical advice",
        "- Email: skycache@jonbailey.xyz",
        "",
        "## One-liner",
        "",
        "SkyCache turns lawful free-to-air reception and open education packs into "
        "a local Wi-Fi library and community mesh, with a dual-access Skybrary "
        f"({works} curated public-domain works), archive size budgets, RX ops, "
        "and honest legal rails. "
        + HONEST_ONE_LINER
        + " Not a complete archive. Not medical advice. "
        "No invented Mbps. No dish Mbps.",
        "",
        "## What a stranger should know",
        "",
        f"- Receive-only satellite RF: {claims['receive_only']}",
        f"- Commercial satellite broadband: {claims['commercial_broadband']}",
        f"- RX doctor legal_receive_only fail-closed: {claims['rx_legal_fail_closed']}",
        f"- Complete archive of every text: {claims['complete_archive']}",
        f"- Medical advice: {claims['medical_advice']}",
        f"- Invented Mbps / dish Mbps: {claims['invented_mbps']}",
        f"- Banner: {HONEST_BANNER}",
        "",
        "## Operator downloads",
        "",
        f"- Golden SD kit: {SITE}/downloads/skycache-golden-sd-kit.zip",
        f"- Dual-radio kit: {SITE}/downloads/skycache-dual-radio-kit.zip",
        f"- Mission kit: {SITE}/downloads/skycache-mission-kit.zip",
        f"- Library kit: {SITE}/downloads/skycache-library-kit.zip",
        f"- Zero-network kit: {SITE}/downloads/skycache-zero-network-demo-kit.zip",
        f"- Literacy / clinic packs: {SITE}/library/",
        "",
        "## FAQ",
        "",
        "Q: Is SkyCache free commercial satellite broadband / free Starlink?",
        "A: No. Receive-only store-and-forward knowledge plus optional unlicensed "
        "community mesh. It does not decrypt paid constellations and does not "
        "provide bidirectional commercial internet.",
        "",
        "Q: Does RX doctor go green on a Starlink or uplink mode string?",
        "A: No. legal_receive_only is fail-closed (v1.34.1+). Unknown, empty, or "
        "forbidden modes fail; go_rx_live stays gated on that check.",
        "",
        "Q: What throughput does a dish get?",
        "A: SkyCache does not advertise dish Mbps or invented satellite speeds. "
        "FTA weather / open amateur paths vary by hardware, weather, and site. "
        "Measure locally; do not quote a product Mbps.",
        "",
        "Q: Do you ship a multi-GB .img in the repo?",
        "A: No. Download the golden SD kit zip, flash Pi OS Lite, run bake. "
        "Optional sealed .img.xz can attach to GitHub Releases when an operator "
        "builds one.",
        "",
        "Q: Multi-GB maps in the monorepo?",
        "A: No. Use skycache maps import + blob store for regional MBTiles you "
        "may legally redistribute.",
        "",
    ]
    return "\n".join(lines)


def render_robots_txt(*, sitemap: str = f"{SITE}/sitemap.xml") -> str:
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            "User-agent: GPTBot",
            "Allow: /",
            "",
            "User-agent: ClaudeBot",
            "Allow: /",
            "",
            "User-agent: PerplexityBot",
            "Allow: /",
            "",
            "User-agent: OAI-SearchBot",
            "Allow: /",
            "",
            f"Sitemap: {sitemap}",
            f"# Answer-engine brief: {SITE}/llms.txt",
            "",
        ]
    )


def write_aeo_files(out_dir: Path, *, sitemap: str = f"{SITE}/sitemap.xml") -> dict[str, Any]:
    """Write UTF-8 llms.txt + robots.txt (no BOM)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    llms = out_dir / "llms.txt"
    robots = out_dir / "robots.txt"
    llms.write_text(render_llms_txt(), encoding="utf-8", newline="\n")
    robots.write_text(render_robots_txt(sitemap=sitemap), encoding="utf-8", newline="\n")
    return {
        "ok": True,
        "version": __version__,
        "llms": str(llms),
        "robots": str(robots),
        "banner": HONEST_BANNER,
    }


def aeo_text_is_honest(text: str) -> tuple[bool, list[str]]:
    """Reject invented numeric throughput / dish Mbps on advertised AEO copy."""
    blob = text or ""
    hits: list[str] = []
    if NUMERIC_THROUGHPUT_RE.search(blob):
        hits.append("numeric Mbps/Mbit")
    if DISH_THROUGHPUT_RE.search(blob):
        hits.append("dish Mbps")
    return (len(hits) == 0, hits)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    write_aeo_files(repo_root())
    print(f"wrote llms.txt + robots.txt for v{__version__}")
