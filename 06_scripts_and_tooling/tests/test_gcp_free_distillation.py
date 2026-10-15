#!/usr/bin/env python3
"""
Unit tests for Google AI Studio Free Tier Distillation Pipeline
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/benchmarks"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

from gcp_free_tier_distillation_pipeline import FreeTierDistillationPipeline


class TestGCPFreeDistillation(unittest.TestCase):
    def setUp(self):
        self.mock_breaker = MagicMock()
        self.mock_breaker.can_call_ai_studio.return_value = (True, "OK")
        self.pipeline = FreeTierDistillationPipeline(
            api_key="test-unbilled-free-key",
            model_name="gemini-3.6-flash",
            min_interval_seconds=0.01,  # Short for tests
            circuit_breaker=self.mock_breaker,
        )

    def test_missing_api_key_blocks(self):
        pipe_no_key = FreeTierDistillationPipeline(api_key="")
        ok, record, msg = pipe_no_key.generate_distillation_pair("Test prompt")
        self.assertFalse(ok)
        self.assertIn("not configured", msg)

    def test_circuit_breaker_blocking(self):
        self.mock_breaker.can_call_ai_studio.return_value = (False, "RPM limit reached")
        ok, record, msg = self.pipeline.generate_distillation_pair("Test prompt")
        self.assertFalse(ok)
        self.assertIn("Circuit breaker blocked", msg)

    @patch("google.genai.Client")
    def test_successful_distillation_generation(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock(text="Pan-Tompkins QRS algorithm uses 512Hz derivative pulses.")
        mock_client.models.generate_content.return_value = mock_response

        ok, record, msg = self.pipeline.generate_distillation_pair("Explain Pan-Tompkins")
        self.assertTrue(ok)
        self.assertEqual(record["cost_usd"], 0.00)
        self.assertEqual(record["tier"], "Free Tier (Unbilled)")
        self.assertIn("Pan-Tompkins", record["teacher_reasoning"])
        self.mock_breaker.record_ai_studio_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
