"""Unit tests for MemoryMappedDatasetLoader."""
import os
import shutil
import tempfile
import pytest
import pyarrow as pa
import datasets

from delta_engine.writer import DeltaDatasetWriter
from delta_engine.mmap_loader import MemoryMappedDatasetLoader
from delta_engine.schema import SFT_TRAINING_ARROW_SCHEMA


@pytest.fixture
def training_delta_dir():
    tmp = tempfile.mkdtemp(prefix="test_mmap_loader_")
    writer = DeltaDatasetWriter(table_uri=tmp, schema=SFT_TRAINING_ARROW_SCHEMA)
    rows = []
    for i in range(250):
        rows.append({
            "pair_id": f"pair_{i:04d}",
            "dataset_name": "sft_mmap_test",
            "format": "alpaca",
            "instruction": f"Instruction for training record {i} with extensive text payload.",
            "thought": f"Detailed step-by-step thought chain {i}.",
            "solution": f"Production output solution {i}.",
            "messages_json": "[]",
            "system_prompt": "Canonical System Prompt",
            "consensus_score": 100.0,
            "pillar": "AI_Inference",
            "source_node": "Mac_Node",
            "timestamp": "2026-08-28T00:00:00Z",
            "metadata_json": '{"tag": "mmap_verified"}',
        })
    writer.write(rows)
    yield tmp
    if os.path.exists(tmp):
        shutil.rmtree(tmp)


def test_mmap_loader_hf_dataset(training_delta_dir):
    ds = MemoryMappedDatasetLoader.load_hf_dataset(training_delta_dir)
    assert isinstance(ds, datasets.Dataset)
    assert len(ds) == 250
    assert "instruction" in ds.column_names
    assert "pair_id" in ds.column_names
    assert ds[0]["pair_id"] == "pair_0000"
    # Ensure backed by MemoryMappedTable
    assert "MemoryMappedTable" in str(type(ds.data))


def test_mmap_loader_column_selection(training_delta_dir):
    ds = MemoryMappedDatasetLoader.load_hf_dataset(
        training_delta_dir,
        columns=["pair_id", "instruction", "solution"]
    )
    assert ds.column_names == ["pair_id", "instruction", "solution"]
    assert len(ds) == 250


def test_mmap_loader_stream_batches(training_delta_dir):
    batch_count = 0
    total_rows = 0
    for batch in MemoryMappedDatasetLoader.stream_batches(training_delta_dir, batch_size=50):
        assert isinstance(batch, pa.RecordBatch)
        batch_count += 1
        total_rows += batch.num_rows

    assert batch_count == 5
    assert total_rows == 250


def test_mmap_loader_rss_footprint(training_delta_dir):
    metrics = MemoryMappedDatasetLoader.measure_rss_footprint(training_delta_dir)
    assert metrics["rows_loaded"] == 250
    assert metrics["delta_rss_mb"] < 50.0
    assert metrics["zero_copy_verified"] is True
    assert "MemoryMappedTable" in metrics["table_backend"]
