#!/usr/bin/env python3
"""
Unit tests for NPU Model Fleet Dispatcher.
"""

import sys
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "02_ai_models_and_inference/npu_fleet"))

from npu_model_fleet_dispatcher import NPUModelFleetDispatcher, NPU_FLEET_CATALOG

def test_npu_mesh_matrix():
    dispatcher = NPUModelFleetDispatcher()
    matrix = dispatcher.get_mesh_npu_matrix()
    assert matrix["total_pooled_tops"] == 100.0
    assert len(matrix["silicon_layers"]) == 5
    assert "L1_Mac_Node" in matrix["silicon_layers"]
    assert "L6_Pixel_10_Pro_XL" in matrix["silicon_layers"]
    assert matrix["silicon_layers"]["L1_Mac_Node"]["tops"] == 38.0
    assert matrix["silicon_layers"]["L6_Pixel_10_Pro_XL"]["tops"] == 14.0

def test_catalog_completeness():
    assert len(NPU_FLEET_CATALOG) >= 9
    expected_models = [
        "nanodraft_10m",
        "grammar_guard_5m",
        "silero_vad_v5",
        "moonshine_tiny_asr",
        "nanoowl_ui_grounder",
        "ecgnet_1d_dsp",
        "edge_embedder_15m",
        "genetic_router_gate",
        "anomaly_watch_network"
    ]
    for m in expected_models:
        assert m in NPU_FLEET_CATALOG

def test_speculative_drafter_dispatch():
    dispatcher = NPUModelFleetDispatcher()
    res = dispatcher.dispatch("nanodraft_10m", {"k": 6})
    assert res["zero_gpu_load_verified"] is True
    assert res["zero_host_vram_consumed"] is True
    assert len(res["result"]["draft_tokens"]) == 6
    assert res["result"]["effective_tok_s"] > 1000.0

def test_grammar_guard_dispatch():
    dispatcher = NPUModelFleetDispatcher()
    res = dispatcher.dispatch("grammar_guard_5m", {"tokens": ["def", "valid():"]})
    assert res["result"]["grammar_conformant"] is True
    assert res["measured_latency_ms"] < 2.0

def test_vad_and_audio_ducking():
    dispatcher = NPUModelFleetDispatcher()
    res = dispatcher.dispatch("silero_vad_v5", {"energy": 0.85})
    assert res["result"]["speech_detected"] is True
    assert res["result"]["audio_ducking_action"] == "DUCK_MUSIC_LEVEL_2"

def test_screen_lens_ui_grounding():
    dispatcher = NPUModelFleetDispatcher()
    res = dispatcher.dispatch("nanoowl_ui_grounder", {"frame": "base64_data"})
    assert len(res["result"]["detected_elements"]) >= 2
    assert res["result"]["fps"] >= 60.0
    assert res["hardware"] == "Google Tensor G5 Edge TPU"

def test_biometrics_512hz_ecg_dsp():
    dispatcher = NPUModelFleetDispatcher()
    res = dispatcher.dispatch("ecgnet_1d_dsp", {"sample_window": [0.1, 0.5, 1.2]})
    assert res["result"]["qrs_peak_detected"] is True
    assert res["hardware"] == "Apple Neural Engine (ANE) / Zen 3 AVX2"
    assert res["measured_latency_ms"] < 1.0

def test_semantic_cache_embedder():
    dispatcher = NPUModelFleetDispatcher()
    res = dispatcher.dispatch("edge_embedder_15m", {"text": "How do I start the mesh?"})
    assert res["result"]["embedding_dim"] == 384
    assert res["measured_latency_ms"] < 2.0

if __name__ == "__main__":
    print("Running NPU Model Fleet Unit Tests...")
    test_npu_mesh_matrix()
    test_catalog_completeness()
    test_speculative_drafter_dispatch()
    test_grammar_guard_dispatch()
    test_vad_and_audio_ducking()
    test_screen_lens_ui_grounding()
    test_biometrics_512hz_ecg_dsp()
    test_semantic_cache_embedder()
    print("✅ All 8 NPU Fleet Unit Tests Passed Successfully!")
