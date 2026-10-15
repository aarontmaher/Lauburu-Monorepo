#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Empirical Tests for Device RAM Tiering & Multi-App Model Allocation
"""

import sys
import pytest
from pathlib import Path

INFERENCE_DIR = Path(__file__).resolve().parents[1]
if str(INFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(INFERENCE_DIR))

from device_ram_tier_model_allocator import DeviceModelAllocator, RAM_TIERS


def test_ram_tier_profiles_loaded():
    assert len(RAM_TIERS) == 5
    assert "4GB" in RAM_TIERS
    assert "12GB" in RAM_TIERS
    assert "16GB" in RAM_TIERS


def test_4gb_mobile_tier_allocations():
    tier_key = "4GB"
    for app in DeviceModelAllocator.APPS:
        alloc = DeviceModelAllocator.get_optimal_allocation(tier_key, app["id"])
        # Invariant: 4GB tier must NEVER exceed 1.3 GB AI RAM
        assert alloc.total_ai_ram_gb <= 1.30
        assert alloc.headroom_remaining_gb > 0.0
        assert alloc.status == "OPTIMAL_CERTIFIED"


def test_8gb_tablet_tier_allocations():
    tier_key = "8GB"
    alloc_lens = DeviceModelAllocator.get_optimal_allocation(tier_key, "screen_lens_vision")
    assert "3B" in alloc_lens.primary_model
    assert alloc_lens.total_ai_ram_gb <= 4.50


def test_12gb_mobile_tier_allocations():
    tier_key = "12GB"
    alloc_flutter = DeviceModelAllocator.get_optimal_allocation(tier_key, "flutter_webgpu_hub")
    assert "7B" in alloc_flutter.primary_model or "1.5B" in alloc_flutter.primary_model
    assert alloc_flutter.total_ai_ram_gb <= 7.50


def test_16gb_pro_mobile_tier_allocations():
    tier_key = "16GB"
    alloc_lens = DeviceModelAllocator.get_optimal_allocation(tier_key, "screen_lens_vision")
    # 16GB tier gets full 7B Multimodal Screen Lens!
    assert "7B" in alloc_lens.primary_model
    assert alloc_lens.total_ai_ram_gb <= 11.20
    assert alloc_lens.headroom_remaining_gb >= 5.0 # Plenty of headroom for OS + Camera


def test_app_functionality_simulation():
    res = DeviceModelAllocator.test_app_functionality("4GB", "flutter_webgpu_hub")
    assert res["zero_crash_verified"] is True
    assert res["memory_safety_invariant_met"] is True
    assert "ecg_sample" in res["test_payload_processed"]


def test_full_matrix_generation_and_obsidian_sync():
    matrix = DeviceModelAllocator.generate_full_matrix_report()
    assert len(matrix) == 5
    for tier, apps in matrix.items():
        assert len(apps) == 4


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
