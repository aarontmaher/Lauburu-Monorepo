"""Unit tests for DeltaCompactor."""
import os
import shutil
import tempfile
import pytest
import pyarrow as pa

from delta_engine.writer import DeltaDatasetWriter
from delta_engine.compactor import DeltaCompactor
from delta_engine.schema import TRUTH_AUDIT_ARROW_SCHEMA


@pytest.fixture
def populated_delta_dir():
    tmp = tempfile.mkdtemp(prefix="test_delta_compactor_")
    writer = DeltaDatasetWriter(table_uri=tmp, schema=TRUTH_AUDIT_ARROW_SCHEMA)
    # Write 10 separate small commits (10 separate Parquet files)
    for i in range(10):
        rec = {
            "artifact_id": f"art_compaction_{i:02d}",
            "artifact_type": "AUDIT_RECORD",
            "title": f"Artifact {i}",
            "source_node": "Mac_Node",
            "timestamp": "2026-08-28T00:00:00Z",
            "tags": ["compaction_test"],
            "payload_json": '{"status": "ok"}',
            "sha256_hash": f"{i:02d}" + "f" * 62,
            "metadata_json": "{}",
            "created_at_epoch_ms": 1724800000000 + i,
        }
        writer.write(rec)
    yield tmp
    if os.path.exists(tmp):
        shutil.rmtree(tmp)


def test_delta_compactor_bin_packing(populated_delta_dir):
    compactor = DeltaCompactor(populated_delta_dir)
    stats_before = compactor.get_stats()
    assert stats_before["file_count"] == 10

    # Compact files into 128MB target size
    compact_res = compactor.compact(target_size_bytes=128 * 1024 * 1024)
    assert compact_res["status"] == "success"
    assert compact_res["files_before"] == 10
    assert compact_res["files_after"] == 1

    stats_after = compactor.get_stats()
    assert stats_after["file_count"] == 1

    # Verify total row count is completely preserved
    writer = DeltaDatasetWriter(populated_delta_dir)
    assert writer.count_rows() == 10


def test_delta_compactor_z_ordering(populated_delta_dir):
    compactor = DeltaCompactor(populated_delta_dir)
    z_res = compactor.z_order(columns=["source_node", "artifact_type"])
    assert z_res["status"] == "success"
    assert z_res["z_order_columns"] == ["source_node", "artifact_type"]


def test_delta_compactor_vacuum(populated_delta_dir):
    compactor = DeltaCompactor(populated_delta_dir)
    # First compact so there are tombstoned files
    compactor.compact()
    # Vacuum with 0 retention hours (without enforce retention duration)
    deleted = compactor.vacuum(retention_hours=0, enforce_retention_duration=False)
    # Should delete the 10 obsolete historical parquet fragments
    assert isinstance(deleted, list)
    assert len(deleted) == 10
