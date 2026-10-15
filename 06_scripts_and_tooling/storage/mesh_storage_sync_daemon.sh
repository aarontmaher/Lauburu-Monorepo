#!/usr/bin/env bash
# ==============================================================================
# LAUBURU MESH 24/7 BIDIRECTIONAL STORAGE SYNC DAEMON
# Subsystem: 06_scripts_and_tooling/storage
# Synchronizes Mac Mini local fast NVMe storage with Router Sovereign Storage
# ==============================================================================
set -euo pipefail

ROUTER_FILER="${ROUTER_FILER:-192.168.8.1:8888}"
LOCAL_FILER="${LOCAL_FILER:-127.0.0.1:8888}"
LOG_FILE="/tmp/lauburu_mesh_storage_sync.log"

while true; do
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting SeaweedFS Filer Real-Time Sync..." >> "${LOG_FILE}"
    if nc -z -w 2 192.168.8.1 8888 2>/dev/null && nc -z -w 2 127.0.0.1 8888 2>/dev/null; then
        /Users/aaron/.local/bin/weed filer.sync \
            -a="${LOCAL_FILER}" \
            -b="${ROUTER_FILER}" \
            >> "${LOG_FILE}" 2>&1 || true
    else
        echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Waiting for filers to become reachable..." >> "${LOG_FILE}"
    fi
    sleep 5
done
