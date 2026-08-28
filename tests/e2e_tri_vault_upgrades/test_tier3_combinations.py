"""
================================================================================
TIER 3: CROSS-FEATURE & CROSS-VAULT COMBINATIONS E2E TEST SUITE
================================================================================
Verifies holistic workflows crossing Obsidian Vault, Llama Embedding API,
Qdrant Vector DB, Delta Lake ACID Data Lake, and SeaweedFS metadata tiers.

Workflows Tested:
1. End-to-end Pipeline: Note Creation -> Vectorize -> Embed -> Qdrant -> Delta Audit Log -> Mmap.
2. Note Modification & Chunk Invalidation Lifecycle (Delete old chunks, upsert new ones).
3. Note Deletion & Tombstone Audit Tracking.
4. High-Concurrency Multi-Threaded Sync & Atomic Delta Lake Commits.
"""
from __future__ import annotations

import os
import time
import json
import uuid
import hashlib
import threading
import importlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

import pytest
import pyarrow as pa
from deltalake import DeltaTable

# Dynamic imports
schema_mod = importlib.import_module("04_data_and_memory.delta_engine.schema")
writer_mod = importlib.import_module("04_data_and_memory.delta_engine.writer")
compactor_mod = importlib.import_module("04_data_and_memory.delta_engine.compactor")
mmap_mod = importlib.import_module("04_data_and_memory.delta_engine.mmap_loader")
vectorizer_mod = importlib.import_module("04_data_and_memory.qdrant_sync.obsidian_vectorizer")

TRUTH_AUDIT_ARROW_SCHEMA = schema_mod.TRUTH_AUDIT_ARROW_SCHEMA
DeltaDatasetWriter = writer_mod.DeltaDatasetWriter
DeltaCompactor = compactor_mod.DeltaCompactor
MemoryMappedDatasetLoader = mmap_mod.MemoryMappedDatasetLoader

MarkdownChunker = vectorizer_mod.MarkdownChunker
LlamaEmbeddingClient = vectorizer_mod.LlamaEmbeddingClient
QdrantSyncStore = vectorizer_mod.QdrantSyncStore
SyncStateCache = vectorizer_mod.SyncStateCache


class TestCrossVaultLifecyclePipeline:
    """Full end-to-end integration workflows crossing all three vaults."""

    def test_full_tri_vault_pipeline_flow(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        """
        Executes complete flow:
        1. Create note in Obsidian Vault.
        2. Chunk with MarkdownChunker.
        3. Embed via Live Embedding HTTP Server.
        4. Store in Qdrant Vector Store.
        5. Log audit record to Delta Lake table.
        6. Compact Delta table and load via MemoryMappedDatasetLoader.
        """
        vault_dir = temp_workspace / "obsidian_vault"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_data"
        delta_table_dir = temp_workspace / "delta_lake_audit"

        # Step 1: Create Note in Obsidian Vault
        note_filename = "07_docs_and_architecture.md"
        note_path = vault_dir / note_filename
        note_content = (
            "---\n"
            "title: \"Tri-Vault Unified Architecture Specification\"\n"
            "tags: [architecture, tri_vault, mesh, obsidian, delta]\n"
            "category: \"Architecture & Docs\"\n"
            "---\n"
            "# Tri-Vault Unified Architecture\n\n"
            "## Storage Tier Overview\n"
            "The monorepo coordinates human knowledge in Obsidian, big data in Delta Lake, and code on GitHub.\n\n"
            "## SeaweedFS Volume Cluster\n"
            "SeaweedFS orchestrates distributed volumes on Layer 6 Pixel 10 Pro XL and Mac Mini M4 Pro.\n"
        )
        note_path.write_text(note_content, encoding="utf-8")

        # Step 2: Chunk with MarkdownChunker
        chunker = MarkdownChunker(max_chunk_size=500, overlap=50)
        chunks = chunker.chunk_file(note_filename, note_path)
        assert len(chunks) >= 2

        # Step 3: Embed via LlamaEmbeddingClient
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        texts_to_embed = [c.text for c in chunks]
        vectors = client.get_embeddings(texts_to_embed)
        assert len(vectors) == len(chunks)
        assert len(vectors[0]) == 128

        # Step 4: Upsert to Qdrant Sync Store
        qdrant_store = QdrantSyncStore(
            qdrant_url="http://127.0.0.1:9999",
            qdrant_path=qdrant_dir,
            collection_name="obsidian_vault"
        )
        upserted_count = qdrant_store.upsert_chunks(chunks, vectors)
        assert upserted_count == len(chunks)

        qdrant_stats = qdrant_store.get_stats()
        assert qdrant_stats["points_count"] == len(chunks)

        # Step 5: Log audit record to Delta Lake Table
        audit_writer = DeltaDatasetWriter(
            table_uri=delta_table_dir,
            schema=TRUTH_AUDIT_ARROW_SCHEMA,
            mode="append"
        )
        audit_record = {
            "artifact_id": f"sync_{uuid.uuid4().hex[:12]}",
            "artifact_type": "obsidian_qdrant_sync",
            "title": "Tri-Vault Unified Architecture Synchronization",
            "source_node": "Mac_Node",
            "timestamp": "2026-08-28T00:00:00Z",
            "tags": ["obsidian", "qdrant", "delta", "seaweedfs"],
            "payload_json": json.dumps({
                "note_file": note_filename,
                "chunks_upserted": len(chunks),
                "qdrant_points": upserted_count,
                "seaweedfs_target": "100.73.38.87:8080/seaweedfs",
                "r2_tiering_status": "synced"
            }),
            "sha256_hash": hashlib.sha256(note_content.encode("utf-8")).hexdigest(),
            "metadata_json": json.dumps({"engine": "delta-rs", "version": "1.0.0"}),
            "created_at_epoch_ms": int(time.time() * 1000),
        }
        res = audit_writer.write([audit_record])
        assert res["status"] == "success"
        assert res["rows_written"] == 1

        # Step 6: Compact and Memory-Map Delta Lake Table
        compactor = DeltaCompactor(delta_table_dir)
        compactor.compact()

        hf_dataset = MemoryMappedDatasetLoader.load_hf_dataset(delta_table_dir)
        assert len(hf_dataset) == 1
        assert hf_dataset[0]["title"] == "Tri-Vault Unified Architecture Synchronization"
        assert "obsidian_qdrant_sync" in hf_dataset[0]["artifact_type"]

    def test_note_edit_and_stale_chunk_invalidation(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        """When an Obsidian note is edited, old chunks in Qdrant must be pruned and replaced."""
        vault_dir = temp_workspace / "obsidian_vault"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_invalidation"
        state_file = temp_workspace / "sync_state.json"

        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_dir)
        cache = SyncStateCache(state_file=state_file)
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        chunker = MarkdownChunker()

        note_rel = "dynamic_doc.md"
        note_file = vault_dir / note_rel

        # V1: 3 sections
        v1_text = (
            "# Dynamic Document\n\n"
            "## Section 1\nContent 1\n\n"
            "## Section 2\nContent 2\n\n"
            "## Section 3\nContent 3\n"
        )
        note_file.write_text(v1_text, encoding="utf-8")

        chunks_v1 = chunker.chunk_file(note_rel, note_file)
        assert len(chunks_v1) == 4  # Title + 3 sections
        vecs_v1 = client.get_embeddings([c.text for c in chunks_v1])
        store.upsert_chunks(chunks_v1, vecs_v1)
        cache.record_indexed(note_rel, note_file, len(chunks_v1))

        assert store.get_stats()["points_count"] == 4

        # V2: Edit note to only have 1 section
        time.sleep(0.01)
        v2_text = (
            "# Dynamic Document\n\n"
            "## Consolidated Section\nAll previous contents consolidated into single section.\n"
        )
        note_file.write_text(v2_text, encoding="utf-8")
        assert cache.is_file_changed(note_rel, note_file) is True

        # Invalidate old chunks and upsert new
        store.delete_file_chunks(note_rel)
        chunks_v2 = chunker.chunk_file(note_rel, note_file)
        assert len(chunks_v2) == 2  # Title + 1 section
        vecs_v2 = client.get_embeddings([c.text for c in chunks_v2])
        store.upsert_chunks(chunks_v2, vecs_v2)
        cache.record_indexed(note_rel, note_file, len(chunks_v2))

        # Final Qdrant point count must be exactly 2 (no orphaned chunks)
        stats_v2 = store.get_stats()
        assert stats_v2["points_count"] == 2

    def test_note_deletion_and_delta_tombstone(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        """Deleting an Obsidian note purges Qdrant vectors and logs a tombstone event to Delta Lake."""
        vault_dir = temp_workspace / "obsidian_vault"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_deletion"
        delta_dir = temp_workspace / "delta_tombstones"

        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_dir)
        writer = DeltaDatasetWriter(delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        chunker = MarkdownChunker()

        note_rel = "obsolete_feature.md"
        note_file = vault_dir / note_rel
        note_file.write_text("# Obsolete Feature\nThis feature will be deleted.", encoding="utf-8")

        chunks = chunker.chunk_file(note_rel, note_file)
        vecs = client.get_embeddings([c.text for c in chunks])
        store.upsert_chunks(chunks, vecs)
        assert store.get_stats()["points_count"] == len(chunks)

        # Now delete file
        note_file.unlink()
        deleted_points = store.delete_file_chunks(note_rel)
        assert deleted_points == len(chunks)
        assert store.get_stats()["points_count"] == 0

        # Record tombstone in Delta Lake
        tombstone_record = {
            "artifact_id": f"del_{uuid.uuid4().hex[:8]}",
            "artifact_type": "tombstone",
            "title": f"Deleted {note_rel}",
            "source_node": "Mac_Node",
            "timestamp": "2026-08-28T00:00:00Z",
            "tags": ["deletion", "tombstone"],
            "payload_json": json.dumps({"deleted_file": note_rel, "points_purged": deleted_points}),
            "sha256_hash": "0" * 64,
            "metadata_json": "{}",
            "created_at_epoch_ms": int(time.time() * 1000),
        }
        res = writer.write([tombstone_record])
        assert res["status"] == "success"

        # Verify Delta table has 1 record
        dt = DeltaTable(str(delta_dir))
        assert len(dt.to_pyarrow_table()) == 1

    def test_concurrent_multi_file_sync(
        self,
        temp_workspace: Path,
        live_embedding_server: str
    ):
        """Simultaneous concurrent sync across multiple threads must be thread-safe and lossless."""
        vault_dir = temp_workspace / "obsidian_vault"
        vault_dir.mkdir(parents=True, exist_ok=True)
        qdrant_dir = temp_workspace / "qdrant_concurrent"
        delta_dir = temp_workspace / "delta_concurrent"

        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_dir)
        writer = DeltaDatasetWriter(delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        chunker = MarkdownChunker()

        def worker_task(worker_id: int):
            rel_name = f"thread_note_{worker_id}.md"
            fpath = vault_dir / rel_name
            fpath.write_text(
                f"# Thread Worker Note {worker_id}\n\n"
                f"## Section A\nWorker {worker_id} content stream.\n\n"
                f"## Section B\nTelemetry stream for worker {worker_id}.\n",
                encoding="utf-8"
            )

            w_chunks = chunker.chunk_file(rel_name, fpath)
            w_vecs = client.get_embeddings([c.text for c in w_chunks])
            store.upsert_chunks(w_chunks, w_vecs)

            w_record = {
                "artifact_id": f"art_w_{worker_id}",
                "artifact_type": "concurrent_sync",
                "title": f"Worker {worker_id} Sync",
                "source_node": f"Node_{worker_id}",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": ["concurrent", "thread_safe"],
                "payload_json": json.dumps({"worker": worker_id, "chunks": len(w_chunks)}),
                "sha256_hash": f"{worker_id}" * 64,
                "metadata_json": "{}",
                "created_at_epoch_ms": int(time.time() * 1000),
            }
            writer.write([w_record])
            return len(w_chunks)

        num_workers = 6
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            chunk_counts = list(executor.map(worker_task, range(num_workers)))

        total_expected_chunks = sum(chunk_counts)

        # Verify Qdrant points count
        qdrant_stats = store.get_stats()
        assert qdrant_stats["points_count"] == total_expected_chunks

        # Verify Delta table has exactly 6 records without data loss
        dt = DeltaTable(str(delta_dir))
        assert len(dt.to_pyarrow_table()) == num_workers
