"""Gateway Ops (v1.8.0): doctor, preset pull + passport, receipts, ethics kit.

Opportunistic legal uplink only. Open-content allowlist. Fair-share quota.
Never commercial decrypt. Not free broadband or automatic mesh-to-internet bridge.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__
from skycache.capabilities.open_fetch import (
    DEFAULT_OPEN_HOST_SUFFIXES,
    fetch_open_url,
    load_extra_hosts,
    validate_open_url,
)
from skycache.community.passport import redistribute_posture
from skycache.nexus.dtn import DtnQueue
from skycache.nexus.gateway import GatewayManager
from skycache.nexus.gateway_presets import (
    PullReceiptLog,
    get_preset,
    list_presets,
)
from skycache.nexus.identity import load_or_create_node_id

HONEST = (
    "Gateway: opportunistic legal uplink only. Open-content allowlist + fair-share quota. "
    "Never commercial decrypt. Not free Starlink or automatic public internet bridging."
)

DOCTOR_SCHEMA = "skycache.gateway.doctor.v1"
PULL_SCHEMA = "skycache.gateway.pull.v1"
KIT_SCHEMA = "skycache.gateway.ethics_kit.v1"
PASSPORT_SCHEMA = "skycache.gateway.pull_passport.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _settings(data_dir: Path | None):
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    return settings


def _gw(settings, *, sim: bool = False) -> GatewayManager:
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    gw = GatewayManager(
        dtn=dtn,
        node_id=node_id,
        sim_uplink=sim,
        receipt_log_path=settings.nexus_dir / "gateway-receipts.json",
    )
    gw.status.daily_quota_bytes = int(settings.gateway_daily_quota_mb) * 1024 * 1024
    return gw


def gateway_doctor(*, data_dir: Path | None = None, sim: bool = False) -> dict[str, Any]:
    """Non-destructive readiness for ethical gateway pulls."""
    settings = _settings(data_dir)
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    presets = list_presets()
    add("presets", len(presets) >= 1, f"{len(presets)} open-mirror presets", 15)

    allow_n = len(DEFAULT_OPEN_HOST_SUFFIXES)
    extra = (
        load_extra_hosts(Path(settings.open_fetch_hosts_file))
        if settings.open_fetch_hosts_file
        else []
    )
    add(
        "open_fetch_allowlist",
        allow_n >= 5,
        f"{allow_n} default hosts + {len(extra)} operator extra",
        15,
    )

    # Validate each preset URL when present
    bad = 0
    for p in presets:
        url = (p.get("example_url") or "").strip()
        if not url:
            continue
        try:
            validate_open_url(url, extra)
        except ValueError:
            bad += 1
    add(
        "preset_urls_legal",
        bad == 0,
        "all preset example URLs pass open-fetch gate" if bad == 0 else f"{bad} preset URL(s) fail gate",
        12,
    )

    quota_mb = int(settings.gateway_daily_quota_mb)
    add("daily_quota", quota_mb > 0, f"{quota_mb} MB daily fair-share quota", 10)

    receipts_path = settings.nexus_dir / "gateway-receipts.json"
    add(
        "receipts_path",
        True,
        str(receipts_path) + (" (exists)" if receipts_path.is_file() else " (will create on pull)"),
        8,
    )

    mode = getattr(settings, "legal_rf_mode", "") or ""
    add(
        "legal_mode_aware",
        True,
        f"legal_rf_mode={mode or 'unset'} (gateway is client uplink, not mesh TX)",
        5,
    )

    gw = _gw(settings, sim=sim)
    snap = gw.snapshot()
    add(
        "detect_path",
        True,
        f"uplink present={snap.get('present')} kind={snap.get('kind')}",
        8,
    )

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_sim = score >= 70 and bad == 0
    go_live = go_sim and bool(snap.get("present")) and not sim

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_sim_gateway": go_sim,
        "go_live_gateway": go_live,
        "preset_count": len(presets),
        "daily_quota_mb": quota_mb,
        "uplink": {
            "present": snap.get("present"),
            "kind": snap.get("kind"),
            "remaining_quota_mb": snap.get("remaining_quota_mb"),
        },
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache gateway doctor",
            "skycache gateway presets",
            "skycache gateway pull-preset gutenberg-sample --dry-run",
            "skycache gateway pull-preset gutenberg-sample --sim",
            "skycache gateway receipts",
            "skycache gateway ethics-kit --out data/gateway-ethics-kit",
        ],
        "legal": (
            "Pull open/FTA/licensed content only. Operator verifies each work license. "
            "Quota is social fair-share, not a product entitlement."
        ),
    }


def gateway_status(*, data_dir: Path | None = None, sim: bool = False) -> dict[str, Any]:
    settings = _settings(data_dir)
    gw = _gw(settings, sim=sim)
    snap = gw.snapshot()
    return {
        "schema": "skycache.gateway.status.v1",
        "generated_at": _iso_now(),
        "software_version": __version__,
        "banner": HONEST,
        **snap,
    }


def gateway_receipts(*, data_dir: Path | None = None, limit: int = 50) -> dict[str, Any]:
    settings = _settings(data_dir)
    path = settings.nexus_dir / "gateway-receipts.json"
    log = PullReceiptLog(path)
    return {
        "schema": "skycache.gateway.receipts.v1",
        "generated_at": _iso_now(),
        "software_version": __version__,
        "summary": log.summary(),
        "recent": log.list_recent(limit=limit),
        "banner": HONEST,
    }


def pull_preset(
    preset_id: str,
    *,
    data_dir: Path | None = None,
    dry_run: bool = False,
    sim: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """One-shot: preset -> open-fetch (or sim) + license passport stub + receipt.

    dry_run: validate URL and write passport plan only (no download).
    sim: write local sample bytes without network (for labs offline).
    live (neither): real allowlisted HTTPS fetch when quota allows.
    """
    settings = _settings(data_dir)
    try:
        preset = get_preset(preset_id)
    except ValueError as exc:
        return {"schema": PULL_SCHEMA, "ok": False, "error": str(exc), "banner": HONEST}

    url = (preset.get("example_url") or "").strip()
    license_hint = str(preset.get("license_hint") or "unknown")
    # Strip parentheticals so "public-domain (varies by work)" does not look like CC-BY
    license_for_posture = license_hint.split("(")[0].strip() or license_hint
    posture = redistribute_posture(license_for_posture)
    extra = (
        load_extra_hosts(Path(settings.open_fetch_hosts_file))
        if settings.open_fetch_hosts_file
        else []
    )

    if not url:
        return {
            "schema": PULL_SCHEMA,
            "ok": False,
            "preset_id": preset_id,
            "error": "Preset has no example_url (operator-curated only - supply materials yourself)",
            "preset": preset,
            "passport": {
                "schema": PASSPORT_SCHEMA,
                "preset_id": preset_id,
                "license_hint": license_hint,
                **posture,
            },
            "banner": HONEST,
        }

    try:
        validate_open_url(url, extra)
    except ValueError as exc:
        return {
            "schema": PULL_SCHEMA,
            "ok": False,
            "preset_id": preset_id,
            "url": url,
            "error": str(exc),
            "banner": HONEST,
        }

    gw = _gw(settings, sim=sim or dry_run)
    remaining = gw.remaining_quota()
    if remaining <= 0 and not dry_run and not force:
        return {
            "schema": PULL_SCHEMA,
            "ok": False,
            "preset_id": preset_id,
            "error": "Daily fair-share quota exhausted",
            "remaining_quota": remaining,
            "banner": HONEST,
        }

    pulls_dir = settings.nexus_dir / "gateway-pulls" / preset_id
    pulls_dir.mkdir(parents=True, exist_ok=True)
    dest = pulls_dir / "payload.bin"
    passport_path = pulls_dir / "pull-passport.json"

    bytes_n = 0
    mode = "dry_run" if dry_run else ("sim" if sim else "live")
    fetch_meta: dict[str, Any] = {}

    if dry_run:
        fetch_meta = {"url": url, "path": None, "bytes": 0, "mode": "dry_run"}
    elif sim:
        sample = (
            f"SkyCache gateway sim pull\npreset={preset_id}\nurl={url}\n"
            f"license_hint={license_hint}\n{HONEST}\n"
        ).encode("utf-8")
        dest.write_bytes(sample)
        bytes_n = len(sample)
        fetch_meta = {
            "url": url,
            "path": str(dest),
            "bytes": bytes_n,
            "mode": "sim",
            "content_type": "text/plain",
        }
    else:
        try:
            fetch_meta = fetch_open_url(url, dest, extra_hosts=extra)
            bytes_n = int(fetch_meta.get("bytes") or 0)
            fetch_meta["mode"] = "live"
        except Exception as exc:  # noqa: BLE001
            return {
                "schema": PULL_SCHEMA,
                "ok": False,
                "preset_id": preset_id,
                "url": url,
                "error": str(exc),
                "banner": HONEST,
            }

    if bytes_n and not dry_run:
        gw.status.daily_bytes_used += bytes_n

    passport = {
        "schema": PASSPORT_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "preset_id": preset_id,
        "preset_label": preset.get("label"),
        "url": url,
        "license_hint": license_hint,
        "priority_class": preset.get("priority_class"),
        "mode": mode,
        "bytes": bytes_n,
        "path": str(dest) if dest.is_file() else None,
        **posture,
        "operator_must": (
            "Verify license of the actual work before village redistribution. "
            "Passport is a gate stub, not legal advice."
        ),
        "banner": HONEST,
    }
    passport_path.write_text(json.dumps(passport, indent=2) + "\n", encoding="utf-8")

    receipt = {
        "ok": True,
        "bytes": bytes_n,
        "priority_class": preset.get("priority_class") or "education",
        "package_id": None,
        "preset": preset_id,
        "url": url,
        "mode": mode,
        "passport": str(passport_path),
    }
    if not dry_run:
        gw._record_receipt(receipt)  # noqa: SLF001 - intentional shared receipt path

    return {
        "schema": PULL_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "preset_id": preset_id,
        "mode": mode,
        "fetch": fetch_meta,
        "passport": passport,
        "passport_path": str(passport_path),
        "receipt": receipt,
        "remaining_quota_mb": round(gw.remaining_quota() / (1024 * 1024), 1),
        "banner": HONEST,
    }


def write_ethics_kit(
    out_dir: Path,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Operator kit: ethics README, presets dump, doctor snapshot, zip."""
    settings = _settings(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = gateway_doctor(data_dir=settings.data_dir, sim=True)
    (out_dir / "gateway-doctor.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "presets.json").write_text(
        json.dumps({"presets": list_presets(), "legal": HONEST}, indent=2) + "\n",
        encoding="utf-8",
    )

    ethics = f"""# SkyCache Gateway Ethics

{HONEST}

## Rules

1. **Open content only** - allowlisted hosts; never commercial constellation decrypt.
2. **Fair-share quota** - default daily cap protects shared metered links (see gateway-daily-quota).
3. **License passport** - every preset pull writes pull-passport.json; operator verifies before redistribute.
4. **No automatic mesh bridge** - gateway is a *client* uplink for curated pulls, not a village NAT to the public internet.
5. **Receipts stay local** - gateway-receipts.json is an operator audit trail, not cloud telemetry.

## Commands

```text
skycache gateway doctor
skycache gateway presets
skycache gateway pull-preset gutenberg-sample --dry-run
skycache gateway pull-preset gutenberg-sample --sim
skycache gateway pull-preset gutenberg-sample
skycache gateway receipts
skycache gateway ethics-kit --out data/gateway-ethics-kit
```

## Presets

See presets.json. Empty example_url means operator-curated materials only (e.g. WHO/MoH packs).

Software v{__version__}
"""
    (out_dir / "ETHICS.md").write_text(ethics, encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# Gateway ethics kit\n\n{HONEST}\n\nSee ETHICS.md and gateway-doctor.json.\n",
        encoding="utf-8",
    )
    (out_dir / "HOSTING.json").write_text(
        json.dumps(
            {
                "schema": KIT_SCHEMA,
                "generated_at": _iso_now(),
                "software_version": __version__,
                "banner": HONEST,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    zip_path = out_dir.parent / f"{out_dir.name}.zip"
    if zip_path.is_file():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out_dir.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=f"{out_dir.name}/{f.relative_to(out_dir).as_posix()}")

    return {
        "schema": KIT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "out_dir": str(out_dir),
        "zip": str(zip_path),
        "files": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
        "banner": HONEST,
    }
