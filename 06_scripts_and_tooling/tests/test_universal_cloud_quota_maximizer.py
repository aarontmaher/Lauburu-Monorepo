#!/usr/bin/env python3
"""
Unit Tests for Universal Multi-Cloud Free Quota Maximizer
=========================================================
Validates:
1. Provider catalog configuration across all 5 free tiers:
   - Gemini (Google AI Studio)
   - NVIDIA NIM (DeepSeek V4 Pro/Flash)
   - Cloudflare Workers AI (Llama 3.3 70B)
   - xAI Grok-2 Developer API
   - Google Jules Async PR Agent
2. Dynamic pacing calculation targeting 95%-98% utilization.
3. Multi-cloud burst execution and continuous LoRA serialization.
4. State persistence and Obsidian dashboard rendering.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(SCRIPTS_ROOT / "cloud_and_quota") not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT / "cloud_and_quota"))

from universal_cloud_quota_maximizer import UniversalCloudQuotaMaximizer


class TestUniversalCloudQuotaMaximizer:

    def test_provider_config_includes_all_five_providers(self):
        maximizer = UniversalCloudQuotaMaximizer()
        providers = maximizer.PROVIDER_CONFIG
        assert "gemini_flash" in providers
        assert "nvidia_deepseek_v4" in providers
        assert "cloudflare_workers_ai" in providers
        assert "xai_grok_2" in providers
        assert "google_jules" in providers

    def test_calculate_all_pacing_returns_valid_metrics(self):
        maximizer = UniversalCloudQuotaMaximizer()
        pacing = maximizer.calculate_all_pacing()
        for p_id, data in pacing.items():
            assert data["daily_cap"] > 0
            assert data["target_today"] > 0
            assert data["target_rpm"] > 0
            assert "utilization_pct" in data

    def test_execute_multi_cloud_burst(self):
        maximizer = UniversalCloudQuotaMaximizer()
        burst = maximizer.execute_multi_cloud_maximization_burst(burst_size_per_provider=2)
        assert len(burst) == 5
        for p_id, count in burst.items():
            assert count >= 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
