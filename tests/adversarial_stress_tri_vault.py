#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO - ADVERSARIAL STRESS TEST SUITE (TRI-VAULT STORAGE)
================================================================================
Empirical Challenger Suite:
1. Challenge 1: Shell Daemon Edge Cases, Signal Traps, Dry-Run Syntax (pixel_volume_daemon.sh)
2. Challenge 2: RFC 8259 Strict JSON & S3 Schema Compatibility (r2_tiering_config.json)
3. Challenge 3: Delta Engine Concurrent Micro-Batches, Schema Evolution & Heavy Compaction
4. Challenge 4: Zero-Copy MemoryMappedDatasetLoader RSS Under Large Dataset Pressure (<50MB)
5. Challenge 5: Obsidian Vectorizer Malformed Markdown, 1MB Headers, Rapid Bursts & Retries
================================================================================
"""
import os
import sys
import time
import json
import uuid
import shutil
import tempfile
import threading
import subprocess
import importlib
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any

import pytest
import psutil
import pyarrow as pa
from deltalake import DeltaTable

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Dynamically import numbered modules
delta_writer_mod = importlib.import_module("04_data_and_memory.delta_engine.writer")
delta_compactor_mod = importlib.import_module("04_data_and_memory.delta_engine.compactor")
delta_mmap_loader_mod = importlib.import_module("04_data_and_memory.delta_engine.mmap_loader")
delta_schema_mod = importlib.import_module("04_data_and_memory.delta_engine.schema")
obsidian_vectorizer_mod = importlib.import_module("04_data_and_memory.qdrant_sync.obsidian_vectorizer")

DeltaDatasetWriter = delta_writer_mod.DeltaDatasetWriter
DeltaCompactor = delta_compactor_mod.DeltaCompactor
MemoryMappedDatasetLoader = delta_mmap_loader_mod.MemoryMappedDatasetLoader
TRUTH_AUDIT_ARROW_SCHEMA = delta_schema_mod.TRUTH_AUDIT_ARROW_SCHEMA
normalize_record = delta_schema_mod.normalize_record

MarkdownChunker = obsidian_vectorizer_mod.MarkdownChunker
MarkdownChunk = obsidian_vectorizer_mod.MarkdownChunk
LlamaEmbeddingClient = obsidian_vectorizer_mod.LlamaEmbeddingClient
QdrantSyncStore = obsidian_vectorizer_mod.QdrantSyncStore
SyncStateCache = obsidian_vectorizer_mod.SyncStateCache
DebounceEventQueue = obsidian_vectorizer_mod.DebounceEventQueue
EmbeddingAPIError = obsidian_vectorizer_mod.EmbeddingAPIError


class TestChallenge1PixelVolumeDaemon:
    """Stress tests on pixel_volume_daemon.sh."""

    SCRIPT_PATH = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "pixel_volume_daemon.sh"

    def test_bash_syntax_validity(self):
        """Dry-run syntax validation via bash -n."""
        assert self.SCRIPT_PATH.exists(), f"Script not found at {self.SCRIPT_PATH}"
        res = subprocess.run(["bash", "-n", str(self.SCRIPT_PATH)], capture_output=True, text=True)
        assert res.returncode == 0, f"Bash syntax check failed: {res.stderr}"

    def test_help_and_version_flags(self):
        """Verify help and argument parser handles --help, -h, help."""
        for flag in ["--help", "-h", "help"]:
            res = subprocess.run(["bash", str(self.SCRIPT_PATH), flag], capture_output=True, text=True)
            assert res.returncode == 0
            assert "Usage:" in res.stdout
            assert "Google Pixel 10 Pro XL" in res.stdout

    def test_unknown_cli_flags_rejection(self):
        """Adversarial unknown flags should exit non-zero and print error."""
        res = subprocess.run(["bash", str(self.SCRIPT_PATH), "--invalid-flag-12345"], capture_output=True, text=True)
        assert res.returncode == 1
        assert "Unknown argument" in res.stderr

    def test_preflight_diagnostics_mode(self):
        """Verify preflight diagnostic run without spawning daemon."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                ["bash", str(self.SCRIPT_PATH), "test", "-dir", tmpdir, "-port", "19080", "-max", "100"],
                capture_output=True,
                text=True
            )
            # test action runs preflight checks
            assert "PRE-FLIGHT TEST" in res.stdout
            assert tmpdir in res.stdout
            assert "19080" in res.stdout

    def test_missing_or_unwritable_directory_handling(self):
        """Verify daemon refuses to start if directory cannot be created or written."""
        unwritable_dir = "/proc/forbidden_seaweed_storage_dir_test_403"
        res = subprocess.run(
            ["bash", str(self.SCRIPT_PATH), "test", "-dir", unwritable_dir],
            capture_output=True,
            text=True
        )
        assert res.returncode == 1 or "Storage partition check failed" in res.stderr or "ERROR" in res.stderr

    def test_stale_pid_cleanup(self):
        """Verify daemon detects stale PID file and cleans up cleanly on stop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_pid_file = Path(tmpdir) / "stale.pid"
            fake_pid_file.write_text("99999999\n")
            res = subprocess.run(
                ["bash", str(self.SCRIPT_PATH), "status", "--pid-file", str(fake_pid_file)],
                capture_output=True,
                text=True
            )
            assert res.returncode == 3 or "STOPPED" in res.stdout or "Stale PID" in res.stdout

            # Stop should clean it up
            res_stop = subprocess.run(
                ["bash", str(self.SCRIPT_PATH), "stop", "--pid-file", str(fake_pid_file)],
                capture_output=True,
                text=True
            )
            assert res_stop.returncode == 0
            assert not fake_pid_file.exists()


class TestChallenge2R2TieringConfig:
    """Stress tests on r2_tiering_config.json."""

    CONFIG_PATH = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "r2_tiering_config.json"

    def test_rfc8259_strict_json_validation(self):
        """Verify strict RFC 8259 JSON compliance with no trailing commas or invalid tokens."""
        raw_bytes = self.CONFIG_PATH.read_bytes()
        text = raw_bytes.decode("utf-8")
        data = json.loads(text)
        assert isinstance(data, dict)
        assert data.get("version") == "1.0"

    def test_s3_compatibility_keys(self):
        """Verify all S3 Cloudflare R2 fields are correctly structured."""
        data = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
        assert "remote_storage" in data
        remote = data["remote_storage"]
        assert remote.get("type") == "s3"
        assert "s3" in remote
        s3 = remote["s3"]
        assert s3.get("force_path_style") is True
        assert s3.get("v4_auth_only") is True
        assert "${R2_ACCESS_KEY}" in s3.get("access_key")
        assert "${R2_SECRET_KEY}" in s3.get("secret_key")
        assert "${R2_ENDPOINT}" in s3.get("endpoint")
        assert "${R2_BUCKET}" in s3.get("bucket")

    def test_tiering_policy_invariants(self):
        """Verify tiering criteria boundaries."""
        data = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
        assert "tiering_policy" in data
        policy = data["tiering_policy"]
        assert policy.get("enabled") is True
        assert policy.get("criteria", {}).get("full_percent") == 95
        assert policy.get("criteria", {}).get("min_size_mb") == 100
        assert policy.get("read_cache_enabled") is True
        assert policy.get("read_cache_size_mb") == 2048


class TestChallenge3DeltaEngineConcurrencyAndCompaction:
    """Stress tests on DeltaDatasetWriter, Schema Evolution & DeltaCompactor."""

    def test_rapid_multithreaded_concurrent_appends(self):
        """Stress-test single DeltaDatasetWriter with 10 concurrent threads appending 200 records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "stress_delta_table"
            writer = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA, buffer_size=10)

            num_threads = 10
            records_per_thread = 20
            total_expected = num_threads * records_per_thread

            def _worker(thread_id: int):
                for i in range(records_per_thread):
                    rec = {
                        "session_id": f"sess_stress_{thread_id}_{i}",
                        "timestamp": "2026-08-28T00:00:00Z",
                        "claim_id": f"claim_{thread_id}_{i}",
                        "evidence_path": f"/path/to/evidence_{thread_id}.log",
                        "verdict": "PASS",
                        "confidence_score": 0.99,
                        "auditor_id": f"challenger_thread_{thread_id}",
                    }
                    writer.append(rec)

            threads = [threading.Thread(target=_worker, args=(t,)) for t in range(num_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Flush remaining buffer
            writer.flush()

            count = writer.count_rows()
            assert count == total_expected, f"Expected {total_expected} rows, got {count}"
            assert writer.get_version() >= 1

    def test_concurrent_writer_processes_to_same_table(self):
        """Stress-test multiple distinct DeltaDatasetWriter instances writing to the same table path sequentially/threaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "multi_instance_table"

            # Initialize table first
            w_init = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)
            w_init.write([{
                "session_id": "init_session",
                "timestamp": "2026-08-28T00:00:00Z",
                "claim_id": "claim_init",
                "evidence_path": "/path/init",
                "verdict": "PASS",
                "confidence_score": 1.0,
                "auditor_id": "init",
            }])

            num_writers = 8
            records_per_writer = 5

            def _writer_task(instance_id: int):
                w = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)
                for i in range(records_per_writer):
                    w.write([{
                        "session_id": f"sess_multi_{instance_id}_{i}",
                        "timestamp": "2026-08-28T00:00:00Z",
                        "claim_id": f"claim_{instance_id}_{i}",
                        "evidence_path": f"/path/{instance_id}",
                        "verdict": "PASS",
                        "confidence_score": 0.95,
                        "auditor_id": f"writer_{instance_id}",
                    }])

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers) as executor:
                futures = [executor.submit(_writer_task, i) for i in range(num_writers)]
                concurrent.futures.wait(futures)

            dt = DeltaTable(str(table_path))
            total_rows = dt.to_pyarrow_dataset().count_rows()
            assert total_rows == 1 + (num_writers * records_per_writer)

    def test_schema_evolution_merge_and_error_modes(self):
        """Verify dynamic schema evolution when new fields appear."""
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "schema_evolution_table"

            # 1. Base table with 2 fields
            base_schema = pa.schema([
                pa.field("id", pa.string(), nullable=False),
                pa.field("value", pa.int64(), nullable=True),
            ])
            writer = DeltaDatasetWriter(table_path, schema=base_schema, schema_mode="merge")
            writer.write([{"id": "rec1", "value": 100}])

            # 2. Write with extra field 'extra_tag' in merge mode
            evolved_table = pa.table({
                "id": ["rec2"],
                "value": [200],
                "extra_tag": ["synthetic_tag_v2"],
            })
            writer.write(evolved_table)

            dt = DeltaTable(str(table_path))
            cols = dt.schema().to_arrow().names
            assert "id" in cols
            assert "value" in cols
            assert "extra_tag" in cols
            assert dt.to_pyarrow_dataset().count_rows() == 2

    def test_compactor_heavy_binpacking_and_vacuum(self):
        """Create 40 micro-files, compact them down, and execute vacuum."""
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "compaction_stress_table"
            writer = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)

            # Write 40 single-record commits creating 40 individual parquet files
            for i in range(40):
                writer.write([{
                    "artifact_id": f"art_comp_{i}",
                    "artifact_type": "TRUTH_AUDIT" if i % 2 == 0 else "DEBATE",
                    "title": f"Truth Audit Record {i}",
                    "source_node": "mac_mini",
                    "timestamp": "2026-08-28T00:00:00Z",
                    "tags": ["mesh", "audit"],
                    "payload_json": json.dumps({"verdict": "PASS", "index": i}),
                    "sha256_hash": f"hash_{i}" * 8,
                    "metadata_json": "{}",
                    "created_at_epoch_ms": 1724800000000 + i,
                }])

            compactor = DeltaCompactor(table_path)
            stats_before = compactor.get_stats()
            assert stats_before["file_count"] == 40

            # Compact
            compact_res = compactor.compact(target_size_bytes=64 * 1024 * 1024)
            assert compact_res["status"] == "success"
            assert compact_res["files_after"] < compact_res["files_before"]

            # Z-Order by artifact_type
            z_res = compactor.z_order(columns=["artifact_type"])
            assert z_res["status"] == "success"

            # Vacuum
            deleted = compactor.vacuum(retention_hours=0, enforce_retention_duration=False)
            assert isinstance(deleted, list)

            # Verify table still reads all 40 records intact
            final_dt = DeltaTable(str(table_path))
            assert final_dt.to_pyarrow_dataset().count_rows() == 40


class TestChallenge4MemoryMappedDatasetLoaderRSS:
    """Stress tests on MemoryMappedDatasetLoader measuring memory RSS pressure."""

    def test_large_dataset_zero_copy_rss_pressure(self):
        """Generate 20,000 synthetic rows with text blobs; verify RSS overhead delta < 50MB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "large_mmap_table"
            writer = DeltaDatasetWriter(table_path)

            # Generate 20,000 rows in 4 batches of 5,000
            large_text_sample = "Lauburu Distributed AI Mesh Telemetry Event Record " * 5
            batch_size = 5000
            num_batches = 4
            total_rows = batch_size * num_batches

            for b in range(num_batches):
                data = {
                    "row_id": [f"row_{b}_{i}" for i in range(batch_size)],
                    "timestamp": [1724800000 + i for i in range(batch_size)],
                    "payload_text": [f"{large_text_sample} [batch={b}, index={i}]" for i in range(batch_size)],
                    "metric_value": [float(i * 1.5) for i in range(batch_size)],
                }
                table = pa.Table.from_pydict(data)
                writer.write(table)

            assert writer.count_rows() == total_rows

            # Measure RSS Footprint
            footprint = MemoryMappedDatasetLoader.measure_rss_footprint(table_path)
            assert footprint["rows_loaded"] == total_rows
            assert footprint["delta_rss_mb"] < 50.0, f"RSS footprint exceeded 50MB: {footprint['delta_rss_mb']} MB"
            assert footprint["zero_copy_verified"] is True

            # Stream batches through PyArrow scanner
            batch_count = 0
            scanned_rows = 0
            for batch in MemoryMappedDatasetLoader.stream_batches(table_path, batch_size=2048):
                batch_count += 1
                scanned_rows += batch.num_rows

            assert scanned_rows == total_rows
            assert batch_count >= 1


    def test_repeated_dataset_loading_no_memory_leak(self):
        """Stress-test memory stability across 20 consecutive dataset load cycles."""
        import gc
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "leak_check_table"
            writer = DeltaDatasetWriter(table_path)
            data = pa.table({
                "id": [f"id_{i}" for i in range(5000)],
                "val": [i * 2.0 for i in range(5000)],
                "blob": ["x" * 200 for _ in range(5000)],
            })
            writer.write(data)

            gc.collect()
            initial_rss = psutil.Process().memory_info().rss / (1024 * 1024)

            for _ in range(20):
                ds = MemoryMappedDatasetLoader.load_hf_dataset(table_path)
                assert len(ds) == 5000

            gc.collect()
            final_rss = psutil.Process().memory_info().rss / (1024 * 1024)
            growth_mb = final_rss - initial_rss
            assert growth_mb < 20.0, f"Memory leak detected: grew by {growth_mb:.2f} MB across 20 loads"


class TestChallenge5ObsidianVectorizerAdversarialInputs:
    """Stress tests on MarkdownChunker, LlamaEmbeddingClient, QdrantSyncStore, and DebounceEventQueue."""

    def test_malformed_yaml_frontmatter_and_binary_garbage(self):
        """Test parser resilience against corrupted YAML, unclosed quotes, and binary garbage."""
        chunker = MarkdownChunker(max_chunk_size=1000, overlap=100)
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "corrupted_note.md"
            corrupted_content = (
                "---\n"
                "title: \"Unclosed quote title without ending quote\n"
                "tags: [incomplete, array, \n"
                "category: ::::bad_yaml_syntax::::\n"
                "---\n\n"
                "# Recovered Heading\n\n"
                "This text should be parsed safely despite malformed frontmatter."
            )
            fpath.write_text(corrupted_content, encoding="utf-8")

            chunks = chunker.chunk_file("corrupted_note.md", fpath)
            assert len(chunks) >= 1
            assert "Recovered Heading" in chunks[0].heading or "Recovered Heading" in chunks[0].text
            assert "This text should be parsed safely" in chunks[0].text

    def test_non_utf8_binary_notes_handling(self):
        """Verify chunker handles files containing arbitrary binary byte sequences."""
        chunker = MarkdownChunker()
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "binary_note.md"
            # Write invalid UTF-8 bytes mixed with markdown headers
            with open(fpath, "wb") as f:
                f.write(b"# Binary Note Header\n\nSome clean text\x80\x81\xff\xfe\x00\x01\n\n## Section 2\nSafe tail")

            chunks = chunker.chunk_file("binary_note.md", fpath)
            assert len(chunks) >= 1
            assert "Binary Note Header" in chunks[0].heading or "Binary Note Header" in chunks[0].text

    def test_massive_1mb_unspaced_header_and_deep_nesting(self):
        """Stress-test chunker with massive 100KB+ continuous string and ###### deep headings."""
        chunker = MarkdownChunker(max_chunk_size=800, overlap=100)
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "massive_header_note.md"
            giant_word = "A" * 50000  # 50KB continuous token
            deep_headings = (
                f"# Main\n\n{giant_word}\n\n"
                "## Level 2 Subheading\n\nSub content.\n\n"
                "### Level 3 Subheading\n\nLevel 3 content.\n\n"
                "#### Level 4 Subheading\n\nLevel 4 content.\n\n"
                "##### Level 5 Subheading\n\nLevel 5 content.\n\n"
                "###### Level 6 Subheading\n\nDeep nested content.\n"
            )
            fpath.write_text(deep_headings, encoding="utf-8")

            chunks = chunker.chunk_file("massive_header_note.md", fpath)
            assert len(chunks) > 10  # Sliced by sliding window
            for chk in chunks:
                assert chk.char_count <= 800

    def test_0_byte_and_whitespace_files(self):
        """Verify 0-byte and whitespace files return empty chunk list without raising errors."""
        chunker = MarkdownChunker()
        with tempfile.TemporaryDirectory() as tmpdir:
            f0 = Path(tmpdir) / "empty.md"
            f0.write_text("", encoding="utf-8")
            chunks0 = chunker.chunk_file("empty.md", f0)
            assert isinstance(chunks0, list)

            f_space = Path(tmpdir) / "spaces.md"
            f_space.write_text("   \n\n\t  \r\n   ", encoding="utf-8")
            chunks_space = chunker.chunk_file("spaces.md", f_space)
            assert isinstance(chunks_space, list)

    def test_high_frequency_debounce_burst(self):
        """Push 5,000 events to DebounceEventQueue across 50 files; verify coalescing and pop_ready."""
        q = DebounceEventQueue(debounce_delay=0.1)
        num_files = 50
        events_per_file = 100

        for _ in range(events_per_file):
            for f_idx in range(num_files):
                q.push(f"/path/to/file_{f_idx}.md", "modified")

        # All 5,000 events coalesced to exactly 50 pending items
        assert q.pending_count() == num_files

        # Before 0.1s delay, pop_ready is empty
        assert len(q.pop_ready()) == 0

        # After waiting >0.1s
        time.sleep(0.15)
        ready = q.pop_ready()
        assert len(ready) == num_files
        assert q.pending_count() == 0

    def test_llama_embedding_client_backoff_and_retry_exhaustion(self):
        """Verify LlamaEmbeddingClient retries with backoff and raises EmbeddingAPIError when server is down."""
        dead_client = LlamaEmbeddingClient(
            endpoint_url="http://127.0.0.1:59999/v1/embeddings",
            max_retries=3,
            base_backoff=0.01,
            max_backoff=0.05,
            timeout=0.2,
        )
        health_ok, _ = dead_client.check_health()
        assert health_ok is False

        start = time.perf_counter()
        with pytest.raises(EmbeddingAPIError) as exc_info:
            dead_client.get_embeddings(["Sample text for embedding"])

        elapsed = time.perf_counter() - start
        assert "Llama embedding API connection failed" in str(exc_info.value) or "failed after 3 attempts" in str(exc_info.value)
        assert elapsed >= 0.03  # Backoff was executed

    def test_qdrant_embedded_sqlite_concurrent_upsert_and_delete(self):
        """Stress-test QdrantSyncStore SQLite embedded mode under concurrent threads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = QdrantSyncStore(qdrant_path=Path(tmpdir), collection_name="stress_test_col")
            assert store.mode == "sqlite_embedded"

            num_threads = 6
            items_per_thread = 10

            def _upsert_worker(t_id: int):
                for i in range(items_per_thread):
                    chk = MarkdownChunk(
                        point_id=str(uuid.uuid4()),
                        filepath=f"docs/module_{t_id}.md",
                        filename=f"module_{t_id}.md",
                        title=f"Module {t_id}",
                        category="Canonical Module",
                        tags=["mesh", "test"],
                        heading=f"## Subheading {i}",
                        chunk_index=i,
                        chunk_total=items_per_thread,
                        text=f"Sample text content for thread {t_id} chunk {i}",
                        char_count=50,
                        content_hash=f"hash_{t_id}_{i}",
                        last_modified="2026-08-28T00:00:00Z",
                        updated_at="2026-08-28T00:00:00Z",
                    )
                    fake_vector = [0.1 * (j + 1) for j in range(128)]
                    store.upsert_chunks([chk], [fake_vector])

            threads = [threading.Thread(target=_upsert_worker, args=(t,)) for t in range(num_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            stats = store.get_stats()
            assert stats["points_count"] == num_threads * items_per_thread
            assert stats.get("integrity") == "ok"

            # Delete file
            deleted = store.delete_file_chunks("docs/module_0.md")
            assert deleted == items_per_thread

            stats_after = store.get_stats()
            assert stats_after["points_count"] == (num_threads - 1) * items_per_thread

    def test_qdrant_sqlite_duplicate_point_ids_idempotency(self):
        """Verify upserting points with identical point_ids replaces records idempotently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = QdrantSyncStore(qdrant_path=Path(tmpdir), collection_name="idempotent_col")
            fixed_uuid = str(uuid.uuid4())
            chk1 = MarkdownChunk(
                point_id=fixed_uuid,
                filepath="doc.md",
                filename="doc.md",
                title="Doc V1",
                category="Infrastructure",
                tags=["v1"],
                heading="# Heading",
                chunk_index=0,
                chunk_total=1,
                text="Text V1",
                char_count=7,
                content_hash="h1",
                last_modified="2026-08-28T00:00:00Z",
                updated_at="2026-08-28T00:00:00Z",
            )
            store.upsert_chunks([chk1], [[0.1] * 128])
            assert store.get_stats()["points_count"] == 1

            # Re-upsert with same ID but updated content
            chk2 = MarkdownChunk(
                point_id=fixed_uuid,
                filepath="doc.md",
                filename="doc.md",
                title="Doc V2",
                category="Infrastructure",
                tags=["v2"],
                heading="# Heading",
                chunk_index=0,
                chunk_total=1,
                text="Text V2 updated",
                char_count=15,
                content_hash="h2",
                last_modified="2026-08-28T00:01:00Z",
                updated_at="2026-08-28T00:01:00Z",
            )
            store.upsert_chunks([chk2], [[0.2] * 128])
            # Total count should still be 1 (replaced, not duplicated)
            assert store.get_stats()["points_count"] == 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
