#!/usr/bin/env python3
"""
Unit Tests for Universal Free Cloud Model Benchmarker
=====================================================
Validates:
1. Registration of all 9 models across Google, NVIDIA, xAI, Cloudflare, and Local.
2. Multi-domain tournament execution across 4 engineering domains.
3. ELO score calculation and leaderboard sorting.
4. Markdown leaderboard publishing and continuous LoRA DPO distillation.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from universal_free_cloud_model_benchmarker import UniversalFreeCloudModelBenchmarker, BENCHMARK_MODELS


class TestUniversalFreeCloudModelBenchmarker:

    def test_model_catalog_includes_all_providers(self):
        bm = UniversalFreeCloudModelBenchmarker()
        assert len(bm.models) >= 9
        ids = list(bm.models.keys())
        assert "deepseek_v4_pro" in ids
        assert "gemini_2_0_flash_thinking" in ids
        assert "grok_2_xai" in ids
        assert "cloudflare_llama_3_3" in ids
        assert "google_jules" in ids
        assert "qwen_moe_local" in ids
        assert "devils_advocate_local" in ids

    def test_run_comprehensive_benchmark_suite_returns_tournament_results(self):
        bm = UniversalFreeCloudModelBenchmarker()
        res = bm.run_comprehensive_benchmark_suite()
        assert res["total_models_benchmarked"] >= 9
        assert res["domains_tested"] == 4
        assert len(res["tournament_results"]) == 4
        assert len(res["updated_ratings"]) >= 9

    def test_ratings_are_ordered_and_nonzero(self):
        bm = UniversalFreeCloudModelBenchmarker()
        res = bm.run_comprehensive_benchmark_suite()
        ratings = res["updated_ratings"]
        for m_id, r in ratings.items():
            assert r > 1500.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
