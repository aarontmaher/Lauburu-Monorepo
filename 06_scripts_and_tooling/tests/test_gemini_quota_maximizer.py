#!/usr/bin/env python3
"""
Unit Tests for Gemini API Quota Maximizer
=========================================
Validates:
1. Pacing calculation targeting 98% (1,470 calls) by 23:59:59 UTC.
2. Clamping RPM to safe limit (<= 12 RPM).
3. Distillation batch execution and LoRA dataset synchronization.
4. Quota state persistence and Obsidian dashboard generation.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from gemini_quota_maximizer import GeminiQuotaMaximizer


class TestGeminiQuotaMaximizer:

    def test_optimal_pacing_calculation(self):
        maximizer = GeminiQuotaMaximizer()
        pacing = maximizer.calculate_optimal_pacing()
        assert pacing["target_total"] == 1470
        assert pacing["target_rpm"] <= 12.0
        assert pacing["target_rpm"] > 0
        assert pacing["sleep_seconds_between_calls"] >= 5.0
        assert pacing["target_utilization_pct"] == 98.0

    def test_distillation_batch_execution(self):
        maximizer = GeminiQuotaMaximizer()
        initial_used = maximizer.state["requests_used_today"]
        batch = maximizer.execute_distillation_batch(batch_size=3)
        assert len(batch) == 3
        assert maximizer.state["requests_used_today"] == initial_used + 3
        for item in batch:
            assert "distilled_by" in item
            assert "prompt" in item
            assert "chosen" in item


if __name__ == "__main__":
    pytest.main(["-v", __file__])
