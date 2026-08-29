#!/usr/bin/env bash
# ==============================================================================
# Launch Qwen-3.8Max Abliterated Adversarial Benchmark Disprover Daemon
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
mkdir -p "${MONOREPO_ROOT}/session_logs"

pkill -f "adversarial_benchmark_disprover.py" 2>/dev/null || true

cd "${MONOREPO_ROOT}"
nohup python3 "${MONOREPO_ROOT}/05_agents_and_swarms/ai_debate/adversarial_benchmark_disprover.py" > "${MONOREPO_ROOT}/session_logs/adversarial_skeptic.log" 2>&1 &

echo "✔ Qwen-3.8Max Abliterated Adversarial Disprover started in background (PID: $!)."
echo "  Log file: ${MONOREPO_ROOT}/session_logs/adversarial_skeptic.log"
