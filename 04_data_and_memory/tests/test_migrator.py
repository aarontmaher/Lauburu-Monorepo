"""Unit tests for JSONLToDeltaMigrator."""
import json
import os
import shutil
import tempfile
import pytest

from delta_engine.migrator import JSONLToDeltaMigrator
from delta_engine.writer import DeltaDatasetWriter


@pytest.fixture
def temp_workspace():
    tmp = tempfile.mkdtemp(prefix="test_migrator_")
    jsonl_path = os.path.join(tmp, "sample_dpo_pairs.jsonl")
    delta_dir = os.path.join(tmp, "delta_dpo_table")

    records = [
        {
            "pair_id": f"dpo_{i:03d}",
            "category": "Interconnect",
            "dimension": "Throughput",
            "prompt": f"Optimize bandwidth query {i}",
            "chosen": f"High performance kernel choice {i}",
            "rejected": f"Slow linear loop choice {i}",
            "consensus_score": 98.0 + (i * 0.1),
            "source": "Council_Debate",
            "timestamp": "2026-08-28T00:00:00Z",
            "metadata": {"test_id": i},
        }
        for i in range(25)
    ]

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    yield {"jsonl_path": jsonl_path, "delta_dir": delta_dir, "count": len(records), "tmp": tmp}

    if os.path.exists(tmp):
        shutil.rmtree(tmp)


def test_migrator_single_file_parity(temp_workspace):
    jsonl_path = temp_workspace["jsonl_path"]
    delta_dir = temp_workspace["delta_dir"]
    expected_count = temp_workspace["count"]

    res = JSONLToDeltaMigrator.migrate_file(
        jsonl_path=jsonl_path,
        delta_table_uri=delta_dir,
        schema_type="dpo_preference",
        verify_parity=True,
    )

    assert res["source_rows"] == expected_count
    assert res["target_rows"] == expected_count
    assert res["parity_verified"] is True
    assert res["sha256_match_count"] == expected_count

    writer = DeltaDatasetWriter(delta_dir)
    assert writer.count_rows() == expected_count


def test_migrator_directory(temp_workspace):
    tmp = temp_workspace["tmp"]
    src_dir = os.path.join(tmp, "raw_jsonls")
    tgt_base = os.path.join(tmp, "migrated_deltas")
    os.makedirs(src_dir, exist_ok=True)

    # Create 3 JSONL files
    for fidx in range(3):
        fpath = os.path.join(src_dir, f"dataset_{fidx}.jsonl")
        with open(fpath, "w", encoding="utf-8") as f:
            for j in range(10):
                f.write(json.dumps({"id": f"rec_{fidx}_{j}", "input": f"q{j}", "output": f"a{j}"}) + "\n")

    results = JSONLToDeltaMigrator.migrate_directory(
        source_dir=src_dir,
        target_base_dir=tgt_base,
        verify_parity=True,
    )

    assert len(results) == 3
    for r in results:
        assert r["source_rows"] == 10
        assert r["target_rows"] == 10
        assert r["parity_verified"] is True
