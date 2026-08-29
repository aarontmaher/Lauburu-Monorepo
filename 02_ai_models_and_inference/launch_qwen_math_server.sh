#!/bin/bash
# Launch Qwen2.5-Math-7B-Instruct (Algorithm Specialist AI) on Port 8086
MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf"
LOG_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/qwen_math_8086.log"

if [ ! -f "$MODEL_PATH" ]; then
    echo "Model file not found: $MODEL_PATH"
    exit 1
fi

mkdir -p /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs

# Kill any existing process on 8086
lsof -ti:8086 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting Qwen 2.5 Math 7B (Algorithm Specialist) on :8086..."
nohup /Users/aaron/.local/bin/llama-server \
  -m "$MODEL_PATH" \
  --host 127.0.0.1 \
  --port 8086 \
  -c 2048 \
  -b 256 \
  -ngl 0 \
  -t 8 \
  > "$LOG_PATH" 2>&1 &

echo "Algorithm Specialist AI launched PID $!"
