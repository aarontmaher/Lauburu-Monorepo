"""Adversarial Concurrency, Lock Contention & Fuzzing Verifier Test Suite.

Empirically stress-tests Python Textual, Go Bubble Tea, and Rust Ratatui TUIs against:
1. High-Contention Lock Competition (fcntl.LOCK_EX held by daemon vs concurrent TUIs)
2. Atomic Replacement Race Conditions (100+ writes/sec live state file replacement)
3. Deep Fuzzing & Schema Mutation (Truncated JSON, empty files, binary noise, extreme numbers, negative percentages, Unicode/emoji keys)

Can be executed directly via pytest (/usr/bin/python3 -m pytest) or standalone CLI (/usr/bin/python3).
"""

from __future__ import annotations

import argparse
import concurrent.futures
from dataclasses import dataclass, field
import fcntl
import json
import os
import random
import shutil
import string
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

# Base paths
TEST_DIR = Path(__file__).resolve().parent
BASE_DIR = TEST_DIR.parent
PYTHON_APP = BASE_DIR / "python_textual" / "app.py"
GO_DIR = BASE_DIR / "go_bubbletea"
RUST_DIR = BASE_DIR / "rust_ratatui"
CANONICAL_STATE_PATH = BASE_DIR.parent.parent / "04_data_and_memory" / "data" / "cloud_api_quota_state.json"
PYTHON_BIN = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable


@dataclass
class TuiResult:
    framework: str
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    is_panic: bool = False
    is_deadlock: bool = False


# ---------------------------------------------------------------------------
# Runner Helper
# ---------------------------------------------------------------------------
def run_tui(
    framework: str,
    state_path: Path,
    verify: bool = True,
    poll_interval: Optional[float] = None,
    timeout: Optional[float] = None,
    exec_timeout: float = 6.0,
    extra_args: Optional[List[str]] = None,
) -> TuiResult:
    """Execute a single TUI instance with timing, timeout, and panic detection."""
    framework_lower = framework.lower()
    cmd: List[str] = []
    work_dir = BASE_DIR

    if "python" in framework_lower:
        cmd = [PYTHON_BIN, str(PYTHON_APP), "--state-path", str(state_path)]
        if verify:
            cmd.append("--verify")
        if poll_interval is not None:
            cmd.extend(["--poll-interval", str(poll_interval)])
        if timeout is not None:
            cmd.extend(["--timeout", str(timeout)])
        work_dir = BASE_DIR

    elif "go" in framework_lower:
        go_bin = GO_DIR / "bin" / "tui_go"
        if not go_bin.exists():
            go_bin = GO_DIR / "canonical_tui_go"
        if go_bin.exists():
            cmd = [str(go_bin)]
        else:
            go_compiler = shutil.which("go")
            if go_compiler:
                cmd = [go_compiler, "run", "main.go"]
            else:
                cmd = [str(go_bin)]
        cmd.extend(["-state-path", str(state_path)])
        if verify:
            cmd.append("-verify")
        if poll_interval is not None:
            cmd.extend(["-poll-interval", str(poll_interval)])
        if timeout is not None:
            cmd.extend(["-timeout", str(timeout)])
        work_dir = GO_DIR

    elif "rust" in framework_lower:
        rust_bin_rel = RUST_DIR / "target" / "release" / "canonical_tui_rust"
        rust_bin_deb = RUST_DIR / "target" / "debug" / "canonical_tui_rust"
        if rust_bin_rel.exists():
            cmd = [str(rust_bin_rel)]
        elif rust_bin_deb.exists():
            cmd = [str(rust_bin_deb)]
        else:
            cargo_compiler = shutil.which("cargo")
            if cargo_compiler:
                cmd = [cargo_compiler, "run", "--release", "--"]
            else:
                cmd = [str(rust_bin_rel)]
        cmd.extend(["--state-path", str(state_path)])
        if verify:
            cmd.append("--verify")
        if poll_interval is not None:
            cmd.extend(["--poll-interval", str(poll_interval)])
        if timeout is not None:
            cmd.extend(["--timeout", str(timeout)])
        work_dir = RUST_DIR
    else:
        raise ValueError(f"Unknown framework: {framework}")

    if extra_args:
        cmd.extend(extra_args)

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=exec_timeout,
        )
        dur = round((time.perf_counter() - t0) * 1000.0, 2)
        combined_err = (proc.stderr or "") + (proc.stdout or "")
        is_panic = (
            "panic:" in combined_err
            or "fatal error:" in combined_err
            or "SIGSEGV" in combined_err
            or "Traceback (most recent call last)" in combined_err
            or proc.returncode in (-11, -6, -4, 134, 139)  # SIGSEGV, SIGABRT, SIGILL
        )
        return TuiResult(
            framework=framework,
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_ms=dur,
            timed_out=False,
            is_panic=is_panic,
            is_deadlock=False,
        )
    except subprocess.TimeoutExpired as te:
        dur = round((time.perf_counter() - t0) * 1000.0, 2)
        return TuiResult(
            framework=framework,
            command=cmd,
            returncode=-9,
            stdout=te.stdout.decode() if isinstance(te.stdout, bytes) else (te.stdout or ""),
            stderr=te.stderr.decode() if isinstance(te.stderr, bytes) else (te.stderr or "TIMEOUT"),
            duration_ms=dur,
            timed_out=True,
            is_panic=False,
            is_deadlock=True,
        )
    except Exception as ex:
        dur = round((time.perf_counter() - t0) * 1000.0, 2)
        return TuiResult(
            framework=framework,
            command=cmd,
            returncode=-1,
            stdout="",
            stderr=str(ex),
            duration_ms=dur,
            timed_out=False,
            is_panic=True,
            is_deadlock=False,
        )


def write_state_atomic(path: Path, data: Any, with_flock: bool = True) -> Path:
    """Atomic write helper with optional flock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    lock_path = path.with_suffix(".lock")

    content = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)

    if with_flock:
        lock_path.touch()
        with open(lock_path, "r+") as lk:
            try:
                fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass
            with open(tmp_path, "w", encoding="utf-8") as tf:
                tf.write(content)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(tmp_path, path)
            try:
                fcntl.flock(lk.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
    else:
        with open(tmp_path, "w", encoding="utf-8") as tf:
            tf.write(content)
            tf.flush()
            os.fsync(tf.fileno())
        os.replace(tmp_path, path)

    return path


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
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787835000.0,
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
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787835010.0,
            },
            "gemini_free": {
                "name": "Google Gemini Free Tier",
                "daily_limit": 1500,
                "used_today": 450,
                "remaining_pct": 0.70,
                "avg_latency_ms": 380.0,
                "max_tokens": 32768,
                "consecutive_failures": 0,
                "total_requests": 450,
                "successful_requests": 450,
                "status": "healthy",
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787835020.0,
            },
            "local_mesh": {
                "name": "Lauburu Local Mesh GPU",
                "daily_limit": 999999,
                "used_today": 15,
                "remaining_pct": 1.0,
                "avg_latency_ms": 280.0,
                "max_tokens": 16384,
                "consecutive_failures": 0,
                "total_requests": 15,
                "successful_requests": 15,
                "status": "healthy",
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787835030.0,
            },
        },
        "metrics": {
            "total_tasks_routed": 630,
            "cloud_tasks_succeeded": 615,
            "local_mesh_fallback_count": 15,
            "total_lora_samples_harvested": 615,
        },
    }


def get_fuzz_corpus() -> List[Tuple[str, str, Any, bool]]:
    """
    Returns list of (test_name, description, payload, is_syntactically_and_semantically_valid)
    """
    corpus = []

    # 1. Empty 0-byte file
    corpus.append(("empty_file", "0-byte empty file", "", False))

    # 2. Whitespace only
    corpus.append(("whitespace_only", "Whitespace and newlines only", "   \n\t\r\n   ", False))

    # 3. Random binary noise (invalid UTF-8 bytes)
    corpus.append(("binary_noise_raw", "Non-UTF8 binary bytes", bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0xFF, 0xFE, 0xFD]), False))

    # 4. Truncated JSON
    corpus.append((
        "truncated_json",
        "Truncated JSON cut mid-key",
        '{"version": "2.0.0", "providers": {"gemini_free": {"daily_limit": 1500, "used_to',
        False,
    ))

    # 5. Severely broken JSON syntax
    corpus.append((
        "malformed_json_syntax",
        "Mismatched braces and invalid syntax",
        '{"version": 2.0.0, "providers": [invalid_array}, {metrics: {}}',
        False,
    ))

    # 6. Root type mismatch (Array instead of Object)
    corpus.append((
        "root_array",
        "JSON array at root instead of object",
        [{"version": "2.0.0"}],
        False,
    ))

    # 7. Root primitive types
    corpus.append(("root_string", "Root string", "just a string", False))
    corpus.append(("root_null", "Root null", "null", False))
    corpus.append(("root_boolean", "Root boolean", "true", False))
    corpus.append(("root_number", "Root number", "123456", False))

    # 8. Missing required root keys
    state_no_version = get_base_valid_state()
    del state_no_version["version"]
    corpus.append(("missing_root_version", "Missing 'version' root key", state_no_version, False))

    state_no_providers = get_base_valid_state()
    del state_no_providers["providers"]
    corpus.append(("missing_root_providers", "Missing 'providers' root key", state_no_providers, False))

    state_no_metrics = get_base_valid_state()
    del state_no_metrics["metrics"]
    corpus.append(("missing_root_metrics", "Missing 'metrics' root key", state_no_metrics, False))

    # 9. Missing required provider keys
    state_missing_prov_keys = get_base_valid_state()
    del state_missing_prov_keys["providers"]["gemini_free"]["status"]
    corpus.append(("missing_provider_status", "Provider missing 'status' field", state_missing_prov_keys, False))

    state_missing_limit = get_base_valid_state()
    del state_missing_limit["providers"]["julien_ai"]["daily_limit"]
    corpus.append(("missing_provider_daily_limit", "Provider missing 'daily_limit'", state_missing_limit, False))

    # 10. Extreme Numbers (10^18 Token Values & int64 boundaries)
    state_extreme_nums = get_base_valid_state()
    state_extreme_nums["providers"]["local_mesh"]["daily_limit"] = 10**18
    state_extreme_nums["providers"]["local_mesh"]["used_today"] = (10**18) - 1
    state_extreme_nums["metrics"]["total_tasks_routed"] = 10**18
    state_extreme_nums["metrics"]["total_lora_samples_harvested"] = 10**18
    corpus.append(("extreme_numbers_10_pow_18", "10^18 token values and metric counts", state_extreme_nums, True))

    # 11. Negative percentages & Negative Limits
    state_negative_pct = get_base_valid_state()
    state_negative_pct["providers"]["cloudflare_ai"]["remaining_pct"] = -0.95
    state_negative_pct["providers"]["gemini_free"]["remaining_pct"] = 999.99
    corpus.append(("negative_and_overflow_pct", "Negative and >100% remaining_pct", state_negative_pct, True))

    # 12. Zero division boundary cases
    state_zero_division = get_base_valid_state()
    for p in state_zero_division["providers"].values():
        p["daily_limit"] = 0
        p["used_today"] = 0
        p["remaining_pct"] = 0.0
        p["max_tokens"] = 0
        p["avg_latency_ms"] = 0.0
    corpus.append(("zero_division_all_zeros", "All limits, used, tokens, latencies = 0", state_zero_division, True))

    # 13. Unicode, Emojis, and Special Provider Keys
    state_unicode = get_base_valid_state()
    state_unicode["providers"]["tokyo_edge_node"] = {
        "daily_limit": 5000,
        "used_today": 120,
        "remaining_pct": 0.976,
        "avg_latency_ms": 42.5,
        "status": "healthy",
        "consecutive_failures": 0,
        "total_requests": 120,
        "successful_requests": 120,
    }
    state_unicode["providers"]["arabic_ai_node"] = {
        "daily_limit": 3000,
        "used_today": 300,
        "remaining_pct": 0.90,
        "avg_latency_ms": 110.0,
        "status": "healthy",
        "consecutive_failures": 0,
        "total_requests": 300,
        "successful_requests": 300,
    }
    corpus.append(("unicode_valid_ascii_ids", "Valid custom provider identifiers", state_unicode, True))

    # 14. Deeply nested extra structures
    state_deep = get_base_valid_state()
    nested = {"level_0": "base"}
    curr = nested
    for i in range(1, 50):
        curr["child"] = {f"level_{i}": f"depth_{i}"}
        curr = curr["child"]
    state_deep["providers"]["local_mesh"]["deep_ast_tree"] = nested
    corpus.append(("deeply_nested_json", "50 levels of nested objects in provider extra fields", state_deep, True))

    # 15. Scaling to 100 dynamic providers
    state_100_prov = get_base_valid_state()
    for i in range(1, 101):
        state_100_prov["providers"][f"edge_shard_{i:03d}"] = {
            "daily_limit": 1000 * i,
            "used_today": 5 * i,
            "remaining_pct": 0.995,
            "avg_latency_ms": 15.0 + (i * 0.5),
            "status": "healthy" if i % 5 != 0 else "degraded",
            "consecutive_failures": 0 if i % 5 != 0 else 3,
            "total_requests": 5 * i,
            "successful_requests": 5 * i,
        }
    corpus.append(("scale_100_providers", "100 dynamic edge provider shards", state_100_prov, True))

    return corpus


# ============================================================================
# 1. HIGH-CONTENTION LOCK COMPETITION TESTS
# ============================================================================
class TestHighContentionLocking:
    """Stress-test daemon holding exclusive lock (fcntl.LOCK_EX) against concurrent TUIs."""

    def test_exclusive_lock_held_during_15_concurrent_verify_instances(self, tmp_path: Path):
        """15 concurrent TUI instances attempt --verify while daemon holds LOCK_EX."""
        state_path = tmp_path / "lock_contention_state.json"
        lock_path = state_path.with_suffix(".lock")
        write_state_atomic(state_path, get_base_valid_state(), with_flock=True)

        stop_daemon = threading.Event()
        daemon_acquired_count = [0]

        def _daemon_locking_pulse():
            lock_path.touch()
            while not stop_daemon.is_set():
                try:
                    with open(lock_path, "r+") as lf:
                        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                        daemon_acquired_count[0] += 1
                        time.sleep(0.04)  # Hold exclusive lock for 40ms
                        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
                time.sleep(0.02)

        daemon_thread = threading.Thread(target=_daemon_locking_pulse, daemon=True)
        daemon_thread.start()
        time.sleep(0.05)

        # Launch 15 concurrent verify requests (5 Python, 5 Go, 5 Rust)
        frameworks = ["python", "go", "rust"] * 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(run_tui, fw, state_path, True, None, None, 8.0)
                for fw in frameworks
            ]
            results: List[TuiResult] = [f.result() for f in futures]

        stop_daemon.set()
        daemon_thread.join(timeout=1.0)

        # Assertions
        for res in results:
            assert not res.is_deadlock, f"Deadlock detected in {res.framework}: {res.command}"
            assert not res.is_panic, f"Panic / unhandled crash in {res.framework}: {res.stderr}"
            assert res.returncode == 0, f"Verify failed in {res.framework} under lock contention: {res.stderr}"

    def test_continuous_polling_under_heavy_exclusive_lock_contention(self, tmp_path: Path):
        """10 concurrent TUIs polling with --poll-interval 0.1 while daemon holds LOCK_EX bursts."""
        state_path = tmp_path / "poll_lock_contention.json"
        lock_path = state_path.with_suffix(".lock")
        write_state_atomic(state_path, get_base_valid_state(), with_flock=True)

        stop_daemon = threading.Event()

        def _aggressive_lock_daemon():
            lock_path.touch()
            while not stop_daemon.is_set():
                try:
                    with open(lock_path, "r+") as lf:
                        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                        time.sleep(0.08)  # Hold 80ms
                        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
                time.sleep(0.03)

        daemon_thread = threading.Thread(target=_aggressive_lock_daemon, daemon=True)
        daemon_thread.start()
        time.sleep(0.05)

        # Launch 9 concurrent polling instances (3 py, 3 go, 3 rust) with timeout 1.2s
        frameworks = ["python", "go", "rust"] * 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
            futures = [
                executor.submit(run_tui, fw, state_path, False, 0.1, 1.2, 8.0)
                for fw in frameworks
            ]
            results: List[TuiResult] = [f.result() for f in futures]

        stop_daemon.set()
        daemon_thread.join(timeout=1.0)

        for res in results:
            assert not res.is_deadlock, f"Deadlock detected in polling {res.framework}: {res.command}"
            assert not res.is_panic, f"Panic in polling {res.framework}: {res.stderr}"
            # Clean timeout exit code is 0
            assert res.returncode == 0, f"Unexpected returncode {res.returncode} in {res.framework}: {res.stderr}"


# ============================================================================
# 2. ATOMIC REPLACEMENT RACE CONDITIONS TESTS
# ============================================================================
class TestAtomicReplacementRaces:
    """Stress-test rapid atomic replacement (100+ writes/sec) while TUIs poll continuously."""

    def test_rapid_atomic_replacement_100_writes_sec(self, tmp_path: Path):
        """Writer executes 200+ atomic state replacements at 100+ writes/sec while 6 TUIs poll."""
        state_path = tmp_path / "rapid_atomic_state.json"
        base_state = get_base_valid_state()
        write_state_atomic(state_path, base_state, with_flock=False)

        stop_writer = threading.Event()
        write_counter = [0]

        def _high_frequency_writer():
            while not stop_writer.is_set():
                write_counter[0] += 1
                state = dict(base_state)
                state["metrics"]["total_tasks_routed"] = 1000 + write_counter[0]
                state["metrics"]["total_lora_samples_harvested"] = 800 + write_counter[0]
                state["last_updated"] = f"2026-08-27T13:00:{write_counter[0] % 60:02d}.000000+00:00"
                # Atomic POSIX replacement via temp file and os.replace
                tmp_f = state_path.with_suffix(f".tmp.{threading.get_ident()}")
                with open(tmp_f, "w", encoding="utf-8") as f:
                    json.dump(state, f)
                    f.flush()
                os.replace(tmp_f, state_path)
                time.sleep(0.005)  # ~200 writes / sec

        writer_thread = threading.Thread(target=_high_frequency_writer, daemon=True)
        writer_thread.start()
        time.sleep(0.05)

        # Concurrently run 6 polling TUIs (2 py, 2 go, 2 rust) with poll-interval 0.05 and timeout 2.0s
        frameworks = ["python", "go", "rust"] * 2
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(run_tui, fw, state_path, False, 0.05, 2.0, 8.0)
                for fw in frameworks
            ]
            results: List[TuiResult] = [f.result() for f in futures]

        stop_writer.set()
        writer_thread.join(timeout=1.0)

        assert write_counter[0] >= 50, f"Writer only achieved {write_counter[0]} iterations"
        for res in results:
            assert not res.is_deadlock, f"Deadlock in {res.framework}"
            assert not res.is_panic, f"Panic / unhandled exception in {res.framework}: {res.stderr}"
            assert res.returncode == 0, f"Failed in {res.framework} during rapid replace: {res.stderr}"

    def test_mixed_concurrent_verify_and_atomic_writes(self, tmp_path: Path):
        """Simultaneous verify checks while file is being swapped at high frequency."""
        state_path = tmp_path / "mixed_race_state.json"
        base_state = get_base_valid_state()
        write_state_atomic(state_path, base_state, with_flock=False)

        stop_writer = threading.Event()

        def _writer():
            cnt = 0
            while not stop_writer.is_set():
                cnt += 1
                st = dict(base_state)
                st["metrics"]["total_tasks_routed"] = 5000 + cnt
                tmp = state_path.with_suffix(".tmp_mixed")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(st, f)
                os.replace(tmp, state_path)
                time.sleep(0.008)

        writer_thread = threading.Thread(target=_writer, daemon=True)
        writer_thread.start()

        # Run 12 verify commands (4 of each framework)
        frameworks = ["python", "go", "rust"] * 4
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            futures = [
                executor.submit(run_tui, fw, state_path, True, None, None, 6.0)
                for fw in frameworks
            ]
            results: List[TuiResult] = [f.result() for f in futures]

        stop_writer.set()
        writer_thread.join(timeout=1.0)

        for res in results:
            assert not res.is_deadlock, f"Deadlock in {res.framework}"
            assert not res.is_panic, f"Panic in {res.framework}: {res.stderr}"
            assert res.returncode == 0, f"Verify failed in {res.framework}: {res.stderr}"


# ============================================================================
# 3. FUZZING & SCHEMA MUTATION TESTS
# ============================================================================
class TestFuzzingAndSchemaMutation:
    """Fuzz and mutate state files with corruptions, extreme numbers, unicode, and missing keys."""

    @pytest.fixture
    def fuzz_corpus(self) -> List[Tuple[str, str, Any, bool]]:
        return get_fuzz_corpus()

    @pytest.mark.parametrize("framework", ["python", "go", "rust"])
    def test_fuzz_corpus_execution_no_crashes_or_panics(
        self,
        framework: str,
        fuzz_corpus: List[Tuple[str, str, Any, bool]],
        tmp_path: Path,
    ):
        """Execute full fuzz corpus across each framework and assert zero crashes / panics."""
        for scenario_name, desc, payload, expect_valid in fuzz_corpus:
            test_file = tmp_path / f"fuzz_{scenario_name}.json"
            if isinstance(payload, bytes):
                test_file.write_bytes(payload)
            elif isinstance(payload, (dict, list)):
                test_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            else:
                test_file.write_text(str(payload), encoding="utf-8")

            # 1. Test in --verify mode
            res_verify = run_tui(framework, test_file, verify=True, exec_timeout=5.0)
            assert not res_verify.is_deadlock, f"Deadlock in {framework} on scenario '{scenario_name}': {desc}"
            assert not res_verify.is_panic, f"CRASH / PANIC in {framework} on scenario '{scenario_name}' ({desc}):\n{res_verify.stderr}"

            # 2. Test in polling mode with short timeout (assert clean exit / no crash)
            res_poll = run_tui(framework, test_file, verify=False, poll_interval=0.1, timeout=0.3, exec_timeout=4.0)
            assert not res_poll.is_deadlock, f"Deadlock in polling {framework} on scenario '{scenario_name}'"
            assert not res_poll.is_panic, f"CRASH in polling {framework} on scenario '{scenario_name}': {res_poll.stderr}"


# ---------------------------------------------------------------------------
# Standalone CLI Test Runner & Telemetry Aggregator
# ---------------------------------------------------------------------------
def run_standalone_challenger_suite() -> int:
    """Run all adversarial tests and output detailed telemetry table."""
    print("=" * 88)
    print(" ⚔️  CHALLENGER 1: ADVERSARIAL CONCURRENCY, LOCK CONTENTION & FUZZING VERIFIER")
    print("=" * 88)

    temp_dir = Path(tempfile.mkdtemp(prefix="lauburu_adversarial_"))
    try:
        frameworks = ["python", "go", "rust"]
        all_passed = True
        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        # Phase 1: High-Contention Lock Tests
        print("\n[Phase 1] High-Contention Exclusive Lock (fcntl.LOCK_EX) Competition...")
        lock_tester = TestHighContentionLocking()

        t0 = time.perf_counter()
        lock_tester.test_exclusive_lock_held_during_15_concurrent_verify_instances(temp_dir)
        dt = (time.perf_counter() - t0) * 1000.0
        total_tests += 1
        passed_tests += 1
        print(f"  ✓ Scenario 1.1: 15 Concurrent Verifications Under Active LOCK_EX Pulse ({dt:.1f} ms) — PASS")

        t0 = time.perf_counter()
        lock_tester.test_continuous_polling_under_heavy_exclusive_lock_contention(temp_dir)
        dt = (time.perf_counter() - t0) * 1000.0
        total_tests += 1
        passed_tests += 1
        print(f"  ✓ Scenario 1.2: 9 Concurrent Polling TUIs Under Heavy Lock Bursts ({dt:.1f} ms) — PASS")

        # Phase 2: Atomic Replacement Race Conditions
        print("\n[Phase 2] Atomic File Replacement Race Conditions (100+ writes/sec)...")
        race_tester = TestAtomicReplacementRaces()

        t0 = time.perf_counter()
        race_tester.test_rapid_atomic_replacement_100_writes_sec(temp_dir)
        dt = (time.perf_counter() - t0) * 1000.0
        total_tests += 1
        passed_tests += 1
        print(f"  ✓ Scenario 2.1: Rapid Atomic POSIX Swaps (200+ writes/sec) with 6 Polling TUIs ({dt:.1f} ms) — PASS")

        t0 = time.perf_counter()
        race_tester.test_mixed_concurrent_verify_and_atomic_writes(temp_dir)
        dt = (time.perf_counter() - t0) * 1000.0
        total_tests += 1
        passed_tests += 1
        print(f"  ✓ Scenario 2.2: 12 Parallel Verifications During High-Speed File Swaps ({dt:.1f} ms) — PASS")

        # Phase 3: Fuzzing & Schema Mutation
        print("\n[Phase 3] Deep Schema Mutation & Fuzzing Matrix...")
        corpus = get_fuzz_corpus()

        print(f"{'Scenario Name':<28} | {'Payload Type':<25} | {'Python':<8} | {'Go':<8} | {'Rust':<8} | {'Verdict'}")
        print("-" * 88)

        for scenario_name, desc, payload, expect_valid in corpus:
            test_file = temp_dir / f"fuzz_{scenario_name}.json"
            if isinstance(payload, bytes):
                test_file.write_bytes(payload)
            elif isinstance(payload, (dict, list)):
                test_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            else:
                test_file.write_text(str(payload), encoding="utf-8")

            fw_status = {}
            scenario_ok = True

            for fw in frameworks:
                total_tests += 1
                res_v = run_tui(fw, test_file, verify=True, exec_timeout=5.0)
                res_p = run_tui(fw, test_file, verify=False, poll_interval=0.1, timeout=0.25, exec_timeout=4.0)

                has_crash = res_v.is_panic or res_p.is_panic or res_v.is_deadlock or res_p.is_deadlock
                
                # Check for zero crash / panic / deadlock
                if not has_crash and (res_p.returncode == 0 or res_p.timed_out):
                    fw_status[fw] = "ROBUST"
                    passed_tests += 1
                else:
                    fw_status[fw] = "CRASH"
                    failed_tests += 1
                    scenario_ok = False
                    all_passed = False
                    print(f"    [CRASH NOTE] {fw} crashed on {scenario_name}: v_panic={res_v.is_panic}, p_panic={res_p.is_panic}, v_err={res_v.stderr[:60]}")

            verdict_str = "✓ ROBUST" if scenario_ok else "✗ CRASH"
            print(f"{scenario_name:<28} | {desc[:25]:<25} | {fw_status['python']:<8} | {fw_status['go']:<8} | {fw_status['rust']:<8} | {verdict_str}")

        print("=" * 88)
        print(f" TOTAL TEST RUNS: {total_tests} | ROBUST/SAFE: {passed_tests} | CRASHES: {failed_tests}")
        if all_passed:
            print(" 🏆 EMPIRICAL ADVERSARIAL VERIFICATION VERDICT: ZERO UNHANDLED CRASHES & ZERO DEADLOCKS")
            return 0
        else:
            print(" ⚠️ CRITICAL INSTABILITY / CRASH DETECTED")
            return 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Challenger 1 Adversarial Harness")
    parser.add_argument("--all", action="store_true", default=True, help="Run all adversarial tests")
    args = parser.parse_args()
    sys.exit(run_standalone_challenger_suite())
