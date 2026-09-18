"""Node identity for Nexus fabric."""

from __future__ import annotations

import hashlib
import json
import socket
import uuid
from pathlib import Path


def load_or_create_node_id(data_dir: Path, explicit: str | None = None) -> str:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "node-id.json"
    if explicit:
        nid = _sanitize(explicit)
        path.write_text(json.dumps({"node_id": nid}, indent=2), encoding="utf-8")
        return nid
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("node_id") or _new_id())
    nid = _new_id()
    path.write_text(json.dumps({"node_id": nid}, indent=2), encoding="utf-8")
    return nid


def _new_id() -> str:
    host = socket.gethostname() or "node"
    raw = f"{host}-{uuid.uuid4().hex[:10]}"
    return _sanitize(raw)


def _sanitize(s: str) -> str:
    out = "".join(c if c.isalnum() or c in "-_" else "-" for c in s.strip())[:48]
    return out or f"node-{uuid.uuid4().hex[:8]}"


def content_fingerprint(package_id: str, size_bytes: int, received_at: str) -> str:
    h = hashlib.sha256(f"{package_id}|{size_bytes}|{received_at}".encode()).hexdigest()
    return h[:16]
