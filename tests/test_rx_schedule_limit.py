"""build_schedule: honor limit=0 (empty slots, not coerce to 1)."""
from __future__ import annotations

from skycache.rx import schedule as sched


def test_build_schedule_limit_zero_empty(monkeypatch=None) -> None:
    fake = {
        "passes": [
            {"satellite": "NOAA-15", "aos": "2026-01-01T00:00:00Z", "los": "x"},
            {"satellite": "NOAA-18", "aos": "2026-01-01T01:00:00Z", "los": "y"},
        ]
    }

    def _fake_predict(**kwargs):
        return fake

    orig = sched.predict_passes
    sched.predict_passes = _fake_predict  # type: ignore[assignment]
    try:
        rep0 = sched.build_schedule(
            data_dir=".",
            lat=0.0,
            lon=0.0,
            alt_m=0.0,
            limit=0,
        )
        assert rep0.get("ok") is not False or "slots" in rep0
        assert rep0["slots"] == [], rep0
        rep1 = sched.build_schedule(
            data_dir=".",
            lat=0.0,
            lon=0.0,
            alt_m=0.0,
            limit=1,
        )
        assert len(rep1["slots"]) == 1
        rep2 = sched.build_schedule(
            data_dir=".",
            lat=0.0,
            lon=0.0,
            alt_m=0.0,
            limit=2,
        )
        assert len(rep2["slots"]) == 2
    finally:
        sched.predict_passes = orig  # type: ignore[assignment]


if __name__ == "__main__":
    test_build_schedule_limit_zero_empty()
    print("PASS test_rx_schedule_limit")
