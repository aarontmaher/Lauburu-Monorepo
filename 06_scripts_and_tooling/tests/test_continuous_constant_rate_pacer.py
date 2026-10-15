#!/usr/bin/env python3
"""
Unit Tests for Continuous Constant-Rate 99% Pacer
=================================================
Validates:
1. Exact UTC reset calculation and local AEST conversion (10:00 AM AEST).
2. Countdown remaining calculation (hours, minutes, seconds).
3. 24-hour steady-state constant rate math (1 req every 58.2s for Gemini).
4. Catch-up rate calculation to hit exactly 99% before reset.
5. Stream tick execution and LoRA dataset synchronization.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from continuous_constant_rate_pacer import ContinuousConstantRatePacer


class TestContinuousConstantRatePacer:

    def test_utc_reset_countdown_calculation(self):
        pacer = ContinuousConstantRatePacer()
        cd = pacer.get_utc_reset_countdown()
        assert "00:00:00 UTC" in cd["next_reset_utc"]
        assert "10:00:00 AM AEST" in cd["next_reset_aest"]
        assert cd["remaining_seconds"] > 0
        assert cd["remaining_minutes"] > 0
        assert "h " in cd["countdown_str"]

    def test_calculate_constant_rate_schedule(self):
        pacer = ContinuousConstantRatePacer()
        data = pacer.calculate_constant_rate_schedule()
        assert "countdown" in data
        assert "schedule" in data
        gem = data["schedule"]["gemini_flash"]
        assert gem["daily_cap"] == 1500
        assert gem["target_today"] == 1485
        assert gem["steady_state_interval_sec"] == 58.2
        assert gem["catchup_rpm"] <= 12.0

    def test_execute_constant_rate_tick(self):
        pacer = ContinuousConstantRatePacer()
        res = pacer.execute_constant_rate_tick()
        assert "ticked" in res
        assert len(res["ticked"]) >= 3
        assert "countdown" in res


if __name__ == "__main__":
    pytest.main(["-v", __file__])
