#!/usr/bin/env python3
"""
Unit tests for 06_scripts_and_tooling/lens_rapid_quota_maximizer.py
"""

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling"))

from lens_rapid_quota_maximizer import LensRapidQuotaMaximizer, AUTHENTIC_SURFACES


class TestLensRapidQuotaMaximizer(unittest.TestCase):

    def setUp(self):
        self.maximizer = LensRapidQuotaMaximizer()

    def test_provider_configs_exist(self):
        self.assertIn("gemini_3_1_pro", self.maximizer.PROVIDER_CONFIGS)
        self.assertIn("nvidia_deepseek_v4", self.maximizer.PROVIDER_CONFIGS)
        self.assertIn("cloudflare_workers_ai", self.maximizer.PROVIDER_CONFIGS)
        self.assertIn("xai_grok_2", self.maximizer.PROVIDER_CONFIGS)

    def test_authentic_surfaces_have_valid_elements(self):
        self.assertGreaterEqual(len(AUTHENTIC_SURFACES), 3)
        for surface in AUTHENTIC_SURFACES:
            self.assertIn("domain", surface)
            self.assertIn("elements", surface)
            for el in surface["elements"]:
                self.assertIn("cx", el)
                self.assertIn("cy", el)
                self.assertGreater(el["cx"], 0)
                self.assertGreater(el["cy"], 0)

    def test_generate_authentic_dpo_triplet(self):
        triplet = self.maximizer.generate_authentic_lens_dpo_triplet("gemini_3_1_pro", 0)
        self.assertIn("prompt", triplet)
        self.assertIn("chosen", triplet)
        self.assertIn("rejected", triplet)
        self.assertTrue(triplet["verified_zero_mock"])
        self.assertEqual(triplet["financial_cost"], 0.00)
        self.assertIn("Dispatch Chrome DevTools Protocol", triplet["chosen"])

    def test_plan_with_gemini_3_1_pro(self):
        res = self.maximizer.plan_with_gemini_3_1_pro("Optimize high-speed lens computer-use pipeline")
        self.assertEqual(res["model"], "gemini-3.1-pro-preview")
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(res["cost"], 0.00)


if __name__ == "__main__":
    unittest.main()
