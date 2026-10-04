"""Scheduled bit-rot / integrity verification (Wave 3.B5).

Local-only: writes last report under data/ops/. No cloud, no PII.
Install tips: systemd timer or cron weekly on the village node.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache.capabilities.integrity_tree import verify_content_tree

REPORT_NAME = "bitrot-last.json"
SCHEDULE_HINT = "weekly"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class BitrotReport:
    ok: bool
    checked_at: str
    content_dir: str
    package_count: int
    failed_count: int
    schedule_hint: str = SCHEDULE_HINT
    legal: str = "Integrity of open packages only - not DRM or commercial media"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checked_at": self.checked_at,
            "content_dir": self.content_dir,
            "package_count": self.package_count,
            "failed_count": self.failed_count,
            "schedule_hint": self.schedule_hint,
            "legal": self.legal,
        }


def ops_dir(data_dir: Path) -> Path:
    d = Path(data_dir) / "ops"
    d.mkdir(parents=True, exist_ok=True)
    return d


def report_path(data_dir: Path) -> Path:
    return ops_dir(data_dir) / REPORT_NAME


def run_bitrot_verify(content_dir: Path, data_dir: Path) -> dict[str, Any]:
    """Run integrity tree check and persist last report under data/ops/."""
    content_dir = Path(content_dir)
    raw = verify_content_tree(content_dir)
    packages = list(raw.get("packages") or [])
    failed = [p for p in packages if not p.get("ok")]
    report = BitrotReport(
        ok=bool(raw.get("ok")),
        checked_at=_utc_now(),
        content_dir=str(content_dir),
        package_count=int(raw.get("count") or len(packages)),
        failed_count=len(failed),
    )
    payload = report.to_dict()
    payload["tree"] = {
        "ok": raw.get("ok"),
        "count": raw.get("count"),
        "failed_ids": [
            p.get("package_id") or p.get("path") for p in failed[:100]
        ],
    }
    path = report_path(data_dir)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def load_last_report(data_dir: Path) -> dict[str, Any] | None:
    path = report_path(data_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def schedule_status(data_dir: Path, *, max_age_days: float = 10.0) -> dict[str, Any]:
    """Whether a recent bit-rot verify has been recorded (operator schedule health)."""
    last = load_last_report(data_dir)
    if not last:
        return {
            "scheduled": False,
            "fresh": False,
            "max_age_days": max_age_days,
            "hint": (
                "Install deploy/bitrot-verify.timer or weekly cron: "
                "skycache skybrary doctor --verify --record"
            ),
            "last": None,
        }
    checked = str(last.get("checked_at") or "")
    age_days: float | None = None
    try:
        # Accept ...Z
        ts = checked.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400.0
    except ValueError:
        age_days = None
    fresh = age_days is not None and age_days <= max_age_days
    return {
        "scheduled": True,
        "fresh": fresh,
        "age_days": round(age_days, 3) if age_days is not None else None,
        "max_age_days": max_age_days,
        "last_ok": bool(last.get("ok")),
        "last": {
            "checked_at": checked,
            "package_count": last.get("package_count"),
            "failed_count": last.get("failed_count"),
            "ok": last.get("ok"),
        },
        "hint": "OK" if fresh and last.get("ok") else "Re-run skycache skybrary doctor --verify --record",
    }


def systemd_unit_text(*, data_dir: str = "/var/lib/skycache") -> str:
    """Example systemd service body (operator copies under /etc/systemd/system/)."""
    return f"""[Unit]
Description=SkyCache Skybrary bit-rot integrity verify (open packs only)
After=network-online.target

[Service]
Type=oneshot
# Village node: run as the service user that owns the data dir
ExecStart=/usr/bin/env skycache skybrary doctor --data-dir {data_dir} --verify --record
Nice=10
IOSchedulingClass=idle

[Install]
WantedBy=multi-user.target
"""


def systemd_timer_text() -> str:
    return """[Unit]
Description=Weekly SkyCache bit-rot verify timer

[Timer]
OnCalendar=Sun *-*-* 03:15:00
Persistent=true
RandomizedDelaySec=45m

[Install]
WantedBy=timers.target
"""


def cron_line(*, data_dir: str = "/var/lib/skycache") -> str:
    return (
        f"15 3 * * 0 root skycache skybrary doctor --data-dir {data_dir} "
        f"--verify --record >>/var/log/skycache-bitrot.log 2>&1"
    )


def write_schedule_templates(out_dir: Path, *, data_dir: str = "/var/lib/skycache") -> dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    service = out_dir / "skycache-bitrot-verify.service"
    timer = out_dir / "skycache-bitrot-verify.timer"
    cron = out_dir / "skycache-bitrot.cron"
    service.write_text(systemd_unit_text(data_dir=data_dir), encoding="utf-8")
    timer.write_text(systemd_timer_text(), encoding="utf-8")
    cron.write_text("# /etc/cron.d/skycache-bitrot\n" + cron_line(data_dir=data_dir) + "\n", encoding="utf-8")
    readme = out_dir / "README.txt"
    readme.write_text(
        "SkyCache bit-rot schedule templates (local only).\n"
        "1. Copy .service + .timer to /etc/systemd/system/\n"
        "2. systemctl daemon-reload && systemctl enable --now skycache-bitrot-verify.timer\n"
        "Or install the cron line under /etc/cron.d/\n"
        "Legal: open packages only. Not commercial media integrity.\n",
        encoding="utf-8",
    )
    return {
        "service": str(service),
        "timer": str(timer),
        "cron": str(cron),
        "readme": str(readme),
        "written_at": _utc_now(),
        "monotonic": time.time(),
    }
