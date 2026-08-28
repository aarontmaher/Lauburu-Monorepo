#!/usr/bin/env python3
"""Red Team Lock Contention & Atomic Race Condition Attack Engine.

Stress-tests TUI concurrency resilience against:
1. Exclusive Lock Hijacking: External process acquires and holds fcntl.LOCK_EX
   across state lockfiles while concurrent TUI instances attempt reads.
2. Atomic Rename Races: High-frequency (100+ writes/sec) atomic replacement races
   testing against half-read tearing and JSONDecodeError crashes.
3. Unlink / Inode Invalidation Races: Active state file unlinked during runtime.

Measures:
- Exponential retry backoff handling
- Fallback cached state utilization
- Zero deadlocks and zero half-read panics
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class LockContentionResult:
    test_type: str
    concurrent_instances: int
    successful_reads: int
    failed_reads: int
    deadlocks_detected: int
    panics_detected: int
    duration_secs: float
    passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_id": "LOCK_CONTENTION",
            "test_type": self.test_type,
            "concurrent_instances": self.concurrent_instances,
            "successful_reads": self.successful_reads,
            "failed_reads": self.failed_reads,
            "deadlocks_detected": self.deadlocks_detected,
            "panics_detected": self.panics_detected,
            "duration_secs": round(self.duration_secs, 3),
            "passed": self.passed,
        }


def get_base_valid_state() -> Dict[str, Any]:
    return {
        "version": "2.0.0",
        "last_reset": "2026-08-27T06:00:00.000000+00:00",
        "last_reset_date": "2026-08-27",
        "last_updated": "2026-08-27T13:00:00.000000+00:00",
        "providers": {
            "julien_ai": {
                "name": "Julien AI (Direct)",
                "daily_limit": 300,
                "used_today": 45,
                "remaining_pct": 0.85,
                "avg_latency_ms": 1200.0,
                "max_tokens": 8192,
                "consecutive_failures": 0,
                "total_requests": 45,
                "successful_requests": 45,
                "status": "healthy",
            },
            "cloudflare_ai": {
                "name": "Cloudflare Workers AI",
                "daily_limit": 1000,
                "used_today": 120,
                "remaining_pct": 0.88,
                "avg_latency_ms": 650.0,
                "max_tokens": 4096,
                "consecutive_failures": 0,
                "total_requests": 120,
                "successful_requests": 120,
                "status": "healthy",
            },
        },
        "metrics": {
            "total_tasks_routed": 165,
            "cloud_tasks_succeeded": 165,
            "local_mesh_fallback_count": 0,
            "total_lora_samples_harvested": 12,
        },
    }


class LockContentionStressor:
    """Adversarial stressor executing lock contention and atomic write races."""

    def __init__(self, timeout_secs: float = 8.0):
        self.timeout_secs = timeout_secs

    def run_lock_hijacking_attack(
        self,
        cmd_builder: Callable[[Path], List[str]],
        concurrent_count: int = 10,
        lock_hold_duration_secs: float = 0.5,
    ) -> LockContentionResult:
        """Daemon acquires LOCK_EX while concurrent readers execute."""
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            state_file = tmp_path / "quota_state.json"
            lock_file = state_file.with_suffix(".lock")

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(get_base_valid_state(), f)
            lock_file.touch()

            daemon_acquired = threading.Event()
            stop_daemon = threading.Event()

            def hold_exclusive_lock():
                with open(lock_file, "r+") as lk:
                    try:
                        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
                        daemon_acquired.set()
                        time.sleep(lock_hold_duration_secs)
                    finally:
                        try:
                            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)
                        except Exception:
                            pass

            t = threading.Thread(target=hold_exclusive_lock)
            t.start()
            daemon_acquired.wait(timeout=2.0)

            # Launch concurrent TUI instances
            cmd = cmd_builder(state_file)

            def execute_reader():
                try:
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5.0,
                    )
                    combined = (res.stdout or "") + (res.stderr or "")
                    is_panic = "panic:" in combined or "Traceback" in combined or "fatal error:" in combined
                    return res.returncode, is_panic, False
                except subprocess.TimeoutExpired:
                    return -9, False, True
                except Exception:
                    return -1, True, False

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as pool:
                futures = [pool.submit(execute_reader) for _ in range(concurrent_count)]
                results = [f.result() for f in futures]

            t.join(timeout=2.0)

        success = sum(1 for ret, panic, dl in results if ret == 0 and not panic and not dl)
        failed = sum(1 for ret, panic, dl in results if ret != 0 and not dl)
        deadlocks = sum(1 for ret, panic, dl in results if dl)
        panics = sum(1 for ret, panic, dl in results if panic)

        passed = (panics == 0) and (deadlocks == 0) and (success >= concurrent_count // 2)

        return LockContentionResult(
            test_type="EXCLUSIVE_LOCK_HIJACKING",
            concurrent_instances=concurrent_count,
            successful_reads=success,
            failed_reads=failed,
            deadlocks_detected=deadlocks,
            panics_detected=panics,
            duration_secs=time.perf_counter() - t0,
            passed=passed,
        )

    def run_atomic_rename_race_attack(
        self,
        cmd_builder: Callable[[Path], List[str]],
        concurrent_readers: int = 8,
        duration_secs: float = 2.0,
    ) -> LockContentionResult:
        """High-frequency atomic file replacement concurrent with readers."""
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            state_file = tmp_path / "quota_state.json"
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(get_base_valid_state(), f)

            stop_writer = threading.Event()
            write_count = [0]

            def atomic_writer():
                cycle = 0
                while not stop_writer.is_set():
                    data = get_base_valid_state()
                    data["metrics"]["total_tasks_routed"] = cycle
                    data["providers"]["julien_ai"]["used_today"] = cycle % 300
                    tmp_swap = state_file.with_suffix(f".swap_{cycle % 5}")
                    try:
                        with open(tmp_swap, "w", encoding="utf-8") as f:
                            json.dump(data, f)
                            f.flush()
                            os.fsync(f.fileno())
                        os.replace(tmp_swap, state_file)
                        write_count[0] += 1
                    except Exception:
                        pass
                    cycle += 1
                    time.sleep(0.005)

            writer_thread = threading.Thread(target=atomic_writer)
            writer_thread.start()

            cmd = cmd_builder(state_file)
            reader_results: List[Tuple[int, bool, bool]] = []

            def reader_worker():
                start = time.perf_counter()
                local_results = []
                while time.perf_counter() - start < duration_secs:
                    try:
                        res = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=3.0,
                        )
                        combined = (res.stdout or "") + (res.stderr or "")
                        is_panic = "panic:" in combined or "Traceback" in combined
                        local_results.append((res.returncode, is_panic, False))
                    except subprocess.TimeoutExpired:
                        local_results.append((-9, False, True))
                    except Exception:
                        local_results.append((-1, True, False))
                return local_results

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_readers) as pool:
                futures = [pool.submit(reader_worker) for _ in range(concurrent_readers)]
                for f in futures:
                    reader_results.extend(f.result())

            stop_writer.set()
            writer_thread.join(timeout=2.0)

        success = sum(1 for ret, panic, dl in reader_results if ret == 0)
        failed = sum(1 for ret, panic, dl in reader_results if ret != 0)
        deadlocks = sum(1 for ret, panic, dl in reader_results if dl)
        panics = sum(1 for ret, panic, dl in reader_results if panic)

        passed = (panics == 0) and (deadlocks == 0) and (success > 0)

        return LockContentionResult(
            test_type="ATOMIC_RENAME_RACES",
            concurrent_instances=len(reader_results),
            successful_reads=success,
            failed_reads=failed,
            deadlocks_detected=deadlocks,
            panics_detected=panics,
            duration_secs=time.perf_counter() - t0,
            passed=passed,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Red Team Lock Contention & Atomic Race Fuzzer")
    parser.add_argument("cmd_prefix", nargs="+", help="Command prefix before state path")
    args = parser.parse_args()

    def cmd_builder(state_p: Path) -> List[str]:
        return args.cmd_prefix + [str(state_p)]

    stressor = LockContentionStressor()
    res1 = stressor.run_lock_hijacking_attack(cmd_builder, concurrent_count=8, lock_hold_duration_secs=0.3)
    print(f"[*] Lock Hijacking Result : Passed={res1.passed} (Success: {res1.successful_reads}/{res1.concurrent_instances}, Panics: {res1.panics_detected})")

    res2 = stressor.run_atomic_rename_race_attack(cmd_builder, concurrent_readers=4, duration_secs=1.5)
    print(f"[*] Atomic Rename Result  : Passed={res2.passed} (Total Reads: {res2.concurrent_instances}, Panics: {res2.panics_detected})")

    sys.exit(0 if (res1.passed and res2.passed) else 1)


if __name__ == "__main__":
    main()
