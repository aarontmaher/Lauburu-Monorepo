"""
================================================================================
TIER 1: FEATURE COVERAGE & FUNCTIONAL UNIT E2E TEST SUITE
================================================================================
Verifies that each individual component, script, configuration, schema, and API
client fulfills its interface contract according to ORIGINAL_REQUEST.md & PROJECT.md.

Components Covered:
1. Pixel 10 Pro XL SeaweedFS Volume Daemon Script (`pixel_volume_daemon.sh`)
2. Cloudflare R2 Cloud Tiering Configuration (`r2_tiering_config.json`)
3. Delta Lake / delta-rs ACID Writer & Schema Normalizer
4. Memory-Mapped HuggingFace Dataset Loader & Zero-Bloat RSS Verification
5. Obsidian Vectorizer Chunker, Llama Embedding Client, & Qdrant Sync Store
"""
from __future__ import annotations

import os
import stat
import json
import subprocess
import importlib
from pathlib import Path
from typing import Dict, Any, List

import pytest
import pyarrow as pa
from deltalake import DeltaTable

# Import numbered modules via importlib
schema_mod = importlib.import_module("04_data_and_memory.delta_engine.schema")
writer_mod = importlib.import_module("04_data_and_memory.delta_engine.writer")
compactor_mod = importlib.import_module("04_data_and_memory.delta_engine.compactor")
mmap_mod = importlib.import_module("04_data_and_memory.delta_engine.mmap_loader")
vectorizer_mod = importlib.import_module("04_data_and_memory.qdrant_sync.obsidian_vectorizer")

TRUTH_AUDIT_ARROW_SCHEMA = schema_mod.TRUTH_AUDIT_ARROW_SCHEMA
SFT_TRAINING_ARROW_SCHEMA = schema_mod.SFT_TRAINING_ARROW_SCHEMA
DPO_PREFERENCE_ARROW_SCHEMA = schema_mod.DPO_PREFERENCE_ARROW_SCHEMA
MESH_TELEMETRY_ARROW_SCHEMA = schema_mod.MESH_TELEMETRY_ARROW_SCHEMA
get_schema_by_name = schema_mod.get_schema_by_name

DeltaDatasetWriter = writer_mod.DeltaDatasetWriter
DeltaCompactor = compactor_mod.DeltaCompactor
MemoryMappedDatasetLoader = mmap_mod.MemoryMappedDatasetLoader

MarkdownChunker = vectorizer_mod.MarkdownChunker
LlamaEmbeddingClient = vectorizer_mod.LlamaEmbeddingClient
QdrantSyncStore = vectorizer_mod.QdrantSyncStore


class TestPixelVolumeDaemonFeature:
    """Feature verification for 00_core_infrastructure/seaweedfs/pixel_volume_daemon.sh"""

    def test_daemon_script_exists_and_executable(self, canonical_paths: Dict[str, Path]):
        """Script must exist in canonical path and have executable permissions."""
        script = canonical_paths["pixel_script"]
        assert script.exists(), f"Missing pixel_volume_daemon.sh at {script}"
        assert script.is_file(), f"{script} is not a regular file"

        # Check executable bit
        file_stat = script.stat()
        is_executable = bool(file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        assert is_executable, f"pixel_volume_daemon.sh must be executable (mode {oct(file_stat.st_mode)})"

    def test_daemon_script_shebang(self, canonical_paths: Dict[str, Path]):
        """Script must declare valid Termux bash shebang for Android 15 execution."""
        script = canonical_paths["pixel_script"]
        with open(script, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        assert first_line == "#!/data/data/com.termux/files/usr/bin/bash", (
            f"Invalid shebang '{first_line}'. Expected '#!/data/data/com.termux/files/usr/bin/bash'"
        )

    def test_daemon_script_bash_syntax_validation(self, canonical_paths: Dict[str, Path]):
        """Script must pass static syntax checking via bash -n."""
        script = canonical_paths["pixel_script"]
        proc = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0, f"Bash syntax check failed: {proc.stderr}"

    def test_daemon_script_help_and_arguments(self, canonical_paths: Dict[str, Path]):
        """Script must display help text detailing flags and defaults."""
        script = canonical_paths["pixel_script"]
        proc = subprocess.run(
            ["bash", str(script), "--help"],
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0, f"Help command exited with {proc.returncode}: {proc.stderr}"
        out = proc.stdout
        assert "-dir" in out, "Help must document -dir parameter"
        assert "-mserver" in out, "Help must document -mserver parameter"
        assert "-ip" in out, "Help must document -ip parameter"
        assert "100.119.199.76:9333" in out, "Help must reference default Mac Mini Master IP:port"
        assert "100.73.38.87" in out, "Help must reference default Pixel 10 Pro XL Tailscale IP"
        assert "500" in out or "seaweedfs" in out, "Help must reference 500GB volume partition"

    def test_daemon_script_preflight_diagnostics(self, canonical_paths: Dict[str, Path], temp_workspace: Path):
        """Script --test action must run pre-flight diagnostics cleanly without crashing."""
        script = canonical_paths["pixel_script"]
        temp_dir = temp_workspace / "seaweed_test_dir"
        temp_dir.mkdir(parents=True, exist_ok=True)

        proc = subprocess.run(
            ["bash", str(script), "--test", "-dir", str(temp_dir)],
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0, f"Preflight test failed: {proc.stderr}\nStdout: {proc.stdout}"
        assert "PRE-FLIGHT TEST" in proc.stdout
        assert str(temp_dir) in proc.stdout


class TestR2TieringConfigFeature:
    """Feature verification for 00_core_infrastructure/seaweedfs/r2_tiering_config.json"""

    def test_r2_config_exists_and_valid_json(self, canonical_paths: Dict[str, Path]):
        """Config file must exist and parse as valid JSON."""
        config_path = canonical_paths["r2_config"]
        assert config_path.exists(), f"Missing r2_tiering_config.json at {config_path}"

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict), "Root of r2_tiering_config.json must be a JSON object"

    def test_r2_config_remote_storage_specification(self, canonical_paths: Dict[str, Path]):
        """Config must specify S3 Cloudflare R2 parameters and environment variable placeholders."""
        config_path = canonical_paths["r2_config"]
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "remote_storage" in data, "Must contain 'remote_storage' section"
        rs = data["remote_storage"]
        assert rs.get("name") == "cloudflare_r2"
        assert rs.get("type") == "s3"
        assert "s3" in rs, "Must contain 's3' configuration block"

        s3_conf = rs["s3"]
        assert "${R2_ACCESS_KEY}" in s3_conf.get("access_key", "")
        assert "${R2_SECRET_KEY}" in s3_conf.get("secret_key", "")
        assert "${R2_ENDPOINT}" in s3_conf.get("endpoint", "")
        assert "${R2_BUCKET}" in s3_conf.get("bucket", "")
        assert s3_conf.get("force_path_style") is True, "Cloudflare R2 requires force_path_style: true"

    def test_r2_config_tiering_policy(self, canonical_paths: Dict[str, Path]):
        """Config must define automated volume tiering policy and criteria."""
        config_path = canonical_paths["r2_config"]
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "tiering_policy" in data, "Must contain 'tiering_policy' section"
        tp = data["tiering_policy"]
        assert tp.get("enabled") is True
        assert tp.get("destination") == "cloudflare_r2"
        assert "${R2_BUCKET}" in tp.get("target_bucket", "")
        assert "criteria" in tp
        assert tp["criteria"].get("full_percent") >= 90
        assert tp.get("read_cache_enabled") is True


class TestDeltaLakeWriterFeature:
    """Feature verification for 04_data_and_memory/delta_engine/"""

    def test_canonical_schemas_registration(self):
        """Registry must contain all canonical schemas."""
        for schema_name in ["truth_audit", "sft_training", "dpo_preference", "mesh_telemetry"]:
            sch = get_schema_by_name(schema_name)
            assert sch is not None, f"Schema {schema_name} must be registered"
            assert isinstance(sch, pa.Schema)

    def test_delta_writer_single_and_batch_writes(self, temp_workspace: Path):
        """DeltaDatasetWriter must write ACID Delta Lake tables with _delta_log/ and Parquet files."""
        table_path = temp_workspace / "delta_test_table"
        writer = DeltaDatasetWriter(
            table_uri=table_path,
            schema=TRUTH_AUDIT_ARROW_SCHEMA,
            mode="append"
        )

        records = [
            {
                "artifact_id": f"art_{i}",
                "artifact_type": "debate_consensus",
                "title": f"Tri-Vault Upgrade Consensus {i}",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": ["delta", "pyspark", "lauburu"],
                "payload_json": json.dumps({"consensus_score": 0.99, "iteration": i}),
                "sha256_hash": "a" * 64,
                "metadata_json": "{}",
                "created_at_epoch_ms": 1787878800000 + i,
            }
            for i in range(5)
        ]

        # Write first batch
        res1 = writer.write(records)
        assert res1["status"] == "success"
        assert res1["rows_written"] == 5
        assert res1["version"] == 0

        # Verify filesystem artifacts
        assert (table_path / "_delta_log").is_dir()
        assert (table_path / "_delta_log" / "00000000000000000000.json").exists()

        parquet_files = list(table_path.glob("*.parquet"))
        assert len(parquet_files) >= 1, "Must generate at least one .parquet file"

        # Write second batch (appends new commit)
        records_2 = [
            {
                "artifact_id": f"art_second_{i}",
                "artifact_type": "audit_log",
                "title": f"Audit {i}",
                "source_node": "Pixel_10_Pro_XL",
                "timestamp": "2026-08-28T01:00:00Z",
                "tags": ["pixel", "seaweedfs"],
                "payload_json": "{}",
                "sha256_hash": "b" * 64,
                "metadata_json": "{}",
                "created_at_epoch_ms": 1787878900000,
            }
            for i in range(3)
        ]
        res2 = writer.write(records_2)
        assert res2["status"] == "success"
        assert res2["version"] == 1
        assert res2["total_rows"] == 8

        # Verify DeltaTable row count and version via deltalake library
        dt = DeltaTable(str(table_path))
        assert dt.version() == 1
        assert len(dt.to_pyarrow_table()) == 8

    def test_delta_compactor_bin_packing(self, temp_workspace: Path):
        """DeltaCompactor must optimize and bin-pack small Parquet ingestion files."""
        table_path = temp_workspace / "delta_compact_table"
        writer = DeltaDatasetWriter(table_path, schema=MESH_TELEMETRY_ARROW_SCHEMA)

        # Write 6 small distinct commits to produce multiple parquet files
        for i in range(6):
            rec = {
                "timestamp": "2026-08-28T00:00:00Z",
                "node_name": f"Node_{i}",
                "ip_address": f"192.168.8.{100 + i}",
                "latency_ms": 0.25 + i * 0.05,
                "status": "ONLINE",
                "transport": "TB4_10G",
                "jitter_ms": 0.02,
                "packet_loss_pct": 0.0,
            }
            writer.write([rec])

        stats_before = DeltaCompactor(table_path).get_stats()
        assert stats_before["file_count"] >= 6, "Expected at least 6 separate Parquet files before compaction"

        # Run compaction
        compactor = DeltaCompactor(table_path)
        compact_res = compactor.compact(target_size_bytes=10 * 1024 * 1024)
        assert compact_res["status"] == "success"

        stats_after = compactor.get_stats()
        assert stats_after["file_count"] < stats_before["file_count"], "Compaction must reduce active file count"

        # Verify data integrity: row count remains 6
        dt = DeltaTable(str(table_path))
        assert len(dt.to_pyarrow_table()) == 6


class TestMemoryMappedLoaderFeature:
    """Feature verification for MemoryMappedDatasetLoader (mmap with zero RAM bloat)"""

    def test_hf_dataset_mmap_loading_and_rss_footprint(self, temp_workspace: Path):
        """Loader must memory-map Delta Parquet tables with <50MB RSS memory footprint."""
        table_path = temp_workspace / "delta_mmap_table"
        writer = DeltaDatasetWriter(table_path, schema=SFT_TRAINING_ARROW_SCHEMA)

        # Write 50 synthetic training rows
        records = [
            {
                "pair_id": f"sft_pair_{i}",
                "dataset_name": "tri_orchestrator_debate",
                "format": "messages",
                "instruction": f"Optimize multi-path routing across layer {i % 7}",
                "thought": "Evaluate Speedify vs Thunderbolt 4 PCIe DMA latency.",
                "solution": "Route high-throughput tensor streams over 10Gbps Thunderbolt 4 bridge.",
                "messages_json": json.dumps([{"role": "user", "content": "hello"}]),
                "system_prompt": "You are a master mesh architect.",
                "consensus_score": 0.98,
                "pillar": "Infrastructure",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "metadata_json": "{}",
            }
            for i in range(50)
        ]
        writer.write(records)

        # Verify HuggingFace dataset loads with keep_in_memory=False
        hf_ds = MemoryMappedDatasetLoader.load_hf_dataset(table_path)
        assert len(hf_ds) == 50
        assert "pair_id" in hf_ds.column_names
        assert "instruction" in hf_ds.column_names
        assert hf_ds[0]["pair_id"] == "sft_pair_0"

        # Verify RSS footprint measurement
        rss_metrics = MemoryMappedDatasetLoader.measure_rss_footprint(table_path)
        assert rss_metrics["rows_loaded"] == 50
        assert rss_metrics["delta_rss_mb"] < 50.0, f"Memory bloat detected: {rss_metrics['delta_rss_mb']}MB"
        assert rss_metrics["zero_copy_verified"] is True

    def test_pyarrow_scanner_batch_streaming(self, temp_workspace: Path):
        """Loader must stream PyArrow RecordBatches directly via zero-copy scanner."""
        table_path = temp_workspace / "delta_stream_table"
        writer = DeltaDatasetWriter(table_path, schema=TRUTH_AUDIT_ARROW_SCHEMA)

        records = [
            {
                "artifact_id": f"art_stream_{i}",
                "artifact_type": "stream_test",
                "title": f"Stream Record {i}",
                "source_node": "Head_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "tags": ["stream"],
                "payload_json": "{}",
                "sha256_hash": "c" * 64,
                "metadata_json": "{}",
                "created_at_epoch_ms": 1787879000000,
            }
            for i in range(25)
        ]
        writer.write(records)

        batch_count = 0
        total_streamed_rows = 0
        for batch in MemoryMappedDatasetLoader.stream_batches(table_path, batch_size=10):
            assert isinstance(batch, pa.RecordBatch)
            batch_count += 1
            total_streamed_rows += batch.num_rows

        assert batch_count == 3  # 10 + 10 + 5
        assert total_streamed_rows == 25


class TestObsidianVectorizerFeature:
    """Feature verification for 04_data_and_memory/qdrant_sync/obsidian_vectorizer.py"""

    def test_markdown_chunker_frontmatter_and_headings(self, sample_vault_dir: Path):
        """MarkdownChunker must extract frontmatter, headings, tags, and category."""
        chunker = MarkdownChunker(max_chunk_size=600, overlap=50)
        note_path = sample_vault_dir / "00_core_infrastructure.md"

        chunks = chunker.chunk_file("00_core_infrastructure.md", note_path)
        assert len(chunks) >= 2, "Expected at least 2 heading chunks"

        # Check first chunk properties
        c0 = chunks[0]
        assert c0.filename == "00_core_infrastructure.md"
        assert c0.title == "00 Core Infrastructure Specification"
        assert "seaweedfs" in c0.tags
        assert c0.category == "Infrastructure"
        assert c0.chunk_total == len(chunks)
        assert len(c0.point_id) == 36  # Valid UUID format
        assert len(c0.content_hash) == 64  # Valid SHA-256

        # Convert to Qdrant payload dictionary
        payload = c0.to_payload()
        assert payload["filepath"] == "00_core_infrastructure.md"
        assert any("SeaweedFS" in c.text for c in chunks)

    def test_llama_embedding_client_live_connection(self, live_embedding_server: str):
        """LlamaEmbeddingClient must query embedding endpoint and receive vector responses."""
        client = LlamaEmbeddingClient(endpoint_url=live_embedding_server)

        # Health check
        healthy, msg = client.check_health()
        assert healthy is True, f"Llama health check failed: {msg}"

        # Fetch embeddings
        texts = [
            "SeaweedFS 500GB volume partition on Pixel 10 Pro XL",
            "Delta Lake ACID parquet compaction over Thunderbolt 4"
        ]
        vectors = client.get_embeddings(texts)
        assert len(vectors) == 2
        assert len(vectors[0]) == 128
        assert all(isinstance(x, float) for x in vectors[0])

    def test_qdrant_sync_store_embedded_operations(self, temp_workspace: Path, sample_vault_dir: Path):
        """QdrantSyncStore must support collection creation, chunk upsert, and deletion."""
        qdrant_path = temp_workspace / "qdrant_data"
        store = QdrantSyncStore(qdrant_url="http://127.0.0.1:9999", qdrant_path=qdrant_path, collection_name="test_vault")

        assert store.mode == "sqlite_embedded"

        chunker = MarkdownChunker()
        chunks = chunker.chunk_file("04_data_and_memory.md", sample_vault_dir / "04_data_and_memory.md")
        dummy_vectors = [[0.1] * 128 for _ in chunks]

        # Upsert chunks
        upserted = store.upsert_chunks(chunks, dummy_vectors)
        assert upserted == len(chunks)

        # Query stats
        stats = store.get_stats()
        assert stats["points_count"] == len(chunks)
        assert stats["status"] == "ok"

        # Delete chunks by file
        deleted = store.delete_file_chunks("04_data_and_memory.md")
        assert deleted == len(chunks)

        stats_after = store.get_stats()
        assert stats_after["points_count"] == 0
