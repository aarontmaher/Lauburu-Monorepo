#!/usr/bin/env bash
# ==============================================================================
# Start Master Priority Automation Daemon (Idempotent from any working directory)
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
mkdir -p "${MONOREPO_ROOT}/session_logs"
mkdir -p "${HOME}/session_logs"

pkill -f "master_priority_automation_loop.py" 2>/dev/null || true

cd "${MONOREPO_ROOT}"
nohup python3 "${MONOREPO_ROOT}/05_agents_and_swarms/master_priority_automation_loop.py" --daemon > "${MONOREPO_ROOT}/session_logs/priority_daemon.log" 2>&1 &

echo "✔ Master Priority Automation Daemon started in background (PID: $!)."
echo "  Log file: ${MONOREPO_ROOT}/session_logs/priority_daemon.log"
