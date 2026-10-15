#!/bin/bash
# Autonomous daemon to fetch the missing champion models for the ELO Benchmarking Harness

echo "Fetching Qwen 3.8 Max 27B Abliterated (16.6GB)..."
hf download huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF --include "*Q4_K_M.gguf" --local-dir /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf

echo "Fetching DeepSeek Coder V2 Lite (10.4GB)..."
hf download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF --include "*Q4_K_M.gguf" --local-dir /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf

echo "Downloads complete."
