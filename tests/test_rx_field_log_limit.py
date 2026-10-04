"""rx field log list must honor limit=0 (no forced single row)."""

from __future__ import annotations

from pathlib import Path

from skycache.rx.field_log import append_field_log, list_field_log


def test_list_field_log_limit_zero(tmp_path: Path) -> None:
    for i in range(5):
        append_field_log(tmp_path, satellite=f"SAT{i}")
    assert list_field_log(tmp_path, limit=0) == []
    assert len(list_field_log(tmp_path, limit=2)) == 2
    assert [e["satellite"] for e in list_field_log(tmp_path, limit=2)] == ["SAT3", "SAT4"]


def test_list_field_log_negative_is_empty(tmp_path: Path) -> None:
    append_field_log(tmp_path, satellite="NOAA-19")
    assert list_field_log(tmp_path, limit=-1) == []
