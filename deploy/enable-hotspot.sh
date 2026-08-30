#!/usr/bin/env bash
# Enable SkyCache WiFi AP on Debian / Raspberry Pi OS (technical volunteer).
# Prerequisites: SkyCache installed; review local WiFi regulations first.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/enable-hotspot.sh"
  exit 1
fi

IFACE="${SKYCACHE_WIFI_IFACE:-wlan0}"
SSID="${SKYCACHE_SSID:-SkyCache-Local}"
APP_ROOT="${SKYCACHE_ROOT:-/opt/skycache}"
IP_CIDR="${SKYCACHE_AP_CIDR:-10.0.0.1/24}"

echo "[legal] Confirm unlicensed AP operation is allowed in your country."
echo "[1/5] Interface $IFACE -> $IP_CIDR"
ip link set "$IFACE" up || true
ip addr flush dev "$IFACE" || true
ip addr add "$IP_CIDR" dev "$IFACE"

echo "[2/5] hostapd"
install -d /etc/hostapd
if [[ -f "$APP_ROOT/deploy/hotspot/hostapd.conf.example" ]]; then
  sed "s/interface=wlan0/interface=${IFACE}/; s/ssid=SkyCache-Local/ssid=${SSID}/" \
    "$APP_ROOT/deploy/hotspot/hostapd.conf.example" > /etc/hostapd/hostapd.conf
else
  cat > /etc/hostapd/hostapd.conf <<EOF
interface=${IFACE}
driver=nl80211
ssid=${SSID}
hw_mode=g
channel=6
wmm_enabled=1
auth_algs=1
EOF
fi
# Unmask / enable (Bookworm often masks hostapd)
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd
systemctl restart hostapd

echo "[3/5] dnsmasq"
install -d /etc/dnsmasq.d
if [[ -f "$APP_ROOT/deploy/hotspot/dnsmasq.conf.example" ]]; then
  sed "s/interface=wlan0/interface=${IFACE}/" \
    "$APP_ROOT/deploy/hotspot/dnsmasq.conf.example" > /etc/dnsmasq.d/skycache.conf
else
  cat > /etc/dnsmasq.d/skycache.conf <<EOF
interface=${IFACE}
bind-interfaces
dhcp-range=10.0.0.50,10.0.0.200,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
address=/#/10.0.0.1
EOF
fi
# Avoid conflict with systemd-resolved if present
systemctl stop systemd-resolved 2>/dev/null || true
systemctl disable systemd-resolved 2>/dev/null || true
systemctl enable dnsmasq
systemctl restart dnsmasq

echo "[4/5] IP forward (optional LAN share - OFF by default for hub isolation)"
# sysctl -w net.ipv4.ip_forward=0

echo "[5/5] SkyCache service"
systemctl restart skycache.service 2>/dev/null || echo "skycache.service not installed yet"

echo "Done."
echo "  SSID: $SSID"
echo "  Portal: http://10.0.0.1:8080/  (or http://10.0.0.1/ if reverse-proxied)"
echo "  Phones may show a captive portal login - open the browser if not auto-redirected."
