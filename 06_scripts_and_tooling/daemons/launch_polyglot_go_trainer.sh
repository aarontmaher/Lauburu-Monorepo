#!/usr/bin/env bash
# ==============================================================================
# launch_polyglot_go_trainer.sh
# ==============================================================================
# 24/7 Continuous Polyglot Model Training Daemon (Rust/wgpu & Go)
# Subsystem: 05_agents_and_swarms/continuous_polyglot_go_trainer
# Lauburu Mesh Ecosystem — 2026
#
# Governs continuous background training, live compiler verification, and
# Tri-Vault synchronization (PySpark JSONL, Obsidian Knowledge Vault, Git).
# ==============================================================================
set -euo pipefail

REPO_ROOT="/Volumes/Lauburu-Monorepo"
MODULE_DIR="${REPO_ROOT}/05_agents_and_swarms/continuous_polyglot_go_trainer"
BINARY="${MODULE_DIR}/continuous_polyglot_go_trainer"
LOG_DIR="${REPO_ROOT}/04_data_and_memory/logs"
LOG_FILE="${LOG_DIR}/polyglot_go_trainer.log"
PID_FILE="${LOG_DIR}/polyglot_go_trainer.pid"
INTERVAL="${1:-30.0}"

mkdir -p "${LOG_DIR}"

# 1. Build binary if missing or if sources are newer
if [[ ! -f "${BINARY}" ]] || [[ "${MODULE_DIR}/trainer.go" -nt "${BINARY}" ]]; then
    echo "🔨 Building continuous_polyglot_go_trainer binary..."
    (cd "${MODULE_DIR}" && go build -o "${BINARY}" .)
fi

# 2. Check if already running
if [[ -f "${PID_FILE}" ]]; then
    OLD_PID=$(cat "${PID_FILE}")
    if ps -p "${OLD_PID}" > /dev/null 2>&1; then
        echo "⚠️ Polyglot Go Trainer is already running with PID: ${OLD_PID}"
        exit 0
    fi
fi

# 3. Launch in background
echo "🚀 Launching Continuous Polyglot Trainer Daemon (interval: ${INTERVAL}s)..."
nohup "${BINARY}" --daemon --interval "${INTERVAL}" >> "${LOG_FILE}" 2>&1 &
TRAINER_PID=$!
echo "${TRAINER_PID}" > "${PID_FILE}"

echo "✅ Polyglot Go Trainer daemon active with PID: ${TRAINER_PID}"
echo "   • Log file: ${LOG_FILE}"
echo "   • State file: ${REPO_ROOT}/04_data_and_memory/polyglot_go_trainer_state.json"
echo "   • Obsidian ledger: ${REPO_ROOT}/obsidian_vault/05_AI_SWARMS/POLYGLOT_GO_RUST_WGPU_TRAINING_LEDGER.md"
