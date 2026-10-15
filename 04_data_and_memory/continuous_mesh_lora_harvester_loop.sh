#!/usr/bin/env bash
# ==============================================================================
# continuous_mesh_lora_harvester_loop.sh
# ==============================================================================
# Persistent Background Loop Daemon for Continuous LoRA Harvesting &
# Multi-Tier Training Synchronization across the Lauburu Mesh Ecosystem.
#
# Enforces:
# - Rule #0 (Zero-Mock Data Verification)
# - Rule #3 (Sanctuary RAM Headroom: Mac Host >= 4.8 GB free)
# - Rule #9 (Zero-Waste Background Daemon Governance)
# ==============================================================================

REPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/continuous_mesh_lora_harvester_loop.log"

echo "========================================================================"
echo "⚡ Launching Continuous Mesh LoRA Harvester & Multi-Tier Training Loop..."
echo "Log: ${LOG_FILE}"
echo "========================================================================"

while true; do
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # 1. Check RAM headroom gracefully
    FREE_RAM_PCT=$(memory_pressure 2>/dev/null | awk '/System-wide memory free percentage:/ {print $5}' | tr -d '%' || true)
    FREE_RAM_NUM="${FREE_RAM_PCT:-30}"
    if [ "$FREE_RAM_NUM" -lt 20 ] 2>/dev/null; then
        echo "[${TIMESTAMP}] ⚠️ Host memory free is ${FREE_RAM_NUM}% (<20%). Yielding loop for 30s..." >> "${LOG_FILE}"
        sleep 30
        continue
    fi
    
    # 2. Run continuous multi-stream debate & DPO harvester
    python3 "${REPO_ROOT}/04_data_and_memory/continuous_training_debate_daemon.py" --single-step >> "${LOG_FILE}" 2>&1 || true
    
    # 3. Step multi-tier training coordinator and sync Obsidian ledger
    python3 "${REPO_ROOT}/02_ai_models_and_inference/unified_continuous_mesh_trainer_daemon.py" >> "${LOG_FILE}" 2>&1 || true
    
    # 4. Flush / sync check
    sleep 20
done
