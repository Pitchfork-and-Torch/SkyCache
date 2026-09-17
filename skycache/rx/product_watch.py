"""Watch SatDump (or any) product directories and ingest weather packages.

This is the primary real-world loop: operator runs SatDump for the pass,
products land on disk, SkyCache watches and publishes to the portal.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.pipelines.runner import PipelineRunner

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
STATE_NAME = "watch-state.json"


def _state_path(data_dir: Path) -> Path:
    return Path(data_dir) / "rx" / STATE_NAME


def load_state(data_dir: Path) -> dict[str, Any]:
    p = _state_path(data_dir)
    if not p.is_file():
        return {"seen": {}, "ingested": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            return {"seen": {}, "ingested": []}
        data.setdefault("seen", {})
        data.setdefault("ingested", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {"seen": {}, "ingested": []}


def save_state(data_dir: Path, state: dict[str, Any]) -> None:
    p = _state_path(data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _file_key(path: Path) -> str:
    st = path.stat()
    raw = f"{path.resolve()}|{st.st_size}|{int(st.st_mtime)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def discover_products(watch_dir: Path) -> list[Path]:
    """Find image products and package dirs under a SatDump output tree."""
    watch_dir = Path(watch_dir)
    if not watch_dir.is_dir():
        return []
    found: list[Path] = []
    packaged_roots: set[Path] = set()
    # Prefer complete package dirs (manifest.json)
    for child in sorted(watch_dir.rglob("manifest.json")):
        root = child.parent.resolve()
        found.append(root)
        packaged_roots.add(root)
    # Loose images not under a package dir we already picked
    for img in sorted(watch_dir.rglob("*")):
        if not img.is_file() or img.suffix.lower() not in IMAGE_EXT:
            continue
        resolved = img.resolve()
        if any(root == resolved.parent or root in resolved.parents for root in packaged_roots):
            continue
        found.append(resolved)
    # de-dupe preserving order
    out: list[Path] = []
    seen: set[str] = set()
    for p in found:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def ingest_product(
    path: Path,
    settings: Settings,
    *,
    recipe: str = "product_import",
    satellite: str = "",
) -> dict[str, Any]:
    """Ingest one image file or package directory into the catalog."""
    path = Path(path)
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    runner = PipelineRunner(settings, content)

    if path.is_dir() and (path / "manifest.json").is_file():
        pkg = content.ingest_package_dir(path)
        catalog.close()
        return {
            "ok": True,
            "mode": "package_dir",
            "package_id": pkg.id,
            "path": str(path),
            "recipe": recipe,
            "satellite": satellite,
        }

    if path.is_file() and path.suffix.lower() in IMAGE_EXT:
        source = SourceSpec(
            plugin="satdump_weather",
            uri=str(path),
            options={
                "pipeline": recipe or "import",
                "kind": "weather",
                "satellite": satellite,
            },
        )
        result = runner.run(source)
        catalog.close()
        pkg_id = None
        if result.suggested_package:
            pkg_id = result.suggested_package.id
        elif result.artifacts:
            # manifest path
            try:
                mpath = Path(result.artifacts[0])
                if mpath.is_file():
                    data = json.loads(mpath.read_text(encoding="utf-8-sig"))
                    pkg_id = data.get("id")
            except (OSError, json.JSONDecodeError):
                pkg_id = None
        return {
            "ok": bool(result.success),
            "mode": "image_file",
            "package_id": pkg_id,
            "path": str(path),
            "message": result.message,
            "recipe": recipe,
            "satellite": satellite,
        }

    catalog.close()
    return {"ok": False, "error": f"unsupported product path: {path}", "path": str(path)}


def watch_once(
    watch_dir: Path,
    settings: Settings,
    *,
    recipe: str = "product_import",
    satellite: str = "",
    max_new: int = 20,
) -> dict[str, Any]:
    """Scan watch_dir once; ingest new products not in state."""
    watch_dir = Path(watch_dir)
    state = load_state(settings.data_dir)
    seen: dict[str, Any] = dict(state.get("seen") or {})
    products = discover_products(watch_dir)
    results: list[dict[str, Any]] = []
    for path in products:
        if len(results) >= max_new:
            break
        key = _file_key(path)
        if key in seen:
            continue
        # skip empty / clearly incomplete files (1x1 PNG demos are ~70B+)
        try:
            if path.is_file() and path.stat().st_size < 32:
                continue
            if path.is_dir():
                # require at least one image beside manifest
                imgs = [
                    p
                    for p in path.iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_EXT
                ]
                if not imgs and not (path / "manifest.json").is_file():
                    continue
        except OSError:
            continue
        rep = ingest_product(path, settings, recipe=recipe, satellite=satellite)
        # Pass Autopilot: when station is armed, append field-log on successful ingest
        if rep.get("ok") and rep.get("package_id"):
            try:
                from skycache.rx.schedule import maybe_auto_field_log

                fl = maybe_auto_field_log(
                    settings.data_dir,
                    package_id=str(rep.get("package_id") or ""),
                    satellite=satellite or str(rep.get("satellite") or ""),
                    recipe=recipe,
                    quality="auto",
                )
                if fl:
                    rep["field_log_id"] = fl.get("id")
                    rep["field_log_auto"] = True
            except Exception:  # noqa: BLE001 - never fail watch on log
                pass
        seen[key] = {
            "path": str(path),
            "at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "ok": rep.get("ok"),
            "package_id": rep.get("package_id"),
            "field_log_id": rep.get("field_log_id"),
        }
        if rep.get("ok") and rep.get("package_id"):
            ing = list(state.get("ingested") or [])
            ing.append(rep["package_id"])
            state["ingested"] = ing[-200:]
        results.append(rep)
    state["seen"] = seen
    state["last_scan"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    state["watch_dir"] = str(watch_dir.resolve())
    save_state(settings.data_dir, state)
    return {
        "schema": "skycache.rx.watch.v1",
        "watch_dir": str(watch_dir),
        "candidates": len(products),
        "new": len(results),
        "results": results,
        "legal": "FTA weather product ingest only",
    }


def watch_loop(
    watch_dir: Path,
    settings: Settings,
    *,
    interval_sec: float = 30.0,
    recipe: str = "product_import",
    satellite: str = "",
    max_iterations: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Poll watch_dir until max_iterations (None = forever for service use)."""
    i = 0
    totals = {"scans": 0, "new": 0, "packages": []}
    while True:
        rep = watch_once(
            watch_dir, settings, recipe=recipe, satellite=satellite
        )
        totals["scans"] += 1
        totals["new"] += int(rep.get("new") or 0)
        for r in rep.get("results") or []:
            if r.get("package_id"):
                totals["packages"].append(r["package_id"])
        i += 1
        if max_iterations is not None and i >= max_iterations:
            break
        sleep_fn(float(interval_sec))
    return totals
