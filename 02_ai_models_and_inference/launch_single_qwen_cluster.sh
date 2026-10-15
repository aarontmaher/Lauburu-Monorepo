#!/bin/bash
set -eo pipefail

LOG_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs"
MODEL_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
# The ONE true Qwen model that survived the benchmark
MODEL_FILE="Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf"

# Single sharding method: llama.cpp RPC
RPC_TARGETS="169.254.175.124:50052,100.101.39.98:50052" 

# Kill any existing llama-server instances
pkill -f "llama-server" || true
sleep 2

nohup /Users/aaron/.local/bin/llama-server \
    -m "${MODEL_DIR}/${MODEL_FILE}" \
    --alias sovereign_qwen \
    -np 2 \
    --cont-batching \
    -ngl 99 \
    -c 16384 \
    --rpc "$RPC_TARGETS" \
    --host 0.0.0.0 \
    --port 8090 \
    > "${LOG_DIR}/sovereign_qwen_sharded.log" 2>&1 &

echo "Sovereign Qwen 7B launched on Port 8090 (Proxy forwards from 8082) via llama.cpp RPC. (PID: $!)"
