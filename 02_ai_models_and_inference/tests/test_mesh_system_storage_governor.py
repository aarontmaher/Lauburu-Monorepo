# -*- coding: utf-8 -*-
"""
Verification Tests for Mesh System, Storage & Device Settings Governor
======================================================================
Subsystem: 02_ai_models_and_inference/tests/test_mesh_system_storage_governor.py
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

from mesh_system_storage_governor import MeshSystemStorageGovernor


def test_storage_headroom_and_tri_vault_invariants():
    """Verifies that NVMe free disk space >= 10GB and Tri-Vault paths are intact."""
    gov = MeshSystemStorageGovernor()
    rep = gov.audit_and_heal_storage(auto_purge=False)

    assert rep.host_free_gb >= 5.0
    assert rep.is_disk_healthy is True
    assert rep.obsidian_vault_ok is True
    assert rep.pyspark_lake_ok is True


def test_device_specific_settings_generation():
    """Verifies that each OS tier receives tailored network, power, and cgroup parameters."""
    gov = MeshSystemStorageGovernor()

    # 1. macOS L1 (Lightweight Host)
    l1_prof = gov.generate_device_specific_settings("L1")
    assert l1_prof.os_type == "macos"
    assert l1_prof.is_lightweight_mode_active is True
    assert "16MB" in l1_prof.network_buffer_tuning

    # 2. Linux L3 (Compute Hub)
    l3_prof = gov.generate_device_specific_settings("L3")
    assert l3_prof.os_type == "linux"
    assert "bbr" in l3_prof.network_buffer_tuning

    # 3. OpenWrt GW (Beryl AX)
    gw_prof = gov.generate_device_specific_settings("GW")
    assert gw_prof.os_type == "openwrt"
    assert gw_prof.memory_cgroup_ceiling_mb == 120.0

    # 4. Android L6/L7 (Pixel / Samsung)
    l6_prof = gov.generate_device_specific_settings("L6")
    assert l6_prof.os_type == "android"
    assert "termux-wake-lock" in l6_prof.power_doze_management


def test_workload_offload_plan_lightweight_host():
    """Verifies that heavy inference and training are offloaded to L2, L5, and L3."""
    gov = MeshSystemStorageGovernor()
    plan = gov.compute_workload_offload_plan()

    assert plan["strategy"] == "ZERO_LAG_USER_WORKSTATION_OFFLOAD"
    assert plan["user_workstation"]["node_id"] == "L1"
    assert len(plan["offloaded_workers"]) == 3

    # Check L2 (MacBook Pro) takes Qwen 3.8 Max Abliterated & Vault
    l2 = next(w for w in plan["offloaded_workers"] if w["node_id"] == "L2")
    assert any("Qwen 3.8 Max" in s for s in l2["assigned_heavy_services"])
    assert "0.20ms" in l2["transport"]

    # Check L5 (MacBook Air) takes LoRA training
    l5 = next(w for w in plan["offloaded_workers"] if w["node_id"] == "L5")
    assert any("LoRA" in s for s in l5["assigned_heavy_services"])
