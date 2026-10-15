#!/bin/bash
set -eo pipefail

LOG_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs"
MODEL_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
MODEL_FILE="Hermes-3-Llama-3.1-70B.Q4_K_M.gguf"
# Pure Mac/Host Sharding (L1, L2, plus L3 for spillover)
RPC_TARGETS="169.254.175.124:50052,100.101.39.98:50052" 

pkill -f "llama-server.*Hermes-3.*70B" || true
sleep 2

nohup /Users/aaron/.local/bin/llama-server \
    -m "${MODEL_DIR}/${MODEL_FILE}" \
    --alias hermes_70b \
    -np 2 \
    --cont-batching \
    -ngl 99 \
    -c 8192 \
    --rpc "$RPC_TARGETS" \
    --tensor-split 10,12,16 \
    --host 0.0.0.0 \
    --port 8084 \
    > "${LOG_DIR}/hermes_70b_sharded.log" 2>&1 &

echo "Hermes 70B launched on Port 8084 with L2/L3 RPC. (PID: $!)"
