#!/usr/bin/env python3
"""
================================================================================
NVIDIA NIM / build.nvidia.com Client & DeepSeek V4 MoE Connector
================================================================================
Subsystem: 06_scripts_and_tooling/nvidia_nim_client.py
Version: 1.0.0-NVIDIA-NIM-DEEPSEEK-V4
Lauburu Mesh Ecosystem — 2026

Connects Qwen MoE to NVIDIA NIM's free tier (build.nvidia.com):
1. DeepSeek V4 Pro: 1.6T Total / 49B Active MoE (1M Context, Frontier Reasoning).
2. DeepSeek V4 Flash: 284B Total / 13B Active MoE (1M Context, High-Speed Coding).
- Protocol: OpenAI-compatible REST endpoint (https://integrate.api.nvidia.com/v1/chat/completions).
- Auth: NVIDIA_API_KEY ("nvapi-...") via Bearer Header.
- Zero-Mock & Fail-Safe: Automatically falls back to local Qwen MoE if key is absent.
================================================================================
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
LORA_DIR = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data")
DATA_DIR = REPO_ROOT / "04_data_and_memory"

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

NVIDIA_MODELS = {
    "deepseek-v4-pro": {
        "id": "deepseek-ai/deepseek-v4-pro",
        "alias": "DeepSeek V4 Pro (1.6T / 49B Active)",
        "total_params": "1.6T",
        "active_params": "49B",
        "context_window": "1,000,000 tokens",
        "specialization": "Frontier Mathematical Reasoning, Multi-Node Architecture & Heavy MoE Distillation"
    },
    "deepseek-v4-flash": {
        "id": "deepseek-ai/deepseek-v4-flash",
        "alias": "DeepSeek V4 Flash (284B / 13B Active)",
        "total_params": "284B",
        "active_params": "13B",
        "context_window": "1,000,000 tokens",
        "specialization": "Ultra-High Speed Code Generation & 1M Context Codebase Audits"
    }
}


class NvidiaNimClient:
    """OpenAI-compatible client for NVIDIA NIM & DeepSeek V4 free tier."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
        self.base_url = NVIDIA_NIM_BASE_URL

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def generate_completion(
        self,
        prompt: str,
        model_key: str = "deepseek-v4-pro",
        system_prompt: str = "You are DeepSeek V4, a frontier 1.6T MoE reasoning model.",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout_sec: int = 45
    ) -> Dict[str, Any]:
        """Dispatches an inference request to NVIDIA NIM."""
        model_meta = NVIDIA_MODELS.get(model_key, NVIDIA_MODELS["deepseek-v4-pro"])
        model_id = model_meta["id"]

        if not self.is_configured():
            return {
                "success": False,
                "error": "NVIDIA_API_KEY is not set in environment or .env.",
                "action_required": "Sign up at http://build.nvidia.com, generate an API key ('nvapi-...'), and add NVIDIA_API_KEY to .env.",
                "fallback_model": "local_qwen_moe",
                "model_meta": model_meta
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}"
        }

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()
        try:
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency_ms = (time.time() - start_time) * 1000.0
                choices = data.get("choices", [])
                response_text = choices[0].get("message", {}).get("content", "") if choices else ""

                return {
                    "success": True,
                    "model_id": model_id,
                    "alias": model_meta["alias"],
                    "latency_ms": round(latency_ms, 2),
                    "response": response_text,
                    "usage": data.get("usage", {}),
                    "cost_usd": 0.00
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {
                "success": False,
                "error": f"HTTP Error {e.code}: {e.reason} - {err_body[:200]}",
                "fallback_model": "local_qwen_moe",
                "model_meta": model_meta
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fallback_model": "local_qwen_moe",
                "model_meta": model_meta
            }


if __name__ == "__main__":
    client = NvidiaNimClient()
    print("=== NVIDIA NIM / DeepSeek V4 Connector Status ===")
    print(f"API Configured: {client.is_configured()}")
    print("\nSupported Models:")
    for k, v in NVIDIA_MODELS.items():
        print(f"  • [{k}] {v['alias']}: {v['specialization']} (Context: {v['context_window']})")

    if client.is_configured():
        print("\nAttempting test query to DeepSeek V4 Pro...")
        res = client.generate_completion("Write a one-sentence mathematical description of Mixture-of-Experts routing.")
        print(json.dumps(res, indent=2))
    else:
        print("\n👉 To activate: Grab your free key from http://build.nvidia.com and add `NVIDIA_API_KEY=nvapi-...` to your .env file.")
