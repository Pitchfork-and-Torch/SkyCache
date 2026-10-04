# v1.34.2 Honesty / AEO consistency - success criteria

| Criterion | Evidence |
|-----------|----------|
| Version 1.34.2 | `__init__.py`, `pyproject.toml`, CHANGELOG, README badge, `llms.txt`, `PROGRESS.md` |
| AEO files | Repo-root `llms.txt` + `robots.txt` match `skycache.aeo` renderer |
| Portal | `GET /llms.txt`, `GET /robots.txt` serve the same brief |
| Health honesty | `GET /api/health` includes receive_only, commercial_broadband=false, rx_legal_fail_closed |
| RX fail-closed | Existing `tests/test_v1170_rx_ops.py` still green |
| No invented Mbps | AEO scanner rejects Mbps / dish Mbps on advertised surfaces |
| Apply-web | `library sync --apply-web` copies `llms.txt` into marketing public/ |
| Legal rails | Receive-only; not free commercial satellite broadband; not a complete archive |
