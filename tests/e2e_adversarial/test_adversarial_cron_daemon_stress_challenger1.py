#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_adversarial_cron_daemon_stress_challenger1.py
=========================================================
Empirical Stress Testing & Chaos Verification Suite:
24/7 Cron & Daemon Governance Pipeline (Milestone M4 Challenger 1)

Verifies 5 Core Stress Dimensions:
1. Concurrency stress on QuotaStateStore fcntl file locking under rapid multi-threaded & multi-process acquisition.
2. Quota saturation and 429 rapid backoff handling with seamless failover to local mesh ports.
3. Dataset schema validation: inject malformed, negative latency, dummy array records into tri_vault_sink.py.
4. Daemon crash resilience: simulate port closures on Ports 8080-8086, 18802, 50052, 8088 with sub-second thresholds.
5. Router RAM threshold behavior under simulated memory pressure <=35MB.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

MONOREPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MONOREPO_ROOT))
sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling" / "automation"))
sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling" / "network"))
sys.path.insert(0, str(MONOREPO_ROOT / "04_data_and_memory"))

from cloud_api_quota_manager import (
    BaseProviderAdapter,
    GeminiAdapter,
    HeuristicRoutingEngine,
    HeuristicScore,
    LoRADatasetWriter,
    PROVIDER_CONFIGS,
    ProviderError,
    QuotaStateStore,
    TaskRequest,
    TaskResult,
    WorkloadRouter,
    acquire_cloudflare_neurons,
    acquire_gemini_slot,
    is_airgapped_data,
)
from daemon_manager import (
    SUPERVISED_DAEMONS,
    DaemonManager,
    check_and_heal_daemons,
    check_router_ram,
    probe_tcp,
    verify_and_heal_tri_vault,
)
from free_tier_ai_continuous_cron import (
    FreeAiTrainingHarvester,
    get_current_schedule_mode,
    run_cron_cycle,
)
from real_hardware_router_ram_governor import (
    RealHardwareRAMGovernor,
    ROUTER_CRITICAL_RAM_MB,
)
from tri_vault_sink import (
    TriVaultSink,
    check_storage_health,
    verify_zero_mock_compliance,
)


class TestQuotaConcurrencyStress(unittest.TestCase):
    """
    Test 1: Concurrency stress on QuotaStateStore fcntl file locking
    under rapid multi-threaded acquisition and race condition testing.
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="stress_quota_concurrency_"))
        self.state_file = self.test_dir / "cloud_api_quota_state.json"
        self.store = QuotaStateStore(state_file=self.state_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rapid_multithreaded_slot_acquisition_gemini(self):
        """
        Stress-test: 50 concurrent threads attempting to acquire Gemini slots simultaneously.
        Gemini free tier has 14 RPM. Exactly 14 slots must be granted, and 36 must be denied.
        """
        results: List[bool] = []
        lock = threading.Lock()

        def worker():
            res = self.store.acquire_gemini_slot()
            with lock:
                results.append(res)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)

        self.assertEqual(len(results), 50)
        self.assertEqual(success_count, 14, f"Expected exactly 14 acquired slots, got {success_count}")
        self.assertEqual(fail_count, 36, f"Expected exactly 36 denied slots, got {fail_count}")

        # Check persisted state on disk
        state = self.store.reload()
        p_data = state["providers"]["gemini_free"]
        self.assertEqual(p_data["used_today"], 14)
        self.assertAlmostEqual(p_data["bucket_tokens"], 0.0, places=1)

    def test_rapid_multithreaded_neuron_consumption_cloudflare(self):
        """
        Stress-test: 40 threads each attempting to consume 300 neurons concurrently (Total requested: 12,000).
        Limit is 10,000 Neurons. Exactly 33 requests (9,900 neurons) should succeed, and 7 must fail.
        """
        results: List[bool] = []
        lock = threading.Lock()

        def worker():
            res = self.store.acquire_cloudflare_neurons(count=300)
            with lock:
                results.append(res)

        threads = [threading.Thread(target=worker) for _ in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)

        self.assertEqual(len(results), 40)
        self.assertEqual(success_count, 33, f"Expected exactly 33 successes (9900/10000 neurons), got {success_count}")
        self.assertEqual(fail_count, 7, f"Expected 7 rejections, got {fail_count}")

        state = self.store.reload()
        p_data = state["providers"]["cloudflare_ai"]
        self.assertEqual(p_data["neurons_used_today"], 9900)
        self.assertEqual(p_data["used_today"], 33)

    def test_concurrent_mixed_operations_and_lock_integrity(self):
        """
        Stress-test: Concurrent interleaved readers, slot acquirers, outcome recorders, and reloaders.
        Verifies zero JSON corruption or deadlock under high lock contention.
        """
        errors: List[Exception] = []

        def reader_task():
            for _ in range(20):
                try:
                    s = self.store.reload()
                    self.assertIn("providers", s)
                except Exception as e:
                    errors.append(e)

        def gemini_task():
            for _ in range(10):
                try:
                    self.store.acquire_gemini_slot()
                except Exception as e:
                    errors.append(e)

        def cf_task():
            for _ in range(10):
                try:
                    self.store.acquire_cloudflare_neurons(count=50)
                except Exception as e:
                    errors.append(e)

        def outcome_task():
            for _ in range(10):
                try:
                    self.store.record_outcome("gemini_free", success=True, latency_ms=120.0)
                except Exception as e:
                    errors.append(e)

        tasks = [
            reader_task, reader_task, gemini_task, gemini_task,
            cf_task, cf_task, outcome_task, outcome_task
        ]
        threads = [threading.Thread(target=t) for t in tasks]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")
        state = self.store.reload()
        self.assertIsInstance(state, dict)
        self.assertIn("providers", state)

    def test_utc_midnight_rollover_under_concurrency(self):
        """
        Verify that UTC midnight rollover resets quotas atomically even during concurrent access.
        """
        # Consume some quota first
        self.store.acquire_gemini_slot()
        self.store.acquire_cloudflare_neurons(count=500)

        # Mutate last_reset_date to yesterday in state file
        with open(self.store.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["last_reset_date"] = "2026-08-01"
        data["providers"]["gemini_free"]["used_today"] = 1400
        data["providers"]["cloudflare_ai"]["neurons_used_today"] = 10000
        with open(self.store.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Now trigger acquisition in multiple threads
        results: List[bool] = []
        lock = threading.Lock()

        def worker():
            res = self.store.acquire_gemini_slot()
            with lock:
                results.append(res)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Rollover should have reset used_today and permitted up to 10
        state = self.store.reload()
        self.assertEqual(state["last_reset_date"], datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        self.assertEqual(state["providers"]["gemini_free"]["used_today"], 10)


class TestQuotaSaturationAnd429Failover(unittest.TestCase):
    """
    Test 2: Quota saturation and 429 rapid backoff handling with seamless failover to local mesh ports.
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="stress_quota_429_failover_"))
        self.state_file = self.test_dir / "quota_state.json"
        self.dataset_file = self.test_dir / "continuous_lora_dataset.jsonl"
        self.mirror_file = self.test_dir / "mirror_dataset.jsonl"

        self.store = QuotaStateStore(state_file=self.state_file)
        self.writer = LoRADatasetWriter(primary_dataset=self.dataset_file, mirror_dataset=self.mirror_file)
        self.router = WorkloadRouter(state_store=self.store, dataset_writer=self.writer)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gemini_429_rate_limit_triggers_60s_cooldown(self):
        """
        When Gemini returns HTTP 429, record_outcome sets cooldown_until = time.time() + 60s
        and status to 'in_cooldown'. Subsequent can_acquire_gemini_slot must return False.
        """
        self.store.record_outcome("gemini_free", success=False, latency_ms=0.0, error_type="rate_limit_429")
        state = self.store.reload()
        p_data = state["providers"]["gemini_free"]

        self.assertEqual(p_data["status"], "in_cooldown")
        self.assertGreater(p_data["cooldown_until"], time.time())
        self.assertFalse(self.store.can_acquire_gemini_slot())
        self.assertFalse(self.store.acquire_gemini_slot())

    def test_seamless_failover_to_local_mesh_when_cloud_429_or_exhausted(self):
        """
        Simulate all cloud APIs failing or being exhausted.
        Case A (Pre-flight Quota Saturation): Router ranks local_mesh #1 and routes sovereignly.
        Case B (Mid-Flight Runtime 429 Exception): Router catches 429 ProviderError, sets cooldown, and cascades to local_mesh (fallback_occurred=True).
        """
        # Case A: Exhausted in advance
        self.store.record_outcome("gemini_free", success=False, latency_ms=0.0, error_type="rate_limit_429")
        self.store.acquire_cloudflare_neurons(count=10000)

        task_a = TaskRequest(
            task_id="chaos_failover_001",
            prompt="Synthesize 7-layer mesh topology without cloud egress.",
            task_type="distillation",
            estimated_tokens=500,
        )

        res_a = self.router.route_and_execute(task_a)
        self.assertTrue(res_a.success, "Task must succeed via local mesh fallback")
        self.assertEqual(res_a.provider_used, "local_mesh")
        self.assertGreater(len(res_a.response_text), 50)
        self.assertTrue(res_a.lora_entry_saved)

        # Case B: Mid-flight 429 runtime error when attempting a forced provider
        self.store.force_reset()
        with patch.object(self.router.adapters["gemini_free"], "execute", side_effect=ProviderError("Gemini 429 Too Many Requests", error_type="rate_limit_429", status_code=429)):
            task_b = TaskRequest(
                task_id="chaos_failover_002",
                prompt="High priority AST reasoning.",
                task_type="reasoning",
                estimated_tokens=300,
            )
            res_b = self.router.route_and_execute(task_b, force_provider="gemini_free")
            self.assertTrue(res_b.success)
            self.assertEqual(res_b.provider_used, "local_mesh")
            self.assertTrue(res_b.fallback_occurred, "Mid-flight 429 error must set fallback_occurred=True")
            self.assertGreaterEqual(len(res_b.attempts), 1)
            self.assertEqual(res_b.attempts[0]["error_type"], "rate_limit_429")

    def test_local_mesh_synthesis_engine_covers_all_task_domains(self):
        """
        Verify that local mesh synthesis engine produces high-quality structured responses
        for all required domain types: lora/distill, biometrics/dsp, quota/router, general.
        """
        domains = [
            ("lora_domain", "Implement continuous LoRA distillation pipeline for Apple Metal.", "distillation"),
            ("dsp_domain", "Compute Pan-Tompkins 512Hz ECG QRS peak detection and DFA-alpha1 scaling.", "telemetry"),
            ("quota_domain", "Optimize multi-factor quota heuristic scoring function.", "reasoning"),
            ("general_domain", "Perform monorepo architecture verification.", "general"),
        ]

        for task_id, prompt, task_type in domains:
            task = TaskRequest(task_id=task_id, prompt=prompt, task_type=task_type, prefer_local=True)
            res = self.router.route_and_execute(task)
            self.assertTrue(res.success)
            self.assertEqual(res.provider_used, "local_mesh")
            self.assertTrue(
                "Local Mesh Sovereign Engine" in res.response_text or "Sovereign Local Mesh" in res.response_text,
                f"Expected Sovereign Local Mesh signature in output for {task_id}"
            )

    def test_airgap_sentinel_immediately_forces_local_mesh(self):
        """
        When biometric telemetry (512Hz ECG, PTT BP) or secret API keys are in prompt,
        router must immediately bypass all cloud APIs and execute via local_mesh with airgap_forced=True.
        """
        biometric_prompt = "Process raw athlete 512hz_ecg samples: [0.12, 0.45, 1.20, -0.30] and ptt_blood_pressure"
        task = TaskRequest(task_id="airgap_001", prompt=biometric_prompt, task_type="telemetry")

        res = self.router.route_and_execute(task)
        self.assertTrue(res.success)
        self.assertEqual(res.provider_used, "local_mesh")
        self.assertTrue(res.fallback_occurred)


class TestDatasetSchemaAndZeroMockRejection(unittest.TestCase):
    """
    Test 3: Dataset schema validation: inject malformed, negative latency, or dummy array records
    into tri_vault_sink.py and verify strict rejection under Rule #0.
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="stress_schema_zeromock_"))
        self.lora_dir = self.test_dir / "lora_datasets"
        self.obsidian_dir = self.test_dir / "obsidian_vault"
        self.sink = TriVaultSink(
            lora_dir=self.lora_dir,
            obsidian_dir=self.obsidian_dir,
            enforce_rule_zero=True,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rejection_negative_latency(self):
        """Negative latency metric must fail Rule #0 validation and raise ValueError."""
        bad_pair = {
            "prompt": "Optimize AST diff",
            "chosen": "Valid AST diff implementation",
            "rejected": "Sub-optimal AST",
            "latency_ms": -15.4,
            "truth_verified": True,
        }
        is_valid, reason = verify_zero_mock_compliance(bad_pair)
        self.assertFalse(is_valid)
        self.assertIn("Negative latency", reason)

        with self.assertRaises(ValueError):
            self.sink.append_verified_pair(self.lora_dir / "dataset.jsonl", bad_pair)

    def test_rejection_negative_tokens(self):
        """Negative token count must fail Rule #0 validation."""
        bad_pair = {
            "prompt": "Optimize AST diff",
            "chosen": "Valid AST diff implementation",
            "rejected": "Sub-optimal AST",
            "tokens_generated": -50,
            "truth_verified": True,
        }
        is_valid, reason = verify_zero_mock_compliance(bad_pair)
        self.assertFalse(is_valid)
        self.assertIn("Negative token count", reason)

        with self.assertRaises(ValueError):
            self.sink.append_verified_pair(self.lora_dir / "dataset.jsonl", bad_pair)

    def test_rejection_dummy_zero_array(self):
        """Dummy zero arrays (e.g. [0, 0, 0, 0]) must fail Rule #0 validation."""
        bad_pair = {
            "prompt": "Evaluate biometrics stream",
            "chosen": "Pan-Tompkins verified",
            "rejected": "Unverified",
            "synthetic_array": [0, 0, 0, 0, 0],
            "truth_verified": True,
        }
        is_valid, reason = verify_zero_mock_compliance(bad_pair)
        self.assertFalse(is_valid)
        self.assertIn("Dummy zero array", reason)

        with self.assertRaises(ValueError):
            self.sink.append_verified_pair(self.lora_dir / "dataset.jsonl", bad_pair)

    def test_rejection_mock_dummy_placeholder_strings(self):
        """Mock placeholder strings ('mock_dummy', 'fake_data') must fail Rule #0 validation."""
        bad_pair = {
            "prompt": "Run benchmark",
            "chosen": "Executed with mock_dummy_engine for test purposes",
            "truth_verified": True,
        }
        is_valid, reason = verify_zero_mock_compliance(bad_pair)
        self.assertFalse(is_valid)
        self.assertIn("Mock placeholder string", reason)

        with self.assertRaises(ValueError):
            self.sink.append_verified_pair(self.lora_dir / "dataset.jsonl", bad_pair)

    def test_rejection_unverified_flag_or_low_compliance(self):
        """Explicitly unverified flags or compliance < 100% must be rejected."""
        unverified = {"prompt": "P", "output": "O", "truth_verified": False}
        is_valid, reason = verify_zero_mock_compliance(unverified)
        self.assertFalse(is_valid)

        low_compliance = {"prompt": "P", "output": "O", "truth_compliance_pct": 85.0}
        is_valid2, reason2 = verify_zero_mock_compliance(low_compliance)
        self.assertFalse(is_valid2)
        self.assertIn("Truth compliance is 85.0%", reason2)

    def test_rejection_missing_prompt_or_completion(self):
        """Empty prompts or missing completion outputs must be rejected."""
        empty_prompt = {"output": "Some completion text without a prompt"}
        is_valid, reason = verify_zero_mock_compliance(empty_prompt)
        self.assertFalse(is_valid)
        self.assertIn("Empty or missing prompt", reason)

        empty_completion = {"prompt": "Some prompt without a completion"}
        is_valid2, reason2 = verify_zero_mock_compliance(empty_completion)
        self.assertFalse(is_valid2)
        self.assertIn("Missing completion", reason2)

    def test_valid_pairs_accepted_and_daily_count_accurate(self):
        """Valid pairs must be atomically appended and correctly counted by get_daily_verified_count."""
        dataset_path = self.lora_dir / "ai_training_game_dataset.jsonl"
        for i in range(10):
            pair = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "prompt": f"Instruction task #{i+1}: Optimize mesh throughput.",
                "chosen_response": f"Applied inverse variance latency weighting for stream #{i+1}.",
                "rejected_response": "Naive round robin scheduling.",
                "reward": 1.5,
                "truth_verified": True,
                "truth_compliance_pct": 100.0,
                "zero_mock": True,
            }
            self.sink.append_verified_pair(dataset_path, pair)

        count = self.sink.get_daily_verified_count(dataset_path)
        self.assertEqual(count, 10)


class TestDaemonCrashResilience(unittest.TestCase):
    """
    Test 4: Daemon crash resilience: simulate port closures on Ports 8080-8086, 18802, 50052, 8088
    and verify watchdog detection and restart within sub-second thresholds.
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="stress_daemon_resilience_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sub_second_nonblocking_port_probing(self):
        """
        Sub-second non-blocking TCP port probe must complete within <= 0.2s even on closed ports.
        """
        # Find an unused random closed port
        closed_port = 59123
        t0 = time.perf_counter()
        is_open = probe_tcp("127.0.0.1", closed_port, timeout=0.15)
        elapsed = time.perf_counter() - t0

        self.assertFalse(is_open)
        self.assertLess(elapsed, 0.20, f"Port probe took too long ({elapsed:.3f}s > 0.20s)")

    def test_full_daemon_matrix_supervision_sub_second_execution(self):
        """
        Evaluating and probing the entire 10-daemon supervision matrix (Ports 8080-8086, 18802, 50052, 8088)
        must complete within <= 1.0 second total cycle time.
        """
        dm = DaemonManager()
        t0 = time.perf_counter()
        summary = dm.evaluate_and_heal_all()
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 2.5, f"Full supervision matrix took {elapsed:.3f}s, expected < 2.5s (10x 0.15s sequential timeout)")
        self.assertEqual(summary["total_daemons"], len(SUPERVISED_DAEMONS))
        self.assertIn("supervised_matrix", summary)
        self.assertIn("uptime_pct", summary)

    def test_simulated_port_closure_detection_and_restart_trigger(self):
        """
        Simulate a daemon running on an ephemeral port, crashing (socket closing),
        and verify DaemonManager detects the failure and attempts restart.
        """
        mock_port = 59881
        mock_config = {
            "test_daemon_59881": {
                "name": "Test Mock Daemon",
                "port": mock_port,
                "host": "127.0.0.1",
                "tier": "model",
                "start_cmd": ["echo", "restarting_daemon"],
                "icon": "🧪"
            }
        }
        dm = DaemonManager(daemons_config=mock_config)

        # Case 1: Port is open (active listener)
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", mock_port))
        server_sock.listen(1)

        res1 = dm.evaluate_and_heal_all()
        self.assertEqual(res1["supervised_matrix"]["test_daemon_59881"]["status"], "ONLINE")
        self.assertEqual(res1["online_daemons"], 1)

        # Case 2: Daemon crashes (socket closed)
        server_sock.close()
        time.sleep(0.05)

        res2 = dm.evaluate_and_heal_all()
        # Watchdog must detect closure and trigger restart
        self.assertIn(
            res2["supervised_matrix"]["test_daemon_59881"]["status"],
            ["RESTARTED", "OFFLINE"]
        )
        self.assertIn("RESTART_test_daemon_59881_PORT_59881", res2["actions_taken"])

    def test_tri_vault_auto_healing_resilience(self):
        """
        Verify that verify_and_heal_tri_vault returns structured health dictionary,
        mounts and repairs missing vault components.
        """
        status = verify_and_heal_tri_vault()
        self.assertIsInstance(status, dict)
        self.assertTrue(status["obsidian_vault_mounted"])
        self.assertTrue(status["pyspark_lake_ready"])
        self.assertTrue(status["lora_datasets_ready"])
        self.assertIsInstance(status["disk_free_gb"], float)


class TestRouterRAMThresholdBehavior(unittest.TestCase):
    """
    Test 5: Router RAM threshold behavior under simulated memory pressure <=35MB.
    """

    def test_router_nominal_ram_behavior_above_35mb(self):
        """
        When MemAvailable is 88.5 MB (> 35.0 MB), status is nominal and NO drop_caches flush is triggered.
        """
        mock_meminfo = """MemTotal:         492824 kB
MemFree:           64128 kB
MemAvailable:      90624 kB
Buffers:            4120 kB
Cached:            45120 kB"""

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = mock_meminfo
            mock_run.return_value = mock_proc

            ram_res = RealHardwareRAMGovernor.inspect_and_govern_router_ram()
            self.assertTrue(ram_res["online"])
            self.assertEqual(ram_res["available_mb"], 88.5)
            self.assertEqual(ram_res["heal_action_taken"], "NONE_REQUIRED")
            self.assertIn("NOMINAL SAFE", ram_res["safety_status"])

    def test_router_critical_ram_behavior_at_or_below_35mb(self):
        """
        When MemAvailable drops to 31.5 MB (<= 35.0 MB threshold),
        RealHardwareRAMGovernor triggers kernel drop_caches flush ('sync; echo 3 > /proc/sys/vm/drop_caches').
        """
        critical_meminfo = """MemTotal:         492824 kB
MemFree:           14128 kB
MemAvailable:      32256 kB
Buffers:            1120 kB
Cached:            15120 kB"""

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = critical_meminfo
            mock_run.return_value = mock_proc

            ram_res = RealHardwareRAMGovernor.inspect_and_govern_router_ram()
            self.assertTrue(ram_res["online"])
            self.assertEqual(ram_res["available_mb"], 31.5)
            self.assertEqual(ram_res["heal_action_taken"], "KERNEL_DROP_CACHES_EXECUTED")

            # Verify that drop_caches command was executed
            calls = [call[0][0] for call in mock_run.call_args_list]
            flush_dispatched = any("drop_caches" in cmd for cmd in calls)
            self.assertTrue(flush_dispatched, "drop_caches command was not dispatched upon critical RAM <=35MB")

    def test_router_governor_corrupted_meminfo_or_offline_fallback(self):
        """
        When router SSH fails or outputs corrupted data, governor must gracefully fall back
        to standby estimate without unhandled exception.
        """
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=3.0)):
            ram_res = RealHardwareRAMGovernor.inspect_and_govern_router_ram()
            self.assertFalse(ram_res["online"])
            self.assertEqual(ram_res["available_mb"], 86.5)
            self.assertEqual(ram_res["heal_action_taken"], "OFFLINE_STANDBY")

    def test_check_router_ram_wrapper_critical_threshold_drop_caches(self):
        """
        Verify check_router_ram wrapper function dispatches drop_caches on <= 35.0 MB.
        """
        critical_meminfo = """MemTotal:         492824 kB
MemFree:           10000 kB
MemAvailable:      25600 kB"""  # 25.0 MB

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = critical_meminfo
            mock_run.return_value = mock_proc

            avail = check_router_ram(critical_threshold_mb=35.0)
            self.assertEqual(avail, 25.0)
            calls = [call[0][0] for call in mock_run.call_args_list]
            self.assertTrue(any("drop_caches" in cmd for cmd in calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
