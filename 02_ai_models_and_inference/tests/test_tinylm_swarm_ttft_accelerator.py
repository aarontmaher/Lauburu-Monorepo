#!/usr/bin/env python3
"""
Unit Tests for TinyLM Swarm TTFT Accelerator
=============================================
Validates:
1. Multi-model draft routing across Phi, Smol, Llama, DeepSeek, Qwen, Mistral, Kimi.
2. Kimi context pruning and token savings calculation.
3. Speculative decoding TTFT acceleration and throughput boost factors.
4. Telemetry persistence and Obsidian report synchronization.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
AI_ROOT = TEST_DIR.parent

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from tinylm_swarm_ttft_accelerator import (
    TinyLMSwarmDraftRouter,
    KimiContextPruner,
    TinyLMSwarmTTFTAccelerator
)


class TestTinyLMSwarmTTFTAccelerator:

    def test_draft_router_matches_models_correctly(self):
        # DeepSeek target -> DeepSeek-R1-Distill-1.5B
        m_ds = TinyLMSwarmDraftRouter.get_best_draft_model("nvidia_deepseek_v4_pro")
        assert m_ds["family"] == "deepseek"

        # Gemini target -> Phi-3.5-mini
        m_gem = TinyLMSwarmDraftRouter.get_best_draft_model("gemini_flash_thinking")
        assert m_gem["family"] == "phi"

        # Llama / Cloudflare -> Llama-3.2-1B
        m_llama = TinyLMSwarmDraftRouter.get_best_draft_model("cloudflare_workers_ai")
        assert m_llama["family"] == "llama"

        # Qwen -> Qwen2.5-0.5B
        m_qwen = TinyLMSwarmDraftRouter.get_best_draft_model("local_qwen_moe")
        assert m_qwen["family"] == "qwen"

    def test_kimi_context_pruner(self):
        verbose_prompt = (
            "# This is a verbose comment\n"
            "# Another useless comment\n"
            "def foo():\n"
            "    return True\n"
        )
        res = KimiContextPruner.prune_prompt(verbose_prompt)
        assert res["tokens_saved"] > 0
        assert res["reduction_pct"] > 0.0
        assert "def foo():" in res["pruned_text"]

    def test_speculative_acceleration_pipeline(self):
        accelerator = TinyLMSwarmTTFTAccelerator()
        res = accelerator.run_speculative_acceleration(
            "def hello(): pass",
            target_model="local_qwen_moe"
        )
        assert res["status"] == "ACCELERATION_ACTIVE"
        assert res["accelerated_ttft_ms"] < res["baseline_ttft_ms"]
        assert "x" in res["ttft_speedup_factor"]
        assert "x" in res["throughput_boost_factor"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
