"""Opportunistic legal gateway manager.

Detects any *legal* upstream (USB modem, Wi-Fi client, Ethernet, shared hotspot)
and schedules fair-share pulls of open content. Never auto-bridges the mesh to
the public internet without operator policy. Never commercial decrypt.
"""

from __future__ import annotations

import logging
import shutil
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from skycache.models import PriorityClass
from skycache.nexus.dtn import BundleKind, DtnQueue
from skycache.nexus.spectrum import validate_mesh_mode

log = logging.getLogger("skycache.nexus.gateway")


@dataclass
class GatewayStatus:
    present: bool = False
    kind: str = "none"  # none | ethernet | wifi_client | usb_modem | sim | unknown
    address: str | None = None
    uplink_mbps: float | None = None
    daily_bytes_used: int = 0
    daily_quota_bytes: int = 500 * 1024 * 1024  # 500 MB default ethical share
    last_check: float = 0.0
    note: str = ""


@dataclass
class GatewayManager:
    dtn: DtnQueue
    node_id: str
    status: GatewayStatus = field(default_factory=GatewayStatus)
    sim_uplink: bool = False
    # Optional pull hook: (priority_class, request_payload) -> bytes_downloaded
    pull_handler: Callable[[str, dict[str, Any]], int] | None = None
    # Optional local receipt log path (data/nexus/gateway-receipts.json)
    receipt_log_path: Path | None = None

    def detect(self) -> GatewayStatus:
        """Probe for any legal upstream. Sim mode can force presence."""
        validate_mesh_mode("gateway-detect")
        self.status.last_check = time.time()
        if self.sim_uplink:
            self.status.present = True
            self.status.kind = "sim"
            self.status.note = "Simulated opportunistic uplink (legal open content only)"
            return self.status

        # Lightweight heuristics - no privileged netlink required
        if self._has_default_route():
            self.status.present = True
            self.status.kind = "unknown"
            self.status.note = (
                "Default route detected. Operator must ensure upstream is authorized "
                "and only open content is pulled."
            )
        else:
            self.status.present = False
            self.status.kind = "none"
            self.status.note = "No upstream detected"
        return self.status

    def _has_default_route(self) -> bool:
        # Prefer `ip route` if available
        ip = shutil.which("ip")
        if ip:
            try:
                import subprocess

                r = subprocess.run(
                    [ip, "route", "show", "default"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                return bool(r.stdout.strip())
            except (OSError, subprocess.TimeoutExpired):
                pass
        # Fallback: try DNS-less TCP to a public DNS (may fail offline - OK)
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
            return True
        except OSError:
            return False

    def remaining_quota(self) -> int:
        return max(0, self.status.daily_quota_bytes - self.status.daily_bytes_used)

    def schedule_pulls(self, max_bundles: int = 5) -> list[dict[str, Any]]:
        """
        Process pending REQUEST bundles fair-share by priority class.
        Never lets general traffic starve emergency/health/education.
        """
        self.detect()
        results: list[dict[str, Any]] = []
        if not self.status.present:
            return results

        remaining = self.remaining_quota()
        if remaining <= 0:
            log.warning("Daily gateway quota exhausted")
            return results

        # Group pending requests by class rank
        reqs = [
            b
            for b in self.dtn.pending()
            if b.kind == BundleKind.REQUEST.value and not b.delivered
        ]
        reqs.sort(key=lambda b: (b.rank, b.created_at))

        processed = 0
        for b in reqs:
            if processed >= max_bundles or remaining <= 0:
                break
            # Soft cap per bundle
            want = min(b.size_bytes or 64 * 1024, remaining, 50 * 1024 * 1024)
            downloaded = 0
            if self.pull_handler:
                try:
                    downloaded = int(self.pull_handler(b.priority_class, b.payload) or 0)
                except Exception as exc:  # noqa: BLE001
                    log.exception("pull_handler failed: %s", exc)
                    results.append({"bundle_id": b.id, "ok": False, "error": str(exc)})
                    continue
            else:
                # Simulation / dry: mark fulfilled with zero network
                downloaded = min(want, 1024)
                b.payload["fulfilled_sim"] = True

            self.status.daily_bytes_used += max(0, downloaded)
            remaining = self.remaining_quota()
            self.dtn.mark_delivered(b.id)
            processed += 1
            row = {
                "bundle_id": b.id,
                "ok": True,
                "bytes": downloaded,
                "priority_class": b.priority_class,
                "package_id": (b.payload or {}).get("package_id"),
                "preset": (b.payload or {}).get("preset"),
            }
            results.append(row)
            self._record_receipt(row)
        return results

    def _record_receipt(self, row: dict[str, Any]) -> None:
        if not self.receipt_log_path:
            return
        try:
            from skycache.nexus.gateway_presets import PullReceiptLog

            PullReceiptLog(self.receipt_log_path).append(row)
        except Exception as exc:  # noqa: BLE001
            log.debug("receipt log failed: %s", exc)

    def request_package(
        self,
        package_id: str,
        priority_class: str = PriorityClass.EDUCATION.value,
    ) -> str:
        b = self.dtn.enqueue(
            kind=BundleKind.REQUEST,
            priority_class=priority_class,
            origin_node=self.node_id,
            payload={"package_id": package_id, "action": "fetch_open"},
            size_bytes=0,
        )
        return b.id

    def set_daily_quota_mb(self, mb: int) -> None:
        """Operator ethics control: daily fair-share cap (megabytes)."""
        self.status.daily_quota_bytes = max(0, int(mb)) * 1024 * 1024

    def receipts_summary(self) -> dict[str, Any]:
        if not self.receipt_log_path:
            return {"count": 0, "recent": [], "note": "receipt log not configured"}
        from skycache.nexus.gateway_presets import PullReceiptLog

        return PullReceiptLog(self.receipt_log_path).summary()

    def snapshot(self) -> dict[str, Any]:
        self.detect()
        from skycache.nexus.gateway_presets import list_presets

        return {
            "present": self.status.present,
            "kind": self.status.kind,
            "daily_bytes_used": self.status.daily_bytes_used,
            "daily_quota_bytes": self.status.daily_quota_bytes,
            "remaining_quota": self.remaining_quota(),
            "daily_quota_mb": round(self.status.daily_quota_bytes / (1024 * 1024), 1),
            "remaining_quota_mb": round(self.remaining_quota() / (1024 * 1024), 1),
            "note": self.status.note,
            "open_mirror_presets": [
                {"id": p["id"], "label": p["label"], "priority_class": p["priority_class"]}
                for p in list_presets()
            ],
            "receipts": self.receipts_summary(),
            "legal": (
                "Gateway pulls open/FTA/licensed content only. "
                "No commercial decryption. Not automatic public internet bridging."
            ),
            "dtn": self.dtn.stats(),
        }
