#!/usr/bin/env bash
# ==============================================================================
# SeaweedFS Multi-Device Distributed Storage Merger & Mount Script
# Subsystem: 00_core_infrastructure/seaweedfs_cluster_merge.sh
# Pools physical drives across all 7 mesh layers into a single unified mount point
# ==============================================================================

# ⚠️ DEPRECATED: Use 00_core_infrastructure/scripts/start_seaweed_ha.sh for the 3-node Raft HA cluster.
# This script is retained for single-node fallback only. It now uses Tailscale IPs.

set -euo pipefail

MASTER_IP="100.119.199.76"
MASTER_PORT="9333"
FILER_PORT="8888"
UNIFIED_MOUNT="/Volumes/Lauburu-Monorepo"
LOCAL_STORAGE_DIR="/Users/aaron/.local/var/seaweedfs"

mkdir -p "${LOCAL_STORAGE_DIR}" "${UNIFIED_MOUNT}"

echo "=================================================================="
echo " 🌊 LAUBURU DISTRIBUTED STORAGE ENGINE: SEAWEEDFS UNIFIED CLUSTER"
echo "=================================================================="

# 1. Check if Master & Filer are already active on Mac Mini Host
if pgrep -f "weed server" >/dev/null; then
    echo "🟢 SeaweedFS Master & Filer already running on ${MASTER_IP}:${MASTER_PORT}."
else
    echo "🚀 Launching SeaweedFS Master & Filer on ${MASTER_IP}..."
    weed server -dir="${LOCAL_STORAGE_DIR}" \
        -master.port="${MASTER_PORT}" \
        -filer=true \
        -filer.port="${FILER_PORT}" \
        -volume.port=8080 \
        -ip.bind=0.0.0.0 \
        -ip="${MASTER_IP}" \
        -master.peers=100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333 > /tmp/seaweedfs_master.log 2>&1 &
    sleep 2
fi

# 2. Instructions to attach remote node storage drives into this master
cat << 'EOF'

To attach remote storage drives into this single unified pool:

1. On MacBook Pro Vault (L2 - 285 GB SSD):
   ssh aaron@192.168.8.127 "weed volume -dir=/Volumes/ModelVault/seaweed_volume -mserver=100.119.199.76:9333 -port=8081 &"

2. On Linux Head Node (L4 - 512 GB NVMe):
   ssh linux@100.101.39.98 "weed volume -dir=/home/linux/seaweed_volume -mserver=192.168.8.230:9333 -port=8082 &"

3. Mount FUSE volume on any client node:
   weed mount -filer=100.119.199.76:8888 -dir=/Volumes/Lauburu-Monorepo

All drives across all machines now function transparently as ONE unified drive!
EOF
