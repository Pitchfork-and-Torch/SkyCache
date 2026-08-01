"""Phone Handoff Ops (v1.7.0): join cards, QR, doctor, one-shot export, import.

Local hub Wi-Fi only (or USB/SD mule). Not commercial broadband tethering.
Not live BLE stack - file bridge under data/handoff with portal QR.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from skycache import __version__
from skycache.capabilities.ble_mule import export_handoff_bundle, import_handoff_bundle
from skycache.nexus.dtn import DtnQueue
from skycache.nexus.identity import load_or_create_node_id

HONEST = (
    "Phone handoff: local hub Wi-Fi, USB, or SD only. "
    "Open content. Not commercial broadband tethering or free Starlink."
)

DOCTOR_SCHEMA = "skycache.handoff.doctor.v1"
JOIN_SCHEMA = "skycache.handoff.join.v1"
EXPORT_SCHEMA = "skycache.handoff.export.v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _qr_svg(data: str, *, box: int = 6, border: int = 2) -> str | None:
    """Build SVG QR matrix; requires optional qrcode package (pure modules, no PIL)."""
    try:
        import qrcode
    except ImportError:
        return None
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    modules = qr.get_matrix()
    n = len(modules)
    size = n * box
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" role="img" aria-label="QR code">'
        f'<rect width="100%" height="100%" fill="#fff"/>'
    ]
    for y, row in enumerate(modules):
        for x, cell in enumerate(row):
            if cell:
                parts.append(
                    f'<rect x="{x * box}" y="{y * box}" width="{box}" height="{box}" fill="#0f172a"/>'
                )
    parts.append("</svg>")
    return "".join(parts)


def handoff_doctor(*, data_dir: Path | None = None) -> dict[str, Any]:
    """Local phone-path readiness (no personal data)."""
    from skycache.config import Settings
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.phone_demo import demos_ready, ensure_demo_texts

    settings = Settings(data_dir=Path(data_dir) if data_dir else Path("data"))
    settings.ensure_dirs()
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, weight: int = 10) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "weight": weight})

    content = settings.content_dir
    pkgs = (
        [p.name for p in content.iterdir() if p.is_dir() and (p / "manifest.json").is_file()]
        if content.is_dir()
        else []
    )
    add("content_packages", len(pkgs) >= 1, f"{len(pkgs)} packages available for mule", 15)

    sky = SkybraryCatalog(settings.skybrary_db_path)
    try:
        ensure_demo_texts(settings, sky)
        demos = demos_ready(settings, sky)
    finally:
        sky.close()
    add("phone_demos", demos, "3 PD demos ready for hub Wi-Fi save" if demos else "run skybrary samples --ingest", 15)

    handoff = settings.handoff_dir
    add("handoff_dir", handoff.is_dir(), str(handoff), 8)

    qr_ok = _qr_svg("http://10.42.0.1:8080/") is not None
    add("qr_engine", qr_ok, "qrcode package available" if qr_ok else "optional: pip install qrcode (SVG still optional)", 5)

    total_w = sum(c["weight"] for c in checks) or 1
    earned = sum(c["weight"] for c in checks if c["ok"])
    score = int(round(100.0 * earned / total_w))
    go_phone = demos and len(pkgs) >= 1

    return {
        "schema": DOCTOR_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "score": score,
        "go_phone_path": go_phone,
        "package_count": len(pkgs),
        "checks": checks,
        "banner": HONEST,
        "next_steps": [
            "skycache handoff join-card --portal-url http://10.42.0.1:8080/ --ssid SkyCache-Village",
            "skycache handoff export --limit 10",
            "Phone: join hub SSID -> open portal -> Save demos / download /handoff/",
        ],
        "legal": "Local transfer only - no cloud mule, no commercial tethering claims",
    }


def write_join_card(
    out_dir: Path,
    *,
    portal_url: str = "http://10.42.0.1:8080/",
    ssid: str = "SkyCache-Village",
    node_name: str = "village-hub",
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Write join.html + qr.svg for phones to open the local portal."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    portal_url = (portal_url or "").strip() or "http://10.42.0.1:8080/"
    if not portal_url.endswith("/"):
        portal_url = portal_url + "/"

    svg = _qr_svg(portal_url)
    qr_path = out_dir / "join-qr.svg"
    qr_note = "QR generated offline"
    if svg:
        qr_path.write_text(svg, encoding="utf-8")
    else:
        qr_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80">'
            '<text x="10" y="40" font-size="12">Install qrcode for SVG QR</text></svg>\n',
            encoding="utf-8",
        )
        qr_note = "qrcode not installed - HTML join card only; pip install qrcode for SVG QR"

    demos_url = portal_url.rstrip("/") + "/api/demo/pack.zip"
    handoff_url = portal_url.rstrip("/") + "/handoff/"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Join SkyCache hub - {node_name}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:28rem;margin:1.5rem auto;padding:0 1rem;line-height:1.45;color:#0f172a}}
.card{{border:1px solid #cbd5e1;border-radius:12px;padding:1rem 1.1rem;background:#f8fafc}}
.banner{{background:#ecfeff;border:1px solid #a5f3fc;padding:.65rem;border-radius:8px;font-size:.88rem;margin-bottom:1rem}}
h1{{font-size:1.25rem;margin:0 0 .5rem}}
.ssid{{font-size:1.35rem;font-weight:700;letter-spacing:.02em}}
.url{{word-break:break-all;font-family:ui-monospace,monospace;font-size:.9rem}}
.qr{{display:block;margin:1rem auto;max-width:220px}}
ol{{padding-left:1.2rem}}
.legal{{color:#64748b;font-size:.8rem;margin-top:1.25rem}}
</style>
</head>
<body>
<div class="banner">{HONEST}</div>
<div class="card">
  <h1>Join this village hub</h1>
  <p>Node: <strong>{node_name}</strong></p>
  <p>Wi-Fi name (SSID)</p>
  <p class="ssid">{ssid}</p>
  <p>Then open in the phone browser:</p>
  <p class="url"><a href="{portal_url}">{portal_url}</a></p>
  <img class="qr" src="join-qr.svg" alt="QR code to open hub portal"/>
  <ol>
    <li>Turn off mobile data if captive portal is flaky</li>
    <li>Join <strong>{ssid}</strong></li>
    <li>Scan QR or type the URL</li>
    <li>Library → Save demos to this phone (no cell plan)</li>
    <li>Or open <a href="{demos_url}">demo pack zip</a> (local hub only)</li>
    <li>Optional: open <a href="{handoff_url}">/handoff/</a> for USB mule packs</li>
  </ol>
</div>
<p class="legal">Software v{__version__} · Public-domain demos only · Not medical advice · Not free Starlink</p>
</body>
</html>
"""
    (out_dir / "join.html").write_text(html, encoding="utf-8")
    meta = {
        "schema": JOIN_SCHEMA,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "portal_url": portal_url,
        "ssid": ssid,
        "node_name": node_name,
        "join_html": str(out_dir / "join.html"),
        "qr_svg": str(qr_path),
        "qr_note": qr_note,
        "demos_hint": demos_url,
        "handoff_path": "/handoff/",
        "banner": HONEST,
    }
    (out_dir / "join.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, **meta}


def export_phone_handoff(
    *,
    data_dir: Path,
    out_dir: Path | None = None,
    package_ids: list[str] | None = None,
    limit: int = 20,
    portal_url: str = "http://10.42.0.1:8080/",
    ssid: str = "SkyCache-Village",
    include_join_card: bool = True,
    zip_bundle: bool = True,
) -> dict[str, Any]:
    """One-shot: export mule packages + join card under handoff dir."""
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir))
    settings.ensure_dirs()
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    out_root = Path(out_dir) if out_dir else settings.handoff_dir
    out_root.mkdir(parents=True, exist_ok=True)

    ids = list(package_ids or [])
    if not ids:
        ids = [p.name for p in settings.content_dir.iterdir() if p.is_dir()][: max(1, int(limit))]

    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    bundle = export_handoff_bundle(
        dtn=dtn,
        content_dir=settings.content_dir,
        package_ids=ids,
        out_dir=out_root,
        node_id=node_id,
    )

    join_meta: dict[str, Any] | None = None
    if include_join_card:
        join_meta = write_join_card(
            bundle / "join",
            portal_url=portal_url,
            ssid=ssid,
            node_name=node_id,
            data_dir=settings.data_dir,
        )
        # Also publish latest join at handoff root for /handoff/join.html
        write_join_card(
            out_root / "join",
            portal_url=portal_url,
            ssid=ssid,
            node_name=node_id,
            data_dir=settings.data_dir,
        )
        # Flat copy for static server convenience
        for name in ("join.html", "join-qr.svg", "join.json"):
            src = out_root / "join" / name
            if src.is_file():
                shutil.copy2(src, out_root / name)

    zip_path: str | None = None
    if zip_bundle:
        zp = out_root / f"{bundle.name}.zip"
        if zp.is_file():
            zp.unlink()
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(bundle.rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=f"{bundle.name}/{f.relative_to(bundle).as_posix()}")
        zip_path = str(zp)

    # Index for /handoff/
    index = out_root / "index.html"
    index.write_text(
        f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SkyCache handoff</title>
<style>body{{font-family:system-ui,sans-serif;max-width:32rem;margin:1.5rem auto;padding:0 1rem;line-height:1.5}}
a{{color:#0d9488}}</style></head><body>
<h1>Hub handoff</h1>
<p>{HONEST}</p>
<ul>
<li><a href="join.html">Join card (SSID + QR)</a></li>
<li><a href="{quote(bundle.name)}/">{bundle.name}/</a> (packages + handoff.json)</li>
{f'<li><a href="{quote(Path(zip_path).name)}">{Path(zip_path).name}</a></li>' if zip_path else ''}
</ul>
<p><a href="/">Back to portal</a></p>
</body></html>
""",
        encoding="utf-8",
    )

    return {
        "schema": EXPORT_SCHEMA,
        "ok": True,
        "generated_at": _iso_now(),
        "software_version": __version__,
        "bundle": str(bundle),
        "zip": zip_path,
        "packages": ids,
        "join": join_meta,
        "handoff_url_path": "/handoff/",
        "banner": HONEST,
    }


def import_phone_handoff(
    bundle_path: Path,
    *,
    data_dir: Path,
) -> dict[str, Any]:
    """Import a mule bundle directory or zip into this node."""
    from skycache.config import Settings

    settings = Settings(data_dir=Path(data_dir))
    settings.ensure_dirs()
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    path = Path(bundle_path)
    work = path
    tmp: Path | None = None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = settings.handoff_dir / f"_import_{path.stem}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(tmp)
        # find handoff.json
        found = list(tmp.rglob("handoff.json"))
        if not found:
            return {"ok": False, "error": "no handoff.json in zip"}
        work = found[0].parent
    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    rep = import_handoff_bundle(
        work,
        dtn=dtn,
        content_dest=settings.content_dir,
        node_id=node_id,
    )
    rep["ok"] = True
    rep["banner"] = HONEST
    if tmp and tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    return rep
