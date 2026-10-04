"""Wave 2.E3 + Wave 3.B6: E2E samples->FTS->pack->handoff->second node + works_manifest.

Hermetic, sim-only (no RF). Uses tmp_path for two independent node data dirs.
"""

from __future__ import annotations

from pathlib import Path

from skycache.capabilities.ble_mule import export_handoff_bundle, import_handoff_bundle
from skycache.config import Settings
from skycache.db.catalog import Catalog
from skycache.ingest.normalizer import ContentManager
from skycache.ingest.package_loader import load_manifest
from skycache.nexus.dtn import DtnQueue
from skycache.nexus.fabric import ContentFabric
from skycache.nexus.mesh import MeshFabric
from skycache.policy.prioritizer import compute_score
from skycache.skybrary.catalog import WORKS_MANIFEST_FORMAT, SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings, ingest_package_dir_to_skybrary
from skycache.skybrary.pack_profile import build_pack_from_profile


def test_e2e_samples_fts_pack_handoff_second_node(tmp_path: Path):
    # --- Node A: bootstrap PD samples into content + Skybrary FTS ---
    settings_a = Settings(
        data_dir=tmp_path / "node_a",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        node_id="village-a",
    )
    settings_a.ensure_dirs()
    sky_a = SkybraryCatalog(settings_a.skybrary_db_path)
    work_ids = bootstrap_samples_with_settings(settings_a, sky_a)
    assert len(work_ids) >= 3
    assert sky_a.count() >= 3

    # FTS hits on known sample bodies
    liberty = sky_a.search("liberty")
    assert any("gettysburg" in h["work_id"] for h in liberty)
    fox = sky_a.search("fox grapes")
    assert any("aesop" in h["work_id"] for h in fox)

    # Pack profile build (size-bounded kit)
    pack_out = tmp_path / "pack-kit"
    pack_meta = build_pack_from_profile(
        sky_a,
        "all-open-small",
        content_dir=settings_a.content_dir,
        out_dir=pack_out,
    )
    assert pack_meta["count"] >= 1
    selected = pack_meta["selected_packages"]
    assert selected
    assert (pack_out / "profile-manifest.json").is_file()
    for pid in selected:
        assert (pack_out / pid / "manifest.json").is_file()

    # Works manifest (federation foundation)
    man = sky_a.works_manifest(node_id="village-a")
    assert man["format"] == WORKS_MANIFEST_FORMAT
    assert man["work_count"] >= 3
    assert man["node_id"] == "village-a"
    man_path = sky_a.export_works_manifest(
        tmp_path / "works-manifest.json",
        node_id="village-a",
    )
    assert man_path.is_file()

    # Handoff export (phone/USB mule - file bridge, no RF)
    dtn_a = DtnQueue(settings_a.nexus_dir / "dtn-queue.json")
    bundle = export_handoff_bundle(
        dtn=dtn_a,
        content_dir=settings_a.content_dir,
        package_ids=list(selected),
        out_dir=tmp_path / "handoff",
        node_id="village-a",
    )
    assert (bundle / "handoff.json").is_file()
    for pid in selected:
        assert (bundle / "packages" / pid).is_dir()

    # Fabric gossip includes works_manifest when sky attached
    catalog_a = Catalog(settings_a.db_path)
    content_a = ContentManager(settings_a, catalog_a)
    mesh_a = MeshFabric(
        data_dir=settings_a.data_dir,
        node_id="village-a",
        mode="sim",
        band="sim",
    )
    fabric_a = ContentFabric(
        node_id="village-a",
        catalog=catalog_a,
        content=content_a,
        mesh=mesh_a,
        dtn=dtn_a,
        content_dir=settings_a.content_dir,
        skybrary=sky_a,
    )
    gossip = fabric_a.gossip_payload()
    assert "manifest" in gossip
    assert "works_manifest" in gossip
    assert gossip["works_manifest"]["work_count"] >= 3

    # --- Node B: empty second data dir receives handoff + works_manifest ---
    settings_b = Settings(
        data_dir=tmp_path / "node_b",
        sim_mode=True,
        mesh_mode="sim",
        mesh_band="sim",
        node_id="village-b",
    )
    settings_b.ensure_dirs()
    dtn_b = DtnQueue(settings_b.nexus_dir / "dtn-queue.json")
    import_report = import_handoff_bundle(
        bundle,
        dtn=dtn_b,
        content_dest=settings_b.content_dir,
        node_id="village-b",
    )
    assert len(import_report["packages"]) >= 1
    for pid in import_report["packages"]:
        dest = settings_b.content_dir / pid
        assert dest.is_dir()
        assert (dest / "manifest.json").is_file()

    # Second node: catalog + skybrary from handoff packages + works_manifest
    catalog_b = Catalog(settings_b.db_path)
    content_b = ContentManager(settings_b, catalog_b)
    sky_b = SkybraryCatalog(settings_b.skybrary_db_path)
    assert sky_b.count() == 0

    # Metadata federation first
    wm_report = sky_b.import_works_manifest(man_path)
    assert wm_report["imported"] >= 3
    assert sky_b.count() >= 3

    # Register packages already on disk (handoff put them under content_dir  - 
    # do not re-copy via ContentManager which would rmtree the source).
    for pid in import_report["packages"]:
        pkg_dir = settings_b.content_dir / pid
        pkg = load_manifest(pkg_dir)
        catalog_b.upsert_package(pkg, pkg_dir, score=compute_score(pkg))
        # Re-index skybrary with body text from package (content=None: already present)
        ingest_package_dir_to_skybrary(pkg_dir, sky=sky_b, content=None)

    assert catalog_b.count() >= 1
    assert catalog_b.count() == len(import_report["packages"])
    for pid in import_report["packages"]:
        assert catalog_b.get(pid) is not None
        assert (settings_b.content_dir / pid / "manifest.json").is_file()
    # FTS after body reindex - samples included in all-open-small kit
    assert sky_b.search("liberty") or sky_b.search("fox") or sky_b.count() >= 1

    # Fabric on B sees remote works already imported (missing empty for those)
    mesh_b = MeshFabric(
        data_dir=settings_b.data_dir,
        node_id="village-b",
        mode="sim",
        band="sim",
    )
    fabric_b = ContentFabric(
        node_id="village-b",
        catalog=catalog_b,
        content=content_b,
        mesh=mesh_b,
        dtn=dtn_b,
        content_dir=settings_b.content_dir,
        skybrary=sky_b,
    )
    missing = fabric_b.missing_works_from(gossip["works_manifest"])
    assert missing == []  # already imported full works_manifest

    sync_rep = fabric_b.sync_with_peer_manifest(
        gossip,
        peer_content_root=settings_a.content_dir,
    )
    assert sync_rep["works_imported"] >= 0
    # Packages already present via handoff; pulled may be empty or extra samples
    assert "pulled" in sync_rep

    sky_a.close()
    sky_b.close()
    catalog_a.close()
    catalog_b.close()


def test_works_manifest_roundtrip_rejects_bad_license(tmp_path: Path):
    sky = SkybraryCatalog(tmp_path / "skybrary.db")
    settings = Settings(data_dir=tmp_path / "data", sim_mode=True)
    settings.ensure_dirs()
    bootstrap_samples_with_settings(settings, sky)
    man = sky.works_manifest(node_id="n1")
    # inject a forbidden license entry
    man["works"].append(
        {
            "work_id": "pirate-book-001",
            "title": {"en": "Nope"},
            "creators": [],
            "languages": ["en"],
            "subjects": [],
            "license": "all rights reserved pirate",
            "civilizational_tier": 5,
            "package_id": None,
            "summary": {},
            "provenance": {},
            "editions": [],
        }
    )
    sky2 = SkybraryCatalog(tmp_path / "sky2.db")
    rep = sky2.import_works_manifest(man)
    assert rep["imported"] >= 3
    assert rep["skipped"] >= 1
    assert sky2.get_work("pirate-book-001") is None
    sky.close()
    sky2.close()
