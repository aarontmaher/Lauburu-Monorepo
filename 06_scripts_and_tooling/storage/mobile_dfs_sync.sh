#!/usr/bin/env bash
# ==============================================================================
# MOBILE DISTRIBUTED DFS SYNCHRONIZER (SeaweedFS Pool)
# Subsystem: 06_scripts_and_tooling/storage/mobile_dfs_sync.sh
# Integrates Samsung Galaxy S20+ (L7) and Pixel 10 Pro XL (L6) into SeaweedFS
# ==============================================================================
set -euo pipefail

WEBDAV_HOST="100.119.199.76:7333"
S20_HOST="192.168.8.131"
PIXEL_HOST="100.73.38.87"

echo "=== 🌊 LAUBURU MOBILE STORAGE POOL SYNCHRONIZER ==="
echo "Target SeaweedFS WebDAV: http://${WEBDAV_HOST}"

# 1. Sync Samsung S20+
echo -e "\n📱 [1/2] Syncing Samsung Galaxy S20+..."
if ssh -p 8022 -o ConnectTimeout=4 "${S20_HOST}" "rclone version" >/dev/null 2>&1; then
    ssh -p 8022 "${S20_HOST}" "
        mkdir -p ~/mobile_pool
        echo \"S20 Heartbeat: \$(date -u +'%Y-%m-%dT%H:%M:%SZ') | Free: \$(df -h /storage/emulated 2>/dev/null | tail -1 | awk '{print \$4}')\" > ~/mobile_pool/s20_telemetry.txt
        rclone copy ~/mobile_pool/ seaweedfs:edge_mounts/s20_storage/
        echo \"✓ Samsung S20+ storage pool synchronized.\"
    "
else
    echo "⚠️ Samsung S20+ unreachable or sleeping."
fi

# 2. Sync Pixel 10 Pro XL
echo -e "\n📱 [2/2] Syncing Pixel 10 Pro XL..."
if ssh -p 8022 -o ConnectTimeout=4 "${PIXEL_HOST}" "rclone version" >/dev/null 2>&1; then
    ssh -p 8022 "${PIXEL_HOST}" "
        mkdir -p ~/mobile_pool
        echo \"Pixel 10 Heartbeat: \$(date -u +'%Y-%m-%dT%H:%M:%SZ') | Free: \$(df -h /storage/emulated 2>/dev/null | tail -1 | awk '{print \$4}')\" > ~/mobile_pool/pixel_telemetry.txt
        rclone copy ~/mobile_pool/ seaweedfs:edge_mounts/pixel_storage/
        echo \"✓ Pixel 10 Pro XL storage pool synchronized.\"
    "
else
    echo "⚠️ Pixel 10 Pro XL unreachable or sleeping."
fi

echo -e "\n=== 📊 VERIFYING POOLED FILES IN SEAWEEDFS FILER ==="
curl -s "http://127.0.0.1:8888/edge_mounts/s20_storage/s20_telemetry.txt" || true
echo ""
curl -s "http://127.0.0.1:8888/edge_mounts/pixel_storage/pixel_telemetry.txt" || true
echo -e "\n✓ Mobile storage pool sync complete."
