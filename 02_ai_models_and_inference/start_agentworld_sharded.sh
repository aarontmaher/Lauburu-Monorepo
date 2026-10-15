#!/bin/bash
# ==============================================================================
# Qwen-AgentWorld-35B-A3B Resilient Launcher (Single-Node & Mesh Sharded Modes)
# ==============================================================================

MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen-AgentWorld-35B-A3B-UD-Q4_K_M.gguf"
PORT=8086

echo "======================================================================"
echo "🤖 LAUNCHING QWEN-AGENTWORLD-35B-A3B (Language World Model Simulator)"
echo "======================================================================"

if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Error: Model file not found at $MODEL_PATH"
    exit 1
fi

# Mode 1: Single Node Adaptive Metal Offload (fits within Mac Mini 24GB Headroom)
echo "⚡ Mode: Adaptive Metal Offload (-ngl 32, --ctx-size 4096, 8 threads)"
echo "📡 Endpoint: http://127.0.0.1:$PORT/v1/chat/completions"
echo "======================================================================"

llama-server \
  --model "$MODEL_PATH" \
  --port "$PORT" \
  --ctx-size 4096 \
  --n-gpu-layers 32 \
  --threads 8 \
  --host 0.0.0.0
