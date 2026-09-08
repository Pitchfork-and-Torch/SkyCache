# v1.0.0 Skybrary Resilience Fabric - success criteria

| Criterion | Evidence |
|-----------|----------|
| Bit-rot record path | `skybrary doctor --verify --record` -> `data/ops/bitrot-last.json` |
| Schedule templates | `bitrot install-templates` + `deploy/bitrot/*` |
| Doctor shows schedule | `skycache doctor` / skybrary doctor schedule lines |
| Multi-node works federation sim | `nexus federation --nodes 2` pulls packages + imports works |
| Local ops API | `GET /api/ops/local`, `skycache ops status` |
| Integrity API | `GET /api/integrity/last` |
| Fleet heartbeat default OFF | ops snapshot `fleet_heartbeat.enabled == false` |
| Threat model one-pager | `docs/threat-model.md` |
| Fabric attaches Skybrary | `create_app` -> `fabric.attach_skybrary` |
| Tests | `tests/test_v100_resilience_fabric.py` green |
| Version 1.0.0 | `__init__.py`, `pyproject.toml`, CHANGELOG, site |
| Honest residual | Real batman hardware video, multi-GB Pi `.img` still operator-hosted |

## Commands

```bash
pytest -q
python -m skycache skybrary doctor --verify --record
python -m skycache ops status
python -m skycache nexus federation --nodes 2 --rounds 1
python -m skycache bitrot install-templates --out deploy/bitrot
```
