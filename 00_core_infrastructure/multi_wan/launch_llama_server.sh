#!/bin/bash
# launch_llama_server.sh - Launches llama.cpp backend for the Lauburu AGI Mesh
# Guaranteed single-instance process lock

PORT=8081
PID_FILE="/tmp/llama_server_8081.pid"

# Check if llama-server is already listening on port 8081
if lsof -i :$PORT | grep -q "LISTEN"; then
    echo "llama-server is already running on port $PORT. No action needed."
    exit 0
fi

MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf"

if [ ! -f "$MODEL_PATH" ]; then
    MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
fi

# Dynamically detect online RPC nodes to prevent connection aborts
ACTIVE_RPC=""
for node in "100.103.212.21:50052" "100.101.39.98:50052" "100.93.158.96:50052" "100.73.38.87:50052"; do
    host="${node%:*}"
    port="${node#*:}"
    if nc -z -w 1 "$host" "$port" 2>/dev/null; then
        if [ -z "$ACTIVE_RPC" ]; then
            ACTIVE_RPC="$node"
        else
            ACTIVE_RPC="$ACTIVE_RPC,$node"
        fi
    fi
done

RPC_ARG=""
if [ -n "$ACTIVE_RPC" ]; then
    echo "Active RPC sharding target(s) detected: $ACTIVE_RPC"
    RPC_ARG="--rpc $ACTIVE_RPC"
fi

echo "Starting llama-server on port $PORT with model $MODEL_PATH (host 0.0.0.0)..."
nohup /Users/aaron/.local/bin/llama-server -m "$MODEL_PATH" -c 16384 --host 0.0.0.0 --port "$PORT" --ui-mcp-proxy $RPC_ARG > /tmp/llama_server_8081.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"
echo "llama-server started with PID $SERVER_PID"
