#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis - High VM Pressure and RAM Sanctuary Headroom.
Stresses Mach virtual memory pressure transitions and Rule 3 sanctuary enforcement:
1. VM Pressure Level 1 (Normal) - Nominal operation
2. VM Pressure Level 2 (Warning) - Pre-emptive throttle warnings
3. VM Pressure Level 3 (Critical) - Emergency memory offload trigger
4. Available RAM below Rule 3 sanctuary limit (< 4.8 GB)
5. Available RAM below critical threshold (< 500 MB)
"""

import sys
import unittest
from pathlib import Path
from typing import Dict, Any

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import query_darwin_mach_memory


def evaluate_memory_governance(available_bytes: int, vm_pressure_level: int) -> Dict[str, Any]:
    """Evaluates memory state against Rule 3 4.8 GB sanctuary and kernel VM pressure."""
    sanctuary_bytes = int(4.8 * (1024 ** 3))
    critical_min_bytes = int(500 * (1024 ** 2))

    status = {
        "allow_local_large_model": False,
        "allow_local_tinylm": False,
        "trigger_emergency_offload": False,
        "sanctuary_violated": False,
        "vm_pressure_state": "NORMAL"
    }

    if vm_pressure_level == 1:
        status["vm_pressure_state"] = "NORMAL"
    elif vm_pressure_level == 2:
        status["vm_pressure_state"] = "WARNING"
    elif vm_pressure_level >= 3:
        status["vm_pressure_state"] = "CRITICAL"
        status["trigger_emergency_offload"] = True

    if available_bytes < sanctuary_bytes:
        status["sanctuary_violated"] = True
        status["allow_local_large_model"] = False
    else:
        status["allow_local_large_model"] = (vm_pressure_level == 1)

    if available_bytes < critical_min_bytes or vm_pressure_level >= 3:
        status["trigger_emergency_offload"] = True
        status["allow_local_tinylm"] = False
    else:
        status["allow_local_tinylm"] = True

    return status


class TestBoundaryHighVmPressure(unittest.TestCase):
    """Boundary testing for VM pressure levels and memory sanctuary."""

    def test_b4_01_nominal_pressure_level_1(self):
        """B4.1: Level 1 (Normal) with healthy RAM permits local inference and has no offload signal."""
        # 8 GB available, Level 1
        res = evaluate_memory_governance(8 * 1024**3, vm_pressure_level=1)
        self.assertEqual(res["vm_pressure_state"], "NORMAL")
        self.assertFalse(res["trigger_emergency_offload"])
        self.assertFalse(res["sanctuary_violated"])
        self.assertTrue(res["allow_local_large_model"])

    def test_b4_02_warning_pressure_level_2(self):
        """B4.2: Level 2 (Warning) suppresses heavy models but permits lightweight TinyLM."""
        # 6 GB available, Level 2
        res = evaluate_memory_governance(6 * 1024**3, vm_pressure_level=2)
        self.assertEqual(res["vm_pressure_state"], "WARNING")
        self.assertFalse(res["trigger_emergency_offload"])
        self.assertFalse(res["allow_local_large_model"])
        self.assertTrue(res["allow_local_tinylm"])

    def test_b4_03_critical_pressure_level_3(self):
        """B4.3: Level 3 (Critical) immediately triggers emergency offload signal."""
        # 3 GB available, Level 3
        res = evaluate_memory_governance(3 * 1024**3, vm_pressure_level=3)
        self.assertEqual(res["vm_pressure_state"], "CRITICAL")
        self.assertTrue(res["trigger_emergency_offload"])
        self.assertFalse(res["allow_local_tinylm"])

    def test_b4_04_sanctuary_boundary_headroom(self):
        """B4.4: Available RAM at 4.79 GB triggers sanctuary violation flag (Rule 3)."""
        just_below = int(4.79 * 1024**3)
        res = evaluate_memory_governance(just_below, vm_pressure_level=1)
        self.assertTrue(res["sanctuary_violated"])
        self.assertFalse(res["allow_local_large_model"])

        just_above = int(4.85 * 1024**3)
        res_above = evaluate_memory_governance(just_above, vm_pressure_level=1)
        self.assertFalse(res_above["sanctuary_violated"])
        self.assertTrue(res_above["allow_local_large_model"])

    def test_b4_05_critical_headroom_under_500mb(self):
        """B4.5: Available RAM < 500 MB forces emergency offload regardless of kernel VM level."""
        low_ram = int(350 * 1024**2)  # 350 MB
        res = evaluate_memory_governance(low_ram, vm_pressure_level=1)
        self.assertTrue(res["trigger_emergency_offload"])
        self.assertFalse(res["allow_local_tinylm"])


if __name__ == "__main__":
    unittest.main()
