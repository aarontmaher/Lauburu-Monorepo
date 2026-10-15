#!/usr/bin/env python3
"""
Unit and Integration Tests for Local AI Notebook Specialist & Live Synchronizer
==============================================================================
Subsystem: 04_data_and_memory/
Validates:
- Notebook generation across Biometrics, Grappling, and Vision domains
- Headless code execution and namespace isolation
- Bidirectional AST module extraction (.ipynb -> .py)
- Live synchronizer performance metrics and Rule #0 compliance
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = MONOREPO_ROOT / "04_data_and_memory"
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from local_ai_notebook_specialist import LocalAINotebookSpecialist
from gemini_app_live_synchronizer import GeminiAppLiveSynchronizer


class TestNotebookSpecialistAndSynchronizer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.notebook_dir = self.temp_dir / "notebooks"
        self.extracted_dir = self.temp_dir / "extracted"
        self.specialist = LocalAINotebookSpecialist(
            notebook_dir=self.notebook_dir,
            extracted_dir=self.extracted_dir
        )
        self.syncer = GeminiAppLiveSynchronizer()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_notebook_generation_and_schema(self):
        for domain in ["grappling", "biometrics", "vision"]:
            nb_path = self.specialist.generate_notebook(domain)
            self.assertTrue(nb_path.exists())
            with open(nb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("cells", data)
            self.assertGreaterEqual(len(data["cells"]), 2)
            self.assertEqual(data["metadata"]["lauburu_specialist"], "LocalAINotebookSpecialist_v2026.1")

    def test_02_headless_execution(self):
        nb_path = self.specialist.generate_notebook("biometrics")
        res = self.specialist.execute_notebook_headless(nb_path)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["executed_code_cells"], 1)
        self.assertIn("pan_tompkins_filter_specs", res["extracted_symbols"])

    def test_03_bidirectional_module_extraction(self):
        nb_path = self.specialist.generate_notebook("biometrics")
        mod_path = self.specialist.extract_to_monorepo_module(nb_path, "extracted_dsp_module.py")
        self.assertTrue(mod_path.exists())
        with open(mod_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("def pan_tompkins_filter_specs", content)

    def test_04_live_synchronizer_effectiveness(self):
        metrics = self.syncer.run_sync_pass()
        self.assertEqual(metrics["bundle_count"], 5)
        self.assertGreater(metrics["total_size_kb"], 10.0)
        self.assertLess(metrics["compile_latency_ms"], 1000.0)

    def test_05_benchmark_effectiveness_score(self):
        report = self.syncer.benchmark_effectiveness(num_queries=1)
        self.assertGreaterEqual(report["overall_effectiveness_score"], 0.8)
        self.assertTrue(report["all_rule_zero_compliant"])


if __name__ == "__main__":
    unittest.main()
