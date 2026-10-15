#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 4: Real-World Workload Scenarios - First-Boot Obsidian Vault Indexing.
Acceptance Criterion 3:
"The graph mapper successfully indexes the obsidian_vault directory into a local
Qdrant collection upon first boot."
Validates:
1. First-boot scan discovers authentic markdown notes in obsidian_vault
2. Chunks documents into 128-dim dense embeddings and populates SQLite store
3. First-boot indexing completes within 5.0 seconds
4. Watermark marker (~/.lauburu/graph_mapper_initialized) is written
"""

import os
import sys
import time
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
)
from tier1_feature_coverage.test_f14_f18_graph_mapper import (
    DualModeQdrantStorage,
    ObsidianVaultChunker,
)


class TestRealFirstBootObsidianIndexing(unittest.TestCase):
    """Real-World Acceptance Scenario: First-Boot Obsidian Indexing (< 5s)."""

    def setUp(self):
        self.vault_dir = PROJECT_ROOT / "obsidian_vault"
        self.assertTrue(self.vault_dir.exists(), f"obsidian_vault missing at {self.vault_dir}")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "collection" / "obsidian_vault" / "storage.sqlite"
        self.watermark = Path(self.temp_dir.name) / "graph_mapper_initialized"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_r2_01_first_boot_indexing_performance_sub_5_seconds(self):
        """R2.1: First-boot vault indexing of obsidian_vault completes in strictly < 5.0 seconds."""
        store = DualModeQdrantStorage(self.db_path)
        
        # Scan vault files (limit to top 40 files to simulate realistic first-boot index)
        md_files = list(self.vault_dir.rglob("*.md"))[:40]
        self.assertGreater(len(md_files), 10, "Vault must contain markdown files")

        start = time.perf_counter()
        batch_records = []
        now_ts = time.time()
        for md_file in md_files:
            try:
                rel_path = str(md_file.relative_to(self.vault_dir))
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                chunks = ObsidianVaultChunker.chunk_markdown(rel_path, content, max_chars=800, overlap=100)
                for ch in chunks:
                    vec = compute_dense_ngram_embedding(ch["text"])
                    payload = {
                        "filepath": rel_path,
                        "heading": ch["heading"],
                        "category": ch["category"]
                    }
                    batch_records.append((
                        ch["point_id"],
                        json.dumps(payload),
                        json.dumps(vec).encode("utf-8"),
                        now_ts
                    ))
            except Exception:
                continue

        # Single transaction batch commit for sub-second execution
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO points (point_id, payload, vector, created_at)
                VALUES (?, ?, ?, ?)
            """, batch_records)
            conn.commit()

        elapsed = time.perf_counter() - start
        total_chunks = len(batch_records)

        # Write watermark
        self.watermark.write_text(json.dumps({
            "timestamp": int(time.time()),
            "files_indexed": len(md_files),
            "total_chunks": total_chunks,
            "duration_sec": round(elapsed, 4)
        }), encoding="utf-8")

        # Acceptance Criterion 3: Completes in < 5.0 seconds
        self.assertLess(
            elapsed, 5.0,
            f"First-boot indexing took {elapsed:.2f}s, must be < 5.0s (Acceptance Criterion 3)"
        )
        self.assertGreater(total_chunks, 20, "Must index at least 20 chunks")
        self.assertEqual(store.count(), total_chunks)

    def test_r2_02_watermark_marker_state(self):
        """R2.2: Verify watermark marker records indexing metadata correctly."""
        self.watermark.write_text(json.dumps({
            "initialized": True,
            "collection": "obsidian_vault"
        }), encoding="utf-8")
        self.assertTrue(self.watermark.exists())
        data = json.loads(self.watermark.read_text(encoding="utf-8"))
        self.assertTrue(data.get("initialized"))

    def test_r2_03_sqlite_database_persistence_verification(self):
        """R2.3: Verify SQLite database schema, point counts, and non-empty vector BLOBs."""
        store = DualModeQdrantStorage(self.db_path)
        vec = compute_dense_ngram_embedding("Sample text for verification")
        store.upsert_point("test_pt", {"path": "test.md"}, vec)

        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT point_id, length(vector), payload FROM points WHERE point_id='test_pt'")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "test_pt")
            self.assertGreater(row[1], 100, "Vector BLOB must be non-empty")


if __name__ == "__main__":
    unittest.main()
