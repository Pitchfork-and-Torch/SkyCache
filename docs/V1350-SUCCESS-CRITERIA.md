# v1.35.0 Village DTN store-and-forward - success criteria

| Criterion | Evidence |
|-----------|----------|
| Version 1.35.0 | `__init__.py`, `pyproject.toml`, CHANGELOG, README badge, `llms.txt`, `PROGRESS.md` |
| SHA-256 | Bundle `payload_sha256`; mule v2 rejects tamper |
| TTL | Expired pending bundles drop out of `pending()` / `expire_stale()` |
| Hop-limit | `forward-sim` does not flood past `hop_limit` |
| Custody | Hop-forward sets `custody_node`; USB mule import takes custody |
| CLI | `skycache dtn doctor|status|enqueue|export|import|verify|forward-sim` |
| API | `GET /api/dtn/status`, `POST /api/dtn/enqueue|export-mule|import-mule|verify` |
| Honesty | Not Starlink. Not RFC 9171. Not free commercial satellite broadband. |
| RX fail-closed | v1.34.1 `legal_receive_only` still rejects uplink / Starlink mode strings |
| Tests | `tests/test_dtn_store_forward.py` |
