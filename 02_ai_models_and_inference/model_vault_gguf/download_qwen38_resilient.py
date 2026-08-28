import os
import sys
import time
import json
import urllib.request

REPO_ID = "huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF"
FILENAME = "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf"
DEST_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
DEST_PATH = os.path.join(DEST_DIR, FILENAME)
TRACK_FILE = os.path.join(DEST_DIR, "qwen3.8_download_progress.json")
URL = f"https://huggingface.co/{REPO_ID}/resolve/main/{FILENAME}?download=true"

os.makedirs(DEST_DIR, exist_ok=True)

def update_status(downloaded, total, speed, percent, eta_s, status="downloading"):
    data = {
        "model": FILENAME,
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

total_size = 17378626464 # fallback from API (16.19 GB)

print(f"Auto-resuming download of {FILENAME}...")

while True:
    existing_size = os.path.getsize(DEST_PATH) if os.path.exists(DEST_PATH) else 0
    if existing_size >= total_size and total_size > 0:
        update_status(existing_size, total_size, 0, 100.0, 0, "completed")
        print(f"SUCCESS: {FILENAME} fully downloaded ({existing_size/(1024**3):.2f} GB).")
        break

    headers = {"User-Agent": "Mozilla/5.0 (Lauburu-Mesh-Downloader/1.0)"}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        print(f"Resuming from {existing_size / (1024**3):.2f} GB / {total_size / (1024**3):.2f} GB...")

    req = urllib.request.Request(URL, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            content_range = resp.headers.get("Content-Range")
            content_length = resp.headers.get("Content-Length")
            
            if content_range:
                total_size = int(content_range.split("/")[-1])
            elif content_length and existing_size == 0:
                total_size = int(content_length)

            mode = "ab" if existing_size > 0 else "wb"
            downloaded = existing_size
            start_time = time.time()
            last_print = start_time
            bytes_since_last = 0

            with open(DEST_PATH, mode) as out_f:
                while True:
                    chunk = resp.read(1024 * 1024 * 4) # 4MB chunks
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    bytes_since_last += len(chunk)

                    now = time.time()
                    if now - last_print >= 2.0:
                        dt = now - last_print
                        speed = bytes_since_last / dt
                        percent = (downloaded / total_size) * 100 if total_size else 0
                        eta_s = (total_size - downloaded) / speed if speed > 0 else 0
                        update_status(downloaded, total_size, speed, percent, eta_s, "downloading")
                        print(f"[{percent:5.1f}%] {downloaded/(1024**3):.2f}/{total_size/(1024**3):.2f} GB | Speed: {speed/(1024**2):.1f} MB/s | ETA: {eta_s:.0f}s", flush=True)
                        last_print = now
                        bytes_since_last = 0

            if downloaded >= total_size:
                update_status(downloaded, total_size, 0, 100.0, 0, "completed")
                print(f"SUCCESS: {FILENAME} downloaded ({downloaded/(1024**3):.2f} GB).", flush=True)
                break

    except Exception as e:
        print(f"Network transient error ({e}), retrying in 3s...", flush=True)
        update_status(existing_size, total_size, 0, (existing_size/total_size)*100, 0, f"retrying: {e}")
        time.sleep(3)
