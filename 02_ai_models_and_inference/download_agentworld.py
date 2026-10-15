#!/usr/bin/env python3
"""
High-Speed Model Procurement Script for Qwen-AgentWorld-35B-A3B (Q4_K_M)
========================================================================
Subsystem: 02_ai_models_and_inference/download_agentworld.py
Lauburu Mesh Ecosystem — 2026
"""

import os
import sys
import time
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO_ID = "unsloth/Qwen-AgentWorld-35B-A3B-GGUF"
FILENAME = "Qwen-AgentWorld-35B-A3B-UD-Q4_K_M.gguf"
TARGET_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf")

TARGET_DIR.mkdir(parents=True, exist_ok=True)
print(f"🚀 Starting download of {FILENAME} from {REPO_ID}...")
print(f"📁 Destination: {TARGET_DIR}")

start_time = time.time()
try:
    downloaded_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=str(TARGET_DIR),
        local_dir_use_symlinks=False,
        resume_download=True
    )
    elapsed = time.time() - start_time
    size_gb = Path(downloaded_path).stat().st_size / (1024**3)
    print(f"\n✅ Download complete! File: {downloaded_path}")
    print(f"📊 Size: {size_gb:.2f} GB in {elapsed:.1f}s ({size_gb / (elapsed/60):.2f} GB/min)")
except Exception as e:
    print(f"\n❌ Download failed: {e}", file=sys.stderr)
    sys.exit(1)
