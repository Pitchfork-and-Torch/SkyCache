#!/usr/bin/env bash
# Example batman-adv bring-up for SkyCache Nexus (Linux).
# LEGAL: Unlicensed Wi-Fi / ISM only. No satellite uplink. Not free commercial broadband.
# Operator MUST verify national EIRP, outdoor, and DFS rules before enabling radios.
#
# This is a TEMPLATE - interface names and modes differ by driver/distro.
# Prefer OpenWrt mesh APs when possible; run SkyCache on Ethernet-backed nodes.

set -euo pipefail

MESH_IF="${MESH_IF:-wlan0}"
BAT_IF="${BAT_IF:-bat0}"
NODE_OCTET="${NODE_OCTET:-10}"   # 10.42.0.NODE_OCTET
SSID_MESH="${SSID_MESH:-SkyCache-Mesh}"

echo "[Nexus] batman-adv template"
echo "  MESH_IF=$MESH_IF BAT_IF=$BAT_IF NODE=10.42.0.$NODE_OCTET"
echo "  Banner: store-and-forward community mesh - not free Starlink"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

modprobe batman-adv || { echo "batman-adv module missing"; exit 1; }
command -v batctl >/dev/null || { echo "install batctl"; exit 1; }

# Put radio in ad-hoc / mesh mode first (device-specific). Example IBSS:
#   ip link set "$MESH_IF" down
#   iw dev "$MESH_IF" set type ibss
#   ip link set "$MESH_IF" up
#   iw dev "$MESH_IF" ibss join "$SSID_MESH" 2412

ip link set "$MESH_IF" up || true
batctl if add "$MESH_IF" || true
ip link set "$BAT_IF" up
ip addr flush dev "$BAT_IF" || true
ip addr add "10.42.0.${NODE_OCTET}/24" dev "$BAT_IF"

echo "[OK] batctl n:"
batctl n || true
echo "Next: systemctl restart skycache; open http://10.42.0.${NODE_OCTET}:8080/"
echo "Docs: docs/mesh-deployment.md"
