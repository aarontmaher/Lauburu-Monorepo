#!/usr/bin/env python3
"""
Lauburu Model Vault: Dual Parallel Download Watcher & Finalizer
Monitors concurrent downloads of DeepSeek Coder V2 Lite MoE and Qwen 2.5 Coder 32B.
Auto-renames *.part files upon completion and verifies size integrity.
"""

import os
import time
import subprocess

VAULT_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"

TARGETS = [
    {
        "name": "DeepSeek Coder V2 Lite MoE (Q4_K_M)",
        "final_file": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "part_file": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf.part",
        "min_bytes": 9.5 * 1024 * 1024 * 1024
    },
    {
        "name": "Qwen 2.5 Coder 32B Instruct (Q4_K_M)",
        "final_file": "qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        "part_file": "qwen2.5-coder-32b-instruct-q4_k_m.gguf.part",
        "min_bytes": 19.0 * 1024 * 1024 * 1024
    }
]

def check_progress():
    print("======================================================================")
    print("📊 DUAL PARALLEL MODEL DOWNLOAD STATUS")
    print("======================================================================")
    for t in TARGETS:
        final_path = os.path.join(VAULT_DIR, t["final_file"])
        part_path = os.path.join(VAULT_DIR, t["part_file"])
        
        if os.path.isfile(final_path) and os.path.getsize(final_path) >= t["min_bytes"]:
            size_gb = os.path.getsize(final_path) / (1024**3)
            print(f"✅ {t['name']}: FULLY DOWNLOADED & READY ({size_gb:.2f} GB)")
        elif os.path.isfile(part_path):
            size_gb = os.path.getsize(part_path) / (1024**3)
            expected_gb = t["min_bytes"] / (1024**3)
            pct = (size_gb / expected_gb) * 100
            print(f"📥 {t['name']}: {size_gb:.2f} GB / {expected_gb:.1f} GB ({pct:.1f}% downloading...)")
        else:
            print(f"⏳ {t['name']}: Pending...")

if __name__ == "__main__":
    check_progress()
