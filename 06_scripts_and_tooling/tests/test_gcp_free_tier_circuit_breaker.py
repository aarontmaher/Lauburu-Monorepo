#!/usr/bin/env python3
"""
Unit tests for Google Cloud Always Free Tier Circuit Breaker
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

from gcp_free_tier_circuit_breaker import FreeTierLimits, GCPFreeTierCircuitBreaker


class TestGCPFreeTierCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "test_quota_state.json"
        self.breaker = GCPFreeTierCircuitBreaker(state_path=self.state_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_state_defaults(self):
        summary = self.breaker.get_summary()
        self.assertEqual(summary["zero_charge_status"], "ENFORCED")
        self.assertEqual(summary["ai_studio"]["requests_today"], 0)
        self.assertEqual(summary["bigquery"]["bytes_processed_gb"], 0.0)

    def test_ai_studio_rate_limiting(self):
        # Should allow calls initially
        ok, msg = self.breaker.can_call_ai_studio()
        self.assertTrue(ok)
        self.assertEqual(msg, "OK")

        # Record 15 calls in the last minute (reaches max RPM)
        for _ in range(15):
            self.breaker.record_ai_studio_call()

        # 16th call should be blocked by RPM limit
        ok, msg = self.breaker.can_call_ai_studio()
        self.assertFalse(ok)
        self.assertIn("RPM limit reached", msg)

    def test_bigquery_query_budget(self):
        # 100 MB query should pass
        ok, msg = self.breaker.can_run_bigquery_query(100 * 1024 * 1024)
        self.assertTrue(ok)

        # Record 801 GB (exceeds 800 GB safety limit)
        huge_bytes = int(801 * (1024 ** 3))
        self.breaker.record_bigquery_query(huge_bytes)

        # Subsequent query should be blocked
        ok, msg = self.breaker.can_run_bigquery_query(1024 * 1024)
        self.assertFalse(ok)
        self.assertIn("budget exceeded", msg)

    def test_gcs_upload_budget(self):
        # 10 MB upload should pass
        ok, msg = self.breaker.can_upload_gcs(10 * 1024 * 1024)
        self.assertTrue(ok)

        # Exceed 4.0 GB safety threshold
        self.breaker.record_gcs_upload(int(4.1 * (1024 ** 3)))

        # Next upload blocked
        ok, msg = self.breaker.can_upload_gcs(1024 * 1024)
        self.assertFalse(ok)
        self.assertIn("storage budget exceeded", msg)

    def test_secret_manager_versions_cap(self):
        # 6 secrets should be allowed
        for _ in range(6):
            ok, _ = self.breaker.can_create_secret_version()
            self.assertTrue(ok)
            self.breaker.record_secret_created()

        # 7th secret should be blocked
        ok, msg = self.breaker.can_create_secret_version()
        self.assertFalse(ok)
        self.assertIn("max active versions", msg)


if __name__ == "__main__":
    unittest.main()
