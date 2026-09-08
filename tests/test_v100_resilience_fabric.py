"""v1.0 Skybrary Resilience Fabric: bit-rot schedule, ops metrics, federation sim."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from skycache.config import Settings
from skycache.health.bitrot_schedule import (
    load_last_report,
    run_bitrot_verify,
    schedule_status,
    write_schedule_templates,
)
from skycache.nexus.federation import multi_node_sim_sync
from skycache.ops.local_metrics import local_ops_snapshot
from skycache.skybrary.catalog import SkybraryCatalog
from skycache.skybrary.ingest import bootstrap_samples_with_settings
from skycache.web.app import create_app


def test_bitrot_record_and_schedule_fresh(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "node", sim_mode=True)
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()

    rep = run_bitrot_verify(settings.content_dir, settings.data_dir)
    assert rep["ok"] is True
    assert rep["package_count"] >= 1
    last = load_last_report(settings.data_dir)
    assert last is not None
    assert last["ok"] is True
    st = schedule_status(settings.data_dir)
    assert st["scheduled"] is True
    assert st["fresh"] is True


def test_bitrot_templates_written(tmp_path: Path):
    meta = write_schedule_templates(tmp_path / "units", data_dir="/var/lib/skycache")
    assert Path(meta["service"]).is_file()
    assert Path(meta["timer"]).is_file()
    assert "bitrot" in Path(meta["cron"]).read_text(encoding="utf-8")


def test_local_ops_snapshot(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "ops", sim_mode=True, mock_battery_percent=88.0)
    settings.ensure_dirs()
    snap = local_ops_snapshot(settings, mesh=None, sky_count=0)
    assert snap["schema"] == "skycache.ops.local.v1"
    assert "disk" in snap
    assert snap["fleet_heartbeat"]["enabled"] is False
    assert snap["power"]["battery_percent"] == 88.0


def test_federation_sim_two_nodes(tmp_path: Path):
    nodes = []
    for i in range(2):
        s = Settings(
            data_dir=tmp_path / f"n{i}",
            sim_mode=True,
            mesh_mode="sim",
            mesh_band="sim",
            node_id=f"v{i}",
        )
        s.ensure_dirs()
        nodes.append(s)
    sky0 = SkybraryCatalog(nodes[0].skybrary_db_path)
    bootstrap_samples_with_settings(nodes[0], sky0)
    sky0.close()
    report = multi_node_sim_sync(nodes, rounds=1)
    assert report["nodes"] == 2
    snaps = report["snapshots"]
    assert snaps[0]["works"] >= 3
    # Node 1 should import works metadata (and/or packages) from node 0
    assert snaps[1]["works"] >= 1 or any(
        (e.get("works_imported") or 0) > 0 for e in report["exchanges"]
    )


def test_api_ops_local_and_integrity(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "web", sim_mode=True, mesh_mode="sim", mesh_band="sim")
    settings.ensure_dirs()
    sky = SkybraryCatalog(settings.skybrary_db_path)
    bootstrap_samples_with_settings(settings, sky)
    sky.close()
    run_bitrot_verify(settings.content_dir, settings.data_dir)

    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/ops/local")
    assert r.status_code == 200
    body = r.json()
    assert body["schema"] == "skycache.ops.local.v1"
    assert body["fleet_heartbeat"]["enabled"] is False

    r2 = client.get("/api/integrity/last")
    assert r2.status_code == 200
    assert r2.json()["last"] is not None
    assert r2.json()["last"]["ok"] is True


def test_compact_works_manifest_and_import(tmp_path: Path):
    """Bandwidth-aware compact gossip still imports metadata."""
    s0 = Settings(data_dir=tmp_path / "a", sim_mode=True, node_id="a")
    s1 = Settings(data_dir=tmp_path / "b", sim_mode=True, node_id="b")
    s0.ensure_dirs()
    s1.ensure_dirs()
    sky0 = SkybraryCatalog(s0.skybrary_db_path)
    bootstrap_samples_with_settings(s0, sky0)
    full = sky0.works_manifest(node_id="a", compact=False)
    compact = sky0.works_manifest(node_id="a", compact=True, max_works=50)
    sky0.close()
    assert compact["compact"] is True
    assert compact["work_count"] >= 3
    # Compact entries omit full editions list
    assert "editions" not in compact["works"][0]
    assert "primary_format" in compact["works"][0]
    # Wire size should be smaller than full for same works
    import json as _json

    assert len(_json.dumps(compact)) < len(_json.dumps(full))

    sky1 = SkybraryCatalog(s1.skybrary_db_path)
    rep = sky1.import_works_manifest(compact)
    assert rep["imported"] >= 3
    assert sky1.count() >= 3
    sky1.close()


def test_cli_federation_and_ops(tmp_path: Path):
    from skycache.__main__ import build_parser

    def run(argv: list[str]) -> int:
        parser = build_parser()
        args = parser.parse_args(argv)
        return int(args.func(args))

    base = tmp_path / "fed"
    assert run(
        [
            "nexus",
            "federation",
            "--nodes",
            "2",
            "--rounds",
            "1",
            "--base-dir",
            str(base),
        ]
    ) == 0

    data = base / "node-0"
    assert data.is_dir()
    assert run(["ops", "status", "--data-dir", str(data)]) == 0
    assert run(
        [
            "skybrary",
            "doctor",
            "--data-dir",
            str(data),
            "--verify",
            "--record",
        ]
    ) == 0
    assert (data / "ops" / "bitrot-last.json").is_file()
    report = json.loads((data / "ops" / "bitrot-last.json").read_text(encoding="utf-8"))
    assert report.get("ok") is True
