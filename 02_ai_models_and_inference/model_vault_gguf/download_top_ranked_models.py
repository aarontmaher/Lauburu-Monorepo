#!/usr/bin/env python3
"""
Lauburu Model Vault: Resilient Multi-Threaded Model Downloader
Downloads top-ranked SWE-bench Genetic MoE models with resume support and disk safety checks:
1. DeepSeek Coder V2 Lite MoE Q4_K_M (9.8 GB)
2. Qwen 2.5 Coder 32B Instruct Q4_K_M (19.8 GB)
"""

import os
import sys
import time
import shutil
import urllib.request
import subprocess

VAULT_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
os.makedirs(VAULT_DIR, exist_ok=True)

DOWNLOAD_TARGETS = [
    {
        "name": "DeepSeek Coder V2 Lite MoE (Q4_K_M)",
        "filename": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF/resolve/main/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "expected_gb": 9.8
    },
    {
        "name": "Qwen 2.5 Coder 32B Instruct (Q4_K_M)",
        "filename": "qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        "expected_gb": 19.8
    }
]

def check_disk_headroom():
    total, used, free = shutil.disk_usage(VAULT_DIR)
    free_gb = free / (1024**3)
    print(f"💾 Local Disk Free Headroom: {free_gb:.1f} GB")
    if free_gb < 15.0:
        print("⚠️ Warning: Disk headroom low. Preserving Tri-Vault minimum threshold (>=10 GB).")
        return False
    return True

def download_with_curl(target):
    dest_path = os.path.join(VAULT_DIR, target["filename"])
    if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100 * 1024 * 1024:
        print(f"✅ {target['name']} already exists at {dest_path} ({os.path.getsize(dest_path)/(1024**3):.2f} GB)")
        return True

    print(f"\n🚀 Initiating resilient download: {target['name']} ({target['expected_gb']} GB)...")
    print(f"   Source: {target['url']}")
    print(f"   Destination: {dest_path}")

    # Use curl with resume flag (-C -) and progress output
    cmd = f'curl -L -C - --fail --retry 5 --retry-delay 3 -o "{dest_path}.part" "{target["url"]}"'
    res = subprocess.run(cmd, shell=True)

    if res.returncode == 0 and os.path.isfile(f"{dest_path}.part"):
        os.rename(f"{dest_path}.part", dest_path)
        print(f"🎉 Download Complete: {target['name']} -> {dest_path}")
        return True
    else:
        print(f"⚠️ Download interrupted for {target['name']} (part file saved for automatic resume).")
        return False

def main():
    print("======================================================================")
    print("📥 LAUBURU MODEL VAULT: RESILIENT DOWNLOAD RUNNER")
    print("======================================================================")
    
    if not check_disk_headroom():
        sys.exit(1)

    for target in DOWNLOAD_TARGETS:
        download_with_curl(target)

if __name__ == "__main__":
    main()
