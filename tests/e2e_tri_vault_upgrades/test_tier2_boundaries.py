"""
================================================================================
TIER 2: BOUNDARY, ADVERSARIAL & CORNER CASE E2E TEST SUITE
================================================================================
Stress-tests boundary conditions, edge cases, corrupted inputs, rapid debouncing,
and fault handling across the Tri-Vault Storage components.

Test Areas Covered:
1. Empty vault directory and 0-byte / whitespace markdown files.
2. Non-existent path handling across Delta Lake, HuggingFace mmap, and Qdrant.
3. Rapid file change burst coalescing & debouncing queue.
4. Malformed frontmatter, giant single-line chunks, and extreme Unicode strings.
5. Error handling and retry exhaustion on embedding client failures.
"""
from __future__ import annotations

import os
import time
import json
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
EmbeddingAPIError = vectorizer_mod.EmbeddingAPIError
QdrantSyncStore = vectorizer_mod.QdrantSyncStore
DebounceEventQueue = vectorizer_mod.DebounceEventQueue


class TestEmptyVaultAndNotesBoundaries:
    """Boundary conditions for empty files, empty directories, and zero-length payloads."""

    def test_zero_byte_markdown_file(self, temp_workspace: Path):
        """Zero-byte markdown file must be parsed safely without exceptions."""
        empty_note = temp_workspace / "empty.md"
        empty_note.write_text("", encoding="utf-8")

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("empty.md", empty_note)
        # Empty file produces valid MarkdownChunk list without crashing
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0].filename == "empty.md"
        assert chunks[0].title == "empty"

    def test_whitespace_only_markdown_file(self, temp_workspace: Path):
        """File with only newlines and spaces must not crash chunker."""
        ws_note = temp_workspace / "whitespace.md"
        ws_note.write_text("   \n\n\t\t\n   ", encoding="utf-8")

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("whitespace.md", ws_note)
        assert isinstance(chunks, list)
        assert len(chunks) == 1

    def test_frontmatter_only_without_body(self, temp_workspace: Path):
        """Note with valid frontmatter but zero body text."""
        fm_note = temp_workspace / "fm_only.md"
        fm_note.write_text(
            "---\n"
            "title: \"Pure Frontmatter Note\"\n"
            "tags: [isolated, boundary]\n"
            "category: \"Architecture & Docs\"\n"
            "---\n",
            encoding="utf-8"
        )

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("fm_only.md", fm_note)
        assert len(chunks) >= 1
        assert chunks[0].title == "Pure Frontmatter Note"
        assert "isolated" in chunks[0].tags

    def test_body_only_without_frontmatter_or_headings(self, temp_workspace: Path):
        """Note with unstructured raw text (no frontmatter, no # headings)."""
        raw_note = temp_workspace / "raw.md"
        raw_text = "This is a single paragraph without any frontmatter or markdown headings."
        raw_note.write_text(raw_text, encoding="utf-8")

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("raw.md", raw_note)
        assert len(chunks) == 1
        assert raw_text in chunks[0].text
        assert chunks[0].title == "raw"

    def test_delta_writer_empty_batch(self, temp_workspace: Path):
        """DeltaDatasetWriter must return noop when passed empty list."""
        table_path = temp_workspace / "delta_empty_test"
        writer = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)
        res = writer.write([])
        assert res["status"] == "noop"
        assert res["rows_written"] == 0


class TestNonExistentPathsBoundaries:
    """Handling missing directories, missing files, and non-existent tables."""

    def test_chunker_non_existent_file(self, temp_workspace: Path):
        """Chunker must return empty list when targeting a non-existent file path."""
        non_existent = temp_workspace / "does_not_exist.md"
        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("does_not_exist.md", non_existent)
        assert chunks == []

    def test_qdrant_store_delete_non_existent_file(self, temp_workspace: Path):
        """Deleting chunks for a non-existent filepath must return 0 deleted points without error."""
        qdrant_path = temp_workspace / "qdrant_boundary"
        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_path)
        store.ensure_collection(128)

        deleted = store.delete_file_chunks("non_existent_path.md")
        assert deleted == 0

    def test_delta_compactor_non_existent_table(self, temp_workspace: Path):
        """DeltaCompactor must raise FileNotFoundError for non-existent table directory."""
        non_existent_table = temp_workspace / "missing_delta_table"
        compactor = DeltaCompactor(non_existent_table)
        with pytest.raises(FileNotFoundError):
            compactor.get_table()

    def test_mmap_loader_non_existent_table(self, temp_workspace: Path):
        """MemoryMappedDatasetLoader must raise FileNotFoundError for non-existent table."""
        non_existent_table = temp_workspace / "missing_delta_table"
        with pytest.raises(FileNotFoundError):
            MemoryMappedDatasetLoader.load_hf_dataset(non_existent_table)


class TestDebounceAndRapidChangesBoundaries:
    """Verifies file change debouncing and burst event coalescing."""

    def test_debounce_burst_coalescing(self):
        """Rapid burst of 10 write events on the same file within 50ms must coalesce into 1 event."""
        queue = DebounceEventQueue(debounce_delay=0.15)
        test_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/burst_test.md"

        # Emit 10 rapid modification events
        for _ in range(10):
            queue.push(test_path, "modified")
            time.sleep(0.005)

        # Immediately check pending before debounce window expires
        assert queue.pending_count() == 1

        ready_before = queue.pop_ready()
        assert len(ready_before) == 0, "Events must not be ready before debounce delay expires"

        # Wait for debounce duration
        time.sleep(0.2)
        ready_after = queue.pop_ready()
        assert len(ready_after) == 1, "Burst must coalesce into exactly 1 ready event"
        assert ready_after[0][0] == test_path
        assert ready_after[0][1] == "modified"


class TestMalformedAndCorruptedInputsBoundaries:
    """Stress tests malformed YAML, massive single lines, Unicode symbols, and corrupted JSON."""

    def test_malformed_yaml_frontmatter(self, temp_workspace: Path):
        """Note with broken YAML frontmatter must fall back safely to regex or body text."""
        broken_note = temp_workspace / "broken_yaml.md"
        broken_note.write_text(
            "---\n"
            "title: [Unclosed bracket\n"
            "tags: {invalid: yaml: mapping\n"
            "random_junk: \"\"\"\n"
            "---\n"
            "# Recovered Note Title\n"
            "Content body following malformed frontmatter.\n",
            encoding="utf-8"
        )

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("broken_yaml.md", broken_note)
        assert len(chunks) >= 1
        assert any("Content body" in c.text for c in chunks)

    def test_massive_unspaced_string_chunking(self, temp_workspace: Path):
        """Extremely large 10,000-character unspaced string must be segmented without overflowing max_chunk_size."""
        massive_note = temp_workspace / "massive.md"
        giant_string = "X" * 10000
        massive_note.write_text(f"# Massive Header\n\n{giant_string}", encoding="utf-8")

        chunker = MarkdownChunker(max_chunk_size=1000, overlap=100)
        chunks = chunker.chunk_file("massive.md", massive_note)
        assert len(chunks) >= 10, f"Expected >=10 chunks for 10000 chars, got {len(chunks)}"
        for c in chunks:
            assert c.char_count <= 1100, f"Chunk size exceeded limit: {c.char_count}"

    def test_unicode_emojis_and_special_characters(self, temp_workspace: Path):
        """Note with emojis, Japanese/Chinese kanji, Arabic script, math formulas, and control characters."""
        unicode_note = temp_workspace / "unicode_stress.md"
        content = (
            "---\n"
            "title: \"🧬 Lauburu Mesh 🚀 108GB VRAM ⚡\"\n"
            "tags: [日本語, 机器学习, العربية, ∀x∈ℝ]\n"
            "category: \"AI & Inference\"\n"
            "---\n"
            "# 🧠 Neural Mesh Architecture\n\n"
            "## 数式 & Kinematics ∫_0^∞ e^{-x^2} dx = √π/2\n"
            "Multi-WAN failover with 0.27ms latency: 🚀 -> 🛰️ -> 📱\n"
        )
        unicode_note.write_text(content, encoding="utf-8")

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("unicode_stress.md", unicode_note)
        assert len(chunks) >= 2
        assert "🚀" in chunks[0].title
        assert "日本語" in chunks[0].tags
        assert any("∫_0^∞" in c.text for c in chunks)

    def test_embedding_client_connection_failure_retries_and_raises(self):
        """LlamaEmbeddingClient must retry on unreachable endpoint and raise EmbeddingAPIError."""
        client = LlamaEmbeddingClient(
            endpoint_url="http://127.0.0.1:9991/v1/embeddings",
            max_retries=2,
            base_backoff=0.01,
            max_backoff=0.02,
            timeout=0.2
        )
        with pytest.raises(EmbeddingAPIError):
            client.get_embeddings(["test embedding request"])
