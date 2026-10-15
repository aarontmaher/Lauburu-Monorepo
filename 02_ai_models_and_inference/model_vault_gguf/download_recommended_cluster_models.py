#!/usr/bin/env python3
"""
Lauburu Mesh: Recommended High-Efficiency Cluster Model Downloader
Downloads optimal GGUF / MLX models balanced for the 82.8 GB VRAM 7-Device Mesh:
1. Qwen 2.5 Coder 32B Instruct (Q4_K_M ~19.8 GB) - #1 Local Coding Model
2. DeepSeek Coder V2 Lite MoE (Q4_K_M ~9.8 GB) - Ultra-Fast MoE Coding (80+ tok/s)
3. Qwen 2.5 Coder 1.5B Instruct (Q4_K_M ~1.0 GB) - Speculative Draft Token Engine
4. Llama 3.3 70B Instruct (Q4_K_M ~42.5 GB) - 50/50 Sharded Reasoning King
"""

import os
import sys
import subprocess

MODEL_VAULT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
os.makedirs(MODEL_VAULT, exist_ok=True)

RECOMMENDED_MODELS = [
    {
        "name": "Qwen 2.5 Coder 32B Instruct (Q4_K_M)",
        "repo": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "filename": "qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        "size_gb": 19.8,
        "role": "Primary Local Developer & Codebase Specialist (Mac Mini Single-Node / TB4 Shard)"
    },
    {
        "name": "DeepSeek Coder V2 Lite Instruct (Q4_K_M MoE 16B)",
        "repo": "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        "filename": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "size_gb": 9.8,
        "role": "High-Throughput Expert Parallelism (80+ tok/s over Wi-Fi 7 / TB4)"
    },
    {
        "name": "Qwen 2.5 Coder 1.5B Instruct (Q4_K_M)",
        "repo": "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
        "filename": "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "size_gb": 1.0,
        "role": "Speculative Decoding Draft Engine (2.2x Speedup on 32B/70B models)"
    },
    {
        "name": "Llama 3.3 70B Instruct (Q4_K_M)",
        "repo": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q4_K_M.gguf",
        "size_gb": 42.5,
        "role": "Frontier Heavy Reasoning (Sharded 50/50 across Mac Mini + MacBook Pro via Prima.cpp)"
    }
]

def check_existing():
    print("======================================================================")
    print("🧠 LAUBURU MESH: RECOMMENDED CLUSTER MODEL CATALOG")
    print("======================================================================")
    for m in RECOMMENDED_MODELS:
        path = os.path.join(MODEL_VAULT, m["filename"])
        exists = os.path.isfile(path) and os.path.getsize(path) > 100 * 1024 * 1024
        status = "✅ PRESENT" if exists else "📥 READY TO DOWNLOAD"
        print(f"• {m['name']} ({m['size_gb']} GB): {status}")
        print(f"    - Role: {m['role']}")
        print(f"    - HF Repo: {m['repo']}\n")

if __name__ == "__main__":
    check_existing()
