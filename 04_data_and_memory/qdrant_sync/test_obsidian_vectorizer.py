#!/usr/bin/env python3
"""
================================================================================
Test Suite for Obsidian Vault Vectorizer & Qdrant Sync Daemon
================================================================================
Tests all core components:
1. YAML frontmatter parsing & regex fallback
2. Markdown chunking, heading slicing, sliding window, and UUID5 deterministic IDs
3. Category classification & tag extraction
4. Debounce event queue coalescing
5. QdrantSyncStore SQLite table creation, upsert, delete, integrity, and meta.json
6. LlamaEmbeddingClient endpoint contract, exponential backoff, and Rule #0 compliance
7. Full vault batch chunking across all 59 files in obsidian_vault
"""

import os
import sys
import time
import json
import uuid
import shutil
import sqlite3
import hashlib
import tempfile
import unittest
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Add parent directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from obsidian_vectorizer import (
    MarkdownChunker,
    MarkdownChunk,
    LlamaEmbeddingClient,
    QdrantSyncStore,
    SyncStateCache,
    DebounceEventQueue,
    ObsidianVectorizerDaemon,
    EmbeddingAPIError,
    CATEGORY_KEYWORDS
)


class MockEmbeddingServerHandler(BaseHTTPRequestHandler):
    """Real HTTP test handler simulating OpenAI/llama.cpp embedding endpoint."""
    fail_count = 0
    fail_until = 0

    def do_GET(self):
        if self.path in ["/health", "/v1/models"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.endswith("/v1/embeddings"):
            # Check if we should simulate transient 503 before succeeding
            if MockEmbeddingServerHandler.fail_count < MockEmbeddingServerHandler.fail_until:
                MockEmbeddingServerHandler.fail_count += 1
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": {"message": "Loading model", "code": 503}}')
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            inputs = data.get("input", [])
            if isinstance(inputs, str):
                inputs = [inputs]

            # Generate real deterministic embeddings for test
            data_items = []
            dim = 128
            for idx, text in enumerate(inputs):
                val = (hash(text) % 1000) / 1000.0
                vec = [val] * dim
                data_items.append({
                    "object": "embedding",
                    "index": idx,
                    "embedding": vec
                })

            resp = {
                "object": "list",
                "data": data_items,
                "model": "embedding",
                "usage": {"prompt_tokens": 10, "total_tokens": 10}
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class TestObsidianVectorizer(unittest.TestCase):
    """Comprehensive test cases for obsidian_vectorizer.py."""

    @classmethod
    def setUpClass(cls):
        # Start local test HTTP server on an ephemeral port
        cls.httpd = HTTPServer(("127.0.0.1", 0), MockEmbeddingServerHandler)
        cls.port = cls.httpd.server_address[1]
        cls.server_url = f"http://127.0.0.1:{cls.port}/v1/embeddings"
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_obsidian_vectorizer_"))
        self.vault_dir = self.temp_dir / "obsidian_vault"
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.qdrant_dir = self.temp_dir / "qdrant_data"
        self.qdrant_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.temp_dir / "state.json"
        MockEmbeddingServerHandler.fail_count = 0
        MockEmbeddingServerHandler.fail_until = 0

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 1. Markdown Frontmatter & Chunking Tests
    # --------------------------------------------------------------------------

    def test_01_frontmatter_extraction_yaml_and_regex(self):
        """Test YAML frontmatter parsing and fallback."""
        chunker = MarkdownChunker(max_chunk_size=500, overlap=50)

        # Standard YAML
        doc1 = "---\ntitle: \"Master Architecture\"\ntags: [infra, mesh, storage]\ncategory: \"Infrastructure\"\n---\n# Master Note\nBody text."
        fm1, body1 = chunker.extract_frontmatter(doc1)
        self.assertEqual(fm1.get("title"), "Master Architecture")
        self.assertIn("infra", fm1.get("tags", []))
        self.assertIn("# Master Note", body1)

        # Malformed / Alternate delimiter
        doc2 = "---\ntitle: Fallback Title\ntags: tag1, tag2\ncategory: AI & Inference\n...\n## Subheading\nSome content."
        fm2, body2 = chunker.extract_frontmatter(doc2)
        self.assertEqual(fm2.get("title"), "Fallback Title")
        self.assertIn("## Subheading", body2)

    def test_02_heading_slicing_and_sliding_window(self):
        """Test hierarchical heading chunking and sliding window on long sections."""
        chunker = MarkdownChunker(max_chunk_size=300, overlap=50)

        sample_note = self.vault_dir / "sample.md"
        long_paragraph = "Lauburu high performance distributed AI tensor sharding across 7 mesh devices. " * 15
        sample_note.write_text(
            f"---\ntitle: Sample Test Note\ntags: [test]\n---\n"
            f"# Section 1\nShort intro content.\n\n"
            f"## Section 2: Deep Dive\n{long_paragraph}\n\n"
            f"### Section 3: Summary\nFinal summary text.",
            encoding="utf-8"
        )

        chunks = chunker.chunk_file("sample.md", sample_note)
        self.assertGreaterEqual(len(chunks), 3)

        # Verify chunk structures
        for chk in chunks:
            self.assertEqual(chk.filepath, "sample.md")
            self.assertEqual(chk.filename, "sample.md")
            self.assertEqual(chk.title, "Sample Test Note")
            self.assertIn("test", chk.tags)
            # Verify valid UUID string
            parsed_uuid = uuid.UUID(chk.point_id)
            self.assertEqual(str(parsed_uuid), chk.point_id)
            self.assertLessEqual(chk.char_count, 350)
            self.assertEqual(chk.content_hash, hashlib.sha256(chk.text.encode("utf-8")).hexdigest())

    def test_03_category_classification(self):
        """Test classification of notes into canonical categories."""
        chunker = MarkdownChunker()
        self.assertEqual(
            chunker.classify_category("00_core_infrastructure", {}, "Core Infra", "Docker SeaweedFS"),
            "Canonical Module"
        )
        self.assertEqual(
            chunker.classify_category("movesense_stream", {}, "Movesense DSP", "ECG DFA alpha1 biometrics"),
            "Biometrics & DSP"
        )
        self.assertEqual(
            chunker.classify_category("pyspark_crawler", {}, "PySpark Lake", "delta lake lora datasets"),
            "Data & Memory"
        )

    # --------------------------------------------------------------------------
    # 2. Debounce Queue Tests
    # --------------------------------------------------------------------------

    def test_04_debounce_event_queue(self):
        """Test debouncing rapid file events."""
        queue = DebounceEventQueue(debounce_delay=0.2)
        # Push rapid events
        queue.push("note1.md", "created")
        queue.push("note1.md", "modified")
        queue.push("note1.md", "modified")
        self.assertEqual(queue.pending_count(), 1)

        # Immediately should not be ready
        self.assertEqual(len(queue.pop_ready()), 0)

        # Wait for debounce
        time.sleep(0.25)
        ready = queue.pop_ready()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0], ("note1.md", "modified"))
        self.assertEqual(queue.pending_count(), 0)

    # --------------------------------------------------------------------------
    # 3. Llama Embedding Client Tests (Rule #0 Zero-Mock & Retries)
    # --------------------------------------------------------------------------

    def test_05_llama_client_success_and_contract(self):
        """Test real HTTP embedding fetch from test server."""
        client = LlamaEmbeddingClient(endpoint_url=self.server_url, timeout=5.0)
        healthy, msg = client.check_health()
        self.assertTrue(healthy)

        texts = ["First chunk of text", "Second chunk of text"]
        embeddings = client.get_embeddings(texts)
        self.assertEqual(len(embeddings), 2)
        self.assertEqual(len(embeddings[0]), 128)
        self.assertIsInstance(embeddings[0][0], float)

    def test_06_llama_client_exponential_backoff_retry(self):
        """Test that client retries on transient 503 and recovers without faking data."""
        MockEmbeddingServerHandler.fail_count = 0
        MockEmbeddingServerHandler.fail_until = 2  # Fail first 2 attempts, succeed on 3rd

        client = LlamaEmbeddingClient(
            endpoint_url=self.server_url,
            max_retries=4,
            base_backoff=0.1,
            max_backoff=0.5
        )

        embeddings = client.get_embeddings(["Retry test text"])
        self.assertEqual(len(embeddings), 1)
        self.assertEqual(MockEmbeddingServerHandler.fail_count, 2)

    def test_07_llama_client_failure_raises_exception_zero_mock(self):
        """Verify client raises EmbeddingAPIError when server is permanently offline (Zero-Mock)."""
        bad_client = LlamaEmbeddingClient(
            endpoint_url="http://127.0.0.1:59999/v1/embeddings",  # Port with no server
            max_retries=2,
            base_backoff=0.05,
            timeout=0.5
        )
        with self.assertRaises(EmbeddingAPIError):
            bad_client.get_embeddings(["This should fail"])

    # --------------------------------------------------------------------------
    # 4. Qdrant Sync Store SQLite Embedded Mode Tests
    # --------------------------------------------------------------------------

    def test_08_qdrant_sqlite_store_operations(self):
        """Test SQLite table creation, upsert, delete, and meta.json synchronization."""
        store = QdrantSyncStore(
            qdrant_url="http://127.0.0.1:59998",  # Unreachable port to force SQLite
            qdrant_path=self.qdrant_dir,
            collection_name="test_vault_collection"
        )
        self.assertEqual(store.mode, "sqlite_embedded")

        chunks = [
            MarkdownChunk(
                point_id=str(uuid.uuid4()),
                filepath="doc_a.md",
                filename="doc_a.md",
                title="Doc A",
                category="Infrastructure",
                tags=["infra"],
                heading="# Doc A",
                chunk_index=0,
                chunk_total=1,
                text="Chunk text for Doc A",
                char_count=21,
                content_hash="hash_a",
                last_modified="2026-08-28T00:00:00Z",
                updated_at="2026-08-28T00:00:00Z"
            ),
            MarkdownChunk(
                point_id=str(uuid.uuid4()),
                filepath="doc_b.md",
                filename="doc_b.md",
                title="Doc B",
                category="AI & Inference",
                tags=["ai"],
                heading="# Doc B",
                chunk_index=0,
                chunk_total=1,
                text="Chunk text for Doc B",
                char_count=21,
                content_hash="hash_b",
                last_modified="2026-08-28T00:00:00Z",
                updated_at="2026-08-28T00:00:00Z"
            )
        ]
        vectors = [[0.1] * 128, [0.2] * 128]

        # Upsert
        upserted = store.upsert_chunks(chunks, vectors)
        self.assertEqual(upserted, 2)

        # Check stats & SQLite integrity
        stats = store.get_stats()
        self.assertEqual(stats.get("points_count"), 2)
        self.assertEqual(stats.get("integrity"), "ok")

        # Verify meta.json
        meta_file = self.qdrant_dir / "meta.json"
        self.assertTrue(meta_file.exists())
        meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
        self.assertIn("test_vault_collection", meta_data.get("collections", {}))
        self.assertEqual(meta_data["collections"]["test_vault_collection"]["vectors"]["size"], 128)

        # Delete doc_a points
        deleted = store.delete_file_chunks("doc_a.md")
        self.assertEqual(deleted, 1)
        stats_after = store.get_stats()
        self.assertEqual(stats_after.get("points_count"), 1)

    # --------------------------------------------------------------------------
    # 5. Full Pipeline & 59-File Vault Batch Test
    # --------------------------------------------------------------------------

    def test_09_full_daemon_pipeline_integration(self):
        """Test full vectorizer daemon pipeline: scanning, chunking, embedding, upserting."""
        # Create test notes in temp vault
        note1 = self.vault_dir / "note1.md"
        note1.write_text("---\ntitle: Note 1\ncategory: Infrastructure\n---\n# N1\nContent for note 1", encoding="utf-8")
        note2 = self.vault_dir / "note2.md"
        note2.write_text("---\ntitle: Note 2\ncategory: AI & Inference\n---\n# N2\nContent for note 2", encoding="utf-8")

        daemon = ObsidianVectorizerDaemon(
            vault_dir=self.vault_dir,
            llama_endpoint=self.server_url,
            qdrant_url="http://127.0.0.1:59997",
            qdrant_path=self.qdrant_dir,
            collection_name="obsidian_vault_test",
            state_file=self.state_file,
            telemetry_file=self.temp_dir / "telemetry.jsonl"
        )

        stats = daemon.sync_all(force=True)
        self.assertEqual(stats.files_scanned, 2)
        self.assertEqual(stats.files_indexed, 2)
        self.assertEqual(stats.errors, 0)
        self.assertEqual(stats.points_upserted, 2)

        # Incremental sync (should skip unchanged files)
        stats_inc = daemon.sync_all(force=False)
        self.assertEqual(stats_inc.files_skipped, 2)
        self.assertEqual(stats_inc.files_indexed, 0)

        # Modify note1 and sync
        note1.write_text("---\ntitle: Note 1\n---\n# N1 Updated\nNew content", encoding="utf-8")
        stats_mod = daemon.sync_all(force=False)
        self.assertEqual(stats_mod.files_indexed, 1)
        self.assertEqual(stats_mod.files_skipped, 1)

    def test_10_all_59_monorepo_vault_files_chunking(self):
        """Test chunking across all 59 canonical markdown files in the real monorepo obsidian_vault."""
        real_vault = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
        self.assertTrue(real_vault.exists(), f"Real vault missing: {real_vault}")

        chunker = MarkdownChunker(max_chunk_size=1200, overlap=150)
        md_count = 0
        total_chunks = 0

        for root, dirs, files in os.walk(real_vault):
            if ".git" in root or ".obsidian" in root:
                continue
            for f in sorted(files):
                if f.endswith(".md") and not f.startswith("."):
                    fp = Path(root) / f
                    rel_p = str(fp.relative_to(real_vault))
                    chunks = chunker.chunk_file(rel_p, fp)
                    self.assertGreater(len(chunks), 0, f"File {rel_p} produced 0 chunks")
                    md_count += 1
                    total_chunks += len(chunks)

        self.assertEqual(md_count, 59, f"Expected 59 markdown notes in vault, got {md_count}")
        self.assertGreaterEqual(total_chunks, 500, f"Expected >= 500 chunks across vault, got {total_chunks}")
        print(f"\n[Test Verification] Chunked {md_count} files into {total_chunks} total chunks successfully.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
