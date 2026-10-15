#!/usr/bin/env bash
set -e

echo "Starting 27B model downloads..."
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/download_all_27b_models.py

echo "Downloads complete. Starting benchmarks..."
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/run_27b_benchmarks.py

echo "Pipeline complete."
