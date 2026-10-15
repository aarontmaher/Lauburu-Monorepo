#!/bin/bash
export PATH="/Users/aaron/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-Math-1.5B-Instruct-Q8_0.gguf"

if [ -f "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf" ]; then
    MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf"
fi

lsof -ti:8086 | xargs kill -9 2>/dev/null || true
exec /Users/aaron/.local/bin/llama-server \
  -m "$MODEL_PATH" \
  --alias qwen2.5-math \
  --host 0.0.0.0 \
  --port 8086 \
  -c 4096 \
  -np 2 \
  -ngl 99 \
  --threads 4
