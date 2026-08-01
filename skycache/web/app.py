"""FastAPI application: portal API + static PWA + captive redirects + Nexus fabric."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from skycache import __version__
from skycache.community.boards import BoardStore
from skycache.community.licenses import LicenseInventory
from skycache.community.passport import package_record_passport, work_passport
from skycache.community.ratings import RatingsStore
from skycache.community.search import search_catalog
from skycache.config import NEXUS_HONEST_BANNER, Settings, webui_dir
from skycache.db.catalog import Catalog
from skycache.health.power import get_power_provider, mode_from_soc, should_run_live_rx
from skycache.health.signal import SignalMonitor
from skycache.ingest.normalizer import ContentManager
from skycache.mesh.agent import MeshAgent
from skycache.messaging.dtn_lite import DtnLiteStore
from skycache.models import SystemStatus
from skycache.nexus.control_plane import ControlPlane
from skycache.nexus.delta import delta_against_remote
from skycache.nexus.dtn import BundleKind, DtnQueue
from skycache.nexus.fabric import ContentFabric
from skycache.nexus.gateway import GatewayManager
from skycache.nexus.identity import load_or_create_node_id
from skycache.nexus.power_map import fabric_power_map
from skycache.nexus.spectrum import compliance_report
from skycache.nexus.traffic import traffic_monitor
from skycache.pipelines.runner import PipelineRunner
from skycache.policy.prioritizer import disk_usage
from skycache.capabilities.ble_mule import export_handoff_bundle
from skycache.capabilities.matrix import build_capability_matrix
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.pack_profile import (
    build_pack_from_profile,
    list_profiles,
    resolve_pack_out_dir,
)
from skycache.web.admin import require_admin_pin
from skycache.web.captive import is_captive_probe

log = logging.getLogger("skycache.web")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_dirs()
    try:
        settings.validate_nexus()
    except ValueError as exc:
        log.error("Invalid Nexus config: %s", exc)
        raise

    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    runner = PipelineRunner(settings, content)
    power = get_power_provider(settings.power_provider, settings.mock_battery_percent)
    signal = SignalMonitor()
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    mesh = MeshAgent(
        enabled=settings.nexus_enabled,
        node_id=node_id,
        data_dir=settings.data_dir,
        mode=settings.mesh_mode,
        band=settings.mesh_band,
    )
    if settings.nexus_enabled:
        mesh.start()
        mesh.fabric.disaster_mode = settings.disaster_mode
    # Legacy community notes (local outbox) + Nexus DTN queue
    dtn = DtnLiteStore(path=settings.data_dir / "dtn-outbox.json")
    dtn.load()
    nexus_dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    fabric = ContentFabric(
        node_id=node_id,
        catalog=catalog,
        content=content,
        mesh=mesh.fabric,
        dtn=nexus_dtn,
        content_dir=settings.content_dir,
        skybrary=None,  # attached after SkybraryCatalog is constructed
    )
    gateway = GatewayManager(
        dtn=nexus_dtn,
        node_id=node_id,
        sim_uplink=settings.sim_mode,
        receipt_log_path=settings.nexus_dir / "gateway-receipts.json",
    )
    gateway.status.daily_quota_bytes = int(settings.gateway_daily_quota_mb) * 1024 * 1024
    ratings = RatingsStore(settings.db_path)
    boards = BoardStore(settings.db_path)
    licenses = LicenseInventory(catalog)
    control = ControlPlane(
        data_dir=settings.data_dir,
        node_id=node_id,
        enabled=settings.mesh_band in ("lora_ism", "sim") and settings.nexus_enabled,
        band="lora_ism" if settings.mesh_band == "lora_ism" else "sim",
    )
    skybrary = SkybraryCatalog(settings.skybrary_db_path)
    fabric.attach_skybrary(skybrary)
    # Phone-offline demos: ensure 3 PD texts on every node start (local disk only).
    try:
        from skycache.skybrary.phone_demo import ensure_demo_texts

        _demo = ensure_demo_texts(settings, skybrary)
        if _demo.get("loaded_now"):
            log.info(
                "Phone demo texts ready: %s/%s",
                _demo.get("count_ready"),
                _demo.get("count_expected"),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not ensure phone demo texts: %s", exc)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        ratings.close()
        boards.close()
        skybrary.close()
        catalog.close()

    app = FastAPI(
        title="SkyCache Nexus",
        version=__version__,
        description=(
            "Community knowledge & connectivity fabric - store-and-forward + mesh. "
            "Not free commercial broadband."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.catalog = catalog
    app.state.content = content
    app.state.runner = runner
    app.state.power = power
    app.state.signal = signal
    app.state.mesh = mesh
    app.state.dtn = dtn
    app.state.nexus_dtn = nexus_dtn
    app.state.fabric = fabric
    app.state.gateway = gateway
    app.state.node_id = node_id
    app.state.ratings = ratings
    app.state.boards = boards
    app.state.control = control
    app.state.skybrary = skybrary

    ui = webui_dir()
    if ui.is_dir():
        app.mount("/static", StaticFiles(directory=str(ui)), name="static")
    # Phone/USB handoff bundles (file bridge under data/handoff)
    app.mount(
        "/handoff",
        StaticFiles(directory=str(settings.handoff_dir), html=True),
        name="handoff",
    )

    @app.middleware("http")
    async def captive_middleware(request: Request, call_next):
        path = request.url.path
        # Let API, static, content, and handoff downloads through
        if (
            path.startswith("/api")
            or path.startswith("/static")
            or path.startswith("/content")
            or path.startswith("/handoff")
        ):
            return await call_next(request)
        if is_captive_probe(path):
            # Force captive login page
            return RedirectResponse(url="/", status_code=302)
        return await call_next(request)

    @app.get("/")
    async def index() -> FileResponse:
        index_path = ui / "index.html"
        if not index_path.is_file():
            raise HTTPException(500, "webui/index.html missing")
        return FileResponse(index_path)

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        path = ui / "admin.html"
        if not path.is_file():
            raise HTTPException(500, "webui/admin.html missing")
        return FileResponse(path)

    @app.get("/manifest.webmanifest")
    async def webmanifest() -> FileResponse:
        return FileResponse(ui / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js")
    async def service_worker() -> FileResponse:
        return FileResponse(ui / "sw.js", media_type="application/javascript")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/status", response_model=SystemStatus)
    async def status() -> SystemStatus:
        total, _used, free = disk_usage(settings.content_dir)
        pct = power.battery_percent()
        mode = mode_from_soc(pct)
        return SystemStatus(
            version=__version__,
            sim_mode=settings.sim_mode,
            power_mode=mode,
            battery_percent=pct,
            disk_free_bytes=free,
            disk_total_bytes=total,
            package_count=catalog.count(),
            last_ingest=catalog.last_ingest(),
            signal_quality=signal.snapshot.quality,
            legal_banner=NEXUS_HONEST_BANNER,
        )

    @app.get("/api/power/guidance")
    async def power_guidance_api() -> dict[str, Any]:
        """How long until ECO / CRITICAL - rough solar maintainer guidance."""
        from skycache.health.power_guidance import power_guidance

        pct = power.battery_percent()
        mode = mode_from_soc(pct)
        return power_guidance(
            pct,
            mode,
            on_ac=power.is_on_ac(),
            battery_wh=float(getattr(settings, "battery_wh", 100.0) or 100.0),
        )

    @app.get("/api/power/maintainer-sheet")
    async def power_maintainer_sheet() -> Response:
        """Printable HTML power sheet for wall mount (browser -> print/PDF)."""
        from skycache.health.power_guidance import (
            maintainer_power_sheet_html,
            power_guidance,
        )

        pct = power.battery_percent()
        mode = mode_from_soc(pct)
        g = power_guidance(
            pct,
            mode,
            on_ac=power.is_on_ac(),
            battery_wh=float(getattr(settings, "battery_wh", 100.0) or 100.0),
        )
        html = maintainer_power_sheet_html(
            g,
            node_id=node_id,
            hotspot_ssid=settings.hotspot_ssid,
            version=__version__,
        )
        return Response(content=html, media_type="text/html; charset=utf-8")

    @app.get("/api/nexus/status")
    async def nexus_status() -> dict[str, Any]:
        pct = power.battery_percent()
        return {
            "version": __version__,
            "product": "SkyCache Nexus",
            "phase": 4,
            "edition": "0.4 community broadband experience",
            "banner": NEXUS_HONEST_BANNER,
            "node_id": node_id,
            "packages": catalog.count(),
            "mesh": mesh.status(),
            "fabric": fabric.status(),
            "dtn": nexus_dtn.stats(),
            "gateway": gateway.snapshot(),
            "disaster_mode": mesh.fabric.disaster_mode,
            "spectrum": compliance_report(),
            "power_map": fabric_power_map(
                mesh.fabric, local_battery=pct, local_solar=bool(power.is_on_ac())
            ),
            "traffic": traffic_monitor(nexus_dtn, gateway),
            "control_plane": control.status(),
        }

    @app.get("/api/search")
    async def api_search(
        q: str = Query(""),
        lang: str | None = None,
        category: str | None = None,
        limit: int = Query(40, ge=1, le=200),
    ) -> dict[str, Any]:
        results = search_catalog(
            catalog, q, lang=lang, category=category, limit=limit, ratings=ratings
        )
        return {
            "q": q,
            "count": len(results),
            "results": results,
            "banner": NEXUS_HONEST_BANNER,
        }

    @app.get("/api/boards")
    async def api_boards() -> list[dict[str, str]]:
        return boards.list_boards()

    @app.get("/api/boards/posts")
    async def api_board_posts(
        board: str | None = None,
        limit: int = Query(40, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        return boards.list_posts(board=board, limit=limit)

    @app.post("/api/boards/posts")
    async def api_board_create(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return boards.post(
                board=str(payload.get("board") or "general"),
                title=str(payload.get("title") or ""),
                body=str(payload.get("body") or ""),
                author=str(payload.get("author") or "anonymous"),
                pinned=bool(payload.get("pinned")),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/packages/{package_id}/passport")
    async def api_package_passport(
        package_id: str,
        verify: bool = Query(False, description="Run on-disk integrity checksums"),
    ) -> dict[str, Any]:
        """License passport: license, provenance, sha256, redistribute posture."""
        rec = catalog.get(package_id)
        if not rec:
            raise HTTPException(404, "Package not found")
        return package_record_passport(rec, include_integrity=verify)

    @app.get("/api/packages/{package_id}/rating")
    async def api_rating_get(package_id: str) -> dict[str, Any]:
        if not catalog.get(package_id):
            raise HTTPException(404, "Package not found")
        return ratings.summary(package_id)

    @app.post("/api/packages/{package_id}/rating")
    async def api_rating_set(package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not catalog.get(package_id):
            raise HTTPException(404, "Package not found")
        try:
            stars = int(payload.get("stars") or 0)
            return ratings.rate(
                package_id,
                stars,
                voter_token=str(payload.get("token") or "") or None,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/ratings/top")
    async def api_ratings_top(limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
        return ratings.top(limit=limit)

    @app.get("/api/licenses")
    async def api_licenses() -> dict[str, Any]:
        return licenses.report()

    @app.get("/api/nexus/power-map")
    async def api_power_map() -> dict[str, Any]:
        return fabric_power_map(
            mesh.fabric,
            local_battery=power.battery_percent(),
            local_solar=bool(power.is_on_ac()),
        )

    @app.get("/api/nexus/traffic")
    async def api_traffic() -> dict[str, Any]:
        return traffic_monitor(nexus_dtn, gateway)

    @app.get("/api/nexus/control")
    async def api_control() -> dict[str, Any]:
        return control.status()

    @app.post("/api/nexus/control/alert")
    async def api_control_alert(payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text required")
        msg = control.publish(
            "alert",
            {"text": text[:500]},
            priority=str(payload.get("priority") or "emergency"),
        )
        # Also elevate on local DTN for mesh delivery
        nexus_dtn.enqueue(
            kind=BundleKind.MESSAGE,
            priority_class="emergency",
            origin_node=node_id,
            payload={"alert": True, "text": text[:500], "control_id": msg.id},
        )
        return {"id": msg.id, "status": "published"}

    @app.post("/api/nexus/delta")
    async def api_delta(payload: dict[str, Any]) -> dict[str, Any]:
        """Compare remote gossip manifest; return delta plan (sim/production)."""
        remote = list(payload.get("manifest") or [])
        return delta_against_remote(fabric, remote)

    @app.get("/api/skybrary/works")
    async def skybrary_works(
        q: str = Query(""),
        language: str | None = None,
        subject: str | None = None,
        license: str | None = Query(None, alias="license"),
        limit: int = Query(40, ge=1, le=200),
    ) -> dict[str, Any]:
        results = skybrary.search(
            q,
            language=language,
            subject=subject,
            license_q=license,
            limit=limit,
        )
        return {
            "count": len(results),
            "results": results,
            "facets": skybrary.facets(),
            "legal": (
                "Skybrary: public domain / open licenses only. "
                "Not a complete archive of every text. Not free commercial broadband."
            ),
        }

    @app.get("/api/skybrary/works/{work_id}")
    async def skybrary_work(work_id: str) -> dict[str, Any]:
        w = skybrary.get_work(work_id)
        if not w:
            raise HTTPException(404, "Work not found")
        return w

    @app.get("/api/skybrary/works/{work_id}/passport")
    async def skybrary_work_passport(
        work_id: str,
        verify: bool = Query(False, description="Run on-disk integrity checksums when package path known"),
    ) -> dict[str, Any]:
        """License passport for a Skybrary work: license, provenance, sha256, redistribute."""
        w = skybrary.get_work(work_id)
        if not w:
            raise HTTPException(404, "Work not found")
        pkg_path = None
        package_id = w.get("package_id")
        if package_id:
            rec = catalog.get(package_id)
            if rec and rec.path:
                pkg_path = rec.path
            else:
                candidate = settings.content_dir / str(package_id)
                if candidate.is_dir():
                    pkg_path = candidate
        return work_passport(w, package_path=pkg_path, include_integrity=verify)

    def _package_dir_for_work(w: dict[str, Any]) -> Path | None:
        package_id = w.get("package_id")
        if not package_id:
            return None
        rec = catalog.get(package_id)
        if rec and rec.path:
            return Path(rec.path)
        candidate = settings.content_dir / str(package_id)
        if candidate.is_dir():
            return candidate
        return None

    @app.get("/api/skybrary/works/{work_id}/chapters")
    async def skybrary_work_chapters(work_id: str) -> dict[str, Any]:
        """Multi-file / EPUB spine chapter list for in-PWA reader."""
        from skycache.skybrary.chapters import chapters_for_work

        w = skybrary.get_work(work_id)
        if not w:
            raise HTTPException(404, "Work not found")
        pkg = _package_dir_for_work(w)
        return chapters_for_work(
            work=w, content_dir=settings.content_dir, package_path=pkg
        )

    @app.get("/api/skybrary/works/{work_id}/chapters/{chapter_index}")
    async def skybrary_work_chapter_body(
        work_id: str,
        chapter_index: int,
    ) -> dict[str, Any]:
        """Load one chapter body (txt/html/epub section) for the reader."""
        from skycache.skybrary.chapters import chapters_for_work, read_chapter_text

        w = skybrary.get_work(work_id)
        if not w:
            raise HTTPException(404, "Work not found")
        pkg = _package_dir_for_work(w)
        meta = chapters_for_work(
            work=w, content_dir=settings.content_dir, package_path=pkg
        )
        chapters = meta.get("chapters") or []
        if chapter_index < 0 or chapter_index >= len(chapters):
            raise HTTPException(404, "Chapter not found")
        ch = chapters[chapter_index]
        if not pkg:
            raise HTTPException(404, "Package not on this node")
        try:
            body = read_chapter_text(
                Path(pkg),
                path=str(ch.get("path") or "work.txt"),
                epub_inner=ch.get("epub_inner"),
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from exc
        body["chapter"] = ch
        body["work_id"] = work_id
        return body

    @app.get("/api/skybrary/facets")
    async def skybrary_facets() -> dict[str, Any]:
        return skybrary.facets()

    @app.get("/api/skybrary/catalog.json")
    async def skybrary_catalog_json(
        limit: int = Query(5000, ge=1, le=20_000),
    ) -> dict[str, Any]:
        """Dual-access catalog v2 (same shape as export-catalog) for local parity."""
        from skycache.skybrary.catalog_export import build_catalog_dict

        return build_catalog_dict(
            skybrary,
            limit=limit,
            site_base="https://skycache.jonbailey.xyz",
        )

    @app.get("/api/skybrary/kits")
    async def skybrary_kits() -> dict[str, Any]:
        """List starter kit definitions and CLI pack profiles for dual-access downloads."""
        from skycache.skybrary.pack_profile import list_profiles

        return {
            "starter_kits": [
                {
                    "id": "literacy-starter",
                    "title": "Literacy starter kit",
                    "cli": "skycache skybrary pack --profile literacy-starter",
                    "online_path": "/library/packs/literacy-starter.zip",
                },
                {
                    "id": "emergency-health-sample",
                    "title": "Emergency / health sample kit",
                    "cli": "skycache skybrary pack --profile emergency-health",
                    "online_path": "/library/packs/emergency-health-sample.zip",
                },
            ],
            "pack_profiles": list_profiles(),
            "legal": (
                "Open/PD educational kits only. Not medical advice. "
                "Not a complete archive. Not free commercial broadband."
            ),
        }

    @app.get("/api/skybrary/status")
    async def skybrary_status() -> dict[str, Any]:
        return {
            "product": "Skybrary",
            "work_count": skybrary.count(),
            "facets": skybrary.facets(),
            "phase": "S4-S6",
            "version_theme": "Skybrary Live + field depth",
            "profiles": list_profiles(),
            "banner": (
                "Sky Library layer on SkyCache - dual access open knowledge. "
                "Legal open texts only. Online portal + offline packs."
            ),
        }

    @app.get("/api/capabilities")
    async def api_capabilities() -> dict[str, Any]:
        matrix = build_capability_matrix(
            legal_rf_mode=settings.legal_rf_mode,
            sim_mode=settings.sim_mode,
            amateur_license_affirmed=settings.amateur_license_affirmed,
            nexus_enabled=settings.nexus_enabled,
            skybrary_works=skybrary.count(),
        )
        return matrix.to_dict()

    @app.post("/api/admin/open-fetch")
    async def admin_open_fetch(request: Request) -> dict[str, Any]:
        """Allowlisted open HTTPS fetch (PIN). Body: {url, license, title?, id?}."""
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        body = await request.json()
        url = str(body.get("url") or "")
        license_name = str(body.get("license") or "")
        from skycache.models import SourceSpec
        from skycache.skybrary.license_gate import assert_license_allowed

        try:
            assert_license_allowed(license_name)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        source = SourceSpec(
            plugin="open_http_import",
            uri=url,
            options={
                "license": license_name,
                "title": body.get("title") or "Open import",
                "id": body.get("id") or "open-import",
                "hosts_file": settings.open_fetch_hosts_file or "",
            },
        )
        result = runner.run(source)
        return result.model_dump(mode="json")

    @app.get("/api/skybrary/profiles")
    async def skybrary_profiles() -> list[dict[str, Any]]:
        return list_profiles()

    @app.post("/api/admin/skybrary/pack")
    async def admin_skybrary_pack(request: Request) -> dict[str, Any]:
        """Build a size-bounded USB kit under data/packs/ (PIN). Body: {profile, out?}."""
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        profile_id = str(body.get("profile") or "all-open-small").strip()
        out_raw = body.get("out")
        out_arg = str(out_raw).strip() if out_raw else None
        try:
            out_dir = resolve_pack_out_dir(settings.data_dir, profile_id, out_arg)
            meta = build_pack_from_profile(
                skybrary,
                profile_id,
                content_dir=settings.content_dir,
                out_dir=out_dir,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return meta

    @app.get("/api/onboarding")
    async def api_onboarding() -> dict[str, Any]:
        from skycache.first_boot import (
            capabilities_summary_dict,
            is_first_boot_done,
            read_first_boot_state,
        )
        from skycache.skybrary.catalog import SkybraryCatalog

        works = 0
        try:
            _sky = SkybraryCatalog(settings.skybrary_db_path)
            works = _sky.count()
            _sky.close()
        except Exception:  # noqa: BLE001
            pass

        cap = capabilities_summary_dict(
            legal_rf_mode=settings.legal_rf_mode,
            sim_mode=settings.sim_mode,
            amateur_license_affirmed=settings.amateur_license_affirmed,
            skybrary_works=works,
        )
        enabled_n = (cap.get("summary") or {}).get("enabled", 0)
        total_n = (cap.get("summary") or {}).get("total", 0)
        fb_done = is_first_boot_done(settings.data_dir)
        fb_state = read_first_boot_state(settings.data_dir) or {}

        return {
            "steps": [
                {
                    "id": "legal",
                    "title": "Honest limits",
                    "body": NEXUS_HONEST_BANNER,
                },
                {
                    "id": "connect",
                    "title": "Connect to the hub Wi-Fi",
                    "body": (
                        f"No cell plan needed. Join SSID {settings.hotspot_ssid} "
                        "on your phone, then open this portal (captive page or hub address)."
                    ),
                },
                {
                    "id": "phone_demo",
                    "title": "Save demo texts to this phone",
                    "body": (
                        "Open Library -> Save demos to this phone. Downloads a zip of three "
                        "public-domain sample texts onto your device over local Wi-Fi only. "
                        "Works offline from the internet once saved."
                    ),
                },
                {
                    "id": "capabilities",
                    "title": f"Legal capabilities ({enabled_n}/{total_n} on)",
                    "body": (
                        f"Mode: {settings.legal_rf_mode}. "
                        f"{cap.get('mode_help') or ''} "
                        "Never: commercial decrypt or default satellite uplink. "
                        "Details: Admin -> capability matrix, or skycache capabilities."
                    ).strip(),
                },
                {
                    "id": "browse",
                    "title": "Browse Emergency, Health, Education first",
                    "body": "Priority classes protect critical knowledge when storage is low.",
                },
                {
                    "id": "library",
                    "title": "Skybrary Library tab",
                    "body": (
                        "Open works (public domain / open licenses) appear under Library. "
                        "Samples are curated demos - not a complete archive of all texts."
                    ),
                },
                {
                    "id": "request",
                    "title": "Request missing open content",
                    "body": "Use Request tab - fulfilled by USB mule or legal gateway pulls.",
                },
                {
                    "id": "community",
                    "title": "Local boards",
                    "body": "School, clinic, and emergency boards stay on the village mesh.",
                },
            ],
            "training_package_id": "training-maintainer-001",
            "hotspot_ssid": settings.hotspot_ssid,
            "legal_rf_mode": settings.legal_rf_mode,
            "demo_download_path": "/api/demo/pack.zip",
            "first_boot_completed": fb_done,
            "first_boot": {
                "completed": fb_done,
                "hotspot_ssid": fb_state.get("hotspot_ssid") or settings.hotspot_ssid,
                "legal_rf_mode": fb_state.get("legal_rf_mode") or settings.legal_rf_mode,
            },
            "capabilities_summary": {
                "legal_rf_mode": cap.get("legal_rf_mode"),
                "enabled": enabled_n,
                "total": total_n,
                "banned_preview": (cap.get("banned") or [])[:5],
                "banner": cap.get("honest_banner") or NEXUS_HONEST_BANNER,
            },
        }

    @app.get("/api/demo")
    async def api_demo(ensure: bool = Query(False)) -> dict[str, Any]:
        """Status of the three phone-offline demo texts on this hub."""
        from skycache.skybrary.phone_demo import demo_status_payload

        return demo_status_payload(settings, skybrary, ensure=ensure)

    @app.get("/api/demo/pack.zip")
    async def api_demo_pack_zip() -> Response:
        """One-tap zip of the three PD demos for phone Downloads (local Wi-Fi only)."""
        from skycache.skybrary.phone_demo import (
            ZIP_FILENAME,
            build_demo_zip_bytes,
            ensure_demo_texts,
        )

        ensure_demo_texts(settings, skybrary)
        try:
            data, n = build_demo_zip_bytes(settings)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        headers = {
            "Content-Disposition": f'attachment; filename="{ZIP_FILENAME}"',
            "Cache-Control": "no-store",
            "X-SkyCache-Demo-Count": str(n),
            "X-SkyCache-Honest": "local-hub-only; not-commercial-broadband",
        }
        return Response(
            content=data,
            media_type="application/zip",
            headers=headers,
        )

    @app.get("/api/demo/zero-network")
    async def api_demo_zero_network() -> dict[str, Any]:
        """How to get demos onto a phone with no Wi-Fi and no cell."""
        from skycache.skybrary.zero_network_kit import KIT_FORMAT, KIT_ZIP_NAME

        return {
            "ok": True,
            "format": KIT_FORMAT,
            "version": "zero_network_v1",
            "problem": (
                "A phone with no Wi-Fi and no cell cannot download over the air. "
                "It can still read demos if files are already on storage."
            ),
            "transfer_paths": [
                "USB / OTG cable from PC or SkyCache hub",
                "microSD card",
                "Bluetooth file send from a peer that already has the kit",
                "Pre-deploy copy before leaving connectivity",
            ],
            "open_on_phone": "READ-OFFLINE.html (works offline, file:// or Files app)",
            "download_kit_zip": "/api/demo/zero-network-kit.zip",
            "download_offline_html": "/api/demo/READ-OFFLINE.html",
            "cli": "skycache skybrary zero-network-kit --out ./kit --zip",
            "kit_zip_name": KIT_ZIP_NAME,
            "honest": (
                "Zero network to read. Physical or prior transfer only. "
                "Not free commercial broadband. Three PD samples only."
            ),
        }

    @app.get("/api/demo/READ-OFFLINE.html")
    async def api_demo_offline_html() -> Response:
        """Single-file offline reader (copy via USB/BT/SD; no network to read)."""
        from skycache.skybrary.zero_network_kit import HTML_NAME, build_offline_reader_html

        body = build_offline_reader_html()
        return Response(
            content=body.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{HTML_NAME}"',
                "Cache-Control": "no-store",
                "X-SkyCache-Honest": "zero-network-reader; not-commercial-broadband",
            },
        )

    @app.get("/api/demo/zero-network-kit.zip")
    async def api_demo_zero_network_kit_zip() -> Response:
        """Full zero-network kit zip for USB/BT/SD load onto radios-off phones."""
        from skycache.skybrary.zero_network_kit import (
            KIT_ZIP_NAME,
            build_zero_network_zip_bytes,
        )

        data, meta = build_zero_network_zip_bytes()
        headers = {
            "Content-Disposition": f'attachment; filename="{KIT_ZIP_NAME}"',
            "Cache-Control": "no-store",
            "X-SkyCache-Kit-Works": str(meta.get("work_count", 0)),
            "X-SkyCache-Honest": "zero-network-kit; usb-sd-bt-predeploy; not-commercial-broadband",
        }
        return Response(content=data, media_type="application/zip", headers=headers)

    @app.get("/api/nexus/mesh")
    async def nexus_mesh() -> dict[str, Any]:
        return mesh.status()

    @app.get("/api/nexus/gateway")
    async def nexus_gateway() -> dict[str, Any]:
        return gateway.snapshot()

    @app.get("/api/nexus/gateway/presets")
    async def nexus_gateway_presets() -> dict[str, Any]:
        from skycache.nexus.gateway_presets import list_presets

        return {
            "presets": list_presets(),
            "legal": (
                "Open-mirror hints only. Fetches still use allowlist / operator gates. "
                "No commercial decrypt."
            ),
        }

    @app.get("/api/nexus/gateway/receipts")
    async def nexus_gateway_receipts(
        limit: int = Query(50, ge=1, le=500),
    ) -> dict[str, Any]:
        """Local 'what got pulled' receipts (no cloud, no PII)."""
        from skycache.nexus.gateway_presets import PullReceiptLog

        path = settings.nexus_dir / "gateway-receipts.json"
        log = PullReceiptLog(path)
        return {
            "receipts": log.list_recent(limit),
            "summary": log.summary(),
        }

    @app.post("/api/admin/gateway/quota")
    async def admin_gateway_quota(request: Request) -> dict[str, Any]:
        """Set daily fair-share gateway quota (MB). PIN-gated."""
        pin = request.headers.get("X-Admin-Pin")
        require_admin_pin(settings.admin_pin, pin)
        body = await request.json()
        mb = int(body.get("daily_quota_mb") or body.get("mb") or 0)
        if mb < 0 or mb > 100_000:
            raise HTTPException(400, "daily_quota_mb must be 0 - 100000")
        gateway.set_daily_quota_mb(mb)
        return {
            "ok": True,
            "daily_quota_mb": mb,
            "daily_quota_bytes": gateway.status.daily_quota_bytes,
            "snapshot": gateway.snapshot(),
        }

    @app.get("/api/licenses/export")
    async def licenses_export_html() -> Response:
        """Printable license inventory (Save as PDF from browser)."""
        html = licenses.report_html(node_id=node_id, version=__version__)
        return Response(content=html, media_type="text/html; charset=utf-8")

    @app.get("/api/nexus/fabric")
    async def nexus_fabric() -> dict[str, Any]:
        return {
            **fabric.status(),
            "gossip_preview": {
                "node_id": node_id,
                "manifest_count": len(fabric.local_manifest()),
            },
        }

    @app.get("/api/ops/local")
    async def ops_local() -> dict[str, Any]:
        """Privacy-preserving local metrics (disk, power, peers, bit-rot). No cloud."""
        from skycache.ops.local_metrics import local_ops_snapshot

        sky_n = None
        try:
            sky_n = skybrary.count()
        except Exception:  # noqa: BLE001
            sky_n = None
        # MeshAgent exposes underlying MeshFabric for peer counts
        mesh_fabric = getattr(mesh, "fabric", mesh)
        return local_ops_snapshot(settings, mesh=mesh_fabric, sky_count=sky_n)

    @app.get("/api/ops/status")
    async def ops_ops_api_status() -> dict[str, Any]:
        """Local Ops status + doctor (v1.16). Fleet heartbeat remains default OFF."""
        from skycache.ops.local_ops import ops_doctor, ops_status

        doc = ops_doctor(data_dir=settings.data_dir)
        st = ops_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/integrity/last")
    async def integrity_last() -> dict[str, Any]:
        """Last recorded bit-rot report (if any)."""
        from skycache.health.bitrot_schedule import load_last_report, schedule_status

        last = load_last_report(settings.data_dir)
        return {
            "last": last,
            "schedule": schedule_status(settings.data_dir),
            "legal": "Open package integrity only",
        }

    @app.get("/api/rx/status")
    async def rx_status() -> dict[str, Any]:
        """SDR/SatDump doctor + station + signal snapshot (live FTA ops)."""
        from skycache.rx.doctor import rx_doctor_report
        from skycache.rx.station import load_station

        doc = rx_doctor_report(data_dir=settings.data_dir)
        return {
            **doc,
            "signal": {
                "quality": signal.snapshot.quality,
                "snr_db": signal.snapshot.snr_db,
                "last_plugin": signal.snapshot.last_plugin,
                "message": signal.snapshot.message,
                "last_pass_at": (
                    signal.snapshot.last_pass_at.isoformat().replace("+00:00", "Z")
                    if signal.snapshot.last_pass_at
                    else None
                ),
            },
            "station": load_station(settings.data_dir),
        }

    @app.get("/api/rx/ops")
    async def rx_ops_api_status() -> dict[str, Any]:
        """RX Ops (v1.17): doctor go flags + station/duty status. Receive-only FTA."""
        from skycache.ops.rx_ops import rx_ops_doctor, rx_ops_status

        doc = rx_ops_doctor(data_dir=settings.data_dir)
        st = rx_ops_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/rx/recipes")
    async def rx_recipes() -> list[dict[str, Any]]:
        from skycache.rx.recipes import list_recipes

        return list_recipes()

    @app.get("/api/rx/passes")
    async def rx_passes(
        hours: float = Query(24.0, ge=1.0, le=168.0),
        min_elev: float = Query(15.0, ge=0.0, le=90.0),
    ) -> dict[str, Any]:
        from skycache.rx.pass_plan import predict_passes
        from skycache.rx.station import load_station

        st = load_station(settings.data_dir)
        if not st:
            raise HTTPException(
                400,
                "Configure station first: skycache rx station --lat LAT --lon LON",
            )
        return predict_passes(
            lat=float(st["lat"]),
            lon=float(st["lon"]),
            alt_m=float(st.get("alt_m") or 0.0),
            hours=float(hours),
            min_elevation=float(min_elev),
            data_dir=settings.data_dir,
        )

    @app.get("/api/rx/field-log")
    async def rx_field_log(limit: int = Query(40, ge=1, le=200)) -> dict[str, Any]:
        from skycache.rx.field_log import list_field_log

        return {
            "entries": list_field_log(settings.data_dir, limit=limit),
            "legal": "FTA / open RX field notes only",
        }

    @app.post("/api/rx/import")
    async def rx_import(payload: dict[str, Any]) -> dict[str, Any]:
        """Ingest a SatDump product path (admin PIN for remote callers)."""
        pin = None
        # optional pin if provided via body
        if payload.get("admin_pin"):
            pin = str(payload.get("admin_pin"))
            require_admin_pin(settings.admin_pin, pin)
        path = (payload.get("path") or "").strip()
        if not path:
            raise HTTPException(400, "path required")
        from skycache.rx.product_watch import ingest_product

        rep = ingest_product(
            Path(path),
            settings,
            recipe=str(payload.get("recipe") or "product_import"),
            satellite=str(payload.get("satellite") or ""),
        )
        if rep.get("ok"):
            signal.update(
                quality=0.7,
                plugin="satdump_weather",
                message=f"Ingested FTA product {rep.get('package_id') or path}",
            )
        return rep

    @app.get("/api/rx/schedule")
    async def rx_schedule(
        hours: float = Query(24.0, ge=1.0, le=168.0),
        min_elev: float = Query(15.0, ge=0.0, le=90.0),
        limit: int = Query(40, ge=1, le=100),
    ) -> dict[str, Any]:
        """Pass Autopilot schedule: passes + recipe binding + SatDump sketches."""
        from skycache.rx.schedule import build_schedule

        return build_schedule(
            settings.data_dir,
            hours=float(hours),
            min_elevation=float(min_elev),
            limit=int(limit),
        )

    @app.get("/api/rx/duty")
    async def rx_duty() -> dict[str, Any]:
        """Station duty board: arm state + next pass countdown."""
        from skycache.rx.schedule import duty_status

        return duty_status(settings.data_dir)

    @app.get("/api/rx/arm")
    async def rx_arm_get() -> dict[str, Any]:
        from skycache.rx.schedule import load_arm

        return load_arm(settings.data_dir) or {"armed": False, "schema": "skycache.rx.arm.v1"}

    @app.post("/api/rx/arm")
    async def rx_arm_post(payload: dict[str, Any]) -> dict[str, Any]:
        """Arm or disarm station for upcoming FTA passes."""
        from skycache.rx.schedule import clear_arm, save_arm

        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        if payload.get("disarm") or payload.get("armed") is False:
            return clear_arm(settings.data_dir)
        recipes = payload.get("recipes")
        if isinstance(recipes, str):
            recipes = [r.strip() for r in recipes.split(",") if r.strip()]
        elif not isinstance(recipes, list):
            recipes = None
        return save_arm(
            settings.data_dir,
            hours=float(payload.get("hours") or 12.0),
            min_elevation=float(payload.get("min_elev") or payload.get("min_elevation") or 15.0),
            products_dir=payload.get("products_dir") or None,
            auto_field_log=bool(payload.get("auto_field_log", True)),
            recipes=recipes,
        )

    @app.get("/api/handoff/status")
    async def handoff_status() -> dict[str, Any]:
        """Phone path readiness + join card locations (local transfer only)."""
        from skycache.capabilities.handoff_ops import handoff_doctor

        doc = handoff_doctor(data_dir=settings.data_dir)
        join_html = settings.handoff_dir / "join.html"
        return {
            **doc,
            "join_card": {
                "html": "/handoff/join.html" if join_html.is_file() else None,
                "qr": "/handoff/join-qr.svg"
                if (settings.handoff_dir / "join-qr.svg").is_file()
                else None,
                "index": "/handoff/",
            },
        }

    @app.post("/api/handoff/join-card")
    async def handoff_join_card(payload: dict[str, Any]) -> dict[str, Any]:
        """Write join.html + QR under data/handoff (admin PIN optional)."""
        from skycache.capabilities.handoff_ops import write_join_card

        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        portal = str(payload.get("portal_url") or "http://10.42.0.1:8080/")
        ssid = str(payload.get("ssid") or settings.hotspot_ssid or "SkyCache-Village")
        rep = write_join_card(
            settings.handoff_dir,
            portal_url=portal,
            ssid=ssid,
            node_name=str(payload.get("node_name") or settings.node_id or "village-hub"),
            data_dir=settings.data_dir,
        )
        # also under join/ subdir for exports
        write_join_card(
            settings.handoff_dir / "join",
            portal_url=portal,
            ssid=ssid,
            node_name=str(payload.get("node_name") or settings.node_id or "village-hub"),
            data_dir=settings.data_dir,
        )
        return rep

    @app.post("/api/handoff/export")
    async def handoff_export(payload: dict[str, Any]) -> dict[str, Any]:
        """One-shot mule export + join card (admin PIN optional)."""
        from skycache.capabilities.handoff_ops import export_phone_handoff

        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        pkgs = payload.get("packages")
        if isinstance(pkgs, str):
            pkgs = [p.strip() for p in pkgs.split(",") if p.strip()]
        elif not isinstance(pkgs, list):
            pkgs = None
        return export_phone_handoff(
            data_dir=settings.data_dir,
            package_ids=pkgs,
            limit=int(payload.get("limit") or 20),
            portal_url=str(payload.get("portal_url") or "http://10.42.0.1:8080/"),
            ssid=str(payload.get("ssid") or settings.hotspot_ssid or "SkyCache-Village"),
            include_join_card=bool(payload.get("include_join_card", True)),
            zip_bundle=bool(payload.get("zip", True)),
        )

    @app.get("/api/gateway/status")
    async def gateway_api_status() -> dict[str, Any]:
        """Gateway doctor + status (open content only, fair-share quota)."""
        from skycache.nexus.gateway_ops import gateway_doctor, gateway_status

        doc = gateway_doctor(data_dir=settings.data_dir, sim=True)
        st = gateway_status(data_dir=settings.data_dir, sim=True)
        return {**st, "doctor": doc}

    @app.get("/api/gateway/presets")
    async def gateway_api_presets() -> dict[str, Any]:
        from skycache.nexus.gateway_ops import HONEST
        from skycache.nexus.gateway_presets import list_presets

        return {"presets": list_presets(), "banner": HONEST}

    @app.post("/api/gateway/pull-preset")
    async def gateway_api_pull_preset(payload: dict[str, Any]) -> dict[str, Any]:
        """Preset pull with passport (default dry-run; set dry_run=false + sim or live)."""
        from skycache.nexus.gateway_ops import pull_preset

        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        preset_id = str(payload.get("preset_id") or "").strip()
        if not preset_id:
            return {"ok": False, "error": "preset_id required"}
        return pull_preset(
            preset_id,
            data_dir=settings.data_dir,
            dry_run=bool(payload.get("dry_run", True)),
            sim=bool(payload.get("sim", False)),
            force=bool(payload.get("force", False)),
        )

    @app.get("/api/gateway/receipts")
    async def gateway_api_receipts(limit: int = 50) -> dict[str, Any]:
        from skycache.nexus.gateway_ops import gateway_receipts

        return gateway_receipts(data_dir=settings.data_dir, limit=int(limit or 50))

    @app.get("/api/capabilities/status")
    async def capabilities_ops_api_status() -> dict[str, Any]:
        """Capabilities doctor + matrix snapshot (local only)."""
        from skycache.ops.capabilities_ops import capabilities_doctor, capabilities_status

        doc = capabilities_doctor(data_dir=settings.data_dir, sim=bool(settings.sim_mode))
        st = capabilities_status(data_dir=settings.data_dir, sim=bool(settings.sim_mode))
        return {**st, "doctor": doc}

    @app.get("/api/report/status")
    async def report_ops_api_status() -> dict[str, Any]:
        """Node Report Ops (v1.18): partner readiness passport rollup."""
        from skycache.ops.report_ops import report_doctor, report_status

        doc = report_doctor(data_dir=settings.data_dir)
        st = report_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/corpus/status")
    async def corpus_ops_api_status() -> dict[str, Any]:
        """Corpus Ops (v1.19): legal bulk corpus doctor + scale snapshot."""
        from skycache.skybrary.corpus_ops import corpus_doctor, corpus_status

        doc = corpus_doctor(data_dir=settings.data_dir)
        st = corpus_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/seal/status")
    async def seal_ops_api_status() -> dict[str, Any]:
        """Seal Ops (v1.20): golden Pi fleet doctor + host/plan snapshot."""
        from skycache.ops.seal_ops import seal_doctor, seal_status

        doc = seal_doctor()
        st = seal_status()
        return {"doctor": doc, **st}

    @app.get("/api/partner/status")
    async def partner_ops_api_status() -> dict[str, Any]:
        """Partner Ops (v1.21): institutional pilot readiness doctor + snapshot."""
        from skycache.ops.partner_ops import partner_doctor, partner_status

        doc = partner_doctor(data_dir=settings.data_dir)
        st = partner_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/dual-radio/status")
    async def dual_radio_ops_api_status() -> dict[str, Any]:
        """Dual Radio Ops (v1.22): board matrix readiness doctor + snapshot."""
        from skycache.ops.dual_radio_ops import dual_radio_doctor, dual_radio_status

        doc = dual_radio_doctor(data_dir=settings.data_dir)
        st = dual_radio_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/library/status")
    async def library_ops_api_status() -> dict[str, Any]:
        """Library Ops (v1.24): dual-access Skybrary catalog doctor + snapshot."""
        from skycache.ops.library_ops import library_doctor, library_status

        doc = library_doctor(data_dir=settings.data_dir)
        st = library_status(data_dir=settings.data_dir)
        return {"doctor": doc, **st}

    @app.get("/api/licenses/status")
    async def licenses_ops_api_status() -> dict[str, Any]:
        """Licenses doctor + inventory snapshot (local only)."""
        from skycache.ops.licenses_ops import licenses_doctor, licenses_status

        doc = licenses_doctor(data_dir=settings.data_dir)
        st = licenses_status(data_dir=settings.data_dir)
        return {**st, "doctor": doc}

    @app.get("/api/power/status")
    async def power_ops_api_status() -> dict[str, Any]:
        """Power doctor + guidance snapshot (local only)."""
        from skycache.ops.power_ops import power_doctor, power_status

        doc = power_doctor(data_dir=settings.data_dir)
        st = power_status(data_dir=settings.data_dir)
        return {**st, "doctor": doc}

    @app.get("/api/disaster/status")
    async def disaster_api_status() -> dict[str, Any]:
        """Disaster drill doctor + last lab receipt (local only)."""
        from skycache.ops.disaster_ops import disaster_doctor
        import json as _json

        doc = disaster_doctor(data_dir=settings.data_dir)
        last_path = settings.data_dir / "ops" / "disaster-drill-last.json"
        last = None
        if last_path.is_file():
            try:
                last = _json.loads(last_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                last = None
        return {**doc, "last_lab": last}

    @app.post("/api/disaster/run")
    async def disaster_api_run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from skycache.ops.disaster_ops import disaster_run

        payload = payload or {}
        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        return disaster_run(
            data_dir=settings.data_dir,
            nodes=int(payload.get("nodes") or 3),
            keep=bool(payload.get("keep", False)),
        )

    @app.post("/api/disaster/closeout")
    async def disaster_api_closeout(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from skycache.ops.disaster_ops import disaster_closeout

        payload = payload or {}
        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        return disaster_closeout(data_dir=settings.data_dir)

    @app.get("/api/integrity/status")
    async def integrity_api_status() -> dict[str, Any]:
        """Integrity doctor + last bit-rot report (local only)."""
        from skycache.ops.integrity_ops import integrity_doctor
        from skycache.health.bitrot_schedule import load_last_report

        doc = integrity_doctor(data_dir=settings.data_dir)
        return {**doc, "last_report": load_last_report(settings.data_dir)}

    @app.post("/api/integrity/verify")
    async def integrity_api_verify(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from skycache.ops.integrity_ops import integrity_verify

        payload = payload or {}
        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        return integrity_verify(
            data_dir=settings.data_dir,
            record=bool(payload.get("record", True)),
        )

    @app.get("/api/federation/status")
    async def federation_api_status() -> dict[str, Any]:
        """Federation doctor + local gossip stats (open content only)."""
        from skycache.nexus.federation_ops import federation_doctor, federation_status

        doc = federation_doctor(data_dir=settings.data_dir)
        st = federation_status(data_dir=settings.data_dir)
        return {**st, "doctor": doc}

    @app.post("/api/federation/export-gossip")
    async def federation_api_export(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from skycache.nexus.federation_ops import export_gossip

        payload = payload or {}
        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        out = settings.nexus_dir / "federation-gossip.json"
        compact = payload.get("compact")
        if compact is not None:
            compact = bool(compact)
        return export_gossip(
            out,
            data_dir=settings.data_dir,
            compact=compact,
            max_tier=int(payload["max_tier"]) if payload.get("max_tier") is not None else None,
        )

    @app.get("/api/village-day/status")
    async def village_day_api_status() -> dict[str, Any]:
        """Weekend stand-up doctor + readiness (local only)."""
        from skycache.ops.village_day_ops import village_day_doctor, village_day_readiness

        doc = village_day_doctor(data_dir=settings.data_dir, sim=True)
        ready = village_day_readiness(data_dir=settings.data_dir, sim=True)
        return {**ready, "doctor": doc}

    @app.post("/api/village-day/readiness")
    async def village_day_api_readiness(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from skycache.ops.village_day_ops import village_day_readiness

        payload = payload or {}
        if payload.get("admin_pin"):
            require_admin_pin(settings.admin_pin, str(payload.get("admin_pin")))
        return village_day_readiness(data_dir=settings.data_dir, sim=True)

    @app.post("/api/nexus/request")
    async def nexus_request(payload: dict[str, str]) -> dict[str, str]:
        """Queue an open-content package request (local + DTN)."""
        package_id = (payload.get("package_id") or "").strip()
        if not package_id:
            raise HTTPException(400, "package_id required")
        priority = (payload.get("priority_class") or "education").strip()
        bid = gateway.request_package(package_id, priority_class=priority)
        return {"bundle_id": bid, "status": "queued", "package_id": package_id}

    @app.get("/api/categories")
    async def categories() -> list[dict[str, str]]:
        return [
            {"id": "emergency", "icon": "alert"},
            {"id": "health", "icon": "health"},
            {"id": "education", "icon": "education"},
            {"id": "agriculture", "icon": "farm"},
            {"id": "weather", "icon": "weather"},
            {"id": "maps", "icon": "maps"},
            {"id": "general", "icon": "library"},
        ]

    @app.get("/api/packages")
    async def list_packages(
        category: str | None = None,
        lang: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        records = catalog.list_packages(priority_class=category, lang=lang, q=q)
        out: list[dict[str, Any]] = []
        for rec in records:
            p = rec.package
            out.append(
                {
                    "id": p.id,
                    "kind": p.kind,
                    "priority_class": p.priority_class.value,
                    "title": p.title,
                    "summary": p.summary,
                    "languages": p.languages,
                    "received_at": p.received_at.isoformat(),
                    "freshness_hours": p.freshness_hours,
                    "size_bytes": p.size_bytes,
                    "tags": p.tags,
                    "icon": p.icon or p.priority_class.value,
                    "score": rec.score,
                    "age_hours": round(rec.age_hours, 2),
                    "is_stale": rec.is_stale,
                    "pinned": p.pinned,
                    "files": [f.model_dump() for f in p.files],
                    "license": p.license,
                }
            )
        return out

    @app.get("/api/packages/{package_id}")
    async def get_package(package_id: str) -> dict[str, Any]:
        rec = catalog.get(package_id)
        if not rec:
            raise HTTPException(404, "Package not found")
        p = rec.package
        return {
            "id": p.id,
            "kind": p.kind,
            "priority_class": p.priority_class.value,
            "title": p.title,
            "summary": p.summary,
            "languages": p.languages,
            "received_at": p.received_at.isoformat(),
            "files": [f.model_dump() for f in p.files],
            "age_hours": rec.age_hours,
            "is_stale": rec.is_stale,
            "score": rec.score,
            "license": p.license,
            "source": p.source.model_dump(),
        }

    @app.get("/content/{package_id}/{file_path:path}")
    async def content_file(
        package_id: str,
        file_path: str,
        download: bool = Query(False),
    ) -> FileResponse:
        rec = catalog.get(package_id)
        if not rec:
            raise HTTPException(404, "Package not found")
        base = Path(rec.path).resolve()
        target = (base / file_path).resolve()
        if not str(target).startswith(str(base)) or not target.is_file():
            raise HTTPException(404, "File not found")
        # ?download=1 -> force Save on phones (attachment disposition)
        if download:
            name = target.name
            return FileResponse(
                target,
                filename=name,
                content_disposition_type="attachment",
            )
        return FileResponse(target)

    @app.get("/api/plugins")
    async def plugins() -> list[dict[str, object]]:
        return runner.list_plugins()

    @app.get("/api/admin/status")
    async def admin_status(request: Request) -> dict[str, Any]:
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        total, used, free = disk_usage(settings.content_dir)
        pct = power.battery_percent()
        mode = mode_from_soc(pct)
        return {
            "version": __version__,
            "sim_mode": settings.sim_mode,
            "power": {
                "percent": pct,
                "mode": mode.value,
                "run_live_rx": should_run_live_rx(mode),
                "on_ac": power.is_on_ac(),
            },
            "disk": {"total": total, "used": used, "free": free},
            "packages": catalog.count(),
            "content_bytes": catalog.total_size(),
            "signal": {
                "quality": signal.snapshot.quality,
                "snr_db": signal.snapshot.snr_db,
                "last_plugin": signal.snapshot.last_plugin,
                "message": signal.snapshot.message,
                "last_pass_at": (
                    signal.snapshot.last_pass_at.isoformat()
                    if signal.snapshot.last_pass_at
                    else None
                ),
            },
            "mesh": mesh.status(),
            "dtn_pending": len(dtn.list_pending()),
            "nexus_dtn": nexus_dtn.stats(),
            "fabric": fabric.status(),
            "gateway": gateway.snapshot(),
            "node_id": node_id,
            "disaster_mode": mesh.fabric.disaster_mode,
            "plugins": runner.list_plugins(),
            "hotspot_ssid": settings.hotspot_ssid,
            "legal": NEXUS_HONEST_BANNER,
            "spectrum": compliance_report(),
            "power_map": fabric_power_map(
                mesh.fabric,
                local_battery=pct,
                local_solar=bool(power.is_on_ac()),
            ),
            "traffic": traffic_monitor(nexus_dtn, gateway),
            "control_plane": control.status(),
            "licenses": licenses.report(),
            "boards_recent": boards.list_posts(limit=5),
            "top_rated": ratings.top(limit=5),
        }

    @app.post("/api/admin/disaster")
    async def admin_disaster(request: Request) -> dict[str, Any]:
        """Enable/disable disaster mode (elevates emergency/health replication)."""
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        body = await request.json()
        enabled = bool(body.get("enabled", True))
        mesh.fabric.disaster_mode = enabled
        if enabled:
            nexus_dtn.enqueue(
                kind=BundleKind.MESSAGE,
                priority_class="emergency",
                origin_node=node_id,
                payload={
                    "alert": "disaster_mode",
                    "text": "Coordinate via local mesh - store-and-forward, not commercial internet",
                },
            )
        mesh.fabric.save()
        return {
            "disaster_mode": mesh.fabric.disaster_mode,
            "legal": NEXUS_HONEST_BANNER,
        }

    @app.post("/api/admin/gateway/pull")
    async def admin_gateway_pull(request: Request) -> dict[str, Any]:
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        results = gateway.schedule_pulls()
        return {"pulls": results, "gateway": gateway.snapshot()}

    @app.post("/api/admin/ingest")
    async def admin_ingest(request: Request, path: str = Query(...)) -> dict[str, Any]:
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        pkgs = content.ingest_path(Path(path))
        return {"ingested": [p.id for p in pkgs]}

    @app.post("/api/admin/pipeline")
    async def admin_pipeline(request: Request) -> dict[str, Any]:
        """Run a decoder plugin (PIN required). Body: {plugin, uri?, options?}."""
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        body = await request.json()
        plugin = str(body.get("plugin") or "")
        if not plugin:
            raise HTTPException(400, "plugin required")
        from skycache.models import SourceSpec

        source = SourceSpec(
            plugin=plugin,
            uri=str(body.get("uri") or ""),
            options=dict(body.get("options") or {}),
        )
        if plugin == "sim_file" and "all" not in source.options:
            source.options["all"] = True
        result = runner.run(source)
        if result.success and result.metadata.get("quality") is not None:
            signal.update(
                quality=float(result.metadata["quality"]),
                plugin=plugin,
                message=result.message,
            )
        elif result.success:
            signal.update(plugin=plugin, message=result.message)
        return result.model_dump(mode="json")

    @app.post("/api/admin/drop-scan")
    async def admin_drop_scan(request: Request) -> dict[str, Any]:
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        from skycache.ingest.drop_watch import DropWatcher

        watcher = DropWatcher(settings)
        ids = watcher.scan_once()
        return {"processed": ids, "incoming": str(watcher.incoming)}

    @app.post("/api/admin/handoff")
    async def admin_handoff(request: Request) -> dict[str, Any]:
        """One-button phone/USB handoff export (file mule; not live BLE).

        Body optional: {packages?: string[], limit?: int}.
        Writes under data/handoff/ and serves at /handoff/<bundle>/.
        """
        require_admin_pin(settings.admin_pin, request.headers.get("x-admin-pin"))
        body: dict[str, Any] = {}
        try:
            parsed = await request.json()
            if isinstance(parsed, dict):
                body = parsed
        except Exception:
            body = {}
        limit = int(body.get("limit") or 20)
        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200
        raw_ids = body.get("packages")
        if isinstance(raw_ids, list) and raw_ids:
            package_ids = [str(x).strip() for x in raw_ids if str(x).strip()]
        elif isinstance(raw_ids, str) and raw_ids.strip():
            package_ids = [x.strip() for x in raw_ids.split(",") if x.strip()]
        else:
            package_ids = [
                p.name for p in sorted(settings.content_dir.iterdir()) if p.is_dir()
            ][:limit]
        if not package_ids:
            raise HTTPException(400, "No packages available to export")
        settings.handoff_dir.mkdir(parents=True, exist_ok=True)
        bundle = export_handoff_bundle(
            dtn=nexus_dtn,
            content_dir=settings.content_dir,
            package_ids=package_ids,
            out_dir=settings.handoff_dir,
            node_id=node_id,
        )
        bundle_name = bundle.name
        url_path = f"/handoff/{bundle_name}/"
        meta_path = bundle / "handoff.json"
        packages_copied: list[str] = list(package_ids)
        if meta_path.is_file():
            try:
                import json as _json

                meta = _json.loads(meta_path.read_text(encoding="utf-8-sig"))
                if isinstance(meta.get("packages"), list):
                    packages_copied = [str(x) for x in meta["packages"]]
            except Exception:
                pass
        return {
            "ok": True,
            "path": str(bundle.resolve()),
            "bundle_name": bundle_name,
            "url_path": url_path,
            "packages": packages_copied,
            "package_count": len(packages_copied),
            "legal": (
                "Open content handoff only. User-consented local transfer. "
                "Not commercial broadband tethering. File bridge - not live BLE stack."
            ),
        }

    @app.post("/api/messages")
    async def post_message(payload: dict[str, str]) -> dict[str, str]:
        """Community notice queue (local store-and-forward)."""
        author = (payload.get("author") or "anonymous").strip()
        subject = (payload.get("subject") or "notice").strip()
        body = (payload.get("body") or "").strip()
        if not body:
            raise HTTPException(400, "body required")
        msg = dtn.enqueue(author, subject, body)
        return {"id": msg.id, "status": "queued"}

    @app.get("/api/messages")
    async def list_messages() -> list[dict[str, Any]]:
        return [
            {
                "id": m.id,
                "created_at": m.created_at,
                "author": m.author,
                "subject": m.subject,
                "body": m.body,
            }
            for m in dtn.list_pending()[-50:]
        ]

    # Captive portal plain responses for some probes that need 200
    @app.get("/ncsi.txt")
    async def ncsi() -> Response:
        return RedirectResponse("/", status_code=302)

    @app.get("/hotspot-detect.html")
    async def apple_captive() -> RedirectResponse:
        return RedirectResponse("/", status_code=302)

    @app.get("/generate_204")
    async def android_captive() -> RedirectResponse:
        return RedirectResponse("/", status_code=302)

    return app


def run_server(settings: Settings) -> None:
    import uvicorn

    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())
