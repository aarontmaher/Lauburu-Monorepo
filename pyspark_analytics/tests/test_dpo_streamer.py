"""
Tests for Organic DPO Streaming from real compiler/test traces into lora_datasets.
"""

import json
import os
import pytest
from pyspark_analytics.dpo_streamer import OrganicDPOStreamer
from pyspark_analytics.zero_mock import RuleZeroError

try:
    from pyspark.sql import SparkSession
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False


@pytest.fixture(scope="module")
def spark_session():
    if not PYSPARK_AVAILABLE:
        pytest.skip("PySpark is not available in this environment")
    spark = SparkSession.builder \
        .appName("DPOStreamerTest") \
        .master("local[1]") \
        .config("spark.ui.enabled", "false") \
        .getOrCreate()
    yield spark
    spark.stop()


def test_dpo_streamer_parse_trace():
    trace_input = {
        "prompt": "Fix pytest error in core/chat-app/src/server/routes/internal.ts: missing auth token handler",
        "chosen": "if (!req.headers.authorization) return res.status(401).json({ error: 'Unauthorized' });",
        "rejected": "// Missing auth check",
        "metadata": {
            "trace_file": "core/chat-app/src/server/routes/internal.ts",
            "exit_code": 1,
            "timestamp": "2026-08-28T20:20:00Z",
            "duration_ms": 150,
            "compiler_tool": "tsc",
        },
    }

    dpo_pair = OrganicDPOStreamer.parse_trace_to_dpo_pair(trace_input)
    assert dpo_pair["prompt"].startswith("Fix pytest error")
    assert "Unauthorized" in dpo_pair["chosen"]
    assert dpo_pair["metadata"]["trace_file"] == "core/chat-app/src/server/routes/internal.ts"


def test_dpo_streamer_python_io(tmp_path):
    output_path = os.path.join(tmp_path, "lora_datasets", "test_dpo.jsonl")
    streamer = OrganicDPOStreamer(output_file=output_path)

    raw_traces = [
        {
            "prompt": "Fix Clang ASan heap-use-after-free error in native_bridge.cpp",
            "chosen": "auto ptr = std::make_unique<Buffer>(); ptr->process();",
            "rejected": "Buffer* ptr = new Buffer(); delete ptr; ptr->process();",
            "metadata": {
                "trace_file": "src/native_bridge.cpp",
                "exit_code": 1,
                "timestamp": "2026-08-28T20:21:00Z",
                "duration_ms": 820,
                "compiler_tool": "clang++ -fsanitize=address",
            },
        }
    ]

    result = streamer.stream_traces_to_lora_datasets(raw_traces)
    assert result["status"] == "STREAMING_COMPLETE"
    assert result["records_streamed"] == 1
    assert os.path.exists(output_path)

    # Read back and verify
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["metadata"]["compiler_tool"] == "clang++ -fsanitize=address"


def test_dpo_streamer_pyspark_integration(spark_session, tmp_path):
    output_path = os.path.join(tmp_path, "lora_datasets", "pyspark_dpo.jsonl")
    streamer = OrganicDPOStreamer(output_file=output_path, spark_session=spark_session)

    raw_traces = [
        {
            "prompt": "Fix eBPF XDP ring buffer overflow in network_filter.c",
            "chosen": "bpf_ringbuf_output(&rb, &event, sizeof(event), 0);",
            "rejected": "bpf_perf_event_output(ctx, &map, BPF_F_CURRENT_CPU, &event, sizeof(event));",
            "metadata": {
                "trace_file": "kernel/ebpf/network_filter.c",
                "exit_code": 0,
                "timestamp": "2026-08-28T20:22:00Z",
                "duration_ms": 1100,
                "compiler_tool": "clang -target bpf",
            },
        }
    ]

    result = streamer.stream_traces_to_lora_datasets(raw_traces)
    assert result["status"] == "STREAMING_COMPLETE"
    assert result["records_streamed"] == 1
    assert os.path.exists(output_path)
