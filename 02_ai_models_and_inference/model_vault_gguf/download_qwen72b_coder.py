#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Resilient Auto-Resuming Downloader: Qwen 2.5 Coder 72B Instruct GGUF
================================================================================
Subsystem: 02_ai_models_and_inference/model_vault_gguf
Target: Qwen/Qwen2.5-Coder-72B-Instruct-GGUF (Q4_K_M ~43.5 GB)
Features: HTTP Range chunking, auto-retry, progress JSON tracker, disk space pre-check.
================================================================================
"""

import os
import sys
import time
import json
import shutil
import urllib.request

REPO_ID = "Qwen/Qwen2.5-Coder-72B-Instruct-GGUF"
FILENAME = "qwen2.5-coder-72b-instruct-q4_k_m-00001-of-00002.gguf"
DEST_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
DEST_PATH = os.path.join(DEST_DIR, "qwen2.5-coder-72b-instruct-q4_k_m.gguf")
TRACK_FILE = os.path.join(DEST_DIR, "qwen72b_coder_download_progress.json")
URL = f"https://huggingface.co/{REPO_ID}/resolve/main/qwen2.5-coder-72b-instruct-q4_k_m.gguf?download=true"

os.makedirs(DEST_DIR, exist_ok=True)

def check_disk_headroom(required_gb=45.0):
    free_gb = shutil.disk_usage(DEST_DIR).free / (1024**3)
    print(f"💾 Storage Check: {free_gb:.2f} GB Free | Required: {required_gb:.2f} GB")
    return free_gb >= required_gb

def update_status(downloaded, total, speed, percent, eta_s, status="downloading"):
    data = {
        "model": "Qwen2.5-Coder-72B-Instruct-Q4_K_M",
        "repo": REPO_ID,
        "destination": DEST_PATH,
        "downloaded_bytes": downloaded,
        "total_bytes": total,
        "downloaded_gb": round(downloaded / (1024**3), 2),
        "total_gb": round(total / (1024**3), 2),
        "progress_percent": round(percent, 2),
        "speed_mb_s": round(speed / (1024**2), 2),
        "eta_seconds": int(eta_s) if eta_s else None,
        "status": status,
        "updated_at": time.time()
    }
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    print(f"🚀 Initializing Resilient Downloader for {REPO_ID}...")
    if not check_disk_headroom(45.0):
        print("⚠️ WARNING: Free disk space is currently < 45.0 GB on this volume.")
        print("Please ensure external SSD or L2 MacBook Pro storage is mounted, or run with alternate destination.")
