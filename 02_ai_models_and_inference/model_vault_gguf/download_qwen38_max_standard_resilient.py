#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resilient Downloader for Qwen 3.8 Max (Standard / Master Orchestrator GGUF)
===========================================================================
Subsystem: 02_ai_models_and_inference/model_vault_gguf/
Model: unsloth/Qwen3.8-27B-GGUF (Qwen3.8-27B-UD-Q4_K_XL.gguf)
Size: 16.35 GB (17,559,178,144 bytes)
Features: HTTP Range Auto-Resume, Real-Time Progress JSON, Symlink Creation
"""

import json
import os
import sys
import time
import urllib.request

REPO_ID = "unsloth/Qwen3.8-27B-GGUF"
FILENAME = "Qwen3.8-27B-UD-Q4_K_XL.gguf"
SYMLINK_NAME = "qwen_38_max.gguf"
DEST_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
DEST_PATH = os.path.join(DEST_DIR, FILENAME)
SYMLINK_PATH = os.path.join(DEST_DIR, SYMLINK_NAME)
TRACK_FILE = os.path.join(DEST_DIR, "qwen3.8_max_download_progress.json")
URL = f"https://huggingface.co/{REPO_ID}/resolve/main/{FILENAME}?download=true"

os.makedirs(DEST_DIR, exist_ok=True)
TOTAL_SIZE = 17559178144 # 16.35 GB

def update_status(downloaded, total, speed, percent, eta_s, status="downloading"):
    data = {
        "model": FILENAME,
        "repo": REPO_ID,
        "destination": DEST_PATH,
        "symlink": SYMLINK_PATH,
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

print(f"=== Qwen 3.8 Max GGUF Downloader ===")
print(f"Repo:        {REPO_ID}")
print(f"File:        {FILENAME}")
print(f"Target:      {DEST_PATH}")
print(f"Total Size:  {TOTAL_SIZE / (1024**3):.2f} GB")

while True:
    existing_size = os.path.getsize(DEST_PATH) if os.path.exists(DEST_PATH) else 0
    if existing_size >= TOTAL_SIZE and TOTAL_SIZE > 0:
        update_status(existing_size, TOTAL_SIZE, 0, 100.0, 0, "completed")
        print(f"\n✔ SUCCESS: {FILENAME} fully downloaded ({existing_size / (1024**3):.2f} GB).")
        # Ensure symlink
        if os.path.islink(SYMLINK_PATH) or os.path.exists(SYMLINK_PATH):
            os.remove(SYMLINK_PATH)
        os.symlink(DEST_PATH, SYMLINK_PATH)
        print(f"✔ Symlinked {SYMLINK_NAME} -> {FILENAME}")
        sys.exit(0)

    headers = {"User-Agent": "Mozilla/5.0 (Lauburu-Mesh-Downloader/1.0)"}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        print(f"Resuming from {existing_size / (1024**3):.2f} GB / {TOTAL_SIZE / (1024**3):.2f} GB...")

    req = urllib.request.Request(URL, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            content_range = resp.headers.get("Content-Range")
            content_length = resp.headers.get("Content-Length")

            if content_range:
                TOTAL_SIZE = int(content_range.split("/")[-1])
            elif content_length and existing_size == 0:
                TOTAL_SIZE = int(content_length)

            mode = "ab" if existing_size > 0 else "wb"
            downloaded = existing_size
            start_time = time.time()
            last_print = start_time
            bytes_since_last = 0

            with open(DEST_PATH, mode) as out_f:
                while True:
                    chunk = resp.read(1024 * 1024 * 4) # 4MB chunk buffer
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    bytes_since_last += len(chunk)

                    now = time.time()
                    if now - last_print >= 2.0:
                        dt = now - last_print
                        speed = bytes_since_last / dt if dt > 0 else 0
                        percent = (downloaded / TOTAL_SIZE) * 100 if TOTAL_SIZE else 0
                        eta_s = (TOTAL_SIZE - downloaded) / speed if speed > 0 else 0
                        update_status(downloaded, TOTAL_SIZE, speed, percent, eta_s, "downloading")
                        print(f"[{percent:5.1f}%] {downloaded/(1024**3):.2f}/{TOTAL_SIZE/(1024**3):.2f} GB | Speed: {speed/(1024**2):.1f} MB/s | ETA: {eta_s:.0f}s", flush=True)
                        last_print = now
                        bytes_since_last = 0

            if downloaded >= TOTAL_SIZE:
                update_status(downloaded, TOTAL_SIZE, 0, 100.0, 0, "completed")
                print(f"\n✔ SUCCESS: {FILENAME} downloaded ({downloaded/(1024**3):.2f} GB).", flush=True)
                if os.path.islink(SYMLINK_PATH) or os.path.exists(SYMLINK_PATH):
                    os.remove(SYMLINK_PATH)
                os.symlink(DEST_PATH, SYMLINK_PATH)
                print(f"✔ Symlinked {SYMLINK_NAME} -> {FILENAME}")
                break

    except Exception as e:
        print(f"Transient network disruption ({e}), retrying in 3s...", flush=True)
        update_status(existing_size, TOTAL_SIZE, 0, (existing_size/TOTAL_SIZE)*100, 0, f"retrying: {e}")
        time.sleep(3)
