# Answer-engine optimization (AEO) - honest scope

SkyCache publishes a machine-readable brief so search and answer engines quote **what the product is**, not a free-Starlink fantasy.

## Canonical files

| File | Role |
|------|------|
| [`llms.txt`](../llms.txt) | Answer-engine brief (version + honesty) |
| [`robots.txt`](../robots.txt) | Crawler allow + sitemap + pointer to `llms.txt` |
| `skycache/aeo.py` | Generator - must match the committed files |
| Local portal | `GET /llms.txt`, `GET /robots.txt`, `GET /api/health` |

Regenerate committed files:

```text
python -m skycache aeo write
```

`skycache library sync --apply-web` stages the same files into `skycache-web/public/` so the marketing site does not drift.

## Non-negotiable claims

- **Receive-only** satellite RF. Unlicensed/ISM mesh TX is not satellite TX.
- **NOT** free commercial satellite broadband (not Starlink, OneWeb, paid VSAT).
- RX doctor `legal_receive_only` is **fail-closed** (v1.34.1+).
- **Not** a complete archive of every text ever written.
- Health samples are **educational**, not medical advice.
- **No invented Mbps.** **No dish Mbps.** Throughput is site-measured, never a product slogan.

## Version lockstep

Advertised version must match `skycache.__version__` / `pyproject.toml` in:

- README version badge
- CHANGELOG latest heading
- `llms.txt` (`Latest:` and `Version:`)
- `PROGRESS.md`
- portal `/api/health`

Tests: `tests/test_v1342_honesty_aeo.py`.

Live marketing site: https://skycache.jonbailey.xyz/llms.txt - redeploy `~/skycache-web` after a version ship.
