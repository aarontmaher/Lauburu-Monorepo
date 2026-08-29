#!/usr/bin/env python3
"""
tests/test_cloud_api_quota_manager_and_scaffolder.py
====================================================
Comprehensive Test Suite for Milestone M5:
- Automated Free-Tier Cloud AI Quota Manager (cloud_api_quota_manager.py)
- Autonomous Code Generation Daemon (code_scaffold_daemon.py)
- Strict Fail-Closed Airgap Sentinel Verification
"""

import ast
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add project root and tooling directories to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTOMATION_DIR = PROJECT_ROOT / "06_scripts_and_tooling" / "automation"

for p in [str(PROJECT_ROOT), str(AUTOMATION_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from cloud_api_quota_manager import (
    QuotaStateStore,
    HeuristicRoutingEngine,
    WorkloadRouter,
    TaskRequest,
    TaskResult,
    LoRADatasetWriter,
    PROVIDER_CONFIGS,
    LocalMeshAdapter,
)
from code_scaffold_daemon import (
    CodeScaffoldDaemon,
    UnitTestSynthesizer,
    UIBoilerplateSynthesizer,
    ApiDocSynthesizer,
    contains_biometric_data,
    extract_code_fence,
    validate_syntax,
)


class TestCloudApiQuotaManager(unittest.TestCase):
    """Test suite for QuotaStateStore and HeuristicRoutingEngine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "quota_state_test.json"
        self.dataset_file = Path(self.temp_dir) / "lora_dataset_test.jsonl"
        self.mirror_dataset = Path(self.temp_dir) / "lora_mirror_test.jsonl"

        self.store = QuotaStateStore(state_file=self.state_file)
        self.writer = LoRADatasetWriter(
            primary_dataset=self.dataset_file,
            mirror_dataset=self.mirror_dataset,
        )
        self.router = WorkloadRouter(
            state_store=self.store,
            dataset_writer=self.writer,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_quota_limits_configuration(self):
        """Verify standard daily quota limits per provider."""
        self.assertEqual(PROVIDER_CONFIGS["gemini_free"]["daily_limit"], 1500)
        self.assertEqual(PROVIDER_CONFIGS["cloudflare_ai"]["daily_limit"], 1000)
        self.assertEqual(PROVIDER_CONFIGS["julien_ai"]["daily_limit"], 300)
        self.assertEqual(PROVIDER_CONFIGS["local_mesh"]["daily_limit"], 999999)

    def test_02_quota_consumption_and_exhaustion(self):
        """Verify quota tracking, percentage remaining, and exhaustion state."""
        state = self.store.reload()
        self.assertEqual(state["providers"]["gemini_free"]["used_today"], 0)
        self.assertEqual(state["providers"]["gemini_free"]["remaining_pct"], 1.0)

        consumed = self.store.consume_quota("gemini_free", 500)
        self.assertTrue(consumed)
        p_data = self.store.get_provider_state("gemini_free")
        self.assertEqual(p_data["used_today"], 500)
        self.assertAlmostEqual(p_data["remaining_pct"], 1000.0 / 1500.0, places=3)

        # Consume remaining 1000
        consumed = self.store.consume_quota("gemini_free", 1000)
        self.assertTrue(consumed)
        p_data = self.store.get_provider_state("gemini_free")
        self.assertEqual(p_data["used_today"], 1500)
        self.assertEqual(p_data["remaining_pct"], 0.0)

        # Over-consume should fail
        over_consumed = self.store.consume_quota("gemini_free", 1)
        self.assertFalse(over_consumed)
        p_data = self.store.get_provider_state("gemini_free")
        self.assertEqual(p_data["status"], "exhausted")

    def test_03_heuristic_ranking_and_disqualification(self):
        """Verify fitness scoring and exhaustion disqualification."""
        engine = HeuristicRoutingEngine(self.store)
        task = TaskRequest(
            task_id="test_rank_1",
            prompt="Analyze system architecture",
            estimated_tokens=500,
            task_type="reasoning",
        )
        scores = engine.rank_providers(task)
        self.assertTrue(len(scores) >= 4)
        top_provider = scores[0].provider
        self.assertIn(top_provider, ["gemini_free", "local_mesh", "cloudflare_ai"])

        # Exhaust gemini_free
        self.store.consume_quota("gemini_free", 1500)
        scores_exhausted = engine.rank_providers(task)
        gemini_score = [s for s in scores_exhausted if s.provider == "gemini_free"][0]
        self.assertTrue(gemini_score.disqualified)
        self.assertEqual(gemini_score.disqualify_reason, "Daily quota exhausted")

    def test_04_rate_limit_cooldown_penalty(self):
        """Verify 429 rate limit triggers cooldown penalty."""
        self.store.record_outcome("cloudflare_ai", success=False, latency_ms=0.0, error_type="rate_limit_429")
        p_data = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(p_data["status"], "in_cooldown")
        self.assertGreater(p_data["cooldown_until"], time.time())

    def test_05_local_mesh_fallback_and_lora_persistence(self):
        """Verify fallback to local mesh and atomic LoRA dataset serialization."""
        task = TaskRequest(
            task_id="test_lora_distill",
            prompt="Implement zero-allocation Pan-Tompkins QRS peak detection filter",
            task_type="distillation",
        )
        res = self.router.route_and_execute(task, force_provider="local_mesh")
        self.assertTrue(res.success)
        self.assertEqual(res.provider_used, "local_mesh")
        self.assertTrue(res.lora_entry_saved)

        self.assertTrue(self.dataset_file.exists())
        with open(self.dataset_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["instruction"], task.prompt)
        self.assertEqual(record["metadata"]["provider"], "local_mesh")
        self.assertTrue(record["metadata"]["real_data_certified"])


class TestCodeScaffoldDaemon(unittest.TestCase):
    """Test suite for CodeScaffoldDaemon and synthesis generators."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "quota_state_test.json"
        self.dataset_file = Path(self.temp_dir) / "lora_dataset_test.jsonl"

        self.store = QuotaStateStore(state_file=self.state_file)
        self.writer = LoRADatasetWriter(primary_dataset=self.dataset_file)
        self.router = WorkloadRouter(state_store=self.store, dataset_writer=self.writer)
        self.daemon = CodeScaffoldDaemon(router=self.router, output_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_biometric_airgap_detection(self):
        """Verify fail-closed detection of raw physiological biometric patterns."""
        clean_text = "def calculate_hash(content: str) -> str:\n    return hashlib.sha256(content.encode()).hexdigest()\n"
        is_bio, matches = contains_biometric_data(clean_text)
        self.assertFalse(is_bio)
        self.assertEqual(len(matches), 0)

        bio_texts = [
            "process ecg_samples from movesense 512hz_ecg stream",
            "raw_ppg_stream optical sensor array data",
            "ptt_blood_pressure_raw waveform inversion",
            "movesense_packet MDS 2.0 GATT byte array",
            "dfa_alpha1_raw scaling exponent buffer",
        ]
        for bt in bio_texts:
            is_b, m = contains_biometric_data(bt)
            self.assertTrue(is_b, f"Failed to detect biometric pattern in: {bt}")
            self.assertGreater(len(m), 0)

    def test_02_unit_test_synthesis(self):
        """Verify automated unit test synthesis and AST syntax validation."""
        source_code = (
            "def calculate_vo2max(hr_max: float, hr_rest: float) -> float:\n"
            "    if hr_rest <= 0:\n"
            "        raise ValueError('Resting HR must be positive')\n"
            "    return round(15.3 * (hr_max / hr_rest), 1)\n"
        )
        out_file = Path(self.temp_dir) / "test_vo2max_generated.py"
        res = self.daemon.scaffold_unit_test(
            source_code=source_code,
            module_name="vo2max_calculator",
            framework="unittest",
            target_file=out_file,
            force_provider="local_mesh",
        )
        self.assertTrue(res.success)
        self.assertTrue(res.syntax_valid)
        self.assertTrue(out_file.exists())

        # Verify generated Python file parses cleanly
        ast_tree = ast.parse(out_file.read_text(encoding="utf-8"))
        self.assertIsNotNone(ast_tree)

    def test_03_ui_boilerplate_synthesis(self):
        """Verify automated UI component boilerplate synthesis."""
        out_file = Path(self.temp_dir) / "CardiacReadinessCard.tsx"
        res = self.daemon.scaffold_ui(
            component_name="CardiacReadinessCard",
            framework="react",
            description="Real-time cardiac readiness gauge card with dark mode.",
            target_file=out_file,
            force_provider="local_mesh",
        )
        self.assertTrue(res.success)
        self.assertTrue(res.syntax_valid)
        self.assertTrue(out_file.exists())
        content = out_file.read_text(encoding="utf-8")
        self.assertIn("CardiacReadinessCard", content)
        self.assertIn("React.FC", content)

    def test_04_api_doc_synthesis(self):
        """Verify automated OpenAPI 3.0 specification synthesis."""
        out_file = Path(self.temp_dir) / "telemetry_openapi.json"
        endpoints = [
            {"path": "/health", "method": "GET", "summary": "Health check"},
            {"path": "/api/readiness", "method": "GET", "summary": "Readiness metrics"},
        ]
        res = self.daemon.scaffold_api_docs(
            service_name="telemetry_api",
            endpoints=endpoints,
            framework="openapi",
            target_file=out_file,
            force_provider="local_mesh",
        )
        self.assertTrue(res.success)
        self.assertTrue(res.syntax_valid)
        self.assertTrue(out_file.exists())
        spec = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/health", spec["paths"])
        self.assertIn("/api/readiness", spec["paths"])

    def test_05_airgap_forces_local_mesh(self):
        """Verify biometric context in scaffolding prompt automatically forces local_mesh."""
        bio_code = "def parse_ecg_samples(raw_ecg_mv: list[float]) -> dict:\n    return {'samples': raw_ecg_mv}\n"
        res = self.daemon.scaffold_unit_test(
            source_code=bio_code,
            module_name="ecg_parser",
            framework="pytest",
            force_provider="gemini_free",  # Requested gemini, but airgap MUST force local_mesh
        )
        self.assertTrue(res.airgap_protected)
        self.assertEqual(res.provider_used, "local_mesh")


if __name__ == "__main__":
    unittest.main()
