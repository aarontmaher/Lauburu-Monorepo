#!/usr/bin/env bash
# ==============================================================================
# Sovereign Single-Chat Nexus Daemon Launcher
# Subsystem: 06_scripts_and_tooling/daemons/sovereign_single_chat_nexus_daemon.sh
# Governed by:
# - Rule 3 (Host Sanctuary): Lightweight backend; offloads heavy models
# - Rule 9 (Zero-Waste Background Daemon): Silent native background execution
# - Rule 0 (Zero-Mock): Authentic SQLite persistence & live endpoints
# ==============================================================================

set -euo pipefail

REPO_ROOT="/Volumes/Lauburu-Monorepo"
BACKEND_DIR="${REPO_ROOT}/01_apps/bluetooth_terminal_ide/backend"
PYTHON_BIN="/Users/aaron/.local/bin/python3"
LOG_FILE="${REPO_ROOT}/04_data_and_memory/nexus_server.log"
PID_FILE="${REPO_ROOT}/04_data_and_memory/nexus_server.pid"
PORT=4050

if [ ! -x "${PYTHON_BIN}" ]; then
    PYTHON_BIN="$(which python3)"
fi

mkdir -p "${REPO_ROOT}/04_data_and_memory"
mkdir -p "${REPO_ROOT}/logs"

# Check if port 4050 is already bound
if lsof -ti :${PORT} >/dev/null 2>&1; then
    CURRENT_PID=$(lsof -ti :${PORT} | head -n 1)
    echo "Single-Chat Nexus server is already bound on port ${PORT} (PID: ${CURRENT_PID})."
    exit 0
fi

cd "${BACKEND_DIR}"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting Sovereign Single-Chat Nexus on port ${PORT}..." >> "${LOG_FILE}"

exec "${PYTHON_BIN}" server.py >> "${LOG_FILE}" 2>&1
