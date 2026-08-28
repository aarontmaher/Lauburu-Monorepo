#!/usr/bin/env bash
# ==============================================================================
# launch_kimi_tandem_rpc.sh
# Lauburu Cluster Distributed 3-Mac All-Metal Thunderbolt Mesh
# ==============================================================================
set -euo pipefail

RPC_PORT=50052
MASTER_PORT=8081
MODEL_PATH="/Users/aaron/.local/share/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"

echo "=========================================================================="
echo "  LAUNCHING DISTRIBUTED 3-MAC ALL-METAL SHARDING (PORT 50052 / 8081)      "
echo "=========================================================================="

# 1. Start ggml-rpc-server on MacBook Air M2 (Shard 1)
echo "[1/3] Initializing ggml-rpc-server on MacBook Air M2..."
ssh -o BatchMode=yes -o ConnectTimeout=5 macbook-air \
  "killall ggml-rpc-server 2>/dev/null || true; nohup /Users/aaronmaher/llama.cpp/build/bin/ggml-rpc-server --host 0.0.0.0 --port ${RPC_PORT} > /tmp/ggml_rpc.log 2>&1 &" || true

# 2. Start ggml-rpc-server on MacBook Pro Vault (Shard 2)
echo "[2/3] Initializing ggml-rpc-server on MacBook Pro..."
ssh -o BatchMode=yes -o ConnectTimeout=5 macbook-pro \
  "killall ggml-rpc-server 2>/dev/null || true; nohup /Users/aaronmaher/llama.cpp/build/bin/ggml-rpc-server --host 0.0.0.0 --port ${RPC_PORT} > /tmp/ggml_rpc.log 2>&1 &" || true

# 3. Launch Master llama-server on Host Mac Mini M4
echo "[3/3] Launching Master Server on Port ${MASTER_PORT} (Sharding across Mac nodes)..."
killall llama-server 2>/dev/null || true

nohup /Users/aaron/.local/bin/llama-b10545/llama-server \
  -m "${MODEL_PATH}" \
  --port ${MASTER_PORT} \
  --host 0.0.0.0 \
  -c 8192 \
  -ngl 999 \
  --rpc "macbook-air:${RPC_PORT},macbook-pro:${RPC_PORT}" \
  > /tmp/llama_master.log 2>&1 &

echo "=========================================================================="
echo "  DISTRIBUTED INFERENCE ACTIVE ON PORT ${MASTER_PORT} (MCP READY)         "
echo "=========================================================================="
