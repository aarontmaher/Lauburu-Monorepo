#!/usr/bin/env python3
"""
Unit and dynamic transition test battery for Neo NPU Training Regulator.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from neo_npu_training_regulator import NeoNpuTrainingRegulator


class TestNeoNpuTrainingRegulator:

    @pytest.fixture
    def regulator(self):
        return NeoNpuTrainingRegulator(active_threshold_sec=30.0, idle_threshold_sec=60.0)

    def test_down_regulation_when_user_active(self, regulator):
        """Active user (idle <= 30s) must trigger instant down-regulation."""
        with patch.object(regulator, 'get_hid_idle_seconds', return_value=12.0), \
             patch.object(regulator, 'get_frontmost_app', return_value="Xcode"), \
             patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(available=16 * (1024**3))
            
            res = regulator.evaluate_and_regulate()
            assert res["user_state"] == "USER_ACTIVE"
            assert res["regulation_action"] == "DOWN_REGULATE"
            assert res["compute_allocation_pct"] <= 20.0
            assert res["target_batch_size"] == 1
            assert res["target_nice"] == 19
            assert res["target_threads"] == 2
            assert "User active" in res["reason"]

    def test_up_regulation_when_user_idle_and_healthy_ram(self, regulator):
        """Idle user (idle >= 60s) with RAM >= 9.6 GB must trigger maximum up-regulation."""
        with patch.object(regulator, 'get_hid_idle_seconds', return_value=180.0), \
             patch.object(regulator, 'get_frontmost_app', return_value="loginwindow"), \
             patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(available=12 * (1024**3))  # 12 GB free
            
            res = regulator.evaluate_and_regulate()
            assert res["user_state"] == "USER_IDLE"
            assert res["regulation_action"] == "UP_REGULATE"
            assert res["compute_allocation_pct"] == 100.0
            assert res["target_batch_size"] == 128
            assert res["sanctuary_ok"] is True
            assert "Up-regulated" in res["reason"]

    def test_ram_sanctuary_guard_when_user_idle_low_ram(self, regulator):
        """Idle user with RAM < 9.6 GB must enforce Rule 3 sanctuary throttle."""
        with patch.object(regulator, 'get_hid_idle_seconds', return_value=300.0), \
             patch.object(regulator, 'get_frontmost_app', return_value="Finder"), \
             patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(available=3.5 * (1024**3))  # 3.5 GB free (< 9.6 GB)
            
            res = regulator.evaluate_and_regulate()
            assert res["user_state"] == "USER_IDLE"
            assert res["sanctuary_ok"] is False
            assert res["regulation_action"] == "RAM_SANCTUARY_GUARD"
            assert res["compute_allocation_pct"] <= 35.0
            assert res["target_batch_size"] <= 4

    def test_cooldown_intermediate_state(self, regulator):
        """Intermediate idle time (30s < idle < 60s) must maintain moderate compute."""
        with patch.object(regulator, 'get_hid_idle_seconds', return_value=45.0), \
             patch.object(regulator, 'get_frontmost_app', return_value="Terminal"), \
             patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(available=11 * (1024**3))
            
            res = regulator.evaluate_and_regulate()
            assert res["user_state"] == "USER_COOLDOWN"
            assert res["regulation_action"] == "MAINTAIN_INTERMEDIATE"
            assert res["compute_allocation_pct"] == 50.0
            assert res["target_batch_size"] == 16

    def test_pure_npu_inference_latency(self, regulator):
        """NPU decision reflex must complete in < 50ms with zero memory crash."""
        res = regulator.evaluate_and_regulate(force_idle_sec=10.0)
        assert res["npu_systolic_latency_ms"] < 50.0
        assert res["npu_active_tops"] >= 10.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
