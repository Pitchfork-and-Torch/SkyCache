#!/usr/bin/env bash
# Golden Raspberry Pi bake helper  -  installs village fabric + verify artifacts.
# LEGAL: receive-only; not free commercial broadband; never leave PIN 2468.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATA_DIR="${SKYCACHE_DATA_DIR:-/var/lib/skycache}"
PIN="${SKYCACHE_ADMIN_PIN:-}"
SSID="${SKYCACHE_HOTSPOT_SSID:-SkyCache-Village}"
LEGAL="${SKYCACHE_LEGAL_RF_MODE:-receive_only}"

echo "[SkyCache] Golden Pi bake"
echo "  ROOT=$ROOT DATA_DIR=$DATA_DIR"
echo "  Banner: offline village node  -  not free Starlink"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

if [[ -z "$PIN" || "$PIN" == "2468" ]]; then
  echo "Set SKYCACHE_ADMIN_PIN to a non-default PIN before bake." >&2
  exit 1
fi

export SKYCACHE_ADMIN_PIN="$PIN"
export SKYCACHE_HOTSPOT_SSID="$SSID"
export SKYCACHE_LEGAL_RF_MODE="$LEGAL"
export SKYCACHE_RUN_FIRST_BOOT=1

bash "$ROOT/deploy/install-village-fabric.sh"

# Write bake plan + verify under data dir
sudo -u skycache env SKYCACHE_DATA_DIR="$DATA_DIR" \
  "$ROOT/.venv/bin/python" -m skycache pi-image write --out "$DATA_DIR/pi-bake" || \
  "$ROOT/.venv/bin/python" -m skycache pi-image write --out "$DATA_DIR/pi-bake"

systemctl enable skycache.service || true
systemctl restart skycache.service || true
sleep 2
bash "$DATA_DIR/pi-bake/golden-pi-verify.sh" || true

echo "[OK] Golden bake steps finished. Seal SD only after manual smoke on hardware."
echo "     Mesh (optional): sudo bash $ROOT/deploy/mesh/batman-day-one.sh"
