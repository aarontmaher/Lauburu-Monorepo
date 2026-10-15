#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Resilient Auto-Resuming Downloader: Qwen3-Next-80B-A3B MoE GGUF
================================================================================
Subsystem: 02_ai_models_and_inference/model_vault_gguf
Target: Qwen3-Next-80B-A3B-Instruct (Q4_K_M ~45.38 GiB / 48.73 GB)
Repo: bartowski/Qwen_Qwen3-Next-80B-A3B-Instruct-GGUF
================================================================================
"""

import os
import sys
import time
import json
import shutil
import urllib.request
import argparse
from pathlib import Path

DEFAULT_REPO = "bartowski/Qwen_Qwen3-Next-80B-A3B-Instruct-GGUF"
DEFAULT_FILENAME = "Qwen_Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
EXPECTED_BYTES = 48727677408  # 45.38 GiB / 48.73 GB

def log_msg(msg: str, log_file: Path = None):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [Qwen80BDownloader] {msg}"
    print(formatted, flush=True)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass

def save_progress(track_file: Path, data: dict):
    try:
        with open(track_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def download(dest_dir: str, repo_id: str = DEFAULT_REPO, filename: str = DEFAULT_FILENAME):
    dest_dir_path = Path(dest_dir).expanduser().resolve()
    dest_dir_path.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir_path / filename
    track_file = dest_dir_path / "qwen_next80b_download_progress.json"
    log_file = dest_dir_path / "download_qwen_next80b.log"

    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}?download=true"

    log_msg("================================================================================", log_file)
    log_msg(f"Target Model:  {filename}", log_file)
    log_msg(f"Repo ID:       {repo_id}", log_file)
    log_msg(f"Destination:   {dest_path}", log_file)
    log_msg(f"Expected Size: {EXPECTED_BYTES / (1024**3):.2f} GiB ({EXPECTED_BYTES:,} bytes)", log_file)
    log_msg("================================================================================", log_file)

    # Storage Headroom Check
    free_bytes = shutil.disk_usage(str(dest_dir_path)).free
    free_gb = free_bytes / (1024**3)
    existing_bytes = dest_path.stat().st_size if dest_path.exists() else 0
    remaining_bytes = max(0, EXPECTED_BYTES - existing_bytes)
    required_gb = remaining_bytes / (1024**3)

    log_msg(f"Storage Check: {free_gb:.2f} GB Free | Remaining Needed: {required_gb:.2f} GB", log_file)
    if free_gb < required_gb + 2.0:
        log_msg(f"ERROR: Insufficient disk space ({free_gb:.2f} GB free vs {required_gb + 2.0:.2f} GB required threshold)!", log_file)
        sys.exit(1)

    while True:
        existing_bytes = dest_path.stat().st_size if dest_path.exists() else 0
        if existing_bytes >= EXPECTED_BYTES:
            log_msg(f"✅ Verified: {filename} already fully downloaded ({existing_bytes / (1024**3):.2f} GiB).", log_file)
            save_progress(track_file, {
                "filename": filename,
                "downloaded_bytes": existing_bytes,
                "total_bytes": EXPECTED_BYTES,
                "progress_pct": 100.0,
                "speed_mb_s": 0.0,
                "eta_seconds": 0,
                "status": "COMPLETED",
                "completed_at": time.time()
            })
            return True

        headers = {"User-Agent": "Mozilla/5.0 (Lauburu-Mesh-Downloader/1.0)"}
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-"
            log_msg(f"Resuming download from byte {existing_bytes:,} ({existing_bytes / (1024**3):.2f} GiB)...", log_file)

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                content_range = resp.headers.get("Content-Range")
                content_length = resp.headers.get("Content-Length")

                total_size = EXPECTED_BYTES
                if content_range:
                    total_size = int(content_range.split("/")[-1])
                elif content_length and existing_bytes == 0:
                    total_size = int(content_length)

                mode = "ab" if existing_bytes > 0 else "wb"
                downloaded = existing_bytes
                start_time = time.time()
                last_update = start_time
                bytes_window = 0

                with open(dest_path, mode) as out_f:
                    while True:
                        chunk = resp.read(1024 * 1024 * 4)  # 4MB chunks
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        bytes_window += len(chunk)

                        now = time.time()
                        if now - last_update >= 2.0:
                            dt = now - last_update
                            speed = bytes_window / dt if dt > 0 else 0
                            pct = (downloaded / total_size) * 100 if total_size else 0
                            eta_s = (total_size - downloaded) / speed if speed > 0 else 0

                            status_dict = {
                                "filename": filename,
                                "downloaded_bytes": downloaded,
                                "total_bytes": total_size,
                                "progress_pct": round(pct, 2),
                                "speed_mb_s": round(speed / (1024**2), 2),
                                "eta_seconds": int(eta_s) if eta_s else None,
                                "status": "DOWNLOADING"
                            }
                            save_progress(track_file, status_dict)

                            d_gb = downloaded / (1024**3)
                            t_gb = total_size / (1024**3)
                            speed_mb = speed / (1024**2)
                            log_msg(f"[{pct:5.1f}%] {d_gb:.2f} / {t_gb:.2f} GiB | Speed: {speed_mb:.2f} MB/s | ETA: {int(eta_s)}s", log_file)

                            last_update = now
                            bytes_window = 0

            final_size = dest_path.stat().st_size if dest_path.exists() else 0
            if final_size >= EXPECTED_BYTES:
                log_msg(f"🎉 Download successfully completed and verified: {final_size:,} bytes", log_file)
                save_progress(track_file, {
                    "filename": filename,
                    "downloaded_bytes": final_size,
                    "total_bytes": EXPECTED_BYTES,
                    "progress_pct": 100.0,
                    "speed_mb_s": 0.0,
                    "eta_seconds": 0,
                    "status": "COMPLETED",
                    "completed_at": time.time()
                })
                return True
            else:
                log_msg(f"Connection ended but file size ({final_size:,}) < expected ({EXPECTED_BYTES:,}). Reconnecting...", log_file)
                time.sleep(3)

        except Exception as e:
            log_msg(f"Download stream error: {e}. Retrying in 5 seconds...", log_file)
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="Resilient Qwen3-Next-80B Downloader")
    parser.add_argument("--dest-dir", default="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf", help="Target directory for downloaded model")
    parser.add_argument("--repo-id", default=DEFAULT_REPO, help="Hugging Face repo ID")
    parser.add_argument("--filename", default=DEFAULT_FILENAME, help="GGUF filename")
    args = parser.parse_args()

    download(dest_dir=args.dest_dir, repo_id=args.repo_id, filename=args.filename)

if __name__ == "__main__":
    main()
