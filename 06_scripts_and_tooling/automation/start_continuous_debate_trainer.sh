#!/usr/bin/env bash
# ==============================================================================
# Start Continuous Polyglot Debate Trainer Daemon
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
mkdir -p "${MONOREPO_ROOT}/session_logs"

pkill -f "continuous_polyglot_debate_trainer.py" 2>/dev/null || true

cd "${MONOREPO_ROOT}"
nohup python3 "${MONOREPO_ROOT}/05_agents_and_swarms/ai_debate/continuous_polyglot_debate_trainer.py" > "${MONOREPO_ROOT}/session_logs/polyglot_debate_trainer.log" 2>&1 &

echo "✔ Continuous Polyglot Debate Trainer started in background (PID: $!)."
echo "  Log file: ${MONOREPO_ROOT}/session_logs/polyglot_debate_trainer.log"
