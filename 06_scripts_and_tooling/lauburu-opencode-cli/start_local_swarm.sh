#!/bin/bash
set -e

SERVER_BIN="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/llama-server"
VAULT_DIR="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"

echo "==========================================================="
echo "🧬 Booting Lauburu Canonical Sovereign AI Mesh (Rule 8)"
echo "==========================================================="

# Kill existing servers to free up ports
pkill -f "llama-server" || true

# 1. Master Local Orchestrator (Port 8082)
echo "Starting [1/3]: Master Local Orchestrator (Qwen 3.8 Max) on Port 8082..."
nohup $SERVER_BIN -m "$VAULT_DIR/qwen_38_max.gguf" --port 8082 -ngl 99 -c 8192 > /tmp/qwen_8082.log 2>&1 &

# 2. Adversarial Red Team (Port 8083)
echo "Starting [2/3]: Adversarial Red Team (Qwen 2.5 7B Abliterated) on Port 8083..."
nohup $SERVER_BIN -m "$VAULT_DIR/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf" --port 8083 -ngl 99 -c 4096 > /tmp/qwen_8083.log 2>&1 &

# 3. Subordinate Syntax Worker (Port 8081)
echo "Starting [3/3]: Subordinate Syntax Worker (Qwen 2.5 Coder 7B) on Port 8081..."
nohup $SERVER_BIN -m "$VAULT_DIR/qwen2.5-coder-7b-instruct-q4_k_m.gguf" --port 8081 -ngl 99 -c 4096 > /tmp/qwen_8081.log 2>&1 &

echo ""
echo "✅ Canonical Rule 8 Sovereign Models dispatched to Metal GPU!"
echo "Run ./mesh_health_check.sh to verify."
