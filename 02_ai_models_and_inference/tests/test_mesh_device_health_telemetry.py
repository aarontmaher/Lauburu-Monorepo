# -*- coding: utf-8 -*-
"""
Verification Tests for Mesh Device Health, Thermals & Protected RAM Priority
============================================================================
Subsystem: 02_ai_models_and_inference/tests/test_mesh_device_health_telemetry.py
Lauburu Mesh Ecosystem — 2026
"""

import sys
import pytest
from pathlib import Path

# Add subsystem root to sys.path
_curr_dir = Path(__file__).resolve().parent
_subsystem_root = _curr_dir.parent
if str(_subsystem_root) not in sys.path:
    sys.path.insert(0, str(_subsystem_root))

from mesh_device_health_telemetry import MeshDeviceHealthTelemetryGovernor


def test_protected_ram_fill_order():
    """Verifies that L1 Mac Mini and L6 Pixel 10 Pro are strictly LAST to fill RAM."""
    gov = MeshDeviceHealthTelemetryGovernor()
    
    # 1. Moderate workload (25 GB = 25600 MB): should be absorbed 100% by Tier 1 (L2, L5, L3)
    plan_25g = gov.compute_ram_allocation_waterfill(workload_mb=25600.0)
    
    l1_alloc = next(n for n in plan_25g if n["node_id"] == "L1")
    l6_alloc = next(n for n in plan_25g if n["node_id"] == "L6")
    l2_alloc = next(n for n in plan_25g if n["node_id"] == "L2")
    l5_alloc = next(n for n in plan_25g if n["node_id"] == "L5")

    # L1 and L6 must have 0MB allocated during Tier 1 capacity
    assert l1_alloc["allocated_mb"] == 0.0
    assert l6_alloc["allocated_mb"] == 0.0
    assert l2_alloc["allocated_mb"] > 0.0
    assert l5_alloc["allocated_mb"] > 0.0


def test_device_health_telemetry_polling():
    """Verifies temperature, battery %, and throttling state across devices."""
    gov = MeshDeviceHealthTelemetryGovernor()

    # L1 Mac Mini
    t_l1 = gov.poll_device_telemetry("L1")
    assert t_l1.is_protected_daily_driver is True
    assert t_l1.temp_celsius < 50.0
    assert t_l1.is_throttling is False

    # L6 Pixel 10 Pro
    t_l6 = gov.poll_device_telemetry("L6")
    assert t_l6.is_protected_daily_driver is True
    assert t_l6.battery_pct is not None

    # Router (GW)
    t_gw = gov.poll_device_telemetry("GW", simulated_temp=78.0)
    assert t_gw.is_throttling is True
    assert t_gw.background_ai_cap_mb <= 2.0


def test_ultra_minimal_router_footprint():
    """Verifies that the router is configured for ultra-minimal RAM footprint (<= 2MB)."""
    gov = MeshDeviceHealthTelemetryGovernor()
    gw_spec = gov.NODE_SPECS["GW"]

    assert gw_spec["ai_cap_mb"] <= 2.0
    assert gw_spec["tier"] == 0
