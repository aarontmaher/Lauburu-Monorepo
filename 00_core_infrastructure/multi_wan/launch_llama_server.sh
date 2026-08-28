#!/bin/bash
# launch_llama_server.sh - Launches llama.cpp backend for the Lauburu AGI Mesh

PORT=8081
MODEL_PATH="/Users/aaron/DFS_UNIFIED/02_ai_models_and_inference/models_vault/gpt-oss-20b-GGUF/gpt-oss-20b-MXFP4.gguf"
RPC_NODES="100.103.212.21:50052,100.93.158.96:50052,100.101.39.98:50052,100.73.38.87:50052"

echo "Starting llama-server on port $PORT with model $MODEL_PATH..."
/Users/aaron/.local/bin/llama-server -m "$MODEL_PATH" -c 4096 --host 0.0.0.0 --port "$PORT" --ui-mcp-proxy --rpc "$RPC_NODES" &
echo $! > /tmp/llama_server.pid
echo "llama-server started with PID $(cat /tmp/llama_server.pid)"
