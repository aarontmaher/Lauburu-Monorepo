#!/bin/bash
export PATH="/Users/aaron/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
MODEL_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-3b-instruct-q4_k_m.gguf"
lsof -ti:8084 | xargs kill -9 2>/dev/null || true
exec /Users/aaron/.local/bin/llama-server \
  -m "$MODEL_PATH" \
  --alias qwen2.5-coder-3b \
  --host 0.0.0.0 \
  --port 8084 \
  -c 4096 \
  -np 2 \
  -ngl 99 \
  --threads 4
