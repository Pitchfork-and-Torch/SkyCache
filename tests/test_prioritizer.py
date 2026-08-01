from datetime import datetime, timedelta, timezone

from skycache.models import ContentPackage, PriorityClass, SourceInfo
from skycache.policy.prioritizer import Prioritizer, compute_score


def _pkg(pid: str, pclass: PriorityClass, hours_ago: float = 1, size: int = 1000, pinned: bool = False):
    return ContentPackage(
        id=pid,
        kind="test",
        priority_class=pclass,
        title={"en": pid},
        received_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        freshness_hours=24,
        size_bytes=size,
        source=SourceInfo(type="test"),
        pinned=pinned,
    )


def test_emergency_beats_general():
    em = _pkg("e1", PriorityClass.EMERGENCY)
    gen = _pkg("g1", PriorityClass.GENERAL)
    assert compute_score(em) > compute_score(gen)


def test_health_beats_weather():
    h = _pkg("h1", PriorityClass.HEALTH)
    w = _pkg("w1", PriorityClass.WEATHER)
    assert compute_score(h) > compute_score(w)


def test_fresh_beats_stale_same_class():
    fresh = _pkg("f1", PriorityClass.EDUCATION, hours_ago=1)
    stale = _pkg("s1", PriorityClass.EDUCATION, hours_ago=200)
    assert compute_score(fresh) > compute_score(stale)


def test_eviction_skips_emergency_and_pinned(tmp_path):
    pri = Prioritizer(content_dir=tmp_path, disk_reserve_bytes=10**15, max_content_bytes=2500)
    candidates = [
        (_pkg("em", PriorityClass.EMERGENCY, size=1000), 9999),
        (_pkg("pin", PriorityClass.GENERAL, size=1000, pinned=True), 10),
        (_pkg("low", PriorityClass.TELEMETRY_RAW, size=1000), 1),
        (_pkg("mid", PriorityClass.GENERAL, size=1000), 50),
    ]
    # Force need_bytes to trigger plan
    remove = pri.plan_evictions(candidates, catalog_total_size=4000, need_bytes=0)
    # max_content 2500 with catalog 4000 -> need to free 1500+
    assert "em" not in remove
    assert "pin" not in remove
    assert "low" in remove


def test_disaster_mode_protects_health(tmp_path):
    pri = Prioritizer(
        content_dir=tmp_path,
        disk_reserve_bytes=10**15,
        max_content_bytes=1500,
        disaster_mode=True,
    )
    candidates = [
        (_pkg("em", PriorityClass.EMERGENCY, size=800), 9999),
        (_pkg("he", PriorityClass.HEALTH, size=800), 8000),
        (_pkg("ed", PriorityClass.EDUCATION, size=800), 100),
        (_pkg("raw", PriorityClass.TELEMETRY_RAW, size=800), 1),
    ]
    remove = pri.plan_evictions(candidates, catalog_total_size=3200, need_bytes=0)
    assert "em" not in remove
    assert "he" not in remove
    assert "raw" in remove or "ed" in remove
    # Disaster scores boost survival classes
    assert pri.score(_pkg("he", PriorityClass.HEALTH)) > pri.score(
        _pkg("ed", PriorityClass.EDUCATION)
    )
