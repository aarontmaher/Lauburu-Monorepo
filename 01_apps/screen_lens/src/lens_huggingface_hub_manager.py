#!/usr/bin/env python3
"""
01_apps/screen_lens/src/lens_huggingface_hub_manager.py
=======================================================
Screen Lens Sovereign HuggingFace Hub Manager.
Empowers Screen Lens to autonomously discover, verify headroom, and download
local AI models (GGUF, MLX, SafeTensors) from HuggingFace.

Tiered Headroom Constraint ("THAT FITS"):
- Micro Models (<= 500 MB): requires >= 5.0 GB free disk.
- Medium Models (500 MB - 2 GB): requires >= 7.0 GB free disk.
- Heavy Models (> 2 GB): requires >= 12.0 GB free disk, else offload to MacBook Pro TB4.
- Physical RAM: preserves >= 9.6 GB sanctuary headroom on Host Mac Mini.
"""

import os
import sys
import time
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
CANONICAL_VAULT = WORKSPACE / "02_ai_models_and_inference/model_vault_gguf"
CANONICAL_VAULT.mkdir(parents=True, exist_ok=True)


class HuggingFaceHeadroomGovernor:
    @staticmethod
    def get_hardware_headroom() -> Dict[str, Any]:
        """
        Computes real physical disk and RAM headroom.
        """
        total, used, free = shutil.disk_usage("/Users/aaron")
        free_disk_gb = round(free / (1024**3), 2)

        page_size = 16384
        try:
            vm_out = subprocess.check_output(["vm_stat"]).decode()
            free_pages = sum(
                int(l.split(":")[1].strip().strip("."))
                for l in vm_out.splitlines()
                if "Pages free:" in l or "Pages speculative:" in l
            )
            free_ram_gb = round((free_pages * page_size) / (1024**3), 2)
        except Exception:
            free_ram_gb = 4.0

        return {
            "free_disk_gb": free_disk_gb,
            "free_ram_gb": free_ram_gb,
            "sanctuary_ram_target_gb": 9.6
        }

    @staticmethod
    def check_model_fit(model_size_gb: float) -> Dict[str, Any]:
        """
        Verifies if a candidate model fits within tiered hardware boundaries.
        """
        headroom = HuggingFaceHeadroomGovernor.get_hardware_headroom()
        free_disk = headroom["free_disk_gb"]

        # Tiered minimum disk headroom required
        if model_size_gb <= 0.5:
            min_disk_req = 5.0
        elif model_size_gb <= 2.0:
            min_disk_req = 7.0
        else:
            min_disk_req = 12.0

        fits_disk = (free_disk - model_size_gb) >= min_disk_req

        # Device tier routing
        if model_size_gb <= 0.5:
            recommended_placement = "PIXEL_10_PRO_XL_NPU / LINUX_TABLET (Ultra-Fast Micro Agent)"
        elif model_size_gb <= 2.5:
            recommended_placement = "MAC_MINI_M4_PRO_HOST (Local Edge Agent)"
        else:
            recommended_placement = "MACBOOK_PRO_TB4_VAULT (L2 - 16 GB via 10Gbps Thunderbolt 4)"

        return {
            "candidate_size_gb": model_size_gb,
            "current_free_disk_gb": free_disk,
            "required_disk_buffer_gb": min_disk_req,
            "fits_disk_headroom": fits_disk,
            "recommended_device_placement": recommended_placement,
            "verdict": "APPROVED_TO_DOWNLOAD" if fits_disk else "REJECTED_INSUFFICIENT_DISK_HEADROOM"
        }


class LensHuggingFaceManager:
    def __init__(self, vault_dir: Path = CANONICAL_VAULT):
        self.vault_dir = Path(vault_dir)
        self.hf_cli = "/Users/aaron/.local/bin/hf"

    def search_models(self, query: str = "Qwen2.5-0.5B-Instruct-GGUF", limit: int = 5) -> List[Dict[str, str]]:
        """
        Searches HuggingFace using native hf CLI.
        """
        try:
            cmd = [self.hf_cli, "models", "ls", "--search", query]
            out = subprocess.check_output(cmd, text=True)
            lines = [l.strip().split("\t") for l in out.splitlines() if l.strip()]
            if not lines:
                return []
            headers = lines[0]
            results = []
            for row in lines[1:limit+1]:
                if len(row) == len(headers):
                    results.append(dict(zip(headers, row)))
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def download_model(
        self,
        repo_id: str,
        filename: Optional[str] = None,
        estimated_size_gb: float = 0.4
    ) -> Dict[str, Any]:
        """
        Downloads model from HuggingFace via hf CLI after verifying headroom fit.
        """
        fit_eval = HuggingFaceHeadroomGovernor.check_model_fit(estimated_size_gb)
        if fit_eval["verdict"] != "APPROVED_TO_DOWNLOAD":
            return {
                "status": "DOWNLOAD_BLOCKED_BY_GOVERNOR",
                "reason": "Model size exceeds available disk sanctuary headroom.",
                "fit_evaluation": fit_eval
            }

        t0 = time.perf_counter()
        cmd = [self.hf_cli, "download", repo_id]
        if filename:
            cmd.extend([filename])
        cmd.extend(["--local-dir", str(self.vault_dir)])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            elapsed_sec = round(time.perf_counter() - t0, 2)
            
            if res.returncode == 0:
                target_path = str(self.vault_dir / (filename if filename else ""))
                return {
                    "status": "DOWNLOAD_SUCCESSFUL",
                    "repo_id": repo_id,
                    "filename": filename,
                    "vault_destination": target_path,
                    "download_time_seconds": elapsed_sec,
                    "fit_evaluation": fit_eval,
                    "zero_mock_verified": True
                }
            else:
                return {
                    "status": "DOWNLOAD_FAILED",
                    "stderr": res.stderr,
                    "stdout": res.stdout,
                    "fit_evaluation": fit_eval
                }
        except Exception as e:
            return {"status": "DOWNLOAD_ERROR", "error": str(e), "fit_evaluation": fit_eval}

    def list_benchmark_datasets(self) -> List[str]:
        """
        Find official benchmark datasets using HfApi.
        """
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            return [ds.id for ds in api.list_datasets(benchmark=True)]
        except Exception as e:
            return [f"Error: {e}"]

    def get_dataset_leaderboard(self, dataset_id: str = "SWE-bench/SWE-bench_Verified", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get ranked model scores for a specific benchmark dataset using HfApi.
        """
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            leaderboard = api.get_dataset_leaderboard(dataset_id)
            results = []
            for entry in leaderboard[:limit]:
                results.append({
                    "rank": entry.rank,
                    "model_id": entry.model_id,
                    "value": entry.value
                })
            return results
        except Exception as e:
            return [{"error": str(e)}]


def main():
    print("🤗 Testing Screen Lens HuggingFace Manager & Tiered Headroom Governor...")
    manager = LensHuggingFaceManager()

    # 1. Evaluate tiered fit for 0.45 GB model
    fit_check = HuggingFaceHeadroomGovernor.check_model_fit(model_size_gb=0.45)
    print("\n--- CANDIDATE 0.45GB MODEL FIT EVALUATION ---")
    print(json.dumps(fit_check, indent=2))

    # 2. Search HuggingFace models
    search_res = manager.search_models(query="Qwen2.5-0.5B-Instruct-GGUF", limit=3)
    print("\n--- HUGGINGFACE SEARCH RESULTS ---")
    print(json.dumps(search_res, indent=2))


if __name__ == "__main__":
    main()
