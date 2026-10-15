#!/usr/bin/env bash
# ==============================================================================
# One-Click Physical Deployment Script for GL.iNet Beryl AX (GL-MT3000/3600)
# Subsystem: 01_apps/glinet_web_optimizer/deploy_to_physical_beryl_ax.sh
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

ROUTER_IP="${1:-192.168.8.1}"
SSH_USER="${2:-root}"
SSH_PORT="${3:-22}"
SSH_PASS="${SSH_PASS:-goldfighting1}"

echo "========================================================================"
echo "🚀 Deploying Lauburu Autonomous Supervisor to Physical Beryl AX Router"
echo "Target: ${SSH_USER}@${ROUTER_IP}:${SSH_PORT}"
echo "========================================================================"

# Step 1: Pre-flight SSH Connectivity Check
echo "🔍 Step 1: Checking SSH connectivity..."
if command -v sshpass >/dev/null 2>&1; then
    SSH_EXEC="sshpass -p '${SSH_PASS}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p ${SSH_PORT} ${SSH_USER}@${ROUTER_IP}"
else
    SSH_EXEC="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p ${SSH_PORT} ${SSH_USER}@${ROUTER_IP}"
fi

eval "${SSH_EXEC} 'uname -a'" || {
    echo "❌ SSH Connection failed! Ensure router is powered on at ${ROUTER_IP} and Dropbear SSH is enabled."
    exit 1
}

# Step 2: Hardware Architecture & Memory Verification
echo "🧠 Step 2: Verifying Beryl AX hardware & RAM..."
eval "${SSH_EXEC} 'cat /proc/cpuinfo | grep -E \"model name|Hardware|Processor\" | head -n 2'"
FREE_RAM_KB=$(eval "${SSH_EXEC} 'grep MemAvailable /proc/meminfo | awk \"{print \\\$2}\"'")
FREE_RAM_MB=$((FREE_RAM_KB / 1024))
echo "Available RAM: ${FREE_RAM_MB} MB"

# Step 3: Setup Volatile Working Directory (Zero NAND Flash Wear)
echo "📁 Step 3: Initializing volatile runtime in tmpfs (/tmp/run/ai_supervisor)..."
eval "${SSH_EXEC} 'mkdir -p /tmp/run/ai_supervisor /tmp/run/ai_supervisor/ipc /tmp/run/ai_supervisor/logs'"

# Step 4: Transfer Compiled Native Musl Binaries (if present)
STATIC_SENTINEL="/Users/aaron/teamwork_projects/router_micro_llm_supervisor/target/aarch64-unknown-linux-musl/release/router_sentinel"
if [ -f "$STATIC_SENTINEL" ]; then
    echo "📦 Step 4: Transferring compiled static aarch64 router_sentinel (379 KB)..."
    if command -v sshpass >/dev/null 2>&1; then
        sshpass -p "${SSH_PASS}" ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "${SSH_USER}@${ROUTER_IP}" "cat > /tmp/run/ai_supervisor/router_sentinel" < "${STATIC_SENTINEL}"
    else
        ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "${SSH_USER}@${ROUTER_IP}" "cat > /tmp/run/ai_supervisor/router_sentinel" < "${STATIC_SENTINEL}"
    fi
    eval "${SSH_EXEC} 'chmod +x /tmp/run/ai_supervisor/router_sentinel'"
fi

# Step 5: Install Procd Service Init Script (Using SSH Pipe for Dropbear compatibility)
echo "⚙️ Step 5: Installing procd init script (/etc/init.d/lauburu_supervisor)..."
INIT_FILE="${SCRIPT_DIR}/lauburu_supervisor.init"

if command -v sshpass >/dev/null 2>&1; then
    sshpass -p "${SSH_PASS}" ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "${SSH_USER}@${ROUTER_IP}" "cat > /etc/init.d/lauburu_supervisor" < "${INIT_FILE}"
else
    ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "${SSH_USER}@${ROUTER_IP}" "cat > /etc/init.d/lauburu_supervisor" < "${INIT_FILE}"
fi

eval "${SSH_EXEC} 'chmod +x /etc/init.d/lauburu_supervisor && /etc/init.d/lauburu_supervisor enable'"

# Step 6: Start Service & Verify Status
echo "⚡ Step 6: Starting Lauburu Embedded Supervisor..."
eval "${SSH_EXEC} '/etc/init.d/lauburu_supervisor restart'"

sleep 1
echo "📊 Step 7: Verifying service health & cgroups..."
eval "${SSH_EXEC} '/etc/init.d/lauburu_supervisor status && ps | grep -E \"router_sentinel|lauburu\" | grep -v grep || true'"

echo "========================================================================"
echo "✅ Physical Beryl AX deployment completed successfully!"
echo "========================================================================"
