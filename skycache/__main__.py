"""SkyCache CLI entry point (includes Nexus fabric commands)."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from skycache import __version__
from skycache.config import NEXUS_HONEST_BANNER, Settings, package_root, samples_dir
from skycache.db.catalog import Catalog
from skycache.health.power import get_power_provider, mode_from_soc
from skycache.ingest.drop_watch import DropWatcher
from skycache.ingest.normalizer import ContentManager
from skycache.models import SourceSpec
from skycache.packages.builder import create_package, validate_package_dir
from skycache.pipelines.runner import PipelineRunner
from skycache.policy.prioritizer import disk_usage


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_init(args: argparse.Namespace) -> int:
    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    # Ensure drop folders exist for USB ingest
    DropWatcher(settings)
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    if args.load_samples:
        pkgs = content.load_samples(samples_dir())
        print(f"Loaded {len(pkgs)} sample packages into {settings.content_dir}")
    else:
        print(f"Initialized data dir at {settings.data_dir}")
    print(f"Drop folder: {settings.data_dir / 'drop' / 'incoming'}")
    catalog.close()
    return 0


def cmd_first_boot(args: argparse.Namespace) -> int:
    """Golden-path first-boot: PIN, SSID, legal_rf_mode, samples, capabilities."""
    from skycache.config import NEXUS_HONEST_BANNER
    from skycache.first_boot import (
        DEFAULT_LEGAL_RF_MODE,
        DEFAULT_PIN,
        DEFAULT_SSID,
        FirstBootConfig,
        apply_first_boot,
        interactive_prompts,
        is_first_boot_done,
    )

    data_dir = Path(args.data_dir)
    print(NEXUS_HONEST_BANNER)

    if is_first_boot_done(data_dir) and not args.force:
        print(f"First-boot already completed under {data_dir}.")
        print("Re-run with --force to reconfigure, or delete data/first_boot.json.")
        return 0

    if args.non_interactive or args.yes:
        pin = args.pin or ""
        if not pin or pin == DEFAULT_PIN:
            print(
                "Non-interactive first-boot requires --pin with a non-default 4 - 8 digit PIN "
                f"(not {DEFAULT_PIN})."
            )
            return 2
        cfg = FirstBootConfig(
            admin_pin=pin,
            hotspot_ssid=args.ssid or DEFAULT_SSID,
            legal_rf_mode=args.legal_rf_mode or DEFAULT_LEGAL_RF_MODE,
            amateur_license_affirmed=bool(args.amateur_affirmed),
            load_samples=not args.no_samples,
            load_skybrary=not args.no_skybrary,
            node_id=args.node_id or "",
            language_hint=args.lang or "en",
        )
    else:
        try:
            cfg = interactive_prompts(
                defaults=FirstBootConfig(
                    admin_pin=args.pin or DEFAULT_PIN,
                    hotspot_ssid=args.ssid or DEFAULT_SSID,
                    legal_rf_mode=args.legal_rf_mode or DEFAULT_LEGAL_RF_MODE,
                    amateur_license_affirmed=bool(args.amateur_affirmed),
                    load_samples=not args.no_samples,
                    load_skybrary=not args.no_skybrary,
                    node_id=args.node_id or "",
                    language_hint=args.lang or "en",
                )
            )
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 130

    env_path = Path(args.env_file) if args.env_file else None
    result = apply_first_boot(
        data_dir,
        cfg,
        env_path=env_path,
        force=bool(args.force),
        sim_mode=bool(args.sim),
    )
    for msg in result.messages:
        print(msg)
    for err in result.errors:
        print(f"ERROR: {err}", file=sys.stderr)
    if not result.ok:
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("")
        print("Next steps:")
        print(f"  1. Point systemd EnvironmentFile= at {result.env_path}")
        print("     (Linux: source the env file, or set EnvironmentFile= in the unit)")
        print(f"  2. skycache serve --data-dir {result.data_dir} [--sim]")
        print("  3. Open portal; complete PWA onboarding; match hostapd SSID to the hint")
        print("  4. skycache capabilities")
        print("Docs: docs/first-boot.md")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    settings = Settings(
        data_dir=Path(args.data_dir),
        host=args.host,
        port=args.port,
        sim_mode=args.sim,
    )
    settings.ensure_dirs()
    DropWatcher(settings)
    _setup_logging(settings.log_level)

    catalog = Catalog(settings.db_path)
    if catalog.count() == 0 and args.sim:
        content = ContentManager(settings, catalog)
        content.load_samples(samples_dir())
        print("Simulation: loaded sample packages (catalog was empty).")
    catalog.close()

    # Phone-offline path: 3 PD demos always ready for hub Wi-Fi download
    try:
        from skycache.skybrary.catalog import SkybraryCatalog
        from skycache.skybrary.phone_demo import ensure_demo_texts

        sky = SkybraryCatalog(settings.skybrary_db_path)
        demo = ensure_demo_texts(settings, sky)
        sky.close()
        if demo.get("ok"):
            print(
                f"Phone demos ready: {demo['count_ready']}/{demo['count_expected']} "
                f" -  GET /api/demo/pack.zip over hub Wi-Fi (no cell plan)."
            )
        else:
            print("WARN: phone demos not fully ready; try: skycache skybrary samples --ingest")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: phone demo ensure failed: {exc}")

    from skycache.web.app import run_server

    print(f"SkyCache Nexus {__version__}  http://{settings.host}:{settings.port}/")
    print(f"LEGAL: {NEXUS_HONEST_BANNER}")
    if settings.sim_mode:
        print("Mode: SIMULATION (no live SDR required)")
    print("Phone path: join hub Wi-Fi -> Library -> Save demos to this phone")
    run_server(settings)
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    pkgs = content.ingest_path(Path(args.path))
    for p in pkgs:
        print(f"Ingested {p.id} [{p.priority_class.value}]")
    catalog.close()
    return 0


def _parse_pipeline_options(raw: list[str] | None, plugin: str | None) -> dict:
    opts: dict = {"all": True} if plugin == "sim_file" else {}
    for item in raw or []:
        if "=" not in item:
            opts[item] = True
            continue
        key, val = item.split("=", 1)
        key = key.strip()
        val = val.strip()
        if val.lower() in {"true", "yes", "1"}:
            opts[key] = True
        elif val.lower() in {"false", "no", "0"}:
            opts[key] = False
        else:
            opts[key] = val
    return opts


def cmd_pipeline(args: argparse.Namespace) -> int:
    settings = Settings(data_dir=Path(args.data_dir), sim_mode=args.sim)
    settings.ensure_dirs()
    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog)
    runner = PipelineRunner(settings, content)
    source = SourceSpec(
        uri=args.uri or "",
        plugin=args.plugin,
        options=_parse_pipeline_options(getattr(args, "option", None), args.plugin),
    )
    result = runner.run(source)
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    catalog.close()
    return 0 if result.success else 1


def cmd_status(args: argparse.Namespace) -> int:
    settings = Settings(data_dir=Path(args.data_dir))
    catalog = Catalog(settings.db_path)
    total, used, free = disk_usage(settings.data_dir if settings.data_dir.exists() else Path("."))
    power = get_power_provider(settings.power_provider, settings.mock_battery_percent)
    pct = power.battery_percent()
    print(f"SkyCache {__version__}")
    print(f"Packages: {catalog.count()}")
    print(f"Content bytes: {catalog.total_size()}")
    print(f"Disk free: {free} / total {total}")
    print(f"Battery: {pct}% mode={mode_from_soc(pct).value}")
    print(f"Last ingest: {catalog.last_ingest()}")
    print(f"Drop incoming: {settings.data_dir / 'drop' / 'incoming'}")
    catalog.close()
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print(f"SkyCache doctor {__version__}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Package root: {package_root()}")
    print(f"Samples: {samples_dir()} exists={samples_dir().is_dir()}")
    for tool in (
        "satdump",
        "satdump_cli",
        "gr_satellites",
        "rtl_test",
        "SoapySDRUtil",
        "batctl",
        "hostapd",
        "dnsmasq",
    ):
        path = shutil.which(tool)
        print(f"  {tool}: {path or 'not on PATH (optional)'}")
    settings = Settings(data_dir=Path(args.data_dir))
    try:
        settings.validate_nexus()
        print(
            f"Nexus config: mesh_mode={settings.mesh_mode} band={settings.mesh_band} "
            f"legal_rf_mode={settings.legal_rf_mode} OK"
        )
    except ValueError as exc:
        print(f"Nexus config ERROR: {exc}")
        return 1
    print(f"Data dir: {settings.data_dir} exists={settings.data_dir.exists()}")
    drop = settings.data_dir / "drop" / "incoming"
    print(f"Drop folder: {drop} exists={drop.is_dir()}")
    # Power guidance (rough hours until ECO)
    try:
        from skycache.health.power_guidance import power_guidance

        provider = get_power_provider(settings.power_provider, settings.mock_battery_percent)
        pct = provider.battery_percent()
        mode = mode_from_soc(pct)
        g = power_guidance(pct, mode, on_ac=provider.is_on_ac())
        eco = g.get("hours_until_eco") or {}
        if eco.get("hours") is not None:
            print(f"Power: {pct}% {mode.value} - ~{eco['hours']} h until ECO (rough)")
        else:
            print(f"Power: {pct}% {mode.value} - {eco.get('message', '')}")
    except Exception as exc:  # noqa: BLE001
        print(f"Power guidance: unavailable ({exc})")
    print("Legal profile: receive-only satellite, FTA/open content, unlicensed mesh TX")
    print(NEXUS_HONEST_BANNER)
    try:
        from skycache.health.bitrot_schedule import schedule_status

        st = schedule_status(settings.data_dir)
        print(
            f"Bit-rot schedule: recorded={st.get('scheduled')} fresh={st.get('fresh')} "
            f"hint={st.get('hint')}"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Bit-rot schedule: unavailable ({exc})")
    print("Full matrix: skycache capabilities")
    print("Local ops: skycache ops status")
    print("Docs: docs/legal-pathways-rf-and-content.md  |  docs/threat-model.md")
    print("OK - core environment ready (use --sim without RF hardware).")
    return 0


def cmd_mesh_status(args: argparse.Namespace) -> int:
    from skycache.nexus.mesh import MeshFabric
    from skycache.nexus.spectrum import compliance_report

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    settings.validate_nexus()
    mesh = MeshFabric(
        data_dir=settings.data_dir,
        node_id=settings.node_id or "",
        enabled=True,
        mode=settings.mesh_mode,
        band=settings.mesh_band,
    )
    mesh.load()
    mesh.start()
    print(json.dumps(mesh.status(), indent=2))
    if args.compliance:
        print(json.dumps(compliance_report(), indent=2))
    return 0


def cmd_gateway(args: argparse.Namespace) -> int:
    """Gateway Ops (v1.8): doctor, presets, pull-preset, receipts, ethics-kit + legacy flags."""
    from skycache.nexus.dtn import DtnQueue
    from skycache.nexus.gateway import GatewayManager
    from skycache.nexus.gateway_ops import (
        gateway_doctor,
        gateway_receipts,
        gateway_status,
        pull_preset,
        write_ethics_kit,
    )
    from skycache.nexus.gateway_presets import list_presets
    from skycache.nexus.identity import load_or_create_node_id

    sub = getattr(args, "gateway_cmd", None)
    data_dir = Path(args.data_dir)
    sim = bool(getattr(args, "sim", False))

    if sub == "doctor":
        rep = gateway_doctor(data_dir=data_dir, sim=sim)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_sim_gateway") else 2
    if sub == "status":
        print(json.dumps(gateway_status(data_dir=data_dir, sim=sim), indent=2))
        return 0
    if sub == "presets" or getattr(args, "presets", False):
        from skycache.nexus.gateway_ops import HONEST

        print(json.dumps({"presets": list_presets(), "banner": HONEST}, indent=2))
        return 0
    if sub == "receipts" or getattr(args, "receipts", False):
        lim = int(getattr(args, "limit", 50) or 50)
        print(json.dumps(gateway_receipts(data_dir=data_dir, limit=lim), indent=2))
        return 0
    if sub == "pull-preset":
        rep = pull_preset(
            str(args.preset_id),
            data_dir=data_dir,
            dry_run=bool(getattr(args, "dry_run", False)),
            sim=sim or bool(getattr(args, "sim_pull", False)),
            force=bool(getattr(args, "force", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "ethics-kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "gateway-ethics-kit"
        rep = write_ethics_kit(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1

    # Legacy flat flags
    settings = Settings(data_dir=data_dir)
    settings.ensure_dirs()
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    gw = GatewayManager(
        dtn=dtn,
        node_id=node_id,
        sim_uplink=sim,
        receipt_log_path=settings.nexus_dir / "gateway-receipts.json",
    )
    gw.status.daily_quota_bytes = int(settings.gateway_daily_quota_mb) * 1024 * 1024
    if getattr(args, "quota_mb", None) is not None:
        gw.set_daily_quota_mb(int(args.quota_mb))
        print(json.dumps({"ok": True, "daily_quota_mb": int(args.quota_mb), "status": gw.snapshot()}, indent=2))
        return 0
    if getattr(args, "request", None):
        bid = gw.request_package(args.request, priority_class=getattr(args, "priority", "education"))
        print(f"Queued request {bid} for package {args.request}")
    if getattr(args, "pull", False):
        results = gw.schedule_pulls()
        print(json.dumps({"pulls": results, "status": gw.snapshot()}, indent=2))
    else:
        print(json.dumps(gateway_status(data_dir=data_dir, sim=sim), indent=2))
    return 0


def cmd_nexus_doctor(args: argparse.Namespace) -> int:
    from skycache.nexus.spectrum import compliance_report

    print(f"SkyCache Nexus doctor {__version__}")
    print(NEXUS_HONEST_BANNER)
    settings = Settings(data_dir=Path(args.data_dir))
    try:
        settings.validate_nexus()
        print(f"mesh_mode={settings.mesh_mode} mesh_band={settings.mesh_band} OK")
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    # Forbidden keyword smoke
    for bad in ("starlink", "satellite-uplink", "decrypt-commercial"):
        try:
            settings.validate_source_name(f"evil-{bad}")
            print(f"FAIL: validator allowed forbidden source containing '{bad}'")
            return 1
        except ValueError:
            print(f"  blocked forbidden source keyword: {bad}")
    print(json.dumps(compliance_report(), indent=2))
    for tool in ("batctl", "hostapd", "dnsmasq"):
        print(f"  {tool}: {shutil.which(tool) or 'not on PATH (optional for physical mesh)'}")
    print("OK - Nexus legal rails and spectrum policy intact.")
    return 0


def cmd_nexus_sim(args: argparse.Namespace) -> int:
    from skycache.nexus.sim import NexusSimulator

    print(NEXUS_HONEST_BANNER)
    sim = NexusSimulator(
        base_dir=Path(args.base_dir) if args.base_dir else None,
        node_count=args.nodes,
    )
    try:
        sim.setup(load_samples_on=args.seed_nodes)
        if args.disaster:
            sim.enable_disaster_mode()
            print("Disaster mode enabled on all sim nodes.")
        report = sim.run_round()
        # Second round so packages can fully replicate
        report2 = sim.run_round()
        out = {
            "round_1": report,
            "round_2": {
                "nodes": report2["nodes"],
                "mule": report2.get("mule"),
            },
            "legal": report.get("legal"),
        }
        print(json.dumps(out, indent=2))
        # Sanity: at least one node has packages after seed
        packages = [n["packages"] for n in report2["nodes"]]
        if max(packages) < 1:
            print("WARN: no packages after simulation rounds", file=sys.stderr)
            return 1
        print(
            f"Nexus sim OK: {args.nodes} nodes, package counts={packages}",
            file=sys.stderr,
        )
        return 0
    finally:
        if not args.keep:
            sim.teardown()


def cmd_nexus_validate(args: argparse.Namespace) -> int:
    """2/3-node mesh validation (sim) - village weekend acceptance."""
    from skycache.nexus.mesh_validate import field_checklist_stub, validate_mesh_sim

    print(NEXUS_HONEST_BANNER)
    if getattr(args, "checklist", False):
        print(json.dumps(field_checklist_stub(), indent=2))
        return 0
    report = validate_mesh_sim(
        nodes=int(args.nodes),
        base_dir=Path(args.base_dir) if args.base_dir else None,
        disaster=bool(args.disaster),
        keep=bool(args.keep),
    )
    print(json.dumps(report, indent=2))
    if not report.get("ok"):
        print("FAIL: mesh validation checks did not all pass", file=sys.stderr)
        return 1
    print(f"Mesh validate OK ({args.nodes} nodes)", file=sys.stderr)
    return 0


def cmd_nexus_status(args: argparse.Namespace) -> int:
    from skycache.nexus.dtn import DtnQueue
    from skycache.nexus.gateway import GatewayManager
    from skycache.nexus.identity import load_or_create_node_id
    from skycache.nexus.mesh import MeshFabric
    from skycache.nexus.traffic import traffic_monitor

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    mesh = MeshFabric(
        data_dir=settings.data_dir,
        node_id=node_id,
        mode=settings.mesh_mode,
        band=settings.mesh_band,
    )
    mesh.load()
    dtn = DtnQueue(settings.nexus_dir / "dtn-queue.json")
    gw = GatewayManager(dtn=dtn, node_id=node_id, sim_uplink=settings.sim_mode)
    catalog = Catalog(settings.db_path)
    payload = {
        "version": __version__,
        "product": "SkyCache Nexus",
        "banner": NEXUS_HONEST_BANNER,
        "node_id": node_id,
        "packages": catalog.count(),
        "mesh": mesh.status(),
        "dtn": dtn.stats(),
        "gateway": gw.snapshot(),
        "traffic": traffic_monitor(dtn, gw),
        "disaster_mode": settings.disaster_mode,
    }
    catalog.close()
    print(json.dumps(payload, indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from skycache.community.search import search_catalog

    settings = Settings(data_dir=Path(args.data_dir))
    catalog = Catalog(settings.db_path)
    results = search_catalog(
        catalog, args.q, category=args.category or None, limit=args.limit
    )
    catalog.close()
    print(json.dumps({"q": args.q, "count": len(results), "results": results}, indent=2))
    return 0


def cmd_licenses(args: argparse.Namespace) -> int:
    """Licenses Ops (v1.14): doctor, status, export, kit + legacy --html/--summary."""
    from skycache.community.licenses import LicenseInventory
    from skycache.ops.licenses_ops import (
        export_licenses_html,
        licenses_doctor,
        licenses_status,
        write_licenses_kit,
    )

    sub = getattr(args, "licenses_cmd", None)
    data_dir = Path(args.data_dir)

    # Legacy flags without subcommand
    if sub is None and getattr(args, "html", None):
        out = Path(args.html)
        rep = export_licenses_html(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        print("Open in browser -> Print -> Save as PDF for partners/regulators.")
        return 0 if rep.get("ok") else 1
    if sub is None and getattr(args, "summary", False):
        st = licenses_status(data_dir=data_dir)
        print(
            json.dumps(
                {
                    k: st[k]
                    for k in ("package_count", "by_license", "unknown_or_blank", "legal", "banner")
                },
                indent=2,
            )
        )
        return 0
    if sub is None:
        # bare licenses -> status inventory
        print(json.dumps(licenses_status(data_dir=data_dir), indent=2))
        return 0

    if sub == "doctor":
        rep = licenses_doctor(data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_licenses_inventory") else 2
    if sub == "status":
        print(json.dumps(licenses_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "licenses-inventory.html"
        rep = export_licenses_html(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "licenses-kit"
        rep = write_licenses_kit(
            out,
            data_dir=data_dir,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1

    # fallback legacy inventory dump
    settings = Settings(data_dir=data_dir)
    catalog = Catalog(settings.db_path)
    inv = LicenseInventory(catalog)
    report = inv.report()
    catalog.close()
    print(json.dumps(report, indent=2))
    return 0


def cmd_skybrary_zero_network_kit(args: argparse.Namespace) -> int:
    """Build self-contained kit for phones with no Wi-Fi and no cell."""
    from skycache.skybrary.zero_network_kit import (
        KIT_ZIP_NAME,
        build_zero_network_zip_bytes,
        write_zero_network_kit,
    )

    out = Path(args.out)
    meta = write_zero_network_kit(out)
    print(f"Zero-network kit: {meta['work_count']} works -> {out.resolve()}")
    print(f"  Open on phone: {(out / 'READ-OFFLINE.html').resolve()}")
    print("  Load via USB / OTG / microSD / Bluetooth / pre-deploy (no Wi-Fi, no cell).")
    if args.zip:
        data, _ = build_zero_network_zip_bytes()
        zpath = out.parent / KIT_ZIP_NAME if out.is_dir() else out.with_suffix(".zip")
        if out.is_dir():
            zpath = out / KIT_ZIP_NAME
        zpath.write_bytes(data)
        print(f"  Zip: {zpath.resolve()} ({len(data)} bytes)")
    print("Legal: PD samples only. Not free commercial broadband. Not a complete archive.")
    return 0


def cmd_skybrary_samples(args: argparse.Namespace) -> int:
    """Build and optionally ingest Skybrary public-domain sample packs."""
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.ingest import bootstrap_samples_with_settings
    from skycache.skybrary.sample_corpus import build_sample_packages

    out = Path(args.out)
    if args.ingest:
        settings = Settings(data_dir=Path(args.data_dir))
        settings.ensure_dirs()
        sky = SkybraryCatalog(settings.skybrary_db_path)
        ids = bootstrap_samples_with_settings(settings, sky, samples_out=out)
        sky.close()
        print(f"Skybrary: built+ingested {len(ids)} works: {ids}")
    else:
        paths = build_sample_packages(out)
        print(f"Skybrary: wrote {len(paths)} PD sample packs under {out}")
    print("Legal: public-domain curated samples only - not a complete archive.")
    return 0


def cmd_skybrary_search(args: argparse.Namespace) -> int:
    from skycache.skybrary.catalog import SkybraryCatalog

    settings = Settings(data_dir=Path(args.data_dir))
    sky = SkybraryCatalog(settings.skybrary_db_path)
    results = sky.search(
        args.q or "",
        language=args.lang or None,
        subject=args.subject or None,
        license_q=args.license or None,
        limit=args.limit,
    )
    print(json.dumps({"q": args.q, "count": len(results), "results": results, "facets": sky.facets()}, indent=2))
    sky.close()
    return 0


def cmd_capabilities(args: argparse.Namespace) -> int:
    """Capabilities Ops (v1.15): doctor, status, export, kit + legacy matrix print."""
    from skycache.capabilities.modes import LegalRfMode
    from skycache.ops.capabilities_ops import (
        capabilities_doctor,
        capabilities_status,
        export_capabilities_html,
        write_capabilities_kit,
    )

    sub = getattr(args, "capabilities_cmd", None)
    data_dir = Path(args.data_dir)
    sim = bool(getattr(args, "sim", False))

    if sub == "doctor":
        rep = capabilities_doctor(data_dir=data_dir, sim=sim)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_capabilities_onboard") else 2
    if sub == "status":
        print(json.dumps(capabilities_status(data_dir=data_dir, sim=sim), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "capabilities-matrix.html"
        rep = export_capabilities_html(out, data_dir=data_dir, sim=sim)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "capabilities-kit"
        rep = write_capabilities_kit(
            out,
            data_dir=data_dir,
            sim=sim,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1

    # Legacy: bare capabilities / --json human matrix
    st = capabilities_status(data_dir=data_dir, sim=sim)
    if getattr(args, "json", False):
        print(json.dumps(st, indent=2))
        return 0
    print(f"SkyCache legal capabilities ({__version__})")
    print(st.get("banner") or "")
    print(f"legal_rf_mode={st.get('legal_rf_mode')}")
    for c in st.get("capabilities") or []:
        mark = "ON " if c.get("enabled") else "off"
        print(f"  [{mark}] {str(c.get('id') or ''):28} {str(c.get('status') or ''):18} {c.get('title')}")
        print(f"         legal: {c.get('legal_basis')}")
        print(f"         how:   {c.get('how')}")
    print("BANNED:")
    for b in st.get("banned") or []:
        print(f"  - {b}")
    print(f"Modes: {', '.join(m.value for m in LegalRfMode)}")
    return 0


def cmd_open_fetch(args: argparse.Namespace) -> int:
    from skycache.capabilities.open_fetch import fetch_open_url, load_extra_hosts

    settings = Settings(data_dir=Path(args.data_dir))
    extra = load_extra_hosts(Path(settings.open_fetch_hosts_file)) if settings.open_fetch_hosts_file else []
    dest = Path(args.out)
    try:
        meta = fetch_open_url(args.url, dest, extra_hosts=extra, max_bytes=args.max_mb * 1024 * 1024)
    except (ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(meta, indent=2))
    return 0


def cmd_verify_tree(args: argparse.Namespace) -> int:
    from skycache.capabilities.integrity_tree import verify_content_tree, verify_package_dir

    path = Path(args.path)
    if (path / "manifest.json").is_file():
        report = verify_package_dir(path)
    else:
        report = verify_content_tree(path)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


def cmd_ble_mule_export(args: argparse.Namespace) -> int:
    """Legacy flat export; prefer handoff export (v1.7)."""
    from skycache.capabilities.handoff_ops import export_phone_handoff

    ids = [x.strip() for x in (args.packages or "").split(",") if x.strip()] or None
    rep = export_phone_handoff(
        data_dir=Path(args.data_dir),
        out_dir=Path(args.out),
        package_ids=ids,
        limit=int(args.limit),
        portal_url=getattr(args, "portal_url", None) or "http://10.42.0.1:8080/",
        ssid=getattr(args, "ssid", None) or "SkyCache-Village",
        include_join_card=not bool(getattr(args, "no_join", False)),
        zip_bundle=not bool(getattr(args, "no_zip", False)),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_handoff(args: argparse.Namespace) -> int:
    """Phone Handoff Ops (v1.7): doctor, join-card, export, import."""
    from skycache.capabilities.handoff_ops import (
        export_phone_handoff,
        handoff_doctor,
        import_phone_handoff,
        write_join_card,
    )

    sub = getattr(args, "handoff_cmd", None) or "export"
    if sub == "doctor":
        rep = handoff_doctor(data_dir=Path(args.data_dir))
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_phone_path") else 2
    if sub == "join-card":
        out = Path(args.out) if args.out else Path(args.data_dir) / "handoff" / "join"
        rep = write_join_card(
            out,
            portal_url=args.portal_url,
            ssid=args.ssid,
            node_name=args.node_name or "village-hub",
            data_dir=Path(args.data_dir),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "import":
        rep = import_phone_handoff(Path(args.path), data_dir=Path(args.data_dir))
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    # export (default)
    ids = [x.strip() for x in (args.packages or "").split(",") if x.strip()] or None
    rep = export_phone_handoff(
        data_dir=Path(args.data_dir),
        out_dir=Path(args.out) if args.out else None,
        package_ids=ids,
        limit=int(args.limit),
        portal_url=args.portal_url,
        ssid=args.ssid,
        include_join_card=not bool(args.no_join),
        zip_bundle=not bool(args.no_zip),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_mesh_day_one(args: argparse.Namespace) -> int:
    from skycache.nexus.mesh_day_one import apply_day_one, day_one_plan

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    if args.apply and not args.yes:
        print("Refusing --apply without --yes (hardware RF). Use --write for plan only.")
        return 2
    if args.apply:
        meta = apply_day_one(
            dry_run=False,
            mesh_if=args.mesh_if,
            bat_if=args.bat_if,
            node_octet=int(args.node_octet),
        )
    else:
        meta = day_one_plan(
            mesh_if=args.mesh_if,
            bat_if=args.bat_if,
            node_octet=int(args.node_octet),
            client_if=args.client_if,
            ssid_client=args.ssid,
            legal_rf_mode=args.legal_rf_mode,
            data_dir=settings.data_dir if args.write else None,
        )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok", True) else 1


def cmd_mesh_dual_radio_pack(args: argparse.Namespace) -> int:
    """Legacy: write validation pack only (same as dual-radio kit pack step)."""
    from skycache.nexus.dual_radio_validation import write_validation_pack

    meta = write_validation_pack(Path(args.out))
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


def cmd_library_ops(args: argparse.Namespace) -> int:
    """Library Ops (v1.24+) / publish (v1.25): doctor, status, export, kit, publish."""
    from skycache.ops.library_ops import (
        export_library_html,
        library_doctor,
        library_status,
        library_sync,
        pack_budget_report,
        publish_library_catalog,
        write_library_kit,
        write_library_pack_kits,
        write_library_zero_network,
    )

    sub = getattr(args, "library_cmd", None)
    data_dir = Path(args.data_dir) if getattr(args, "data_dir", None) else Path("data")
    if sub == "doctor":
        rep = library_doctor(data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_sim_library") else 2
    if sub == "status":
        print(
            json.dumps(
                library_status(data_dir=data_dir, repo_root=package_root()),
                indent=2,
            )
        )
        return 0
    if sub == "export":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "ops" / "library-board.html"
        )
        rep = export_library_html(out, data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "library-kit"
        )
        rep = write_library_kit(
            out,
            data_dir=data_dir,
            repo_root=package_root(),
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "publish":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "catalog-publish"
        )
        rep = publish_library_catalog(
            out,
            site_base=getattr(args, "site_base", None)
            or "https://skycache.jonbailey.xyz",
            rebuild_samples=not bool(getattr(args, "no_samples", False)),
            repo_root=package_root(),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "zero-network":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else Path("phone-zero-network")
        )
        rep = write_library_zero_network(
            out,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
            repo_root=package_root(),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") and rep.get("parity") else 1
    if sub == "sync":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "library-sync"
        )
        apply_web: Path | str | bool | None = None
        if bool(getattr(args, "apply_web", False)):
            aw = getattr(args, "web_public", None)
            apply_web = Path(aw) if aw else "auto"
        rep = library_sync(
            out,
            data_dir=data_dir,
            site_base=getattr(args, "site_base", None)
            or "https://skycache.jonbailey.xyz",
            rebuild_zero_network=not bool(getattr(args, "skip_zero_network", False)),
            rebuild_ops_kit=not bool(getattr(args, "skip_kit", False)),
            with_packs=bool(getattr(args, "with_packs", False)),
            apply_web=apply_web,
            repo_root=package_root(),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "pack-kits":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "library-pack-kits"
        )
        profiles = None
        if getattr(args, "profiles", None):
            profiles = [
                p.strip()
                for p in str(args.profiles).split(",")
                if p.strip()
            ]
        rep = write_library_pack_kits(
            out,
            profiles=profiles,
            content_dir=Path(args.content_dir)
            if getattr(args, "content_dir", None)
            else None,
            data_dir=data_dir if getattr(args, "data_dir", None) else None,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
            repo_root=package_root(),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "pack-budgets":
        profiles = None
        if getattr(args, "profiles", None):
            profiles = [
                p.strip()
                for p in str(args.profiles).split(",")
                if p.strip()
            ]
        rep = pack_budget_report(profiles=profiles, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0
    print(
        "Usage: skycache library doctor|status|export|kit|publish|zero-network|"
        "sync|pack-kits|pack-budgets",
        file=sys.stderr,
    )
    return 2


def cmd_dual_radio_ops(args: argparse.Namespace) -> int:
    """Dual Radio Ops (v1.22): doctor, status, export, kit."""
    from skycache.ops.dual_radio_ops import (
        dual_radio_doctor,
        dual_radio_status,
        export_dual_radio_html,
        write_dual_radio_kit,
    )

    sub = getattr(args, "dual_radio_cmd", None)
    data_dir = Path(args.data_dir) if getattr(args, "data_dir", None) else Path("data")
    if sub == "doctor":
        rep = dual_radio_doctor(data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_sim_validation") else 2
    if sub == "status":
        print(
            json.dumps(
                dual_radio_status(data_dir=data_dir, repo_root=package_root()),
                indent=2,
            )
        )
        return 0
    if sub == "export":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "ops" / "dual-radio-board.html"
        )
        rep = export_dual_radio_html(
            out, data_dir=data_dir, repo_root=package_root()
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = (
            Path(args.out)
            if getattr(args, "out", None)
            else data_dir / "dual-radio-kit"
        )
        rep = write_dual_radio_kit(
            out,
            data_dir=data_dir,
            repo_root=package_root(),
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print(
        "Usage: skycache dual-radio doctor|status|export|kit",
        file=sys.stderr,
    )
    return 2


def cmd_mesh_doctor(args: argparse.Namespace) -> int:
    from skycache.nexus.field_mesh_ops import mesh_doctor

    rep = mesh_doctor(data_dir=Path(args.data_dir), repo_root=package_root())
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("go_sim_mesh") else 2


def cmd_mesh_readiness(args: argparse.Namespace) -> int:
    from skycache.nexus.field_mesh_ops import mesh_readiness

    rep = mesh_readiness(
        data_dir=Path(args.data_dir),
        nodes=int(args.nodes),
        run_sim=not bool(args.skip_sim),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("go_sim_mesh") else 2


def cmd_mesh_disaster_drill(args: argparse.Namespace) -> int:
    from skycache.nexus.field_mesh_ops import run_disaster_drill

    rep = run_disaster_drill(
        nodes=int(args.nodes),
        data_dir=Path(args.data_dir),
        keep=bool(args.keep),
    )
    print(json.dumps(rep, indent=2))
    print("Lab drill only - field procedure: docs/disaster-drill.md")
    return 0 if rep.get("ok") else 1


def cmd_mesh_field_kit(args: argparse.Namespace) -> int:
    from skycache.nexus.field_mesh_ops import build_field_mesh_kit

    meta = build_field_mesh_kit(
        Path(args.out),
        repo_root=package_root(),
        make_zip=not bool(args.no_zip),
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


def cmd_maps_mbtiles(args: argparse.Namespace) -> int:
    from skycache.skybrary.blob_store import BlobStore
    from skycache.skybrary.mbtiles_pack import (
        import_mbtiles_to_pack,
        write_sample_mbtiles,
    )

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    if args.maps_cmd == "sample":
        path = Path(args.out)
        write_sample_mbtiles(path)
        print(json.dumps({"ok": True, "path": str(path), "bytes": path.stat().st_size}, indent=2))
        return 0
    # import
    blobs = BlobStore(settings.data_dir / "blobs") if not args.no_blob else None
    meta = import_mbtiles_to_pack(
        Path(args.mbtiles),
        Path(args.out),
        blobs=blobs,
        license_name=args.license,
        package_id=args.id,
        title=args.title,
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


def cmd_seal(args: argparse.Namespace) -> int:
    """Seal Ops (v1.20): golden Pi fleet doctor, status, export, kit."""
    from skycache.ops.seal_ops import (
        export_seal_html,
        seal_doctor,
        seal_status,
        write_seal_kit,
    )

    sub = getattr(args, "seal_cmd", None)
    if sub == "doctor":
        rep = seal_doctor()
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_kit_path") else 2
    if sub == "status":
        print(json.dumps(seal_status(), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else Path("data/ops/seal-board.html")
        rep = export_seal_html(out)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else Path("data/seal-kit")
        rep = write_seal_kit(out, zip_bundle=not bool(getattr(args, "no_zip", False)))
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print("Usage: skycache seal doctor|status|export|kit", file=sys.stderr)
    return 2


def cmd_pi_image(args: argparse.Namespace) -> int:
    from skycache.deploy_pi import (
        bake_plan,
        build_downloadable_sd_kit,
        hash_file_sha256,
        pi_image_doctor,
        sealed_image_manifest,
        write_bake_artifacts,
        write_seal_checklist,
    )

    if args.pi_cmd == "doctor":
        print(json.dumps(pi_image_doctor(), indent=2))
        return 0
    if args.pi_cmd == "plan":
        plan = bake_plan(
            hostname=args.hostname,
            ssid=args.ssid,
            legal_rf_mode=args.legal_rf_mode,
            mesh_mode=args.mesh_mode,
            include_optional_sdr=args.sdr,
        )
        print(json.dumps(plan, indent=2))
        return 0
    if args.pi_cmd == "bundle":
        meta = build_downloadable_sd_kit(
            Path(args.out),
            repo_root=package_root(),
            include_optional_sdr=bool(getattr(args, "sdr", False)),
        )
        print(json.dumps(meta, indent=2))
        print("Host kit zip at site /downloads/ and GitHub Release asset.")
        return 0 if meta.get("ok") else 1
    if args.pi_cmd == "seal-checklist":
        plan = bake_plan(
            hostname=getattr(args, "hostname", "skycache-village"),
            ssid=getattr(args, "ssid", "SkyCache-Village"),
            legal_rf_mode=getattr(args, "legal_rf_mode", "receive_only"),
            mesh_mode=getattr(args, "mesh_mode", "sim"),
            include_optional_sdr=bool(getattr(args, "sdr", False)),
        )
        meta = write_seal_checklist(Path(args.out), plan=plan)
        print(json.dumps(meta, indent=2))
        return 0 if meta.get("ok") else 1
    if args.pi_cmd == "hash":
        print(json.dumps(hash_file_sha256(Path(args.path)), indent=2))
        return 0
    if args.pi_cmd == "sealed-manifest":
        size = int(args.size_bytes) if args.size_bytes is not None else None
        if args.path and not args.sha256:
            h = hash_file_sha256(Path(args.path))
            if not h.get("ok"):
                print(json.dumps(h, indent=2))
                return 1
            args.sha256 = h["sha256"]
            if size is None:
                size = int(h["size_bytes"])
        meta = sealed_image_manifest(
            url=args.url,
            sha256=args.sha256 or "",
            size_bytes=size,
            out_path=Path(args.out) if args.out else None,
            note=args.note or "",
        )
        print(json.dumps(meta, indent=2))
        return 0 if meta.get("ok") else 1
    meta = write_bake_artifacts(
        Path(args.out),
        bake_plan(
            hostname=args.hostname,
            ssid=args.ssid,
            legal_rf_mode=args.legal_rf_mode,
            mesh_mode=args.mesh_mode,
            include_optional_sdr=args.sdr,
        ),
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


def cmd_blobs(args: argparse.Namespace) -> int:
    from skycache.skybrary.blob_store import BlobStore

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    store = BlobStore(settings.data_dir / "blobs")
    if args.blobs_cmd == "stats":
        print(json.dumps(store.stats(), indent=2))
        return 0
    if args.blobs_cmd == "put":
        meta = store.put_file(Path(args.path), media_type=args.media_type or "application/octet-stream")
        print(json.dumps(meta, indent=2))
        return 0 if meta.get("ok") else 1
    if args.blobs_cmd == "verify":
        print(json.dumps(store.verify(args.digest), indent=2))
        return 0 if store.verify(args.digest).get("ok") else 1
    if args.blobs_cmd == "ingest-content":
        meta = store.ingest_content_tree(settings.content_dir)
        print(json.dumps(meta, indent=2))
        return 0 if meta.get("ok") else 1
    print("Unknown blobs command", file=sys.stderr)
    return 2


def cmd_partner_kit(args: argparse.Namespace) -> int:
    from skycache.partner_kit import build_partner_kit

    meta = build_partner_kit(
        Path(args.out),
        kit_type=args.type,
        include_docs_copy=not args.no_docs,
        repo_root=package_root(),
        make_zip=bool(getattr(args, "zip", False)),
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


def cmd_partner_package_all(args: argparse.Namespace) -> int:
    from skycache.partner_kit import package_all_partner_kits

    meta = package_all_partner_kits(
        Path(args.out),
        repo_root=package_root(),
        include_docs_copy=not args.no_docs,
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


def cmd_partner_report_validate(args: argparse.Namespace) -> int:
    from skycache.partner_kit import validate_pilot_report

    rep = validate_pilot_report(Path(args.path))
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_partner_readiness(args: argparse.Namespace) -> int:
    """Legacy readiness (same gates as partner doctor)."""
    from skycache.ops.partner_ops import partner_doctor

    rep = partner_doctor(data_dir=Path(args.data_dir))
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("go_sim_pilot") else 2


def cmd_partner_ops(args: argparse.Namespace) -> int:
    """Partner Ops (v1.21): doctor, status, export, ops-kit."""
    from skycache.ops.partner_ops import (
        export_partner_html,
        partner_doctor,
        partner_status,
        write_partner_ops_kit,
    )

    sub = getattr(args, "partner_cmd", None)
    data_dir = Path(args.data_dir) if getattr(args, "data_dir", None) else Path("data")
    if sub == "doctor":
        rep = partner_doctor(data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_sim_pilot") else 2
    if sub == "status":
        print(json.dumps(partner_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "partner-board.html"
        rep = export_partner_html(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "ops-kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "partner-ops-kit"
        rep = write_partner_ops_kit(
            out,
            data_dir=data_dir,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print("Usage: skycache partner doctor|status|export|ops-kit|...", file=sys.stderr)
    return 2


def cmd_skybrary_corpus(args: argparse.Namespace) -> int:
    """Bulk Open Corpus Ops (v1.19): doctor / status / export / kit / batch / sample-manifest."""
    from skycache.skybrary.corpus_ops import (
        corpus_doctor,
        corpus_status,
        export_corpus_html,
        run_corpus_batch,
        write_corpus_kit,
        write_sample_batch_manifest,
    )

    sub = getattr(args, "corpus_cmd", None)
    data_dir = Path(args.data_dir) if getattr(args, "data_dir", None) else Path("data")
    if sub == "doctor":
        rep = corpus_doctor(data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_offline_batch") else 2
    if sub == "status":
        print(json.dumps(corpus_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "corpus-board.html"
        rep = export_corpus_html(out, data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "corpus-kit"
        rep = write_corpus_kit(
            out,
            data_dir=data_dir,
            repo_root=package_root(),
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "sample-manifest":
        meta = write_sample_batch_manifest(Path(args.out), repo_root=package_root())
        print(json.dumps(meta, indent=2))
        return 0 if meta.get("ok") else 1
    if sub == "batch":
        rep = run_corpus_batch(
            Path(args.manifest),
            data_dir=data_dir,
            out_root=Path(args.out) if args.out else None,
            ingest=bool(args.ingest),
            dry_run=bool(args.dry_run),
            allow_local=bool(args.allow_local),
            repo_root=package_root(),
        )
        print(json.dumps(rep, indent=2))
        print("Legal: open/PD only - see docs/skybrary-corpus-import.md")
        return 0 if rep.get("ok") else 1
    print("Unknown corpus subcommand")
    return 2


def cmd_corpus(args: argparse.Namespace) -> int:
    """Top-level Corpus Ops alias (v1.19 product surface)."""
    return cmd_skybrary_corpus(args)


def cmd_skybrary_import_oa_science(args: argparse.Namespace) -> int:
    from skycache.skybrary.oa_science import import_oa_science_catalog

    settings = Settings(data_dir=Path(args.data_dir)) if args.ingest else None
    if settings is not None:
        settings.ensure_dirs()
    meta = import_oa_science_catalog(
        Path(args.catalog),
        Path(args.out),
        max_works=int(args.max),
        max_bytes_total=int(args.max_bytes),
        delay_s=float(args.delay),
        dry_run=bool(args.dry_run),
        allow_local_file=bool(args.allow_local),
        settings=settings,
        ingest=bool(args.ingest),
        default_license=args.license,
    )
    print(json.dumps(meta, indent=2))
    print("Legal: OA/CC/PD science only  -  see docs/skybrary-corpus-import.md")
    return 0 if meta.get("ok") else 1


def cmd_skybrary_export_catalog(args: argparse.Namespace) -> int:
    """Export static dual-access catalog (JSON + HTML) for online portal."""
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.catalog_export import export_works_catalog

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    try:
        meta = export_works_catalog(
            sky,
            Path(args.out),
            limit=int(args.limit),
            include_html=not args.json_only,
            site_base=args.site_base,
            content_dir=settings.content_dir,
            include_starter_kits=bool(getattr(args, "starter_kits", False)),
        )
    finally:
        sky.close()
    print(json.dumps(meta, indent=2))
    print(
        "Deploy catalog.json / skybrary-catalog.json + index.html + packs/ "
        "to site /library/ (dual-access metadata + optional starter kits)."
    )
    return 0 if meta.get("ok") else 1


def cmd_skybrary_import_gutenberg_catalog(args: argparse.Namespace) -> int:
    """Batch import from Gutenberg-style catalog snapshot (operator-run)."""
    from skycache.skybrary.gutenberg_catalog import import_gutenberg_catalog

    settings = Settings(data_dir=Path(args.data_dir)) if args.ingest else None
    if settings is not None:
        settings.ensure_dirs()
    meta = import_gutenberg_catalog(
        Path(args.catalog),
        Path(args.out),
        license_name=args.license,
        language=args.lang or None,
        subject_contains=args.subject or None,
        max_works=int(args.max),
        max_bytes_total=int(args.max_bytes),
        delay_s=float(args.delay),
        dry_run=bool(args.dry_run),
        settings=settings,
        ingest=bool(args.ingest),
        allow_local_file=bool(args.allow_local),
    )
    print(json.dumps(meta, indent=2))
    print("Legal: open/PD only - see docs/skybrary-corpus-import.md")
    return 0 if meta.get("ok") else 1


def cmd_skybrary_provenance(args: argparse.Namespace) -> int:
    """Batch provenance report for content tree (partners/regulators)."""
    from skycache.skybrary.provenance import (
        provenance_report_from_content_dir,
        write_provenance_report,
    )

    settings = Settings(data_dir=Path(args.data_dir))
    report = provenance_report_from_content_dir(settings.content_dir)
    out = Path(args.out) if args.out else settings.data_dir / "provenance-report.json"
    write_provenance_report(report, out)
    print(json.dumps({
        "ok": True,
        "path": str(out.resolve()),
        "item_count": report["item_count"],
        "incomplete_passport_count": report["incomplete_passport_count"],
    }, indent=2))
    return 0


def cmd_skybrary_pack(args: argparse.Namespace) -> int:
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.pack_profile import build_pack_from_profile, list_profiles

    if args.list:
        print(json.dumps(list_profiles(), indent=2))
        return 0
    settings = Settings(data_dir=Path(args.data_dir))
    sky = SkybraryCatalog(settings.skybrary_db_path)
    try:
        meta = build_pack_from_profile(
            sky,
            args.profile,
            content_dir=settings.content_dir,
            out_dir=Path(args.out),
        )
    except ValueError as exc:
        print(f"FAIL: {exc}")
        sky.close()
        return 1
    sky.close()
    print(json.dumps(meta, indent=2))
    return 0


def cmd_skybrary_export_manifest(args: argparse.Namespace) -> int:
    """Export lightweight works_manifest JSON for catalog federation."""
    from skycache.nexus.identity import load_or_create_node_id
    from skycache.skybrary.catalog import SkybraryCatalog

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    node_id = settings.node_id or load_or_create_node_id(settings.data_dir)
    sky = SkybraryCatalog(settings.skybrary_db_path)
    out = Path(args.out)
    path = sky.export_works_manifest(out, node_id=node_id, max_works=args.limit)
    count = sky.count()
    sky.close()
    print(f"Works manifest: {path} ({count} works indexed, node={node_id})")
    return 0


def cmd_skybrary_import_manifest(args: argparse.Namespace) -> int:
    """Import peer works_manifest (metadata only; packages via handoff/fabric)."""
    from skycache.skybrary.catalog import SkybraryCatalog

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    try:
        report = sky.import_works_manifest(Path(args.path))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        sky.close()
        return 1
    sky.close()
    print(json.dumps(report, indent=2))
    return 0


def cmd_skybrary_import_folder(args: argparse.Namespace) -> int:
    """Import a directory of open .txt/.epub (license required)."""
    from skycache.skybrary.corpus_import import import_folder, register_packages_to_skybrary

    license_name = (args.license or "").strip()
    if not license_name:
        print("FAIL: --license is required (fail closed). Example: --license 'public domain'")
        return 1
    subjects = [s.strip() for s in (args.subjects or "").split(",") if s.strip()]
    creators = [c.strip() for c in (args.creators or "").split(",") if c.strip()]
    out = Path(args.out)
    try:
        report = import_folder(
            Path(args.path),
            out,
            license_name=license_name,
            language=args.lang,
            subjects=subjects or None,
            creators=creators or None,
            recursive=bool(args.recursive),
            max_files=int(args.max_files),
            id_prefix=args.id_prefix,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps({k: v for k, v in report.items() if k != "packages"}, indent=2))
    for p in report.get("packages") or []:
        print(f"  package: {p}")
    if args.ingest and report.get("packages"):
        settings = Settings(data_dir=Path(args.data_dir))
        settings.ensure_dirs()
        ids = register_packages_to_skybrary(
            [Path(p) for p in report["packages"]],
            settings=settings,
            register_content=True,
        )
        print(f"Ingested + Skybrary indexed: {ids}")
    print("Legal: open/authorized only - see docs/skybrary-corpus-import.md")
    return 0 if report.get("ok") else 1


def cmd_skybrary_import_open(args: argparse.Namespace) -> int:
    """Fetch one allowlisted open URL (Gutenberg-style) and package it."""
    from skycache.capabilities.open_fetch import load_extra_hosts
    from skycache.skybrary.corpus_import import import_open_url, register_packages_to_skybrary

    license_name = (args.license or "").strip()
    if not license_name:
        print("FAIL: --license is required (fail closed). Example: --license 'project gutenberg'")
        return 1
    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    extra = (
        load_extra_hosts(Path(settings.open_fetch_hosts_file))
        if settings.open_fetch_hosts_file
        else []
    )
    subjects = [s.strip() for s in (args.subjects or "").split(",") if s.strip()]
    try:
        report = import_open_url(
            args.url,
            Path(args.out),
            license_name=license_name,
            title=args.title or None,
            work_id=args.id or None,
            language=args.lang,
            subjects=subjects or None,
            extra_hosts=extra,
            max_bytes=int(args.max_mb) * 1024 * 1024,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(report, indent=2))
    if args.ingest and report.get("package"):
        ids = register_packages_to_skybrary(
            [Path(report["package"])],
            settings=settings,
            register_content=True,
        )
        print(f"Ingested + Skybrary indexed: {ids}")
    print("Legal: allowlisted open host only - never pirate mirrors.")
    return 0


def cmd_skybrary_doctor(args: argparse.Namespace) -> int:
    print(f"Skybrary doctor (SkyCache {__version__})")
    print("Mission: dual-access open written knowledge - not free commercial broadband.")
    print("Docs: docs/VISION-SKYBRARY.md  |  docs/skybrary-architecture.md  |  docs/threat-model.md")
    from skycache.health.bitrot_schedule import load_last_report, run_bitrot_verify, schedule_status
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.license_gate import license_allowed

    for lic in ("public domain", "CC-BY-4.0", "all rights reserved pirate"):
        print(f"  license_allowed({lic!r}) = {license_allowed(lic)}")
    settings = Settings(data_dir=Path(args.data_dir))
    sky = SkybraryCatalog(settings.skybrary_db_path)
    print(f"  works indexed: {sky.count()}")
    print(f"  facets: {json.dumps(sky.facets())}")
    sky.close()

    sched = schedule_status(settings.data_dir)
    last = load_last_report(settings.data_dir)
    if last:
        print(
            f"  bit-rot last: {last.get('checked_at')} ok={last.get('ok')} "
            f"packages={last.get('package_count')} fresh={sched.get('fresh')}"
        )
    else:
        print("  bit-rot last: never recorded (use --verify --record)")

    rc = 0
    if getattr(args, "verify", False):
        content_dir = settings.content_dir
        print(f"  integrity tree: {content_dir}")
        if getattr(args, "record", False):
            report = run_bitrot_verify(content_dir, settings.data_dir)
            tree = report.get("tree") or {}
            bad_ids = list(tree.get("failed_ids") or [])
            print(f"  packages checked: {report.get('package_count', 0)}")
            print(f"  integrity ok: {report.get('ok')}")
            print(f"  recorded: {settings.data_dir / 'ops' / 'bitrot-last.json'}")
            if not report.get("ok"):
                rc = 1
                for pid in bad_ids[:20]:
                    print(f"  FAIL {pid}")
            else:
                print("  bit-rot check: no drift detected")
            if getattr(args, "json", False):
                print(json.dumps(report, indent=2))
        else:
            from skycache.capabilities.integrity_tree import verify_content_tree

            report = verify_content_tree(content_dir)
            bad = [p for p in report.get("packages") or [] if not p.get("ok")]
            print(f"  packages checked: {report.get('count', 0)}")
            print(f"  integrity ok: {report.get('ok')}")
            if bad:
                rc = 1
                for p in bad[:20]:
                    print(f"  FAIL {p.get('package_id') or p.get('path')}: {p.get('error') or 'checksum/missing'}")
                    for f in p.get("files") or []:
                        if not f.get("ok"):
                            print(f"    - {f.get('path')}: {f.get('error') or 'hash mismatch'}")
            else:
                print("  bit-rot check: no drift detected")
            if getattr(args, "json", False):
                print(json.dumps(report, indent=2))
        print(
            "  schedule tip: skycache bitrot install-templates "
            "or weekly cron - skybrary doctor --verify --record"
        )
    if rc == 0:
        print("OK - Skybrary catalog ready" + (" + integrity clean" if getattr(args, "verify", False) else "") + ".")
    else:
        print("FAIL - integrity drift; re-ingest or restore from good packs.")
    return rc


def cmd_ops(args: argparse.Namespace) -> int:
    """Local Ops (v1.16): doctor, status, export, kit (privacy-preserving, fleet OFF)."""
    from skycache.ops.local_ops import (
        export_ops_html,
        ops_doctor,
        ops_status,
        write_ops_kit,
    )

    sub = getattr(args, "ops_cmd", None)
    data_dir = Path(args.data_dir)

    if sub == "doctor":
        rep = ops_doctor(data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_local_lab") else 2
    if sub == "status":
        print(json.dumps(ops_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "local-ops-board.html"
        rep = export_ops_html(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops-kit"
        rep = write_ops_kit(
            out,
            data_dir=data_dir,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1

    print("Usage: skycache ops doctor|status|export|kit", file=sys.stderr)
    return 2


def cmd_report(args: argparse.Namespace) -> int:
    """Node Report Ops (v1.18): rollup doctor, status, passport export, kit."""
    from skycache.ops.report_ops import (
        export_report_html,
        report_doctor,
        report_status,
        write_report_kit,
    )

    sub = getattr(args, "report_cmd", None)
    data_dir = Path(args.data_dir)

    if sub == "doctor":
        rep = report_doctor(data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_partner_review") else 2
    if sub == "status":
        print(json.dumps(report_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "export":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "node-report.html"
        rep = export_report_html(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "report-kit"
        rep = write_report_kit(
            out,
            data_dir=data_dir,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1

    print("Usage: skycache report doctor|status|export|kit", file=sys.stderr)
    return 2


def cmd_village_day(args: argparse.Namespace) -> int:
    """Village Day Ops (v1.9): doctor, readiness, runbook, kit."""
    from skycache.ops.village_day_ops import (
        village_day_doctor,
        village_day_readiness,
        write_village_day_kit,
        write_village_day_runbook,
    )

    sub = getattr(args, "village_day_cmd", None) or "doctor"
    data_dir = Path(args.data_dir)
    if sub == "doctor":
        rep = village_day_doctor(
            data_dir=data_dir,
            repo_root=package_root(),
            sim=bool(getattr(args, "sim", True)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_weekend_sim") else 2
    if sub == "readiness":
        rep = village_day_readiness(
            data_dir=data_dir,
            repo_root=package_root(),
            sim=bool(getattr(args, "sim", True)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_weekend_sim") else 2
    if sub == "runbook":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "village-day"
        rep = write_village_day_runbook(out, data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if getattr(args, "out", None) else data_dir / "village-day-kit"
        rep = write_village_day_kit(
            out,
            data_dir=data_dir,
            repo_root=package_root(),
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({"error": f"unknown village-day cmd {sub}"}, indent=2))
    return 1


def cmd_bitrot_install_templates(args: argparse.Namespace) -> int:
    from skycache.health.bitrot_schedule import write_schedule_templates

    meta = write_schedule_templates(Path(args.out), data_dir=args.data_dir_path)
    print(json.dumps(meta, indent=2))
    print("Legal: open packs only. Install on the village node, not a cloud host.")
    return 0


def cmd_power(args: argparse.Namespace) -> int:
    """Power Ops (v1.13): doctor, status, sheet, kit."""
    from skycache.ops.power_ops import (
        power_doctor,
        power_status,
        write_power_kit,
        write_power_sheet,
    )

    sub = getattr(args, "power_cmd", None) or "doctor"
    data_dir = Path(args.data_dir)
    if sub == "doctor":
        rep = power_doctor(data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_power_lab") else 2
    if sub == "status":
        print(json.dumps(power_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "sheet":
        out = Path(args.out) if args.out else data_dir / "ops" / "power-sheet.html"
        rep = write_power_sheet(out, data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if args.out else data_dir / "power-kit"
        rep = write_power_kit(
            out,
            data_dir=data_dir,
            repo_root=package_root(),
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({"error": f"unknown power cmd {sub}"}, indent=2))
    return 1


def cmd_disaster(args: argparse.Namespace) -> int:
    """Disaster Drill Ops (v1.12): doctor, run, report, closeout, kit."""
    from skycache.ops.disaster_ops import (
        disaster_closeout,
        disaster_doctor,
        disaster_run,
        write_disaster_kit,
        write_disaster_report_html,
    )

    sub = getattr(args, "disaster_cmd", None) or "doctor"
    data_dir = Path(args.data_dir)
    if sub == "doctor":
        rep = disaster_doctor(data_dir=data_dir, repo_root=package_root())
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_lab_drill") else 2
    if sub == "run":
        rep = disaster_run(
            data_dir=data_dir,
            nodes=int(getattr(args, "nodes", 3) or 3),
            keep=bool(getattr(args, "keep", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "report":
        out = Path(args.out) if args.out else data_dir / "ops" / "disaster-report.html"
        rep = write_disaster_report_html(
            out,
            data_dir=data_dir,
            run_lab=bool(getattr(args, "run", False)),
            nodes=int(getattr(args, "nodes", 3) or 3),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "closeout":
        rep = disaster_closeout(data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if args.out else data_dir / "disaster-kit"
        rep = write_disaster_kit(
            out,
            data_dir=data_dir,
            repo_root=package_root(),
            zip_bundle=not bool(getattr(args, "no_zip", False)),
            run_lab=bool(getattr(args, "run", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({"error": f"unknown disaster cmd {sub}"}, indent=2))
    return 1


def cmd_integrity(args: argparse.Namespace) -> int:
    """Integrity Ops (v1.11): doctor, verify, report, install-templates, kit."""
    from skycache.ops.integrity_ops import (
        integrity_doctor,
        integrity_verify,
        write_integrity_kit,
        write_integrity_report_html,
    )
    from skycache.health.bitrot_schedule import write_schedule_templates

    sub = getattr(args, "integrity_cmd", None) or "doctor"
    data_dir = Path(args.data_dir)
    if sub == "doctor":
        rep = integrity_doctor(
            data_dir=data_dir,
            max_age_days=float(getattr(args, "max_age_days", 10) or 10),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_integrity_sim") else 2
    if sub == "verify":
        rep = integrity_verify(
            data_dir=data_dir,
            record=not bool(getattr(args, "no_record", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "report":
        out = Path(args.out) if args.out else data_dir / "ops" / "integrity-report.html"
        rep = write_integrity_report_html(
            out,
            data_dir=data_dir,
            run_verify=bool(getattr(args, "verify", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "install-templates":
        meta = write_schedule_templates(
            Path(args.out),
            data_dir=str(getattr(args, "data_dir_path", None) or "/var/lib/skycache"),
        )
        print(json.dumps(meta, indent=2))
        return 0
    if sub == "kit":
        out = Path(args.out) if args.out else data_dir / "integrity-kit"
        rep = write_integrity_kit(
            out,
            data_dir=data_dir,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
            run_verify=bool(getattr(args, "verify", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({"error": f"unknown integrity cmd {sub}"}, indent=2))
    return 1


def cmd_rx_doctor(args: argparse.Namespace) -> int:
    """RX Ops doctor (v1.17): readiness + legacy tool inventory."""
    from skycache.ops.rx_ops import rx_ops_doctor
    from skycache.rx.doctor import rx_doctor_report

    settings = Settings(data_dir=Path(args.data_dir))
    if getattr(args, "legacy", False):
        print(json.dumps(rx_doctor_report(data_dir=settings.data_dir), indent=2))
        return 0
    rep = rx_ops_doctor(data_dir=settings.data_dir)
    # attach raw tool inventory for field operators
    raw = rx_doctor_report(data_dir=settings.data_dir)
    rep["tools"] = raw.get("tools")
    rep["probes"] = raw.get("probes")
    rep["station"] = raw.get("station")
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("go_rx_lab") else 2


def cmd_rx_status(args: argparse.Namespace) -> int:
    from skycache.ops.rx_ops import rx_ops_status

    print(json.dumps(rx_ops_status(data_dir=Path(args.data_dir)), indent=2))
    return 0


def cmd_rx_export(args: argparse.Namespace) -> int:
    from skycache.ops.rx_ops import export_rx_html

    data_dir = Path(args.data_dir)
    out = Path(args.out) if getattr(args, "out", None) else data_dir / "ops" / "rx-station-board.html"
    rep = export_rx_html(out, data_dir=data_dir)
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_rx_kit(args: argparse.Namespace) -> int:
    from skycache.ops.rx_ops import write_rx_kit

    data_dir = Path(args.data_dir)
    out = Path(args.out) if getattr(args, "out", None) else data_dir / "rx-kit"
    rep = write_rx_kit(
        out,
        data_dir=data_dir,
        zip_bundle=not bool(getattr(args, "no_zip", False)),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_rx_recipes(args: argparse.Namespace) -> int:
    from skycache.rx.recipes import list_recipes

    print(json.dumps(list_recipes(), indent=2))
    return 0


def cmd_rx_station(args: argparse.Namespace) -> int:
    from skycache.rx.station import load_station, save_station

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    if args.lat is None or args.lon is None:
        st = load_station(settings.data_dir)
        print(json.dumps(st or {"error": "no station.json - set --lat --lon"}, indent=2))
        return 0 if st else 1
    st = save_station(
        settings.data_dir,
        lat=float(args.lat),
        lon=float(args.lon),
        alt_m=float(args.alt_m),
        name=args.name,
        antenna=args.antenna or "",
        notes=args.notes or "",
    )
    print(json.dumps(st, indent=2))
    return 0


def cmd_rx_passes(args: argparse.Namespace) -> int:
    from skycache.rx.pass_plan import predict_passes
    from skycache.rx.station import load_station

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    lat, lon, alt = args.lat, args.lon, args.alt_m
    if lat is None or lon is None:
        st = load_station(settings.data_dir)
        if not st:
            print("Set station first: skycache rx station --lat LAT --lon LON")
            return 1
        lat = float(st["lat"])
        lon = float(st["lon"])
        alt = float(st.get("alt_m") or 0.0)
    report = predict_passes(
        lat=float(lat),
        lon=float(lon),
        alt_m=float(alt or 0.0),
        hours=float(args.hours),
        min_elevation=float(args.min_elev),
        data_dir=settings.data_dir,
    )
    print(json.dumps(report, indent=2))
    return 0


def cmd_rx_tle_import(args: argparse.Namespace) -> int:
    from skycache.rx.pass_plan import import_tle_text

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    text = Path(args.path).read_text(encoding="utf-8", errors="replace")
    try:
        rep = import_tle_text(settings.data_dir, text)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(rep, indent=2))
    print("Legal: only import TLEs you are allowed to use. Refresh often.")
    return 0


def cmd_rx_watch(args: argparse.Namespace) -> int:
    from skycache.rx.product_watch import watch_loop, watch_once

    settings = Settings(data_dir=Path(args.data_dir), sim_mode=bool(args.sim))
    settings.ensure_dirs()
    watch_dir = Path(args.dir)
    if args.once or args.iterations:
        if args.once:
            rep = watch_once(
                watch_dir,
                settings,
                recipe=args.recipe,
                satellite=args.satellite or "",
            )
            print(json.dumps(rep, indent=2))
            return 0 if all(r.get("ok", True) for r in (rep.get("results") or []) or [True]) else 1
        rep = watch_loop(
            watch_dir,
            settings,
            interval_sec=float(args.interval),
            recipe=args.recipe,
            satellite=args.satellite or "",
            max_iterations=int(args.iterations),
        )
        print(json.dumps(rep, indent=2))
        return 0
    # Service mode: loop forever
    print(
        json.dumps(
            {
                "watching": str(watch_dir),
                "interval_sec": args.interval,
                "legal": "FTA product ingest only",
            }
        )
    )
    watch_loop(
        watch_dir,
        settings,
        interval_sec=float(args.interval),
        recipe=args.recipe,
        satellite=args.satellite or "",
        max_iterations=None,
    )
    return 0


def cmd_rx_import(args: argparse.Namespace) -> int:
    from skycache.rx.product_watch import ingest_product

    settings = Settings(data_dir=Path(args.data_dir), sim_mode=bool(args.sim))
    settings.ensure_dirs()
    rep = ingest_product(
        Path(args.path),
        settings,
        recipe=args.recipe,
        satellite=args.satellite or "",
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_rx_capture(args: argparse.Namespace) -> int:
    from skycache.rx.capture import capture_to_catalog

    settings = Settings(data_dir=Path(args.data_dir), sim_mode=bool(args.sim))
    settings.ensure_dirs()
    rep = capture_to_catalog(
        settings,
        recipe_id=args.recipe,
        input_path=args.input,
        force_live=bool(args.force_live),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_rx_log(args: argparse.Namespace) -> int:
    from skycache.rx.field_log import append_field_log, list_field_log

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    if args.list:
        print(json.dumps(list_field_log(settings.data_dir, limit=int(args.limit)), indent=2))
        return 0
    try:
        entry = append_field_log(
            settings.data_dir,
            satellite=args.satellite,
            elevation_deg=float(args.elevation) if args.elevation is not None else None,
            quality=args.quality or "",
            snr_db=float(args.snr) if args.snr is not None else None,
            recipe=args.recipe or "",
            package_id=args.package_id or "",
            notes=args.notes or "",
            operator=args.operator or "",
        )
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(entry, indent=2))
    return 0


def cmd_rx_schedule(args: argparse.Namespace) -> int:
    """Pass Autopilot: upcoming passes bound to FTA recipes + SatDump sketches."""
    from skycache.rx.schedule import build_schedule

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    rep = build_schedule(
        settings.data_dir,
        hours=float(args.hours),
        min_elevation=float(args.min_elev),
        products_dir=args.products_dir or None,
        limit=int(args.limit),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_rx_arm(args: argparse.Namespace) -> int:
    """Arm station for upcoming duty windows (enables watch auto field-log)."""
    from skycache.rx.schedule import clear_arm, duty_status, load_arm, save_arm

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    if getattr(args, "disarm", False):
        print(json.dumps(clear_arm(settings.data_dir), indent=2))
        return 0
    if getattr(args, "status", False):
        print(json.dumps(duty_status(settings.data_dir), indent=2))
        return 0
    if getattr(args, "show", False):
        print(json.dumps(load_arm(settings.data_dir) or {"armed": False}, indent=2))
        return 0
    recipes = None
    if args.recipes:
        recipes = [r.strip() for r in str(args.recipes).split(",") if r.strip()]
    arm = save_arm(
        settings.data_dir,
        hours=float(args.hours),
        min_elevation=float(args.min_elev),
        products_dir=args.products_dir or None,
        auto_field_log=not bool(args.no_auto_log),
        recipes=recipes,
    )
    print(json.dumps(arm, indent=2))
    return 0 if arm.get("armed") else 1


def cmd_rx_cmd(args: argparse.Namespace) -> int:
    """Print SatDump CLI sketch for a recipe (or next armed/scheduled pass)."""
    from skycache.rx.schedule import (
        build_schedule,
        load_arm,
        recipe_for_satellite,
        satdump_command,
    )

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    recipe = (args.recipe or "").strip()
    products = args.products_dir or str(settings.data_dir / "satdump-products")
    if not recipe:
        arm = load_arm(settings.data_dir)
        nxt = (arm or {}).get("next") if arm else None
        if not nxt:
            sched = build_schedule(settings.data_dir, hours=24.0)
            nxt = sched.get("next")
        if nxt:
            recipe = str(nxt.get("recipe_id") or recipe_for_satellite(str(nxt.get("satellite") or "")))
            products = str((arm or {}).get("products_dir") or products)
        else:
            recipe = "noaa_apt"
    rep = satdump_command(
        recipe_id=recipe,
        products_dir=products,
        input_hint=args.mode or "live",
        satdump_bin=args.satdump or "satdump",
    )
    if getattr(args, "next_pass", False):
        sched = build_schedule(settings.data_dir, hours=24.0, products_dir=products)
        rep = {"next_pass": sched.get("next"), "satdump": rep, "schedule_count": sched.get("count")}
    print(json.dumps(rep, indent=2))
    return 0


def cmd_rx_duty(args: argparse.Namespace) -> int:
    from skycache.rx.schedule import duty_status

    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    print(json.dumps(duty_status(settings.data_dir), indent=2))
    return 0


def cmd_nexus_federation_sim(args: argparse.Namespace) -> int:
    """Legacy nexus federation sim - prefer skycache federation sim (v1.10)."""
    from skycache.nexus.federation_ops import run_federation_sim

    base = (getattr(args, "base_dir", None) or "").strip()
    rep = run_federation_sim(
        nodes=max(2, int(args.nodes)),
        rounds=max(1, int(args.rounds)),
        base_dir=Path(base) if base else None,
        data_dir=Path(getattr(args, "data_dir", None) or "data"),
    )
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 1


def cmd_federation(args: argparse.Namespace) -> int:
    """Federation Ops (v1.10): doctor, status, export/import gossip, sim, kit."""
    from skycache.nexus.federation_ops import (
        export_gossip,
        federation_doctor,
        federation_status,
        import_gossip,
        run_federation_sim,
        write_federation_kit,
    )

    sub = getattr(args, "federation_cmd", None) or "doctor"
    data_dir = Path(args.data_dir)
    if sub == "doctor":
        rep = federation_doctor(data_dir=data_dir)
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("go_sim_federation") else 2
    if sub == "status":
        print(json.dumps(federation_status(data_dir=data_dir), indent=2))
        return 0
    if sub == "export-gossip":
        out = Path(args.out) if args.out else data_dir / "federation" / "gossip.json"
        compact = None
        if getattr(args, "compact", False):
            compact = True
        if getattr(args, "full", False):
            compact = False
        rep = export_gossip(
            out,
            data_dir=data_dir,
            compact=compact,
            max_tier=int(args.max_tier) if getattr(args, "max_tier", None) else None,
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "import-gossip":
        peer = (getattr(args, "peer_content", None) or "").strip()
        rep = import_gossip(
            Path(args.path),
            data_dir=data_dir,
            peer_content_root=Path(peer) if peer else None,
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "sim":
        base = (getattr(args, "base_dir", None) or "").strip()
        rep = run_federation_sim(
            nodes=int(args.nodes),
            rounds=int(args.rounds),
            data_dir=data_dir,
            base_dir=Path(base) if base else None,
            seed=not bool(getattr(args, "no_seed", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    if sub == "kit":
        out = Path(args.out) if args.out else data_dir / "federation-kit"
        rep = write_federation_kit(
            out,
            data_dir=data_dir,
            zip_bundle=not bool(getattr(args, "no_zip", False)),
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({"error": f"unknown federation cmd {sub}"}, indent=2))
    return 1


def cmd_package_validate(args: argparse.Namespace) -> int:
    errs = validate_package_dir(Path(args.path))
    if errs:
        print("INVALID")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK  {args.path}")
    return 0


def cmd_package_create(args: argparse.Namespace) -> int:
    files = [Path(p) for p in (args.file or [])]
    out = create_package(
        Path(args.out),
        package_id=args.id,
        title=args.title,
        priority_class=args.priority,
        summary=args.summary or "",
        language=args.lang,
        source_files=files or None,
        license_name=args.license,
        tags=[t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None,
    )
    print(f"Created package at {out}")
    if args.ingest:
        settings = Settings(data_dir=Path(args.data_dir))
        settings.ensure_dirs()
        catalog = Catalog(settings.db_path)
        content = ContentManager(settings, catalog)
        pkg = content.ingest_package_dir(out)
        print(f"Ingested {pkg.id}")
        catalog.close()
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    settings = Settings(data_dir=Path(args.data_dir))
    settings.ensure_dirs()
    watcher = DropWatcher(settings, Path(args.drop) if args.drop else None)
    print(f"Drop incoming: {watcher.incoming}")
    if args.once:
        ids = watcher.scan_once()
        print(f"Processed: {ids or '(none)'}")
        return 0
    _setup_logging(settings.log_level)
    try:
        watcher.loop(interval_sec=args.interval)
    except KeyboardInterrupt:
        print("Stopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skycache",
        description=(
            "SkyCache Nexus - store-and-forward knowledge + community mesh "
            "(not free commercial broadband)"
        ),
    )
    p.add_argument("--version", action="version", version=f"skycache {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create data directories")
    init.add_argument("--data-dir", default="data")
    init.add_argument("--load-samples", action="store_true")
    init.set_defaults(func=cmd_init)

    fb = sub.add_parser(
        "first-boot",
        help="First-boot wizard: PIN, SSID, legal_rf_mode, samples, capabilities",
    )
    fb.add_argument("--data-dir", default="data")
    fb.add_argument("--pin", default="", help="Admin PIN (4 - 8 digits, not default 2468)")
    fb.add_argument("--ssid", default="", help="Hotspot SSID hint (operators / hostapd)")
    fb.add_argument(
        "--legal-rf-mode",
        default="",
        help="receive_only|ism_mesh|ism_lora_control|hybrid_gateway|amateur_operator",
    )
    fb.add_argument(
        "--amateur-affirmed",
        action="store_true",
        help="Required with --legal-rf-mode amateur_operator",
    )
    fb.add_argument("--node-id", default="", help="Optional SKYCACHE_NODE_ID")
    fb.add_argument("--lang", default="en", help="Language hint (en fr es ar sw hi pt)")
    fb.add_argument("--env-file", default="", help="Write env file path (default: DATA/skycache.env)")
    fb.add_argument("--no-samples", action="store_true", help="Skip demo package load")
    fb.add_argument("--no-skybrary", action="store_true", help="Skip Skybrary PD samples")
    fb.add_argument("--sim", action="store_true", help="Mark capabilities for sim mode")
    fb.add_argument("--force", action="store_true", help="Redo even if first_boot.json exists")
    fb.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Non-interactive (requires --pin)",
    )
    fb.add_argument(
        "--non-interactive",
        action="store_true",
        help="Same as --yes",
    )
    fb.add_argument("--json", action="store_true", help="Print machine-readable result")
    fb.set_defaults(func=cmd_first_boot)

    serve = sub.add_parser("serve", help="Run local portal")
    serve.add_argument("--data-dir", default="data")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--sim", action="store_true", help="Simulation mode")
    serve.set_defaults(func=cmd_serve)

    ingest = sub.add_parser("ingest", help="Ingest package path")
    ingest.add_argument("path")
    ingest.add_argument("--data-dir", default="data")
    ingest.set_defaults(func=cmd_ingest)

    pipe = sub.add_parser("pipeline", help="Run a decoder plugin")
    pipe.add_argument("--plugin", required=True)
    pipe.add_argument("--uri", default="")
    pipe.add_argument(
        "--option",
        action="append",
        default=[],
        help="Plugin option KEY=VALUE (repeatable); e.g. --option license=public domain",
    )
    pipe.add_argument("--data-dir", default="data")
    pipe.add_argument("--sim", action="store_true")
    pipe.set_defaults(func=cmd_pipeline)

    st = sub.add_parser("status", help="Show local status")
    st.add_argument("--data-dir", default="data")
    st.set_defaults(func=cmd_status)

    doc = sub.add_parser("doctor", help="Environment checks")
    doc.add_argument("--data-dir", default="data")
    doc.set_defaults(func=cmd_doctor)

    pkg = sub.add_parser("package", help="Create or validate content packages")
    pkg_sub = pkg.add_subparsers(dest="package_cmd", required=True)

    pv = pkg_sub.add_parser("validate", help="Validate a package directory")
    pv.add_argument("path")
    pv.set_defaults(func=cmd_package_validate)

    pc = pkg_sub.add_parser("create", help="Scaffold a package from files/title")
    pc.add_argument("--id", required=True, help="Package id (safe chars)")
    pc.add_argument("--title", required=True)
    pc.add_argument("--out", required=True, help="Output package directory")
    pc.add_argument("--priority", default="education")
    pc.add_argument("--summary", default="")
    pc.add_argument("--lang", default="en")
    pc.add_argument("--file", action="append", help="File to include (repeatable)")
    pc.add_argument("--license", default="operator_supplied")
    pc.add_argument("--tags", default="")
    pc.add_argument("--ingest", action="store_true", help="Ingest after create")
    pc.add_argument("--data-dir", default="data")
    pc.set_defaults(func=cmd_package_create)

    watch = sub.add_parser("watch", help="Watch USB/drop folder for packages")
    watch.add_argument("--data-dir", default="data")
    watch.add_argument("--drop", default="", help="Override drop root (contains incoming/)")
    watch.add_argument("--once", action="store_true", help="Single scan then exit")
    watch.add_argument("--interval", type=float, default=15.0)
    watch.set_defaults(func=cmd_watch)

    # --- Nexus fabric ---
    mesh = sub.add_parser("mesh", help="Mesh fabric status / spectrum compliance")
    mesh_sub = mesh.add_subparsers(dest="mesh_cmd", required=True)
    ms = mesh_sub.add_parser("status", help="Topology, peers, power-prefer routes")
    ms.add_argument("--data-dir", default="data")
    ms.add_argument("--compliance", action="store_true", help="Print spectrum policy")
    ms.set_defaults(func=cmd_mesh_status)
    md1 = mesh_sub.add_parser(
        "day-one",
        help="batman-adv day-one OOB plan (sim-safe; --apply only on Linux+root)",
    )
    md1.add_argument("--data-dir", default="data")
    md1.add_argument("--mesh-if", default="wlan0")
    md1.add_argument("--bat-if", default="bat0")
    md1.add_argument("--client-if", default="wlan1")
    md1.add_argument("--node-octet", type=int, default=10)
    md1.add_argument("--ssid", default="SkyCache-Village")
    md1.add_argument("--legal-rf-mode", default="ism_mesh")
    md1.add_argument("--write", action="store_true", help="Write plan JSON under data/nexus/")
    md1.add_argument("--apply", action="store_true", help="Run batman-day-one.sh (Linux only)")
    md1.add_argument("--yes", action="store_true", help="Confirm hardware apply")
    md1.set_defaults(func=cmd_mesh_day_one)
    mdr = mesh_sub.add_parser(
        "dual-radio-pack",
        help="Legacy: board matrix + storyboard pack (prefer: dual-radio kit)",
    )
    mdr.add_argument("--out", default="media/dual-radio-validation")
    mdr.set_defaults(func=cmd_mesh_dual_radio_pack)

    # Library Ops (v1.24+) / publish (v1.25) - dual-access Skybrary catalog
    lib = sub.add_parser(
        "library",
        help=(
            "Library Ops: doctor/status/export/kit/publish/zero-network/"
            "sync/pack-kits/pack-budgets"
        ),
    )
    lib_sub = lib.add_subparsers(dest="library_cmd", required=True)
    libdoc = lib_sub.add_parser("doctor", help="Dual-access library readiness")
    libdoc.add_argument("--data-dir", default="data")
    libdoc.set_defaults(func=cmd_library_ops, library_cmd="doctor")
    libst = lib_sub.add_parser("status", help="Work count + language snapshot")
    libst.add_argument("--data-dir", default="data")
    libst.set_defaults(func=cmd_library_ops, library_cmd="status")
    libexp = lib_sub.add_parser("export", help="Printable library board HTML")
    libexp.add_argument("--data-dir", default="data")
    libexp.add_argument("--out", default="data/ops/library-board.html")
    libexp.set_defaults(func=cmd_library_ops, library_cmd="export")
    libkit = lib_sub.add_parser("kit", help="Build library ops kit + zip")
    libkit.add_argument("--data-dir", default="data")
    libkit.add_argument("--out", default="data/library-kit")
    libkit.add_argument("--no-zip", action="store_true")
    libkit.set_defaults(func=cmd_library_ops, library_cmd="kit")
    libpub = lib_sub.add_parser(
        "publish",
        help="Write marketing-ready skybrary-catalog.json (+ rebuild samples)",
    )
    libpub.add_argument("--data-dir", default="data")
    libpub.add_argument("--out", default="data/catalog-publish")
    libpub.add_argument(
        "--site-base",
        default="https://skycache.jonbailey.xyz",
        help="Public site base for dual_access URLs",
    )
    libpub.add_argument(
        "--no-samples",
        action="store_true",
        help="Skip regenerating samples/skybrary packages",
    )
    libpub.set_defaults(func=cmd_library_ops, library_cmd="publish")
    libzn = lib_sub.add_parser(
        "zero-network",
        help="Write zero-network phone kit matching full curated sample count",
    )
    libzn.add_argument("--out", default="phone-zero-network")
    libzn.add_argument("--no-zip", action="store_true")
    libzn.set_defaults(func=cmd_library_ops, library_cmd="zero-network")
    libsync = lib_sub.add_parser(
        "sync",
        help="One-shot: publish catalog + kits into staging for skycache-web",
    )
    libsync.add_argument("--data-dir", default="data")
    libsync.add_argument("--out", default="data/library-sync")
    libsync.add_argument(
        "--site-base",
        default="https://skycache.jonbailey.xyz",
    )
    libsync.add_argument(
        "--skip-zero-network",
        action="store_true",
        help="Skip rebuilding the large zero-network phone kit",
    )
    libsync.add_argument(
        "--skip-kit",
        action="store_true",
        help="Skip library ops kit zip",
    )
    libsync.add_argument(
        "--apply-web",
        action="store_true",
        help="Copy staged public/ into skycache-web/public (auto path or --web-public)",
    )
    libsync.add_argument(
        "--web-public",
        default=None,
        help="Target marketing public dir (default: ~/skycache-web/public)",
    )
    libsync.add_argument(
        "--with-packs",
        action="store_true",
        help="Also build multilingual-literacy + literacy-starter pack zips",
    )
    libsync.set_defaults(func=cmd_library_ops, library_cmd="sync")
    libpk = lib_sub.add_parser(
        "pack-kits",
        help="Build USB pack profile zips (multilingual-literacy, literacy-starter)",
    )
    libpk.add_argument("--data-dir", default="data")
    libpk.add_argument("--out", default="data/library-pack-kits")
    libpk.add_argument(
        "--profiles",
        default=(
            "multilingual-literacy,literacy-starter,emergency-health,"
            "health-priority,stem-lite,archive-100mb"
        ),
        help="Comma-separated profile ids",
    )
    libpk.add_argument(
        "--content-dir",
        default=None,
        help="Package content root (default: samples/skybrary)",
    )
    libpk.add_argument("--no-zip", action="store_true")
    libpk.set_defaults(func=cmd_library_ops, library_cmd="pack-kits")
    libpb = lib_sub.add_parser(
        "pack-budgets",
        help="List size-bounded dual-access pack profiles (100MB / 1GB / clinic / STEM)",
    )
    libpb.add_argument(
        "--profiles",
        default=None,
        help="Optional comma-separated profile ids (default: all built-in)",
    )
    libpb.set_defaults(func=cmd_library_ops, library_cmd="pack-budgets")

    # Dual Radio Ops (v1.22.0) - top-level product surface
    dr = sub.add_parser(
        "dual-radio",
        help="Dual Radio Ops: doctor/status/export/kit (mesh day-one proof)",
    )
    dr_sub = dr.add_subparsers(dest="dual_radio_cmd", required=True)
    drdoc = dr_sub.add_parser("doctor", help="Sim vs field dual-radio readiness")
    drdoc.add_argument("--data-dir", default="data")
    drdoc.set_defaults(func=cmd_dual_radio_ops, dual_radio_cmd="doctor")
    drst = dr_sub.add_parser("status", help="Board matrix + environment snapshot")
    drst.add_argument("--data-dir", default="data")
    drst.set_defaults(func=cmd_dual_radio_ops, dual_radio_cmd="status")
    drexp = dr_sub.add_parser("export", help="Printable dual-radio board HTML")
    drexp.add_argument("--data-dir", default="data")
    drexp.add_argument("--out", default="data/ops/dual-radio-board.html")
    drexp.set_defaults(func=cmd_dual_radio_ops, dual_radio_cmd="export")
    drkit = dr_sub.add_parser("kit", help="Build dual-radio ops kit + zip")
    drkit.add_argument("--data-dir", default="data")
    drkit.add_argument("--out", default="data/dual-radio-kit")
    drkit.add_argument("--no-zip", action="store_true")
    drkit.set_defaults(func=cmd_dual_radio_ops, dual_radio_cmd="kit")

    # Field Mesh Ops (v1.6.0)
    mdoc = mesh_sub.add_parser("doctor", help="Mesh host + docs readiness (sim vs field)")
    mdoc.add_argument("--data-dir", default="data")
    mdoc.set_defaults(func=cmd_mesh_doctor)

    mready = mesh_sub.add_parser(
        "readiness",
        help="go_sim_mesh / go_field_mesh score (runs nexus validate sim)",
    )
    mready.add_argument("--data-dir", default="data")
    mready.add_argument("--nodes", type=int, default=2)
    mready.add_argument("--skip-sim", action="store_true", help="Doctor only, no sim round")
    mready.set_defaults(func=cmd_mesh_readiness)

    mdrill = mesh_sub.add_parser(
        "disaster-drill",
        help="Lab disaster priority flood + receipt JSON (no RF)",
    )
    mdrill.add_argument("--data-dir", default="data")
    mdrill.add_argument("--nodes", type=int, default=3)
    mdrill.add_argument("--keep", action="store_true", help="Keep sim dirs under data/")
    mdrill.set_defaults(func=cmd_mesh_disaster_drill)

    mkit = mesh_sub.add_parser(
        "field-kit",
        help="Build field mesh kit folder + zip for site downloads",
    )
    mkit.add_argument("--out", default="data/field-mesh-kit")
    mkit.add_argument("--no-zip", action="store_true")
    mkit.set_defaults(func=cmd_mesh_field_kit)

    gw = sub.add_parser("gateway", help="Gateway Ops: doctor, preset pull+passport, receipts, ethics kit")
    gw.add_argument("--data-dir", default="data")
    gw.add_argument("--sim", action="store_true", help="Simulated uplink / sim pull mode")
    gw.add_argument("--request", default="", help="(legacy) Queue open-content package request")
    gw.add_argument("--priority", default="education")
    gw.add_argument("--pull", action="store_true", help="(legacy) Run fair-share pull scheduler")
    gw.add_argument("--presets", action="store_true", help="(legacy) List open-mirror presets")
    gw.add_argument("--receipts", action="store_true", help="(legacy) Show local pull receipts")
    gw.add_argument(
        "--quota-mb",
        type=int,
        default=None,
        help="Set daily fair-share quota (MB) for this process snapshot",
    )
    gw.set_defaults(func=cmd_gateway, gateway_cmd=None)
    gw_sub = gw.add_subparsers(dest="gateway_cmd")

    gwd = gw_sub.add_parser("doctor", help="Gateway ethics readiness")
    gwd.add_argument("--data-dir", default="data")
    gwd.add_argument("--sim", action="store_true")
    gwd.set_defaults(func=cmd_gateway, gateway_cmd="doctor")

    gws = gw_sub.add_parser("status", help="Uplink + quota + presets snapshot")
    gws.add_argument("--data-dir", default="data")
    gws.add_argument("--sim", action="store_true")
    gws.set_defaults(func=cmd_gateway, gateway_cmd="status")

    gwp = gw_sub.add_parser("presets", help="List open-mirror presets")
    gwp.add_argument("--data-dir", default="data")
    gwp.set_defaults(func=cmd_gateway, gateway_cmd="presets")

    gwpp = gw_sub.add_parser(
        "pull-preset",
        help="Preset open-fetch + license passport + receipt",
    )
    gwpp.add_argument("preset_id", help="e.g. gutenberg-sample")
    gwpp.add_argument("--data-dir", default="data")
    gwpp.add_argument("--dry-run", action="store_true", help="Validate only; no download")
    gwpp.add_argument(
        "--sim",
        action="store_true",
        dest="sim_pull",
        help="Write local sim payload without network",
    )
    gwpp.add_argument("--force", action="store_true", help="Ignore quota soft-stop")
    gwpp.set_defaults(func=cmd_gateway, gateway_cmd="pull-preset", sim=False)

    gwr = gw_sub.add_parser("receipts", help="Local pull receipt audit trail")
    gwr.add_argument("--data-dir", default="data")
    gwr.add_argument("--limit", type=int, default=50)
    gwr.set_defaults(func=cmd_gateway, gateway_cmd="receipts")

    gwek = gw_sub.add_parser("ethics-kit", help="Build ethics kit folder + zip")
    gwek.add_argument("--data-dir", default="data")
    gwek.add_argument("--out", default="data/gateway-ethics-kit")
    gwek.set_defaults(func=cmd_gateway, gateway_cmd="ethics-kit")

    nx = sub.add_parser("nexus", help="SkyCache Nexus fabric (mesh + DTN + gateway)")
    nx_sub = nx.add_subparsers(dest="nexus_cmd", required=True)

    nxd = nx_sub.add_parser("doctor", help="Nexus legal rails + spectrum checks")
    nxd.add_argument("--data-dir", default="data")
    nxd.set_defaults(func=cmd_nexus_doctor)

    nxs = nx_sub.add_parser("sim", help="Multi-node fabric simulation (no RF)")
    nxs.add_argument("--nodes", type=int, default=3)
    nxs.add_argument("--seed-nodes", type=int, default=1, help="Nodes seeded with samples")
    nxs.add_argument("--base-dir", default="", help="Persist sim dirs (default: temp)")
    nxs.add_argument("--disaster", action="store_true", help="Enable disaster priority flood")
    nxs.add_argument("--keep", action="store_true", help="Do not teardown temp dirs")
    nxs.set_defaults(func=cmd_nexus_sim)

    nxst = nx_sub.add_parser("status", help="Combined mesh + DTN + gateway snapshot")
    nxst.add_argument("--data-dir", default="data")
    nxst.set_defaults(func=cmd_nexus_status)

    nxv = nx_sub.add_parser(
        "validate",
        help="2/3-node mesh validation (sim) - village weekend acceptance",
    )
    nxv.add_argument("--nodes", type=int, default=2, help="2 or 3 nodes")
    nxv.add_argument("--base-dir", default="", help="Persist sim dirs (default: temp)")
    nxv.add_argument("--disaster", action="store_true")
    nxv.add_argument("--keep", action="store_true")
    nxv.add_argument(
        "--checklist",
        action="store_true",
        help="Print field checklist IDs (pair with docs/mesh-field-checklist.md)",
    )
    nxv.set_defaults(func=cmd_nexus_validate)

    nxf = nx_sub.add_parser(
        "federation",
        help="Works-manifest multi-node federation sim (open packs only)",
    )
    nxf.add_argument("--nodes", type=int, default=3)
    nxf.add_argument("--rounds", type=int, default=1)
    nxf.add_argument("--base-dir", default="", help="Persist sim dirs (default: data/federation-sim)")
    nxf.set_defaults(func=cmd_nexus_federation_sim)

    search = sub.add_parser("search", help="Search local content catalog")
    search.add_argument("q", nargs="?", default="", help="Search query")
    search.add_argument("--category", default="")
    search.add_argument("--limit", type=int, default=40)
    search.add_argument("--data-dir", default="data")
    search.set_defaults(func=cmd_search)

    lic = sub.add_parser("licenses", help="Licenses Ops: doctor, status, export, kit")
    lic.add_argument("--data-dir", default="data")
    lic.add_argument("--summary", action="store_true", help="(legacy) summary only")
    lic.add_argument(
        "--html",
        default="",
        help="(legacy) Write printable HTML inventory",
    )
    lic.set_defaults(func=cmd_licenses, licenses_cmd=None)
    lic_sub = lic.add_subparsers(dest="licenses_cmd")
    ldoc = lic_sub.add_parser("doctor", help="License inventory readiness")
    ldoc.add_argument("--data-dir", default="data")
    ldoc.set_defaults(func=cmd_licenses, licenses_cmd="doctor")
    lst = lic_sub.add_parser("status", help="Inventory snapshot")
    lst.add_argument("--data-dir", default="data")
    lst.set_defaults(func=cmd_licenses, licenses_cmd="status")
    lex = lic_sub.add_parser("export", help="Printable HTML inventory")
    lex.add_argument("--data-dir", default="data")
    lex.add_argument("--out", default="data/ops/licenses-inventory.html")
    lex.set_defaults(func=cmd_licenses, licenses_cmd="export")
    lkit = lic_sub.add_parser("kit", help="Build licenses kit folder + zip")
    lkit.add_argument("--data-dir", default="data")
    lkit.add_argument("--out", default="data/licenses-kit")
    lkit.add_argument("--no-zip", action="store_true")
    lkit.set_defaults(func=cmd_licenses, licenses_cmd="kit")

    sky = sub.add_parser("skybrary", help="Skybrary (Sky Library) archive layer")
    sky_sub = sky.add_subparsers(dest="skybrary_cmd", required=True)
    skd = sky_sub.add_parser(
        "doctor",
        help="Skybrary mission + catalog check; --verify runs content-tree integrity (bit-rot)",
    )
    skd.add_argument("--data-dir", default="data")
    skd.add_argument(
        "--verify",
        action="store_true",
        help="Verify sha256/file presence for all packages under data/content",
    )
    skd.add_argument(
        "--record",
        action="store_true",
        help="With --verify, persist last report under data/ops/bitrot-last.json",
    )
    skd.add_argument("--json", action="store_true", help="With --verify, also print full integrity JSON")
    skd.set_defaults(func=cmd_skybrary_doctor)
    sks = sky_sub.add_parser("samples", help="Build public-domain sample text packs")
    sks.add_argument("--out", default="samples/skybrary")
    sks.add_argument("--ingest", action="store_true", help="Ingest into content + works FTS catalog")
    sks.add_argument("--data-dir", default="data")
    sks.set_defaults(func=cmd_skybrary_samples)
    skzn = sky_sub.add_parser(
        "zero-network-kit",
        help="Kit for phones with NO Wi-Fi and NO cell (USB/SD/BT/pre-deploy; open READ-OFFLINE.html)",
    )
    skzn.add_argument(
        "--out",
        default="samples/phone-zero-network",
        help="Output directory for the kit",
    )
    skzn.add_argument(
        "--zip",
        action="store_true",
        help="Also write skycache-zero-network-demo-kit.zip inside out dir",
    )
    skzn.set_defaults(func=cmd_skybrary_zero_network_kit)
    skq = sky_sub.add_parser("search", help="Full-text search works catalog (FTS5)")
    skq.add_argument("q", nargs="?", default="")
    skq.add_argument("--lang", default="")
    skq.add_argument("--subject", default="")
    skq.add_argument("--license", default="")
    skq.add_argument("--limit", type=int, default=40)
    skq.add_argument("--data-dir", default="data")
    skq.set_defaults(func=cmd_skybrary_search)

    skp = sky_sub.add_parser("pack", help="Build size-bounded offline kit from profile")
    skp.add_argument("--profile", default="all-open-small")
    skp.add_argument("--out", default="data/packs/out")
    skp.add_argument("--list", action="store_true", help="List built-in profiles")
    skp.add_argument("--data-dir", default="data")
    skp.set_defaults(func=cmd_skybrary_pack)

    skcat = sky_sub.add_parser(
        "export-catalog",
        help="Export static dual-access catalog v2 (JSON+HTML) for online /library/",
    )
    skcat.add_argument("--out", default="data/catalog-export")
    skcat.add_argument("--data-dir", default="data")
    skcat.add_argument("--limit", type=int, default=5000)
    skcat.add_argument("--json-only", action="store_true", help="Skip index.html")
    skcat.add_argument(
        "--site-base",
        default="https://skycache.jonbailey.xyz",
        help="Base URL written into dual_access metadata",
    )
    skcat.add_argument(
        "--starter-kits",
        action="store_true",
        help="Also zip literacy/emergency starter kits under out/packs/",
    )
    skcat.set_defaults(func=cmd_skybrary_export_catalog)

    # --- Bulk Open Corpus Ops (v1.5.0 + v1.19 export/kit) ---
    skcorp = sky_sub.add_parser(
        "corpus",
        help="Bulk open corpus ops: doctor, status, export, kit, batch (legal only)",
    )
    skcorp_sub = skcorp.add_subparsers(dest="corpus_cmd", required=True)
    skcd = skcorp_sub.add_parser("doctor", help="Corpus pipeline readiness (fixtures + license gate)")
    skcd.add_argument("--data-dir", default="data")
    skcd.set_defaults(func=cmd_skybrary_corpus, corpus_cmd="doctor")
    skcs = skcorp_sub.add_parser("status", help="Local corpus scale snapshot + passport gaps")
    skcs.add_argument("--data-dir", default="data")
    skcs.set_defaults(func=cmd_skybrary_corpus, corpus_cmd="status")
    skce = skcorp_sub.add_parser("export", help="Printable corpus board HTML")
    skce.add_argument("--data-dir", default="data")
    skce.add_argument("--out", default="data/ops/corpus-board.html")
    skce.set_defaults(func=cmd_skybrary_corpus, corpus_cmd="export")
    skck = skcorp_sub.add_parser("kit", help="Build corpus kit + zip")
    skck.add_argument("--data-dir", default="data")
    skck.add_argument("--out", default="data/corpus-kit")
    skck.add_argument("--no-zip", action="store_true")
    skck.set_defaults(func=cmd_skybrary_corpus, corpus_cmd="kit")
    skcsm = skcorp_sub.add_parser(
        "sample-manifest",
        help="Write offline demo batch JSON (fixtures + samples only)",
    )
    skcsm.add_argument("--out", default="data/corpus-batch-demo.json")
    skcsm.set_defaults(func=cmd_skybrary_corpus, corpus_cmd="sample-manifest")
    skcb = skcorp_sub.add_parser(
        "batch",
        help="Run a legal batch manifest (folder / gutenberg / oa / open_url)",
    )
    skcb.add_argument("--manifest", required=True, help="Path to corpus batch JSON")
    skcb.add_argument("--data-dir", default="data")
    skcb.add_argument("--out", default="", help="Build root (default: data/skybrary-build/batch)")
    skcb.add_argument("--ingest", action="store_true", help="Register into content + Skybrary FTS")
    skcb.add_argument("--dry-run", action="store_true")
    skcb.add_argument(
        "--allow-local",
        action="store_true",
        help="Allow local fixture paths in catalogs (CI/sim)",
    )
    skcb.set_defaults(func=cmd_skybrary_corpus, corpus_cmd="batch")

    skpg = sky_sub.add_parser(
        "import-gutenberg-catalog",
        help="Batch import from Gutenberg-style catalog JSON/CSV (operator-run, rate-limited)",
    )
    skpg.add_argument(
        "--catalog",
        required=True,
        help="Path to catalog snapshot JSON/CSV (fixture for sim; never pirate mirrors)",
    )
    skpg.add_argument("--out", default="data/skybrary-build/gutenberg")
    skpg.add_argument(
        "--license",
        default="project gutenberg",
        help="Required open license (default: project gutenberg)",
    )
    skpg.add_argument("--lang", default="en", help="Language filter (empty=all)")
    skpg.add_argument("--subject", default="", help="Optional subject/title substring filter")
    skpg.add_argument("--max", type=int, default=25, help="Max works per batch")
    skpg.add_argument(
        "--max-bytes",
        type=int,
        default=50 * 1024 * 1024,
        help="Stop after this many total payload bytes",
    )
    skpg.add_argument("--delay", type=float, default=1.5, help="Seconds between remote fetches")
    skpg.add_argument("--dry-run", action="store_true", help="List selected rows only")
    skpg.add_argument(
        "--allow-local",
        action="store_true",
        help="Allow local file paths in catalog (fixtures / sim)",
    )
    skpg.add_argument("--ingest", action="store_true", help="Register into content + Skybrary FTS")
    skpg.add_argument("--data-dir", default="data")
    skpg.set_defaults(func=cmd_skybrary_import_gutenberg_catalog)

    skoa = sky_sub.add_parser(
        "import-oa-science",
        help="Batch import open-access science catalog (arXiv/PMC-style; license-gated)",
    )
    skoa.add_argument("--catalog", required=True, help="JSON/CSV catalog snapshot (fixture OK)")
    skoa.add_argument("--out", default="data/skybrary-build/oa-science")
    skoa.add_argument("--license", default="open-access")
    skoa.add_argument("--max", type=int, default=20)
    skoa.add_argument("--max-bytes", type=int, default=80 * 1024 * 1024)
    skoa.add_argument("--delay", type=float, default=2.0)
    skoa.add_argument("--dry-run", action="store_true")
    skoa.add_argument("--allow-local", action="store_true")
    skoa.add_argument("--ingest", action="store_true")
    skoa.add_argument("--data-dir", default="data")
    skoa.set_defaults(func=cmd_skybrary_import_oa_science)

    skprov = sky_sub.add_parser(
        "provenance",
        help="Batch provenance report for content tree (partners/regulators)",
    )
    skprov.add_argument("--data-dir", default="data")
    skprov.add_argument("--out", default="", help="Default: data/provenance-report.json")
    skprov.set_defaults(func=cmd_skybrary_provenance)

    skx = sky_sub.add_parser(
        "export-manifest",
        help="Export works_manifest JSON for catalog federation (metadata only)",
    )
    skx.add_argument("--out", default="data/works-manifest.json")
    skx.add_argument("--limit", type=int, default=10_000)
    skx.add_argument("--data-dir", default="data")
    skx.set_defaults(func=cmd_skybrary_export_manifest)

    ski = sky_sub.add_parser(
        "import-manifest",
        help="Import peer works_manifest (metadata; pair with handoff for packages)",
    )
    ski.add_argument("path", help="Path to works-manifest.json")
    ski.add_argument("--data-dir", default="data")
    ski.set_defaults(func=cmd_skybrary_import_manifest)

    skif = sky_sub.add_parser(
        "import-folder",
        help="Import directory of open .txt/.epub (license required)",
    )
    skif.add_argument("path", help="Directory containing .txt/.md/.html/.epub")
    skif.add_argument(
        "--license",
        required=True,
        help="Required open license (public domain, CC-BY-4.0, project gutenberg, ...)",
    )
    skif.add_argument("--out", default="data/skybrary-build/corpus")
    skif.add_argument("--lang", default="en")
    skif.add_argument("--subjects", default="corpus_import,literature_pd")
    skif.add_argument("--creators", default="")
    skif.add_argument("--id-prefix", default="corpus")
    skif.add_argument("--recursive", action="store_true")
    skif.add_argument("--max-files", type=int, default=200)
    skif.add_argument(
        "--ingest",
        action="store_true",
        help="Register into content catalog + Skybrary FTS",
    )
    skif.add_argument("--data-dir", default="data")
    skif.set_defaults(func=cmd_skybrary_import_folder)

    skio = sky_sub.add_parser(
        "import-open",
        help="Fetch one allowlisted open URL (Gutenberg-style) into a package",
    )
    skio.add_argument("url", help="HTTPS URL on open-content allowlist (e.g. gutenberg.org)")
    skio.add_argument(
        "--license",
        required=True,
        help="Required open license (e.g. project gutenberg, public domain)",
    )
    skio.add_argument("--out", default="data/skybrary-build/open")
    skio.add_argument("--title", default="")
    skio.add_argument("--id", default="", help="Optional work/package id")
    skio.add_argument("--lang", default="en")
    skio.add_argument("--subjects", default="corpus_import,open_http")
    skio.add_argument("--max-mb", type=int, default=20)
    skio.add_argument(
        "--ingest",
        action="store_true",
        help="Register into content catalog + Skybrary FTS",
    )
    skio.add_argument("--data-dir", default="data")
    skio.set_defaults(func=cmd_skybrary_import_open)

    # Full legal capability surface
    cap = sub.add_parser("capabilities", help="Capabilities Ops: legal matrix doctor, status, export, kit")
    cap.add_argument("--data-dir", default="data")
    cap.add_argument("--sim", action="store_true")
    cap.add_argument("--json", action="store_true", help="(legacy) JSON matrix dump")
    cap.set_defaults(func=cmd_capabilities, capabilities_cmd=None)
    cap_sub = cap.add_subparsers(dest="capabilities_cmd")
    cdoc = cap_sub.add_parser("doctor", help="Legal onboarding readiness")
    cdoc.add_argument("--data-dir", default="data")
    cdoc.add_argument("--sim", action="store_true")
    cdoc.set_defaults(func=cmd_capabilities, capabilities_cmd="doctor")
    cst = cap_sub.add_parser("status", help="Full matrix JSON")
    cst.add_argument("--data-dir", default="data")
    cst.add_argument("--sim", action="store_true")
    cst.set_defaults(func=cmd_capabilities, capabilities_cmd="status")
    cexp = cap_sub.add_parser("export", help="Printable HTML matrix")
    cexp.add_argument("--data-dir", default="data")
    cexp.add_argument("--sim", action="store_true")
    cexp.add_argument("--out", default="data/ops/capabilities-matrix.html")
    cexp.set_defaults(func=cmd_capabilities, capabilities_cmd="export")
    ckit = cap_sub.add_parser("kit", help="Build capabilities kit + zip")
    ckit.add_argument("--data-dir", default="data")
    ckit.add_argument("--sim", action="store_true")
    ckit.add_argument("--out", default="data/capabilities-kit")
    ckit.add_argument("--no-zip", action="store_true")
    ckit.set_defaults(func=cmd_capabilities, capabilities_cmd="kit")

    ofetch = sub.add_parser("open-fetch", help="Allowlisted open HTTPS download")
    ofetch.add_argument("url")
    ofetch.add_argument("--out", required=True)
    ofetch.add_argument("--max-mb", type=int, default=50)
    ofetch.add_argument("--data-dir", default="data")
    ofetch.set_defaults(func=cmd_open_fetch)

    ver = sub.add_parser("verify", help="Verify package or content tree integrity")
    ver.add_argument("path", help="Package dir or content/ tree")
    ver.set_defaults(func=cmd_verify_tree)

    ops = sub.add_parser(
        "ops",
        help="Local Ops: privacy-preserving doctor, status, printable board, kit (fleet OFF)",
    )
    ops_sub = ops.add_subparsers(dest="ops_cmd", required=True)
    odoc = ops_sub.add_parser("doctor", help="Local ops readiness (fleet OFF, disk headroom)")
    odoc.add_argument("--data-dir", default="data")
    odoc.set_defaults(func=cmd_ops, ops_cmd="doctor")
    ops_st = ops_sub.add_parser("status", help="Disk, power, peers, pack freshness, bit-rot schedule")
    ops_st.add_argument("--data-dir", default="data")
    ops_st.set_defaults(func=cmd_ops, ops_cmd="status")
    oexp = ops_sub.add_parser("export", help="Printable local ops board HTML")
    oexp.add_argument("--data-dir", default="data")
    oexp.add_argument("--out", default="data/ops/local-ops-board.html")
    oexp.set_defaults(func=cmd_ops, ops_cmd="export")
    okit = ops_sub.add_parser("kit", help="Build local ops kit + zip")
    okit.add_argument("--data-dir", default="data")
    okit.add_argument("--out", default="data/ops-kit")
    okit.add_argument("--no-zip", action="store_true")
    okit.set_defaults(func=cmd_ops, ops_cmd="kit")

    rep = sub.add_parser(
        "report",
        help="Node Report Ops: partner readiness passport rollup (doctor/status/export/kit)",
    )
    rep_sub = rep.add_subparsers(dest="report_cmd", required=True)
    rdoc = rep_sub.add_parser("doctor", help="Rollup readiness across ops surfaces")
    rdoc.add_argument("--data-dir", default="data")
    rdoc.set_defaults(func=cmd_report, report_cmd="doctor")
    rst = rep_sub.add_parser("status", help="Gate table + surface scores")
    rst.add_argument("--data-dir", default="data")
    rst.set_defaults(func=cmd_report, report_cmd="status")
    rexp = rep_sub.add_parser("export", help="Printable node readiness HTML")
    rexp.add_argument("--data-dir", default="data")
    rexp.add_argument("--out", default="data/ops/node-report.html")
    rexp.set_defaults(func=cmd_report, report_cmd="export")
    rkit = rep_sub.add_parser("kit", help="Build report kit + zip")
    rkit.add_argument("--data-dir", default="data")
    rkit.add_argument("--out", default="data/report-kit")
    rkit.add_argument("--no-zip", action="store_true")
    rkit.set_defaults(func=cmd_report, report_cmd="kit")

    corp = sub.add_parser(
        "corpus",
        help="Corpus Ops: legal bulk open corpus doctor/status/export/kit/batch",
    )
    corp_sub = corp.add_subparsers(dest="corpus_cmd", required=True)
    cdoc = corp_sub.add_parser("doctor", help="Corpus pipeline readiness")
    cdoc.add_argument("--data-dir", default="data")
    cdoc.set_defaults(func=cmd_corpus, corpus_cmd="doctor")
    cst = corp_sub.add_parser("status", help="Local scale + passport gaps")
    cst.add_argument("--data-dir", default="data")
    cst.set_defaults(func=cmd_corpus, corpus_cmd="status")
    cexp = corp_sub.add_parser("export", help="Printable corpus board HTML")
    cexp.add_argument("--data-dir", default="data")
    cexp.add_argument("--out", default="data/ops/corpus-board.html")
    cexp.set_defaults(func=cmd_corpus, corpus_cmd="export")
    ckit = corp_sub.add_parser("kit", help="Build corpus kit + zip")
    ckit.add_argument("--data-dir", default="data")
    ckit.add_argument("--out", default="data/corpus-kit")
    ckit.add_argument("--no-zip", action="store_true")
    ckit.set_defaults(func=cmd_corpus, corpus_cmd="kit")
    csm = corp_sub.add_parser("sample-manifest", help="Write offline demo batch JSON")
    csm.add_argument("--out", default="data/corpus-batch-demo.json")
    csm.add_argument("--data-dir", default="data")
    csm.set_defaults(func=cmd_corpus, corpus_cmd="sample-manifest")
    cbat = corp_sub.add_parser("batch", help="Run legal batch manifest")
    cbat.add_argument("--manifest", required=True)
    cbat.add_argument("--data-dir", default="data")
    cbat.add_argument("--out", default="")
    cbat.add_argument("--ingest", action="store_true")
    cbat.add_argument("--dry-run", action="store_true")
    cbat.add_argument("--allow-local", action="store_true")
    cbat.set_defaults(func=cmd_corpus, corpus_cmd="batch")

    seal = sub.add_parser(
        "seal",
        help="Seal Ops: golden Pi fleet doctor, status, printable board, kit",
    )
    seal_sub = seal.add_subparsers(dest="seal_cmd", required=True)
    sdoc = seal_sub.add_parser("doctor", help="Host readiness for kit bake vs Linux seal")
    sdoc.set_defaults(func=cmd_seal, seal_cmd="doctor")
    sst = seal_sub.add_parser("status", help="Host probe + bake plan summary")
    sst.set_defaults(func=cmd_seal, seal_cmd="status")
    sexp = seal_sub.add_parser("export", help="Printable seal/flash board HTML")
    sexp.add_argument("--out", default="data/ops/seal-board.html")
    sexp.set_defaults(func=cmd_seal, seal_cmd="export")
    skit = seal_sub.add_parser("kit", help="Build seal kit + zip")
    skit.add_argument("--out", default="data/seal-kit")
    skit.add_argument("--no-zip", action="store_true")
    skit.set_defaults(func=cmd_seal, seal_cmd="kit")

    fed = sub.add_parser(
        "federation",
        help="Federation Ops: multi-village works/package gossip doctor, sim, kit",
    )
    fed_sub = fed.add_subparsers(dest="federation_cmd", required=True)
    fdd = fed_sub.add_parser("doctor", help="Federation readiness")
    fdd.add_argument("--data-dir", default="data")
    fdd.set_defaults(func=cmd_federation, federation_cmd="doctor")
    fds = fed_sub.add_parser("status", help="Local gossip snapshot stats")
    fds.add_argument("--data-dir", default="data")
    fds.set_defaults(func=cmd_federation, federation_cmd="status")
    fde = fed_sub.add_parser("export-gossip", help="Write gossip JSON for USB/mesh peer")
    fde.add_argument("--data-dir", default="data")
    fde.add_argument("--out", default="data/federation/gossip.json")
    fde.add_argument("--compact", action="store_true", help="Force compact works_manifest")
    fde.add_argument("--full", action="store_true", help="Force full works_manifest")
    fde.add_argument("--max-tier", type=int, default=None)
    fde.set_defaults(func=cmd_federation, federation_cmd="export-gossip")
    fdi = fed_sub.add_parser("import-gossip", help="Import peer gossip JSON")
    fdi.add_argument("path")
    fdi.add_argument("--data-dir", default="data")
    fdi.add_argument("--peer-content", default="", help="Peer content/ root for package copy")
    fdi.set_defaults(func=cmd_federation, federation_cmd="import-gossip")
    fdsim = fed_sub.add_parser("sim", help="Multi-node federation sim + receipt")
    fdsim.add_argument("--data-dir", default="data")
    fdsim.add_argument("--nodes", type=int, default=2)
    fdsim.add_argument("--rounds", type=int, default=1)
    fdsim.add_argument("--base-dir", default="")
    fdsim.add_argument("--no-seed", action="store_true")
    fdsim.set_defaults(func=cmd_federation, federation_cmd="sim")
    fdk = fed_sub.add_parser("kit", help="Build federation kit folder + zip")
    fdk.add_argument("--data-dir", default="data")
    fdk.add_argument("--out", default="data/federation-kit")
    fdk.add_argument("--no-zip", action="store_true")
    fdk.set_defaults(func=cmd_federation, federation_cmd="kit")

    vd = sub.add_parser(
        "village-day",
        help="Village Day Ops: weekend stand-up doctor, readiness, runbook, kit",
    )
    vd_sub = vd.add_subparsers(dest="village_day_cmd", required=True)
    vdd = vd_sub.add_parser("doctor", help="Aggregate handoff/mesh/gateway/partner readiness")
    vdd.add_argument("--data-dir", default="data")
    vdd.add_argument("--sim", action="store_true", default=True)
    vdd.set_defaults(func=cmd_village_day, village_day_cmd="doctor")
    vdr = vd_sub.add_parser("readiness", help="Write go/no-go receipt under data/ops/")
    vdr.add_argument("--data-dir", default="data")
    vdr.add_argument("--sim", action="store_true", default=True)
    vdr.set_defaults(func=cmd_village_day, village_day_cmd="readiness")
    vdrb = vd_sub.add_parser("runbook", help="Write weekend RUNBOOK.md + doctor JSON")
    vdrb.add_argument("--data-dir", default="data")
    vdrb.add_argument("--out", default="data/village-day")
    vdrb.set_defaults(func=cmd_village_day, village_day_cmd="runbook")
    vdk = vd_sub.add_parser("kit", help="Build village-day kit folder + zip")
    vdk.add_argument("--data-dir", default="data")
    vdk.add_argument("--out", default="data/village-day-kit")
    vdk.add_argument("--no-zip", action="store_true")
    vdk.set_defaults(func=cmd_village_day, village_day_cmd="kit")

    br = sub.add_parser("bitrot", help="Bit-rot schedule templates + integrity recording")
    br_sub = br.add_subparsers(dest="bitrot_cmd", required=True)
    brit = br_sub.add_parser("install-templates", help="Write systemd timer + cron examples")
    brit.add_argument("--out", default="deploy/bitrot")
    brit.add_argument(
        "--data-dir-path",
        default="/var/lib/skycache",
        help="Absolute data dir path for unit files (Linux node)",
    )
    brit.set_defaults(func=cmd_bitrot_install_templates)

    pwr = sub.add_parser(
        "power",
        help="Power Ops: solar/battery doctor, guidance status, maintainer sheet, kit",
    )
    pwr_sub = pwr.add_subparsers(dest="power_cmd", required=True)
    pwd = pwr_sub.add_parser("doctor", help="Power path readiness")
    pwd.add_argument("--data-dir", default="data")
    pwd.set_defaults(func=cmd_power, power_cmd="doctor")
    pws = pwr_sub.add_parser("status", help="SOC/mode/guidance snapshot")
    pws.add_argument("--data-dir", default="data")
    pws.set_defaults(func=cmd_power, power_cmd="status")
    pwsh = pwr_sub.add_parser("sheet", help="Write printable power maintainer sheet")
    pwsh.add_argument("--data-dir", default="data")
    pwsh.add_argument("--out", default="data/ops/power-sheet.html")
    pwsh.set_defaults(func=cmd_power, power_cmd="sheet")
    pwk = pwr_sub.add_parser("kit", help="Build power kit folder + zip")
    pwk.add_argument("--data-dir", default="data")
    pwk.add_argument("--out", default="data/power-kit")
    pwk.add_argument("--no-zip", action="store_true")
    pwk.set_defaults(func=cmd_power, power_cmd="kit")

    dis = sub.add_parser(
        "disaster",
        help="Disaster Drill Ops: doctor, lab run, printable report, closeout, kit",
    )
    dis_sub = dis.add_subparsers(dest="disaster_cmd", required=True)
    dsd = dis_sub.add_parser("doctor", help="Drill readiness")
    dsd.add_argument("--data-dir", default="data")
    dsd.set_defaults(func=cmd_disaster, disaster_cmd="doctor")
    dsr = dis_sub.add_parser("run", help="Lab disaster priority flood + receipt")
    dsr.add_argument("--data-dir", default="data")
    dsr.add_argument("--nodes", type=int, default=3)
    dsr.add_argument("--keep", action="store_true")
    dsr.set_defaults(func=cmd_disaster, disaster_cmd="run")
    dsrep = dis_sub.add_parser("report", help="Printable HTML drill report")
    dsrep.add_argument("--data-dir", default="data")
    dsrep.add_argument("--out", default="data/ops/disaster-report.html")
    dsrep.add_argument("--run", action="store_true", help="Run lab drill first")
    dsrep.add_argument("--nodes", type=int, default=3)
    dsrep.set_defaults(func=cmd_disaster, disaster_cmd="report")
    dsc = dis_sub.add_parser("closeout", help="Post-drill: mode OFF + receipt check")
    dsc.add_argument("--data-dir", default="data")
    dsc.set_defaults(func=cmd_disaster, disaster_cmd="closeout")
    dsk = dis_sub.add_parser("kit", help="Build disaster kit folder + zip")
    dsk.add_argument("--data-dir", default="data")
    dsk.add_argument("--out", default="data/disaster-kit")
    dsk.add_argument("--no-zip", action="store_true")
    dsk.add_argument("--run", action="store_true")
    dsk.set_defaults(func=cmd_disaster, disaster_cmd="kit")

    integ = sub.add_parser(
        "integrity",
        help="Integrity Ops: bit-rot doctor, verify, printable report, kit",
    )
    integ_sub = integ.add_subparsers(dest="integrity_cmd", required=True)
    ind = integ_sub.add_parser("doctor", help="Integrity schedule + content readiness")
    ind.add_argument("--data-dir", default="data")
    ind.add_argument("--max-age-days", type=float, default=10.0)
    ind.set_defaults(func=cmd_integrity, integrity_cmd="doctor")
    inv = integ_sub.add_parser("verify", help="Verify content tree; record bitrot-last.json")
    inv.add_argument("--data-dir", default="data")
    inv.add_argument("--no-record", action="store_true")
    inv.set_defaults(func=cmd_integrity, integrity_cmd="verify")
    inr = integ_sub.add_parser("report", help="Printable HTML integrity report")
    inr.add_argument("--data-dir", default="data")
    inr.add_argument("--out", default="data/ops/integrity-report.html")
    inr.add_argument("--verify", action="store_true", help="Run verify --record first")
    inr.set_defaults(func=cmd_integrity, integrity_cmd="report")
    init = integ_sub.add_parser("install-templates", help="Write systemd/cron bit-rot templates")
    init.add_argument("--out", default="deploy/bitrot")
    init.add_argument("--data-dir-path", default="/var/lib/skycache")
    init.add_argument("--data-dir", default="data")
    init.set_defaults(func=cmd_integrity, integrity_cmd="install-templates")
    ink = integ_sub.add_parser("kit", help="Build integrity kit folder + zip")
    ink.add_argument("--data-dir", default="data")
    ink.add_argument("--out", default="data/integrity-kit")
    ink.add_argument("--no-zip", action="store_true")
    ink.add_argument("--verify", action="store_true")
    ink.set_defaults(func=cmd_integrity, integrity_cmd="kit")

    # Phone Handoff Ops (v1.7) - subcommands; bare `handoff export` also works
    ble = sub.add_parser("handoff", help="Phone/USB handoff: doctor, join-card QR, export, import")
    ble_sub = ble.add_subparsers(dest="handoff_cmd", required=False)
    # default export when no subcommand (legacy)
    ble.add_argument("--data-dir", default="data")
    ble.add_argument("--out", default="data/handoff")
    ble.add_argument("--packages", default="", help="Comma package ids (default: first N)")
    ble.add_argument("--limit", type=int, default=20)
    ble.add_argument("--portal-url", default="http://10.42.0.1:8080/")
    ble.add_argument("--ssid", default="SkyCache-Village")
    ble.add_argument("--no-join", action="store_true")
    ble.add_argument("--no-zip", action="store_true")
    ble.set_defaults(func=cmd_ble_mule_export)

    hdoc = ble_sub.add_parser("doctor", help="Phone path readiness (demos + packages)")
    hdoc.add_argument("--data-dir", default="data")
    hdoc.set_defaults(func=cmd_handoff, handoff_cmd="doctor")

    hjoin = ble_sub.add_parser("join-card", help="Write join.html + QR for hub SSID/portal")
    hjoin.add_argument("--data-dir", default="data")
    hjoin.add_argument("--out", default="")
    hjoin.add_argument("--portal-url", default="http://10.42.0.1:8080/")
    hjoin.add_argument("--ssid", default="SkyCache-Village")
    hjoin.add_argument("--node-name", default="")
    hjoin.set_defaults(func=cmd_handoff, handoff_cmd="join-card")

    hexp = ble_sub.add_parser("export", help="Export mule packages + join card under /handoff/")
    hexp.add_argument("--data-dir", default="data")
    hexp.add_argument("--out", default="")
    hexp.add_argument("--packages", default="")
    hexp.add_argument("--limit", type=int, default=20)
    hexp.add_argument("--portal-url", default="http://10.42.0.1:8080/")
    hexp.add_argument("--ssid", default="SkyCache-Village")
    hexp.add_argument("--no-join", action="store_true")
    hexp.add_argument("--no-zip", action="store_true")
    hexp.set_defaults(func=cmd_handoff, handoff_cmd="export")

    himp = ble_sub.add_parser("import", help="Import mule bundle dir or zip into this node")
    himp.add_argument("path", help="Bundle directory or .zip")
    himp.add_argument("--data-dir", default="data")
    himp.set_defaults(func=cmd_handoff, handoff_cmd="import")

    pi = sub.add_parser(
        "pi-image",
        help="Golden Node Bake Ops: plan, doctor, seal checklist, sealed-manifest, kit zip",
    )
    pi_sub = pi.add_subparsers(dest="pi_cmd", required=True)
    pid = pi_sub.add_parser("doctor", help="Host readiness for kit path vs seal path")
    pid.set_defaults(func=cmd_pi_image)
    pip = pi_sub.add_parser("plan", help="Print golden bake plan JSON")
    pip.add_argument("--hostname", default="skycache-village")
    pip.add_argument("--ssid", default="SkyCache-Village")
    pip.add_argument("--legal-rf-mode", default="receive_only")
    pip.add_argument("--mesh-mode", default="sim")
    pip.add_argument("--sdr", action="store_true", help="Include optional rtl-sdr packages")
    pip.set_defaults(func=cmd_pi_image)
    piw = pi_sub.add_parser("write", help="Write plan + verify + seal checklist to a directory")
    piw.add_argument("--out", default="data/pi-bake")
    piw.add_argument("--hostname", default="skycache-village")
    piw.add_argument("--ssid", default="SkyCache-Village")
    piw.add_argument("--legal-rf-mode", default="receive_only")
    piw.add_argument("--mesh-mode", default="sim")
    piw.add_argument("--sdr", action="store_true")
    piw.set_defaults(func=cmd_pi_image)
    pib = pi_sub.add_parser(
        "bundle",
        help="Build downloadable golden-SD kit zip for site/Release hosting",
    )
    pib.add_argument("--out", default="data/pi-download")
    pib.add_argument("--sdr", action="store_true")
    pib.set_defaults(func=cmd_pi_image)
    pisc = pi_sub.add_parser("seal-checklist", help="Write SEAL-CHECKLIST.md only")
    pisc.add_argument("--out", default="data/pi-bake")
    pisc.add_argument("--hostname", default="skycache-village")
    pisc.add_argument("--ssid", default="SkyCache-Village")
    pisc.add_argument("--legal-rf-mode", default="receive_only")
    pisc.add_argument("--mesh-mode", default="sim")
    pisc.add_argument("--sdr", action="store_true")
    pisc.set_defaults(func=cmd_pi_image)
    pih = pi_sub.add_parser("hash", help="SHA-256 a local sealed image file")
    pih.add_argument("path", help="Path to .img or .img.xz")
    pih.set_defaults(func=cmd_pi_image)
    pism = pi_sub.add_parser(
        "sealed-manifest",
        help="Register operator-hosted .img.xz metadata (URL + sha256; no binary in git)",
    )
    pism.add_argument("--url", required=True, help="https URL where operators can download the image")
    pism.add_argument("--sha256", default="", help="64-char hex digest")
    pism.add_argument("--path", default="", help="Local file to hash if --sha256 omitted")
    pism.add_argument("--size-bytes", type=int, default=None)
    pism.add_argument("--out", default="data/pi-download/sealed-manifest.json")
    pism.add_argument("--note", default="")
    pism.set_defaults(func=cmd_pi_image)

    maps = sub.add_parser("maps", help="Offline maps / MBTiles (operator extracts + blobs)")
    maps_sub = maps.add_subparsers(dest="maps_cmd", required=True)
    msample = maps_sub.add_parser("sample", help="Write tiny sample MBTiles fixture")
    msample.add_argument("--out", default="samples/packages/maps-local-001/sample-region.mbtiles")
    msample.add_argument("--data-dir", default="data")
    msample.set_defaults(func=cmd_maps_mbtiles)
    mimp = maps_sub.add_parser("import", help="Package operator MBTiles + optional blob put")
    mimp.add_argument("mbtiles", help="Path to .mbtiles file")
    mimp.add_argument("--out", default="data/content/maps-region-operator")
    mimp.add_argument("--license", default="ODbL")
    mimp.add_argument("--id", default="maps-region-operator")
    mimp.add_argument("--title", default="Offline region map (MBTiles)")
    mimp.add_argument("--data-dir", default="data")
    mimp.add_argument("--no-blob", action="store_true")
    mimp.set_defaults(func=cmd_maps_mbtiles)

    bl = sub.add_parser("blobs", help="Content-addressed blob store (dedup/integrity)")
    bl_sub = bl.add_subparsers(dest="blobs_cmd", required=True)
    bls = bl_sub.add_parser("stats", help="Blob store stats")
    bls.add_argument("--data-dir", default="data")
    bls.set_defaults(func=cmd_blobs)
    blp = bl_sub.add_parser("put", help="Store a file by SHA-256")
    blp.add_argument("path")
    blp.add_argument("--data-dir", default="data")
    blp.add_argument("--media-type", default="")
    blp.set_defaults(func=cmd_blobs)
    blv = bl_sub.add_parser("verify", help="Verify blob digest on disk")
    blv.add_argument("digest")
    blv.add_argument("--data-dir", default="data")
    blv.set_defaults(func=cmd_blobs)
    bli = bl_sub.add_parser("ingest-content", help="Hash large content-tree files into blobs")
    bli.add_argument("--data-dir", default="data")
    bli.set_defaults(func=cmd_blobs)

    pk = sub.add_parser(
        "partner",
        help="Partner Ops: doctor/status/export/ops-kit + field pilot kits (v1.21)",
    )
    pk_sub = pk.add_subparsers(dest="partner_cmd", required=True)

    pkdoc = pk_sub.add_parser("doctor", help="Partner pilot readiness (go_sim_pilot / go_field_rf)")
    pkdoc.add_argument("--data-dir", default="data")
    pkdoc.set_defaults(func=cmd_partner_ops, partner_cmd="doctor")
    pkst = pk_sub.add_parser("status", help="Readiness snapshot JSON")
    pkst.add_argument("--data-dir", default="data")
    pkst.set_defaults(func=cmd_partner_ops, partner_cmd="status")
    pkexp = pk_sub.add_parser("export", help="Printable partner board HTML")
    pkexp.add_argument("--data-dir", default="data")
    pkexp.add_argument("--out", default="data/ops/partner-board.html")
    pkexp.set_defaults(func=cmd_partner_ops, partner_cmd="export")
    pkok = pk_sub.add_parser("ops-kit", help="Build partner ops kit + zip")
    pkok.add_argument("--data-dir", default="data")
    pkok.add_argument("--out", default="data/partner-ops-kit")
    pkok.add_argument("--no-zip", action="store_true")
    pkok.set_defaults(func=cmd_partner_ops, partner_cmd="ops-kit")

    pkk = pk_sub.add_parser("kit", help="Build NGO/university/civil-protection pilot folder")
    pkk.add_argument("--type", default="ngo", choices=["ngo", "university", "civil-protection"])
    pkk.add_argument("--out", default="data/partner-kit")
    pkk.add_argument("--no-docs", action="store_true", help="Skip copying docs/* into kit")
    pkk.add_argument("--zip", action="store_true", help="Also write a .zip next to the kit folder")
    pkk.set_defaults(func=cmd_partner_kit)

    pkpa = pk_sub.add_parser(
        "package-all",
        help="Build all three kit types + zips + HOSTING.json for site downloads",
    )
    pkpa.add_argument("--out", default="data/partner-kits")
    pkpa.add_argument("--no-docs", action="store_true")
    pkpa.set_defaults(func=cmd_partner_package_all)

    pkr = pk_sub.add_parser("report", help="Pilot report tools")
    pkr_sub = pkr.add_subparsers(dest="partner_report_cmd", required=True)
    pkrv = pkr_sub.add_parser("validate", help="Validate filled pilot-report JSON")
    pkrv.add_argument("path", help="Path to pilot-report.json")
    pkrv.set_defaults(func=cmd_partner_report_validate)

    pkready = pk_sub.add_parser(
        "readiness",
        help="Alias of partner doctor (local lab go/no-go)",
    )
    pkready.add_argument("--data-dir", default="data")
    pkready.set_defaults(func=cmd_partner_readiness)

    # --- Live FTA RX ops (Phase 2 production) ---
    rx = sub.add_parser(
        "rx",
        help="RX Ops: live FTA doctor/status/export/kit + SatDump watch, passes, field log",
    )
    rx_sub = rx.add_subparsers(dest="rx_cmd", required=True)

    rxd = rx_sub.add_parser("doctor", help="RX readiness: go_rx_lab / go_rx_live + tools")
    rxd.add_argument("--data-dir", default="data")
    rxd.add_argument(
        "--legacy",
        action="store_true",
        help="Print raw skycache.rx.doctor.v1 only (no ops score)",
    )
    rxd.set_defaults(func=cmd_rx_doctor)

    rxst = rx_sub.add_parser("status", help="Station + duty + ready snapshot")
    rxst.add_argument("--data-dir", default="data")
    rxst.set_defaults(func=cmd_rx_status)

    rxexp = rx_sub.add_parser("export", help="Printable RX station board HTML")
    rxexp.add_argument("--data-dir", default="data")
    rxexp.add_argument("--out", default="data/ops/rx-station-board.html")
    rxexp.set_defaults(func=cmd_rx_export)

    rxkit = rx_sub.add_parser("kit", help="Build RX ops kit + zip")
    rxkit.add_argument("--data-dir", default="data")
    rxkit.add_argument("--out", default="data/rx-kit")
    rxkit.add_argument("--no-zip", action="store_true")
    rxkit.set_defaults(func=cmd_rx_kit)

    rxr = rx_sub.add_parser("recipes", help="List legal FTA RX recipes")
    rxr.set_defaults(func=cmd_rx_recipes)

    rxs = rx_sub.add_parser("station", help="Get/set ground station lat/lon/alt")
    rxs.add_argument("--data-dir", default="data")
    rxs.add_argument("--lat", type=float, default=None)
    rxs.add_argument("--lon", type=float, default=None)
    rxs.add_argument("--alt-m", type=float, default=0.0)
    rxs.add_argument("--name", default="village-station")
    rxs.add_argument("--antenna", default="")
    rxs.add_argument("--notes", default="")
    rxs.set_defaults(func=cmd_rx_station)

    rxp = rx_sub.add_parser("passes", help="Predict upcoming open-weather passes")
    rxp.add_argument("--data-dir", default="data")
    rxp.add_argument("--lat", type=float, default=None)
    rxp.add_argument("--lon", type=float, default=None)
    rxp.add_argument("--alt-m", type=float, default=0.0)
    rxp.add_argument("--hours", type=float, default=24.0)
    rxp.add_argument("--min-elev", type=float, default=15.0)
    rxp.set_defaults(func=cmd_rx_passes)

    rxt = rx_sub.add_parser("tle-import", help="Import operator TLE file into local cache")
    rxt.add_argument("path", help="Text file with 3-line TLE blocks")
    rxt.add_argument("--data-dir", default="data")
    rxt.set_defaults(func=cmd_rx_tle_import)

    rxw = rx_sub.add_parser(
        "watch",
        help="Watch SatDump product directory and auto-ingest weather packages",
    )
    rxw.add_argument("--dir", required=True, help="Directory SatDump writes products into")
    rxw.add_argument("--data-dir", default="data")
    rxw.add_argument("--recipe", default="product_import")
    rxw.add_argument("--satellite", default="")
    rxw.add_argument("--once", action="store_true", help="Single scan then exit")
    rxw.add_argument("--iterations", type=int, default=0, help="Poll N times then exit (0=forever)")
    rxw.add_argument("--interval", type=float, default=30.0, help="Seconds between polls")
    rxw.add_argument("--sim", action="store_true")
    rxw.set_defaults(func=cmd_rx_watch)

    rxi = rx_sub.add_parser("import", help="Ingest one image or package dir from a live pass")
    rxi.add_argument("path", help="PNG/JPG product or package directory with manifest.json")
    rxi.add_argument("--data-dir", default="data")
    rxi.add_argument("--recipe", default="product_import")
    rxi.add_argument("--satellite", default="")
    rxi.add_argument("--sim", action="store_true")
    rxi.set_defaults(func=cmd_rx_import)

    rxc = rx_sub.add_parser(
        "capture",
        help="Run SatDump CLI on IQ/baseband or image path then ingest",
    )
    rxc.add_argument("--recipe", default="noaa_apt", help="Recipe id from skycache rx recipes")
    rxc.add_argument("--input", required=True, help="Image, wav, or baseband path")
    rxc.add_argument("--data-dir", default="data")
    rxc.add_argument("--force-live", action="store_true", help="Allow hardware plugin in sim_mode")
    rxc.add_argument("--sim", action="store_true")
    rxc.set_defaults(func=cmd_rx_capture)

    rxl = rx_sub.add_parser("log", help="Append or list real-world pass field notes")
    rxl.add_argument("--data-dir", default="data")
    rxl.add_argument("--list", action="store_true")
    rxl.add_argument("--limit", type=int, default=40)
    rxl.add_argument("--satellite", default="")
    rxl.add_argument("--elevation", type=float, default=None)
    rxl.add_argument("--quality", default="")
    rxl.add_argument("--snr", type=float, default=None)
    rxl.add_argument("--recipe", default="")
    rxl.add_argument("--package-id", default="")
    rxl.add_argument("--notes", default="")
    rxl.add_argument("--operator", default="")
    rxl.set_defaults(func=cmd_rx_log)

    # --- Pass Autopilot (v1.2.0) ---
    rxsch = rx_sub.add_parser(
        "schedule",
        help="Pass Autopilot: bind upcoming FTA passes to recipes + SatDump sketches",
    )
    rxsch.add_argument("--data-dir", default="data")
    rxsch.add_argument("--hours", type=float, default=24.0)
    rxsch.add_argument("--min-elev", type=float, default=15.0)
    rxsch.add_argument("--products-dir", default="")
    rxsch.add_argument("--limit", type=int, default=40)
    rxsch.set_defaults(func=cmd_rx_schedule)

    rxarm = rx_sub.add_parser(
        "arm",
        help="Arm station for upcoming passes (enables watch auto field-log)",
    )
    rxarm.add_argument("--data-dir", default="data")
    rxarm.add_argument("--hours", type=float, default=12.0)
    rxarm.add_argument("--min-elev", type=float, default=15.0)
    rxarm.add_argument("--products-dir", default="")
    rxarm.add_argument(
        "--recipes",
        default="",
        help="Comma-separated recipe filter (e.g. noaa_apt,meteor_lrpt)",
    )
    rxarm.add_argument(
        "--no-auto-log",
        action="store_true",
        help="Do not auto-append field log on product watch",
    )
    rxarm.add_argument("--disarm", action="store_true", help="Clear arm state")
    rxarm.add_argument("--status", action="store_true", help="Duty board (arm + next pass)")
    rxarm.add_argument("--show", action="store_true", help="Show raw arm-state.json")
    rxarm.set_defaults(func=cmd_rx_arm)

    rxcmd = rx_sub.add_parser(
        "cmd",
        help="Print SatDump CLI sketch for a recipe or next scheduled pass",
    )
    rxcmd.add_argument("--data-dir", default="data")
    rxcmd.add_argument("--recipe", default="", help="Recipe id (default: next pass)")
    rxcmd.add_argument("--products-dir", default="")
    rxcmd.add_argument("--mode", default="live", choices=["live", "iq"])
    rxcmd.add_argument("--satdump", default="satdump", help="SatDump binary name/path")
    rxcmd.add_argument(
        "--next-pass",
        action="store_true",
        help="Include next schedule slot in the JSON",
    )
    rxcmd.set_defaults(func=cmd_rx_cmd)

    rxduty = rx_sub.add_parser("duty", help="Station duty board: arm + next pass countdown")
    rxduty.add_argument("--data-dir", default="data")
    rxduty.set_defaults(func=cmd_rx_duty)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging("INFO")
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
