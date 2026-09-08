"""Worldwide legal capability matrix - what this build can do, within the law."""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass, field
from typing import Any

from skycache.capabilities.modes import LegalRfMode


@dataclass
class Capability:
    id: str
    title: str
    category: str  # content_decode | content_open | local_tx | receive | distribution | archive
    legal_basis: str
    status: str  # available | optional_tool | sim_only | operator_licensed | disabled
    enabled: bool
    how: str
    never: str = ""


@dataclass
class CapabilityMatrix:
    legal_rf_mode: str
    capabilities: list[Capability] = field(default_factory=list)
    banned: list[str] = field(default_factory=list)
    banner: str = (
        "Full legal capability matrix. Open decode, open corpora, unlicensed mesh, "
        "optional licensed amateur *by operator*. Never commercial constellation piracy "
        "or default satellite uplink. Not free Starlink."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "legal_rf_mode": self.legal_rf_mode,
            "banner": self.banner,
            "capabilities": [asdict(c) for c in self.capabilities],
            "banned": self.banned,
            "summary": {
                "enabled": sum(1 for c in self.capabilities if c.enabled),
                "total": len(self.capabilities),
            },
        }


def _tool(name: str) -> bool:
    return shutil.which(name) is not None


def build_capability_matrix(
    *,
    legal_rf_mode: LegalRfMode | str = LegalRfMode.ISM_MESH,
    sim_mode: bool = False,
    amateur_license_affirmed: bool = False,
    nexus_enabled: bool = True,
    skybrary_works: int = 0,
) -> CapabilityMatrix:
    mode = (
        legal_rf_mode
        if isinstance(legal_rf_mode, LegalRfMode)
        else LegalRfMode(str(legal_rf_mode))
    )
    mesh_ok = mode in {
        LegalRfMode.ISM_MESH,
        LegalRfMode.ISM_LORA_CONTROL,
        LegalRfMode.HYBRID_GATEWAY,
        LegalRfMode.AMATEUR_OPERATOR,
    }
    lora_ok = mode in {
        LegalRfMode.ISM_LORA_CONTROL,
        LegalRfMode.HYBRID_GATEWAY,
        LegalRfMode.AMATEUR_OPERATOR,
    }
    gw_ok = mode in {LegalRfMode.HYBRID_GATEWAY, LegalRfMode.AMATEUR_OPERATOR} or sim_mode

    caps: list[Capability] = [
        Capability(
            id="fta_weather_decode",
            title="Free-to-air weather demodulation",
            category="content_decode",
            legal_basis="Unencrypted public satellite broadcasts (receive-only)",
            status="optional_tool" if not _tool("satdump") and not _tool("satdump_cli") else "available",
            enabled=True,
            how="pipeline --plugin satdump_weather | install SatDump",
            never="Commercial encrypted constellations",
        ),
        Capability(
            id="amateur_telemetry_decode",
            title="Open amateur / CubeSat telemetry decode",
            category="content_decode",
            legal_basis="Amateur/open designs; lawful reception",
            status="optional_tool" if not _tool("gr_satellites") else "available",
            enabled=True,
            how="pipeline --plugin gr_satellites",
            never="Decrypting private commercial payloads",
        ),
        Capability(
            id="sim_file_decode",
            title="Simulation / recorded file ingest",
            category="content_decode",
            legal_basis="Local files operator may process",
            status="available",
            enabled=True,
            how="pipeline --plugin sim_file --sim",
        ),
        Capability(
            id="package_import",
            title="Offline package / folder / ZIM import",
            category="content_open",
            legal_basis="Operator-licensed redistribution (CC, PD, Kiwix terms, ...)",
            status="available",
            enabled=True,
            how="pipeline --plugin package_import | bulk_open_pack",
        ),
        Capability(
            id="open_http_fetch",
            title="Opportunistic open HTTPS fetch (allowlisted)",
            category="content_open",
            legal_basis="Authorized download of open content over normal internet client",
            status="available" if gw_ok or sim_mode else "disabled",
            enabled=gw_ok or sim_mode,
            how="capabilities open-fetch | gateway with open_url allowlist",
            never="Paywalled DRM or commercial decrypt",
        ),
        Capability(
            id="skybrary_fts",
            title="Skybrary works catalog + full-text search",
            category="archive",
            legal_basis="Public domain / open licensed texts only",
            status="available",
            enabled=True,
            how="skybrary samples --ingest | skybrary search",
        ),
        Capability(
            id="skybrary_corpus_import",
            title="Skybrary corpus folder / open-URL import",
            category="archive",
            legal_basis="Operator-verified PD/CC/open only; license required (fail closed)",
            status="available",
            enabled=True,
            how="skybrary import-folder | import-open | pipeline corpus_folder_import",
            never="Pirate mirrors, warez, commercial DRM dumps",
        ),
        Capability(
            id="skybrary_gutenberg_catalog",
            title="Gutenberg-style open catalog batch import",
            category="archive",
            legal_basis="Project Gutenberg / public-domain terms; operator-run, rate-limited",
            status="available",
            enabled=True,
            how="skybrary import-gutenberg-catalog --catalog FILE [--ingest]",
            never="Pirate mirrors, unrestricted mass scrape, commercial DRM dumps",
        ),
        Capability(
            id="skybrary_dual_access_export",
            title="Dual-access static catalog export (v2)",
            category="archive",
            legal_basis="Metadata for open/PD works only",
            status="available",
            enabled=True,
            how="skybrary export-catalog --out DIR [--starter-kits]",
            never="Claiming complete archive or free commercial broadband",
        ),
        Capability(
            id="skybrary_oa_science",
            title="Open-access science catalog import (arXiv/PMC-style)",
            category="archive",
            legal_basis="Per-work OA/CC/PD only; operator-run; rate-limited",
            status="available",
            enabled=True,
            how="skybrary import-oa-science --catalog FILE [--allow-local]",
            never="Pirate mirrors, paywalled full-text dumps, DRM defeat",
        ),
        Capability(
            id="content_blob_store",
            title="Content-addressed blob store (dedup / integrity)",
            category="archive",
            legal_basis="Integrity of open packages only",
            status="available",
            enabled=True,
            how="skycache blobs put|verify|ingest-content",
            never="Not a piracy CDN",
        ),
        Capability(
            id="mesh_batman_day_one",
            title="batman-adv day-one mesh OOB plan / apply",
            category="local_tx",
            legal_basis="Unlicensed Wi-Fi/ISM; national EIRP rules; operator spectrum check",
            status="available",
            enabled=True,
            how="mesh day-one [--apply] | deploy/mesh/batman-day-one.sh",
            never="Satellite uplink; licensed bands without authorization",
        ),
        Capability(
            id="golden_pi_image",
            title="Golden Raspberry Pi image bake + downloadable SD kit",
            category="distribution",
            legal_basis="Operator-flashed offline node; same legal rails as install",
            status="available",
            enabled=True,
            how="skycache pi-image plan|write|bundle -> site /downloads/ + Release asset",
            never="Shipping default PIN 2468 on field images; multi-GB .img in git",
        ),
        Capability(
            id="mesh_dual_radio_validation",
            title="Dual-radio validation media (all board models)",
            category="local_tx",
            legal_basis="Unlicensed Wi-Fi/ISM; shared storyboard + per-board matrix",
            status="available",
            enabled=True,
            how="skycache mesh dual-radio-pack --out media/dual-radio-validation",
            never="Claiming filmed lab on every PCB revision without evidence",
        ),
        Capability(
            id="maps_mbtiles_blobs",
            title="Offline MBTiles via blob store (operator extracts)",
            category="archive",
            legal_basis="ODbL/CC map licenses with attribution; operator-run extracts",
            status="available",
            enabled=True,
            how="skycache maps sample|import + blobs put; pack profile maps-offline",
            never="Committing multi-GB regional tiles to the monorepo",
        ),
        Capability(
            id="partner_field_pilot",
            title="Partner field pilot kit packaging",
            category="distribution",
            legal_basis="Institutional training + legal one-pager; open content only",
            status="available",
            enabled=True,
            how="skycache partner kit --type ngo|university|civil-protection",
            never="Over-claim free broadband or complete archive",
        ),
        Capability(
            id="skybrary_pack_profiles",
            title="Size-bounded offline pack profiles",
            category="archive",
            legal_basis="Same open-license gates as Skybrary",
            status="available",
            enabled=True,
            how="skybrary pack --profile literacy-1gb",
        ),
        Capability(
            id="integrity_verify",
            title="Package checksum / integrity verify",
            category="archive",
            legal_basis="Integrity of open packages (not DRM defeat)",
            status="available",
            enabled=True,
            how="capabilities verify-tree | skybrary integrity",
        ),
        Capability(
            id="wifi_ap",
            title="Local Wi-Fi access point (captive portal)",
            category="local_tx",
            legal_basis="Unlicensed Wi-Fi; national EIRP/outdoor rules",
            status="optional_tool" if not _tool("hostapd") else "available",
            enabled=True,
            how="deploy/hotspot/ + serve",
        ),
        Capability(
            id="wifi_mesh",
            title="Unlicensed Wi-Fi mesh (batman-adv)",
            category="local_tx",
            legal_basis="Unlicensed/ISM mesh only",
            status="optional_tool" if not _tool("batctl") else "available",
            enabled=mesh_ok and nexus_enabled,
            how="mesh status | deploy/mesh/",
            never="Licensed microwave or sat uplink",
        ),
        Capability(
            id="lora_control",
            title="LoRa/ISM low-bandwidth control plane",
            category="local_tx",
            legal_basis="Regional ISM; duty-cycle/power limits",
            status="sim_only" if sim_mode or not lora_ok else "available",
            enabled=lora_ok or sim_mode,
            how="control plane API | nexus control alert",
            never="Bulk media over LoRa; illegal power",
        ),
        Capability(
            id="usb_mule",
            title="USB / file data-mule DTN",
            category="distribution",
            legal_basis="Physical transfer of open packages",
            status="available",
            enabled=True,
            how="nexus DTN export_mule / import_mule",
        ),
        Capability(
            id="ble_mule_sim",
            title="Phone handoff mule (sim / file bridge)",
            category="distribution",
            legal_basis="User-consented local transfer of open packs",
            status="sim_only",
            enabled=True,
            how="capabilities ble-mule-export (file-based handoff package)",
        ),
        Capability(
            id="opportunistic_gateway",
            title="Opportunistic legal uplink client",
            category="distribution",
            legal_basis="Operator-authorized modem/Wi-Fi/Ethernet; open pulls only",
            status="available" if gw_ok or sim_mode else "disabled",
            enabled=gw_ok or sim_mode,
            how="gateway --pull | legal_rf_mode=hybrid_gateway",
            never="Transparent mesh NAT to public internet by default",
        ),
        Capability(
            id="community_boards",
            title="Local village boards + notes",
            category="distribution",
            legal_basis="Local store-and-forward; no third-party analytics",
            status="available",
            enabled=True,
            how="PWA Board / Notes",
        ),
        Capability(
            id="sdr_receive_only",
            title="SDR receive-only frontend",
            category="receive",
            legal_basis="Receive-only RF; confirm national reception rules",
            status="optional_tool",
            enabled=True,
            how="RTL-SDR + SatDump / gr-satellites",
            never="Satellite transmit",
        ),
        Capability(
            id="amateur_operator_docs",
            title="Amateur radio TX (operator-licensed, external)",
            category="local_tx",
            legal_basis="Valid national amateur license + band plan",
            status="operator_licensed",
            enabled=amateur_license_affirmed,
            how="Docs only - software does not ship automatic sat uplink",
            never="Unlicensed TX; commercial sat uplink",
        ),
    ]

    banned = [
        "Commercial constellation decryption (Starlink, OneWeb, paid VSAT, CAS)",
        "Default satellite uplink / VSAT TX modes",
        "Card-sharing / DRM circumvention for redistribution",
        "Jamming, GPS spoofing, pirate cellular base stations",
        "Claiming free commercial broadband",
    ]

    # Annotate skybrary count in how string
    for c in caps:
        if c.id == "skybrary_fts":
            c.how = f"{c.how} (works_indexed={skybrary_works})"

    return CapabilityMatrix(
        legal_rf_mode=mode.value,
        capabilities=caps,
        banned=banned,
    )
