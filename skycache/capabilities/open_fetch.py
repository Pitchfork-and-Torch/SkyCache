"""Allowlisted open HTTPS fetch for legal opportunistic gateway pulls.

Never fetches arbitrary URLs. Only known open-content patterns or operator
allowlist files. No commercial decrypt.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger("skycache.capabilities.open_fetch")

# Host suffixes that may host open content (operator still verifies license of each work)
DEFAULT_OPEN_HOST_SUFFIXES: tuple[str, ...] = (
    "gutenberg.org",
    "www.gutenberg.org",
    "gutenberg.cc",
    "archive.org",
    "www.archive.org",
    "wikimedia.org",
    "upload.wikimedia.org",
    "kiwix.org",
    "download.kiwix.org",
    "raw.githubusercontent.com",
    "github.com",
    "gitlab.com",
    "creativecommons.org",
    "openlibrary.org",
    "cdn.jsdelivr.net",  # only for open project assets
    # Open-access science (operator still verifies per-work license)
    "arxiv.org",
    "export.arxiv.org",
    "ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "europepmc.org",
    "www.europepmc.org",
    "plos.org",
    "journals.plos.org",
)

FORBIDDEN_URL_MARKERS: frozenset[str] = frozenset(
    {
        "starlink",
        "oneweb",
        "decrypt",
        "card-sharing",
        "warez",
        "pirate",
        "netflix",
        "spotify",
        "kindle",
    }
)


def _host_allowed(host: str, extra: list[str] | None = None) -> bool:
    host = (host or "").lower().strip(".")
    allowed = list(DEFAULT_OPEN_HOST_SUFFIXES) + list(extra or [])
    for suf in allowed:
        suf = suf.lower().strip(".")
        if host == suf or host.endswith("." + suf):
            return True
    return False


def validate_open_url(url: str, extra_hosts: list[str] | None = None) -> str:
    url = (url or "").strip()
    lowered = url.lower()
    for bad in FORBIDDEN_URL_MARKERS:
        if bad in lowered:
            raise ValueError(f"Refusing URL: forbidden marker '{bad}'")
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError("Only http(s) URLs allowed for open fetch")
    if parsed.scheme == "http":
        # Prefer HTTPS; allow http only for local sim mirrors
        if parsed.hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("Remote open fetch requires HTTPS")
    if not _host_allowed(parsed.hostname or "", extra_hosts):
        raise ValueError(
            f"Host '{parsed.hostname}' not on open-content allowlist. "
            "Add to operator allowlist file only for hosts you legally may use."
        )
    return url


def load_extra_hosts(path: Path | None) -> list[str]:
    if not path or not Path(path).is_file():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return [str(x) for x in data]
    return [str(x) for x in data.get("hosts") or []]


def fetch_open_url(
    url: str,
    dest: Path,
    *,
    extra_hosts: list[str] | None = None,
    timeout: float = 30.0,
    max_bytes: int = 50 * 1024 * 1024,
    user_agent: str = "SkyCache-OpenFetch/0.6 (+https://github.com/Pitchfork-and-Torch/SkyCache; open content only)",
) -> dict[str, Any]:
    """Download allowlisted open URL to dest. Returns metadata."""
    url = validate_open_url(url, extra_hosts)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = 0
            with dest.open("wb") as out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"Exceeds max_bytes={max_bytes}")
                    out.write(chunk)
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Open fetch failed: {exc}") from exc
    log.info("Open fetch %s -> %s (%d bytes)", url, dest, total)
    return {
        "url": url,
        "path": str(dest),
        "bytes": total,
        "content_type": ctype,
        "legal": "Allowlisted open HTTPS fetch only - verify work license before redistribute",
    }
