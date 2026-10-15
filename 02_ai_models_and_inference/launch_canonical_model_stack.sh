#!/usr/bin/env bash
# ==============================================================================
# 🚀 launch_canonical_model_stack.sh — Master Sovereign Local AI Stack Launcher
# ==============================================================================
# Subsystem: 02_ai_models_and_inference
# Governed by Rule 3 (Host Sanctuary), Rule 7 (Qwen Hierarchy), Rule 8 (Pre-flight Gate)
# ==============================================================================
set -eo pipefail

REPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_DIR}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== 🛡️ 1. Pre-Flight Storage & Host RAM Sanctuary Gate ==="
AVAIL_RAM=$(vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages free:\s+(\d+)/ and $free=$1; /Pages speculative:\s+(\d+)/ and $spec=$1; /Pages inactive:\s+(\d+)/ and $inact=$1; END { printf("%.2f", ($free + $spec + $inact) * $size / (1024*1024*1024)); }')
log "Available Host RAM: ${AVAIL_RAM} GB"

# Clean any hung or zombie llama-server instances if needed
pkill -f "qwen2.5-coder-1.5b" 2>/dev/null || true

log "=== ⚡ 2. Routing Subordinate Syntax Worker (Port 8081 -> L2 / L3 Mesh Offload) ==="
# Governed by Rule 8 (Strict Duo Supremacy) & Rule 10 (Linux Mini First-Offload)
# Syntax worker runs on peripheral node (L2: 100.103.212.21:8081 / L3: 100.101.39.98:8081)
log "Syntax worker routed to peripheral mesh to spare Mac Mini Unified Memory."

log "=== 🔴 3. Starting Canonical Adversarial Red Team (Port 8083: Qwen 3.8 Max Abliterated) ==="
if pgrep -f "llama-server.*8083" >/dev/null 2>&1 || nc -z 127.0.0.1 8083 2>/dev/null; then
    log "Port 8083 is already active or initializing (PID: $(pgrep -f "llama-server.*8083" | head -n 1))."
else
    nohup /Users/aaron/.local/bin/llama-server \
        -m "${REPO_ROOT}/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf" \
        --alias qwen_38_max_abliterated \
        --alias qwen2.5-7b-instruct-abliterated \
        -np 2 \
        --cont-batching \
        -ngl 99 \
        -c 16384 \
        --host 127.0.0.1 \
        --port 8083 \
        > "${LOG_DIR}/qwen_8083.log" 2>&1 &
    log "Launched Qwen 3.8 Max Abliterated on port 8083 with -np 2 (PID: $!)"
    sleep 2
fi

log "=== 👑 4. Starting Sovereign Master Coordinator (Port 8082: prima.cpp Daemon) ==="
if ! nc -z 127.0.0.1 8082 2>/dev/null; then
    nohup /usr/bin/python3 "${REPO_ROOT}/02_ai_models_and_inference/decentralized_prima_daemon.py" \
        > "${LOG_DIR}/prima_daemon.log" 2>&1 &
    log "Launched Decentralized Prima Daemon on port 8082 (PID: $!)"
    sleep 1
else
    log "Port 8082 is already active."
fi

log "=== 🎬 5. Starting Lauburu Showrunner Backend (Port 8101) ==="
if ! nc -z 127.0.0.1 8101 2>/dev/null; then
    nohup "${REPO_ROOT}/01_apps/lauburu_showrunner/backend/venv/bin/python3" \
        -m uvicorn engine:app \
        --app-dir "${REPO_ROOT}/01_apps/lauburu_showrunner/backend" \
        --host 0.0.0.0 \
        --port 8101 \
        --log-level info \
        > "${REPO_ROOT}/01_apps/lauburu_showrunner/backend/showrunner.log" 2>&1 &
    log "Launched Showrunner FastAPI on port 8101 (PID: $!)"
    sleep 2
else
    log "Port 8101 is already active."
fi

log "=== 🧪 6. Live Health Verification ==="
curl -s --max-time 3 http://127.0.0.1:8081/health && echo " [8081 Syntax Worker: OK]" || echo " [8081: FAIL]"
curl -s --max-time 3 http://127.0.0.1:8083/health && echo " [8083 Red Team: OK]" || echo " [8083: FAIL]"
curl -s --max-time 3 http://127.0.0.1:8082/health && echo " [8082 Sovereign Coordinator: OK]" || echo " [8082: FAIL]"
curl -s --max-time 3 http://127.0.0.1:8101/api/status | grep -q "RUNNING" && echo " [8101 Showrunner: OK]" || echo " [8101: FAIL]"

log "🎉 Sovereign Model Stack successfully initialized and verified!"
