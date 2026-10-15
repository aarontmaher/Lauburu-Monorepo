#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_data_and_memory/hf_sovereign_hub.py
======================================
Sovereign Hugging Face Hub Integration Module for the Lauburu Ecosystem.
Governs offline-first model caching, GGUF/adapter downloads, dataset formatting,
and private repository synchronization.

Strict Security & Sovereign Invariant (Rule 9):
- Tokens are NEVER emitted to stdout, logs, or external cloud prompts.
- All tokens are masked as `hf_...[SECURE]`.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HF Hub] %(levelname)s: %(message)s")
logger = logging.getLogger("HF_Sovereign_Hub")

CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"
TOKEN_FILE = Path.home() / ".cache" / "huggingface" / "token"
LOCAL_VAULT_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf")


def get_sovereign_token() -> Optional[str]:
    """Retrieves HF token from local token file or environment without exposing it."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token and token.strip():
        return token.strip()
    if TOKEN_FILE.is_file():
        try:
            with open(TOKEN_FILE, "r") as f:
                t = f.read().strip()
                if t:
                    return t
        except Exception as e:
            logger.warning(f"Could not read token file: {e}")
    return None


def mask_token(token: Optional[str]) -> str:
    """Masks token for safe display compliant with Rule 9."""
    if not token:
        return "NONE"
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}...{token[-4:]} [REDACTED_SOVEREIGN]"


def check_auth_status() -> Dict[str, Any]:
    """Verifies Hugging Face credentials and permissions."""
    token = get_sovereign_token()
    if not token:
        return {
            "status": "UNAUTHENTICATED",
            "error": "No HF_TOKEN found in ~/.cache/huggingface/token or environment",
            "exit_code": 1
        }
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        user_info = api.whoami()
        return {
            "status": "AUTHENTICATED",
            "username": user_info.get("name"),
            "user_type": user_info.get("type"),
            "token_masked": mask_token(token),
            "orgs": [org.get("name") for org in user_info.get("orgs", [])],
            "exit_code": 0
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "token_masked": mask_token(token),
            "exit_code": 1
        }


def list_cached_models() -> Dict[str, Any]:
    """Inspects locally cached HuggingFace models on disk."""
    if not CACHE_DIR.exists():
        return {"status": "SUCCESS", "cached_models": [], "total_size_gb": 0.0}

    try:
        from huggingface_hub import scan_cache_dir
        report = scan_cache_dir()
        models = []
        for repo in report.repos:
            models.append({
                "repo_id": repo.repo_id,
                "repo_type": repo.repo_type,
                "size_on_disk_gb": round(repo.size_on_disk / (1024**3), 2),
                "nb_files": repo.nb_files,
                "last_modified": str(repo.last_modified)
            })
        return {
            "status": "SUCCESS",
            "cached_models": models,
            "total_size_gb": round(report.size_on_disk / (1024**3), 2),
            "exit_code": 0
        }
    except Exception as e:
        # Fallback to direct directory scan
        dirs = [d.name for d in CACHE_DIR.iterdir() if d.is_dir()]
        return {
            "status": "FALLBACK",
            "raw_cache_dirs": dirs,
            "error": str(e),
            "exit_code": 0
        }


def download_hf_model(
    repo_id: str,
    filename: str,
    target_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Downloads a specific model file (e.g. GGUF or SafeTensors) from HF Hub."""
    token = get_sovereign_token()
    dest_dir = Path(target_dir) if target_dir else LOCAL_VAULT_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download
        logger.info(f"Downloading {filename} from {repo_id}...")
        local_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            token=token,
            local_dir=str(dest_dir),
            local_dir_use_symlinks=False
        )
        return {
            "status": "SUCCESS",
            "repo_id": repo_id,
            "filename": filename,
            "local_path": local_path,
            "size_bytes": os.path.getsize(local_path),
            "exit_code": 0
        }
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return {
            "status": "ERROR",
            "repo_id": repo_id,
            "filename": filename,
            "error": str(e),
            "exit_code": 1
        }


def push_lora_adapter(
    repo_id: str,
    adapter_path: str,
    commit_message: str = "Update specialist LoRA adapter"
) -> Dict[str, Any]:
    """Uploads a trained local LoRA adapter to a private/public Hugging Face repository."""
    token = get_sovereign_token()
    if not token:
        return {"status": "ERROR", "error": "Unauthenticated: Missing HF token", "exit_code": 1}

    p = Path(adapter_path)
    if not p.is_file():
        return {"status": "ERROR", "error": f"Adapter file not found: {adapter_path}", "exit_code": 1}

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        api.create_repo(repo_id=repo_id, exist_ok=True, private=True)
        res = api.upload_file(
            path_or_fileobj=str(p),
            path_in_repo=p.name,
            repo_id=repo_id,
            commit_message=commit_message
        )
        return {
            "status": "SUCCESS",
            "repo_id": repo_id,
            "uploaded_file": p.name,
            "commit_url": str(res),
            "exit_code": 0
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "exit_code": 1}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps(check_auth_status(), indent=2))
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "status":
        print(json.dumps(check_auth_status(), indent=2))
    elif cmd == "cache":
        print(json.dumps(list_cached_models(), indent=2))
    elif cmd == "download":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: hf_sovereign_hub.py download <repo_id> <filename> [target_dir]"}))
            sys.exit(1)
        r_id = sys.argv[2]
        f_name = sys.argv[3]
        t_dir = sys.argv[4] if len(sys.argv) > 4 else None
        print(json.dumps(download_hf_model(r_id, f_name, t_dir), indent=2))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}. Available: status, cache, download"}))
        sys.exit(1)
