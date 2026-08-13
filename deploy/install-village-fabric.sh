#!/usr/bin/env bash
# Multi-node village fabric bootstrap (Debian / Raspberry Pi OS).
# Golden path: install runtime -> first-boot wizard -> portal up with samples.
# LEGAL: unlicensed Wi-Fi mesh only; receive-only satellite; not free commercial broadband.
set -euo pipefail

NODE_ID="${SKYCACHE_NODE_ID:-node-$(hostname | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-' | cut -c1-24)}"
INSTALL_ROOT="${SKYCACHE_INSTALL_ROOT:-/opt/skycache}"
DATA_DIR="${SKYCACHE_DATA_DIR:-/var/lib/skycache}"
MESH_MODE="${SKYCACHE_MESH_MODE:-sim}"
MESH_BAND="${SKYCACHE_MESH_BAND:-sim}"
# Safest field default until wizard raises mode
LEGAL_RF_MODE="${SKYCACHE_LEGAL_RF_MODE:-receive_only}"
RUN_FIRST_BOOT="${SKYCACHE_RUN_FIRST_BOOT:-1}"
SKIP_APT="${SKYCACHE_SKIP_APT:-0}"

echo "[SkyCache Nexus] village fabric install (Wave 1 golden path)"
echo "  NODE_ID=$NODE_ID"
echo "  INSTALL_ROOT=$INSTALL_ROOT"
echo "  DATA_DIR=$DATA_DIR"
echo "  MESH_MODE=$MESH_MODE MESH_BAND=$MESH_BAND"
echo "  LEGAL_RF_MODE=$LEGAL_RF_MODE (override via SKYCACHE_LEGAL_RF_MODE)"
echo "  Banner: store-and-forward + community mesh - not free Starlink"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

if [[ "$SKIP_APT" != "1" ]]; then
  apt-get update -y
  apt-get install -y python3 python3-venv python3-pip git rsync || true
fi

mkdir -p "$INSTALL_ROOT" "$DATA_DIR"
if [[ ! -d "$INSTALL_ROOT/.git" && ! -f "$INSTALL_ROOT/pyproject.toml" ]]; then
  # Allow install from the tree that contains this script
  SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
  if [[ -f "$SRC_DIR/pyproject.toml" ]]; then
    echo "Syncing tree from $SRC_DIR -> $INSTALL_ROOT"
    rsync -a --delete --exclude '.git' --exclude 'data' --exclude '.venv' \
      --exclude '__pycache__' --exclude '.pytest_cache' \
      "$SRC_DIR"/ "$INSTALL_ROOT"/
  else
    echo "Copy or clone SkyCache into $INSTALL_ROOT first."
    echo "  git clone https://github.com/Pitchfork-and-Torch/SkyCache.git $INSTALL_ROOT"
    exit 1
  fi
fi

cd "$INSTALL_ROOT"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]" || pip install -e .

id skycache 2>/dev/null || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin skycache
chown -R skycache:skycache "$DATA_DIR" "$INSTALL_ROOT" || true

# Baseline init (wizard will re-load samples with PIN/mode)
sudo -u skycache env \
  SKYCACHE_DATA_DIR="$DATA_DIR" \
  "$INSTALL_ROOT/.venv/bin/python" -m skycache init --data-dir "$DATA_DIR" || true

sudo -u skycache env \
  SKYCACHE_DATA_DIR="$DATA_DIR" \
  "$INSTALL_ROOT/.venv/bin/python" -m skycache nexus doctor --data-dir "$DATA_DIR" || true

ENV_FILE="$DATA_DIR/skycache.env"
# Placeholder env until first-boot overwrites (default PIN must be changed by wizard)
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<EOF
# SkyCache env - first-boot wizard will rewrite PIN and modes
# LEGAL: receive-only satellite; no commercial decrypt; not free Starlink.
SKYCACHE_DATA_DIR=$DATA_DIR
SKYCACHE_NODE_ID=$NODE_ID
SKYCACHE_MESH_MODE=$MESH_MODE
SKYCACHE_MESH_BAND=$MESH_BAND
SKYCACHE_LEGAL_RF_MODE=$LEGAL_RF_MODE
SKYCACHE_NEXUS_ENABLED=1
SKYCACHE_GATEWAY_DAILY_QUOTA_MB=500
# CHANGE ME - default 2468 is refused by first-boot wizard
SKYCACHE_ADMIN_PIN=2468
SKYCACHE_HOTSPOT_SSID=SkyCache-Local
EOF
  chmod 600 "$ENV_FILE" || true
  chown skycache:skycache "$ENV_FILE" || true
fi

UNIT=/etc/systemd/system/skycache.service
cat > "$UNIT" <<EOF
[Unit]
Description=SkyCache Nexus community knowledge hub
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=skycache
Group=skycache
WorkingDirectory=$INSTALL_ROOT
EnvironmentFile=-$ENV_FILE
Environment=SKYCACHE_DATA_DIR=$DATA_DIR
Environment=SKYCACHE_NODE_ID=$NODE_ID
Environment=SKYCACHE_MESH_MODE=$MESH_MODE
Environment=SKYCACHE_MESH_BAND=$MESH_BAND
Environment=SKYCACHE_NEXUS_ENABLED=1
Environment=SKYCACHE_GATEWAY_DAILY_QUOTA_MB=500
Environment=SKYCACHE_LEGAL_RF_MODE=$LEGAL_RF_MODE
ExecStart=$INSTALL_ROOT/.venv/bin/python -m skycache serve --host 0.0.0.0 --port 8080 --data-dir $DATA_DIR
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable skycache.service

# First-boot wizard (PIN + SSID + legal mode + samples + Skybrary + capabilities)
if [[ "$RUN_FIRST_BOOT" == "1" ]]; then
  echo ""
  echo "[SkyCache] Running first-boot wizard (set SKYCACHE_RUN_FIRST_BOOT=0 to skip)..."
  export SKYCACHE_INSTALL_ROOT="$INSTALL_ROOT"
  export SKYCACHE_DATA_DIR="$DATA_DIR"
  export SKYCACHE_ENV_FILE="$ENV_FILE"
  export SKYCACHE_NODE_ID="$NODE_ID"
  export SKYCACHE_LEGAL_RF_MODE="$LEGAL_RF_MODE"
  export SKYCACHE_PYTHON="$INSTALL_ROOT/.venv/bin/python"
  if [[ -n "${SKYCACHE_ADMIN_PIN:-}" && "${SKYCACHE_ADMIN_PIN}" != "2468" ]]; then
    # Fully non-interactive golden path for scripted demos
    export SKYCACHE_FIRST_BOOT_YES=1
    bash "$INSTALL_ROOT/deploy/first-boot-wizard.sh" --non-interactive || {
      echo "[WARN] first-boot non-interactive failed; run: sudo bash deploy/first-boot-wizard.sh" >&2
    }
  elif [[ -t 0 ]]; then
    bash "$INSTALL_ROOT/deploy/first-boot-wizard.sh" || {
      echo "[WARN] first-boot incomplete; run: sudo bash $INSTALL_ROOT/deploy/first-boot-wizard.sh" >&2
    }
  else
    echo "[INFO] No TTY and no SKYCACHE_ADMIN_PIN - defer first-boot."
    echo "       After install: sudo bash $INSTALL_ROOT/deploy/first-boot-wizard.sh"
    echo "       Or: SKYCACHE_ADMIN_PIN=.... SKYCACHE_FIRST_BOOT_YES=1 sudo -E bash deploy/first-boot-wizard.sh --non-interactive"
  fi
fi

systemctl restart skycache.service || systemctl start skycache.service

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "[OK] SkyCache Nexus node $NODE_ID"
echo "     Portal: http://${IP:-<device-ip>}:8080/"
echo "     Env:    $ENV_FILE"
echo "     Caps:   $INSTALL_ROOT/.venv/bin/python -m skycache capabilities --data-dir $DATA_DIR"
echo "     Wizard: sudo bash $INSTALL_ROOT/deploy/first-boot-wizard.sh"
echo "     Hotspot: configure hostapd per deploy/hotspot/ (SSID should match wizard hint)"
echo "     Docs:   docs/first-boot.md  |  docs/mesh-deployment.md"
echo "     Verify spectrum rules before enabling live mesh radios."
echo "     LEGAL: receive-only sat  |  no commercial decrypt  |  not free broadband"
