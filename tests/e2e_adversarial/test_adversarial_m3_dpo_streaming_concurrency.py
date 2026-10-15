#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
LAUBURU MONOREPO: ADVERSARIAL CHALLENGER TEST SUITE (MILESTONE M3)
DPO Formatter Robustness, Multi-Process Concurrency Safety, & 400MB+ Dataset Streaming
================================================================================
Classification: Empirical Stress Testing • Zero-Mock Audit • Concurrency & Memory Safety
"""
import os
import sys
import gc
import json
import math
import time
import uuid
import psutil
import shutil
import tempfile
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Iterator

import pytest
import pyarrow as pa
import pyarrow.dataset as ds

# Enforce headless matplotlib backend as per critical directive
try:
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "04_data_and_memory"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))

from tri_vault_sink import TriVaultSink, verify_zero_mock_compliance
from delta_engine.schema import (
    DPO_PREFERENCE_ARROW_SCHEMA,
    SFT_TRAINING_ARROW_SCHEMA,
    normalize_record,
    records_to_arrow_table,
    get_schema_by_name,
)
from delta_engine.writer import DeltaDatasetWriter
from delta_engine.mmap_loader import MemoryMappedDatasetLoader
from delta_engine.migrator import JSONLToDeltaMigrator


# ==============================================================================
# WORKER FUNCTIONS FOR MULTI-PROCESS CONCURRENCY STRESS
# ==============================================================================

def _worker_safe_append_contention(
    worker_id: int,
    target_file: str,
    num_records: int,
    payload_type: str = "mixed"
) -> Tuple[int, int, List[str]]:
    """
    Worker process function for high-concurrency atomic appends.
    Appends varied payload sizes (small, medium, large > 4KB).
    Returns (worker_id, successful_writes, list_of_errors).
    """
    errors: List[str] = []
    successes = 0
    target_path = Path(target_file)
    sink = TriVaultSink(lora_dir=target_path.parent, secondary_lora_dir=target_path.parent)

    for i in range(num_records):
        rec_id = f"proc_{worker_id}_rec_{i:04d}_{uuid.uuid4().hex[:6]}"
        
        if payload_type == "small":
            payload_content = f"Small content payload {i}"
        elif payload_type == "large":
            # Exceed POSIX PIPE_BUF (4096 bytes) to stress atomic append boundaries
            payload_content = f"Large content payload {i}: " + ("x" * 6000)
        else: # mixed
            if i % 3 == 0:
                payload_content = f"Small {i}"
            elif i % 3 == 1:
                payload_content = f"Medium payload {i}: " + ("m" * 1500)
            else:
                payload_content = f"Large payload {i}: " + ("L" * 7500)

        record = {
            "trial_id": rec_id,
            "worker_pid": os.getpid(),
            "worker_id": worker_id,
            "seq_num": i,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "domain": "concurrency_stress_test",
            "prompt": f"Stress test prompt from worker {worker_id} iteration {i}",
            "chosen": f"Verified robust execution output for {rec_id}. {payload_content}",
            "rejected": f"Sub-optimal interleaved execution for {rec_id}.",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True,
            "scores": {"correctness": 100.0, "latency_ms": 1.25},
        }

        try:
            # Test direct safe_append_jsonl under multi-process contention
            sink.safe_append_jsonl(target_path, record)
            successes += 1
        except Exception as e:
            errors.append(f"Write failed on record {rec_id}: {type(e).__name__}: {str(e)}")

    return (worker_id, successes, errors)


def _worker_dpo_export_contention(
    worker_id: int,
    lora_dir: str,
    target_filename: str,
    num_records: int,
) -> Tuple[int, int, List[str]]:
    """
    Worker process testing TriVaultSink.export_dpo_pair under multi-process contention.
    """
    errors: List[str] = []
    successes = 0
    lora_path = Path(lora_dir)
    sink = TriVaultSink(lora_dir=lora_path, secondary_lora_dir=lora_path)

    for i in range(num_records):
        trial_id = f"trial_w{worker_id}_{i:04d}_{uuid.uuid4().hex[:6]}"
        trial_record = {
            "trial_id": trial_id,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prompt": f"Benchmark task prompt {worker_id}-{i}",
            "winner_id": f"qwen_moe_worker_{worker_id}",
            "winner_alias": "gamma",
            "judicial_rationale": f"Optimal AST transformation with zero mock data {i}: " + ("Z" * (1000 if i % 2 == 0 else 5000)),
            "pairwise_matches": [
                {"winner_id": f"qwen_moe_worker_{worker_id}", "loser_id": f"inferior_model_{worker_id}"}
            ],
            "total_scores": {f"qwen_moe_worker_{worker_id}": 98.5},
            "scores": {"ast_syntax": 100.0, "truth_compliance": 100.0},
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True,
        }

        try:
            sink.export_dpo_pair(trial_record, target_filename=target_filename)
            successes += 1
        except Exception as e:
            errors.append(f"DPO export failed on {trial_id}: {type(e).__name__}: {str(e)}")

    return (worker_id, successes, errors)


# ==============================================================================
# TEST SUITE: DPO FORMATTER ROBUSTNESS & FUZZING
# ==============================================================================

class TestDPOFormatterRobustness:
    """
    Adversarial stress-testing of DPO Formatters across TriVaultSink,
    SyntheticDebateEngine, Delta Engine Schema, and Migrator.
    """

    @pytest.fixture
    def workspace(self):
        tmp = tempfile.mkdtemp(prefix="m3_dpo_test_")
        yield Path(tmp)
        if os.path.exists(tmp):
            shutil.rmtree(tmp)

    def test_dpo_formatter_empty_and_missing_keys_rule_zero(self, workspace):
        """
        Verify that TriVaultSink rejects missing prompts under Rule #0 enforcement,
        and gracefully formats records when prompt is present but optional fields are missing.
        """
        sink_strict = TriVaultSink(lora_dir=workspace, secondary_lora_dir=workspace, enforce_rule_zero=True)
        sink_permissive = TriVaultSink(lora_dir=workspace, secondary_lora_dir=workspace, enforce_rule_zero=False)
        
        # Test 1: Missing prompt under strict Rule #0 -> Must raise ValueError
        empty_record = {}
        with pytest.raises(ValueError) as exc:
            sink_strict.export_dpo_pair(empty_record, target_filename="empty_dpo.jsonl")
        assert "Rule #0 Violation: Empty or missing prompt" in str(exc.value)

        # Test 2: Permissive mode -> Populates all default keys gracefully
        res_perm = sink_permissive.export_dpo_pair(empty_record, target_filename="perm_empty_dpo.jsonl")
        assert "trial_id" in res_perm
        assert "prompt" in res_perm
        assert res_perm["prompt"] == ""
        assert "chosen" in res_perm
        assert "rejected" in res_perm
        assert "meta" in res_perm
        assert res_perm["meta"]["zero_mock_certified"] is True

        # Test 3: Valid prompt but missing optional fields (winner_alias, pairwise_matches, scores)
        partial_record = {
            "trial_id": "partial-001",
            "prompt": "Optimize tensor parallel RPC sharding",
            "winner_id": "qwen_2.5_coder",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True,
        }
        res3 = sink_strict.export_dpo_pair(partial_record, target_filename="partial_dpo.jsonl")
        assert res3["trial_id"] == "partial-001"
        assert res3["prompt"] == "Optimize tensor parallel RPC sharding"
        assert "Winner (qwen_2.5_coder" in res3["chosen"]
        assert "Sub-optimal reasoning solution" in res3["rejected"]

    def test_dpo_formatter_non_string_types(self, workspace):
        """Test DPO export with non-string types in all string fields."""
        sink = TriVaultSink(lora_dir=workspace, secondary_lora_dir=workspace, enforce_rule_zero=False)

        # Fuzz with complex types (int, float, list, dict, None, bool)
        fuzz_record = {
            "trial_id": 99999,
            "prompt": "Valid string prompt for fuzzer",
            "winner_id": "model_alpha",
            "winner_alias": 42.5,
            "judicial_rationale": "Empirical mathematical proof of 10Gbps bridge",
            "pairwise_matches": [{"winner_id": "model_alpha", "loser_id": "model_beta"}],
            "scores": {"ast_syntax": 100.0},
            "total_scores": {"model_alpha": 99.0},
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True,
        }

        res = sink.export_dpo_pair(fuzz_record, target_filename="fuzz_dpo.jsonl")
        assert res is not None
        assert "trial_id" in res
        assert "chosen" in res
        assert "rejected" in res

        # Verify output file is valid JSONL
        out_file = workspace / "fuzz_dpo.jsonl"
        assert out_file.exists()
        with open(out_file, "r", encoding="utf-8") as f:
            line = f.readline()
            parsed = json.loads(line)
            assert str(parsed["trial_id"]) == "99999"

    def test_dpo_formatter_corrupted_unicode_and_huge_payloads(self, workspace):
        """Test DPO export with emojis, null bytes, escaped quotes, and huge strings."""
        sink = TriVaultSink(lora_dir=workspace, secondary_lora_dir=workspace)

        huge_prompt = "🔥" * 5000 + " \x00\x01\x02 " + "Line 1\nLine 2\r\nLine 3\tTabbed" + '{"key": "value\\"escaped"}'
        huge_rationale = "A" * (2 * 1024 * 1024) # 2 MB rationale string

        record = {
            "trial_id": "huge-unicode-001",
            "prompt": huge_prompt,
            "winner_id": "gemini_pro_ultra",
            "judicial_rationale": huge_rationale,
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True,
        }

        res = sink.export_dpo_pair(record, target_filename="huge_dpo.jsonl")
        assert res["trial_id"] == "huge-unicode-001"
        assert len(res["chosen"]) >= 2 * 1024 * 1024

        out_file = workspace / "huge_dpo.jsonl"
        with open(out_file, "r", encoding="utf-8") as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed["trial_id"] == "huge-unicode-001"
            assert "🔥" in parsed["prompt"]

    def test_dpo_schema_normalization_and_arrow_conversion(self):
        """Test delta_engine PyArrow schema normalization for DPO pairs with corrupted types."""
        raw_records = [
            # Record 1: All None
            {},
            # Record 2: Nested types in string fields
            {
                "pair_id": 101,
                "category": ["edge", "routing"],
                "dimension": {"dim": "throughput"},
                "prompt": {"role": "user", "content": "Explain 10Gbps bridge"},
                "chosen": {"proof": "0.277ms latency verified"},
                "rejected": 500,
                "consensus_score": "95.5",
                "source": None,
                "timestamp": "2026-09-01T12:00:00Z",
                "metadata_json": {"audit": "pass"},
            },
            # Record 3: Numeric timestamps, negative scores, nan values
            {
                "pair_id": "pair_003",
                "category": "biometrics",
                "dimension": "dfa_alpha1",
                "prompt": "Compute Pan-Tompkins QRS",
                "chosen": "Valid R-peak detected at 512Hz",
                "rejected": "Flat line mock array",
                "consensus_score": -10.0,
                "source": "Mac_Node",
                "timestamp": 1756700000.123,
                "metadata_json": '{"zero_mock": true}',
            }
        ]

        normalized = [normalize_record(r, DPO_PREFERENCE_ARROW_SCHEMA) for r in raw_records]
        assert len(normalized) == 3
        
        # Verify normalized fields conform to PyArrow types
        table = records_to_arrow_table(raw_records, schema=DPO_PREFERENCE_ARROW_SCHEMA)
        assert isinstance(table, pa.Table)
        assert table.num_rows == 3
        assert table.schema == DPO_PREFERENCE_ARROW_SCHEMA

        # Check Record 2 string serialization of nested dicts
        pylist = table.to_pylist()
        assert "Explain 10Gbps bridge" in pylist[1]["prompt"]
        assert pylist[1]["consensus_score"] == 95.5

    def test_dpo_migrator_transform_record_resilience_and_vulnerabilities(self):
        """
        Test JSONLToDeltaMigrator.transform_record on edge cases,
        documenting handling of corrupted consensus_score strings.
        """
        valid_case = {"id": "custom_id_123", "instruction": "Migrate me", "positive": "Good", "negative": "Bad"}
        transformed = JSONLToDeltaMigrator.transform_record(valid_case, schema_type="dpo_preference")
        assert transformed["pair_id"] == "custom_id_123"
        assert transformed["prompt"] == "Migrate me"
        assert transformed["chosen"] == "Good"
        assert transformed["rejected"] == "Bad"
        assert transformed["consensus_score"] == 100.0

        # Empirical challenge: Non-numeric consensus_score string (e.g. 'N/A') raises ValueError in migrator
        with pytest.raises(ValueError) as exc_info:
            JSONLToDeltaMigrator.transform_record({"consensus_score": "unparseable_string"}, schema_type="dpo_preference")
        assert "could not convert string to float" in str(exc_info.value)

    def test_dpo_rule_zero_quarantine(self, workspace):
        """Test that DPO exporter strictly quarantines Rule #0 zero-mock violations."""
        sink = TriVaultSink(lora_dir=workspace, secondary_lora_dir=workspace, enforce_rule_zero=True)

        fake_record = {
            "trial_id": "fake-001",
            "prompt": "Run simulated test",
            "chosen": "Generated mock_data simulation array",
            "truth_verified": False, # Violation!
            "truth_compliance_pct": 50.0,
            "zero_mock": False,
        }

        with pytest.raises(ValueError) as exc_info:
            sink.export_dpo_pair(fake_record)
        assert "Rule #0 Violation" in str(exc_info.value)
        assert sink.get_metrics()["rule_zero_violations_quarantined"] == 1


# ==============================================================================
# TEST SUITE: MULTI-PROCESS CONCURRENT ATOMIC APPEND CONTENTION
# ==============================================================================

class TestConcurrentAtomicAppendsContention:
    """
    Adversarial stress-testing of multi-process concurrent write contention
    targeting continuous_lora_dataset.jsonl and Delta tables.
    """

    @pytest.fixture
    def contention_dir(self):
        tmp = tempfile.mkdtemp(prefix="m3_concurrency_stress_")
        yield Path(tmp)
        if os.path.exists(tmp):
            shutil.rmtree(tmp)

    def test_multi_process_safe_append_contention(self, contention_dir):
        """
        Stress test: 8 worker processes concurrently appending 250 records each (2,000 total)
        with mixed small, medium, and large (>4KB) payloads to the exact same JSONL file.
        """
        target_file = contention_dir / "continuous_lora_dataset.jsonl"
        num_workers = 8
        records_per_worker = 250
        expected_total_records = num_workers * records_per_worker

        start_time = time.perf_counter()

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(
                    _worker_safe_append_contention,
                    worker_id=w,
                    target_file=str(target_file),
                    num_records=records_per_worker,
                    payload_type="mixed"
                )
                for w in range(num_workers)
            ]

            results = [f.result() for f in as_completed(futures)]

        duration = time.perf_counter() - start_time
        total_successes = sum(r[1] for r in results)
        all_errors = [err for r in results for err in r[2]]

        # Verification 1: Zero errors reported by worker processes
        assert len(all_errors) == 0, f"Encountered {len(all_errors)} worker errors: {all_errors[:5]}"
        assert total_successes == expected_total_records

        # Verification 2: File exists and has content
        assert target_file.exists()
        file_size_mb = target_file.stat().st_size / (1024 * 1024)

        # Verification 3: Every single line in JSONL is parseable (NO interleaved lines or corruption)
        parsed_records = []
        corrupted_lines = 0
        with open(target_file, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    obj = json.loads(clean_line)
                    parsed_records.append(obj)
                except json.JSONDecodeError as e:
                    corrupted_lines += 1
                    print(f"CORRUPTED LINE {line_idx}: {e}\nContent snippet: {line[:200]}")

        assert corrupted_lines == 0, f"Found {corrupted_lines} corrupted/interleaved lines!"
        assert len(parsed_records) == expected_total_records

        # Verification 4: All worker IDs and sequence numbers accounted for with zero loss
        worker_seq_map = {w: set() for w in range(num_workers)}
        for rec in parsed_records:
            w_id = rec["worker_id"]
            seq = rec["seq_num"]
            worker_seq_map[w_id].add(seq)

        for w in range(num_workers):
            assert len(worker_seq_map[w]) == records_per_worker, f"Worker {w} lost writes!"

        throughput = expected_total_records / duration
        print(f"\n✅ Multi-Process Concurrency Passed: {expected_total_records} records ({file_size_mb:.2f} MB) written in {duration:.2f}s ({throughput:.1f} rec/s)")

    def test_multi_process_dpo_export_contention(self, contention_dir):
        """
        Stress test: 6 worker processes executing TriVaultSink.export_dpo_pair concurrently.
        """
        target_filename = "continuous_lora_dataset.jsonl"
        num_workers = 6
        records_per_worker = 150
        expected_total = num_workers * records_per_worker

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(
                    _worker_dpo_export_contention,
                    worker_id=w,
                    lora_dir=str(contention_dir),
                    target_filename=target_filename,
                    num_records=records_per_worker,
                )
                for w in range(num_workers)
            ]
            results = [f.result() for f in as_completed(futures)]

        all_errors = [err for r in results for err in r[2]]
        assert len(all_errors) == 0

        target_file = contention_dir / target_filename
        assert target_file.exists()

        valid_lines = 0
        with open(target_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    assert "trial_id" in obj
                    assert "chosen" in obj
                    assert "rejected" in obj
                    valid_lines += 1

        assert valid_lines == expected_total


# ==============================================================================
# TEST SUITE: 400MB+ DATASET STREAMING PERFORMANCE & MEMORY SPIKE BENCHMARK
# ==============================================================================

class TestStreamingPerformance400MB:
    """
    Adversarial stress-testing of dataset streaming performance on 400MB+ dataset files.
    Empirically measures RSS memory footprint to ensure zero memory spikes (< 50MB delta).
    """

    @pytest.fixture
    def large_dataset_dir(self):
        tmp = tempfile.mkdtemp(prefix="m3_large_stream_")
        yield Path(tmp)
        if os.path.exists(tmp):
            shutil.rmtree(tmp)

    def _generate_400mb_jsonl(self, file_path: Path, target_size_mb: float = 410.0) -> int:
        """
        Generates a 400MB+ JSONL dataset containing realistic DPO and SFT training pairs.
        Returns total number of records generated.
        """
        target_bytes = int(target_size_mb * 1024 * 1024)
        bytes_written = 0
        record_idx = 0
        
        # Standard synthetic payload block (~4 KB per record)
        base_rationale = (
            "Detailed architectural synthesis: "
            "1. Verified AST syntax integrity across all diff mutations.\n"
            "2. Evaluated 10Gbps Thunderbolt 4 PCIe DMA low-latency bridge performance.\n"
            "3. Enforced Rule #0 Zero-Mock truth verification with 100% compliance.\n"
            "4. Confirmed sub-millisecond memory-mapped dataset streaming.\n"
            + ("Qwen MoE synthesis proof step " * 80)
        )

        with open(file_path, "w", encoding="utf-8") as f:
            while bytes_written < target_bytes:
                record = {
                    "pair_id": f"dpo_stream_{record_idx:07d}",
                    "category": "multi_path_physics" if record_idx % 2 == 0 else "biometrics_dsp",
                    "dimension": "V2_high_throughput",
                    "prompt": f"Benchmark prompt query for training instance {record_idx}: Optimize tensor sharding.",
                    "chosen": f"Approved solution {record_idx}: {base_rationale}",
                    "rejected": f"Rejected sub-optimal solution {record_idx}: Failed on token economy.",
                    "consensus_score": 98.5,
                    "source": "TriOrchestrator_Council",
                    "timestamp": "2026-09-01T15:30:00Z",
                    "metadata_json": json.dumps({"batch_id": record_idx // 1000, "verified": True}),
                }
                line = json.dumps(record, ensure_ascii=False) + "\n"
                f.write(line)
                bytes_written += len(line.encode("utf-8"))
                record_idx += 1

                if record_idx % 5000 == 0:
                    f.flush()

        return record_idx

    def test_400mb_jsonl_streaming_memory_footprint(self, large_dataset_dir):
        """
        Generates 400MB+ JSONL file and streams line-by-line using generator.
        Verifies constant memory footprint (delta RSS < 50MB) across entire file.
        """
        jsonl_file = large_dataset_dir / "continuous_lora_large_400mb.jsonl"
        print(f"\n[1/3] Generating 400MB+ JSONL dataset at {jsonl_file}...")
        t_gen_start = time.perf_counter()
        total_records = self._generate_400mb_jsonl(jsonl_file, target_size_mb=410.0)
        t_gen_dur = time.perf_counter() - t_gen_start
        file_size_mb = jsonl_file.stat().st_size / (1024 * 1024)
        print(f"Generated {total_records} records ({file_size_mb:.2f} MB) in {t_gen_dur:.2f}s")
        assert file_size_mb >= 400.0

        # Memory baseline before streaming
        gc.collect()
        proc = psutil.Process(os.getpid())
        rss_start_mb = proc.memory_info().rss / (1024 * 1024)
        peak_rss_mb = rss_start_mb

        print(f"[2/3] Streaming {file_size_mb:.2f} MB dataset line-by-line...")
        t_stream_start = time.perf_counter()
        streamed_count = 0
        sample_checkpoints = []

        def jsonl_stream_generator(path: Path) -> Iterator[Dict[str, Any]]:
            with open(path, "r", encoding="utf-8") as f:
                for l in f:
                    if l.strip():
                        yield json.loads(l)

        for rec in jsonl_stream_generator(jsonl_file):
            streamed_count += 1
            # Periodic memory checkpoint every 10,000 records
            if streamed_count % 10000 == 0:
                current_rss_mb = proc.memory_info().rss / (1024 * 1024)
                if current_rss_mb > peak_rss_mb:
                    peak_rss_mb = current_rss_mb
                sample_checkpoints.append((streamed_count, current_rss_mb))

        t_stream_dur = time.perf_counter() - t_stream_start
        rss_end_mb = proc.memory_info().rss / (1024 * 1024)
        delta_rss_mb = peak_rss_mb - rss_start_mb
        throughput_mb_s = file_size_mb / t_stream_dur
        throughput_rec_s = streamed_count / t_stream_dur

        print(f"[3/3] Streaming Complete:")
        print(f"  - Total records streamed: {streamed_count} / {total_records}")
        print(f"  - Duration: {t_stream_dur:.2f}s ({throughput_mb_s:.1f} MB/s, {throughput_rec_s:.0f} rec/s)")
        print(f"  - RSS Start: {rss_start_mb:.2f} MB | Peak: {peak_rss_mb:.2f} MB | End: {rss_end_mb:.2f} MB")
        print(f"  - Max RSS Delta: {delta_rss_mb:.2f} MB")

        # Assertions
        assert streamed_count == total_records
        assert delta_rss_mb < 50.0, f"Memory spiked by {delta_rss_mb:.2f} MB (exceeded 50 MB threshold)!"

    def test_memory_mapped_hf_dataset_load_zero_copy(self, large_dataset_dir):
        """
        Verifies HuggingFace zero-copy dataset loading (MemoryMappedTable)
        on Delta Lake Parquet files maintains memory footprint < 50MB delta.
        """
        delta_table_dir = large_dataset_dir / "delta_dpo_sample_table"
        writer = DeltaDatasetWriter(table_uri=delta_table_dir, schema=DPO_PREFERENCE_ARROW_SCHEMA)
        
        # Write 5,000 realistic records
        batch = []
        for i in range(5000):
            batch.append({
                "pair_id": f"hf_mmap_{i:05d}",
                "category": "multi_path",
                "dimension": "speedify",
                "prompt": f"Query {i}",
                "chosen": "Valid output with verified AST proof " * 20,
                "rejected": "Invalid sub-optimal output " * 20,
                "consensus_score": 99.0,
                "source": "Mac_Node",
                "timestamp": "2026-09-01T12:00:00Z",
                "metadata_json": '{"zero_mock": true}',
            })
        writer.write(batch)

        # Measure RSS footprint with MemoryMappedDatasetLoader
        metrics = MemoryMappedDatasetLoader.measure_rss_footprint(delta_table_dir)
        print(f"\n✅ HF Zero-Copy Dataset Load: {metrics}")
        assert metrics["rows_loaded"] == 5000
        assert metrics["zero_copy_verified"] is True
        assert metrics["delta_rss_mb"] < 50.0


# ==============================================================================
# MAIN ENTRYPOINT FOR STANDALONE EXECUTION
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
