#!/usr/bin/env bash
# SkyCache first-boot wizard (Debian / Raspberry Pi OS)
# Sets PIN, SSID hint, legal_rf_mode; loads samples + Skybrary; prints capabilities.
# LEGAL: receive-only satellite; no commercial decrypt; not free Starlink / broadband.
set -euo pipefail

INSTALL_ROOT="${SKYCACHE_INSTALL_ROOT:-/opt/skycache}"
DATA_DIR="${SKYCACHE_DATA_DIR:-/var/lib/skycache}"
APP_USER="${SKYCACHE_USER:-skycache}"
ENV_FILE="${SKYCACHE_ENV_FILE:-$DATA_DIR/skycache.env}"
UNIT="${SKYCACHE_SYSTEMD_UNIT:-/etc/systemd/system/skycache.service}"
PY="${SKYCACHE_PYTHON:-}"

echo "[SkyCache] first-boot wizard"
echo "  INSTALL_ROOT=$INSTALL_ROOT"
echo "  DATA_DIR=$DATA_DIR"
echo "  Banner: store-and-forward + community mesh - not free commercial broadband"
echo ""

if [[ -z "$PY" ]]; then
  if [[ -x "$INSTALL_ROOT/.venv/bin/python" ]]; then
    PY="$INSTALL_ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "ERROR: Python not found. Run deploy/install-village-fabric.sh or install-debian.sh first." >&2
    exit 1
  fi
fi

mkdir -p "$DATA_DIR"

# Build args for skycache first-boot (pass-through)
FB_ARGS=(first-boot --data-dir "$DATA_DIR" --env-file "$ENV_FILE" --sim)
if [[ "${1:-}" == "--non-interactive" ]] || [[ "${SKYCACHE_FIRST_BOOT_YES:-}" == "1" ]]; then
  shift || true
  if [[ -z "${SKYCACHE_ADMIN_PIN:-}" ]]; then
    echo "ERROR: non-interactive mode needs SKYCACHE_ADMIN_PIN (4-8 digits, not 2468)." >&2
    exit 2
  fi
  FB_ARGS+=(--yes --pin "$SKYCACHE_ADMIN_PIN")
  [[ -n "${SKYCACHE_HOTSPOT_SSID:-}" ]] && FB_ARGS+=(--ssid "$SKYCACHE_HOTSPOT_SSID")
  [[ -n "${SKYCACHE_LEGAL_RF_MODE:-}" ]] && FB_ARGS+=(--legal-rf-mode "$SKYCACHE_LEGAL_RF_MODE")
  [[ "${SKYCACHE_AMATEUR_LICENSE_AFFIRMED:-}" == "true" || "${SKYCACHE_AMATEUR_LICENSE_AFFIRMED:-}" == "1" ]] && \
    FB_ARGS+=(--amateur-affirmed)
  [[ -n "${SKYCACHE_NODE_ID:-}" ]] && FB_ARGS+=(--node-id "$SKYCACHE_NODE_ID")
  [[ -n "${SKYCACHE_LANG:-}" ]] && FB_ARGS+=(--lang "$SKYCACHE_LANG")
  [[ "${SKYCACHE_FIRST_BOOT_FORCE:-}" == "1" ]] && FB_ARGS+=(--force)
  FB_ARGS+=("$@")
else
  FB_ARGS+=("$@")
fi

# Prefer app user when present and we are root
run_fb() {
  if [[ "$(id -u)" -eq 0 ]] && id "$APP_USER" &>/dev/null; then
    chown -R "$APP_USER":"$APP_USER" "$DATA_DIR" || true
    sudo -u "$APP_USER" env \
      SKYCACHE_DATA_DIR="$DATA_DIR" \
      "$PY" -m skycache "${FB_ARGS[@]}"
  else
    env SKYCACHE_DATA_DIR="$DATA_DIR" "$PY" -m skycache "${FB_ARGS[@]}"
  fi
}

run_fb
RC=$?
if [[ $RC -ne 0 ]]; then
  exit "$RC"
fi

# Wire EnvironmentFile into systemd unit when root + unit exists
if [[ "$(id -u)" -eq 0 ]] && [[ -f "$UNIT" ]] && [[ -f "$ENV_FILE" ]]; then
  if ! grep -q "EnvironmentFile=.*skycache.env" "$UNIT" 2>/dev/null; then
    # Insert after [Service] block start if missing
    if grep -q '^\[Service\]' "$UNIT"; then
      tmp="$(mktemp)"
      awk -v envf="EnvironmentFile=-$ENV_FILE" '
        BEGIN { done=0 }
        /^\[Service\]/ { print; if (!done) { print envf; done=1; next } }
        { print }
      ' "$UNIT" > "$tmp"
      mv "$tmp" "$UNIT"
      echo "[SkyCache] Added EnvironmentFile=-$ENV_FILE to $UNIT"
      systemctl daemon-reload || true
      if systemctl is-enabled skycache.service &>/dev/null; then
        systemctl restart skycache.service || systemctl start skycache.service || true
        echo "[SkyCache] Restarted skycache.service with new env"
      fi
    fi
  else
    systemctl daemon-reload || true
    systemctl restart skycache.service 2>/dev/null || true
  fi
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "[OK] First-boot complete"
echo "  Env:    $ENV_FILE"
echo "  Portal: http://${IP:-<device-ip>}:8080/"
echo "  Caps:   $PY -m skycache capabilities --data-dir $DATA_DIR"
echo "  Docs:   docs/first-boot.md"
echo "  Legal:  receive-only sat  |  no commercial decrypt  |  honest mesh only"
exit 0
