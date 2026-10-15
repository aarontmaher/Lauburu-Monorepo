#!/usr/bin/env python3
"""
Lauburu Mesh — Synchronous QLoRA Training Pipeline
Trains Qwen MoE local model on high-priority Loop Skill DPO pairs.
Targets: Free-tier model governance, Gemini Pro block, and cost-aware routing.
"""
import json
import os
import sys
import subprocess
import time
from pathlib import Path

LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
TRAIN_OUTPUT = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/priority_train_batch.jsonl")
MLX_ADAPTER_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/lora_adapters/qwen_moe_loop_governor")

# ─── STEP 1: Extract High-Priority Loop Skill DPO Pairs ───────────────────────
PRIORITY_KEYWORDS = [
    "free-tier", "free tier", "gemini-3.1-pro", "paid model", "quota",
    "cost governor", "429", "resource_exhausted", "model cost", "flash only",
    "loop skill", "generational handoff", "qwen watchdog", "asynchronous persistence",
    "hardware isolation", "headless", "lauburu lens", "dpo distillation"
]

all_entries = []
priority_entries = []

with open(LORA_DATASET, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            all_entries.append(entry)
            text = (entry.get('instruction','') + entry.get('output','')).lower()
            if any(kw.lower() in text for kw in PRIORITY_KEYWORDS):
                priority_entries.append(entry)
        except:
            continue

print(f"📊 Total LoRA dataset entries: {len(all_entries)}")
print(f"🎯 Priority loop-skill entries: {len(priority_entries)}")

# ─── STEP 2: Write Priority Training Batch ────────────────────────────────────
# Convert to MLX-LM chat format
train_data = []
for e in priority_entries:
    train_data.append({
        "messages": [
            {"role": "system", "content": e.get("system", "Lauburu AI Mesh Governor")},
            {"role": "user", "content": e.get("instruction", "") + "\n" + e.get("input", "")},
            {"role": "assistant", "content": e.get("output", "")}
        ]
    })

TRAIN_OUTPUT.write_text('\n'.join(json.dumps(d) for d in train_data))
print(f"✅ Priority training batch written: {TRAIN_OUTPUT} ({len(train_data)} pairs)")

# ─── STEP 3: Attempt MLX Training (with graceful fallback) ────────────────────
MLX_ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

# Try finding mlx_lm
mlx_candidates = [
    "mlx_lm.lora",
    "/Users/aaron/.venv/bin/mlx_lm.lora",
    "/opt/homebrew/bin/mlx_lm.lora",
]

mlx_cmd = None
for candidate in mlx_candidates:
    result = subprocess.run(["which", candidate.split()[0]], capture_output=True, text=True)
    if result.returncode == 0:
        mlx_cmd = candidate
        break

if mlx_cmd is None:
    # Try python -m mlx_lm.lora
    result = subprocess.run([sys.executable, "-c", "import mlx_lm; print('ok')"],
                          capture_output=True, text=True)
    if result.returncode == 0:
        mlx_cmd = f"{sys.executable} -m mlx_lm.lora"

if mlx_cmd:
    print(f"✅ MLX-LM found: {mlx_cmd}")
    print("🚀 Launching synchronous QLoRA training step (~5 seconds)...")
    # Run a minimal LoRA fine-tune step
    train_cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", "mlx-community/Qwen2-7B-Instruct-4bit",  # use available quantized
        "--train",
        "--data", str(TRAIN_OUTPUT.parent),
        "--adapter-path", str(MLX_ADAPTER_DIR),
        "--num-layers", "4",
        "--iters", "10",
        "--batch-size", "1",
        "--learning-rate", "1e-5",
    ]
    result = subprocess.run(train_cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        print("✅ QLoRA training step COMPLETE!")
        print(result.stdout[-500:])
    else:
        print(f"⚠️  MLX training stderr: {result.stderr[-300:]}")
else:
    print("⚠️  MLX-LM not installed. Writing install instructions...")
    install_note = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/INSTALL_MLX_LM.md")
    install_note.write_text("""# Install MLX-LM for Apple Silicon LoRA Training

```bash
uv tool install mlx-lm
# or
pip install mlx-lm
```

Then run:
```bash
mlx_lm.lora --model mlx-community/Qwen2-7B-Instruct-4bit --train \\
  --data /Users/aaron/DFS_UNIFIED/lora_datasets/ \\
  --adapter-path /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/lora_adapters/qwen_moe_loop_governor \\
  --num-layers 4 --iters 50 --batch-size 1 --learning-rate 1e-5
```
""")
    print(f"✅ Install instructions written to {install_note}")

# ─── STEP 4: Write LoRA Training Audit Entry ──────────────────────────────────
audit_entry = {
    "instruction": "Record LoRA training run for Qwen MoE prioritizing Loop Skill cost governance DPO pairs.",
    "input": f"Dataset: {len(all_entries)} total entries. Priority batch: {len(priority_entries)} loop-skill entries extracted.",
    "output": f"Extracted {len(priority_entries)} high-priority DPO pairs covering free-tier governance, Gemini Pro block, hardware isolation, Lauburu Lens, and generational handoffs. Written to {TRAIN_OUTPUT}. MLX adapter target: {MLX_ADAPTER_DIR}.",
    "system": "Lauburu LoRA Training Pipeline"
}
with open(LORA_DATASET, 'a') as f:
    f.write(json.dumps(audit_entry) + '\n')

print(f"\n📈 TRAINING SUMMARY")
print(f"   Dataset size:      {len(all_entries)} entries")
print(f"   Priority batch:    {len(priority_entries)} loop-skill pairs")
print(f"   Adapter target:    {MLX_ADAPTER_DIR}")
print(f"   LoRA audit logged: ✅")
