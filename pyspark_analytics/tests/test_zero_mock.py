"""
Tests for Rule #0 Zero-Mock Verification Engine.
Asserts that synthetic or mock records are strictly rejected and valid organic trace records pass.
"""

import json
import os
import tempfile
import pytest
from pyspark_analytics.zero_mock import ZeroMockVerifier, RuleZeroError


def test_zero_mock_valid_organic_record():
    valid_record = {
        "prompt": "Fix TypeScript compilation error in cloudflare-worker/src/mcp-core.ts: Property 'status' does not exist on type 'LaneOverview'.",
        "chosen": "export interface LaneOverview {\n  status: string;\n  lastUpdated: string;\n}",
        "rejected": "export interface LaneOverview {\n  lastUpdated: string;\n}",
        "metadata": {
            "trace_file": "core/cloudflare-worker/test/test-mcp-core.ts",
            "exit_code": 1,
            "compiler_exit_code": 1,
            "timestamp": "2026-08-28T20:15:00Z",
            "duration_ms": 340,
            "environment": "linux_node_m4",
        },
    }

    assert ZeroMockVerifier.verify_record(valid_record) is True


def test_zero_mock_rejects_explicit_flag():
    mock_record = {
        "prompt": "Fix compiler error",
        "chosen": "code",
        "rejected": "bad_code",
        "is_mock": True,
        "metadata": {
            "trace_file": "traces/trace1.log",
            "exit_code": 1,
            "timestamp": "2026-08-28T20:15:00Z",
            "duration_ms": 100,
        },
    }

    with pytest.raises(RuleZeroError, match="flagged with is_mock=True"):
        ZeroMockVerifier.verify_record(mock_record)


def test_zero_mock_rejects_missing_provenance():
    no_trace_record = {
        "prompt": "Fix compiler error",
        "chosen": "code",
        "rejected": "bad_code",
        "metadata": {
            "exit_code": 1,
            "timestamp": "2026-08-28T20:15:00Z",
            "duration_ms": 100,
        },
    }

    with pytest.raises(RuleZeroError, match="Missing valid trace provenance"):
        ZeroMockVerifier.verify_record(no_trace_record)


def test_zero_mock_rejects_mock_content_indicator():
    mock_content_record = {
        "prompt": "[mock_prompt] simulate test run",
        "chosen": "mock_code_output",
        "rejected": "error",
        "metadata": {
            "trace_file": "traces/trace1.log",
            "exit_code": 1,
            "timestamp": "2026-08-28T20:15:00Z",
            "duration_ms": 100,
        },
    }

    with pytest.raises(RuleZeroError, match="mock indicator"):
        ZeroMockVerifier.verify_record(mock_content_record)


def test_verify_dataset_file_pass(tmp_path):
    dataset_path = os.path.join(tmp_path, "valid_dpo.jsonl")
    rec1 = {
        "prompt": "Fix Rust compiler error in src/lib.rs E0308 mismatched types",
        "chosen": "let x: u32 = 42;",
        "rejected": "let x: u32 = \"42\";",
        "metadata": {
            "trace_file": "src/lib.rs",
            "exit_code": 101,
            "timestamp": "2026-08-28T20:15:00Z",
            "duration_ms": 520,
        },
    }

    with open(dataset_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec1) + "\n")

    res = ZeroMockVerifier.verify_dataset_file(dataset_path)
    assert res["status"] == "PASS_ZERO_MOCK_VERIFIED"
    assert res["total_records"] == 1
    assert res["verified_records"] == 1


def test_verify_dataset_file_fail(tmp_path):
    dataset_path = os.path.join(tmp_path, "invalid_dpo.jsonl")
    bad_rec = {
        "prompt": "Fix bug",
        "chosen": "code",
        "rejected": "bad",
        "synthetic": True,
        "metadata": {
            "trace_file": "trace.log",
            "exit_code": 1,
            "timestamp": "2026-08-28T20:15:00Z",
            "duration_ms": 10,
        },
    }

    with open(dataset_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(bad_rec) + "\n")

    with pytest.raises(RuleZeroError):
        ZeroMockVerifier.verify_dataset_file(dataset_path)
