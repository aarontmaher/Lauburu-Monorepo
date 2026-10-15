#!/usr/bin/env bash
# ==============================================================================
# Pixel AVF IDE Supervisor & Watchdog
# Monitors code-server (:8443), jupyterlab (:8888), chromium (:9222)
# ==============================================================================
set -euo pipefail

STATUS_FILE="/tmp/pixel_avf_ide_status.json"

check_port() {
    local port="$1"
    nc -z -w 2 127.0.0.1 "$port" &>/dev/null && echo "ONLINE" || echo "OFFLINE"
}

action="${1:-status}"

case "$action" in
    start)
        echo "==> Starting Pixel AVF IDE suite..."
        systemctl start code-server.service || true
        systemctl start jupyterlab.service || true
        systemctl start chromium_kiosk.service || true
        ;;
    stop)
        echo "==> Stopping Pixel AVF IDE suite..."
        systemctl stop chromium_kiosk.service || true
        systemctl stop jupyterlab.service || true
        systemctl stop code-server.service || true
        ;;
    status)
        cs_status=$(check_port 8443)
        jl_status=$(check_port 8888)
        cr_status=$(check_port 9222)
        cat <<EOF | tee "$STATUS_FILE"
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "device": "Pixel 10 Pro XL (AVF microVM)",
  "services": {
    "code_server": {"port": 8443, "status": "$cs_status"},
    "jupyterlab": {"port": 8888, "status": "$jl_status"},
    "chromium_devtools": {"port": 9222, "status": "$cr_status"}
  }
}
EOF
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
