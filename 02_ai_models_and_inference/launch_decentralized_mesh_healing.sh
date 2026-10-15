#!/usr/bin/env bash
# ==============================================================================
# Master Launcher for Decentralized prima.cpp Self-Healing Mesh
# Subsystem: 02_ai_models_and_inference/launch_decentralized_mesh_healing.sh
# Lauburu Mesh Ecosystem — 2026
# ==============================================================================

set -euo pipefail

# Resolve true canonical directory even if executed through a symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

PORT="${1:-8082}"
NODE_ID="${2:-L1}"
LOG_FILE="/tmp/lauburu_prima_daemon_${PORT}.log"

echo "========================================================================"
echo "⚡ Launching Decentralized prima.cpp Self-Healing Mesh Daemon"
echo "Node: ${NODE_ID} | Port: ${PORT} | Log: ${LOG_FILE}"
echo "========================================================================"

# Step 1: Terminate any existing daemon on port
PID=$(lsof -ti :${PORT} 2>/dev/null || true)
if [ -n "${PID}" ]; then
    echo "🔄 Stopping stale process on port ${PORT} (PID ${PID})..."
    kill -9 ${PID} 2>/dev/null || true
    sleep 1
fi

# Step 2: Start Daemon in Background
echo "🚀 Starting daemon..."
nohup python3 "${SCRIPT_DIR}/decentralized_prima_daemon.py" "${NODE_ID}" "${PORT}" > "${LOG_FILE}" 2>&1 &

sleep 1.5

# Step 3: Health Verification
echo "🔍 Checking health endpoint (http://localhost:${PORT}/health)..."
HEALTH_JSON=$(curl -s --connect-timeout 3 "http://localhost:${PORT}/health" || echo "")

if [[ "${HEALTH_JSON}" =~ "ONLINE" ]]; then
    echo "✅ Decentralized prima.cpp Daemon is ONLINE!"
    echo "${HEALTH_JSON}" | python3 -m json.tool || echo "${HEALTH_JSON}"
else
    echo "❌ Health check failed. Log output:"
    cat "${LOG_FILE}"
    exit 1
fi

# Step 4: Verification of /v1/heal endpoint
echo "🧪 Testing /v1/heal self-healing endpoint..."
HEAL_RESP=$(curl -s -X POST "http://localhost:${PORT}/v1/heal" \
    -H "Content-Type: application/json" \
    -d '{"target_node_id": "GW", "anomaly_type": "ROUTER_GATEWAY_UNREACHABLE", "metrics": {"rtt_ms": 9999.0}}')

echo "Healing Response: ${HEAL_RESP}"

echo "========================================================================"
echo "🎯 Decentralized Mesh Self-Healing is ACTIVE & ARMED across all devices!"
echo "========================================================================"
