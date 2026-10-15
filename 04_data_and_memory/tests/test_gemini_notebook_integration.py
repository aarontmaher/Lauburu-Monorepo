#!/usr/bin/env python3
"""
Unit and Integration Tests for NotebookLM & Gemini Spark Integration
====================================================================
Subsystem: 04_data_and_memory/
Validates:
- 5-Source bundle compilation and Markdown schema formatting
- Google Drive sync resilience and local directory fallback
- Gemini Spark client multimodal context assembly and DPO logging
- Rule #0 Zero-Mock validation
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project paths
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = MONOREPO_ROOT / "04_data_and_memory"
SCRIPTS_DIR = MONOREPO_ROOT / "06_scripts_and_tooling"

for p in [DATA_DIR, SCRIPTS_DIR, SCRIPTS_DIR / "tui_and_ui", SCRIPTS_DIR / "workspace_integration", SCRIPTS_DIR / "gemini_lens_integration"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from notebooklm_knowledge_compiler import NotebookLMKnowledgeCompiler
from gemini_spark_integration_client import GeminiSparkClient
from notebooklm_chrome_bridge import NotebookLMChromeBridge


class TestGeminiNotebookIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_output_dir = Path(tempfile.mkdtemp())
        self.temp_gdrive_dir = Path(tempfile.mkdtemp()) / "gdrive_test"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_output_dir, ignore_errors=True)
        shutil.rmtree(self.temp_gdrive_dir.parent, ignore_errors=True)

    def test_01_knowledge_compiler_produces_valid_bundles(self):
        compiler = NotebookLMKnowledgeCompiler(
            output_dir=self.temp_output_dir,
            gdrive_dir=self.temp_gdrive_dir
        )
        bundles = compiler.compile_all()
        self.assertEqual(len(bundles), 5)

        for b in bundles:
            self.assertTrue(b.exists(), f"Bundle {b.name} does not exist")
            self.assertGreater(b.stat().st_size, 100, f"Bundle {b.name} is too small")

            with open(b, "r", encoding="utf-8") as f:
                content = f.read()

            # Rule #0 Zero-Mock Assertions
            self.assertNotIn("lorem ipsum", content.lower())
            self.assertNotIn("fake_array", content.lower())
            self.assertNotIn("mock_telemetry", content.lower())

            # Header verification
            self.assertTrue(content.startswith("# "), f"Bundle {b.name} missing top-level H1")
            self.assertIn("Compilation Timestamp", content)

    def test_02_google_drive_sync_fallback(self):
        # 1. Test successful sync when target dir exists
        compiler = NotebookLMKnowledgeCompiler(
            output_dir=self.temp_output_dir,
            gdrive_dir=self.temp_gdrive_dir
        )
        synced = compiler.sync_to_google_drive()
        self.assertTrue(synced)
        self.assertEqual(len(list(self.temp_gdrive_dir.glob("*.md"))), 5)

        # 2. Test fallback when parent does not exist
        missing_dir = Path("/nonexistent/mount/gdrive")
        compiler_fail = NotebookLMKnowledgeCompiler(
            output_dir=self.temp_output_dir,
            gdrive_dir=missing_dir
        )
        synced_fail = compiler_fail.sync_to_google_drive()
        self.assertFalse(synced_fail)

    def test_03_gemini_spark_client_context_ingestion(self):
        client = GeminiSparkClient()
        ctx = client.get_live_mesh_context()
        self.assertIn("timestamp", ctx)
        self.assertIn("screen_lens", ctx)
        self.assertIn("git_state", ctx)

    def test_04_gemini_spark_query_and_dpo_logging(self):
        client = GeminiSparkClient()
        prompt = "Verify Rule #0 compliance across monorepo."
        result = client.query(prompt, include_live_context=True)

        self.assertEqual(result["prompt"], prompt)
        self.assertIn("engine", result)
        self.assertIn("response", result)
        self.assertTrue(len(result["response"]) > 0)
        self.assertTrue(result["context_injected"])

        # Check DPO log existence
        benchmark_file = MONOREPO_ROOT / "04_data_and_memory" / "lora_datasets" / "gemini_spark_benchmarks.jsonl"
        self.assertTrue(benchmark_file.exists())

    def test_05_notebooklm_bridge_staging_interface(self):
        bridge = NotebookLMChromeBridge()
        desktop_dst = bridge.stage_local_desktop()
        self.assertTrue(desktop_dst.exists())


if __name__ == "__main__":
    unittest.main()
