"""batman-adv day-one hardware OOB helpers (v0.9.1).

Dry-run and sim-safe on Windows/CI. On Linux with root + batctl, can emit a
concrete bring-up plan and optionally invoke deploy/mesh/batman-day-one.sh.

Legal: unlicensed Wi-Fi / ISM only. Never satellite uplink.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HONEST = (
    "Community mesh day-one: unlicensed Wi-Fi/ISM only. "
    "Receive-only satellite. Not free commercial broadband or Starlink."
)


def detect_mesh_environment() -> dict[str, Any]:
    """Probe host for batman-adv readiness (non-destructive)."""
    system = platform.system().lower()
    batctl = shutil.which("batctl")
    ip_cmd = shutil.which("ip")
    iw = shutil.which("iw")
    modprobe = shutil.which("modprobe")
    is_linux = system == "linux"
    batman_module = False
    neighbors: list[str] = []
    if batctl and is_linux:
        try:
            r = subprocess.run(
                [batctl, "n"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if r.returncode == 0 and r.stdout:
                neighbors = [
                    ln.strip()
                    for ln in r.stdout.splitlines()
                    if ln.strip() and not ln.lower().startswith("batman")
                ][:20]
        except (OSError, subprocess.TimeoutExpired):
            pass
    if is_linux and Path("/sys/module/batman_adv").exists():
        batman_module = True

    return {
        "system": system,
        "is_linux": is_linux,
        "batctl": batctl or "",
        "ip": ip_cmd or "",
        "iw": iw or "",
        "modprobe": modprobe or "",
        "batman_module_loaded": batman_module,
        "neighbor_lines": neighbors,
        "hardware_oob_ready": bool(is_linux and batctl),
        "sim_only_here": not is_linux or not batctl,
        "legal": HONEST,
    }


def day_one_plan(
    *,
    mesh_if: str = "wlan0",
    bat_if: str = "bat0",
    node_octet: int = 10,
    client_if: str = "wlan1",
    ssid_client: str = "SkyCache-Village",
    legal_rf_mode: str = "ism_mesh",
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Produce a day-one mesh bring-up plan (always safe; no RF unless applied)."""
    env = detect_mesh_environment()
    steps = [
        {
            "id": 1,
            "title": "Spectrum & legal check",
            "cmd": None,
            "note": (
                f"Confirm national unlicensed rules for {mesh_if}. "
                f"legal_rf_mode={legal_rf_mode}. No satellite TX."
            ),
        },
        {
            "id": 2,
            "title": "Load batman-adv",
            "cmd": "modprobe batman-adv && command -v batctl",
            "note": "Requires Linux kernel module + batctl package",
        },
        {
            "id": 3,
            "title": "Mesh radio -> bat0",
            "cmd": (
                f"ip link set {mesh_if} up; batctl if add {mesh_if}; "
                f"ip link set {bat_if} up; "
                f"ip addr add 10.42.0.{int(node_octet)}/24 dev {bat_if}"
            ),
            "note": "Adjust IBSS/mesh join per driver  -  see batman-day-one.sh",
        },
        {
            "id": 4,
            "title": "Client AP (second radio optional)",
            "cmd": f"hostapd for {client_if} SSID={ssid_client}",
            "note": "Phones join client SSID; mesh stays on mesh_if",
        },
        {
            "id": 5,
            "title": "SkyCache mesh mode",
            "cmd": (
                "skycache first-boot ... --legal-rf-mode ism_mesh "
                "or set SKYCACHE_MESH_MODE=batman"
            ),
            "note": "Portal must bind on bat0 / LAN IP",
        },
        {
            "id": 6,
            "title": "Validate",
            "cmd": "batctl n; skycache nexus validate --nodes 2; curl -s localhost:8080/api/health",
            "note": "2-node physical checklist: docs/mesh-field-checklist.md",
        },
    ]
    script = _repo_script()
    plan = {
        "schema": "skycache.mesh.day_one.v1",
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {
            "mesh_if": mesh_if,
            "bat_if": bat_if,
            "node_octet": int(node_octet),
            "client_if": client_if,
            "ssid_client": ssid_client,
            "legal_rf_mode": legal_rf_mode,
        },
        "environment": env,
        "steps": steps,
        "script_path": str(script) if script else "",
        "apply_allowed": bool(env.get("hardware_oob_ready") and env.get("is_linux")),
        "banner": HONEST,
        "docs": [
            "docs/mesh-deployment.md",
            "docs/mesh-field-checklist.md",
            "deploy/mesh/batman-day-one.sh",
        ],
    }
    if data_dir:
        out = Path(data_dir) / "nexus" / "mesh-day-one-plan.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        plan["written"] = str(out)
    return plan


def _repo_script() -> Path | None:
    # skycache/nexus/ -> repo root deploy/mesh/
    here = Path(__file__).resolve()
    cand = here.parents[2] / "deploy" / "mesh" / "batman-day-one.sh"
    return cand if cand.is_file() else None


def apply_day_one(
    *,
    dry_run: bool = True,
    mesh_if: str = "wlan0",
    bat_if: str = "bat0",
    node_octet: int = 10,
    env_extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run batman-day-one.sh when safe; otherwise return plan-only result."""
    plan = day_one_plan(mesh_if=mesh_if, bat_if=bat_if, node_octet=node_octet)
    script = _repo_script()
    if dry_run or not plan.get("apply_allowed"):
        return {
            "ok": True,
            "applied": False,
            "dry_run": True,
            "reason": (
                "dry_run" if dry_run else "host not Linux/batctl-ready  -  plan only"
            ),
            "plan": plan,
        }
    if not script:
        return {"ok": False, "error": "batman-day-one.sh missing", "plan": plan}
    env = {
        "MESH_IF": mesh_if,
        "BAT_IF": bat_if,
        "NODE_OCTET": str(node_octet),
        **(env_extra or {}),
    }
    try:
        r = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env={**dict(**__import__("os").environ), **env},
        )
        return {
            "ok": r.returncode == 0,
            "applied": True,
            "returncode": r.returncode,
            "stdout": (r.stdout or "")[-4000:],
            "stderr": (r.stderr or "")[-2000:],
            "plan": plan,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "applied": False, "error": str(exc), "plan": plan}
