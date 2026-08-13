#!/usr/bin/env bash
# SkyCache Nexus  -  batman-adv day-one hardware OOB (Linux).
# LEGAL: Unlicensed Wi-Fi / ISM only. No satellite uplink. Not free commercial broadband.
# Operator MUST verify national EIRP, outdoor, and DFS rules before enabling radios.
#
# Usage:
#   sudo MESH_IF=wlan0 CLIENT_IF=wlan1 NODE_OCTET=10 bash deploy/mesh/batman-day-one.sh
# Dry documentation only (no root changes):
#   DRY_RUN=1 bash deploy/mesh/batman-day-one.sh
set -euo pipefail

MESH_IF="${MESH_IF:-wlan0}"
BAT_IF="${BAT_IF:-bat0}"
CLIENT_IF="${CLIENT_IF:-wlan1}"
NODE_OCTET="${NODE_OCTET:-10}"
SSID_MESH="${SSID_MESH:-SkyCache-Mesh}"
SSID_CLIENT="${SSID_CLIENT:-SkyCache-Village}"
FREQ_MHZ="${FREQ_MHZ:-2412}"
DRY_RUN="${DRY_RUN:-0}"
DATA_DIR="${SKYCACHE_DATA_DIR:-/var/lib/skycache}"

echo "[SkyCache] batman-adv day-one OOB"
echo "  MESH_IF=$MESH_IF BAT_IF=$BAT_IF CLIENT_IF=$CLIENT_IF NODE=10.42.0.$NODE_OCTET"
echo "  Banner: store-and-forward community mesh  -  not free Starlink"
echo "  Docs: docs/mesh-deployment.md  |  docs/mesh-field-checklist.md"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY_RUN] Would: modprobe batman-adv; batctl if add $MESH_IF; address bat0; optional hostapd on $CLIENT_IF"
  echo "[DRY_RUN] Set legal_rf_mode=ism_mesh after spectrum check"
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (or DRY_RUN=1)." >&2
  exit 1
fi

if ! modprobe batman-adv 2>/dev/null; then
  echo "ERROR: batman-adv module missing. Install: apt install batctl && reboot if needed." >&2
  exit 1
fi
command -v batctl >/dev/null || { echo "install batctl"; exit 1; }
command -v ip >/dev/null || { echo "iproute2 required"; exit 1; }

# Best-effort: bring mesh interface up. Driver-specific IBSS join is commented  - 
# many village deploys use OpenWrt APs for mesh and Ethernet to the Pi.
if ip link show "$MESH_IF" &>/dev/null; then
  ip link set "$MESH_IF" up || true
  # Optional IBSS (uncomment after confirming driver support):
  # ip link set "$MESH_IF" down
  # iw dev "$MESH_IF" set type ibss || true
  # ip link set "$MESH_IF" up
  # iw dev "$MESH_IF" ibss join "$SSID_MESH" "$FREQ_MHZ" || true
  batctl if add "$MESH_IF" || batctl meshif "$BAT_IF" interface add "$MESH_IF" || true
else
  echo "WARN: $MESH_IF not present  -  create bat0 anyway for Ethernet-backed mesh tests"
fi

ip link set "$BAT_IF" up 2>/dev/null || ip link add name "$BAT_IF" type batadv 2>/dev/null || true
ip link set "$BAT_IF" up || true
ip addr flush dev "$BAT_IF" 2>/dev/null || true
ip addr add "10.42.0.${NODE_OCTET}/24" dev "$BAT_IF" 2>/dev/null || \
  ip addr replace "10.42.0.${NODE_OCTET}/24" dev "$BAT_IF"

echo "[OK] batctl interfaces / neighbors:"
batctl if || batctl meshif "$BAT_IF" interface || true
batctl n || batctl meshif "$BAT_IF" n || true

# Optional client AP note (do not start hostapd automatically without conf)
if ip link show "$CLIENT_IF" &>/dev/null; then
  echo "[INFO] Client radio $CLIENT_IF present  -  configure hostapd for SSID $SSID_CLIENT"
  echo "       Example: deploy/mesh/hostapd-client-ap.example.conf"
else
  echo "[INFO] No $CLIENT_IF  -  use Ethernet AP or single-radio careful mode"
fi

mkdir -p "$DATA_DIR/nexus"
cat > "$DATA_DIR/nexus/mesh-day-one-applied.json" <<EOF
{
  "applied_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "mesh_if": "$MESH_IF",
  "bat_if": "$BAT_IF",
  "node": "10.42.0.${NODE_OCTET}",
  "ssid_mesh": "$SSID_MESH",
  "legal": "Unlicensed Wi-Fi/ISM only; not free commercial broadband"
}
EOF

echo "[NEXT] systemctl restart skycache"
echo "[NEXT] open http://10.42.0.${NODE_OCTET}:8080/  (or LAN IP)"
echo "[NEXT] skycache nexus validate --nodes 2  (sim) then physical peer batctl n"
echo "[OK] day-one mesh bring-up finished"
