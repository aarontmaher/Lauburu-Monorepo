"""
================================================================================
TIER 4: REAL-WORLD APPLICATION SCENARIOS & LIVE VAULT BATCH SYNC
================================================================================
Executes complete production-scale batch parsing, vectorization, Qdrant indexing,
and Delta Lake auditing against all 59 live notes in the canonical Obsidian Knowledge Vault.

Scenarios Covered:
1. Live Obsidian Vault Discovery & 100% Parsing Integrity (All 59 Notes).
2. Canonical 13-Module Specification & Category Classification Audit.
3. Production Full-Vault Batch Vectorization & Qdrant Ingestion.
4. Comprehensive Delta Lake Telemetry Audit & Memory-Mapped Dataset Loading.
"""
from __future__ import annotations

import os
import time
import json
import uuid
import hashlib
import importlib
from pathlib import Path
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
DEFAULT_VAULT_DIR = vectorizer_mod.DEFAULT_VAULT_DIR


class TestRealWorldObsidianVaultSync:
    """Production-grade batch sync and integrity tests over the 59 live notes in obsidian_vault."""

    def test_live_vault_59_notes_discovery_and_parsing(self, canonical_paths: Dict[str, Path]):
        """Discovers and parses all 59 live notes in obsidian_vault with 100% success."""
        vault_path = canonical_paths["obsidian_vault"]
        assert vault_path.exists(), f"Obsidian vault missing at {vault_path}"

        # Find all markdown files excluding hidden directories
        live_files: List[Path] = []
        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.endswith(".md") and not f.startswith("."):
                    live_files.append(Path(root) / f)

        print(f"\n[Tier 4] Discovered {len(live_files)} live markdown notes in {vault_path}")
        assert len(live_files) == 59, f"Expected exactly 59 live notes, found {len(live_files)}"

        chunker = MarkdownChunker(max_chunk_size=1200, overlap=150)
        total_chunks = 0
        categories_found: Dict[str, int] = {}

        for md_path in live_files:
            rel_path = str(md_path.relative_to(vault_path))
            chunks = chunker.chunk_file(rel_path, md_path)

            assert len(chunks) > 0, f"Failed to produce chunks for live note {rel_path}"
            total_chunks += len(chunks)

            # Validate each chunk integrity
            for c in chunks:
                assert c.filepath == rel_path
                assert len(c.title) > 0
                assert len(c.point_id) == 36
                assert len(c.content_hash) == 64
                categories_found[c.category] = categories_found.get(c.category, 0) + 1

        print(f"[Tier 4] Total semantic chunks generated across 59 notes: {total_chunks}")
        print(f"[Tier 4] Category distribution: {categories_found}")

        assert total_chunks > 100, f"Expected >100 chunks across vault, got {total_chunks}"
        assert len(categories_found) >= 5, f"Expected diverse architectural categories, got {len(categories_found)}"

    def test_canonical_13_modules_presence(self, canonical_paths: Dict[str, Path]):
        """Verifies that all 13 canonical monorepo modules (00_ to 12_) exist and classify properly."""
        vault_path = canonical_paths["obsidian_vault"]
        canonical_module_files = [
            f"{i:02d}_{suffix}.md"
            for i, suffix in enumerate([
                "core_infrastructure",
                "apps",
                "ai_models_and_inference",
                "biometrics_and_telemetry",
                "data_and_memory",
                "agents_and_swarms",
                "scripts_and_tooling",
                "docs_and_architecture",
                "business_and_commerce",
                "app_store_and_release",
                "spatial_grappling_kinematics",
                "security_and_governance",
                "continuous_lora_evolution",
            ])
        ]

        chunker = MarkdownChunker()
        for mod_file in canonical_module_files:
            fpath = vault_path / mod_file
            assert fpath.exists(), f"Missing canonical module specification note: {mod_file}"

            chunks = chunker.chunk_file(mod_file, fpath)
            assert len(chunks) >= 1
            # Must classify as Canonical Module
            assert chunks[0].category == "Canonical Module", (
                f"Module {mod_file} should classify as 'Canonical Module', got {chunks[0].category}"
            )

    def test_full_vault_batch_indexing_into_qdrant_and_delta(
        self,
        temp_workspace: Path,
        canonical_paths: Dict[str, Path],
        live_embedding_server: str
    ):
        """
        Executes full batch vectorization and Qdrant ingestion of all 59 notes,
        writing an ACID Delta Lake audit dataset with memory-mapped verification.
        """
        vault_path = canonical_paths["obsidian_vault"]
        qdrant_dir = temp_workspace / "qdrant_full_vault"
        delta_dir = temp_workspace / "delta_full_vault_audit"

        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_dir, collection_name="obsidian_vault")
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)
        chunker = MarkdownChunker(max_chunk_size=1200, overlap=150)
        writer = DeltaDatasetWriter(delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)

        # Collect and chunk all 59 live notes
        live_files: List[Path] = []
        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.endswith(".md") and not f.startswith("."):
                    live_files.append(Path(root) / f)

        all_chunks = []
        for md_path in live_files:
            rel = str(md_path.relative_to(vault_path))
            file_chunks = chunker.chunk_file(rel, md_path)
            all_chunks.extend(file_chunks)

        print(f"\n[Tier 4 Full Batch] Vectorizing {len(all_chunks)} chunks across {len(live_files)} notes...")

        # Batch embed in groups of 32
        batch_size = 32
        all_vectors = []
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [c.text for c in batch]
            vecs = client.get_embeddings(texts)
            all_vectors.extend(vecs)

        assert len(all_vectors) == len(all_chunks)

        # Upsert all points into Qdrant
        upserted_points = store.upsert_chunks(all_chunks, all_vectors)
        assert upserted_points == len(all_chunks)

        qdrant_stats = store.get_stats()
        assert qdrant_stats["points_count"] == len(all_chunks)
        assert qdrant_stats["status"] == "ok"
        print(f"[Tier 4 Full Batch] Qdrant successfully populated with {qdrant_stats['points_count']} points.")

        # Log batch completion audit into Delta Lake
        audit_rows = [
            {
                "artifact_id": f"vault_sync_{uuid.uuid4().hex[:10]}",
                "artifact_type": "full_vault_batch_sync",
                "title": "Lauburu Monorepo Obsidian Full Vault 59-Note Synchronization",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": ["vault_sync", "qdrant", "delta_lake", "tier4", "production"],
                "payload_json": json.dumps({
                    "files_scanned": len(live_files),
                    "total_chunks": len(all_chunks),
                    "qdrant_points": upserted_points,
                    "storage_path": str(qdrant_dir),
                }),
                "sha256_hash": hashlib.sha256(f"sync_count_{len(all_chunks)}".encode("utf-8")).hexdigest(),
                "metadata_json": json.dumps({"engine": "delta-rs", "status": "COMPLETED_SUCCESS"}),
                "created_at_epoch_ms": int(time.time() * 1000),
            }
        ]
        res = writer.write(audit_rows)
        assert res["status"] == "success"

        # Compact Delta Table
        compactor = DeltaCompactor(delta_dir)
        compact_res = compactor.compact()
        assert compact_res["status"] == "success"

        # Memory-Map and verify RSS footprint
        rss_metrics = MemoryMappedDatasetLoader.measure_rss_footprint(delta_dir)
        assert rss_metrics["rows_loaded"] == 1
        assert rss_metrics["zero_copy_verified"] is True
        print(f"[Tier 4 Full Batch] Delta Lake Memory-Mapped RSS Delta: {rss_metrics['delta_rss_mb']}MB")
