#!/bin/bash
# ---------------------------------------------------------------------------
# MLX LoRA Fine-Tuning Trigger
# ---------------------------------------------------------------------------
# Triggered by the Genetic Orchestrator when a specialist dataset reaches maturity.

DATASET="/Users/aaron/DFS_UNIFIED/lora_datasets/specialist_candidates.jsonl"
OUTPUT_ADAPTER="/Users/aaron/DFS_UNIFIED/lora_datasets/latest_specialist_lora.safetensors"
BASE_MODEL="qwen2.5-coder-7b-instruct-q4_k_m.gguf"

echo "🧠 Checking dataset maturity at $DATASET..."

if [ ! -f "$DATASET" ]; then
    echo "❌ Dataset not found."
    exit 1
fi

LINE_COUNT=$(wc -l < "$DATASET" | tr -d ' ')
THRESHOLD=100

if [ "$OVERRIDE_TRAIN_THRESHOLD" == "1" ]; then
    THRESHOLD=10
    echo "⚠️ Threshold manually overridden to $THRESHOLD for priority testing."
fi

if [ "$LINE_COUNT" -lt "$THRESHOLD" ]; then
    echo "⚠️ Dataset only has $LINE_COUNT examples. $THRESHOLD required for training. Skipping."
    exit 0
fi

echo "🚀 Dataset mature ($LINE_COUNT examples). Triggering Apple Silicon MLX LoRA fine-tuning..."

# Authentic Execution per Rule 0 (Zero-Mock Invariant) and Rule 3 (RAM Sanctuary)
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/local_ai_training_engine.py specialist-headless-finder "$DATASET" 10
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Authentic MLX training complete. Adapter saved to $OUTPUT_ADAPTER"
    echo "🔧 To execute: llama-server -m $BASE_MODEL --lora $OUTPUT_ADAPTER"
else
    echo "❌ Local AI training halted with exit code $EXIT_CODE."
    exit $EXIT_CODE
fi
