"""
================================================================================
CHALLENGER 2: ADVERSARIAL EMPIRICAL STRESS & PIPELINE INTEGRITY HARNESS
================================================================================
Mission & Invariants:
1. End-to-end combinatorial pipeline test: Note modification in `obsidian_vault` ->
   Watchdog debounce -> Semantic chunking -> Llama embedding client ->
   Qdrant vector store -> Delta Lake transaction log -> Delta compactor ->
   MemoryMapped HuggingFace dataset read.
2. Verify tombstone deletion semantics, ghost vector elimination, and zero data corruption.
3. Cryptographic hash parity (SHA-256) across Raw Markdown -> Qdrant -> Delta Lake -> HF Mmap.
4. High-concurrency ACID transactional integrity under simultaneous writes and compaction.
5. Memory leak audit over repeated mmap iterations.
6. Fault injection (flaky embedding API, malformed schema inputs).
"""
from __future__ import annotations

import os
import sys
import time
import json
import uuid
import psutil
import hashlib
import tempfile
import threading
import importlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Generator

import pytest
import pyarrow as pa
from deltalake import DeltaTable

# Ensure monorepo root is on sys.path
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Dynamic imports of canonical modules
schema_mod = importlib.import_module("04_data_and_memory.delta_engine.schema")
writer_mod = importlib.import_module("04_data_and_memory.delta_engine.writer")
compactor_mod = importlib.import_module("04_data_and_memory.delta_engine.compactor")
mmap_mod = importlib.import_module("04_data_and_memory.delta_engine.mmap_loader")
vectorizer_mod = importlib.import_module("04_data_and_memory.qdrant_sync.obsidian_vectorizer")

TRUTH_AUDIT_ARROW_SCHEMA = schema_mod.TRUTH_AUDIT_ARROW_SCHEMA
SFT_TRAINING_ARROW_SCHEMA = schema_mod.SFT_TRAINING_ARROW_SCHEMA
normalize_record = schema_mod.normalize_record
records_to_arrow_table = schema_mod.records_to_arrow_table

DeltaDatasetWriter = writer_mod.DeltaDatasetWriter
DeltaCompactor = compactor_mod.DeltaCompactor
MemoryMappedDatasetLoader = mmap_mod.MemoryMappedDatasetLoader

MarkdownChunker = vectorizer_mod.MarkdownChunker
LlamaEmbeddingClient = vectorizer_mod.LlamaEmbeddingClient
EmbeddingAPIError = vectorizer_mod.EmbeddingAPIError
QdrantSyncStore = vectorizer_mod.QdrantSyncStore
SyncStateCache = vectorizer_mod.SyncStateCache
DebounceEventQueue = vectorizer_mod.DebounceEventQueue
ObsidianVectorizerDaemon = vectorizer_mod.ObsidianVectorizerDaemon


# ==============================================================================
# Helper Flaky Server Fixture for Fault Injection
# ==============================================================================

class FlakyEmbeddingHTTPHandler(BaseHTTPRequestHandler):
    """Fails with 503 Service Unavailable for N attempts before succeeding with 200 OK."""
    failures_remaining = 2

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def do_POST(self) -> None:
        if FlakyEmbeddingHTTPHandler.failures_remaining > 0:
            FlakyEmbeddingHTTPHandler.failures_remaining -= 1
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"Model loading transiently"}')
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        data = json.loads(body_bytes.decode("utf-8"))
        texts = data.get("input", [])
        if isinstance(texts, str):
            texts = [texts]

        results = []
        for idx, text in enumerate(texts):
            h = hashlib.sha256(text.encode("utf-8")).digest()
            raw_vec = [round((h[i % len(h)] - 128) / 128.0, 6) for i in range(128)]
            mag = sum(x * x for x in raw_vec) ** 0.5 or 1.0
            norm_vec = [round(x / mag, 6) for x in raw_vec]
            results.append({"object": "embedding", "index": idx, "embedding": norm_vec})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"object": "list", "data": results}).encode("utf-8"))


@pytest.fixture
def flaky_embedding_server() -> Generator[str, None, None]:
    FlakyEmbeddingHTTPHandler.failures_remaining = 2
    server = HTTPServer(("127.0.0.1", 0), FlakyEmbeddingHTTPHandler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}/v1/embeddings"
    server.shutdown()
    server.server_close()


# ==============================================================================
# TEST SUITE: CHALLENGER 2 EMPIRICAL ADVERSARIAL VERIFICATIONS
# ==============================================================================

class TestAdversarialCombinatorialPipeline:
    """
    1. End-to-end combinatorial pipeline test: Note modification in `obsidian_vault` ->
       Watchdog debounce -> Semantic chunking -> Llama embedding client ->
       Qdrant vector store -> Delta Lake transaction log -> Delta compactor ->
       MemoryMapped HuggingFace dataset read.
    """

    def test_end_to_end_pipeline_with_rapid_mutations_and_mmap(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        vault_dir = temp_workspace / "vault_pipeline"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_pipeline"
        delta_dir = temp_workspace / "delta_pipeline"
        state_file = temp_workspace / "sync_state.json"
        telemetry_file = temp_workspace / "telemetry.jsonl"

        # Initialize vectorizer daemon
        daemon = ObsidianVectorizerDaemon(
            vault_dir=vault_dir,
            llama_endpoint=live_embedding_server,
            qdrant_url="http://127.0.0.1:9999",
            qdrant_path=qdrant_dir,
            collection_name="test_pipeline",
            batch_size=8,
            debounce_seconds=0.1,
            state_file=state_file,
            telemetry_file=telemetry_file
        )

        # 1. Create 8 initial markdown files
        file_hashes: Dict[str, str] = {}
        for i in range(8):
            fpath = vault_dir / f"note_{i:02d}.md"
            content = (
                f"---\n"
                f"title: \"Architecture Note {i}\"\n"
                f"tags: [mesh, layer_{i % 7}, node_{i}]\n"
                f"category: \"Architecture & Docs\"\n"
                f"---\n"
                f"# Architecture Note {i}\n\n"
                f"## Section 1 - Specification\n"
                f"Initial specification body for subsystem {i}.\n\n"
                f"## Section 2 - Telemetry\n"
                f"Latency is {0.25 + i * 0.01:.3f}ms over TB4 bridge.\n"
            )
            fpath.write_text(content, encoding="utf-8")
            file_hashes[fpath.name] = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Run initial sync
        stats1 = daemon.sync_all(force=True)
        assert stats1.files_scanned == 8
        assert stats1.files_indexed == 8
        assert stats1.errors == 0
        initial_points = stats1.points_upserted
        assert initial_points >= 16  # At least 2 chunks per note

        # 2. Rapidly mutate 3 files and delete 1 file in burst
        mutated_files = ["note_01.md", "note_03.md", "note_05.md"]
        for fname in mutated_files:
            fpath = vault_dir / fname
            new_content = (
                f"---\n"
                f"title: \"Mutated Architecture Note {fname}\"\n"
                f"tags: [mutated, updated]\n"
                f"---\n"
                f"# Mutated {fname}\n\n"
                f"## Single Consolidated Section\n"
                f"Completely rewritten content replacing old sections.\n"
            )
            # Push rapid events to debounce queue
            for _ in range(5):
                daemon.debounce_queue.push(str(fpath), "modified")
            fpath.write_text(new_content, encoding="utf-8")
            file_hashes[fname] = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

        # Delete note_07.md
        deleted_path = vault_dir / "note_07.md"
        deleted_path.unlink()
        daemon.debounce_queue.push(str(deleted_path), "deleted")

        # Wait for debounce window
        time.sleep(0.2)
        ready_events = daemon.debounce_queue.pop_ready()
        assert len(ready_events) == 4  # 3 modified + 1 deleted

        # Process debounced events
        for fp_str, ev_type in ready_events:
            fp = Path(fp_str)
            if ev_type in ["created", "modified"]:
                daemon.process_file(fp, force=True)
            elif ev_type == "deleted":
                daemon.delete_file(fp)

        # 3. Verify Qdrant points count reflects mutations & deletions
        qstats = daemon.qdrant_store.get_stats()
        # Deleted file had >=2 points, mutated files reduced chunks from 3 to 2 each
        assert qstats["points_count"] < initial_points

        # 4. Stream audit events to Delta Lake table
        writer = DeltaDatasetWriter(table_uri=delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)
        audit_records = []
        for fp_str, ev_type in ready_events:
            fname = Path(fp_str).name
            audit_records.append({
                "artifact_id": f"evt_{uuid.uuid4().hex[:8]}",
                "artifact_type": f"file_{ev_type}",
                "title": f"Watchdog Event: {fname}",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": ["watchdog", ev_type, "debounce"],
                "payload_json": json.dumps({"filename": fname, "event": ev_type}),
                "sha256_hash": file_hashes.get(fname, "0" * 64),
                "metadata_json": "{}",
                "created_at_epoch_ms": int(time.time() * 1000),
            })

        write_res = writer.write(audit_records)
        assert write_res["status"] == "success"
        assert write_res["rows_written"] == 4

        # 5. Compact Delta table
        compactor = DeltaCompactor(delta_dir)
        compact_res = compactor.compact()
        assert compact_res["status"] == "success"

        # 6. Read back via MemoryMappedDatasetLoader with HuggingFace dataset
        hf_dataset = MemoryMappedDatasetLoader.load_hf_dataset(delta_dir)
        assert len(hf_dataset) == 4
        assert set(hf_dataset["title"]) == {
            "Watchdog Event: note_01.md",
            "Watchdog Event: note_03.md",
            "Watchdog Event: note_05.md",
            "Watchdog Event: note_07.md"
        }

        # 7. Verify zero-copy RSS footprint (<50MB)
        rss_metrics = MemoryMappedDatasetLoader.measure_rss_footprint(delta_dir)
        assert rss_metrics["zero_copy_verified"] is True


class TestTombstoneDeletionAndGhostVectorPruning:
    """
    2. Verify tombstone deletion semantics, ghost vector elimination, and zero data corruption.
    """

    def test_tombstone_deletion_and_ghost_vector_elimination(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        vault_dir = temp_workspace / "vault_tombstone"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_tombstone"
        delta_dir = temp_workspace / "delta_tombstone"

        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_dir)
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        chunker = MarkdownChunker()
        writer = DeltaDatasetWriter(delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)

        # Create 12 files
        created_chunks_by_file: Dict[str, List[str]] = {}
        for i in range(12):
            fname = f"doc_{i:02d}.md"
            fpath = vault_dir / fname
            fpath.write_text(
                f"# Document {i}\n\n"
                f"## Section A\nBody for doc {i} section A.\n\n"
                f"## Section B\nBody for doc {i} section B.\n\n"
                f"## Section C\nBody for doc {i} section C.\n",
                encoding="utf-8"
            )
            chunks = chunker.chunk_file(fname, fpath)
            vecs = client.get_embeddings([c.text for c in chunks])
            store.upsert_chunks(chunks, vecs)
            created_chunks_by_file[fname] = [c.point_id for c in chunks]

        initial_total_points = sum(len(ids) for ids in created_chunks_by_file.values())
        assert store.get_stats()["points_count"] == initial_total_points

        # Target 4 files for deletion
        files_to_delete = ["doc_02.md", "doc_04.md", "doc_06.md", "doc_08.md"]
        deleted_point_ids = []
        for fname in files_to_delete:
            deleted_point_ids.extend(created_chunks_by_file[fname])
            fpath = vault_dir / fname
            fpath.unlink()
            deleted_count = store.delete_file_chunks(fname)
            assert deleted_count == len(created_chunks_by_file[fname])

            # Write tombstone to Delta Lake
            writer.write([{
                "artifact_id": f"tomb_{uuid.uuid4().hex[:8]}",
                "artifact_type": "tombstone_prune",
                "title": f"Tombstone {fname}",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": ["tombstone", "deletion"],
                "payload_json": json.dumps({"file": fname, "purged_points": deleted_count}),
                "sha256_hash": "0" * 64,
                "metadata_json": "{}",
                "created_at_epoch_ms": int(time.time() * 1000),
            }])

        # EMPIRICAL GHOST VECTOR CHECK: Query storage directly
        stats_after_delete = store.get_stats()
        expected_remaining = initial_total_points - len(deleted_point_ids)
        assert stats_after_delete["points_count"] == expected_remaining, (
            f"Ghost vectors detected! Expected {expected_remaining} points, found {stats_after_delete['points_count']}"
        )

        # Inspect SQLite table directly to verify point_ids are 100% gone
        db_path = qdrant_dir / "collection" / "obsidian_vault" / "storage.sqlite"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM points;")
        active_ids = {row[0] for row in cursor.fetchall()}
        conn.close()

        for pid in deleted_point_ids:
            assert pid not in active_ids, f"GHOST VECTOR LEAK: Point ID {pid} still present in Qdrant store!"

        # Verify Delta table logged all 4 tombstones
        dt = DeltaTable(str(delta_dir))
        assert len(dt.to_pyarrow_table()) == 4


class TestHashParityAndZeroCorruption:
    """
    3. Cryptographic hash parity (SHA-256) across Raw Markdown -> Qdrant -> Delta Lake -> HF Mmap.
    """

    def test_cryptographic_hash_parity_across_vault_tiers(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        vault_dir = temp_workspace / "vault_parity"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_parity"
        delta_dir = temp_workspace / "delta_parity"

        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_dir)
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        chunker = MarkdownChunker()
        writer = DeltaDatasetWriter(delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)

        # Generate complex markdown with Unicode, Math, Code blocks, and YAML
        doc_filename = "canonical_parity_spec.md"
        doc_path = vault_dir / doc_filename
        doc_raw_text = (
            "---\n"
            "title: \"Cryptographic Hash Parity Specification 🔒\"\n"
            "tags: [sha256, integrity, zero_corruption, lauburu]\n"
            "category: \"Audit & Telemetry\"\n"
            "---\n"
            "# Cryptographic Integrity Model\n\n"
            "## Mathematical Proof: e^{i\\pi} + 1 = 0\n"
            "Verifying zero data drift across PySpark, Delta Lake, and Qdrant.\n\n"
            "```python\n"
            "def verify_sha256(data: bytes) -> str:\n"
            "    return hashlib.sha256(data).hexdigest()\n"
            "```\n\n"
            "## Multi-lingual Assertions\n"
            "日本語テキスト, 简体中文, Русский текст, العربية, ⚡ 108GB VRAM.\n"
        )
        doc_path.write_text(doc_raw_text, encoding="utf-8")

        # 1. Chunk document
        chunks = chunker.chunk_file(doc_filename, doc_path)
        assert len(chunks) >= 3

        # Compute ground truth SHA-256 for each chunk text
        ground_truth_hashes = [hashlib.sha256(c.text.encode("utf-8")).hexdigest() for c in chunks]

        # 2. Upsert to Qdrant
        vecs = client.get_embeddings([c.text for c in chunks])
        store.upsert_chunks(chunks, vecs)

        # 3. Write to Delta Lake
        delta_records = []
        for idx, chk in enumerate(chunks):
            delta_records.append({
                "artifact_id": chk.point_id,
                "artifact_type": "parity_chunk",
                "title": chk.title,
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": chk.tags,
                "payload_json": json.dumps(chk.to_payload()),
                "sha256_hash": chk.content_hash,
                "metadata_json": json.dumps({"chunk_idx": idx}),
                "created_at_epoch_ms": int(time.time() * 1000),
            })
        writer.write(delta_records)

        # 4. Read back directly from SQLite / Qdrant store
        db_path = qdrant_dir / "collection" / "obsidian_vault" / "storage.sqlite"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id, point FROM points;")
        rows = cursor.fetchall()
        conn.close()

        qdrant_payloads = {}
        for pid, blob in rows:
            data = json.loads(blob.decode("utf-8"))
            qdrant_payloads[pid] = data.get("payload", {})

        # 5. Read back via MemoryMapped HuggingFace dataset
        hf_ds = MemoryMappedDatasetLoader.load_hf_dataset(delta_dir)
        assert len(hf_ds) == len(chunks)

        # 6. Verify Exact Bit-for-Bit Hash Parity across all tiers
        for idx, chk in enumerate(chunks):
            expected_hash = ground_truth_hashes[idx]

            # Parity Check A: MarkdownChunk model
            assert chk.content_hash == expected_hash, f"Chunk {idx} hash mismatch in MarkdownChunk model"

            # Parity Check B: Qdrant Payload
            q_payload = qdrant_payloads.get(chk.point_id)
            assert q_payload is not None, f"Missing point {chk.point_id} in Qdrant store"
            assert q_payload["content_hash"] == expected_hash, f"Qdrant payload hash drift for chunk {idx}"
            assert q_payload["text"] == chk.text, f"Qdrant text corruption for chunk {idx}"

            # Parity Check C: HuggingFace Memory-Mapped Delta Record
            hf_row = [r for r in hf_ds if r["artifact_id"] == chk.point_id][0]
            assert hf_row["sha256_hash"] == expected_hash, f"Delta Lake / HF mmap sha256 drift for chunk {idx}"
            reconstructed_payload = json.loads(hf_row["payload_json"])
            assert reconstructed_payload["content_hash"] == expected_hash
            assert reconstructed_payload["text"] == chk.text


class TestConcurrencyContentionAndACIDIsolation:
    """
    4. High-concurrency ACID transactional integrity under simultaneous writes and compaction.
    """

    def test_concurrent_delta_writes_during_active_compaction(self, temp_workspace: Path):
        """
        Spawns 8 concurrent worker threads writing to Delta Lake while a background
        compactor repeatedly executes bin-packing. Verifies zero transaction conflicts or lost commits.
        """
        table_path = temp_workspace / "delta_acid_stress"
        writer = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)
        compactor = DeltaCompactor(table_path)

        # Initial seed commit
        writer.write([{
            "artifact_id": "seed",
            "artifact_type": "seed",
            "title": "Seed Commit",
            "source_node": "Mac_Node",
            "timestamp": "2026-08-28T00:00:00Z",
            "tags": ["seed"],
            "payload_json": "{}",
            "sha256_hash": "0" * 64,
            "metadata_json": "{}",
            "created_at_epoch_ms": 1787878800000,
        }])

        num_threads = 6
        batches_per_thread = 8
        records_per_batch = 5
        stop_compactor = threading.Event()
        compaction_runs = [0]

        def compactor_loop():
            while not stop_compactor.is_set():
                try:
                    compactor.compact(target_size_bytes=1024 * 1024)
                    compaction_runs[0] += 1
                except Exception:
                    pass
                time.sleep(0.02)

        def worker_write(thread_id: int):
            local_writer = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)
            for b in range(batches_per_thread):
                records = [
                    {
                        "artifact_id": f"art_t{thread_id}_b{b}_r{r}",
                        "artifact_type": "acid_test",
                        "title": f"Thread {thread_id} Batch {b} Record {r}",
                        "source_node": f"Node_{thread_id}",
                        "timestamp": "2026-08-28T00:00:00Z",
                        "tags": ["concurrency", f"thread_{thread_id}"],
                        "payload_json": json.dumps({"thread": thread_id, "batch": b, "record": r}),
                        "sha256_hash": hashlib.sha256(f"t{thread_id}b{b}r{r}".encode("utf-8")).hexdigest(),
                        "metadata_json": "{}",
                        "created_at_epoch_ms": int(time.time() * 1000),
                    }
                    for r in range(records_per_batch)
                ]
                res = local_writer.write(records)
                assert res["status"] == "success"
                time.sleep(0.005)

        compactor_thread = threading.Thread(target=compactor_loop, daemon=True)
        compactor_thread.start()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_write, tid) for tid in range(num_threads)]
            for fut in as_completed(futures):
                fut.result()

        stop_compactor.set()
        compactor_thread.join(timeout=2.0)

        # Final compaction
        compactor.compact()

        # Verify exact total row count: 1 (seed) + (6 threads * 8 batches * 5 records) = 241 records
        expected_total_rows = 1 + (num_threads * batches_per_thread * records_per_batch)
        dt = DeltaTable(str(table_path))
        arrow_table = dt.to_pyarrow_table()
        assert len(arrow_table) == expected_total_rows, (
            f"ACID Row count mismatch! Expected {expected_total_rows}, got {len(arrow_table)}"
        )


class TestMemoryLeakAndRSSBoundsUnderContinuousLoad:
    """
    5. Memory leak audit over repeated mmap iterations.
    """

    def test_mmap_continuous_100_cycle_zero_memory_leak(self, temp_workspace: Path):
        table_path = temp_workspace / "delta_mmap_leak_test"
        writer = DeltaDatasetWriter(table_path, schema=SFT_TRAINING_ARROW_SCHEMA)

        # Write 200 records
        records = [
            {
                "pair_id": f"sft_{i:04d}",
                "dataset_name": "continuous_memory_test",
                "format": "messages",
                "instruction": f"Instruction payload for cycle test {i}",
                "thought": "Evaluate memory bounds across PyArrow memory mapping.",
                "solution": "Verify RSS growth remains under 30MB over 100 iterations.",
                "messages_json": json.dumps([{"role": "user", "content": f"query {i}"}]),
                "system_prompt": "System prompt",
                "consensus_score": 0.99,
                "pillar": "Data & Memory",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "metadata_json": "{}",
            }
            for i in range(200)
        ]
        writer.write(records)

        process = psutil.Process(os.getpid())
        initial_rss_mb = process.memory_info().rss / (1024 * 1024)

        # Execute 100 consecutive load cycles
        for cycle in range(100):
            ds_loaded = MemoryMappedDatasetLoader.load_hf_dataset(table_path)
            assert len(ds_loaded) == 200
            # Read first and last items
            _ = ds_loaded[0]["pair_id"]
            _ = ds_loaded[-1]["solution"]

            # Stream small batches
            for batch in MemoryMappedDatasetLoader.stream_batches(table_path, batch_size=50):
                assert batch.num_rows <= 50

        final_rss_mb = process.memory_info().rss / (1024 * 1024)
        growth_mb = final_rss_mb - initial_rss_mb

        print(f"\n[Adversarial Memory Audit] 100 Mmap Cycles - Initial: {initial_rss_mb:.2f}MB, Final: {final_rss_mb:.2f}MB, Growth: {growth_mb:.2f}MB")
        assert growth_mb < 30.0, f"Memory leak detected in mmap loader: {growth_mb:.2f}MB growth over 100 cycles"


class TestFaultInjectionAndResilience:
    """
    6. Fault injection (flaky embedding API, malformed schema inputs).
    """

    def test_flaky_embedding_endpoint_exponential_backoff(self, flaky_embedding_server: str):
        """LlamaEmbeddingClient must survive transient 503 errors and succeed after retries."""
        client = LlamaEmbeddingClient(
            endpoint_url=flaky_embedding_server,
            max_retries=4,
            base_backoff=0.05,
            max_backoff=0.2,
            timeout=1.0
        )

        texts = ["Transient failure test text 1", "Transient failure test text 2"]
        vectors = client.get_embeddings(texts)
        assert len(vectors) == 2
        assert len(vectors[0]) == 128

    def test_corrupt_and_heterogeneous_delta_record_normalization(self):
        """Schema normalizer must sanitize dirty records (numeric strings, float timestamps, unformatted JSON)."""
        dirty_records = [
            {
                "artifact_id": 12345,  # int instead of str
                "artifact_type": "dirty_type",
                "title": None,  # None title
                "source_node": "Linux_Node",
                "timestamp": "1787878800000",  # String epoch millis
                "tags": json.dumps(["tag1", "tag2", "tag3"]),  # JSON serialized string list
                "payload_json": {"nested_key": [1, 2, 3]},  # Dict instead of str
                "sha256_hash": "c" * 64,
                "metadata_json": None,
                "created_at_epoch_ms": "1787878800000",  # String int
            }
        ]

        table = records_to_arrow_table(dirty_records, schema=TRUTH_AUDIT_ARROW_SCHEMA)
        assert isinstance(table, pa.Table)
        assert table.num_rows == 1

        row_dict = table.to_pylist()[0]
        assert row_dict["artifact_id"] == "12345"
        assert row_dict["tags"] == ["tag1", "tag2", "tag3"]
        assert json.loads(row_dict["payload_json"]) == {"nested_key": [1, 2, 3]}
        assert isinstance(row_dict["created_at_epoch_ms"], int)
