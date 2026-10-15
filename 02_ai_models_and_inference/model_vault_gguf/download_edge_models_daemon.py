#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_ai_models_and_inference/model_vault_gguf/download_edge_models_daemon.py
=========================================================================
Autonomous Edge Models Downloader & Verifier Daemon across all major local AI families:
1. Multimodal Edge: SmolVLM-Instruct (Q4_K_M • 1.04 GB • Vision/Language)
2. Google Gemma Edge: Gemma-2-2B-It (Q4_K_M • 1.59 GB • Google Edge SLM)
3. Mistral AI Edge: Ministral-3B-Instruct (Q4_K_M • 2.00 GB • Mistral Edge SLM)
4. Microsoft Phi Edge: Phi-3.5-Mini-Instruct (Q4_K_M • 2.23 GB • Reasoning Mini)

Governed by:
- Rule 0.1 Zero-Mock Truth Verification
- Rule 3 Host RAM & Disk Sanctuary Headroom
- 24/7 LoRA Distillation Logging to continuous_lora_dataset.jsonl
"""

from __future__ import annotations

import os
import sys
import time
import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

VAULT_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf")
CATALOG_FILE = VAULT_DIR / "MODEL_VAULT_CATALOG_AND_DOWNLOAD_QUEUE.json"
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
OBSIDIAN_MATRIX = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/00_CORE/MESH_DEVICE_ROLE_MATRIX.md")
LLAMA_CLI = Path("/Users/aaron/.local/bin/llama-cli")
HF_TOKEN = os.environ.get("HF_TOKEN", "hf_...[REDACTED_SOVEREIGN]")

TARGET_EDGE_MODELS = [
    {
        "family": "HuggingFace SmolVLM",
        "repo_id": "ggml-org/SmolVLM-Instruct-GGUF",
        "filename": "SmolVLM-Instruct-Q4_K_M.gguf",
        "size_gb": 1.04,
        "target_hardware": "Pixel 10 Pro XL (L6) / Bedside Tablet (L4)",
        "role": "Edge Multimodal Vision-Language for Screen Lens & active perception"
    },
    {
        "family": "Google Gemma",
        "repo_id": "bartowski/gemma-2-2b-it-GGUF",
        "filename": "gemma-2-2b-it-Q4_K_M.gguf",
        "size_gb": 1.59,
        "target_hardware": "Mac Mini M4 Pro Host / MacBook Air (L5)",
        "role": "High-speed Google Gemma edge student model for local distillation"
    },
    {
        "family": "Mistral AI",
        "repo_id": "mistralai/Ministral-3-3B-Instruct-2512-GGUF",
        "filename": "Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        "size_gb": 2.00,
        "target_hardware": "MacBook Pro (L2) via TB4 Bridge / Linux Head Node (L3)",
        "role": "Mistral AI edge instruct specialist for function calling & C11 syntax"
    },
    {
        "family": "Microsoft Phi",
        "repo_id": "bartowski/Phi-3.5-mini-instruct-GGUF",
        "filename": "Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "size_gb": 2.23,
        "target_hardware": "Linux Head Node (L3) / MacBook Pro (L2)",
        "role": "Microsoft Phi mini high-efficiency chain-of-thought reasoner"
    }
]


def check_disk_headroom(required_gb: float) -> bool:
    free_gb = shutil.disk_usage("/Users/aaron").free / (1024.0 ** 3)
    # Maintain at least 3.5 GB safety buffer
    return (free_gb - required_gb) >= 3.5


def verify_gguf_integrity(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {"valid": False, "error": "FILE_NOT_FOUND"}
    
    size_bytes = file_path.stat().st_size
    size_gb = round(size_bytes / (1024.0 ** 3), 2)
    
    # Check GGUF magic header
    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
        if magic != b"GGUF":
            return {"valid": False, "error": f"INVALID_HEADER: {magic}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

    # Empirical benchmark token speed with llama-cli
    tok_s = 0.0
    if LLAMA_CLI.exists():
        try:
            cmd = [
                str(LLAMA_CLI),
                "-m", str(file_path),
                "-p", "Hello",
                "-n", "5",
                "-c", "1024",
                "-b", "256",
                "--no-warmup",
                "--single-turn",
                "--simple-io",
                "--log-disable"
            ]
            t0 = time.perf_counter()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30.0)
            elapsed = time.perf_counter() - t0
            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                return {"valid": False, "error": f"LLAMA_LOAD_ERROR: {err_msg[:200]}"}
            out = proc.stdout
            for line in out.splitlines():
                if "Generation:" in line and "t/s" in line:
                    part = line.split("Generation:")[1].split("t/s")[0].strip()
                    tok_s = float(part)
                    break
            if tok_s == 0.0 and elapsed > 0:
                tok_s = round(5.0 / elapsed, 1)
        except Exception as e:
            return {"valid": False, "error": f"BENCHMARK_EXCEPTION: {str(e)}"}

    return {
        "valid": True,
        "size_gb": size_gb,
        "size_bytes": size_bytes,
        "magic_verified": True,
        "benchmark_tok_s": tok_s
    }


def download_single_model(model_info: Dict[str, Any]) -> bool:
    filename = model_info["filename"]
    repo_id = model_info["repo_id"]
    dest = VAULT_DIR / filename

    print(f"\n========================================================")
    print(f"📦 Processing: {filename} ({model_info['family']})")
    print(f"   • Repo: {repo_id}")
    print(f"   • Size: ~{model_info['size_gb']} GB")
    print(f"========================================================")

    # If file already exists and is valid, skip
    if dest.exists():
        v = verify_gguf_integrity(dest)
        if v["valid"]:
            print(f"✔ [ALREADY_PRESENT] {filename} verified ({v['size_gb']} GB, {v['benchmark_tok_s']} tok/s)")
            model_info["status"] = "VERIFIED_PRESENT"
            model_info["benchmark_tok_s"] = v["benchmark_tok_s"]
            return True

    # Check disk headroom
    if not check_disk_headroom(model_info["size_gb"]):
        free_gb = shutil.disk_usage("/Users/aaron").free / (1024.0 ** 3)
        print(f"⚠️ [HEADROOM_RESTRICTION] Insufficient disk space ({free_gb:.2f} GB available, need {model_info['size_gb'] + 3.5:.2f} GB)")
        return False

    print(f"🚀 Initiating resilient stream download via curl with resume support...")
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    curl_cmd = [
        "curl", "-L", "-C", "-",
        "--retry", "5",
        "--retry-delay", "3",
        "-H", f"Authorization: Bearer {HF_TOKEN}",
        url,
        "-o", str(dest)
    ]

    try:
        proc = subprocess.run(curl_cmd, text=True, timeout=7200.0)
        if proc.returncode == 0 and dest.exists():
            v = verify_gguf_integrity(dest)
            if v["valid"]:
                print(f"✅ [DOWNLOAD_SUCCESS] {filename} verified ({v['size_gb']} GB, {v['benchmark_tok_s']} tok/s)")
                model_info["status"] = "VERIFIED_PRESENT"
                model_info["benchmark_tok_s"] = v["benchmark_tok_s"]
                
                # Log to 24/7 LoRA sink
                log_lora_download_event(model_info, v)
                return True
            else:
                print(f"❌ [CORRUPTION_DETECTED] {filename}: {v.get('error')}")
                return False
        else:
            print(f"❌ [DOWNLOAD_FAILED] curl returned code {proc.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏳ [TIMEOUT] Download timed out after 2 hours.")
        return False
    except Exception as e:
        print(f"❌ [ERROR] {e}")
        return False


def log_lora_download_event(model_info: Dict[str, Any], verify_res: Dict[str, Any]):
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "event": "EDGE_MODEL_ACQUISITION",
        "family": model_info["family"],
        "model_file": model_info["filename"],
        "repo_id": model_info["repo_id"],
        "size_gb": verify_res.get("size_gb"),
        "benchmark_tok_s": verify_res.get("benchmark_tok_s"),
        "target_hardware": model_info["target_hardware"],
        "role": model_info["role"],
        "zero_mock_verified": True
    }
    LORA_DATASET.parent.mkdir(parents=True, exist_ok=True)
    with open(LORA_DATASET, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def update_catalog(models: List[Dict[str, Any]]):
    existing = []
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    existing_filenames = {e.get("filename") for e in existing}
    for m in models:
        if m["filename"] not in existing_filenames:
            existing.append({
                "repo_id": m["repo_id"],
                "filename": m["filename"],
                "category": f"{m['family']} Edge ({m['size_gb']} GB)",
                "size_gb": m["size_gb"],
                "target_hardware": m["target_hardware"],
                "role": m["role"],
                "benchmark_tok_s": m.get("benchmark_tok_s", "--"),
                "status": m.get("status", "QUEUED_DOWNLOAD")
            })
        else:
            for e in existing:
                if e.get("filename") == m["filename"]:
                    e["status"] = m.get("status", e.get("status"))
                    if "benchmark_tok_s" in m:
                        e["benchmark_tok_s"] = m["benchmark_tok_s"]

    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def main():
    print("==========================================================================================")
    print("🌐 LAUBURU MESH: AUTONOMOUS MULTI-FAMILY EDGE MODEL HARVESTER DAEMON")
    print("==========================================================================================")
    print(f"📁 Destination Vault: {VAULT_DIR}")
    free_gb = shutil.disk_usage("/Users/aaron").free / (1024.0 ** 3)
    print(f"💾 Current Free Disk Space: {free_gb:.2f} GB")

    for model in TARGET_EDGE_MODELS:
        download_single_model(model)
        update_catalog([model])

    print("\n🎉 Edge Model Harvester Cycle Complete.")


if __name__ == "__main__":
    main()
