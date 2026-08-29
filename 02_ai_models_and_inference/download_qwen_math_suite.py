#!/usr/bin/env python3
"""
Qwen2.5-Math Model Download Manager & 24/7 Training Pipeline Orchestrator
=========================================================================
Subsystem: 02_ai_models_and_inference/download_qwen_math_suite.py
Version: 1.0.0
Lauburu Mesh Ecosystem — 2026

Downloads the full Qwen2.5-Math suite across the mesh based on node capabilities:

MAC MINI (13 GB free):
  - Qwen2.5-Math-1.5B-Instruct-Q8_0.gguf   (~1.7 GB) → Edge inference on Port 8086
  - Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf   (~4.4 GB) → Enhanced math fact-check Port 8086
  - Qwen2.5-Math-72B-Instruct-IQ2_XXS.gguf (~19 GB)  → Full 72B ultra-compressed (needs cleanup)

MACBOOK PRO (285 GB vault, via WoL):
  - Qwen2.5-Math-72B-Instruct-Q4_K_M.gguf  (~42 GB)  → High-quality 72B math
  - Qwen2.5-Math-72B-Instruct-Q6_K.gguf    (~58 GB)  → Premium quality 72B math
  - Qwen2.5-Math-RM-72B (BF16 safetensors) (~146 GB) → Reward model for DPO training

LINUX HEAD NODE (AMD 5700U, 16 GB):
  - Qwen2.5-Math-7B-Instruct-Q8_0.gguf     (~8 GB)   → Full precision 7B on Linux
  - Qwen2.5-Math-1.5B-Instruct-Q8_0.gguf   (~1.7 GB) → Ultra-fast edge on Linux
"""

import os
import sys
import json
import time
import subprocess
import threading
import socket
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any
from huggingface_hub import hf_hub_download, snapshot_download, HfApi

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
GGUF_VAULT = REPO_ROOT / "02_ai_models_and_inference" / "gguf_vault"
HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
LOG_FILE = REPO_ROOT / "session_logs" / "qwen_math_download_status.json"

# Download manifest — ordered by priority (smallest/most impactful first)
DOWNLOAD_MANIFEST: List[Dict[str, Any]] = [
    # ── TIER 1: Mac Mini (local, immediate) ─────────────────────────────────
    {
        "id": "qwen_math_1.5b_q8_mac_mini",
        "name": "Qwen2.5-Math-1.5B-Instruct-Q8_0",
        "repo_id": "bartowski/Qwen2.5-Math-1.5B-Instruct-GGUF",
        "filename": "Qwen2.5-Math-1.5B-Instruct-Q8_0.gguf",
        "size_gb": 1.7,
        "target_node": "mac_mini",
        "target_path": GGUF_VAULT,
        "serve_port": 8086,
        "serve_alias": "qwen-math-1.5b-edge",
        "priority": 1,
        "use_case": "Ultra-fast edge math fact-check, router-level inference, 24/7 training pair generation",
    },
    {
        "id": "qwen_math_7b_q4km_mac_mini",
        "name": "Qwen2.5-Math-7B-Instruct-Q4_K_M",
        "repo_id": "bartowski/Qwen2.5-Math-7B-Instruct-GGUF",
        "filename": "Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.4,
        "target_node": "mac_mini",
        "target_path": GGUF_VAULT,
        "serve_port": 8086,
        "serve_alias": "qwen-math-7b",
        "priority": 2,
        "use_case": "Enhanced math reasoning, DPO pair quality scoring, architecture optimization",
    },
    {
        "id": "qwen_math_7b_q8_mac_mini",
        "name": "Qwen2.5-Math-7B-Instruct-Q8_0",
        "repo_id": "bartowski/Qwen2.5-Math-7B-Instruct-GGUF",
        "filename": "Qwen2.5-Math-7B-Instruct-Q8_0.gguf",
        "size_gb": 8.0,
        "target_node": "mac_mini",
        "target_path": GGUF_VAULT,
        "serve_port": 8086,
        "serve_alias": "qwen-math-7b-q8",
        "priority": 3,
        "use_case": "High-quality math inference for LoRA teacher-student distillation",
    },
    # ── TIER 2: Mac Mini 72B compressed ─────────────────────────────────────
    {
        "id": "qwen_math_72b_iq2xxs_mac_mini",
        "name": "Qwen2.5-Math-72B-Instruct-IQ2_XXS (Ultra-Compressed)",
        "repo_id": "bartowski/Qwen2.5-Math-72B-Instruct-GGUF",
        "filename": "Qwen2.5-Math-72B-Instruct-IQ2_XXS.gguf",
        "size_gb": 19.0,
        "target_node": "mac_mini",
        "target_path": GGUF_VAULT,
        "serve_port": 8084,
        "serve_alias": "qwen-math-72b-edge",
        "priority": 4,
        "use_case": "72B math reasoning with minimum VRAM — fits on 21.6 GB Metal GPU when 1.5/7B offloaded",
        "requires_free_gb": 6.0,  # Need to ensure enough headroom
    },
    # ── TIER 3: MacBook Pro via WoL (download via SSH after WoL) ─────────────
    {
        "id": "qwen_math_72b_q4km_mbp",
        "name": "Qwen2.5-Math-72B-Instruct-Q4_K_M (High Quality)",
        "repo_id": "bartowski/Qwen2.5-Math-72B-Instruct-GGUF",
        "filename": "Qwen2.5-Math-72B-Instruct-Q4_K_M.gguf",
        "size_gb": 42.0,
        "target_node": "macbook_pro",
        "target_host": "192.168.8.127",  # Or TB4: 169.254.187.138
        "target_path": Path("/Users/aaron/models/gguf"),
        "serve_port": 50052,
        "serve_alias": "qwen-math-72b-q4",
        "priority": 5,
        "use_case": "Production-quality 72B math reasoning via TB4 RPC shard",
    },
    {
        "id": "qwen_math_rm_72b_mbp",
        "name": "Qwen2.5-Math-RM-72B (Reward Model, BF16)",
        "repo_id": "Qwen/Qwen2.5-Math-RM-72B",
        "filename": None,  # Full snapshot
        "size_gb": 146.0,
        "target_node": "macbook_pro",
        "target_host": "192.168.8.127",
        "target_path": Path("/Users/aaron/models/Qwen2.5-Math-RM-72B"),
        "serve_port": None,  # Used for DPO training, not serving
        "serve_alias": "qwen-math-rm-72b",
        "priority": 6,
        "use_case": "Reward model for DPO/RLHF training pipeline — scores math solution quality",
    },
]

STATUS_STORE: Dict[str, Any] = {}


def probe_disk_free(path: Path) -> float:
    """Returns free disk space in GB at the given path."""
    import shutil
    try:
        return shutil.disk_usage(str(path)).free / (1024 ** 3)
    except Exception:
        return 0.0


def download_gguf_local(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Download a single GGUF file to local GGUF vault."""
    target_path = entry["target_path"]
    target_path.mkdir(parents=True, exist_ok=True)
    dest_file = target_path / entry["filename"]

    if dest_file.exists():
        size_gb = dest_file.stat().st_size / (1024 ** 3)
        print(f"  ✅ Already exists: {dest_file.name} ({size_gb:.1f} GB)")
        return {"status": "ALREADY_EXISTS", "path": str(dest_file), "size_gb": size_gb}

    free_gb = probe_disk_free(target_path)
    required = entry.get("requires_free_gb", entry["size_gb"] * 1.05)
    if free_gb < required:
        print(f"  ⚠️  SKIPPED {entry['name']}: only {free_gb:.1f} GB free, need {required:.1f} GB")
        return {"status": "SKIPPED_LOW_DISK", "free_gb": free_gb, "required_gb": required}

    print(f"  ⬇️  Downloading {entry['name']} ({entry['size_gb']:.1f} GB) → {dest_file}")
    t0 = time.time()
    try:
        downloaded = hf_hub_download(
            repo_id=entry["repo_id"],
            filename=entry["filename"],
            local_dir=str(target_path),
            local_dir_use_symlinks=False,
        )
        elapsed = round(time.time() - t0, 1)
        size_gb = Path(downloaded).stat().st_size / (1024 ** 3)
        print(f"  ✅ Downloaded: {entry['filename']} ({size_gb:.1f} GB) in {elapsed:.0f}s")
        return {"status": "DOWNLOADED", "path": downloaded, "size_gb": size_gb, "elapsed_s": elapsed}
    except Exception as e:
        elapsed = round(time.time() - t0, 1)
        print(f"  ❌ FAILED: {entry['name']}: {e}")
        return {"status": "FAILED", "error": str(e), "elapsed_s": elapsed}


def download_snapshot_remote_prep(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Generate SSH download command for remote node (MacBook Pro)."""
    cmd = f"""ssh -o ConnectTimeout=5 {entry['target_host']} '
        mkdir -p {entry['target_path']}
        cd {entry['target_path']}
        python3 -c "
from huggingface_hub import hf_hub_download, snapshot_download
import os
os.makedirs(\\"{entry['target_path']}\\", exist_ok=True)
"""
    if entry.get("filename"):
        cmd += f"""
hf_hub_download(repo_id=\\"{entry['repo_id']}\\", filename=\\"{entry['filename']}\\", local_dir=\\"{entry['target_path']}\\", local_dir_use_symlinks=False)
print(\\"DONE: {entry['filename']}\\")
"""
    else:
        cmd += f"""
snapshot_download(repo_id=\\"{entry['repo_id']}\\", local_dir=\\"{entry['target_path']}\\")
print(\\"DONE: {entry['repo_id']}\\")
"""
    cmd += '"\'"""
    return {"status": "SSH_COMMAND_READY", "ssh_cmd": cmd}


def launch_llama_server(entry: Dict[str, Any]) -> bool:
    """Launch llama-server for a downloaded GGUF model on the specified port."""
    dest_file = entry["target_path"] / entry["filename"]
    if not dest_file.exists():
        return False

    port = entry.get("serve_port")
    if not port:
        return False

    # Kill existing server on same port
    subprocess.run(f"lsof -ti :{port} | xargs kill -9 2>/dev/null || true", shell=True)
    time.sleep(0.5)

    llama_server = Path("/Users/aaron/.local/bin/llama-server")
    if not llama_server.exists():
        llama_server = Path("/Users/aaron/.local/bin/llama-b10545/llama-server")

    # Optimal GPU layers for Apple Silicon Metal
    n_gpu_layers = 999  # offload everything to Metal GPU
    ctx_size = 4096
    threads = 4

    cmd = [
        str(llama_server),
        "--model", str(dest_file),
        "--port", str(port),
        "--host", "0.0.0.0",
        "--n-gpu-layers", str(n_gpu_layers),
        "--ctx-size", str(ctx_size),
        "--threads", str(threads),
        "--alias", entry.get("serve_alias", "qwen-math"),
        "--log-disable",
    ]

    log_path = REPO_ROOT / "session_logs" / f"llama_server_{port}.log"
    with open(log_path, "a") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)

    time.sleep(3.0)
    # Verify it's listening
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    online = s.connect_ex(("127.0.0.1", port)) == 0
    s.close()

    print(f"  {'🟢' if online else '🔴'} llama-server on :{port} for {entry['name']} — {'ONLINE' if online else 'FAILED'}")
    return online


def run_download_pipeline() -> Dict[str, Any]:
    """Main download pipeline — runs all local downloads by priority."""
    results = {}
    print("\n🚀 Qwen2.5-Math Suite Download Pipeline Starting...\n")
    print(f"  Mac Mini disk free: {probe_disk_free(Path.home()):.1f} GB")
    print(f"  GGUF Vault: {GGUF_VAULT}\n")

    local_entries = [e for e in DOWNLOAD_MANIFEST if e["target_node"] == "mac_mini"]
    remote_entries = [e for e in DOWNLOAD_MANIFEST if e["target_node"] != "mac_mini"]

    # Download local models
    for entry in sorted(local_entries, key=lambda x: x["priority"]):
        print(f"\n[{entry['priority']}] {entry['name']}")
        print(f"    Use case: {entry['use_case']}")
        result = download_gguf_local(entry)
        results[entry["id"]] = result

        # Auto-launch server if downloaded and port available
        if result["status"] in ("DOWNLOADED", "ALREADY_EXISTS") and entry.get("serve_port"):
            launch_llama_server(entry)

        # Re-check disk after each download
        free_remaining = probe_disk_free(Path.home())
        print(f"    Disk remaining: {free_remaining:.1f} GB")
        if free_remaining < 2.0:
            print("  ⚠️  Low disk space — stopping local downloads")
            break

    # Generate SSH commands for remote nodes
    print("\n\n📡 Remote Node Download Instructions (MacBook Pro, requires WoL):\n")
    for entry in sorted(remote_entries, key=lambda x: x["priority"]):
        print(f"\n[{entry['priority']}] {entry['name']} ({entry['size_gb']:.0f} GB)")
        print(f"    Node: {entry['target_node']} @ {entry.get('target_host', 'N/A')}")
        result = download_snapshot_remote_prep(entry)
        results[entry["id"]] = result
        print(f"    Status: SSH command generated (run after WoL wake)")

    # Persist status
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    status = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": {k: {kk: str(vv) if isinstance(vv, Path) else vv for kk, vv in v.items()} for k, v in results.items()},
        "gguf_vault": str(GGUF_VAULT),
        "disk_free_gb": probe_disk_free(Path.home()),
    }
    with open(LOG_FILE, "w") as f:
        json.dump(status, f, indent=2)

    return results


if __name__ == "__main__":
    results = run_download_pipeline()
    downloaded = sum(1 for r in results.values() if r.get("status") in ("DOWNLOADED", "ALREADY_EXISTS"))
    print(f"\n✅ Pipeline complete: {downloaded}/{len(results)} models ready")
    print(f"📁 GGUF Vault: {GGUF_VAULT}")
    print(f"📄 Status log: {LOG_FILE}")
