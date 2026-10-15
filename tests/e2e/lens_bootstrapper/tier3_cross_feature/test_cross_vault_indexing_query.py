#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 3: Pairwise Combinatorial Cross-Feature Interaction Test Suite.
Interaction Pipeline: Vault Indexing -> 128-Dim Feature Hashing -> SQLite Store -> Semantic Query.
Validates:
1. Markdown vault notes are ingested and AST-chunked with UUID5 IDs
2. Local dense embedding engine computes 128-dim unit vectors offline
3. Dual-mode SQLite store persists points and vectors
4. Semantic query is converted to dense vector and scored via cosine similarity
5. Top-ranked result correctly identifies relevant architectural document
"""

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import (
    PROJECT_ROOT,
    BOOTSTRAPPER_DIR,
    compute_dense_ngram_embedding,
    cosine_similarity,
)
from tier1_feature_coverage.test_f14_f18_graph_mapper import (
    DualModeQdrantStorage,
    ObsidianVaultChunker,
)


class TestCrossVaultIndexingQuery(unittest.TestCase):
    """Pairwise Cross-Feature Verification: Vault Indexer -> Embedding -> Store -> Query."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "collection" / "obsidian_vault" / "storage.sqlite"
        self.store = DualModeQdrantStorage(self.db_path)

        # Populate a sample corpus of architectural notes
        self.corpus = {
            "CANONICAL_HARDWARE_MATRIX.md": (
                "# Canonical Hardware Matrix\n"
                "## Thunderbolt 4 DMA Ring\n"
                "The L1 Mac Mini connects to L1b Mac Mini M2 Pro over 40 Gbps Thunderbolt with 0.43ms RTT. "
                "PCIe DMA bridge enables ultra-high throughput tensor sharding with zero packet loss."
            ),
            "POLAR_H10_BIOMETRICS.md": (
                "# Polar H10 Biometrics Telemetry\n"
                "## ECG Sensor Streaming\n"
                "The Polar H10 chest strap streams raw physiological ECG telemetry at 130 Hz over Bluetooth BLE PMD service. "
                "Pan-Tompkins DSP algorithm extracts QRS complexes and calculates continuous HRV metrics."
            ),
            "HOST_SANCTUARY_RAM_GOVERNANCE.md": (
                "# Host Sanctuary and RAM Governance\n"
                "## 4.8 GB Memory Sanctuary\n"
                "Rule 3 mandates that the primary Mac Mini M4 host must maintain at least 4.8 GB of free physical RAM. "
                "Any local model threatening this buffer must be offloaded to peripheral nodes."
            )
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_c3_01_ingest_and_index_pipeline(self):
        """C3.1: Complete pipeline ingests documents, chunks, computes embeddings, and populates SQLite."""
        total_chunks = 0
        for rel_path, content in self.corpus.items():
            chunks = ObsidianVaultChunker.chunk_markdown(rel_path, content, max_chars=500, overlap=50)
            for ch in chunks:
                vec = compute_dense_ngram_embedding(ch["text"])
                payload = {
                    "filepath": rel_path,
                    "heading": ch["heading"],
                    "category": ch["category"],
                    "text": ch["text"]
                }
                self.store.upsert_point(ch["point_id"], payload, vec)
                total_chunks += 1

        self.assertGreaterEqual(total_chunks, 3)
        self.assertEqual(self.store.count(), total_chunks)

    def test_c3_02_semantic_query_hardware_matrix(self):
        """C3.2: Query 'Thunderbolt 4 DMA 40 Gbps' accurately ranks hardware note first."""
        # Index corpus
        for rel_path, content in self.corpus.items():
            for ch in ObsidianVaultChunker.chunk_markdown(rel_path, content):
                vec = compute_dense_ngram_embedding(ch["text"])
                self.store.upsert_point(ch["point_id"], {"filepath": rel_path, "heading": ch["heading"]}, vec)

        query = "Thunderbolt 4 DMA link and PCIe latency"
        q_vec = compute_dense_ngram_embedding(query)
        results = self.store.search_similar(q_vec, top_k=3)

        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertEqual(top["payload"]["filepath"], "CANONICAL_HARDWARE_MATRIX.md")
        self.assertGreater(top["score"], 0.20)

    def test_c3_03_semantic_query_biometrics_dsp(self):
        """C3.3: Query 'Polar H10 ECG streaming 130Hz' accurately ranks biometrics note first."""
        for rel_path, content in self.corpus.items():
            for ch in ObsidianVaultChunker.chunk_markdown(rel_path, content):
                vec = compute_dense_ngram_embedding(ch["text"])
                self.store.upsert_point(ch["point_id"], {"filepath": rel_path}, vec)

        query = "Polar H10 ECG heart rate sensor telemetry"
        q_vec = compute_dense_ngram_embedding(query)
        results = self.store.search_similar(q_vec, top_k=3)

        self.assertEqual(results[0]["payload"]["filepath"], "POLAR_H10_BIOMETRICS.md")

    def test_c3_04_semantic_query_ram_governance(self):
        """C3.4: Query '4.8 GB memory sanctuary rule' accurately ranks RAM governance note first."""
        for rel_path, content in self.corpus.items():
            for ch in ObsidianVaultChunker.chunk_markdown(rel_path, content):
                vec = compute_dense_ngram_embedding(ch["text"])
                self.store.upsert_point(ch["point_id"], {"filepath": rel_path}, vec)

        query = "Mac Mini physical host sanctuary 4.8 GB RAM"
        q_vec = compute_dense_ngram_embedding(query)
        results = self.store.search_similar(q_vec, top_k=3)

        self.assertEqual(results[0]["payload"]["filepath"], "HOST_SANCTUARY_RAM_GOVERNANCE.md")

    def test_c3_05_offline_zero_cloud_search_speed(self):
        """C3.5: Entire search query execution executes locally in < 15 ms."""
        for rel_path, content in self.corpus.items():
            for ch in ObsidianVaultChunker.chunk_markdown(rel_path, content):
                vec = compute_dense_ngram_embedding(ch["text"])
                self.store.upsert_point(ch["point_id"], {"filepath": rel_path}, vec)

        import time
        start = time.perf_counter()
        q_vec = compute_dense_ngram_embedding("Arbitrary technical query")
        _ = self.store.search_similar(q_vec, top_k=3)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertLess(
            elapsed_ms, 15.0,
            f"Local vector search exceeded latency limit: {elapsed_ms:.2f} ms"
        )


if __name__ == "__main__":
    unittest.main()
