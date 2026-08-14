#!/usr/bin/env bash
# SkyCache installer for Debian / Raspberry Pi OS (technical volunteers)
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install-debian.sh"
  exit 1
fi

APP_USER="${SKYCACHE_USER:-skycache}"
APP_ROOT="${SKYCACHE_ROOT:-/opt/skycache}"
DATA_DIR="${SKYCACHE_DATA:-/var/lib/skycache}"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/6] Packages"
apt-get update
apt-get install -y python3 python3-venv python3-pip git hostapd dnsmasq iptables

echo "[2/6] User + dirs"
id -u "$APP_USER" &>/dev/null || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_ROOT" "$DATA_DIR"
rsync -a --delete --exclude '.git' --exclude 'data' --exclude '.venv' "$SRC_DIR"/ "$APP_ROOT"/
chown -R "$APP_USER":"$APP_USER" "$APP_ROOT" "$DATA_DIR"

echo "[3/6] Python venv"
sudo -u "$APP_USER" python3 -m venv "$APP_ROOT/.venv"
sudo -u "$APP_USER" "$APP_ROOT/.venv/bin/pip" install -U pip
sudo -u "$APP_USER" "$APP_ROOT/.venv/bin/pip" install -e "$APP_ROOT"
sudo -u "$APP_USER" "$APP_ROOT/.venv/bin/python" "$APP_ROOT/scripts/make_sample_package.py" || true
sudo -u "$APP_USER" "$APP_ROOT/.venv/bin/python" -m skycache init --data-dir "$DATA_DIR" --load-samples

echo "[4/6] systemd unit"
cp "$APP_ROOT/deploy/skycache.service" /etc/systemd/system/skycache.service
systemctl daemon-reload
systemctl enable skycache.service
systemctl restart skycache.service

echo "[5/6] Hotspot configs (NOT enabled automatically)"
echo "  Review and copy:"
echo "    $APP_ROOT/deploy/hotspot/hostapd.conf.example -> /etc/hostapd/hostapd.conf"
echo "    $APP_ROOT/deploy/hotspot/dnsmasq.conf.example -> /etc/dnsmasq.d/skycache.conf"
echo "  Assign 10.0.0.1/24 to your AP interface, then: systemctl enable --now hostapd dnsmasq"
echo "  Check local WiFi regulations before enabling an access point."

echo "[6/6] Done"
echo "  Portal: http://<device-ip>:8080/"
echo "  NEXT: run first-boot wizard (sets PIN, legal mode, samples, capabilities):"
echo "    sudo bash $APP_ROOT/deploy/first-boot-wizard.sh"
echo "  Or village golden path: sudo bash $APP_ROOT/deploy/install-village-fabric.sh"
echo "  Admin PIN default until wizard: 2468  (wizard refuses to leave it)"
echo "  Legal: receive-only FTA/open content - see docs/legal-ethics.md  |  docs/first-boot.md"
systemctl --no-pager status skycache.service || true
