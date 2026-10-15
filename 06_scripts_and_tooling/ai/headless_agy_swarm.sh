#!/bin/bash
TASK="Conduct a line-by-line audit of the continuous_lens_sovereign_auditor_trainer.py script. Focus on Zero-Mock invariants, UI/UX audit cadence, and RAM governance."

MODELS=(
    "gemini-3.8-flash-high"
    "gemini-3.1-pro-high"
    "claude-sonnet-4-6"
    "claude-opus-4-6-thinking"
    "gpt-oss-120b-medium"
)

echo "====================================================="
echo "🌐 LAUNCHING HEADLESS AGY SWARM ACROSS ALL MODELS"
echo "====================================================="
echo "Task: $TASK"
echo ""

mkdir -p /tmp/agy_swarm_outputs

# Launch all models in the background
for model in "${MODELS[@]}"; do
    echo "[*] Dispatching to $model..."
    agy --model "$model" --print "$TASK" > "/tmp/agy_swarm_outputs/${model}.txt" 2>&1 &
done

echo "[*] Waiting for all models to complete their audits..."
wait

echo "====================================================="
echo "✅ HEADLESS AGY SWARM COMPLETE. SYNTHESIZING RESULTS."
echo "====================================================="

for model in "${MODELS[@]}"; do
    echo "--- Model: $model ---"
    cat "/tmp/agy_swarm_outputs/${model}.txt" | head -n 20
    echo "... (truncated) ..."
    echo ""
done
