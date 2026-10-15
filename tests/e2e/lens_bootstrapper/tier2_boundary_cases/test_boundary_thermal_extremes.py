#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis - Thermal Extremes and Transitions.
Stresses thermal adaptation logic against:
1. Valid thermal boundary states: 0 (Nominal), 1 (Fair), 2 (Serious), 3 (Critical)
2. Negative or extreme out-of-range thermal values (-1, 99)
3. Rapid thermal oscillation / state flapping
4. Critical saturation (Level 3 quarantine)
5. Hysteresis and recovery to nominal state
"""

import sys
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from tier1_feature_coverage.test_f11_f13_prima_sharding import PrimaMeshAllocator


class TestBoundaryThermalExtremes(unittest.TestCase):
    """Boundary testing for thermal level transitions and extremes."""

    def test_b3_01_all_discrete_thermal_levels(self):
        """B3.1: Verify allocation preserves total layers across all valid thermal states (0..3)."""
        for level in [0, 1, 2, 3]:
            alloc = PrimaMeshAllocator.allocate_layers(total_layers=64, thermal_overrides={"L1_mac_mini": level})
            total = sum(n["layers"] for n in alloc.values())
            self.assertEqual(total, 64, f"Layer conservation failed at thermal level {level}")

    def test_b3_02_negative_or_extreme_thermal_levels(self):
        """B3.2: Verify invalid negative or extreme thermal integers are safely handled without crash."""
        # Extreme value 99 should be treated as maximum throttling (level >= 3)
        alloc_extreme = PrimaMeshAllocator.allocate_layers(total_layers=64, thermal_overrides={"L1_mac_mini": 99})
        total = sum(n["layers"] for n in alloc_extreme.values())
        self.assertEqual(total, 64)
        # Throttled node should receive 0 or minimal layers
        self.assertLessEqual(alloc_extreme["L1_mac_mini"]["layers"], 4)

    def test_b3_03_rapid_thermal_flapping_simulation(self):
        """B3.3: Verify rapid alternating thermal spikes (0 -> 2 -> 0 -> 2) preserve layer conservation."""
        sequence = [0, 2, 0, 2, 1, 3, 0]
        for step, level in enumerate(sequence):
            alloc = PrimaMeshAllocator.allocate_layers(total_layers=64, thermal_overrides={"L1_mac_mini": level})
            total = sum(n["layers"] for n in alloc.values())
            self.assertEqual(total, 64, f"Flap step {step} (level={level}) failed layer conservation")

    def test_b3_04_level_3_critical_quarantine(self):
        """B3.4: Verify Level 3 (Critical) forces node layer allocation to zero or near-zero."""
        alloc = PrimaMeshAllocator.allocate_layers(total_layers=64, thermal_overrides={"L1_mac_mini": 3})
        # L1 should receive 0 layers (or minimal fallback) under critical throttling
        l1_layers = alloc["L1_mac_mini"]["layers"]
        self.assertLessEqual(l1_layers, 2, f"Critical node must be quarantined, got {l1_layers} layers")

    def test_b3_05_multi_node_simultaneous_thermal_spike(self):
        """B3.5: Verify simultaneous thermal spikes on multiple nodes reallocates to remaining healthy nodes."""
        # L1 and L1b both spike to level 2
        alloc = PrimaMeshAllocator.allocate_layers(
            total_layers=64,
            thermal_overrides={"L1_mac_mini": 2, "L1b_mac_mini_m2": 2}
        )
        total = sum(n["layers"] for n in alloc.values())
        self.assertEqual(total, 64)
        # L5 (MacBook Air M4) should absorb majority of layers
        l5_layers = alloc["L5_mac_air_m4"]["layers"]
        self.assertGreater(l5_layers, 20, "L5 should absorb layers when L1 and L1b are hot")


if __name__ == "__main__":
    unittest.main()
