#!/usr/bin/env python3
"""
tests/test_m1_free_tier_scheduling_and_airgap.py
=================================================
Milestone 1 (M1) Comprehensive Verification Test Suite:
- Gemini 2.5 Flash Free Tier 14 RPM / 1,400 RPD token-bucket rate limiter
- Cloudflare Workers AI 10,000 Neurons/Day tracking & 60s 429 cooldown
- Daytime Active vs. Overnight Off-Peak Workload Scheduling in free_tier_ai_continuous_cron.py
- Failover across Local Mesh Ports 8081-8086
- 100% Fail-Closed Biometric Airgap & Secret Protection in cloud_api_quota_manager.py and worker.ts
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTOMATION_DIR = PROJECT_ROOT / "06_scripts_and_tooling" / "automation"
for p in [str(PROJECT_ROOT), str(AUTOMATION_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from cloud_api_quota_manager import (
    QuotaStateStore,
    WorkloadRouter,
    TaskRequest,
    TaskResult,
    LoRADatasetWriter,
    PROVIDER_CONFIGS,
    LocalMeshAdapter,
    acquire_gemini_slot,
    acquire_cloudflare_neurons,
    is_airgapped_data,
)
from free_tier_ai_continuous_cron import (
    get_current_schedule_mode,
    execute_daytime_workload,
    execute_overnight_workload,
    run_cron_cycle,
    FreeAiTrainingHarvester,
    HybridMeshGovernor,
)


class TestMilestone1FreeTierAndAirgap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "quota_state_m1.json"
        self.dataset_file = Path(self.temp_dir) / "lora_dataset_m1.jsonl"
        self.mirror_dataset = Path(self.temp_dir) / "lora_mirror_m1.jsonl"

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

    # -----------------------------------------------------------------------
    # 1. Gemini 2.5 Flash Free Tier 14 RPM / 1,400 RPD Rate Limiter Tests
    # -----------------------------------------------------------------------
    def test_01_gemini_rpm_limit_configuration(self):
        """Verify Gemini provider is configured for 14 RPM and 1,400 RPD daily envelope."""
        self.assertEqual(PROVIDER_CONFIGS["gemini_free"]["rpm_limit"], 14)
        self.assertEqual(PROVIDER_CONFIGS["gemini_free"]["daily_target_limit"], 1400)
        self.assertEqual(PROVIDER_CONFIGS["gemini_free"]["daily_limit"], 1500)

    def test_02_gemini_token_bucket_burst_and_exhaustion(self):
        """Verify token bucket permits up to 14 requests in burst and then clamps."""
        # Clean state has full capacity (14 tokens)
        for i in range(14):
            acquired = self.store.acquire_gemini_slot()
            self.assertTrue(acquired, f"Failed to acquire Gemini slot #{i+1} within initial 14 RPM capacity")

        # 15th immediate request should be rejected by the token bucket rate limiter
        acquired_15 = self.store.acquire_gemini_slot()
        self.assertFalse(acquired_15, "15th immediate request should be blocked by 14 RPM token bucket")

    def test_03_gemini_token_bucket_refill(self):
        """Verify token bucket refills over time."""
        # Drain all 14 tokens
        for _ in range(14):
            self.store.acquire_gemini_slot()
        self.assertFalse(self.store.acquire_gemini_slot())

        # Simulate 10 seconds of elapsed time (refill_rate = 14/60 = ~0.233 tokens/sec -> ~2.33 tokens)
        with self.store._locked_state() as state:
            p_data = state["providers"]["gemini_free"]
            p_data["bucket_last_refill"] -= 10.0

        # Now at least 2 slots should be acquirable
        self.assertTrue(self.store.acquire_gemini_slot())
        self.assertTrue(self.store.acquire_gemini_slot())

    def test_04_gemini_daily_target_limit_exhaustion(self):
        """Verify Gemini daily limit clamps when daily target (1,400) is reached."""
        with self.store._locked_state() as state:
            p_data = state["providers"]["gemini_free"]
            p_data["used_today"] = 1400

        acquired = self.store.acquire_gemini_slot()
        self.assertFalse(acquired, "Acquire slot should fail when 1,400 daily limit is reached")

    # -----------------------------------------------------------------------
    # 2. Cloudflare Workers AI 10,000 Neurons/Day & 60s 429 Cooldown Tests
    # -----------------------------------------------------------------------
    def test_05_cloudflare_neurons_budget_tracking(self):
        """Verify Cloudflare Workers AI tracks 10,000 Neurons/Day budget."""
        self.assertEqual(PROVIDER_CONFIGS["cloudflare_ai"]["daily_neurons_limit"], 10000)

        # Consume 5,000 neurons
        acquired = self.store.acquire_cloudflare_neurons(count=5000)
        self.assertTrue(acquired)
        p_data = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(p_data["neurons_used_today"], 5000)
        self.assertAlmostEqual(p_data["remaining_pct"], 0.5, places=2)

        # Consume another 5,000 neurons
        acquired_2 = self.store.acquire_cloudflare_neurons(count=5000)
        self.assertTrue(acquired_2)
        p_data = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(p_data["neurons_used_today"], 10000)
        self.assertEqual(p_data["remaining_pct"], 0.0)

        # Exceeding budget should fail
        over_acquired = self.store.acquire_cloudflare_neurons(count=1)
        self.assertFalse(over_acquired)
        p_data = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(p_data["status"], "exhausted")

    def test_06_cloudflare_429_cooldown(self):
        """Verify 429 error triggers a 60-second cooldown penalty."""
        self.store.record_outcome("cloudflare_ai", success=False, latency_ms=0.0, error_type="rate_limit_429")
        p_data = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(p_data["status"], "in_cooldown")
        self.assertGreater(p_data["cooldown_until"], time.time() + 50.0)
        # In cooldown, acquiring neurons must fail
        self.assertFalse(self.store.acquire_cloudflare_neurons(count=10))

    # -----------------------------------------------------------------------
    # 3. 100% Fail-Closed Airgap Protection Tests
    # -----------------------------------------------------------------------
    def test_07_is_airgapped_data_detection(self):
        """Verify is_airgapped_data detects physiological biometrics and secrets."""
        # Clean text
        self.assertFalse(is_airgapped_data("Build a responsive React landing page with TailwindCSS"))
        self.assertFalse(is_airgapped_data({"status": "nominal", "cpu_percent": 12.5}))

        # Raw biometrics
        self.assertTrue(is_airgapped_data("Stream movesense 512hz_ecg samples to local buffer"))
        self.assertTrue(is_airgapped_data("raw_ecg_mv array [0.12, 0.45, 0.99]"))
        self.assertTrue(is_airgapped_data("ptt_blood_pressure_raw calibration waveform"))
        self.assertTrue(is_airgapped_data("movesense_gatt_raw packet bytes"))
        self.assertTrue(is_airgapped_data("optical_ppg_raw continuous telemetry"))
        self.assertTrue(is_airgapped_data("pan_tompkins_qrs peak detector"))
        self.assertTrue(is_airgapped_data({"ecg_samples": [1.0, 2.0, 3.0]}))
        self.assertTrue(is_airgapped_data({"metrics": {"raw_ppg_stream": [0.1] * 25}}))

        # Secrets & credentials
        self.assertTrue(is_airgapped_data("Authorization: Bearer sk-antigravity0123456789abcdef"))
        self.assertTrue(is_airgapped_data("ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"))
        self.assertTrue(is_airgapped_data("GEMINI_API_KEY='AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz'"))
        self.assertTrue(is_airgapped_data("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA..."))

    def test_08_router_enforces_airgap_and_routes_to_local_mesh(self):
        """Verify router intercepts airgapped task and forces local mesh execution."""
        task = TaskRequest(
            task_id="m1_airgap_ecg",
            prompt="Analyze movesense 512Hz ECG stream and raw_ecg_mv array",
            system_prompt="You are a DSP specialist",
        )
        res = self.router.route_and_execute(task, force_provider="gemini_free")
        self.assertTrue(res.success)
        self.assertEqual(res.provider_used, "local_mesh")
        self.assertTrue(res.fallback_occurred)
        self.assertTrue(res.lora_entry_saved)

    # -----------------------------------------------------------------------
    # 4. Workload Scheduling (Daytime vs Overnight) Tests
    # -----------------------------------------------------------------------
    def test_09_schedule_mode_detection(self):
        """Verify schedule mode detection: Overnight (00:00-06:00 UTC) vs Daytime (06:00-24:00 UTC)."""
        # Overnight tests
        dt_night_1 = datetime(2026, 8, 29, 0, 30, tzinfo=timezone.utc)
        dt_night_2 = datetime(2026, 8, 29, 5, 59, tzinfo=timezone.utc)
        self.assertEqual(get_current_schedule_mode(dt_night_1), "OVERNIGHT_OFF_PEAK")
        self.assertEqual(get_current_schedule_mode(dt_night_2), "OVERNIGHT_OFF_PEAK")

        # Daytime tests
        dt_day_1 = datetime(2026, 8, 29, 6, 0, tzinfo=timezone.utc)
        dt_day_2 = datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc)
        dt_day_3 = datetime(2026, 8, 29, 23, 59, tzinfo=timezone.utc)
        self.assertEqual(get_current_schedule_mode(dt_day_1), "DAYTIME_ACTIVE")
        self.assertEqual(get_current_schedule_mode(dt_day_2), "DAYTIME_ACTIVE")
        self.assertEqual(get_current_schedule_mode(dt_day_3), "DAYTIME_ACTIVE")

    def test_10_daytime_workload_execution(self):
        """Verify daytime workload focuses on real-time biometrics and local airgap."""
        gov = HybridMeshGovernor()
        res = execute_daytime_workload(gov, router=self.router)
        self.assertEqual(res["mode"], "DAYTIME_ACTIVE")
        self.assertIn("REAL_TIME_BIOMETRICS", res["focus"])
        self.assertIn("100% STRICT LOCAL HARDWARE AIRGAP", res["airgap_status"])
        self.assertEqual(res["harvest"]["status"], "HARVEST_SUCCESS")

    def test_11_overnight_workload_execution(self):
        """Verify overnight workload dispatches batch synthetic scaffolding jobs."""
        gov = HybridMeshGovernor()
        res = execute_overnight_workload(gov, router=self.router, batch_size=3)
        self.assertEqual(res["mode"], "OVERNIGHT_OFF_PEAK")
        self.assertIn("HEAVY_SYNTHETIC_AST_SCAFFOLDING", res["focus"])
        self.assertEqual(res["harvest"]["status"], "HARVEST_SUCCESS")
        self.assertGreaterEqual(res["harvest"]["new_samples_added"], 3)

    def test_12_cron_cycle_full_run(self):
        """Verify run_cron_cycle runs end-to-end and writes status JSON."""
        status = run_cron_cycle(cycle_type="test_run", force_mode="DAYTIME_ACTIVE")
        self.assertEqual(status["status"], "ALL_NOMINAL")
        self.assertEqual(status["schedule_mode"], "DAYTIME_ACTIVE")
        self.assertIn("14 RPM / 1,400 RPD", status["quota_safety"])

    # -----------------------------------------------------------------------
    # 5. Local Mesh Ports 8081-8086 Failover & Synthesis Tests
    # -----------------------------------------------------------------------
    def test_13_local_mesh_adapter_ports_coverage(self):
        """Verify LocalMeshAdapter handles requests without throwing exceptions."""
        adapter = LocalMeshAdapter()
        task = TaskRequest(
            task_id="m1_local_synth",
            prompt="Implement Pan-Tompkins 512Hz ECG filter in Rust",
            task_type="biometrics",
        )
        resp, p_tok, c_tok, lat = adapter.execute(task)
        self.assertGreater(len(resp), 50)
        self.assertGreater(p_tok, 0)
        self.assertGreater(c_tok, 0)
        self.assertGreaterEqual(lat, 0.0)
        self.assertIn("Pan-Tompkins", resp)


if __name__ == "__main__":
    unittest.main()
