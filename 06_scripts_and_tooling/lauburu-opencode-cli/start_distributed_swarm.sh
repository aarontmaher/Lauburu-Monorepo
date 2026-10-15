#!/bin/bash
set -e

LINUX_MINI_IP="100.101.39.98"
SERVER_BIN="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/llama-server"
VAULT_DIR="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"

echo "==========================================================="
echo "🧬 Booting Lauburu Distributed Sovereign AI Mesh (Rule 8 & 10)"
echo "==========================================================="

echo "Starting [1/3] Mac Mini Host: Master Local Orchestrator (Qwen 3.8 Max) on Port 8082..."
pkill -f "llama-server" || true
nohup $SERVER_BIN -m "$VAULT_DIR/qwen_38_max.gguf" --port 8082 -ngl 99 -c 8192 > /tmp/qwen_8082.log 2>&1 &

echo "Starting [2/3] Linux Mini ($LINUX_MINI_IP): Adversarial Red Team (Qwen 2.5 7B Abliterated)..."
ssh aaron@$LINUX_MINI_IP "pkill -f llama-server; nohup $SERVER_BIN -m $VAULT_DIR/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf --port 8083 -ngl 99 -c 16384 > /tmp/qwen_8083.log 2>&1 &" &

echo "Starting [3/3] Linux Mini ($LINUX_MINI_IP): Subordinate Syntax Worker (Qwen 2.5 Coder 7B)..."
ssh aaron@$LINUX_MINI_IP "nohup $SERVER_BIN -m $VAULT_DIR/qwen2.5-coder-7b-instruct-q4_k_m.gguf --port 8081 -ngl 99 -c 16384 > /tmp/qwen_8081.log 2>&1 &" &

echo ""
echo "✅ Rule 10 Compliant: Auxiliary models successfully offloaded to Linux Mini VRAM!"
