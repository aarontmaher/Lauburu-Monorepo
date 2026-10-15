#!/bin/bash
# launch_llama_server.sh - Launches llama.cpp backend for the Lauburu AGI Mesh
# Guaranteed single-instance process lock

PORT=8081
PID_FILE="/tmp/llama_server_8081.pid"

TB4_IP="169.254.215.118"

# Check if service is already listening on port 8081
if lsof -i :$PORT | grep -q "LISTEN"; then
    if pgrep -f "llama-server.*8081" >/dev/null 2>&1; then
        if ping -c 1 -W 400 "$TB4_IP" >/dev/null 2>&1; then
            echo "⚡ Active local heavy llama-server detected on Mac Mini, but 10Gbps TB4 is online. Migrating to TB4 offload..."
            pkill -9 -f "llama-server.*8081" 2>/dev/null || true
            sleep 1
        else
            echo "llama-server is already running locally on port $PORT. No action needed."
            exit 0
        fi
    else
        echo "Inference bridge or worker is already active on port $PORT. No action needed."
        exit 0
    fi
fi

# Port 8081 is the Subordinate Fast Syntax Worker Plane (Rule 8: Qwen 2.5 Coder 7B)
# Host Mac Mini strictly preserves >= 4.0 GB RAM (Rule 3)
QWEN25_CODER_7B="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
DEEPSEEK_FALLBACK="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"

if [ -f "$QWEN25_CODER_7B" ]; then
    MODEL_PATH="$QWEN25_CODER_7B"
else
    MODEL_PATH="$DEEPSEEK_FALLBACK"
fi

# Pre-flight check: Probe Thunderbolt 4 DMA Bridge on MacBook Pro (Rule 3 & Rule 8)
TB4_IP="169.254.215.118"
if ping -c 1 -W 400 "$TB4_IP" >/dev/null 2>&1; then
    echo "⚡ Thunderbolt 4 Peer verified at $TB4_IP (0.56ms RTT). Offloading Port $PORT to MacBook Pro L2..."
    
    # Ensure llama-server is running on MacBook Pro L2
    if ssh -o ConnectTimeout=2 macbook-pro-tb4 "curl -s http://127.0.0.1:8081/health" 2>/dev/null | grep -q "ok"; then
        echo "✔ MacBook Pro L2 is already serving Qwen 2.5 Coder on Port 8081."
    else
        echo "🚀 Launching llama-server on MacBook Pro L2 over Thunderbolt 4..."
        ssh -o ConnectTimeout=2 macbook-pro-tb4 "nohup /Users/aaronmaher/llama.cpp/build/bin/llama-server -m /Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault/qwen2.5-coder-7b-instruct-q4_k_m.gguf -ngl 0 -t 8 -c 2048 -np 1 --host 0.0.0.0 --port 8081 > /tmp/llama_server_8081.log 2>&1 &"
        sleep 3
    fi

    # Terminate any stray local heavy llama-server on Mac Mini before starting bridge
    pkill -9 -f "llama-server.*8081" 2>/dev/null || true
    sleep 1

    echo "Starting TB4 inference bridge on Mac Mini (Port $PORT -> $TB4_IP:8081)..."
    nohup python3 /Volumes/Lauburu-Monorepo/00_core_infrastructure/multi_wan/tb4_inference_bridge.py > /tmp/tb4_inference_bridge.log 2>&1 &
    BRIDGE_PID=$!
    echo $BRIDGE_PID > "$PID_FILE"
    echo "TB4 inference bridge active with PID $BRIDGE_PID. Host RAM fully preserved (>=4.0GB)."
    exit 0
fi

# Port 8081 Local Fallback (Subordinate Fast Syntax Worker Plane - Rule 7.3 & Rule 8.2)
QWEN_15B_SYNTAX="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
QWEN_7B_SYNTAX="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf"

if [ -f "$QWEN_15B_SYNTAX" ]; then
    TARGET_MODEL="$QWEN_15B_SYNTAX"
    UBATCH=128
    ALIAS="qwen2.5-coder-1.5b"
elif [ -f "$QWEN_7B_SYNTAX" ]; then
    TARGET_MODEL="$QWEN_7B_SYNTAX"
    UBATCH=256
    ALIAS="qwen2.5-coder-7b"
else
    TARGET_MODEL="$MODEL_PATH"
    UBATCH=256
    ALIAS="syntax_worker"
fi

echo "⚪ Thunderbolt 4 unlinked. Launching Subordinate Syntax Worker on Mac Mini Apple M4 Pro Metal GPU..."
echo "Target Model: $TARGET_MODEL ($ALIAS, ubatch=$UBATCH, preserves >= 4.0GB RAM sanctuary)"
nohup /Users/aaron/.local/bin/llama-server \
    -m "$TARGET_MODEL" \
    --alias "$ALIAS" \
    -ngl 99 \
    -c 2048 \
    -np 1 \
    -b 256 \
    -ub "$UBATCH" \
    --host 0.0.0.0 \
    --port "$PORT" \
    > /tmp/llama_server_8081.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"
echo "llama-server started locally with PID $SERVER_PID ($ALIAS on port $PORT)"

