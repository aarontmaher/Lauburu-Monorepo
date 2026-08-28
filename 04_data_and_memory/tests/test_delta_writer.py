"""Unit tests for DeltaDatasetWriter."""
import os
import shutil
import tempfile
import threading
import pytest
import pyarrow as pa

from delta_engine.writer import DeltaDatasetWriter
from delta_engine.schema import TRUTH_AUDIT_ARROW_SCHEMA, SFT_TRAINING_ARROW_SCHEMA


@pytest.fixture
def temp_delta_dir():
    tmp = tempfile.mkdtemp(prefix="test_delta_writer_")
    yield tmp
    if os.path.exists(tmp):
        shutil.rmtree(tmp)


def test_delta_writer_single_write(temp_delta_dir):
    writer = DeltaDatasetWriter(table_uri=temp_delta_dir, schema=TRUTH_AUDIT_ARROW_SCHEMA)
    record = {
        "artifact_id": "art_test_001",
        "artifact_type": "AUDIT_TEST",
        "title": "Unit Test Artifact",
        "source_node": "Mac_Node",
        "timestamp": "2026-08-28T00:00:00Z",
        "tags": ["test", "delta"],
        "payload_json": '{"status": "ok"}',
        "sha256_hash": "a" * 64,
        "metadata_json": "{}",
        "created_at_epoch_ms": 1724800000000,
    }
    res = writer.write(record)
    assert res["status"] == "success"
    assert res["version"] == 0
    assert res["rows_written"] == 1
    assert writer.count_rows() == 1


def test_delta_writer_micro_batch_buffering(temp_delta_dir):
    with DeltaDatasetWriter(
        table_uri=temp_delta_dir,
        schema=SFT_TRAINING_ARROW_SCHEMA,
        buffer_size=5,
    ) as writer:
        for i in range(12):
            record = {
                "pair_id": f"pair_{i:03d}",
                "dataset_name": "sft_test",
                "format": "alpaca",
                "instruction": f"Instruction {i}",
                "thought": f"Thought {i}",
                "solution": f"Solution {i}",
                "messages_json": "[]",
                "system_prompt": "You are a helpful AI.",
                "consensus_score": 99.5,
                "pillar": "AI_Telemetry",
                "source_node": "Mac_Node",
                "timestamp": "2026-08-28T00:00:00Z",
                "metadata_json": "{}",
            }
            writer.append(record)

    # After exiting context manager, all 12 rows should be flushed
    assert writer.count_rows() == 12


def test_delta_writer_schema_evolution(temp_delta_dir):
    writer = DeltaDatasetWriter(table_uri=temp_delta_dir, schema_mode="merge")
    # Write initial batch with 2 columns
    t1 = pa.Table.from_pydict({"col_a": [1, 2], "col_b": ["x", "y"]})
    writer.write(t1)
    assert writer.count_rows() == 2

    # Write second batch with a new column col_c
    t2 = pa.Table.from_pydict({"col_a": [3], "col_c": [99.9]})
    writer.write(t2)
    assert writer.count_rows() == 3

    dt = writer.get_table()
    arrow_table = dt.to_pyarrow_table()
    assert "col_a" in arrow_table.column_names
    assert "col_b" in arrow_table.column_names
    assert "col_c" in arrow_table.column_names


def test_delta_writer_multithreaded_concurrency(temp_delta_dir):
    writer = DeltaDatasetWriter(table_uri=temp_delta_dir, buffer_size=1)
    num_threads = 4
    records_per_thread = 10

    def worker_fn(thread_id):
        for j in range(records_per_thread):
            rec = {
                "thread_id": thread_id,
                "seq": j,
                "payload": f"Thread {thread_id} item {j}",
            }
            writer.write(rec)

    threads = [threading.Thread(target=worker_fn, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert writer.count_rows() == num_threads * records_per_thread
