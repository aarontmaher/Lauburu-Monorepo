#!/usr/bin/env python3
"""
Unit tests for 05_agents_and_swarms/local_model_burst_swarm.py
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))

from local_model_burst_swarm import LocalModelBurstSwarm, CONFIRMED_LOCAL_MODELS


class TestLocalModelBurstSwarm(unittest.TestCase):

    def setUp(self):
        self.swarm = LocalModelBurstSwarm()

    def test_confirmed_models_count(self):
        self.assertGreaterEqual(len(CONFIRMED_LOCAL_MODELS), 8)
        self.assertIn("smol_135m", CONFIRMED_LOCAL_MODELS)
        self.assertIn("qwen_coder_7b", CONFIRMED_LOCAL_MODELS)
        self.assertIn("prima_ring_mesh", CONFIRMED_LOCAL_MODELS)

    def test_verify_models_on_disk(self):
        verified = self.swarm.verify_confirmed_models()
        confirmed_count = sum(1 for v in verified.values() if v["confirmed_on_disk"])
        self.assertGreaterEqual(confirmed_count, 8)

    def test_host_ram_sanctuary(self):
        free_ram = self.swarm.check_host_ram_sanctuary()
        self.assertGreater(free_ram, 0.0)

    def test_execute_burst_cycle(self):
        res = self.swarm.execute_generational_burst(domain="test_domain")
        self.assertEqual(res["status"], "GENERATIONAL_BURST_COMPLETE")
        self.assertGreaterEqual(len(res["matches"]), 2)
        self.assertIn("elo_ratings", res)


if __name__ == "__main__":
    unittest.main()
