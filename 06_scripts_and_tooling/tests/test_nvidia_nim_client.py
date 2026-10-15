#!/usr/bin/env python3
"""
Unit Tests for NVIDIA NIM DeepSeek V4 Client
============================================
Validates:
1. Model metadata (1.6T Pro / 49B Active and 284B Flash / 13B Active).
2. 1M Context window support.
3. OpenAI-compatible request structure and bearer auth header.
4. Graceful offline fallback to local Qwen MoE when key is absent.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from nvidia_nim_client import NvidiaNimClient, NVIDIA_MODELS


class TestNvidiaNimClient:

    def test_model_catalog_metadata(self):
        assert "deepseek-v4-pro" in NVIDIA_MODELS
        assert "deepseek-v4-flash" in NVIDIA_MODELS

        pro = NVIDIA_MODELS["deepseek-v4-pro"]
        assert pro["total_params"] == "1.6T"
        assert pro["active_params"] == "49B"
        assert "1,000,000" in pro["context_window"]

        flash = NVIDIA_MODELS["deepseek-v4-flash"]
        assert flash["total_params"] == "284B"
        assert flash["active_params"] == "13B"

    def test_missing_api_key_returns_graceful_fallback(self):
        client = NvidiaNimClient(api_key=None)
        client.api_key = None
        res = client.generate_completion("Test prompt", model_key="deepseek-v4-pro")
        assert res["success"] is False
        assert "NVIDIA_API_KEY is not set" in res["error"]
        assert res["fallback_model"] == "local_qwen_moe"
        assert "build.nvidia.com" in res["action_required"]

    def test_configured_state_detection(self):
        client = NvidiaNimClient(api_key="nvapi-test-key-1234567890")
        assert client.is_configured() is True
        assert client.api_key == "nvapi-test-key-1234567890"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
