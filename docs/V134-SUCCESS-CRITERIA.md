# v1.34.0 Software Mission Seal - success criteria

| Criterion | Evidence |
|-----------|----------|
| BLE ATT sim round-trip | `simulate_ble_exchange` ok, `live_radio` false |
| Power calibration | `power calibrate` writes `data/ops/power-calibration.json` |
| Soak protocols | four surfaces under kit/soak |
| Partner tabletop | `disaster tabletop` six stations, no RF |
| Mission doctor 100 | `go_software_mission` true, failed=[] |
| Field residuals listed | doctor includes residual ids, not deducted |
| API | `GET /api/mission/status` |
| Tests | `tests/test_v1340_mission_seal.py` green |
| Version 1.34.0 | `__init__.py`, `pyproject.toml`, CHANGELOG, site |
| Honest residual | Physical soaks / pilots / .img.xz / live BLE radio remain operator-owned |
