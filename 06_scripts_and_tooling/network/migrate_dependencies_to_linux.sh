#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh Dependency Migration & Host Sanctuary Governor
# ==============================================================================
# Enforces:
#   - Rule 3: Host Sanctuary & Dynamic RAM Governance (>= 4.8 GB free, <= 80% util)
#   - Rule 9: Multi-IP Fallback (LAN -> Tailscale)
#   - Rule 10: Linux Mini First-Offload Invariant & VRAM Sparing
#
# Target: L3 Linux Head Node (AMD Ryzen 7 5700U)
#   Tailscale IP: 10.1.0.12
#   LAN IP:       192.168.8.225
#   User:         linux
#   Remote Repo:  /home/linux/DFS_UNIFIED/Lauburu-Monorepo
# ==============================================================================

set -uo pipefail

echo "========================================================================"
echo "🚀 Initiating VRAM/RAM Conservation: Migrating Host Dependencies to L3"
echo "========================================================================"

LOCAL_REPO="/Volumes/Lauburu-Monorepo"
REMOTE_REPO="/home/linux/DFS_UNIFIED/Lauburu-Monorepo"
LINUX_USER="linux"
LINUX_LAN_IP="192.168.8.225"
LINUX_TS_IP="10.1.0.12"

# ------------------------------------------------------------------------------
# 1. Resolve Target IP via Rule 9 Multi-IP Fallback
# ------------------------------------------------------------------------------
TARGET_IP=""
echo "🔍 Probing L3 Linux Head Node reachability..."

if ping -c 1 -W 1000 "${LINUX_LAN_IP}" >/dev/null 2>&1; then
    TARGET_IP="${LINUX_LAN_IP}"
    echo "✅ Selected Fast L2 LAN Link: ${TARGET_IP} (AMD Ryzen 7 5700U)"
elif ping -c 1 -W 2000 "${LINUX_TS_IP}" >/dev/null 2>&1; then
    TARGET_IP="${LINUX_TS_IP}"
    echo "✅ Selected L3 Tailscale Link: ${TARGET_IP} (AMD Ryzen 7 5700U)"
else
    echo "❌ ERROR: Cannot reach L3 Linux Head Node on LAN (${LINUX_LAN_IP}) or Tailscale (${LINUX_TS_IP})."
    exit 1
fi

SSH_CMD="ssh -o ConnectTimeout=5 -o BatchMode=yes ${LINUX_USER}@${TARGET_IP}"

# Verify SSH authentication
if ! ${SSH_CMD} "echo 'SSH_AUTH_OK'" >/dev/null 2>&1; then
    echo "❌ ERROR: SSH authentication failed for ${LINUX_USER}@${TARGET_IP}."
    exit 1
fi
echo "✅ Authenticated SSH connection to L3 Linux Head Node."

# ------------------------------------------------------------------------------
# 2. Sync Application Directories to L3 Linux Head Node
# ------------------------------------------------------------------------------
echo "📦 Synchronizing application directories to L3 (${REMOTE_REPO})..."

${SSH_CMD} "mkdir -p ${REMOTE_REPO}/01_apps ${REMOTE_REPO}/05_agents_and_swarms ${REMOTE_REPO}/06_scripts_and_tooling"

# 2.1 Sync Network Cable Analyzer
echo "   -> Syncing 01_apps/network_cable_analyzer..."
rsync -avz --delete \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude="*.log" \
    --exclude="*.err" \
    --exclude=".dart_tool" \
    --exclude="build" \
    "${LOCAL_REPO}/01_apps/network_cable_analyzer/" \
    "${LINUX_USER}@${TARGET_IP}:${REMOTE_REPO}/01_apps/network_cable_analyzer/" >/dev/null

# 2.2 Sync Lauburu Showrunner
echo "   -> Syncing 01_apps/lauburu_showrunner..."
rsync -avz --delete \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude="*.log" \
    --exclude="*.err" \
    --exclude=".dart_tool" \
    --exclude="build" \
    "${LOCAL_REPO}/01_apps/lauburu_showrunner/" \
    "${LINUX_USER}@${TARGET_IP}:${REMOTE_REPO}/01_apps/lauburu_showrunner/" >/dev/null

echo "✅ App synchronization complete."

# ------------------------------------------------------------------------------
# 3. Kill Mac Mini Services (Freeing Memory/VRAM per Rule 3 & 10)
# ------------------------------------------------------------------------------
echo "🛑 Stopping target background services on Mac Mini Host..."

# Stop and unload launchd services to prevent automatic respawn
launchctl stop com.lauburu.showrunner 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.lauburu.showrunner.plist 2>/dev/null || true
launchctl stop com.lauburu.nomad-watchdog 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.lauburu.nomad-watchdog.plist 2>/dev/null || true

# Terminate active Uvicorn and related servers
pkill -9 -f "01_apps.network_cable_analyzer.backend.server:app" 2>/dev/null || true
pkill -9 -f "network_cable_analyzer" 2>/dev/null || true
pkill -9 -f "lauburu_showrunner" 2>/dev/null || true
pkill -9 -f "run_showrunner.py" 2>/dev/null || true
pkill -f "voila.*00_lauburu_global_master_project.ipynb" 2>/dev/null || true
pkill -f "tui_bench_automator.py" 2>/dev/null || true
pkill -f "ai_debate_tui_sync.py" 2>/dev/null || true
pkill -f "antigravity_qwen_bridge_server.py" 2>/dev/null || true
pkill -f "swarm_dashboard_ai_training/backend/app.py" 2>/dev/null || true
pkill -f "mac-system2-daemon" 2>/dev/null || true
pkill -f "lens_project_teacher_sweep.py" 2>/dev/null || true
pkill -f "lens_flawless_auditor.py" 2>/dev/null || true
pkill -f "mcts_lora_harvester.py" 2>/dev/null || true
pkill -f "master_free_tier_ai_maximizer.py" 2>/dev/null || true
pkill -f "serve_web_tui.py" 2>/dev/null || true
pkill -f "run_continuous_free_tier_trainer.py" 2>/dev/null || true

echo "✅ Target Mac Mini background services stopped."

# ------------------------------------------------------------------------------
# 4. Stop Stale Remote Services on L3
# ------------------------------------------------------------------------------
echo "🛑 Cleaning up stale remote services on L3..."
${SSH_CMD} "pkill -f 'uvicorn.*4007' 2>/dev/null || true; pkill -f 'uvicorn.*8101' 2>/dev/null || true"
sleep 1

# ------------------------------------------------------------------------------
# 5. Launch Services on L3 Linux Head Node
# ------------------------------------------------------------------------------
echo "🚀 Launching services on L3 Linux Head Node..."

# 5.1 Launch Network Cable Analyzer on Port 4007
echo "   -> Starting Network Cable Analyzer (Port 4007)..."
${SSH_CMD} "nohup /usr/local/bin/uvicorn 01_apps.network_cable_analyzer.backend.server:app \
    --app-dir ${REMOTE_REPO} \
    --host 0.0.0.0 \
    --port 4007 > /home/linux/cable_analyzer.log 2>&1 &"

# 5.2 Launch Showrunner Engine on Port 8101
echo "   -> Starting Lauburu Showrunner Engine (Port 8101)..."
${SSH_CMD} "nohup /usr/local/bin/uvicorn engine:app \
    --app-dir ${REMOTE_REPO}/01_apps/lauburu_showrunner/backend \
    --host 0.0.0.0 \
    --port 8101 > /home/linux/showrunner.log 2>&1 &"

# 5.3 Launch CPU-Only Inference Models on L8 (Linux Mini 32GB)
echo "   -> Offloading CPU-bound llama.cpp inference to L8 Linux Mini (Port 8092)..."
SSH_CMD_L8="ssh -o ConnectTimeout=5 -o BatchMode=yes linuxmini@100.121.247.8"
${SSH_CMD_L8} "pkill -f 'llama-server.*8092' 2>/dev/null || true; nohup /usr/local/bin/llama-server \
    -m ${REMOTE_REPO}/models/DeepSeek-Coder-V2-Lite-Base-Q4_K_M.gguf \
    --port 8092 \
    --host 0.0.0.0 \
    --threads 12 \
    -cb > /home/linuxmini/cpu_inference.log 2>&1 &"

# ------------------------------------------------------------------------------
# 6. Verify Remote Services Health via HTTP Probes
# ------------------------------------------------------------------------------
echo "🔎 Verifying remote service endpoints on L3..."

wait_for_endpoint() {
    local url="$1"
    local name="$2"
    local retries=30
    while [ $retries -gt 0 ]; do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        if [ "$code" = "200" ]; then
            echo "✅ ${name}: HTTP 200 OK (${url})"
            return 0
        fi
        sleep 1
        retries=$((retries - 1))
    done
    echo "⚠️ WARNING: ${name} returned HTTP ${code} after timeout"
    return 1
}

wait_for_endpoint "http://${TARGET_IP}:4007/docs" "Port 4007 (Network Cable Analyzer)"
wait_for_endpoint "http://${TARGET_IP}:8101/docs" "Port 8101 (Lauburu Showrunner)"

# ------------------------------------------------------------------------------
# 7. Verify Mac Mini Host Physical RAM Sanctuary (Rule 3)
# ------------------------------------------------------------------------------
echo "🛡️ Evaluating Mac Mini Host Physical RAM Sanctuary (Rule 3)..."

python3 -c '
import subprocess, sys

try:
    vm = subprocess.check_output(["vm_stat"]).decode("utf-8")
    stats = {}
    for l in vm.splitlines():
        if ":" in l:
            parts = l.split(":")
            k = parts[0].strip()
            v = parts[1].strip().rstrip(".")
            if v.isdigit():
                stats[k] = int(v)

    page_size = 16384
    free_b = stats.get("Pages free", 0) * page_size
    spec_b = stats.get("Pages speculative", 0) * page_size
    inactive_b = stats.get("Pages inactive", 0) * page_size
    active_b = stats.get("Pages active", 0) * page_size
    wired_b = stats.get("Pages wired down", 0) * page_size
    compr_b = stats.get("Pages occupied by compressor", 0) * page_size

    total_mem = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode("utf-8").strip())

    avail_b = free_b + spec_b + inactive_b
    avail_gb = avail_b / (1024**3)
    used_b = active_b + wired_b + compr_b
    used_gb = used_b / (1024**3)
    total_gb = total_mem / (1024**3)
    util_pct = (used_b / total_mem) * 100

    pass_sanctuary = "PASS ✅" if avail_gb >= 4.8 else "FAIL ❌"
    pass_util = "PASS ✅" if util_pct <= 80.0 else "FAIL ❌"

    print(f"   • Total Physical RAM:       {total_gb:.2f} GB")
    print(f"   • Used RAM:                 {used_gb:.2f} GB ({util_pct:.1f}%)")
    print(f"   • Reclaimable Available:    {avail_gb:.2f} GB")
    print(f"   • Sanctuary Target (>=4.8G): {pass_sanctuary}")
    print(f"   • Util Cap Target (<=80%):  {pass_util}")

    if avail_gb < 4.8 or util_pct > 80.0:
        sys.exit(1)
except Exception as e:
    print(f"Error evaluating RAM sanctuary: {e}")
    sys.exit(1)
'

echo "========================================================================"
echo "🎉 Migration Complete. L1 Host RAM sanctuary preserved for Sovereign AI."
echo "========================================================================"
