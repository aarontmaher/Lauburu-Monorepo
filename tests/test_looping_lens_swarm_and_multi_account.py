#!/usr/bin/env python3
"""
================================================================================
Test Suite: Looping Self-Optimizing Lens Swarm & Multi-Account Free-Tier AI
================================================================================
Path: tests/test_looping_lens_swarm_and_multi_account.py
Governed by Rule #0 (Zero-Mock Empirical Truth Verification)
================================================================================
"""

import ast
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))

from multi_account_free_tier_manager import MultiAccountFreeTierManager, AccountCredential
from looping_self_optimizing_lens_swarm import LoopingSelfOptimizingLensSwarm, AUTHENTIC_SURFACES
from strongest_free_tier_client import QualityGate, QualityResult


class TestMultiAccountFreeTierManager(unittest.TestCase):
    def setUp(self):
        self.mgr = MultiAccountFreeTierManager()

    def test_account_email_mapping(self):
        self.assertEqual(self.mgr.ACCOUNT_EMAILS["personal"], "aaron.t.maher@gmail.com")
        self.assertEqual(self.mgr.ACCOUNT_EMAILS["business"], "lauburu@lauburugrappling.com")

    def test_register_and_rotate_credentials(self):
        # Register test keys for both accounts
        self.mgr.register_account_key("google_gemini", "personal", "test_key_aaron_12345", persist=False)
        self.mgr.register_account_key("google_gemini", "business", "test_key_lauburu_67890", persist=False)

        cred1 = self.mgr.get_active_credential("google_gemini")
        self.assertIsNotNone(cred1)

        cred2 = self.mgr.get_active_credential("google_gemini")
        self.assertIsNotNone(cred2)

        # Verify round-robin between distinct accounts
        self.assertNotEqual(cred1.api_key, cred2.api_key)

    def test_credential_masking_rule5(self):
        cred = AccountCredential(
            account_email="aaron.t.maher@gmail.com",
            account_type="personal",
            provider="google_gemini",
            api_key="AIzaSyA1234567890ABCDEF1234567890",
        )
        masked = cred.mask()
        self.assertNotIn("AIzaSyA1234567890ABCDEF1234567890", masked)
        self.assertIn("[REDACTED_PERSONAL]", masked)

    def test_aggregate_quota_status(self):
        status = self.mgr.get_aggregate_quota_status()
        self.assertIn("accounts", status)
        self.assertIn("providers", status)
        self.assertIn("total_daily_capacity", status)
        self.assertGreaterEqual(status["total_daily_capacity"], 0)


class TestLoopingLensSwarm(unittest.TestCase):
    def setUp(self):
        self.swarm = LoopingSelfOptimizingLensSwarm()

    def test_ram_sanctuary_check(self):
        # Rule #3 check
        has_ram = self.swarm.check_host_ram_sanctuary()
        self.assertTrue(has_ram)

    def test_time_to_reset_calculation(self):
        hours, minutes, seconds, rem_sec = self.swarm.get_time_to_reset()
        self.assertGreater(rem_sec, 0)
        self.assertLessEqual(rem_sec, 86400)
        self.assertGreaterEqual(hours, 0)
        self.assertLessEqual(hours, 24)

    def test_authentic_mesh_surfaces(self):
        self.assertGreaterEqual(len(AUTHENTIC_SURFACES), 3)
        for surface in AUTHENTIC_SURFACES:
            self.assertIn("domain", surface)
            self.assertIn("target", surface)
            self.assertIn("elements", surface)
            self.assertGreater(len(surface["elements"]), 0)

    def test_dpo_pair_generation_and_zero_mock(self):
        record = self.swarm.generate_dpo_pair_from_surface(0)
        self.assertIn("prompt", record)
        self.assertIn("chosen", record)
        self.assertIn("rejected", record)
        self.assertTrue(record["verified_zero_mock"])
        self.assertEqual(record["financial_cost"], 0.00)

    def test_quality_gate_ast_and_zero_mock(self):
        gate = QualityGate(min_length=30, strict_zero_mock=True)
        valid_response = "```python\ndef compute_vla_action(x: float, y: float) -> dict:\n    return {'x': x, 'y': y, 'action': 'click'}\n```"
        result = gate.evaluate(valid_response)
        self.assertTrue(result.passed)
        self.assertTrue(result.code_syntactically_valid)

        # Prohibited mock test
        mock_response = "```python\ndef test():\n    pass # mock\n```"
        mock_result = gate.evaluate(mock_response)
        self.assertFalse(mock_result.passed)


if __name__ == "__main__":
    unittest.main()
