#!/usr/bin/env python3
"""
Small Draft Models Procurement Script
======================================
Downloads diverse sub-3B GGUF models across various model families
(SmolLM2, Qwen2.5, DeepSeek-R1 Distill, Gemma-2, Llama-3.2) to support
comprehensive multi-family speculative decoding distillation trials.
"""

import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

TARGET_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

MODELS_TO_DOWNLOAD = [
    {
        "repo_id": "HuggingFaceTB/SmolLM2-135M-Instruct-GGUF",
        "filename": "smollm2-135m-instruct-q4_k_m.gguf",
        "name": "SmolLM2-135M"
    },
    {
        "repo_id": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        "filename": "smollm2-360m-instruct-q4_k_m.gguf",
        "name": "SmolLM2-360M"
    },
    {
        "repo_id": "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
        "filename": "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "name": "DeepSeek-R1-Distill-1.5B"
    },
    {
        "repo_id": "bartowski/gemma-2-2b-it-GGUF",
        "filename": "gemma-2-2b-it-Q4_K_M.gguf",
        "name": "Gemma-2-2B"
    }
]

def main():
    print("======================================================================")
    print("🚀 DOWNLOADING SUB-3B SPECULATIVE DRAFT MODELS")
    print("======================================================================")
    for m in MODELS_TO_DOWNLOAD:
        dest = TARGET_DIR / m["filename"]
        if dest.exists() and dest.stat().st_size > 1024 * 1024:
            print(f"✅ {m['name']} already exists at: {dest} ({dest.stat().st_size / (1024*1024):.1f} MB)")
            continue
        print(f"📥 Downloading {m['name']} from {m['repo_id']} -> {m['filename']}...")
        try:
            downloaded_path = hf_hub_download(
                repo_id=m["repo_id"],
                filename=m["filename"],
                local_dir=TARGET_DIR,
                local_dir_use_symlinks=False
            )
            print(f"✅ Downloaded {m['name']} to {downloaded_path}")
        except Exception as e:
            print(f"⚠️ Failed to download {m['name']}: {e}")

    print("======================================================================\n")

if __name__ == "__main__":
    main()
