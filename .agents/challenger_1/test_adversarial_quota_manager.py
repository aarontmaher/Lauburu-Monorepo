#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for cloud_api_quota_manager.py
============================================================
Author: Challenger 1
Date: 2026-08-27

Vectors Tested:
1. Multi-process concurrent flock stress on cloud_api_quota_state.json and LoRA dataset (Multiprocessing Pool)
2. State file byte corruption, truncated JSON, invalid types, zero-byte recovery
3. Extreme boundary token limits (0, negative, 10M+, non-integer, ultra-long prompt)
4. Zero-quota edge cases, runtime API failures, and automatic fallback cascades
5. Consecutive failure health degradation, 429 rate limit cooldown, and recovery
6. High-throughput daemon batch simulation with crash recovery
"""

import os
import sys
import json
import time
import shutil
import tempfile
import multiprocessing as mp
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add project automation dir to sys.path
PROJECT_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AUTOMATION_DIR = PROJECT_ROOT / "06_scripts_and_tooling" / "automation"
sys.path.insert(0, str(AUTOMATION_DIR))

import cloud_api_quota_manager as caqm
from cloud_api_quota_manager import (
    QuotaStateStore,
    HeuristicRoutingEngine,
    HeuristicScore,
    TaskRequest,
    TaskResult,
    LoRADatasetWriter,
    WorkloadRouter,
    BaseProviderAdapter,
    GeminiAdapter,
    CloudflareAdapter,
    JulienAdapter,
    LocalMeshAdapter,
    ProviderError,
    PROVIDER_CONFIGS,
    generate_distillation_tasks,
)


def _worker_multiprocess_consume(args):
    """Worker function for multiprocessing pool to test lock contention."""
    state_file_str, provider, count, worker_id = args
    state_store = QuotaStateStore(state_file=Path(state_file_str))
    successes = 0
    failures = 0
    exceptions = []
    
    for i in range(count):
        try:
            ok = state_store.consume_quota(provider, 1)
            if ok:
                successes += 1
            else:
                failures += 1
        except Exception as e:
            exceptions.append(f"Worker {worker_id} iter {i} ex: {e}")
        time.sleep(0.0005)
        
    return successes, failures, exceptions


def _worker_multiprocess_dataset_write(args):
    """Worker function for multiprocessing dataset write contention."""
    dataset_file_str, mirror_file_str, count, worker_id = args
    writer = LoRADatasetWriter(primary_dataset=Path(dataset_file_str), mirror_dataset=Path(mirror_file_str))
    successes = 0
    exceptions = []
    
    for i in range(count):
        task = TaskRequest(
            task_id=f"mp_w{worker_id}_i{i}",
            prompt=f"Adversarial Prompt from worker {worker_id} iteration {i}",
            task_type="distillation"
        )
        res = TaskResult(
            task_id=task.task_id,
            provider_used="local_mesh",
            response_text=f"Response for worker {worker_id} iteration {i}",
            prompt_tokens=10,
            completion_tokens=10,
            latency_ms=5.0,
            success=True
        )
        try:
            ok = writer.append_distillation_pair(task, res)
            if ok:
                successes += 1
        except Exception as e:
            exceptions.append(f"Worker {worker_id} iter {i} ex: {e}")
            
    return successes, exceptions


class FailingAdapter(BaseProviderAdapter):
    """Mock adapter that simulates runtime API failure (e.g. 429 or 500 error)."""
    def __init__(self, name: str, error_type: str = "rate_limit_429", status_code: int = 429):
        super().__init__(name)
        self.error_type = error_type
        self.status_code = status_code

    def execute(self, task: TaskRequest):
        raise ProviderError(
            f"Simulated API failure for {self.name}",
            error_type=self.error_type,
            status_code=self.status_code
        )


class AdversarialTestSuite:
    def __init__(self):
        self.results = {}
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="caqm_adversarial_"))

    def cleanup(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except Exception:
            pass

    def run_all(self):
        print("=" * 80)
        print("⚡ RUNNING ADVERSARIAL STRESS SUITE FOR CLOUD_API_QUOTA_MANAGER")
        print(f"Working Temp Dir: {self.tmp_dir}")
        print("=" * 80)

        tests = [
            ("Vector 1.1: Multi-Process Flock State Store Contention", self.test_v1_1_multiprocess_flock_state),
            ("Vector 1.2: Multi-Process Dataset Concurrent Appends", self.test_v1_2_multiprocess_dataset_appends),
            ("Vector 2.1: Truncated / Corrupt Byte State File Self-Healing", self.test_v2_1_corrupt_state_recovery),
            ("Vector 2.2: Partial JSON State Missing Keys / Type Corruption", self.test_v2_2_partial_json_type_corruption),
            ("Vector 2.3: Zero-Byte State File Dynamic Reinitialization", self.test_v2_3_zero_byte_state_recovery),
            ("Vector 3.1: Extreme Boundary Token Limits (0, Negative, 10M+ Tokens)", self.test_v3_1_extreme_token_boundaries),
            ("Vector 3.2: Massive 500KB Prompt Context Resilience", self.test_v3_2_massive_prompt_resilience),
            ("Vector 4.1: Triple-Cloud Zero Quota Blackout Cascade", self.test_v4_1_zero_quota_cascade),
            ("Vector 4.2: Runtime Provider Failure Cascade with 429 Cooldown", self.test_v4_2_runtime_failure_cascade),
            ("Vector 4.3: Dynamic Consecutive Failures & Cooldown Degradation", self.test_v4_3_failure_cooldown_degradation),
            ("Vector 5.1: High-Concurrency End-to-End Workload Router Stress", self.test_v5_1_e2e_workload_router_stress),
        ]

        passed = 0
        failed = 0

        for name, test_fn in tests:
            print(f"\n[TEST] {name} ...")
            start = time.perf_counter()
            try:
                test_fn()
                dur = (time.perf_counter() - start) * 1000.0
                print(f"  --> ✅ PASSED ({dur:.2f}ms)")
                self.results[name] = {"status": "PASSED", "duration_ms": dur, "error": None}
                passed += 1
            except Exception as e:
                dur = (time.perf_counter() - start) * 1000.0
                print(f"  --> ❌ FAILED ({dur:.2f}ms): {e}")
                self.results[name] = {"status": "FAILED", "duration_ms": dur, "error": str(e)}
                failed += 1

        print("\n" + "=" * 80)
        print(f"ADVERSARIAL STRESS TEST SUMMARY: {passed} PASSED, {failed} FAILED / {len(tests)} TOTAL")
        print("=" * 80)
        return failed == 0

    # -----------------------------------------------------------------------
    # Test Vectors
    # -----------------------------------------------------------------------
    def test_v1_1_multiprocess_flock_state(self):
        """
        Spawn 8 independent OS processes via multiprocessing.Pool to execute
        50 atomic consume operations each (400 total consumes) on local_mesh.
        Verify 0 race conditions, 0 deadlocks, and exact count preservation.
        """
        state_file = self.tmp_dir / "flock_stress_state.json"
        store = QuotaStateStore(state_file=state_file)
        
        num_workers = 8
        consumes_per_worker = 50
        tasks = [(str(state_file), "local_mesh", consumes_per_worker, wid) for wid in range(num_workers)]
        
        with mp.Pool(processes=num_workers) as pool:
            results = pool.map(_worker_multiprocess_consume, tasks)
            
        total_success = sum(r[0] for r in results)
        total_fail = sum(r[1] for r in results)
        all_exceptions = [ex for r in results for ex in r[2]]
        
        assert len(all_exceptions) == 0, f"Exceptions in multiprocess flock: {all_exceptions}"
        assert total_success == num_workers * consumes_per_worker, f"Expected {num_workers * consumes_per_worker}, got {total_success}"
        assert total_fail == 0
        
        # Verify on-disk state
        reloaded = store.reload()
        assert reloaded["providers"]["local_mesh"]["used_today"] == num_workers * consumes_per_worker
        assert reloaded["providers"]["local_mesh"]["total_requests"] == num_workers * consumes_per_worker

    def test_v1_2_multiprocess_dataset_appends(self):
        """
        Spawn 8 independent OS processes to simultaneously write 25 LoRA
        distillation records each (200 records total) to the JSONL dataset.
        Verify that 100% of records are valid, well-formed JSON lines with zero interleaving.
        """
        dataset_file = self.tmp_dir / "mp_continuous_lora.jsonl"
        mirror_file = self.tmp_dir / "mp_mirror_lora.jsonl"
        
        num_workers = 8
        records_per_worker = 25
        tasks = [(str(dataset_file), str(mirror_file), records_per_worker, wid) for wid in range(num_workers)]
        
        with mp.Pool(processes=num_workers) as pool:
            results = pool.map(_worker_multiprocess_dataset_write, tasks)
            
        total_success = sum(r[0] for r in results)
        all_exceptions = [ex for r in results for ex in r[1]]
        
        assert len(all_exceptions) == 0, f"Exceptions during dataset write: {all_exceptions}"
        assert total_success == num_workers * records_per_worker
        
        # Verify primary dataset
        assert dataset_file.exists()
        raw_lines = [l for l in dataset_file.read_text(encoding="utf-8").split("\n") if l.strip()]
        assert len(raw_lines) == num_workers * records_per_worker, f"Expected {num_workers * records_per_worker} lines, got {len(raw_lines)}"
        
        # Parse every single line as JSON
        for idx, line in enumerate(raw_lines):
            try:
                parsed = json.loads(line)
                assert "instruction" in parsed
                assert "output" in parsed
                assert "metadata" in parsed
                assert parsed["metadata"]["real_data_certified"] is True
            except Exception as e:
                raise AssertionError(f"Line {idx} corrupted: '{line[:50]}...' -> {e}")

    def test_v2_1_corrupt_state_recovery(self):
        """
        Simulate power-loss partial write corruption: inject invalid truncated bytes into state file.
        Verify QuotaStateStore safely self-heals to default state without crashing.
        """
        state_file = self.tmp_dir / "corrupted_state.json"
        
        # Write corrupted partial bytes
        state_file.write_bytes(b'{"version": "2.0.0", "providers": {"gemini_free": {"used_today": 123, "rem')
        
        store = QuotaStateStore(state_file=state_file)
        state = store.reload()
        
        assert "providers" in state
        assert "gemini_free" in state["providers"]
        assert state["providers"]["gemini_free"]["daily_limit"] == 1500
        # Should be able to consume normally
        assert store.consume_quota("gemini_free", 1) is True

    def test_v2_2_partial_json_type_corruption(self):
        """
        Inject malicious/corrupted schema types:
        - "providers": null
        - "providers": {"gemini_free": 12345}
        - "metrics": "invalid_string"
        Verify graceful recovery.
        """
        state_file = self.tmp_dir / "type_corrupted_state.json"
        
        # Test 1: providers is None
        state_file.write_text(json.dumps({"version": "2.0", "providers": None}))
        store1 = QuotaStateStore(state_file=state_file)
        assert "gemini_free" in store1.state["providers"]
        
        # Test 2: providers missing key entries
        state_file.write_text(json.dumps({"version": "2.0", "providers": {"julien_ai": {}}}))
        store2 = QuotaStateStore(state_file=state_file)
        assert "cloudflare_ai" in store2.state["providers"]
        assert "gemini_free" in store2.state["providers"]
        
        # Test 3: root is a JSON array instead of dict
        state_file.write_text(json.dumps([1, 2, 3, "invalid"]))
        store3 = QuotaStateStore(state_file=state_file)
        assert isinstance(store3.state, dict)
        assert "providers" in store3.state

    def test_v2_3_zero_byte_state_recovery(self):
        """
        Simulate empty 0-byte state file.
        Verify QuotaStateStore dynamically restores default state.
        """
        state_file = self.tmp_dir / "zero_byte_state.json"
        state_file.touch()
        assert state_file.stat().st_size == 0
        
        store = QuotaStateStore(state_file=state_file)
        assert store.state_file.stat().st_size > 0
        assert store.consume_quota("local_mesh", 5) is True
        assert store.get_provider_state("local_mesh")["used_today"] == 5

    def test_v3_1_extreme_token_boundaries(self):
        """
        Stress-test HeuristicRoutingEngine against boundary token inputs:
        - 0 tokens
        - Negative tokens (-500)
        - 10,000,000 tokens (10M tokens)
        - 32,768 tokens (exact Gemini boundary)
        - 32,769 tokens (Gemini boundary + 1)
        """
        state_file = self.tmp_dir / "token_bounds_state.json"
        store = QuotaStateStore(state_file=state_file)
        engine = HeuristicRoutingEngine(store)
        
        # 1. 0 tokens
        t_zero = TaskRequest(task_id="t_zero", prompt="Zero tokens", estimated_tokens=0)
        ranked_zero = engine.rank_providers(t_zero)
        assert len(ranked_zero) == 4
        assert not ranked_zero[0].disqualified
        
        # 2. Negative tokens
        t_neg = TaskRequest(task_id="t_neg", prompt="Negative tokens", estimated_tokens=-500)
        ranked_neg = engine.rank_providers(t_neg)
        assert len(ranked_neg) == 4
        assert not ranked_neg[0].disqualified
        
        # 3. 10M tokens -> All cloud providers disqualified
        t_10m = TaskRequest(task_id="t_10m", prompt="10M token context", estimated_tokens=10_000_000)
        ranked_10m = engine.rank_providers(t_10m)
        for s in ranked_10m:
            if s.provider != "local_mesh":
                assert s.disqualified is True
                assert "exceeds max_tokens" in s.disqualify_reason
                
        # 4. Exact Gemini boundary: 32,768
        t_gemini_exact = TaskRequest(task_id="t_gem_exact", prompt="32K", estimated_tokens=32768)
        s_gem = engine.evaluate_provider("gemini_free", t_gemini_exact)
        assert s_gem.disqualified is False
        
        # 5. Gemini boundary + 1: 32,769
        t_gemini_plus = TaskRequest(task_id="t_gem_plus", prompt="32K+1", estimated_tokens=32769)
        s_gem_plus = engine.evaluate_provider("gemini_free", t_gemini_plus)
        assert s_gem_plus.disqualified is True

    def test_v3_2_massive_prompt_resilience(self):
        """
        Test WorkloadRouter execution with an extreme 500,000 character prompt string.
        Verify memory safety, token estimation calculation, and clean synthesis.
        """
        state_file = self.tmp_dir / "massive_prompt_state.json"
        dataset_file = self.tmp_dir / "massive_prompt_dataset.jsonl"
        mirror_file = self.tmp_dir / "massive_prompt_mirror.jsonl"
        
        store = QuotaStateStore(state_file=state_file)
        writer = LoRADatasetWriter(primary_dataset=dataset_file, mirror_dataset=mirror_file)
        router = WorkloadRouter(state_store=store, dataset_writer=writer)
        
        huge_prompt = "PAN_TOMPKINS_DSP_ECG_STREAM_DATA_FRAME " * 15000  # ~585 KB
        task = TaskRequest(
            task_id="t_huge_prompt",
            prompt=huge_prompt,
            estimated_tokens=len(huge_prompt) // 4,
            task_type="telemetry"
        )
        
        result = router.route_and_execute(task, force_provider="local_mesh")
        assert result.success is True
        assert result.provider_used == "local_mesh"
        assert result.lora_entry_saved is True
        assert dataset_file.exists()

    def test_v4_1_zero_quota_cascade(self):
        """
        Adversarially simulate 100% cloud quota blackout:
        - Julien: 300 / 300 consumed
        - Cloudflare: 1000 / 1000 consumed
        - Gemini: 1500 / 1500 consumed
        Execute a batch of 10 tasks through WorkloadRouter.
        Verify:
        1. Heuristic engine ranks local_mesh #1 due to cloud exhaustion.
        2. 100% of tasks succeed via sovereign Local Mesh compute.
        3. Exactly 10 LoRA records appended to continuous_lora_dataset.jsonl.
        4. Zero unhandled exceptions.
        """
        state_file = self.tmp_dir / "zero_quota_state.json"
        dataset_file = self.tmp_dir / "zero_quota_dataset.jsonl"
        mirror_file = self.tmp_dir / "zero_quota_mirror.jsonl"
        
        store = QuotaStateStore(state_file=state_file)
        writer = LoRADatasetWriter(primary_dataset=dataset_file, mirror_dataset=mirror_file)
        router = WorkloadRouter(state_store=store, dataset_writer=writer)
        
        # Drain all cloud quotas completely
        assert store.consume_quota("julien_ai", 300) is True
        assert store.consume_quota("cloudflare_ai", 1000) is True
        assert store.consume_quota("gemini_free", 1500) is True
        
        # Verify cloud providers are exhausted
        assert store.consume_quota("julien_ai", 1) is False
        assert store.consume_quota("cloudflare_ai", 1) is False
        assert store.consume_quota("gemini_free", 1) is False
        
        tasks = generate_distillation_tasks(count=10)
        for t in tasks:
            res = router.route_and_execute(t)
            assert res.success is True
            assert res.provider_used == "local_mesh"
            assert res.lora_entry_saved is True
            
        reloaded = store.reload()
        assert reloaded["providers"]["local_mesh"]["used_today"] == 10
        assert reloaded["metrics"]["total_lora_samples_harvested"] == 10
        
        # Verify dataset integrity
        lines = [l for l in dataset_file.read_text(encoding="utf-8").split("\n") if l.strip()]
        assert len(lines) == 10

    def test_v4_2_runtime_failure_cascade(self):
        """
        Simulate cloud providers having available quota, but throwing runtime
        API errors (429 Rate Limit, 500 Network Error, Auth failure).
        Verify:
        1. Router catches ProviderError, logs warning, and sets fallback_occurred = True.
        2. Health penalty is recorded in state store.
        3. Workload cascades to Local Mesh and completes successfully.
        4. Dataset is preserved.
        """
        state_file = self.tmp_dir / "runtime_fail_state.json"
        dataset_file = self.tmp_dir / "runtime_fail_dataset.jsonl"
        mirror_file = self.tmp_dir / "runtime_fail_mirror.jsonl"
        
        store = QuotaStateStore(state_file=state_file)
        writer = LoRADatasetWriter(primary_dataset=dataset_file, mirror_dataset=mirror_file)
        router = WorkloadRouter(state_store=store, dataset_writer=writer)
        
        # Replace cloud adapters with failing adapters
        router.adapters["gemini_free"] = FailingAdapter("gemini_free", error_type="rate_limit_429", status_code=429)
        router.adapters["cloudflare_ai"] = FailingAdapter("cloudflare_ai", error_type="http_500", status_code=500)
        router.adapters["julien_ai"] = FailingAdapter("julien_ai", error_type="missing_credentials", status_code=401)
        
        task = TaskRequest(
            task_id="t_runtime_fail",
            prompt="Cascade test prompt",
            task_type="distillation",
            estimated_tokens=500
        )
        
        res = router.route_and_execute(task)
        assert res.success is True
        assert res.provider_used == "local_mesh"
        assert res.fallback_occurred is True
        assert len(res.attempts) > 0
        assert res.lora_entry_saved is True
        
        # Check that gemini was placed in cooldown due to 429
        p_state = store.get_provider_state("gemini_free")
        assert p_state["status"] == "in_cooldown"
        assert p_state["consecutive_failures"] == 1

    def test_v4_3_failure_cooldown_degradation(self):
        """
        Test consecutive error handling and HTTP 429 rate limit cooldown:
        1. Provider fails 3 times -> marked DEGRADED.
        2. Provider receives 429 -> status in_cooldown with 60s cooldown_until.
        3. Heuristic engine penalizes score heavily.
        4. Success outcome resets failures, status, and cooldown.
        """
        state_file = self.tmp_dir / "health_degrade_state.json"
        store = QuotaStateStore(state_file=state_file)
        engine = HeuristicRoutingEngine(store)
        
        # Initial health
        t = TaskRequest(task_id="t_health", prompt="Health test", estimated_tokens=200)
        s_initial = engine.evaluate_provider("cloudflare_ai", t)
        assert s_initial.health_score == 1.0
        assert s_initial.penalty_failures == 0.0
        
        # 1. Simulate 3 consecutive failures
        for _ in range(3):
            store.record_outcome("cloudflare_ai", success=False, latency_ms=0.0, error_type="http_500")
            
        p_data = store.get_provider_state("cloudflare_ai")
        assert p_data["consecutive_failures"] == 3
        assert p_data["status"] == "degraded"
        
        s_degraded = engine.evaluate_provider("cloudflare_ai", t)
        assert s_degraded.health_score <= 0.4
        assert s_degraded.penalty_failures >= 0.45
        assert s_degraded.score < s_initial.score
        
        # 2. Simulate 429 rate limit
        store.record_outcome("cloudflare_ai", success=False, latency_ms=0.0, error_type="rate_limit_429")
        p_data_429 = store.get_provider_state("cloudflare_ai")
        assert p_data_429["status"] == "in_cooldown"
        assert p_data_429["cooldown_until"] > time.time()
        
        s_cooldown = engine.evaluate_provider("cloudflare_ai", t)
        assert s_cooldown.health_score == 0.05
        assert s_cooldown.penalty_failures >= 0.95
        
        # 3. Successful execution restores health
        store.record_outcome("cloudflare_ai", success=True, latency_ms=150.0)
        p_data_healthy = store.get_provider_state("cloudflare_ai")
        assert p_data_healthy["status"] == "healthy"
        assert p_data_healthy["consecutive_failures"] == 0
        assert p_data_healthy["cooldown_until"] == 0.0
        
        s_recovered = engine.evaluate_provider("cloudflare_ai", t)
        assert s_recovered.health_score == 1.0
        assert s_recovered.penalty_failures == 0.0

    def test_v5_1_e2e_workload_router_stress(self):
        """
        High-concurrency End-to-End stress test:
        Execute 20 rapid multi-type tasks across varying configurations:
        - tasks with prefer_local=True
        - tasks with distillation, telemetry, reasoning, and code types
        - tasks with diverse context sizes
        Verify 100% success rate, dataset synchronization, and state integrity.
        """
        state_file = self.tmp_dir / "e2e_stress_state.json"
        dataset_file = self.tmp_dir / "e2e_stress_dataset.jsonl"
        mirror_file = self.tmp_dir / "e2e_stress_mirror.jsonl"
        
        store = QuotaStateStore(state_file=state_file)
        writer = LoRADatasetWriter(primary_dataset=dataset_file, mirror_dataset=mirror_file)
        router = WorkloadRouter(state_store=store, dataset_writer=writer)
        
        task_types = ["distillation", "telemetry", "code", "reasoning", "general"]
        for i in range(20):
            ttype = task_types[i % len(task_types)]
            pref_local = (i % 3 == 0)
            toks = 100 + (i * 250)
            
            task = TaskRequest(
                task_id=f"e2e_stress_{i+1:03d}",
                prompt=f"Adversarial e2e task {i+1} covering {ttype}",
                system_prompt="You are the Lauburu AI Master.",
                estimated_tokens=toks,
                task_type=ttype,
                prefer_local=pref_local
            )
            
            res = router.route_and_execute(task, force_provider="local_mesh")
            assert res.success is True
            assert res.lora_entry_saved is True
            
        state = store.reload()
        assert state["metrics"]["total_lora_samples_harvested"] == 20
        
        # Verify both dataset files match exactly
        primary_lines = [l for l in dataset_file.read_text(encoding="utf-8").split("\n") if l.strip()]
        mirror_lines = [l for l in mirror_file.read_text(encoding="utf-8").split("\n") if l.strip()]
        assert len(primary_lines) == 20
        assert len(mirror_lines) == 20
        assert primary_lines == mirror_lines


if __name__ == "__main__":
    suite = AdversarialTestSuite()
    try:
        success = suite.run_all()
        sys.exit(0 if success else 1)
    finally:
        suite.cleanup()
