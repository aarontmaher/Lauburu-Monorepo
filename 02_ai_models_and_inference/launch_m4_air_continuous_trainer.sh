#!/usr/bin/env bash
# ==============================================================================
# Dedicated 24/7 Continuous Training Engine for M4 MacBook Air / Apple Silicon
# Subsystem: 02_ai_models_and_inference/launch_m4_air_continuous_trainer.sh
# Lauburu Mesh Ecosystem — 2026
#
# Framework: Native Apple MLX on Metal GPU Device(gpu, 0)
# ==============================================================================

set -euo pipefail

MODEL_ID="${1:-mlx-community/Qwen2.5-3B-Instruct-4bit}"
DATASET_PATH="${2:-/Users/aaron/DFS_UNIFIED/lora_datasets/screen_lens_perception_workflow.jsonl}"
ADAPTER_DIR="${3:-/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/qwen_screen_lens_adapter}"

echo "========================================================================"
echo "🚀 Launching Native Apple MLX Continuous QLoRA Training Engine..."
echo "Model Target:    ${MODEL_ID}"
echo "Dataset Inode:   ${DATASET_PATH}"
echo "Adapter Output:  ${ADAPTER_DIR}"
echo "========================================================================"

mkdir -p "${ADAPTER_DIR}"

uv run python /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mlx_lens_qlora_trainer.py \
    "${DATASET_PATH}" \
    "${ADAPTER_DIR}"

echo "✨ Native MLX Continuous Training Step Completed Successfully."
