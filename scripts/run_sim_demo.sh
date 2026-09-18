#!/usr/bin/env bash
# Quick simulation demo (Linux/macOS). On Windows: py -3 -m skycache serve --sim
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -e ".[dev]" -q
python scripts/make_sample_package.py
python -m skycache init --load-samples
echo "Open http://127.0.0.1:8080/"
exec python -m skycache serve --sim --host 127.0.0.1 --port 8080
