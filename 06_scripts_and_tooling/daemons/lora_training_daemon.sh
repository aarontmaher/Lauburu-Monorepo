#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lauburu Mesh — 24/7 Background LoRA Training Daemon
# Trains Qwen MoE on priority loop-skill DPO pairs using Apple MLX
# ─────────────────────────────────────────────────────────────────────────────

PYTHON=/Users/aaron/.venv/bin/python
LORA_DATA=/Volumes/Lauburu-Monorepo/04_data_and_memory/data/
ADAPTER=/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/lora_adapters/qwen_moe_loop_governor
LOG=/Volumes/Lauburu-Monorepo/logs/lora_training.log
PRIORITY_BATCH=/Volumes/Lauburu-Monorepo/04_data_and_memory/data/priority_train_batch.jsonl

mkdir -p "$ADAPTER" "$(dirname $LOG)"

echo "$(date): 🚀 Starting Lauburu LoRA Training Daemon" | tee -a "$LOG"
echo "$(date): 📊 Priority batch: $(wc -l < $PRIORITY_BATCH) DPO pairs" | tee -a "$LOG"

# Try Qwen2-1.5B first (fastest, M4 Pro compatible), fallback to Qwen2-7B
for MODEL in \
  "mlx-community/Qwen2-1.5B-Instruct-4bit" \
  "mlx-community/Qwen2.5-1.5B-Instruct-4bit" \
  "mlx-community/Qwen2-7B-Instruct-4bit"; do
  
  echo "$(date): 🔄 Trying model: $MODEL" | tee -a "$LOG"
  
  $PYTHON -m mlx_lm.lora \
    --model "$MODEL" \
    --train \
    --data "$LORA_DATA" \
    --adapter-path "$ADAPTER" \
    --num-layers 4 \
    --iters 50 \
    --batch-size 1 \
    --learning-rate 1e-5 \
    --max-seq-length 512 \
    --save-every 25 \
    2>&1 | tee -a "$LOG"
  
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "$(date): ✅ Training complete for $MODEL!" | tee -a "$LOG"
    break
  else
    echo "$(date): ⚠️  Model $MODEL failed, trying next..." | tee -a "$LOG"
  fi
done

echo "$(date): 📝 Training session complete. Adapter saved to: $ADAPTER" | tee -a "$LOG"
