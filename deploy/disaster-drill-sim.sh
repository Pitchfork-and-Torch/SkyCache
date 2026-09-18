#!/usr/bin/env bash
# Lab-only disaster flood simulation for SkyCache Nexus.
# LEGAL: No RF. Store-and-forward priority demo only - not free commercial broadband.
# Field procedure: docs/disaster-drill.md

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NODES="${NODES:-3}"

echo "[DRILL] SkyCache nexus sim with disaster priority flood (lab)"
echo "  Banner: local mesh / store-and-forward - not free Starlink"
echo "  Nodes=$NODES"
echo "  After real field drills: turn Disaster mode OFF in /admin"
echo

python -m skycache nexus sim --nodes "$NODES" --disaster

echo
echo "[DRILL] Optional pytest nexus suite"
if command -v pytest >/dev/null 2>&1; then
  python -m pytest tests/test_nexus.py -q || true
else
  echo "  pytest not on PATH - skip"
fi

echo
echo "[OK] Lab sim finished. Field checklist: docs/disaster-drill.md"
echo "     Mesh day-of: docs/mesh-field-checklist.md"
