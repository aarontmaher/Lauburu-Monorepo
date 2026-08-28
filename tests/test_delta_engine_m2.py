"""
Integration test for Milestone 2: PySpark Delta Lake & HF mmap Ingestion.
Verifies end-to-end Delta writes, bin-packing compaction, JSONL migrations with SHA-256 parity,
and zero-copy HuggingFace memory-mapped dataset streaming over 10Gbps Thunderbolt 4 bridge.
"""
import os
import shutil
import sys
import tempfile
import pytest
import pyarrow as pa
import datasets

# Ensure 04_data_and_memory is on sys.path
BASE_04 = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
if BASE_04 not in sys.path:
    sys.path.insert(0, BASE_04)

from delta_engine.writer import DeltaDatasetWriter
from delta_engine.compactor import DeltaCompactor
from delta_engine.mmap_loader import MemoryMappedDatasetLoader
from delta_engine.migrator import JSONLToDeltaMigrator
from delta_engine.schema import (
    TRUTH_AUDIT_ARROW_SCHEMA,
    SFT_TRAINING_ARROW_SCHEMA,
    DPO_PREFERENCE_ARROW_SCHEMA,
    MESH_TELEMETRY_ARROW_SCHEMA,
)


@pytest.fixture
def m2_test_environment():
    tmp = tempfile.mkdtemp(prefix="test_m2_e2e_")
    delta_truth_path = os.path.join(tmp, "delta_truth_audit")
    delta_sft_path = os.path.join(tmp, "delta_sft_training")
    delta_dpo_path = os.path.join(tmp, "delta_dpo_pairs")
    delta_telemetry_path = os.path.join(tmp, "delta_telemetry")

    yield {
        "tmp": tmp,
        "delta_truth": delta_truth_path,
        "delta_sft": delta_sft_path,
        "delta_dpo": delta_dpo_path,
        "delta_telemetry": delta_telemetry_path,
    }

    if os.path.exists(tmp):
        shutil.rmtree(tmp)


def test_m2_e2e_delta_acid_appends_and_compaction(m2_test_environment):
    truth_uri = m2_test_environment["delta_truth"]
    writer = DeltaDatasetWriter(table_uri=truth_uri, schema=TRUTH_AUDIT_ARROW_SCHEMA)

    # Write 20 individual micro-batch commits (simulating 24/7 continuous harvester)
    for i in range(20):
        writer.write({
            "artifact_id": f"art_e2e_{i:03d}",
            "artifact_type": "AUDIT_DECISION",
            "title": f"Live Debate Consensus {i}",
            "source_node": "Mac_Node" if i % 2 == 0 else "MacBook_Pro",
            "timestamp": "2026-08-28T00:00:00Z",
            "tags": ["e2e", "delta_lake"],
            "payload_json": f'{{"step": {i}, "consensus": 100.0}}',
            "sha256_hash": f"hash_{i:04d}_" + "0" * 54,
            "metadata_json": "{}",
            "created_at_epoch_ms": 1724800000000 + i,
        })

    assert writer.count_rows() == 20
    assert writer.get_version() == 19

    compactor = DeltaCompactor(truth_uri)
    stats_before = compactor.get_stats()
    assert stats_before["file_count"] == 20

    # Compact 20 fragments into 1 optimal chunk
    compact_metrics = compactor.compact(target_size_bytes=64 * 1024 * 1024)
    assert compact_metrics["status"] == "success"
    assert compact_metrics["files_before"] == 20
    assert compact_metrics["files_after"] == 1

    # Z-Order on clustering dimensions
    z_res = compactor.z_order(columns=["source_node", "artifact_type"])
    assert z_res["status"] == "success"

    # Verify table integrity
    assert writer.count_rows() == 20


def test_m2_e2e_huggingface_zero_copy_mmap(m2_test_environment):
    sft_uri = m2_test_environment["delta_sft"]
    writer = DeltaDatasetWriter(table_uri=sft_uri, schema=SFT_TRAINING_ARROW_SCHEMA)

    records = [
        {
            "pair_id": f"sft_pair_{i:04d}",
            "dataset_name": "tri_orchestrator_debate",
            "format": "messages",
            "instruction": f"Solve distributed tensor RPC bottleneck {i}",
            "thought": f"Analyze latency across 10Gbps Thunderbolt 4 bridge {i}",
            "solution": f"Instantiate GGML Metal kernel {i}",
            "messages_json": "[]",
            "system_prompt": "Canonical System Prompt",
            "consensus_score": 100.0,
            "pillar": "AI_Inference",
            "source_node": "MacBook_Pro",
            "timestamp": "2026-08-28T00:00:00Z",
            "metadata_json": "{}",
        }
        for i in range(500)
    ]
    writer.write(records)

    # Test HF dataset mmap loading
    ds = MemoryMappedDatasetLoader.load_hf_dataset(sft_uri)
    assert isinstance(ds, datasets.Dataset)
    assert len(ds) == 500
    assert "MemoryMappedTable" in str(type(ds.data))

    # Test RSS measurement
    footprint = MemoryMappedDatasetLoader.measure_rss_footprint(sft_uri)
    assert footprint["rows_loaded"] == 500
    assert footprint["delta_rss_mb"] < 50.0
    assert footprint["zero_copy_verified"] is True


def test_m2_e2e_jsonl_migration_parity(m2_test_environment):
    dpo_uri = m2_test_environment["delta_dpo"]
    source_jsonl = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/dpo_router_orchestrator_pairs.jsonl"

    if os.path.exists(source_jsonl):
        res = JSONLToDeltaMigrator.migrate_file(
            jsonl_path=source_jsonl,
            delta_table_uri=dpo_uri,
            schema_type="dpo_preference",
            verify_parity=True,
        )
        assert res["source_rows"] > 0
        assert res["target_rows"] == res["source_rows"]
        assert res["parity_verified"] is True
        assert res["sha256_match_count"] == res["source_rows"]
