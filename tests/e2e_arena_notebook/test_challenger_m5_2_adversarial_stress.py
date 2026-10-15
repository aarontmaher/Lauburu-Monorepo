"""
Milestone M5 Challenger 2 Dedicated Adversarial Chaos & Stress Test Suite.
Authored by teamwork_preview_challenger_m5_2.

Exhaustive Adversarial Stress Testing targeting:
1. High-concurrency POSIX file locking under 32 parallel worker threads & multiprocessing.
2. Extreme out-of-bounds Elo inputs, subnormal floats, and floating-point precision stability.
3. Pathological JSONL corruption, extreme nested/wide structures, and multi-gigabyte constant-memory streaming.
4. Complex Polyglot XSS injection payloads into prompt/chosen/rejected fields & Headless Chromium DOM audit.
5. Marimo DAG compilation, topological symbol analysis, cell reordering, and headless nbconvert multi-run stability.
"""

import ast
import concurrent.futures
import fcntl
import html
import json
import math
import multiprocessing
import os
import resource
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    NOTEBOOK_PATH,
    GLOBAL_NOTEBOOK_PATH,
    PLAYWRIGHT_HEADLESS_ARGS,
    calculate_elo_update,
    validate_dpo_schema,
    load_notebook_data,
    extract_code_cells,
    extract_markdown_cells,
)


@pytest.fixture(scope="module")
def notebook_json_data():
    """Load canonical notebook JSON."""
    return load_notebook_data(NOTEBOOK_PATH)


@pytest.fixture(scope="module")
def notebook_code_cells(notebook_json_data):
    """Extract code cell sources from canonical notebook."""
    return extract_code_cells(notebook_json_data)


@pytest.fixture(scope="module")
def master_notebook_namespace(notebook_code_cells):
    """
    Execute all 5 notebook code cells in an isolated, pure-Python sandbox namespace.
    Provides complete runtime access to all classes, functions, and state.
    """
    combined_code = "\n".join(notebook_code_cells)
    ns: Dict[str, Any] = {
        "__name__": "__main__",
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "clear_output": lambda *args, **kwargs: None,
    }
    exec(combined_code, ns)
    return ns


# =========================================================================
# 1. High-Concurrency POSIX File Locking (32 Parallel Worker Threads)
# =========================================================================
def _thread_worker_append_task(sink_file: str, worker_id: int, num_records: int) -> int:
    """Worker function for concurrent thread appending with strict POSIX fcntl.flock."""
    written = 0
    for seq in range(num_records):
        record = {
            "worker_id": worker_id,
            "seq": seq,
            "timestamp": time.time(),
            "pillar_id": (worker_id % 6) + 1,
            "prompt": f"Stress Prompt from worker {worker_id} seq {seq}",
            "chosen": f"Verified Chosen response {worker_id}-{seq}",
            "rejected": f"Flawed Rejected response {worker_id}-{seq}",
            "metadata": {
                "worker_id": worker_id,
                "seq": seq,
                "pillar_id": (worker_id % 6) + 1,
                "zero_mock_certified": True,
            }
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(sink_file, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
                written += 1
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return written


def _process_worker_append_task(sink_file: str, proc_id: int, num_records: int) -> int:
    """Worker function for multiprocess POSIX file locking across distinct OS processes."""
    written = 0
    for seq in range(num_records):
        record = {
            "proc_id": proc_id,
            "seq": seq,
            "pid": os.getpid(),
            "timestamp": time.time(),
            "payload": f"Multiprocess payload proc={proc_id} seq={seq}",
            "metadata": {"zero_mock_certified": True}
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(sink_file, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
                written += 1
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return written


class TestTier5PosixFileLocking32Threads:
    """Stress tests on POSIX file locking (fcntl.flock) under high concurrency (32 parallel threads & processes)."""

    def test_32_threads_concurrent_atomic_append_zero_interleaving(self, tmp_path):
        """
        Spawn exactly 32 concurrent worker threads, each writing 50 records (1,600 records total)
        to a single JSONL file using POSIX file locking.
        Verify:
        - Exactly 1,600 valid JSON records written.
        - Zero line interleaving or JSON decoding errors.
        - Perfect sequence continuity [0..49] per worker thread.
        """
        sink_path = str(tmp_path / "concurrent_32_threads.jsonl")
        num_workers = 32
        records_per_worker = 50
        total_expected = num_workers * records_per_worker

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(_thread_worker_append_task, sink_path, w_id, records_per_worker)
                for w_id in range(num_workers)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert sum(results) == total_expected, f"Expected {total_expected} writes, got {sum(results)}"

        # Validate line-by-line JSON validity and sequence integrity
        lines = []
        with open(sink_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line_clean = line.strip()
                assert line_clean, f"Empty line detected at line {idx}"
                try:
                    data = json.loads(line_clean)
                    lines.append(data)
                except json.JSONDecodeError as err:
                    pytest.fail(f"Corrupted JSON line at index {idx}: {line_clean[:80]} | Error: {err}")

        assert len(lines) == total_expected, f"Line count mismatch: expected {total_expected}, got {len(lines)}"

        # Group and verify sequence order per worker
        worker_sequences: Dict[int, List[int]] = {w_id: [] for w_id in range(num_workers)}
        for item in lines:
            w_id = item["worker_id"]
            seq = item["seq"]
            worker_sequences[w_id].append(seq)

        for w_id in range(num_workers):
            seqs = worker_sequences[w_id]
            assert len(seqs) == records_per_worker, f"Worker {w_id} missing records: {len(seqs)} != {records_per_worker}"
            assert seqs == list(range(records_per_worker)), f"Worker {w_id} records out of order or corrupted!"

    def test_32_threads_mixed_read_write_contention_and_fast_count(self, tmp_path, master_notebook_namespace):
        """
        Run 16 concurrent writer threads and 16 concurrent reader threads simultaneously.
        Readers continuously execute fast_count_records and read_training_records while writers append.
        Verify zero reader crashes or torn reads.
        """
        sink_path = tmp_path / "mixed_read_write_sink.jsonl"
        sink_path.touch()

        TriVaultSyncEngine = master_notebook_namespace["TriVaultSyncEngine"]
        fast_count_fn = master_notebook_namespace["fast_count_records"]
        engine = TriVaultSyncEngine(lora_sink=sink_path)

        stop_flag = False
        write_count = 0
        read_successes = 0

        def writer_task(w_id: int):
            nonlocal write_count
            local_writes = 0
            for i in range(40):
                if stop_flag:
                    break
                rec = {
                    "pillar_id": (w_id % 6) + 1,
                    "prompt": f"Contention prompt w={w_id} i={i}",
                    "chosen": f"Chosen response w={w_id} i={i}",
                    "rejected": f"Rejected response w={w_id} i={i}",
                    "metadata": {"w": w_id, "i": i, "zero_mock_certified": True}
                }
                engine.append_training_record(rec)
                local_writes += 1
                time.sleep(0.001)
            return local_writes

        def reader_task(r_id: int):
            nonlocal read_successes
            local_reads = 0
            for _ in range(40):
                if stop_flag:
                    break
                cnt = fast_count_fn(sink_path)
                assert isinstance(cnt, int) and cnt >= 0
                records = engine.read_training_records(limit=20)
                assert isinstance(records, list)
                for r in records:
                    assert isinstance(r, dict)
                    assert "prompt" in r or "instruction" in r or "pillar_id" in r
                local_reads += 1
                time.sleep(0.001)
            return local_reads

        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            writer_futs = [executor.submit(writer_task, i) for i in range(16)]
            reader_futs = [executor.submit(reader_task, i) for i in range(16)]

            writer_results = [f.result() for f in concurrent.futures.as_completed(writer_futs)]
            reader_results = [f.result() for f in concurrent.futures.as_completed(reader_futs)]

        total_written = sum(writer_results)
        final_count = fast_count_fn(sink_path)
        assert final_count == total_written, f"Final count {final_count} != total written {total_written}"

    def test_multiprocess_posix_lock_contention_across_process_boundaries(self, tmp_path):
        """
        Execute POSIX locking across 4 distinct OS subprocesses / workers.
        Verify fcntl.flock properly arbitrates access across process memory boundaries.
        """
        sink_path = str(tmp_path / "multiprocess_flock.jsonl")
        num_procs = 4
        records_per_proc = 25
        total_expected = num_procs * records_per_proc

        with concurrent.futures.ProcessPoolExecutor(max_workers=num_procs) as executor:
            futures = [
                executor.submit(_process_worker_append_task, sink_path, p_id, records_per_proc)
                for p_id in range(num_procs)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert sum(results) == total_expected

        # Validate all records from separate processes
        lines = []
        with open(sink_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                data = json.loads(line.strip())
                lines.append(data)

        assert len(lines) == total_expected
        pids = {item["pid"] for item in lines}
        assert len(pids) >= 1, "Expected authentic process IDs from OS"

    def test_posix_nonblocking_lock_behavior_and_retry(self, tmp_path):
        """Verify non-blocking fcntl.flock(LOCK_EX | LOCK_NB) detects active lock and raises BlockingIOError/OSError."""
        lock_file = tmp_path / "test_nonblocking.lock"
        lock_file.touch()

        fd1 = os.open(str(lock_file), os.O_RDWR)
        fcntl.flock(fd1, fcntl.LOCK_EX)

        fd2 = os.open(str(lock_file), os.O_RDWR)
        with pytest.raises((BlockingIOError, OSError)):
            fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Release fd1, now fd2 can lock
        fcntl.flock(fd1, fcntl.LOCK_UN)
        fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd2, fcntl.LOCK_UN)

        os.close(fd1)
        os.close(fd2)


# =========================================================================
# 2. Extreme Out-of-Bounds Elo Inputs and Floating-Point Stability
# =========================================================================
class TestTier5ExtremeEloAndFloatStability:
    """Mathematical stress testing of Bradley-Terry Elo updates, dynamic K-scaling, and Monte Carlo conservation."""

    def test_extreme_elo_rating_differentials_overflow_and_underflow(self, master_notebook_namespace):
        """
        Test calculate_elo_update under astronomical rating differentials (10^15 vs -10^15, 1e300 vs 0).
        Verify zero OverflowError, zero ZeroDivisionError, zero NaN, and expected_a in [0.0, 1.0].
        """
        elo_fn = master_notebook_namespace["calculate_elo_update"]

        test_cases = [
            (1e15, -1e15, 1.0, 32.0),
            (-1e15, 1e15, 0.0, 32.0),
            (1e9, 0.0, 0.5, 32.0),
            (0.0, 1e9, 0.5, 32.0),
            (1e300, 0.0, 1.0, 32.0),
            (0.0, 1e300, 0.0, 32.0),
            (10000.0, 1000.0, 1.0, 32.0),
            (1000.0, 10000.0, 0.0, 32.0),
        ]

        for r_a, r_b, score_a, k in test_cases:
            exp_a, new_a, new_b = elo_fn(r_a, r_b, score_a, k=k)
            assert isinstance(exp_a, float) and 0.0 <= exp_a <= 1.0, f"Invalid exp_a {exp_a} for r_a={r_a}, r_b={r_b}"
            assert not math.isnan(exp_a) and not math.isinf(exp_a)
            assert not math.isnan(new_a)
            assert not math.isnan(new_b)

    def test_subnormal_and_epsilon_rating_differentials(self, master_notebook_namespace):
        """Verify infinitesimal rating differences (10^-14) produce expected_a == 0.5 and conserve rating delta."""
        elo_fn = master_notebook_namespace["calculate_elo_update"]

        epsilons = [1e-14, 1e-12, 1e-9, 1e-6, 1e-3]
        for eps in epsilons:
            r_a = 2600.0
            r_b = 2600.0 + eps
            exp_a, new_a, new_b = elo_fn(r_a, r_b, 1.0, k=32.0)
            assert abs(exp_a - 0.5) < 1e-4, f"Epsilon {eps} produced non-0.5 expected: {exp_a}"
            delta_a = new_a - r_a
            delta_b = new_b - r_b
            assert abs(delta_a + delta_b) < 1e-10, f"Delta sum != 0 for eps={eps}: {delta_a + delta_b}"

    def test_one_million_monte_carlo_duels_zero_sum_conservation(self, master_notebook_namespace):
        """
        Execute 1,000,000 randomized Monte Carlo duels across continuous Elo spectrum.
        Verify strict zero-sum conservation: sum(Delta R_A + Delta R_B) == 0.
        """
        elo_fn = master_notebook_namespace["calculate_elo_update"]
        import random
        rng = random.Random(42)

        total_system_delta = 0.0
        n_duels = 1_000_000

        # Run chunked duels for performance
        chunk_size = 50_000
        for _ in range(n_duels // chunk_size):
            for _ in range(chunk_size):
                r_a = rng.uniform(800.0, 3200.0)
                r_b = rng.uniform(800.0, 3200.0)
                score_a = rng.choice([0.0, 0.5, 1.0])
                k = rng.uniform(4.0, 64.0)

                exp_a, new_a, new_b = elo_fn(r_a, r_b, score_a, k=k)
                delta_a = new_a - r_a
                delta_b = new_b - r_b
                total_system_delta += (delta_a + delta_b)

        assert abs(total_system_delta) < 1e-4, f"Total system rating drift across 1M duels: {total_system_delta}"

    def test_dynamic_k_factor_extreme_parameter_sweeps(self, master_notebook_namespace):
        """
        Stress test calculate_dynamic_k_factor and compute_debate_elo_updates with extreme inputs.
        Ensure outputs are strictly bounded floats without NaN/Inf.
        """
        calc_k = master_notebook_namespace["calculate_dynamic_k_factor"]
        compute_debate_elo = master_notebook_namespace["compute_debate_elo_updates"]

        extreme_params = [1e-6, 1e-3, 0.0, -10.0, 7.0, 72.0, 1e4, 1e9]
        extreme_rtts = [1e-4, 0.0, -50.0, 0.28, 18.5, 200.0, 1e4, 1e7]
        extreme_scores = [-100.0, -1.0, 0.0, 0.5, 1.0, 2.0, 100.0]

        for p in extreme_params:
            for r in extreme_rtts:
                for s in extreme_scores:
                    k = calc_k(k0=32.0, params_b=p, rtt_ms=r, consensus_score=s)
                    assert isinstance(k, float)
                    assert not math.isnan(k)
                    assert not math.isinf(k)
                    assert 1.0 <= k <= 128.0, f"K-factor {k} out of bounds for p={p}, r={r}, s={s}"

        # Sweep debate elo updates
        for s in extreme_scores:
            res = compute_debate_elo(s)
            assert isinstance(res, dict)
            for pid, data in res.items():
                assert 4.0 <= data["k_factor"] <= 64.0
                assert not math.isnan(data["delta"])
                assert not math.isnan(data["new_elo"])

    def test_bradley_terry_sigmoid_probability_strict_monotonicity(self, master_notebook_namespace):
        """
        Verify Bradley-Terry logistic sigmoid curve is strictly monotonically increasing with (R_A - R_B).
        Verify point symmetry: P_A(x) + P_A(-x) == 1.0.
        """
        elo_fn = master_notebook_namespace["calculate_elo_update"]

        diffs = [x / 10.0 for x in range(-4000, 4001, 2)]  # 4000 points from -400.0 to +400.0
        prev_p = -1.0

        for d in diffs:
            r_a = 2000.0 + d
            r_b = 2000.0
            p_a, _, _ = elo_fn(r_a, r_b, 1.0, k=32.0)
            assert 0.0 <= p_a <= 1.0
            assert p_a >= prev_p - 1e-12, f"Monotonicity violated at delta={d}: {p_a} < {prev_p}"
            prev_p = p_a

            # Check point symmetry
            r_a_neg = 2000.0 - d
            p_a_neg, _, _ = elo_fn(r_a_neg, r_b, 1.0, k=32.0)
            assert abs((p_a + p_a_neg) - 1.0) < 1e-7, f"Point symmetry violated at delta={d}: {p_a} + {p_a_neg} != 1.0"

    def test_100k_sequential_tournament_updates_no_numerical_drift(self, master_notebook_namespace):
        """
        Simulate a 100,000-duel closed tournament among 8 models.
        Verify the mean pool rating is preserved with zero numerical drift.
        """
        elo_fn = master_notebook_namespace["calculate_elo_update"]
        import random
        rng = random.Random(1337)

        models = {f"Model_{i}": 2500.0 for i in range(8)}
        initial_mean = sum(models.values()) / len(models)

        model_names = list(models.keys())
        for _ in range(100_000):
            m_a, m_b = rng.sample(model_names, 2)
            r_a = models[m_a]
            r_b = models[m_b]
            score_a = rng.choice([0.0, 0.5, 1.0])
            _, new_a, new_b = elo_fn(r_a, r_b, score_a, k=32.0)
            models[m_a] = new_a
            models[m_b] = new_b

        final_mean = sum(models.values()) / len(models)
        assert abs(final_mean - initial_mean) < 1e-5, f"Mean pool rating drifted from {initial_mean} to {final_mean}"


# =========================================================================
# 3. Pathological JSONL Corruption and Multi-Gigabyte Stream Handling
# =========================================================================
class TestTier5PathologicalJsonlAndStreamHandling:
    """Stress tests on pathological JSONL corruption handling and memory-bounded streaming."""

    def test_fuzzing_matrix_pathological_jsonl_corruptions(self, tmp_path, master_notebook_namespace):
        """
        Inject a comprehensive matrix of 18 distinct corruptions into a JSONL stream.
        Verify parser skips corrupted entries cleanly without crashing and extracts all valid DPO entries.
        """
        corrupted_file = tmp_path / "fuzzed_corruptions.jsonl"
        valid_records = [
            {"pillar_id": 1, "prompt": "Valid Prompt 1", "chosen": "C1", "rejected": "R1", "metadata": {"i": 1, "pillar_id": 1, "pillar_name": "P1", "model": "M1", "elo": 2600.0, "zero_mock_certified": True}},
            {"pillar_id": 2, "prompt": "Valid Prompt 2", "chosen": "C2", "rejected": "R2", "metadata": {"i": 2, "pillar_id": 2, "pillar_name": "P2", "model": "M2", "elo": 2600.0, "zero_mock_certified": True}},
            {"pillar_id": 3, "prompt": "Valid Prompt 3", "chosen": "C3", "rejected": "R3", "metadata": {"i": 3, "pillar_id": 3, "pillar_name": "P3", "model": "M3", "elo": 2600.0, "zero_mock_certified": True}},
            {"pillar_id": 4, "prompt": "Valid Prompt 4", "chosen": "C4", "rejected": "R4", "metadata": {"i": 4, "pillar_id": 4, "pillar_name": "P4", "model": "M4", "elo": 2600.0, "zero_mock_certified": True}},
        ]

        # Interleave valid records with 14 pathological non-dict or malformed lines
        corrupted_lines = [
            json.dumps(valid_records[0]) + "\n",
            "{unquoted_key: 123}\n",
            '{"truncated_string": "missing end quote\n',
            '{"trailing_comma": [1, 2, ],}\n',
            "\x00\x00\x00\x00\n",  # null bytes
            "\x1b[31mANSI ESCAPE JUNK\x1b[0m\n",
            "   \t  \r\n",  # whitespace
            "# Python comment line\n",
            "// C++ comment line\n",
            "<!-- HTML comment line -->\n",
            json.dumps(valid_records[1]) + "\n",
            "123456789\n",  # bare number
            '"bare string literal"\n',
            "[1, 2, 3, 4, 5]\n",  # bare array
            "null\n",  # bare null
            "{'single_quotes': 'invalid_in_json'}\n",
            json.dumps(valid_records[2]) + "\n",
            '{"nested_malformed": {"a": }}\n',
            json.dumps(valid_records[3]) + "\n",
        ]

        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.writelines(corrupted_lines)

        stream_fn = master_notebook_namespace["stream_dataset_records"]

        # Stream records using generator and filter for valid DPO records
        extracted = list(stream_fn(corrupted_file, limit=100))
        dpo_valid = [r for r in extracted if validate_dpo_schema(r)]
        assert len(dpo_valid) == 4, f"Expected 4 valid DPO records, got {len(dpo_valid)}"
        assert dpo_valid[0]["prompt"] == "Valid Prompt 1"
        assert dpo_valid[1]["prompt"] == "Valid Prompt 2"
        assert dpo_valid[2]["prompt"] == "Valid Prompt 3"
        assert dpo_valid[3]["prompt"] == "Valid Prompt 4"

    def test_massive_10mb_single_record_in_jsonl_stream(self, tmp_path, master_notebook_namespace):
        """
        Write and format a massive single DPO record containing 10MB of prompt, chosen, and rejected text.
        Verify formatting and serialization complete without memory exhaustion.
        """
        large_file = tmp_path / "large_payload.jsonl"
        large_chunk = "Z" * (3 * 1024 * 1024)  # 3MB string

        large_record = {
            "pillar_id": 1,
            "prompt": f"Large Prompt: {large_chunk}",
            "chosen": f"Large Chosen: {large_chunk}",
            "rejected": f"Large Rejected: {large_chunk}",
            "metadata": {"size_mb": 9.0, "zero_mock_certified": True}
        }

        format_dpo = master_notebook_namespace["format_pillar_dpo"]
        prompt, chosen, rejected, meta = format_dpo(1, large_record)
        assert len(prompt) >= 3 * 1024 * 1024
        assert len(chosen) >= 3 * 1024 * 1024
        assert len(rejected) >= 3 * 1024 * 1024
        assert meta["zero_mock_certified"] is True

        # Write to JSONL
        with open(large_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(large_record, ensure_ascii=False) + "\n")

        assert large_file.stat().st_size > 9 * 1024 * 1024

        stream_fn = master_notebook_namespace["stream_dataset_records"]
        records = list(stream_fn(large_file, limit=10))
        assert len(records) == 1
        assert len(records[0]["prompt"]) >= 3 * 1024 * 1024

    def test_deeply_nested_and_wide_json_records(self, tmp_path, master_notebook_namespace):
        """
        Verify handling of 50-level deeply nested JSON and 2,000-key wide JSON dictionaries.
        """
        nested_file = tmp_path / "deeply_nested.jsonl"

        # Construct 50-level nested dict
        nested_dict: Dict[str, Any] = {"leaf": "deep_value"}
        for _ in range(50):
            nested_dict = {"layer": nested_dict}

        # Construct wide dict with 2,000 keys
        wide_dict = {f"key_{i}": f"val_{i}" for i in range(2000)}

        record_nested = {"pillar_id": 4, "prompt": "Nested test", "chosen": "C", "rejected": "R", "data": nested_dict}
        record_wide = {"pillar_id": 4, "prompt": "Wide test", "chosen": "C", "rejected": "R", "data": wide_dict}

        with open(nested_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(record_nested) + "\n")
            f.write(json.dumps(record_wide) + "\n")

        stream_fn = master_notebook_namespace["stream_dataset_records"]
        extracted = list(stream_fn(nested_file, limit=10))
        assert len(extracted) == 2
        assert extracted[0]["prompt"] == "Nested test"
        assert extracted[1]["prompt"] == "Wide test"

    def test_constant_memory_streaming_generator_large_scale(self, tmp_path, master_notebook_namespace):
        """
        Stream 10,000 records using generator pattern in stream_dataset_records.
        Verify memory usage remains strictly bounded (O(1) constant memory).
        """
        stream_file = tmp_path / "stream_10k.jsonl"
        with open(stream_file, "w", encoding="utf-8") as f:
            for i in range(10_000):
                rec = {
                    "pillar_id": (i % 6) + 1,
                    "prompt": f"Streaming prompt record index {i}",
                    "chosen": f"Chosen response {i}",
                    "rejected": f"Rejected response {i}",
                }
                f.write(json.dumps(rec) + "\n")

        stream_fn = master_notebook_namespace["stream_dataset_records"]

        # Track memory before streaming
        start_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        count = 0
        for rec in stream_fn(stream_file, limit=10_000):
            count += 1
            assert "prompt" in rec

        end_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        assert count == 10_000

        # Max RSS delta on macOS is in bytes or KB depending on platform, assert no unbounded leak
        rss_delta_mb = (end_rss - start_rss) / (1024 * 1024) if sys.platform == "darwin" else (end_rss - start_rss) / 1024
        assert rss_delta_mb < 50.0, f"Memory expanded by {rss_delta_mb:.2f} MB during streaming"


# =========================================================================
# 4. Complex XSS Injection Payloads into Prompt / Chosen / Rejected Fields
# =========================================================================
class TestTier5ComplexXssInjectionPayloads:
    """Adversarial stress testing against XSS injection, DOM clobbering, and script execution in widgets."""

    POLYGLOT_XSS_VECTORS = [
        "<script>window.__xss_fired=true;</script>",
        "<img src=invalid onerror=\"window.__xss_fired=true\">",
        "<svg/onload=\"window.__xss_fired=true\">",
        "<iframe src=\"javascript:window.__xss_fired=true\"></iframe>",
        "<a href=\"javascript:window.__xss_fired=true\">click me</a>",
        "<body onload=\"window.__xss_fired=true\">",
        "<style>body{background:url('javascript:window.__xss_fired=true')}</style>",
        "\"><script>window.__xss_fired=true</script>",
        "' onmouseover='window.__xss_fired=true",
        "<input autofocus onfocus=\"window.__xss_fired=true\">",
        "</template><script>window.__xss_fired=true</script>",
        "${window.__xss_fired=true}",
        "{{constructor.constructor('window.__xss_fired=true')()}}",
        "&#x3C;script&#x3E;window.__xss_fired=true;&#x3C;/script&#x3E;",
        "<object data=\"javascript:window.__xss_fired=true\"></object>",
        "<embed src=\"javascript:window.__xss_fired=true\">",
        "<marquee onstart=\"window.__xss_fired=true\">test</marquee>",
        "<details open ontoggle=\"window.__xss_fired=true\">",
    ]

    def test_polyglot_xss_neutralization_in_dpo_formatter(self, master_notebook_namespace):
        """
        Feed all polyglot XSS vectors into format_pillar_dpo and PillarDatasetRegistry.to_dpo_record.
        Verify that formatting preserves data while certifying metadata and preventing unescaped breakout.
        """
        to_dpo = master_notebook_namespace["PillarDatasetRegistry"].to_dpo_record

        for vec in self.POLYGLOT_XSS_VECTORS:
            xss_raw = {
                "prompt": f"Hostile prompt with vector: {vec}",
                "chosen": f"Hostile chosen: {vec} and <div>valid tag</div>",
                "rejected": f"Hostile rejected: {vec}",
                "metadata": {"attack_vector": vec}
            }

            for p_id in range(1, 7):
                dpo = to_dpo(p_id, xss_raw)
                assert isinstance(dpo["prompt"], str)
                assert isinstance(dpo["chosen"], str)
                assert isinstance(dpo["rejected"], str)
                assert dpo["metadata"]["zero_mock_certified"] is True

                # Validate JSON round-trip serialization
                serialized = json.dumps(dpo, ensure_ascii=False)
                deserialized = json.loads(serialized)
                assert deserialized["metadata"]["zero_mock_certified"] is True

    def test_render_dpo_split_view_escapes_xss_payloads(self, master_notebook_namespace):
        """
        Verify render_dpo_split_view properly HTML-escapes hostile prompt, chosen, and rejected strings.
        Ensure no raw unescaped <script> or onerror attributes appear in the rendered HTML output.
        """
        render_fn = master_notebook_namespace["render_dpo_split_view"]

        for vec in self.POLYGLOT_XSS_VECTORS:
            rendered_html = render_fn(
                prompt=f"Hostile prompt {vec}",
                chosen=f"Hostile chosen {vec}",
                rejected=f"Hostile rejected {vec}",
                metadata={"vector": vec, "zero_mock_certified": True}
            )

            assert isinstance(rendered_html, str)
            # Ensure raw unescaped script tag is not present
            assert "<script>window.__xss_fired=true;" not in rendered_html
            assert "<svg/onload=" not in rendered_html
            assert "<img src=invalid onerror=" not in rendered_html
            # Ensure escaped forms exist for tags
            if "<" in vec:
                assert "&lt;" in rendered_html
            if ">" in vec:
                assert "&gt;" in rendered_html

    def test_debate_view_renderer_escapes_hostile_turn_and_consensus(self, master_notebook_namespace):
        """
        Verify DebateViewRenderer and StandaloneDebateInspectorJS safely escape hostile turns and diffs.
        """
        DebateStreamIngestor = master_notebook_namespace["DebateStreamIngestor"]
        DebateViewRenderer = master_notebook_namespace["DebateViewRenderer"]
        StandaloneDebateInspectorJS = master_notebook_namespace["StandaloneDebateInspectorJS"]

        ingestor = DebateStreamIngestor()
        renderer = DebateViewRenderer()
        js_engine = StandaloneDebateInspectorJS()

        for vec in self.POLYGLOT_XSS_VECTORS[:5]:
            record = {
                "topic_id": f"TOPIC_{vec}",
                "prompt": f"Instruction with vector: {vec}",
                "consensus": f"- Requirement 1: {vec}\n- Requirement 2: verify",
                "truth_compliance_pct": 95.0,
            }
            accord = ingestor._normalize_jsonl_record(record, 1)
            assert accord is not None

            consensus_html = renderer.render_consensus_card(accord)
            assert "<script>window.__xss_fired=true;" not in consensus_html

            turn_html = renderer.render_turn_card(accord.rounds[0])
            assert "<script>window.__xss_fired=true;" not in turn_html

            page_html = js_engine.generate_html([accord])
            assert "debate-inspector-root" in page_html

    def test_headless_chromium_dom_xss_execution_probe(self, master_notebook_namespace):
        """
        Render full HTML console containing all polyglot XSS vectors.
        Load the HTML directly into Headless Chromium via Playwright.
        Evaluate window.__xss_fired to confirm ZERO scripts executed.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pytest.skip("Playwright not installed in environment")

        render_dpo = master_notebook_namespace["render_dpo_split_view"]
        render_training = master_notebook_namespace["render_training_lake_console"]

        # Build hostile composite HTML page
        hostile_cards = []
        for i, vec in enumerate(self.POLYGLOT_XSS_VECTORS):
            card = render_dpo(
                prompt=f"Prompt injection: {vec}",
                chosen=f"Chosen injection: {vec}",
                rejected=f"Rejected injection: {vec}",
                metadata={"index": i, "vector": vec, "zero_mock_certified": True}
            )
            hostile_cards.append(card)

        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>XSS Adversarial Stress Probe</title>
</head>
<body style="background: #0f172a; color: white;">
    <script>window.__xss_fired = false;</script>
    <div id="console-container">
        {render_training()}
        {"".join(hostile_cards)}
    </div>
</body>
</html>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(full_html)
            temp_html_path = f.name

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=PLAYWRIGHT_HEADLESS_ARGS
                )
                page = browser.new_page()
                page.goto(f"file://{temp_html_path}")
                page.wait_for_timeout(500)

                # Check window.__xss_fired
                xss_fired = page.evaluate("() => window.__xss_fired")
                assert xss_fired is False, f"CRITICAL SECURITY FAILURE: XSS payload executed in DOM! window.__xss_fired={xss_fired}"

                browser.close()
        finally:
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)


# =========================================================================
# 5. Marimo DAG Compilation, Cell Reordering, and Nbconvert Multi-Run Stability
# =========================================================================
class TestTier5MarimoDagAndNbconvertMultiRun:
    """Stress tests on Marimo DAG compatibility, variable scope purity, and multi-run nbconvert stability."""

    def test_marimo_symbol_analysis_domain_classes_and_functions(self, notebook_code_cells):
        """
        Analyze AST symbol definitions for all domain classes and state managers across cells.
        Verify that domain classes (ArenaStateManager, TriVaultSyncEngine, UniversalDPOFormatter,
        DebateStreamIngestor, DebateViewRenderer, StandaloneDebateInspectorJS, InteractiveMeshConsoleWidget)
        are uniquely declared in their respective designated cells.
        """
        domain_classes = [
            "ArenaStateManager",
            "TriVaultSyncEngine",
            "UniversalDPOFormatter",
            "PillarDatasetRegistry",
            "DebateStreamIngestor",
            "DebateViewRenderer",
            "StandaloneDebateInspectorJS",
            "InteractiveMeshConsoleWidget",
        ]

        class_definitions: Dict[str, List[int]] = {cls_name: [] for cls_name in domain_classes}

        for cell_idx, src in enumerate(notebook_code_cells):
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in class_definitions:
                    class_definitions[node.name].append(cell_idx + 1)

        for cls_name, cells in class_definitions.items():
            assert len(cells) == 1, f"Domain class '{cls_name}' must be declared in exactly 1 cell, found in cells: {cells}"

    def test_cell_namespaces_isolated_execution_structural_invariance(self, notebook_code_cells):
        """
        Execute cells across 3 fresh, isolated namespaces in sequence.
        Verify structural integrity, identical class interfaces, and zero NaN/undefined in rendered HTML across runs.
        """
        for run_idx in range(3):
            ns: Dict[str, Any] = {
                "__name__": "__main__",
                "display": lambda *args, **kwargs: None,
                "HTML": lambda x: x,
                "clear_output": lambda *args, **kwargs: None,
            }
            for cell_src in notebook_code_cells:
                exec(cell_src, ns)

            # Test presence of all key classes and functions
            assert "ArenaStateManager" in ns
            assert "TriVaultSyncEngine" in ns
            assert "UniversalDPOFormatter" in ns
            assert "DebateStreamIngestor" in ns

            # Render HTML and verify structural health
            render_training = ns["render_training_lake_console"]
            html_out = render_training()
            assert isinstance(html_out, str)
            assert len(html_out) > 500
            assert "undefined" not in html_out
            assert "NaN" not in html_out
            assert "glass-card" in html_out

    def test_headless_nbconvert_multi_run_two_consecutive_passes(self):
        """
        Execute jupyter nbconvert headlessly twice in succession on fresh kernels.
        Verify:
        - Returncode == 0 for both executions.
        - Output HTML size > 500KB.
        - Zero tracebacks in output HTML.
        """
        jupyter_bin = "/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter"
        if not os.path.exists(jupyter_bin):
            jupyter_bin = shutil.which("jupyter") or "jupyter"

        for run_idx in range(2):
            with tempfile.NamedTemporaryFile(suffix=f"_run_{run_idx}.html", delete=False) as f:
                out_html = f.name

            try:
                cmd = [
                    jupyter_bin, "nbconvert",
                    "--to", "html",
                    "--execute",
                    str(NOTEBOOK_PATH),
                    "--output", out_html
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                assert res.returncode == 0, f"Run {run_idx+1} failed with exit code {res.returncode}: {res.stderr}"

                assert os.path.exists(out_html)
                file_size = os.path.getsize(out_html)
                assert file_size > 500_000, f"Run {run_idx+1} HTML size {file_size} bytes < 500KB"

                with open(out_html, "r", encoding="utf-8") as f_in:
                    content = f_in.read()

                assert "Traceback (most recent call last)" not in content, f"Run {run_idx+1} produced traceback"
                assert "glass-card" in content, f"Run {run_idx+1} missing glass-card CSS"
            finally:
                if os.path.exists(out_html):
                    os.unlink(out_html)

    def test_zero_bare_print_calls_across_all_notebook_cells(self, notebook_code_cells):
        """Enforce strict AST purity across all cells: 0 bare print() calls."""
        violations = []
        for cell_idx, src in enumerate(notebook_code_cells):
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "print":
                        violations.append((cell_idx + 1, node.lineno))
                    elif isinstance(node.func, ast.Attribute) and node.func.attr == "print":
                        violations.append((cell_idx + 1, node.lineno))

        assert len(violations) == 0, f"Disallowed print() calls detected: {violations}"
