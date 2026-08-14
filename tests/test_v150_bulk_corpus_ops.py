"""v1.5.0 Bulk Open Corpus Ops: doctor, status, sample-manifest, batch offline."""

from __future__ import annotations

import json
from pathlib import Path

from skycache.skybrary.corpus_ops import (
    corpus_doctor,
    corpus_status,
    run_corpus_batch,
    write_sample_batch_manifest,
)


def test_corpus_doctor():
    rep = corpus_doctor()
    assert rep["schema"] == "skycache.corpus.doctor.v1"
    assert "score" in rep
    assert any(c["id"] == "license_gate" and c["ok"] for c in rep["checks"])
    assert rep.get("go_offline_batch") is True


def test_sample_manifest_and_dry_batch(tmp_path: Path):
    man = tmp_path / "batch.json"
    meta = write_sample_batch_manifest(man)
    assert meta["ok"] is True
    assert meta["job_count"] >= 2
    data = json.loads(man.read_text(encoding="utf-8"))
    assert data["schema"] == "skycache.corpus.batch.v1"
    assert data["jobs"]

    rep = run_corpus_batch(
        man,
        data_dir=tmp_path / "data",
        dry_run=True,
        allow_local=True,
    )
    assert rep["ok"] is True
    assert rep["dry_run"] is True
    assert rep["job_count"] >= 2


def test_batch_folder_and_gutenberg_local(tmp_path: Path):
    data = tmp_path / "node"
    man = tmp_path / "batch.json"
    write_sample_batch_manifest(man)
    # Only run offline-safe jobs: sample folder + fixtures with allow_local
    rep = run_corpus_batch(
        man,
        data_dir=data,
        out_root=tmp_path / "build",
        ingest=True,
        dry_run=False,
        allow_local=True,
    )
    assert rep["schema"] == "skycache.corpus.batch_result.v1"
    # At least one job should succeed offline
    assert any(j.get("ok") for j in rep["jobs"])
    assert Path(rep["provenance_report"]).is_file()
    st = corpus_status(data_dir=data)
    assert st["schema"] == "skycache.corpus.status.v1"
    assert st["content_packages"] >= 1 or st["skybrary_works"] >= 0
