"""Golden Raspberry Pi SD image bake support (v1.4.0 Golden Node Bake Ops).

Produces bake plans, host doctor, seal checklist, optional sealed-image
manifest (URL + sha256 only), and the public download kit zip.

Actual multi-GB .img write requires Linux + pi-gen / dd / rpi-imager on the
operator machine. Raw images never live in git.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skycache import __version__

HONEST = (
    "Golden Pi image: offline village node. Receive-only satellite hooks. "
    "Not free commercial broadband. Operator flashes SD; verify local law. "
    "Never ship default PIN 2468."
)

APT_PACKAGES = [
    "python3",
    "python3-venv",
    "python3-pip",
    "git",
    "rsync",
    "hostapd",
    "dnsmasq",
    "iptables",
    "batctl",
    "wireless-tools",
    "iw",
    "usbutils",
    "sqlite3",
    "curl",
]

OPTIONAL_APT = [
    "rtl-sdr",
    "soapysdr-tools",
]

FORBIDDEN_PINS = frozenset({"2468", "0000", "1234", "1111", "9999"})

DOWNLOAD_KIT_NAME = "skycache-golden-sd-kit.zip"
DEFAULT_HOSTED_PATHS = {
    "site": "https://skycache.jonbailey.xyz/downloads/skycache-golden-sd-kit.zip",
    "github_release_asset": (
        f"https://github.com/Pitchfork-and-Torch/SkyCache/releases/download/"
        f"v{__version__}/skycache-golden-sd-kit.zip"
    ),
    "pages_path": "/downloads/skycache-golden-sd-kit.zip",
    "install_page": "https://skycache.jonbailey.xyz/install/",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bake_plan(
    *,
    hostname: str = "skycache-village",
    ssid: str = "SkyCache-Village",
    legal_rf_mode: str = "receive_only",
    mesh_mode: str = "sim",
    admin_pin_hint: str = "(set at first-boot; never default 2468)",
    include_optional_sdr: bool = False,
    include_rx_ops: bool = True,
) -> dict[str, Any]:
    pkgs = list(APT_PACKAGES)
    if include_optional_sdr:
        pkgs.extend(OPTIONAL_APT)
    steps: list[dict[str, Any]] = [
        {
            "id": "base",
            "title": "Flash Raspberry Pi OS Lite (64-bit) to microSD",
            "tool": "Raspberry Pi Imager or dd",
            "note": "Enable SSH + set hostname in Imager advanced options",
        },
        {
            "id": "boot",
            "title": "First boot on LAN; apt update",
            "cmds": [
                "sudo apt-get update -y",
                "sudo apt-get install -y " + " ".join(pkgs),
            ],
        },
        {
            "id": "install",
            "title": "Install SkyCache village fabric",
            "cmds": [
                "sudo bash deploy/install-village-fabric.sh",
                f"sudo -u skycache skycache first-boot --yes --pin <OPERATOR_PIN> "
                f"--ssid {ssid} --legal-rf-mode {legal_rf_mode} "
                f"{'--sim' if mesh_mode == 'sim' else ''}",
            ],
            "note": "OPERATOR_PIN must not be 2468 / 0000 / 1234",
        },
        {
            "id": "services",
            "title": "Enable portal service",
            "cmds": [
                "sudo systemctl enable --now skycache.service",
                "curl -sf http://127.0.0.1:8080/api/health || true",
            ],
        },
        {
            "id": "readiness",
            "title": "Partner / lab readiness score",
            "cmds": [
                "skycache partner readiness --data-dir /var/lib/skycache/data",
            ],
            "note": "Want go_sim_pilot true before cloning the image",
        },
    ]
    if include_rx_ops:
        steps.append(
            {
                "id": "rx_optional",
                "title": "Optional FTA RX stack (product import path)",
                "cmds": [
                    "skycache rx doctor --data-dir /var/lib/skycache/data",
                    "# Optional: skycache rx station --lat LAT --lon LON",
                    "# Optional: skycache rx schedule --hours 24",
                ],
                "note": "SatDump/RTL optional; product import works without dongle",
            }
        )
    steps.extend(
        [
            {
                "id": "mesh",
                "title": "Optional day-one mesh (second radio)",
                "cmds": [
                    "sudo bash deploy/mesh/batman-day-one.sh",
                    "skycache mesh day-one --write",
                ],
                "note": "Only after spectrum check; legal_rf_mode=ism_mesh",
            },
            {
                "id": "verify",
                "title": "Golden image verify",
                "cmds": [
                    "skycache doctor",
                    "skycache capabilities",
                    "skycache skybrary doctor",
                    "skycache partner readiness",
                    "curl -s http://127.0.0.1:8080/api/health",
                ],
            },
            {
                "id": "seal",
                "title": "Seal image for cloning (optional fleet)",
                "cmds": [
                    "sudo systemctl enable skycache.service",
                    "sudo bash -c 'test -f SEAL-CHECKLIST.md && cat SEAL-CHECKLIST.md'",
                    "# Power off; on Linux host: dd if=/dev/sdX bs=4M status=progress | xz -T0 > skycache-village-pi.img.xz",
                    "# Register without committing binary: skycache pi-image sealed-manifest --url ... --sha256 ...",
                ],
                "note": "Never ship default PIN 2468 on sealed images; rotate PIN per site after clone",
            },
        ]
    )
    return {
        "schema": "skycache.pi.golden_image.v2",
        "software_version": __version__,
        "built_at": _iso_now(),
        "hostname": hostname,
        "ssid": ssid,
        "legal_rf_mode": legal_rf_mode,
        "mesh_mode": mesh_mode,
        "admin_pin_policy": admin_pin_hint,
        "forbidden_pins": sorted(FORBIDDEN_PINS),
        "apt_packages": pkgs,
        "optional_apt": OPTIONAL_APT,
        "steps": steps,
        "host_probe": _host_probe(),
        "banner": HONEST,
        "docs": [
            "docs/first-boot.md",
            "deploy/pi-image/README.md",
            "deploy/install-village-fabric.sh",
            "docs/partner-kits.md",
            "docs/phase2-live-rx.md",
        ],
        "site": {
            "install": DEFAULT_HOSTED_PATHS["install_page"],
            "kit_zip": DEFAULT_HOSTED_PATHS["site"],
        },
    }


def _host_probe() -> dict[str, Any]:
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "can_flash_here": platform.system().lower() == "linux",
        "rpi_imager": bool(shutil.which("rpi-imager") or shutil.which("rpi-imager.exe")),
        "pi_gen": bool(shutil.which("pi-gen") or Path("/usr/bin/pi-gen").exists()),
        "dd": bool(shutil.which("dd")),
        "xz": bool(shutil.which("xz")),
        "python3": bool(shutil.which("python3") or shutil.which("py")),
    }


def pi_image_doctor() -> dict[str, Any]:
    """Host readiness for golden bake / seal (no personal data)."""
    probe = _host_probe()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    add("python", probe["python3"], "Python available for skycache CLI", 15)
    sys_name = str(probe.get("system") or "")
    add(
        "linux_flash",
        sys_name.lower() == "linux",
        "Linux host can dd/pi-gen seal" if sys_name.lower() == "linux" else f"OS={sys_name}: flash/seal on Linux later; plan/bundle OK here",
        12,
    )
    add("rpi_imager", bool(probe.get("rpi_imager")), "Raspberry Pi Imager on PATH (optional)", 5)
    add("dd", bool(probe.get("dd")), "dd available for seal" if probe.get("dd") else "dd missing (Linux seal host)", 8)
    add("xz", bool(probe.get("xz")), "xz available for .img.xz" if probe.get("xz") else "xz missing (optional compress)", 5)
    add("pi_gen", bool(probe.get("pi_gen")), "pi-gen present (advanced)" if probe.get("pi_gen") else "pi-gen not required for kit path", 3)

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    # Kit path works on Windows; seal needs Linux
    go_kit = bool(probe.get("python3"))
    go_seal = go_kit and sys_name.lower() == "linux" and bool(probe.get("dd"))

    return {
        "schema": "skycache.pi.doctor.v1",
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_kit_path": go_kit,
        "go_seal_path": go_seal,
        "host_probe": probe,
        "checks": checks,
        "banner": HONEST,
        "next_steps": _doctor_next(go_kit, go_seal, probe),
        "legal": "Receive-only village node kit - not free commercial broadband",
    }


def _doctor_next(go_kit: bool, go_seal: bool, probe: dict[str, Any]) -> list[str]:
    steps: list[str] = []
    if go_kit:
        steps.append("skycache pi-image plan")
        steps.append("skycache pi-image bundle --out data/pi-download")
        steps.append("Flash Pi OS Lite, then bake-golden.sh with SKYCACHE_ADMIN_PIN")
    if not go_seal:
        steps.append("Seal/clone on a Linux host: dd + xz; then pi-image sealed-manifest")
    else:
        steps.append("After bake: power off SD, dd | xz, then sealed-manifest --url --sha256")
    steps.append("Never use PIN 2468 on field images")
    return steps


def write_seal_checklist(out_dir: Path, *, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write SEAL-CHECKLIST.md for fleet clone discipline."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = plan or bake_plan()
    path = out_dir / "SEAL-CHECKLIST.md"
    body = f"""# Golden node seal checklist

Software: {plan.get('software_version')}
Built plan: {plan.get('built_at')}

{HONEST}

## Before imaging the SD

- [ ] Admin PIN is **not** one of: {', '.join(sorted(FORBIDDEN_PINS))}
- [ ] `skycache partner readiness` shows go_sim_pilot true
- [ ] Portal health OK: `curl http://127.0.0.1:8080/api/health`
- [ ] Skybrary samples load; license inventory printable
- [ ] Legal banner reviewed with local maintainer
- [ ] Optional: `skycache rx doctor` if FTA weather path desired
- [ ] SSH default passwords changed / keys only
- [ ] Hostname set ({plan.get('hostname')}); SSID plan ({plan.get('ssid')})

## Seal (Linux host)

- [ ] Power off Pi cleanly
- [ ] Identify block device carefully (destroy data if wrong disk)
- [ ] `sudo dd if=/dev/sdX bs=4M status=progress | xz -T0 > skycache-village-pi.img.xz`
- [ ] `sha256sum skycache-village-pi.img.xz`
- [ ] Register (no binary in git):
  `skycache pi-image sealed-manifest --url <https-url> --sha256 <hex> --size-bytes N --out data/pi-download/sealed-manifest.json`

## After clone to a new site

- [ ] Change admin PIN again
- [ ] Set station lat/lon if using RX schedule
- [ ] Re-run partner readiness
- [ ] Do not claim free commercial broadband
"""
    path.write_text(body, encoding="utf-8")
    return {"ok": True, "path": str(path), "forbidden_pins": sorted(FORBIDDEN_PINS)}


def write_bake_artifacts(out_dir: Path, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write bake plan JSON + shell checklist + seal checklist under out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = plan or bake_plan()
    plan_path = out_dir / "golden-pi-bake-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    sh_path = out_dir / "golden-pi-verify.sh"
    sh_path.write_text(_verify_shell(plan), encoding="utf-8", newline="\n")
    seal = write_seal_checklist(out_dir, plan=plan)
    readme = out_dir / "README-BAKE.txt"
    readme.write_text(
        f"""SkyCache Golden Raspberry Pi image bake
Version: {plan.get('software_version')}
{plan.get('banner')}

1. Flash Raspberry Pi OS Lite 64-bit with Raspberry Pi Imager
2. Boot, then run: sudo bash deploy/install-village-fabric.sh
3. skycache first-boot --yes --pin <new non-default> --ssid {plan.get('ssid')} --legal-rf-mode {plan.get('legal_rf_mode')}
4. bash {sh_path.name}
5. skycache partner readiness
6. Optional mesh: sudo bash deploy/mesh/batman-day-one.sh
7. Optional seal: see SEAL-CHECKLIST.md (Linux dd + sealed-manifest)

Never leave admin PIN as 2468 on field images.
Full plan: {plan_path.name}
Install page: {DEFAULT_HOSTED_PATHS['install_page']}
""",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "out_dir": str(out_dir),
        "plan": str(plan_path),
        "verify_script": str(sh_path),
        "seal_checklist": seal.get("path"),
        "readme": str(readme),
        "schema": plan.get("schema"),
    }


def sealed_image_manifest(
    *,
    url: str,
    sha256: str,
    size_bytes: int | None = None,
    out_path: Path | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Record operator-hosted sealed .img.xz metadata (binary stays off-repo)."""
    url = (url or "").strip()
    sha = (sha256 or "").strip().lower()
    errors: list[str] = []
    if not url.startswith("https://"):
        errors.append("url must be https://")
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        errors.append("sha256 must be 64 hex chars")
    if size_bytes is not None and int(size_bytes) < 0:
        errors.append("size_bytes must be >= 0")
    manifest = {
        "schema": "skycache.pi.sealed_image.v1",
        "software_version": __version__,
        "registered_at": _iso_now(),
        "url": url,
        "sha256": sha,
        "size_bytes": int(size_bytes) if size_bytes is not None else None,
        "filename_hint": "skycache-village-pi.img.xz",
        "note": (note or "").strip(),
        "banner": HONEST,
        "legal": (
            "Operator-hosted sealed image only. Not shipped in git. "
            "Verify sha256 before flash. Not free commercial broadband."
        ),
        "ok": len(errors) == 0,
        "errors": errors,
    }
    if out_path and manifest["ok"]:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        manifest["path"] = str(out_path)
    return manifest


def hash_file_sha256(path: Path, *, chunk: int = 1024 * 1024) -> dict[str, Any]:
    """Hash a local sealed image for sealed-manifest (operator machine)."""
    path = Path(path)
    if not path.is_file():
        return {"ok": False, "error": f"not a file: {path}"}
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
            size += len(block)
    return {
        "ok": True,
        "path": str(path),
        "sha256": h.hexdigest(),
        "size_bytes": size,
        "filename": path.name,
    }


def build_downloadable_sd_kit(
    out_dir: Path,
    *,
    repo_root: Path | None = None,
    zip_name: str = DOWNLOAD_KIT_NAME,
    include_optional_sdr: bool = False,
) -> dict[str, Any]:
    """Build downloadable golden-SD operator kit (zip) for public hosting."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    stage = out_dir / "skycache-golden-sd-kit"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    plan = bake_plan(include_optional_sdr=include_optional_sdr)
    arts = write_bake_artifacts(stage / "bake", plan)

    copy_map = {
        "deploy/install-village-fabric.sh": repo_root / "deploy" / "install-village-fabric.sh",
        "deploy/first-boot-wizard.sh": repo_root / "deploy" / "first-boot-wizard.sh",
        "deploy/pi-image/bake-golden.sh": repo_root / "deploy" / "pi-image" / "bake-golden.sh",
        "deploy/pi-image/README.md": repo_root / "deploy" / "pi-image" / "README.md",
        "deploy/mesh/batman-day-one.sh": repo_root / "deploy" / "mesh" / "batman-day-one.sh",
        "deploy/mesh/batman-setup.example.sh": repo_root / "deploy" / "mesh" / "batman-setup.example.sh",
        "deploy/mesh/hostapd-client-ap.example.conf": (
            repo_root / "deploy" / "mesh" / "hostapd-client-ap.example.conf"
        ),
        "docs/first-boot.md": repo_root / "docs" / "first-boot.md",
        "docs/mesh-field-checklist.md": repo_root / "docs" / "mesh-field-checklist.md",
        "docs/hardware-bom.md": repo_root / "docs" / "hardware-bom.md",
        "docs/legal-ethics.md": repo_root / "docs" / "legal-ethics.md",
        "docs/partner-kits.md": repo_root / "docs" / "partner-kits.md",
        "docs/phase2-live-rx.md": repo_root / "docs" / "phase2-live-rx.md",
        "docs/threat-model.md": repo_root / "docs" / "threat-model.md",
    }
    included: list[str] = []
    for rel, src in copy_map.items():
        if not src.is_file():
            continue
        dest = stage / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        included.append(rel)

    hosting = {
        "schema": "skycache.pi.download_kit.v2",
        "software_version": __version__,
        "kit_name": zip_name,
        "built_at": plan.get("built_at"),
        "banner": HONEST,
        "what_this_is": (
            "Operator flash kit: scripts + plan to produce a golden village SD after "
            "flashing Raspberry Pi OS Lite. Not a multi-GB raw .img in git."
        ),
        "how_to_flash": [
            "1. Flash Raspberry Pi OS Lite 64-bit (Imager)",
            "2. Copy this kit to the Pi (USB/scp)",
            "3. export SKYCACHE_ADMIN_PIN=<non-default non-2468>",
            "4. sudo bash deploy/pi-image/bake-golden.sh  OR install-village-fabric.sh + first-boot",
            "5. bash bake/golden-pi-verify.sh",
            "6. skycache partner readiness",
            "7. Optional seal: bake/SEAL-CHECKLIST.md + pi-image sealed-manifest",
        ],
        "hosted_urls": DEFAULT_HOSTED_PATHS,
        "optional_raw_img": (
            "Operators who produce a sealed .img.xz via dd/pi-gen host it themselves "
            "and register with skycache pi-image sealed-manifest (sha256 + https URL only)."
        ),
        "files": included,
        "legal": "Receive-only; never ship PIN 2468; not free commercial broadband.",
    }
    (stage / "HOSTING.json").write_text(
        json.dumps(hosting, indent=2) + "\n", encoding="utf-8"
    )
    (stage / "README.txt").write_text(
        f"""SkyCache Golden SD Kit v{__version__}
{HONEST}

This download is the public golden-image *kit* (scripts + plan + seal checklist).
Flash Raspberry Pi OS Lite first, then run bake-golden.sh with a strong PIN.

CLI on any machine:
  skycache pi-image doctor
  skycache pi-image plan
  skycache pi-image bundle --out data/pi-download

Hosted at:
  {DEFAULT_HOSTED_PATHS['site']}
  {DEFAULT_HOSTED_PATHS['install_page']}

See HOSTING.json, bake/README-BAKE.txt, bake/SEAL-CHECKLIST.md.
""",
        encoding="utf-8",
    )

    zip_path = out_dir / zip_name
    if zip_path.is_file():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in stage.rglob("*"):
            if f.is_file():
                zf.write(
                    f,
                    arcname=f"skycache-golden-sd-kit/{f.relative_to(stage).as_posix()}",
                )

    return {
        "ok": True,
        "zip": str(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "stage": str(stage),
        "hosting": hosting,
        "bake": arts,
        "download_urls": DEFAULT_HOSTED_PATHS,
        "software_version": __version__,
    }


def _verify_shell(plan: dict[str, Any]) -> str:
    return f"""#!/usr/bin/env bash
# Golden Pi post-flash verify - SkyCache {plan.get('software_version')}
set -euo pipefail
echo "{plan.get('banner')}"
python3 -m skycache doctor || skycache doctor
python3 -m skycache capabilities || skycache capabilities
python3 -m skycache skybrary doctor || true
python3 -m skycache partner readiness || skycache partner readiness || true
python3 -m skycache rx doctor || true
curl -sf http://127.0.0.1:8080/api/health || curl -sf http://127.0.0.1:8080/api/status || echo "WARN: portal not up yet - start skycache.service"
echo "[OK] golden verify finished"
"""
