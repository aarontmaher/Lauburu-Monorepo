#!/usr/bin/env bash
# ==============================================================================
# Screen Lens Continuous Canonical Workflow & Auto-Trainer Daemon
# Subsystem: 01_apps/screen_lens/launch_lens_workflow_daemon.sh
# Lauburu Mesh Ecosystem — 2026
#
# 1. Harvests screen/OCR observations every 15s into Obsidian & JSONL.
# 2. Automatically triggers MLX Metal QLoRA training when new pairs >= 50.
# ==============================================================================

set -euo pipefail

LOG_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/screen_lens_workflow_daemon.log"

echo "========================================================================"
echo "👁️ Launching Screen Lens Canonical Workflow & Auto-Trainer Daemon..."
echo "Log Target: ${LOG_FILE}"
echo "========================================================================"

nohup python3 -u -c '
import time, os, sys, subprocess, json
from pathlib import Path
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens")
from src.canonical_workflow_engine import ScreenLensCanonicalWorkflowEngine

engine = ScreenLensCanonicalWorkflowEngine()
print("👁️ Screen Lens Workflow Daemon Active. Polling every 15s...", flush=True)

last_trained_count = 0
dataset_path = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/screen_lens_perception_workflow.jsonl")
trainer_script = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mlx_lens_qlora_trainer.py"

while True:
    try:
        events = engine.harvest_active_observations(max_records=15)
        verdict = engine.process_and_update_canonical_workflow(events)
        
        # Count total dataset lines
        if dataset_path.exists():
            with open(dataset_path, "r", encoding="utf-8") as f:
                current_count = sum(1 for line in f if line.strip())
            
            # Auto-trigger MLX training if 50+ new pairs accumulated
            if current_count - last_trained_count >= 50:
                ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                print(f"[{ts}] 🚀 Auto-triggering MLX Metal QLoRA ({current_count} pairs, delta: +{current_count - last_trained_count})...", flush=True)
                try:
                    res = subprocess.run(
                        [sys.executable, trainer_script, str(dataset_path)],
                        capture_output=True,
                        text=True,
                        timeout=60.0,
                        check=True
                    )
                    last_trained_count = current_count
                    ts_done = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    print(f"[{ts_done}] ✨ Auto-training complete (Exit 0)! Weights updated.", flush=True)
                    if res.stderr:
                        for line in res.stderr.strip().splitlines():
                            if "Step [" in line or "Training Complete" in line or "Saved ->" in line:
                                print(f"   [MLX] {line}", flush=True)
                    if res.stdout:
                        try:
                            manifest = json.loads(res.stdout)
                            loss_i = manifest.get("initial_loss")
                            loss_f = manifest.get("final_loss")
                            lat = manifest.get("avg_step_latency_ms")
                            tps = manifest.get("avg_tokens_per_sec")
                            art = manifest.get("adapter_artifact")
                            print(f"   [MLX Manifest] Loss: {loss_i} -> {loss_f} | Latency: {lat}ms | Throughput: {tps} tok/s | Artifact: {art}", flush=True)
                        except Exception:
                            pass
                except subprocess.CalledProcessError as cpe:
                    ts_err = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    print(f"[{ts_err}] ❌ MLX Auto-training failed with exit code {cpe.returncode}:", flush=True)
                    if cpe.stderr:
                        print(f"   STDERR: {cpe.stderr.strip()}", flush=True)
                    if cpe.stdout:
                        print(f"   STDOUT: {cpe.stdout.strip()}", flush=True)
        
    except Exception as e:
        print(f"Workflow engine tick error: {e}", flush=True)
    time.sleep(15.0)
' > "${LOG_FILE}" 2>&1 &

echo "✅ Screen Lens Auto-Trainer Daemon active (PID: $!)."
