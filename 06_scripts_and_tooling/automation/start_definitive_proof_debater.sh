#!/usr/bin/env bash
# ==============================================================================
# Start Continuous Definitive Proof AI Debate Daemon
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
mkdir -p "${MONOREPO_ROOT}/session_logs"

pkill -f "continuous_definitive_proof_debater.py" 2>/dev/null || true

cd "${MONOREPO_ROOT}"
nohup python3 "${MONOREPO_ROOT}/05_agents_and_swarms/ai_debate/continuous_definitive_proof_debater.py" > "${MONOREPO_ROOT}/session_logs/definitive_proof_debater.log" 2>&1 &

echo "✔ Continuous Definitive Proof Debater started in background (PID: $!)."
echo "  Log file: ${MONOREPO_ROOT}/session_logs/definitive_proof_debater.log"
