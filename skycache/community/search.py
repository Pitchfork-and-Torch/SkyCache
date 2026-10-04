"""Full-library search across catalog (local mesh node)."""

from __future__ import annotations

from typing import Any

from skycache.db.catalog import Catalog
from skycache.community.ratings import RatingsStore


def search_catalog(
    catalog: Catalog,
    q: str,
    *,
    lang: str | None = None,
    category: str | None = None,
    limit: int = 50,
    ratings: RatingsStore | None = None,
) -> list[dict[str, Any]]:
    """Rank packages by simple term match on title, summary, tags, id, license."""
    q = (q or "").strip().lower()
    records = catalog.list_packages(
        priority_class=category,
        lang=lang,
        q=None,
        limit=10_000,
    )
    out: list[dict[str, Any]] = []
    terms = [t for t in q.split() if t] if q else []

    for rec in records:
        p = rec.package
        blob = " ".join(
            [
                p.id,
                " ".join(p.title.values()),
                " ".join(p.summary.values()),
                " ".join(p.tags),
                p.license,
                p.priority_class.value,
                p.kind,
            ]
        ).lower()
        if terms:
            hits = sum(1 for t in terms if t in blob)
            if hits == 0:
                continue
            # Prefer more term hits + prioritizer score
            rank = hits * 1000.0 + float(rec.score or 0)
        else:
            rank = float(rec.score or 0)

        item: dict[str, Any] = {
            "id": p.id,
            "title": p.title,
            "summary": p.summary,
            "priority_class": p.priority_class.value,
            "license": p.license,
            "tags": p.tags,
            "score": rec.score,
            "age_hours": round(rec.age_hours, 2),
            "is_stale": rec.is_stale,
            "rank": rank,
            "size_bytes": p.size_bytes,
            "files": [f.model_dump() for f in p.files],
            "freshness_hours": p.freshness_hours,
            "received_at": p.received_at.isoformat(),
        }
        if ratings:
            item["rating"] = ratings.summary(p.id)
        out.append(item)

    out.sort(key=lambda x: (-x["rank"], -float(x.get("score") or 0)))
    return out[:limit]
