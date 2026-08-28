#!/usr/bin/env python3
"""
Deep Edge Cases and High-Saturation Stress Harness for cloud_api_quota_manager.py
================================================================================
Author: Challenger 1
Date: 2026-08-27

Vectors:
1. 16-Process High-Saturation Multiprocessing Stress (1,600 concurrent transactions)
2. Midnight Rollover Race Condition across 10 concurrent processes at the same instant
3. Edge Case Inputs: Float tokens, NaN, Inf, Empty strings, Unicode emoji floods, Null fields
4. LoRA Dataset Disk Headroom / Mirror Path Resilience
5. Consecutive CLI Subprocess Blast (Spawning 10 independent Python processes simultaneously)
"""

import os
import sys
import json
import time
import math
import shutil
import tempfile
import multiprocessing as mp
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone

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
    PROVIDER_CONFIGS,
    generate_distillation_tasks,
)


def _worker_rollover_race(args):
    """Multiple workers hitting reload() when last_reset_date is old."""
    state_file_str, worker_id = args
    store = QuotaStateStore(state_file=Path(state_file_str))
    state = store.reload()
    return state["last_reset_date"], state["providers"]["gemini_free"]["used_today"]


def _worker_heavy_consume(args):
    """High-volume consume worker."""
    state_file_str, provider, count = args
    store = QuotaStateStore(state_file=Path(state_file_str))
    succ = 0
    for _ in range(count):
        if store.consume_quota(provider, 1):
            succ += 1
    return succ


def _worker_cli_exec(args):
    """Spawn real python subprocess executing CLI command."""
    script_path, state_file, dataset_file, task_id = args
    cmd = [
        sys.executable,
        str(script_path),
        "--task", f"Adversarial CLI Task {task_id}",
        "--state-file", str(state_file),
        "--dataset-file", str(dataset_file),
        "--force-provider", "local_mesh"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return res.returncode, res.stdout, res.stderr


class DeepEdgeCaseSuite:
    def __init__(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="caqm_deep_stress_"))

    def cleanup(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except Exception:
            pass

    def run_all(self):
        print("=" * 80)
        print("💥 RUNNING DEEP EDGE CASES & SATURATION STRESS SUITE")
        print(f"Working Temp Dir: {self.tmp_dir}")
        print("=" * 80)

        tests = [
            ("Deep Vector 1: 16-Process Saturation (1,600 Transactions)", self.test_dv1_16_process_saturation),
            ("Deep Vector 2: Midnight Rollover Concurrent Race Condition", self.test_dv2_midnight_rollover_race),
            ("Deep Vector 3: Exotic Token Limits & Weird Payloads (Float, Inf, Unicode)", self.test_dv3_exotic_payloads),
            ("Deep Vector 4: Unwritable Mirror Directory Resilience", self.test_dv4_unwritable_mirror_resilience),
            ("Deep Vector 5: 10-Process Concurrent CLI Subprocess Blast", self.test_dv5_concurrent_cli_blast),
        ]

        passed = 0
        failed = 0

        for name, fn in tests:
            print(f"\n[DEEP TEST] {name} ...")
            start = time.perf_counter()
            try:
                fn()
                dur = (time.perf_counter() - start) * 1000.0
                print(f"  --> ✅ PASSED ({dur:.2f}ms)")
                passed += 1
            except Exception as e:
                dur = (time.perf_counter() - start) * 1000.0
                print(f"  --> ❌ FAILED ({dur:.2f}ms): {e}")
                failed += 1

        print("\n" + "=" * 80)
        print(f"DEEP STRESS SUMMARY: {passed} PASSED, {failed} FAILED / {len(tests)} TOTAL")
        print("=" * 80)
        return failed == 0

    def test_dv1_16_process_saturation(self):
        """Spawn 16 processes, each consuming 100 quota slots (1600 consumes total)."""
        state_file = self.tmp_dir / "saturation_state.json"
        store = QuotaStateStore(state_file=state_file)
        
        num_procs = 16
        consumes_per_proc = 100
        tasks = [(str(state_file), "local_mesh", consumes_per_proc) for _ in range(num_procs)]
        
        with mp.Pool(processes=num_procs) as pool:
            results = pool.map(_worker_heavy_consume, tasks)
            
        total_succ = sum(results)
        assert total_succ == num_procs * consumes_per_proc
        
        reloaded = store.reload()
        assert reloaded["providers"]["local_mesh"]["used_today"] == 1600

    def test_dv2_midnight_rollover_race(self):
        """
        Simulate state file configured with yesterday's date.
        10 worker processes reload the file concurrently.
        Verify:
        - Date is updated to today.
        - Used count is reset to 0.
        - No corruption or multiple overlapping reset errors.
        """
        state_file = self.tmp_dir / "rollover_race_state.json"
        store = QuotaStateStore(state_file=state_file)
        store.consume_quota("gemini_free", 800)
        
        # Mutate date to yesterday
        yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        with open(state_file, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["last_reset_date"] = yesterday_str
            f.seek(0)
            f.truncate()
            json.dump(data, f)
            
        num_workers = 10
        tasks = [(str(state_file), wid) for wid in range(num_workers)]
        with mp.Pool(processes=num_workers) as pool:
            results = pool.map(_worker_rollover_race, tasks)
            
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for reset_date, used_today in results:
            assert reset_date == today_str
            assert used_today == 0

    def test_dv3_exotic_payloads(self):
        """
        Test strange/adversarial payloads:
        - Floating point estimated tokens: 500.5
        - Unicode explosion / emoji flood prompt: 10,000 emojis
        - Empty string prompt
        - Prompt with null bytes and control chars
        """
        state_file = self.tmp_dir / "exotic_state.json"
        dataset_file = self.tmp_dir / "exotic_dataset.jsonl"
        mirror_file = self.tmp_dir / "exotic_mirror.jsonl"
        
        store = QuotaStateStore(state_file=state_file)
        writer = LoRADatasetWriter(primary_dataset=dataset_file, mirror_dataset=mirror_file)
        router = WorkloadRouter(state_store=store, dataset_writer=writer)
        
        # 1. Float tokens
        t_float = TaskRequest(task_id="t_float", prompt="Float tokens", estimated_tokens=500.5)
        res1 = router.route_and_execute(t_float, force_provider="local_mesh")
        assert res1.success is True
        
        # 2. Emoji flood prompt
        emoji_prompt = "🔥🚀🤖🧠✨⚡" * 1500
        t_emoji = TaskRequest(task_id="t_emoji", prompt=emoji_prompt, estimated_tokens=1000)
        res2 = router.route_and_execute(t_emoji, force_provider="local_mesh")
        assert res2.success is True
        
        # 3. Empty string prompt
        t_empty = TaskRequest(task_id="t_empty", prompt="", estimated_tokens=0)
        res3 = router.route_and_execute(t_empty, force_provider="local_mesh")
        assert res3.success is True
        
        # 4. Null byte in prompt
        t_null = TaskRequest(task_id="t_null", prompt="Safe\x00Control\x01Bytes", estimated_tokens=50)
        res4 = router.route_and_execute(t_null, force_provider="local_mesh")
        assert res4.success is True

    def test_dv4_unwritable_mirror_resilience(self):
        """
        Verify that if the mirror dataset path is unwritable (e.g. read-only or invalid root),
        the primary dataset write still succeeds and the router does not crash.
        """
        state_file = self.tmp_dir / "unwritable_mirror_state.json"
        dataset_file = self.tmp_dir / "valid_primary.jsonl"
        bad_mirror = Path("/root_protected_dir_xyz_123/mirror.jsonl")
        
        store = QuotaStateStore(state_file=state_file)
        writer = LoRADatasetWriter(primary_dataset=dataset_file, mirror_dataset=bad_mirror)
        router = WorkloadRouter(state_store=store, dataset_writer=writer)
        
        task = TaskRequest(task_id="t_unwritable_mirror", prompt="Test unwritable mirror", estimated_tokens=100)
        res = router.route_and_execute(task, force_provider="local_mesh")
        
        assert res.success is True
        assert dataset_file.exists()
        assert len(dataset_file.read_text(encoding="utf-8").strip().split("\n")) == 1

    def test_dv5_concurrent_cli_blast(self):
        """
        Spawn 10 real CLI subprocesses simultaneously targeting the same state file and dataset file.
        Verify zero race condition crashes (all returncode == 0) and exactly 10 tasks recorded.
        """
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        state_file = self.tmp_dir / "cli_blast_state.json"
        dataset_file = self.tmp_dir / "cli_blast_dataset.jsonl"
        
        # Initialize store
        QuotaStateStore(state_file=state_file)
        
        num_cli = 10
        tasks = [(script_path, state_file, dataset_file, i) for i in range(num_cli)]
        
        with mp.Pool(processes=num_cli) as pool:
            results = pool.map(_worker_cli_exec, tasks)
            
        for returncode, stdout, stderr in results:
            assert returncode == 0, f"CLI execution failed with stderr: {stderr}"
            assert "Task Result (local_mesh)" in stdout
            
        store = QuotaStateStore(state_file=state_file)
        state = store.reload()
        assert state["providers"]["local_mesh"]["used_today"] == num_cli
        assert state["metrics"]["total_lora_samples_harvested"] == num_cli
        
        lines = [l for l in dataset_file.read_text(encoding="utf-8").split("\n") if l.strip()]
        assert len(lines) == num_cli


if __name__ == "__main__":
    suite = DeepEdgeCaseSuite()
    try:
        ok = suite.run_all()
        sys.exit(0 if ok else 1)
    finally:
        suite.cleanup()
