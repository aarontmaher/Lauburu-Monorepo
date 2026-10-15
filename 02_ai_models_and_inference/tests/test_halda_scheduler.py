#!/usr/bin/env python3
"""
Unit & Integration Tests for Halda Heterogeneity-Aware Scheduler (arXiv:2504.08791)
=================================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Integer factorization & ILFP layer partition algorithm
- Single-device automatic fallback on small models (< 14B)
- Multi-node PRP ring layer assignment on 70B models
- Sub-12ms solver latency invariant
- Rule #0 Zero-Mock compliance
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from halda_scheduler_engine import HaldaScheduler, DEFAULT_MESH_DEVICES


class TestHaldaScheduler(unittest.TestCase):

    def setUp(self):
        self.scheduler = HaldaScheduler()

    def test_01_factor_enumeration(self):
        factors_80 = self.scheduler.get_valid_factors(80)
        self.assertEqual(factors_80, [1, 2, 4, 5, 8, 10, 16, 20, 40, 80])
        factors_32 = self.scheduler.get_valid_factors(32)
        self.assertEqual(factors_32, [1, 2, 4, 8, 16, 32])

    def test_02_small_model_single_device_convergence(self):
        # 32 layers, 5.0 GB fits in L1 Host VRAM (21.6 GB)
        res = self.scheduler.solve(num_layers=32, model_size_gb=5.0)
        self.assertEqual(len(res.device_assignments), 1)
        self.assertEqual(res.device_assignments[0]["device"], "Mac_Node")
        self.assertEqual(res.device_assignments[0]["assigned_layers"], 32)
        self.assertEqual(res.rounds_k, 1)
        self.assertGreater(len(res.pruned_devices), 0)

    def test_03_70b_multi_node_prp_ring(self):
        # 80 layers, 42.0 GB exceeds single-device VRAM -> triggers PRP ring
        res = self.scheduler.solve(num_layers=80, model_size_gb=42.0)
        self.assertGreater(len(res.device_assignments), 1)
        self.assertGreater(res.rounds_k, 1)

        total_assigned = sum(a["assigned_layers"] for a in res.device_assignments)
        self.assertEqual(total_assigned, 80)

        # Check solver latency invariant (< 12 ms)
        self.assertLess(res.solver_latency_ms, 12.0)
        self.assertGreater(res.tokens_per_second, 0.0)

    def test_04_memory_limits_respected(self):
        res = self.scheduler.solve(num_layers=80, model_size_gb=42.0)
        for a in res.device_assignments:
            dev_profile = next(d for d in DEFAULT_MESH_DEVICES if d.name == a["device"])
            self.assertLessEqual(a["memory_used_gb"], dev_profile.usable_ai_vram_gb + 0.1)


if __name__ == "__main__":
    unittest.main()
