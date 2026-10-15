#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Apple Neural Engine (ANE) & Unified RAM Coprocessor Engine
========================================================================
Subsystem: 01_apps/canonical_port/tests/unit/test_npu_unified_engine.py
Verifies:
1. Zero-copy mmap buffer initialization and size.
2. ANE 16-Core 38 TOPS telemetry reporting.
3. Unified memory profile and Rule 3 sanctuary calculations.
4. Sub-millisecond INT8 systolic biometric anomaly inference.
5. Zero-copy prompt intent classification and speculative draft proposal.
6. Central router endpoints (/api/v1/npu/*).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.npu_unified_engine import NpuUnifiedEngine, NpuInferenceOutput
from backend.spec_modules.spec_02_ai_inference import Spec02AiInferenceModule


@pytest.fixture
def engine():
    return NpuUnifiedEngine.get_instance()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_npu_unified_engine_telemetry(engine):
    """Verifies ANE telemetry parameters and 38.0 TOPS hardware specs."""
    telem = engine.get_telemetry()
    assert telem["status"] == "ONLINE"
    assert telem["npu_type"] == "Apple Neural Engine (ANE)"
    assert telem["ane_cores"] == 16
    assert telem["peak_tops"] == 38.0
    assert telem["zero_copy_ram_allocation_mb"] == 0.0
    assert telem["unified_memory_bandwidth_gbs"] == 273.0
    assert telem["zero_copy_buffer_active"] is True
    assert telem["zero_copy_buffer_bytes"] > 0


def test_npu_unified_ram_profile(engine):
    """Verifies Apple Silicon Unified Memory Architecture specs and Rule 3 targets."""
    profile = engine.get_unified_ram_profile()
    assert "Apple Silicon Unified Memory" in profile["architecture"]
    assert profile["total_ram_gb"] > 0
    assert profile["available_ram_gb"] > 0
    assert profile["peak_bandwidth_gbs"] == 273.0
    assert profile["memory_bus_width_bit"] == 192
    assert "Direct Pointer Mapping" in profile["zero_copy_dispatch"]["cpu_to_ane"]
    assert profile["rule_3_sanctuary"]["headroom_target_gb"] == 9.6


def test_npu_biometric_anomaly_inference(engine):
    """Verifies systolic INT8 convolution on 512Hz ECG array in < 2ms."""
    signal = [10.0, 20.0, 45.0, 150.0, 380.0, 620.0, 350.0, 80.0, 15.0, 5.0] * 25
    out = engine.infer_biometric_anomaly(signal)
    assert isinstance(out, NpuInferenceOutput)
    assert out.task_type == "anomaly_detection"
    assert out.executed_on == "Apple Neural Engine (ANE) 16-Core"
    assert out.latency_us < 2000.0  # Under 2 milliseconds
    assert "bpm" in out.result
    assert "arrhythmia_risk" in out.result
    assert out.result["npu_ratio"] == 1.0


def test_npu_prompt_intent_classification(engine):
    """Verifies prompt intent routing with zero memory overhead."""
    out = engine.classify_prompt_intent("How much unified memory does the M4 Pro have?")
    assert out.task_type == "intent_classification"
    assert out.result["intent"] == "unified_ram"
    assert out.result["confidence"] >= 0.70
    assert out.latency_us < 1000.0  # Sub-millisecond


def test_npu_speculative_draft_generation(engine):
    """Verifies speculative token drafting proposal."""
    out = engine.generate_speculative_draft("Optimize NPU systolic inference", max_tokens=3)
    assert out.task_type == "speculative_draft"
    assert len(out.result["draft_tokens"]) == 3
    assert out.result["speedup_factor"] > 1.0


def test_spec_02_status_integration():
    """Verifies that Spec-02 module status now surfaces NPU and Unified RAM."""
    mod = Spec02AiInferenceModule()
    status = mod.get_status()
    metrics = status["metrics"]
    assert "npu_accelerator" in metrics
    assert metrics["npu_accelerator"]["type"] == "Apple Neural Engine (ANE)"
    assert metrics["npu_accelerator"]["peak_tops"] == 38.0
    assert "unified_ram_architecture" in metrics
    assert metrics["unified_ram_architecture"]["peak_bandwidth_gbs"] == 273.0


def test_router_npu_endpoints(client):
    """Verifies all new /api/v1/npu/* REST endpoints via TestClient."""
    # 1. Telemetry
    r_telem = client.get("/api/v1/npu/telemetry")
    assert r_telem.status_code == 200
    d_telem = r_telem.json()
    assert d_telem["npu_type"] == "Apple Neural Engine (ANE)"

    # 2. Unified RAM
    r_ram = client.get("/api/v1/npu/unified-ram")
    assert r_ram.status_code == 200
    d_ram = r_ram.json()
    assert d_ram["peak_bandwidth_gbs"] == 273.0

    # 3. Systolic Infer
    r_infer = client.post("/api/v1/npu/infer", json={"signal": [10.0, 50.0, 300.0, 50.0, 10.0]})
    assert r_infer.status_code == 200
    d_infer = r_infer.json()
    assert d_infer["executed_on"] == "Apple Neural Engine (ANE) 16-Core"
    assert "result" in d_infer

    # 4. Classify
    r_class = client.post("/api/v1/npu/classify", json={"prompt": "check Movesense 512Hz ECG"})
    assert r_class.status_code == 200
    d_class = r_class.json()
    assert d_class["result"]["intent"] == "biometrics"

    # 5. Speculative Draft
    r_draft = client.post("/api/v1/npu/speculative-draft", json={"prefix": "overnight training loop", "max_tokens": 4})
    assert r_draft.status_code == 200
    d_draft = r_draft.json()
    assert len(d_draft["result"]["draft_tokens"]) == 4

    # 6. Data Analysis
    r_data = client.post("/api/v1/npu/analyze-data", json={"values": [1.45, 1.42, 1.40, 1.38], "dataset_name": "test_loss"})
    assert r_data.status_code == 200
    d_data = r_data.json()
    assert d_data["executed_on"] == "Apple Neural Engine (ANE) 16-Core Systolic Unit"
    assert "slope" in d_data["result"]
    assert d_data["result"]["trend_direction"] == "CONVERGING"

    # 7. Neo Project App Graph
    r_graph = client.get("/api/v1/neo/graph")
    assert r_graph.status_code == 200
    d_graph = r_graph.json()
    assert "nodes" in d_graph
    assert "edges" in d_graph
    assert any(n["id"] == "npu_apple_ane" for n in d_graph["nodes"])
    assert any(n["id"] == "bt_pixel_ide" for n in d_graph["nodes"])

    # 8. Neo Monorepo Structuring & Organization
    r_struct = client.get("/api/v1/neo/structure")
    assert r_struct.status_code == 200
    d_struct = r_struct.json()
    assert d_struct["status"] == "ORGANIZED_HEALTHY"
    assert len(d_struct["domains"]) == 8

    # 9. Neo Sync Obsidian
    r_sync = client.post("/api/v1/neo/sync-obsidian")
    assert r_sync.status_code == 200
    d_sync = r_sync.json()
    assert d_sync["success"] is True

