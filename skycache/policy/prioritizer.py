"""Content prioritization and disk pressure eviction."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from skycache.models import CLASS_WEIGHTS, ContentPackage, PriorityClass


def hours_since(when: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (now - when.astimezone(timezone.utc)).total_seconds() / 3600.0)


def freshness_factor(package: ContentPackage, now: datetime | None = None) -> float:
    """1.0 when fresh; decays toward 0.15 after freshness_hours."""
    age = hours_since(package.received_at, now)
    if package.freshness_hours <= 0:
        return 0.5
    ratio = age / float(package.freshness_hours)
    if ratio <= 1.0:
        return 1.0 - 0.3 * ratio
    # Stale but not worthless (historical education still useful)
    return max(0.15, 0.7 / ratio)


def language_match_factor(package: ContentPackage, preferred: list[str] | None) -> float:
    if not preferred:
        return 1.0
    langs = set(package.languages) | set(package.title.keys())
    for i, lang in enumerate(preferred):
        if lang in langs:
            # Prefer earlier languages slightly
            return 1.0 - min(0.15, 0.03 * i)
    return 0.75


def compute_score(
    package: ContentPackage,
    preferred_languages: list[str] | None = None,
    now: datetime | None = None,
) -> float:
    weight = CLASS_WEIGHTS.get(package.priority_class, 100.0)
    fresh = freshness_factor(package, now)
    lang = language_match_factor(package, preferred_languages)
    pin = 10.0 if package.pinned else 1.0
    # Emergency always dominates
    if package.priority_class == PriorityClass.EMERGENCY:
        pin = max(pin, 5.0)
    return weight * fresh * lang * pin


def disk_usage(path: Path) -> tuple[int, int, int]:
    """Return (total, used, free) bytes for the filesystem containing path."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    return usage.total, usage.used, usage.free


# Classes protected under disaster / power-critical disk pressure
SURVIVAL_CLASSES = frozenset(
    {
        PriorityClass.EMERGENCY,
        PriorityClass.HEALTH,
    }
)


class Prioritizer:
    """Apply retention policy when storage is low."""

    def __init__(
        self,
        content_dir: Path,
        disk_reserve_bytes: int = 500 * 1024 * 1024,
        max_content_bytes: int = 0,
        preferred_languages: list[str] | None = None,
        *,
        disaster_mode: bool = False,
        power_critical: bool = False,
    ) -> None:
        self.content_dir = Path(content_dir)
        self.disk_reserve_bytes = disk_reserve_bytes
        self.max_content_bytes = max_content_bytes
        self.preferred_languages = preferred_languages or ["en"]
        # Disaster / power-critical: never evict emergency+health; demote archive first
        self.disaster_mode = bool(disaster_mode)
        self.power_critical = bool(power_critical)

    def score(self, package: ContentPackage) -> float:
        base = compute_score(package, self.preferred_languages)
        if self.disaster_mode or self.power_critical:
            if package.priority_class in SURVIVAL_CLASSES:
                return base * 3.0
            if package.priority_class == PriorityClass.TELEMETRY_RAW:
                return base * 0.25
            if package.priority_class == PriorityClass.GENERAL:
                return base * 0.5
        return base

    def pressure(self, catalog_total_size: int) -> bool:
        _, _, free = disk_usage(self.content_dir)
        if free < self.disk_reserve_bytes:
            return True
        if self.max_content_bytes > 0 and catalog_total_size > self.max_content_bytes:
            return True
        return False

    def is_protected(self, package: ContentPackage) -> bool:
        """True if package must not be evicted under current policy."""
        if package.pinned:
            return True
        if package.priority_class == PriorityClass.EMERGENCY:
            return True
        if (self.disaster_mode or self.power_critical) and package.priority_class in SURVIVAL_CLASSES:
            return True
        return False

    def plan_evictions(
        self,
        candidates: list[tuple[ContentPackage, float]],
        catalog_total_size: int,
        need_bytes: int = 0,
    ) -> list[str]:
        """
        Return package ids to remove (lowest score first).

        Under disaster_mode or power_critical, emergency AND health are protected
        so survival content always wins under extreme disk or power pressure.
        Archive / telemetry go first; education can still flow when space remains.
        """
        _, _, free = disk_usage(self.content_dir)
        to_free = 0
        if free < self.disk_reserve_bytes:
            to_free = self.disk_reserve_bytes - free
        if self.max_content_bytes > 0 and catalog_total_size + need_bytes > self.max_content_bytes:
            to_free = max(
                to_free,
                catalog_total_size + need_bytes - self.max_content_bytes,
            )
        if to_free <= 0:
            return []

        ordered = sorted(candidates, key=lambda x: (x[1], x[0].received_at))
        remove: list[str] = []
        freed = 0
        for pkg, _score in ordered:
            if self.is_protected(pkg):
                continue
            remove.append(pkg.id)
            freed += max(0, pkg.size_bytes)
            if freed >= to_free:
                break
        return remove
