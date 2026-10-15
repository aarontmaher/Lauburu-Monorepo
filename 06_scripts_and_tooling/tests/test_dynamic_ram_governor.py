#!/usr/bin/env python3
"""
06_scripts_and_tooling/tests/test_dynamic_ram_governor.py
=========================================================
Unit & Integration Test Suite for Dynamic RAM & VRAM Governor.
Validates:
1. Strict Host RAM safety ceiling (<85.0% baseline) and warning threshold (80.0%).
2. Adaptive User-Aware Dynamic VRAM Elasticity (IOHIDSystem user-presence):
   - Interactive Mode (idle < 60s): 75.0% ceiling, worker throttling (0.5 / 0.2).
   - Maximum Burst Mode (idle >= 60s): 88.0% ceiling, 1.0 unthrottled burst.
3. Memory pressure state probing and throttle factor calculation.
4. Autonomous cache reclamation (gc.collect, torch.mps.empty_cache, OS drop_caches).
5. Dynamic TB4 DMA layer offload triggers (169.254.187.138 / bridge0).
6. Background worker throttle notification callbacks.
7. Real-time JSON status file synchronization.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

AUTOMATION_DIR = PROJECT_ROOT / "06_scripts_and_tooling" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from dynamic_ram_governor import (
    DynamicRamGovernor,
    MemoryPressureLevel,
    OperatingMode,
    get_memory_pressure_state,
    purge_buffers_and_cache,
    trigger_tb4_offload,
    STATUS_FILE,
)


class TestDynamicRamGovernorThresholdsAndMetrics:
    """Validates governor initialization, thresholds, and metric calculations."""

    def test_default_thresholds_initialization(self):
        gov = DynamicRamGovernor()
        assert gov.warn_pct == 80.0
        assert gov.crit_pct == 85.0
        assert gov.tb4_peer_ip == "169.254.187.138"
        assert gov.reclaim_count == 0
        assert gov.tb4_offload_count == 0
        assert len(gov.default_offload_layers) > 0

    def test_custom_thresholds_initialization(self):
        gov = DynamicRamGovernor(
            warning_threshold_pct=75.0,
            critical_threshold_pct=82.0,
            host_total_gb=24.0,
            tb4_peer_ip="169.254.114.190",
            default_offload_layers=[16, 17, 18, 19, 20],
            idle_threshold_sec=30.0
        )
        assert gov.warn_pct == 75.0
        assert gov.crit_pct == 82.0
        assert gov.host_total_gb == 24.0
        assert gov.tb4_peer_ip == "169.254.114.190"
        assert gov.default_offload_layers == [16, 17, 18, 19, 20]
        assert gov.idle_threshold_sec == 30.0


class TestAdaptiveUserPresenceElasticity:
    """Validates Adaptive User-Aware Elasticity (Interactive vs Burst Mode)."""

    def test_interactive_mode_evaluation(self):
        gov = DynamicRamGovernor()
        # User active (idle 5 seconds < 60s)
        is_active, mode, ceiling, warn = gov.evaluate_user_presence(idle_seconds=5.0)
        assert is_active is True
        assert mode == OperatingMode.INTERACTIVE_MODE
        assert ceiling == 75.0
        assert warn == 70.0

    def test_maximum_burst_mode_evaluation(self):
        gov = DynamicRamGovernor()
        # User idle (idle 120 seconds >= 60s)
        is_active, mode, ceiling, warn = gov.evaluate_user_presence(idle_seconds=120.0)
        assert is_active is False
        assert mode == OperatingMode.MAXIMUM_BURST_MODE
        assert ceiling == 88.0
        assert warn == 82.0

    def test_throttle_factor_interactive_mode(self):
        gov = DynamicRamGovernor()
        # In interactive mode:
        # Load 50% (< 70%) -> throttle factor = 0.5 (reserve CPU for desktop UI)
        assert gov.compute_throttle_factor(50.0, is_user_active=True, eff_warn=70.0, eff_crit=75.0) == 0.5
        # Load 72% (70-75%) -> throttle factor = 0.2
        assert gov.compute_throttle_factor(72.0, is_user_active=True, eff_warn=70.0, eff_crit=75.0) == 0.2
        # Load 78% (>= 75%) -> throttle factor = 0.1
        assert gov.compute_throttle_factor(78.0, is_user_active=True, eff_warn=70.0, eff_crit=75.0) == 0.1

    def test_throttle_factor_burst_mode(self):
        gov = DynamicRamGovernor()
        # In burst mode:
        # Load 50% (< 82%) -> throttle factor = 1.0 (Full 100% burst)
        assert gov.compute_throttle_factor(50.0, is_user_active=False, eff_warn=82.0, eff_crit=88.0) == 1.0
        # Load 84% (82-88%) -> throttle factor = 0.5 - 0.7
        tf = gov.compute_throttle_factor(84.0, is_user_active=False, eff_warn=82.0, eff_crit=88.0)
        assert 0.4 <= tf <= 0.8
        # Load 90% (>= 88%) -> throttle factor = 0.1
        assert gov.compute_throttle_factor(90.0, is_user_active=False, eff_warn=82.0, eff_crit=88.0) == 0.1

    def test_live_iohid_query(self):
        gov = DynamicRamGovernor()
        idle_sec = gov.get_user_idle_seconds()
        assert idle_sec >= 0.0


class TestDynamicRamGovernorStateEvaluation:
    """Validates memory pressure state evaluation with mock overrides."""

    def test_get_memory_pressure_state_schema(self):
        gov = DynamicRamGovernor()
        state = gov.get_memory_pressure_state()
        assert "ram_used_pct" in state
        assert "vram_used_pct" in state
        assert "headroom_gb" in state
        assert "throttle_factor" in state
        assert "state" in state
        assert "governor_status" in state
        assert "operating_mode" in state
        assert "is_user_active" in state
        assert "effective_safety_ceiling_pct" in state
        assert "effective_warning_pct" in state

    def test_state_interactive_healthy(self):
        gov = DynamicRamGovernor()
        gov._mock_idle_sec = 10.0  # Interactive mode
        gov._mock_memory_override = {
            "total_gb": 24.0,
            "used_gb": 12.0,
            "free_gb": 12.0,
            "headroom_gb": 12.0,
            "ram_used_pct": 50.0,
            "vram_used_pct": 50.0,
        }
        state = gov.get_memory_pressure_state()
        assert state["is_user_active"] is True
        assert state["operating_mode"] == OperatingMode.INTERACTIVE_MODE
        assert state["effective_safety_ceiling_pct"] == 75.0
        assert state["state"] == MemoryPressureLevel.HEALTHY
        assert state["throttle_factor"] == 0.5

    def test_state_burst_healthy(self):
        gov = DynamicRamGovernor()
        gov._mock_idle_sec = 300.0  # Burst mode
        gov._mock_memory_override = {
            "total_gb": 24.0,
            "used_gb": 12.0,
            "free_gb": 12.0,
            "headroom_gb": 12.0,
            "ram_used_pct": 50.0,
            "vram_used_pct": 50.0,
        }
        state = gov.get_memory_pressure_state()
        assert state["is_user_active"] is False
        assert state["operating_mode"] == OperatingMode.MAXIMUM_BURST_MODE
        assert state["effective_safety_ceiling_pct"] == 88.0
        assert state["state"] == MemoryPressureLevel.HEALTHY
        assert state["throttle_factor"] == 1.0


class TestReclamationAndOffloadOperations:
    """Validates buffer purging, TB4 offload dispatch, and governance actions."""

    def test_purge_buffers_and_cache(self):
        gov = DynamicRamGovernor()
        init_reclaim = gov.reclaim_count
        ops = gov.purge_buffers_and_cache()
        assert ops >= 1
        assert gov.reclaim_count == init_reclaim + 1

    def test_trigger_tb4_offload_dispatch(self):
        gov = DynamicRamGovernor()
        init_offloads = gov.tb4_offload_count
        success = gov.trigger_tb4_offload(target_layers=[12, 13, 14, 15], target_node_ip="169.254.187.138")
        assert success is True
        assert gov.tb4_offload_count == init_offloads + 1

    def test_worker_throttle_callback_notification(self):
        gov = DynamicRamGovernor()
        received_factors = []

        def worker_callback(factor: float):
            received_factors.append(factor)

        gov.register_worker_throttle_callback(worker_callback)
        gov.notify_workers_throttle(0.5)
        gov.notify_workers_throttle(0.1)

        assert received_factors == [0.5, 0.1]

    def test_check_and_govern_interactive_critical_at_76_pct(self):
        gov = DynamicRamGovernor()
        gov._mock_idle_sec = 5.0  # Interactive mode -> ceiling 75.0%
        gov._mock_memory_override = {
            "total_gb": 24.0,
            "used_gb": 18.24,
            "free_gb": 5.76,
            "headroom_gb": 5.76,
            "ram_used_pct": 76.0,
            "vram_used_pct": 76.0,
        }
        state = gov.check_and_govern()
        assert state["operating_mode"] == OperatingMode.INTERACTIVE_MODE
        assert state["governor_status"] == MemoryPressureLevel.CRITICAL_HEADROOM
        assert state["last_action"] == "EMERGENCY_PURGE_THROTTLE_AND_TB4_OFFLOAD"
        assert gov.reclaim_count >= 1
        assert gov.tb4_offload_count >= 1

    def test_check_and_govern_burst_healthy_at_76_pct(self):
        gov = DynamicRamGovernor()
        gov._mock_idle_sec = 200.0  # Burst mode -> ceiling 88.0%, warn 82.0%
        gov._mock_memory_override = {
            "total_gb": 24.0,
            "used_gb": 18.24,
            "free_gb": 5.76,
            "headroom_gb": 5.76,
            "ram_used_pct": 76.0,
            "vram_used_pct": 76.0,
        }
        state = gov.check_and_govern()
        assert state["operating_mode"] == OperatingMode.MAXIMUM_BURST_MODE
        assert state["governor_status"] == MemoryPressureLevel.HEALTHY
        assert state["last_action"] == "NONE"

    def test_status_file_written_and_valid(self):
        gov = DynamicRamGovernor()
        gov.check_and_govern()
        assert STATUS_FILE.exists()
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "ram_used_pct" in data
        assert "governor_status" in data
        assert "operating_mode" in data
        assert "last_action" in data


class TestModuleLevelInterfaceContracts:
    """Validates PROJECT.md interface contract functions."""

    def test_module_get_memory_pressure_state(self):
        state = get_memory_pressure_state()
        assert isinstance(state, dict)
        assert "ram_used_pct" in state
        assert "throttle_factor" in state
        assert "state" in state

    def test_module_purge_buffers_and_cache(self):
        ops = purge_buffers_and_cache()
        assert isinstance(ops, int)
        assert ops >= 1

    def test_module_trigger_tb4_offload(self):
        success = trigger_tb4_offload([12, 13, 14], "169.254.187.138")
        assert success is True
