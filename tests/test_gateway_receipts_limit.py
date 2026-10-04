"""gateway receipts must honor limit=0 (no forced single receipt)."""

from __future__ import annotations

import json
from pathlib import Path

from skycache.nexus.gateway_presets import PullReceiptLog


def _seed(path: Path, n: int = 5) -> None:
    entries = [{"preset_id": f"p{i}", "ok": True, "bytes": i} for i in range(n)]
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_list_recent_limit_zero(tmp_path: Path) -> None:
    path = tmp_path / "gateway-receipts.json"
    _seed(path, 5)
    log = PullReceiptLog(path)
    assert log.list_recent(0) == []
    assert len(log.list_recent(2)) == 2
    assert [e["preset_id"] for e in log.list_recent(2)] == ["p3", "p4"]


def test_list_recent_negative_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "gateway-receipts.json"
    _seed(path, 3)
    log = PullReceiptLog(path)
    assert log.list_recent(-1) == []
