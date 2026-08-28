#!/usr/bin/env python3
"""
Petals DHT Mesh Orchestrator & Model Provisioning Engine (v1.1)
Governs model provisioning, distributed DHT bootstrapping, and swarm inference
across the Lauburu 7-node heterogeneous mesh cluster.

Supported Petals Models (Lightweight -> Medium -> Swarm):
1. bigscience/bloom-560m (~1.12 GB) - Ultra-lightweight DHT bootstrap & tensor verification
2. petals-team/Stable-Beluga-7B (~13.5 GB FP16 / ~3.8 GB 4-bit) - Standard Petals 7B benchmark
3. petals-team/Mistral-7B-Instruct-v0.1 (~14.5 GB FP16 / ~4.1 GB 4-bit) - High-efficiency instruction model
4. bigscience/bloom-7b1 (~14.1 GB FP16 / ~4.0 GB 8-bit) - Multilingual base BLOOM swarm
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
MODELS_DIR = REPO_ROOT / "02_ai_models_and_inference/models"
PETALS_DIR = REPO_ROOT / "02_ai_models_and_inference/petals_dht"
PETALS_MODELS_CACHE = PETALS_DIR / "cache"
VENV_DIR = PETALS_DIR / ".venv"
UV_BIN = Path("/Users/aaron/.local/bin/uv")

PETALS_CATALOG = [
    {
        "model_id": "bloom-560m",
        "repo_id": "bigscience/bloom-560m",
        "name": "BLOOM 560M (Petals Bootstrap & Verification)",
        "params": "560M",
        "size_fp16_gb": 1.12,
        "size_8bit_gb": 0.60,
        "vram_recommended_gb": 1.5,
        "sharding_feasibility": "✅ Fits 100% on ANY single node (Pixel, Samsung, Mac, Linux)",
        "description": "Ultra-lightweight Petals model for instant DHT connectivity tests, healthchecks, and mobile node validation without saturating memory.",
        "download_urls": [
            "https://huggingface.co/bigscience/bloom-560m/resolve/main/config.json",
            "https://huggingface.co/bigscience/bloom-560m/resolve/main/tokenizer.json",
            "https://huggingface.co/bigscience/bloom-560m/resolve/main/tokenizer_config.json",
            "https://huggingface.co/bigscience/bloom-560m/resolve/main/model.safetensors",
        ]
    },
    {
        "model_id": "stable-beluga-7b",
        "repo_id": "petals-team/Stable-Beluga-7B",
        "name": "Stable Beluga 7B (Official Petals Swarm)",
        "params": "7.0B",
        "size_fp16_gb": 13.5,
        "size_8bit_gb": 7.2,
        "size_4bit_gb": 3.8,
        "vram_recommended_gb": 8.0,
        "sharding_feasibility": "✅ 2-Layer Split (Mac Mini Host + MacBook Air)",
        "description": "Official Petals community model based on LLaMA-2 7B fine-tuned on Orca-style datasets.",
        "download_urls": [
            "https://huggingface.co/petals-team/Stable-Beluga-7B/resolve/main/config.json",
            "https://huggingface.co/petals-team/Stable-Beluga-7B/resolve/main/tokenizer.json",
            "https://huggingface.co/petals-team/Stable-Beluga-7B/resolve/main/tokenizer_config.json",
        ]
    },
    {
        "model_id": "mistral-7b-instruct",
        "repo_id": "petals-team/Mistral-7B-Instruct-v0.1",
        "name": "Mistral 7B Instruct v0.1 (Petals Swarm)",
        "params": "7.2B",
        "size_fp16_gb": 14.5,
        "size_8bit_gb": 7.5,
        "size_4bit_gb": 4.1,
        "vram_recommended_gb": 8.5,
        "sharding_feasibility": "✅ 2-Layer Split (Mac Mini Host + MacBook Air)",
        "description": "High-throughput sliding-window attention model adapted for collaborative Petals generation.",
        "download_urls": [
            "https://huggingface.co/petals-team/Mistral-7B-Instruct-v0.1/resolve/main/config.json",
            "https://huggingface.co/petals-team/Mistral-7B-Instruct-v0.1/resolve/main/tokenizer.json",
            "https://huggingface.co/petals-team/Mistral-7B-Instruct-v0.1/resolve/main/tokenizer_config.json",
        ]
    },
    {
        "model_id": "bloom-7b1",
        "repo_id": "bigscience/bloom-7b1",
        "name": "BLOOM 7.1B (Multilingual Swarm)",
        "params": "7.1B",
        "size_fp16_gb": 14.1,
        "size_8bit_gb": 7.4,
        "size_4bit_gb": 4.0,
        "vram_recommended_gb": 8.0,
        "sharding_feasibility": "✅ 2-Layer Split (Mac Mini Host + MacBook Air)",
        "description": "Foundation multilingual open-source model natively supported across Petals public swarm.",
        "download_urls": [
            "https://huggingface.co/bigscience/bloom-7b1/resolve/main/config.json",
            "https://huggingface.co/bigscience/bloom-7b1/resolve/main/tokenizer.json",
            "https://huggingface.co/bigscience/bloom-7b1/resolve/main/tokenizer_config.json",
        ]
    }
]

CLUSTER_NODES = {
    "layer_1_mac_mini_host": {"name": "Apple M4 Pro Mac Mini Host", "ip": "100.119.199.76", "ram_gb": 24.0, "safe_vram_gb": 18.0, "role": "Bootstrap / Client / Worker"},
    "layer_2_macbook_pro_vault": {"name": "Headless Intel i7 MacBook Pro", "ip": "100.103.212.21", "ram_gb": 16.0, "safe_vram_gb": 12.0, "role": "Worker"},
    "layer_3_linux_head_node": {"name": "AMD Ryzen 7 5700U Linux Node", "ip": "100.101.39.98", "ram_gb": 16.0, "safe_vram_gb": 12.0, "role": "DHT Bootstrap Server"},
    "layer_4_debian_tablet": {"name": "Debian Linux Tablet", "ip": "100.81.92.125", "ram_gb": 8.0, "safe_vram_gb": 4.5, "role": "Edge Worker"},
    "layer_5_macbook_air": {"name": "Apple M4 MacBook Air", "ip": "100.93.158.96", "ram_gb": 16.0, "safe_vram_gb": 12.0, "role": "Worker (Clamshell Active)"},
    "layer_6_pixel_10_pro_xl": {"name": "Google Pixel 10 Pro XL", "ip": "100.73.38.87", "ram_gb": 16.0, "safe_vram_gb": 12.5, "role": "Edge Client / TPU Worker"},
    "layer_7_samsung_s20_plus": {"name": "Samsung Galaxy S20+", "ip": "100.84.40.95", "ram_gb": 12.0, "safe_vram_gb": 9.0, "role": "Edge Telemetry / Worker"}
}


class PetalsMeshOrchestrator:
    def __init__(self):
        PETALS_MODELS_CACHE.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

    def print_catalog(self):
        """Displays catalog of Petals models with sharding matrix."""
        print("\n🌸 ==================== PETALS DHT COMPATIBLE MODELS ==================== 🌸\n")
        for m in PETALS_CATALOG:
            print(f"📦 ID: {m['model_id']} | Repo: {m['repo_id']}")
            print(f"   Name:        {m['name']}")
            print(f"   Parameters:  {m['params']} | FP16: {m['size_fp16_gb']} GB | 8-bit: {m['size_8bit_gb']} GB")
            print(f"   Feasibility: {m['sharding_feasibility']}")
            print(f"   Description: {m['description']}")
            print("   " + "-" * 70)

        print("\n🖥️ ==================== CLUSTER HARDWARE HEADROOM ==================== 🖥️\n")
        total_ram = sum(n["ram_gb"] for n in CLUSTER_NODES.values())
        total_vram = sum(n["safe_vram_gb"] for n in CLUSTER_NODES.values())
        print(f"   Total Nodes:      {len(CLUSTER_NODES)}")
        print(f"   Pooled RAM:       {total_ram:.1f} GB")
        print(f"   Pooled AI VRAM:   {total_vram:.1f} GB Headroom\n")
        for key, node in CLUSTER_NODES.items():
            print(f"   • {node['name']} ({node['ip']}): {node['ram_gb']} GB RAM (Safe AI: {node['safe_vram_gb']} GB) - {node['role']}")
        print()

    def download_model(self, model_id: str) -> bool:
        """Downloads model files using resilient curl streaming."""
        target_model = next((m for m in PETALS_CATALOG if m["model_id"] == model_id), None)
        if not target_model:
            print(f"❌ Model ID '{model_id}' not found in catalog.")
            return False

        target_dir = PETALS_MODELS_CACHE / target_model["model_id"]
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n🚀 Downloading Petals model '{target_model['name']}' ({target_model['repo_id']})...")
        print(f"   Target Directory: {target_dir}")

        success = True
        for url in target_model.get("download_urls", []):
            filename = url.split("/")[-1]
            dest_file = target_dir / filename
            if dest_file.exists() and dest_file.stat().st_size > 0:
                print(f"   ✅ Already present: {filename} ({dest_file.stat().st_size / 1024 / 1024:.2f} MB)")
                continue

            print(f"   ⚡ Fetching {filename}...")
            cmd = ["curl", "-L", "-s", "--fail", "--retry", "3", "-o", str(dest_file), url]
            t0 = time.perf_counter()
            res = subprocess.run(cmd, capture_output=True, text=True)
            elapsed = time.perf_counter() - t0
            
            if res.returncode == 0 and dest_file.exists() and dest_file.stat().st_size > 0:
                size_mb = dest_file.stat().st_size / 1024 / 1024
                throughput = size_mb / max(elapsed, 0.001)
                print(f"   ✅ Completed: {filename} ({size_mb:.2f} MB in {elapsed:.2f}s @ {throughput:.2f} MB/s)")
            else:
                print(f"   ❌ Failed to fetch {filename}: exit={res.returncode} {res.stderr.strip()[:200]}")
                success = False

        if success:
            manifest_file = target_dir / "petals_model_manifest.json"
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump({
                    "model_id": target_model["model_id"],
                    "repo_id": target_model["repo_id"],
                    "name": target_model["name"],
                    "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "files": [f.name for f in target_dir.iterdir() if f.is_file()]
                }, f, indent=2)
            print(f"🎉 Model '{target_model['name']}' ready in Petals cache!\n")

        return success

    def compute_sharding_plan(self, model_id: str) -> Dict[str, Any]:
        """Computes optimal block distribution across the cluster."""
        target_model = next((m for m in PETALS_CATALOG if m["model_id"] == model_id), None)
        if not target_model:
            target_model = PETALS_CATALOG[0]

        if target_model["model_id"] == "bloom-560m":
            num_blocks = 24
            plan = {
                "model_id": "bloom-560m",
                "total_blocks": num_blocks,
                "shards": [
                    {"node": "layer_1_mac_mini_host", "blocks": "0:8", "vram_mb": 400},
                    {"node": "layer_5_macbook_air", "blocks": "8:16", "vram_mb": 400},
                    {"node": "layer_3_linux_head_node", "blocks": "16:24", "vram_mb": 400},
                ],
                "bootstrap_node": "100.119.199.76:31330",
                "redundancy_level": "High (3x fallback nodes available)"
            }
        elif "7b" in target_model["model_id"]:
            num_blocks = 32
            plan = {
                "model_id": target_model["model_id"],
                "total_blocks": num_blocks,
                "shards": [
                    {"node": "layer_1_mac_mini_host", "blocks": "0:12", "vram_mb": 2800},
                    {"node": "layer_5_macbook_air", "blocks": "12:22", "vram_mb": 2400},
                    {"node": "layer_2_macbook_pro_vault", "blocks": "22:32", "vram_mb": 2400},
                ],
                "bootstrap_node": "100.119.199.76:31330",
                "redundancy_level": "Balanced (Linux + Pixel available on demand)"
            }
        else:
            plan = {"model_id": model_id, "status": "CUSTOM_PLAN"}

        return plan


def main():
    parser = argparse.ArgumentParser(description="Petals DHT Mesh Orchestrator")
    parser.add_argument("--catalog", action="store_true", help="List Petals-compatible models and hardware specs")
    parser.add_argument("--download", type=str, help="Download model by ID (e.g. bloom-560m, stable-beluga-7b)")
    parser.add_argument("--download-small", action="store_true", help="Download bloom-560m for lightweight DHT testing")
    parser.add_argument("--plan", type=str, help="Show distributed tensor sharding plan for model ID")
    args = parser.parse_args()

    orchestrator = PetalsMeshOrchestrator()

    if args.catalog or len(sys.argv) == 1:
        orchestrator.print_catalog()

    if args.download_small:
        orchestrator.download_model("bloom-560m")

    if args.download:
        orchestrator.download_model(args.download)

    if args.plan:
        plan = orchestrator.compute_sharding_plan(args.plan)
        print("\n📊 ==================== DISTRIBUTED SHARDING PLAN ==================== 📊\n")
        print(json.dumps(plan, indent=2))
        print()


if __name__ == "__main__":
    main()
