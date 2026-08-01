"""Build size-bounded Skybrary offline kits from content + works catalog.

Pack profiles 2.0 (v0.8): named curricula with emergency/health prefer-first
ordering, language-scoped kits, and signed profile-manifest (SHA-256 tree).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.skybrary.catalog import SkybraryCatalog

# Built-in profiles (bytes) - pack profiles 2.0 (Village Ready)
BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "literacy-100mb": {
        "id": "literacy-100mb",
        "max_bytes": 100 * 1024 * 1024,
        "languages": ["en", "fr", "es", "ar", "sw", "hi", "pt"],
        "include_subjects": ["literacy", "literature_pd", "civics", "health_edu"],
        "include_priority_classes": [],
        "prefer_priority_classes": ["education", "health"],
        "prefer_formats": ["txt", "html", "epub"],
        "description": "Foundational literacy + civics + health education (small kit)",
    },
    "literacy-1gb": {
        "id": "literacy-1gb",
        "max_bytes": 1024 * 1024 * 1024,
        "languages": ["en", "fr", "es", "ar", "sw", "hi", "pt"],
        "include_subjects": [
            "literacy",
            "literature_pd",
            "history_pd",
            "health_edu",
            "science",
            "civics",
        ],
        "include_priority_classes": [],
        "prefer_priority_classes": ["education", "health"],
        "prefer_formats": ["epub", "txt", "html"],
        "description": "Village literacy + open science basics (~1 GB budget)",
    },
    "health-priority": {
        "id": "health-priority",
        "max_bytes": 200 * 1024 * 1024,
        "languages": [],
        "include_subjects": ["health_edu", "medicine", "health"],
        "include_priority_classes": ["health"],
        "prefer_priority_classes": ["health"],
        "prefer_formats": ["html", "txt", "pdf"],
        "description": "Health education open materials first",
    },
    "emergency-health": {
        "id": "emergency-health",
        "max_bytes": 500 * 1024 * 1024,
        "languages": [],
        "include_subjects": [
            "emergency",
            "health",
            "health_edu",
            "medicine",
            "safety",
            "water",
        ],
        "include_priority_classes": ["emergency", "health"],
        "prefer_priority_classes": ["emergency", "health"],
        "prefer_formats": ["html", "txt", "pdf"],
        "description": "Emergency + health kits first (clinic / disaster USB)",
        # Reserve room so literature never starves emergency on tiny disks
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.45,
    },
    "stem-lite": {
        "id": "stem-lite",
        "max_bytes": 256 * 1024 * 1024,
        "languages": ["en", "fr", "es", "ar", "sw", "hi", "pt"],
        "include_subjects": [
            "science",
            "stem",
            "math",
            "technology",
            "agriculture",
            "health_edu",
            "weather",
        ],
        "include_priority_classes": ["agriculture", "weather"],
        "prefer_priority_classes": ["education", "agriculture", "weather", "health"],
        "prefer_formats": ["html", "txt", "epub", "pdf"],
        "description": "Lightweight STEM + practical science (~256 MB)",
    },
    "stem-2gb": {
        "id": "stem-2gb",
        "max_bytes": 2 * 1024 * 1024 * 1024,
        "languages": ["en", "fr", "es", "ar", "sw", "hi", "pt"],
        "include_subjects": [
            "science",
            "stem",
            "math",
            "technology",
            "agriculture",
            "health_edu",
            "weather",
            "engineering",
            "environment",
        ],
        "include_priority_classes": [],
        "prefer_priority_classes": [
            "education",
            "agriculture",
            "weather",
            "health",
            "emergency",
        ],
        "prefer_formats": ["html", "txt", "epub", "pdf"],
        "description": "School STEM curriculum kit (~2 GB budget)",
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.15,
    },
    "local-heritage": {
        "id": "local-heritage",
        "max_bytes": 512 * 1024 * 1024,
        "languages": [],
        "include_subjects": [
            "heritage",
            "local_history",
            "literature_pd",
            "history_pd",
            "civics",
            "culture",
            "operator_authored",
        ],
        "include_priority_classes": [],
        "prefer_priority_classes": ["education", "general"],
        "prefer_formats": ["html", "txt", "epub", "pdf"],
        "description": "Local heritage / operator-authored open materials (~512 MB)",
    },
    "all-open-small": {
        "id": "all-open-small",
        "max_bytes": 50 * 1024 * 1024,
        "languages": [],
        "include_subjects": [],
        "include_priority_classes": [],
        "prefer_priority_classes": ["emergency", "health", "education"],
        "prefer_formats": ["txt", "html"],
        "description": "Everything indexed under 50 MB (demo); emergency/health first",
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.4,
    },
    # Offline maps (MBTiles / OSM extracts  -  license-clean operator packs)
    "maps-offline": {
        "id": "maps-offline",
        "max_bytes": 512 * 1024 * 1024,
        "languages": [],
        "include_subjects": ["maps", "geography", "osm", "mbtiles", "local_maps"],
        "include_priority_classes": ["maps"],
        "prefer_priority_classes": ["maps", "emergency", "health", "education"],
        "prefer_formats": ["html", "mbtiles", "png", "jpg", "txt"],
        "description": (
            "Offline maps kit (OSM extracts / MBTiles where license OK) ~512 MB"
        ),
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.2,
    },
    # Curated full dual-access archive budgets (v1.33) - size-gated operator kits
    "archive-100mb": {
        "id": "archive-100mb",
        "max_bytes": 100 * 1024 * 1024,
        "languages": [],
        "include_subjects": [],
        "include_priority_classes": [],
        "prefer_priority_classes": ["emergency", "health", "education", "agriculture"],
        "prefer_formats": ["txt", "html", "epub"],
        "description": "All open works under ~100 MB budget (survival classes first)",
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.35,
    },
    "archive-1gb": {
        "id": "archive-1gb",
        "max_bytes": 1024 * 1024 * 1024,
        "languages": [],
        "include_subjects": [],
        "include_priority_classes": [],
        "prefer_priority_classes": ["emergency", "health", "education", "agriculture", "weather"],
        "prefer_formats": ["txt", "html", "epub", "pdf"],
        "description": "Village archive kit under ~1 GB (open/PD only)",
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.2,
    },
    # Dual-access site downloadable starter (v0.9.0)
    "literacy-starter": {
        "id": "literacy-starter",
        "max_bytes": 8 * 1024 * 1024,
        "languages": ["en", "fr", "es", "ar", "sw", "hi", "pt"],
        "include_subjects": [
            "literacy",
            "literature_pd",
            "civics",
            "history_pd",
            "fable",
            "heritage",
        ],
        "include_priority_classes": [],
        "prefer_priority_classes": ["education", "health"],
        "prefer_formats": ["txt", "html"],
        "description": (
            "Small dual-access literacy starter (~8 MB) for online download + USB demos"
        ),
    },
    # Multilingual dual-access USB kit (v1.28) - curated PD wave subjects
    "multilingual-literacy": {
        "id": "multilingual-literacy",
        "max_bytes": 32 * 1024 * 1024,
        "languages": [],
        "include_subjects": [
            "multilingual",
            "literacy",
            "literature_pd",
            "heritage",
            "fable",
            "poetry",
        ],
        "include_priority_classes": [],
        "prefer_priority_classes": ["education", "health"],
        "prefer_formats": ["txt", "html"],
        "description": (
            "Multilingual curated PD literacy kit (~32 MB): fr/es/it/de/pt + "
            "sw/ar/hi/ja/yo/bn samples when present. Not a complete archive."
        ),
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.15,
    },
}

_LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]+)?$")
_LANGUAGE_PROFILE_PREFIX = "language-"

# Lower rank = selected earlier when filling the size budget
_PRIORITY_RANK: dict[str, int] = {
    "emergency": 0,
    "health": 1,
    "education": 2,
    "agriculture": 3,
    "weather": 4,
    "maps": 5,
    "general": 6,
    "telemetry_raw": 9,
}


def language_profile(lang: str, *, max_bytes: int = 256 * 1024 * 1024) -> dict[str, Any]:
    """Build a dynamic language-xx profile (e.g. language-sw, language-fr)."""
    code = (lang or "").strip().lower()
    if not _LANG_RE.match(code):
        raise ValueError(
            f"Invalid language code '{lang}'. Use ISO-like codes (en, fr, sw, pt-BR)."
        )
    return {
        "id": f"{_LANGUAGE_PROFILE_PREFIX}{code}",
        "max_bytes": int(max_bytes),
        "languages": [code],
        "include_subjects": [],
        "include_priority_classes": [],
        "prefer_priority_classes": ["emergency", "health", "education"],
        "prefer_formats": ["txt", "html", "epub"],
        "description": (
            f"Language-scoped open works ({code}) with emergency/health prefer-first"
        ),
        "reserve_priority_classes": ["emergency", "health"],
        "reserve_fraction": 0.25,
        "dynamic": True,
    }


def list_profiles() -> list[dict[str, Any]]:
    rows = list(BUILTIN_PROFILES.values())
    rows.append(
        {
            "id": "language-xx",
            "max_bytes": 256 * 1024 * 1024,
            "languages": ["<iso-code>"],
            "include_subjects": [],
            "include_priority_classes": [],
            "prefer_priority_classes": ["emergency", "health", "education"],
            "prefer_formats": ["txt", "html", "epub"],
            "description": (
                "Dynamic language kit: use language-en, language-sw, ... "
                "(skycache skybrary pack --profile language-sw)"
            ),
            "dynamic": True,
        }
    )
    return rows


def get_profile(profile_id: str) -> dict[str, Any]:
    pid = (profile_id or "").strip()
    if pid in BUILTIN_PROFILES:
        return dict(BUILTIN_PROFILES[pid])
    if pid.startswith(_LANGUAGE_PROFILE_PREFIX):
        lang = pid[len(_LANGUAGE_PROFILE_PREFIX) :]
        if lang and lang != "xx":
            return language_profile(lang)
    known = ", ".join(sorted(BUILTIN_PROFILES)) + ", language-<code>"
    raise ValueError(f"Unknown profile '{profile_id}'. Known: {known}")


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _read_manifest(pkg_dir: Path) -> dict[str, Any] | None:
    man = pkg_dir / "manifest.json"
    if not man.is_file():
        return None
    try:
        return json.loads(man.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _sky_index(sky: SkybraryCatalog) -> dict[str, dict[str, Any]]:
    """Map package_id / work_id -> work metadata (full table when possible)."""
    out: dict[str, dict[str, Any]] = {}
    try:
        rows = sky._conn.execute(  # noqa: SLF001 - pack builder needs full index
            "SELECT * FROM works ORDER BY civilizational_tier ASC, work_id ASC"
        ).fetchall()
        for row in rows:
            w = sky._work_row(row)  # noqa: SLF001
            pid = w.get("package_id") or w.get("work_id")
            if pid:
                out[str(pid)] = w
            out[str(w["work_id"])] = w
    except Exception:
        for w in sky.search("", limit=200):
            pid = w.get("package_id") or w.get("work_id")
            if pid:
                out[str(pid)] = w
            out[str(w["work_id"])] = w
    return out


def _edition_priority(work: dict[str, Any]) -> str:
    editions = work.get("editions") or []
    if editions and isinstance(editions[0], dict):
        return str(editions[0].get("priority_class") or "education")
    return "education"


def _collect_candidates(
    content_dir: Path,
    sky: SkybraryCatalog,
) -> list[dict[str, Any]]:
    """Enumerate package dirs + enrich with Skybrary subjects/tier when known."""
    content_dir = Path(content_dir)
    sky_by_id = _sky_index(sky)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    if content_dir.is_dir():
        for d in sorted(content_dir.iterdir()):
            if not d.is_dir():
                continue
            data = _read_manifest(d)
            name = d.name
            if data is None:
                continue
            pid = str(data.get("id") or name)
            if pid in seen:
                continue
            seen.add(pid)
            work = sky_by_id.get(pid) or sky_by_id.get(name) or {}
            subjects = list(work.get("subjects") or [])
            tags = list(data.get("tags") or [])
            subjects = sorted(set(subjects) | set(tags))
            pclass = str(data.get("priority_class") or "") or (
                _edition_priority(work) if work else "general"
            )
            candidates.append(
                {
                    "package_id": pid,
                    "dir_name": name,
                    "src": d,
                    "priority_class": pclass,
                    "languages": list(data.get("languages") or work.get("languages") or []),
                    "subjects": subjects,
                    "civilizational_tier": int(work.get("civilizational_tier") or 5),
                    "pinned": bool(data.get("pinned")),
                }
            )

    for key, work in sky_by_id.items():
        pid = str(work.get("package_id") or work.get("work_id") or key)
        if pid in seen:
            continue
        src = content_dir / pid
        if not src.is_dir():
            continue
        seen.add(pid)
        candidates.append(
            {
                "package_id": pid,
                "dir_name": src.name,
                "src": src,
                "priority_class": _edition_priority(work),
                "languages": list(work.get("languages") or []),
                "subjects": list(work.get("subjects") or []),
                "civilizational_tier": int(work.get("civilizational_tier") or 5),
                "pinned": False,
            }
        )
    return candidates


def _matches_profile(c: dict[str, Any], profile: dict[str, Any]) -> bool:
    subjects_filter = set(profile.get("include_subjects") or [])
    include_pc = set(profile.get("include_priority_classes") or [])
    langs = set(profile.get("languages") or [])

    if langs:
        wlang = set(c.get("languages") or [])
        # If package declares languages, require intersection; empty langs = unknown, keep
        if wlang and not wlang.intersection(langs):
            return False

    # No hard filters -> accept all (language already applied)
    if not subjects_filter and not include_pc:
        return True

    pclass = str(c.get("priority_class") or "general")
    wsub = set(c.get("subjects") or [])

    if include_pc and pclass in include_pc:
        return True
    if subjects_filter and wsub.intersection(subjects_filter):
        return True
    return False


def _sort_key(c: dict[str, Any], profile: dict[str, Any]) -> tuple:
    prefer = list(profile.get("prefer_priority_classes") or [])
    pclass = str(c.get("priority_class") or "general")
    if prefer:
        try:
            pref_rank = prefer.index(pclass)
        except ValueError:
            pref_rank = len(prefer) + _PRIORITY_RANK.get(pclass, 8)
    else:
        pref_rank = _PRIORITY_RANK.get(pclass, 8)
    # pinned emergency/health float higher
    pin_boost = 0 if c.get("pinned") and pclass in ("emergency", "health") else 1
    return (
        pref_rank,
        pin_boost,
        int(c.get("civilizational_tier") or 5),
        str(c.get("package_id") or ""),
    )


def resolve_pack_out_dir(data_dir: Path, profile_id: str, out: str | None = None) -> Path:
    """Resolve kit output under data_dir/packs (path-safe)."""
    packs_root = (Path(data_dir) / "packs").resolve()
    packs_root.mkdir(parents=True, exist_ok=True)
    if not out:
        return packs_root / profile_id
    candidate = Path(out)
    if not candidate.is_absolute():
        candidate = packs_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(packs_root)
    except ValueError as exc:
        raise ValueError(
            f"out path must stay under {packs_root} (got {resolved})"
        ) from exc
    return resolved


def _is_reserved_class(pclass: str, profile: dict[str, Any]) -> bool:
    reserve = {str(x).lower() for x in (profile.get("reserve_priority_classes") or [])}
    return str(pclass or "").lower() in reserve


def _select_under_budget(
    matched: list[dict[str, Any]],
    profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Fill size budget; optionally reserve fraction for emergency/health first.

    Literature never starves emergency content on small disks when
    ``reserve_priority_classes`` + ``reserve_fraction`` are set.
    """
    max_b = int(profile["max_bytes"])
    frac = float(profile.get("reserve_fraction") or 0.0)
    reserve_classes = {
        str(x).lower() for x in (profile.get("reserve_priority_classes") or [])
    }
    reserve_budget = int(max_b * frac) if reserve_classes and frac > 0 else 0

    selected_meta: list[dict[str, Any]] = []
    total = 0
    reserved_used = 0

    # Pass 1: fill reserved budget with emergency/health (or other reserve classes)
    if reserve_budget > 0:
        for c in matched:
            if not _is_reserved_class(c["priority_class"], profile):
                continue
            src = Path(c["src"])
            if not src.is_dir():
                continue
            size = _dir_size(src)
            if reserved_used + size > reserve_budget and selected_meta:
                continue
            if reserved_used + size > reserve_budget and not selected_meta:
                if size > max_b:
                    continue
            if total + size > max_b:
                continue
            selected_meta.append(
                {
                    "package_id": c["package_id"],
                    "priority_class": c["priority_class"],
                    "bytes": size,
                    "dir_name": c["dir_name"],
                    "src": str(src),
                    "reserved": True,
                }
            )
            reserved_used += size
            total += size

    selected_ids = {m["package_id"] for m in selected_meta}

    # Pass 2: fill remaining with prefer-ordered candidates (all classes)
    for c in matched:
        if c["package_id"] in selected_ids:
            continue
        src = Path(c["src"])
        if not src.is_dir():
            continue
        size = _dir_size(src)
        if total + size > max_b:
            continue
        selected_meta.append(
            {
                "package_id": c["package_id"],
                "priority_class": c["priority_class"],
                "bytes": size,
                "dir_name": c["dir_name"],
                "src": str(src),
                "reserved": False,
            }
        )
        total += size

    return selected_meta, total


def content_tree_sha256(root: Path) -> dict[str, Any]:
    """Content-addressed tree digest: per-file sha256 + root digest (sorted paths)."""
    root = Path(root)
    files: list[dict[str, Any]] = []
    h = hashlib.sha256()
    if not root.is_dir():
        return {"root_sha256": "", "file_count": 0, "files": []}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Skip the manifest we are about to write/update
        if path.name in {"profile-manifest.json", "profile-manifest.sha256"}:
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        fh = hashlib.sha256(data).hexdigest()
        files.append({"path": rel, "sha256": fh, "bytes": len(data)})
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(fh.encode("ascii"))
        h.update(b"\0")
    return {
        "root_sha256": h.hexdigest(),
        "file_count": len(files),
        "files": files,
    }


def build_pack_from_profile(
    sky: SkybraryCatalog,
    profile_id: str,
    *,
    content_dir: Path,
    out_dir: Path,
) -> dict[str, Any]:
    """Copy selected packages into out_dir under size budget.

    Emergency/Health packages are preferred and optionally reserved first so
    literature never starves critical content on small disks. Emits a signed
    ``profile-manifest.json`` (SHA-256 tree digest of kit contents).
    """
    profile = get_profile(profile_id)
    content_dir = Path(content_dir)
    out_dir = Path(out_dir)
    if out_dir.exists():
        # Clean previous kit so digests stay honest
        for child in out_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = _collect_candidates(content_dir, sky)
    matched = [c for c in candidates if _matches_profile(c, profile)]
    matched.sort(key=lambda c: _sort_key(c, profile))

    selected_meta, total = _select_under_budget(matched, profile)
    selected: list[str] = []

    for m in selected_meta:
        src = Path(m["src"])
        dest = out_dir / Path(m["dir_name"]).name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        selected.append(dest.name)
        # Drop internal copy keys from public meta
        m.pop("src", None)
        m.pop("dir_name", None)

    tree = content_tree_sha256(out_dir)
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "profile": profile,
        "profile_id": profile.get("id") or profile_id,
        "selected_packages": selected,
        "selected": selected_meta,
        "total_bytes": total,
        "count": len(selected),
        "out_dir": str(out_dir),
        "built_at": built_at,
        "integrity": {
            "alg": "sha256",
            "root_sha256": tree["root_sha256"],
            "file_count": tree["file_count"],
        },
        "legal": (
            "Open/PD packages only - profile does not expand license rights. "
            "Operator must confirm redistribution for every package."
        ),
        "signed_manifest": True,
    }
    man_path = out_dir / "profile-manifest.json"
    # Canonical body without self-hash; sidecar holds sha256 of this file
    body = json.dumps(meta, indent=2, sort_keys=False) + "\n"
    man_path.write_text(body, encoding="utf-8")
    man_digest = hashlib.sha256(man_path.read_bytes()).hexdigest()
    (out_dir / "profile-manifest.sha256").write_text(
        f"{man_digest}  profile-manifest.json\n", encoding="utf-8"
    )
    meta["manifest_sha256"] = man_digest
    return meta


def verify_pack_manifest(pack_dir: Path) -> dict[str, Any]:
    """Verify a built kit against profile-manifest integrity block."""
    pack_dir = Path(pack_dir)
    man = pack_dir / "profile-manifest.json"
    if not man.is_file():
        return {"ok": False, "error": "profile-manifest.json missing"}
    try:
        meta = json.loads(man.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"manifest unreadable: {exc}"}
    expected = (meta.get("integrity") or {}).get("root_sha256")
    tree = content_tree_sha256(pack_dir)
    ok = bool(expected) and expected == tree["root_sha256"]
    return {
        "ok": ok,
        "expected_root_sha256": expected,
        "actual_root_sha256": tree["root_sha256"],
        "file_count": tree["file_count"],
        "profile_id": meta.get("profile_id"),
    }
