#!/usr/bin/env bash
# ==============================================================================
# 🛡️ nomad_mesh_health_watchdog.sh — 24/7 Autonomous Sovereign Mesh Watchdog
# ==============================================================================
REPO_ROOT="/Volumes/Lauburu-Monorepo"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_DIR}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "${LOG_DIR}/nomad_watchdog.log"; }

# 1. Monorepo AI Health: Multi-core CPU usage during prompt evaluation legitimately
# exceeds 250% on Apple Silicon. CPU percentage kill logic has been removed to preserve
# active inference. Unresponsive daemons are detected via HTTP /health probes below.

# 2. Check Port 8081 (Qwen 2.5 Coder)
if ! curl -s --max-time 3 http://127.0.0.1:8081/health >/dev/null; then
    if pgrep -f "llama-server.*8081" >/dev/null 2>&1; then
        log "Port 8081 process alive but not ready yet. Skipping restart."
    else
        log "Port 8081 unresponsive. Restarting..."
        launchctl kickstart -k gui/501/com.lauburu.qwen-8081 2>/dev/null || "${REPO_ROOT}/02_ai_models_and_inference/launch_canonical_model_stack.sh" >> "${LOG_DIR}/nomad_watchdog.log" 2>&1
    fi
fi

# 3. Check Port 8083 (Qwen Abliterated Red Team)
if ! curl -s --max-time 3 http://127.0.0.1:8083/health >/dev/null; then
    if pgrep -f "llama-server.*8083" >/dev/null 2>&1; then
        log "Port 8083 process alive but not ready yet. Skipping restart."
    else
        log "Port 8083 unresponsive. Restarting..."
        "${REPO_ROOT}/02_ai_models_and_inference/launch_canonical_model_stack.sh" >> "${LOG_DIR}/nomad_watchdog.log" 2>&1
    fi
fi

# 4. Check Port 8082 (Prima Coordinator)
if ! curl -s --max-time 3 http://127.0.0.1:8082/health >/dev/null; then
    if pgrep -f "decentralized_prima_daemon.py" >/dev/null 2>&1; then
        log "Port 8082 prima daemon alive but not ready. Skipping restart."
    else
        log "Port 8082 unresponsive. Restarting..."
        "${REPO_ROOT}/02_ai_models_and_inference/launch_canonical_model_stack.sh" >> "${LOG_DIR}/nomad_watchdog.log" 2>&1
    fi
fi

# 5. Check Port 8101 (Showrunner)
if ! curl -s --max-time 3 http://127.0.0.1:8101/api/status >/dev/null; then
    if pgrep -f "uvicorn.*engine:app.*8101" >/dev/null 2>&1; then
        log "Port 8101 Showrunner process alive but busy. Skipping restart."
    else
        log "Port 8101 Showrunner unresponsive. Restarting..."
        "${REPO_ROOT}/01_apps/lauburu_showrunner/run_showrunner.py" restart >> "${LOG_DIR}/nomad_watchdog.log" 2>&1
    fi
fi
