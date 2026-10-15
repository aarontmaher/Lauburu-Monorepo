#!/usr/bin/env python3
"""
Fast E2E Integration Test: NPU Fleet Dispatcher + Genetic MoE RAM Governor + Static Model Graphs.
"""

import sys
import time
import json
from pathlib import Path
import torch

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "02_ai_models_and_inference/npu_fleet"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms/genetic_moe"))

from npu_model_fleet_dispatcher import NPUModelFleetDispatcher
import genetic_moe_mesh_ram_governor as gov_mod
from genetic_moe_mesh_ram_governor import GeneticMoEMeshRAMGovernor

MODELS_DIR = REPO_ROOT / "02_ai_models_and_inference/model_vault_gguf/micro_models/npu"

# Fast-mock ping for instant test execution
gov_mod.probe_node_latency = lambda ip, timeout_ms=500: 5.0

def test_traced_model_forward_passes():
    manifest_path = MODELS_DIR / "npu_models_manifest.json"
    assert manifest_path.exists(), "Manifest must exist"
    manifest = json.loads(manifest_path.read_text())

    dummy_input = torch.randint(0, 1000, (1, 128), dtype=torch.long)

    # 1. NanoDraft
    m1 = torch.jit.load(manifest["nanodraft_10m"]["file"])
    m1.eval()
    t0 = time.time()
    out1 = m1(dummy_input)
    lat1 = (time.time() - t0) * 1000
    assert list(out1.shape) == [1, 128, 32000]
    print(f"✅ NanoDraft-10M forward pass verified: shape {list(out1.shape)} in {lat1:.2f}ms", flush=True)

    # 2. GrammarGuard
    m2 = torch.jit.load(manifest["grammar_guard_5m"]["file"])
    m2.eval()
    t0 = time.time()
    out2 = m2(dummy_input)
    lat2 = (time.time() - t0) * 1000
    assert list(out2.shape) == [1, 8]
    print(f"✅ GrammarGuard-5M forward pass verified: shape {list(out2.shape)} in {lat2:.2f}ms", flush=True)

    # 3. EdgeEmbedder
    m3 = torch.jit.load(manifest["edge_embedder_15m"]["file"])
    m3.eval()
    t0 = time.time()
    out3 = m3(dummy_input)
    lat3 = (time.time() - t0) * 1000
    assert list(out3.shape) == [1, 384]
    print(f"✅ EdgeEmbedder-15M forward pass verified: shape {list(out3.shape)} in {lat3:.2f}ms", flush=True)

def test_governor_npu_routing():
    gov = GeneticMoEMeshRAMGovernor()
    test_cases = [
        ("execute speculative_draft tokens on npu", "LAYER_0_NPU_REALTIME_SENTINEL"),
        ("silero vad speech detection voice_duck", "LAYER_0_NPU_REALTIME_SENTINEL"),
        ("screen lens ui_ground bounding_box coords", "LAYER_0_NPU_REALTIME_SENTINEL"),
        ("movesense ecg_dsp 512hz telemetry filter", "LAYER_0_NPU_REALTIME_SENTINEL"),
        ("query semantic_cache for quick answer", "LAYER_0_NPU_REALTIME_SENTINEL"),
    ]
    for prompt, expected_tier in test_cases:
        route = gov.route_task(prompt)
        assert route["tier"] == expected_tier, f"Expected {expected_tier}, got {route['tier']}"
        assert route["allocated_ram_gb"] == 0.0, "NPU must allocate 0.0 GB host RAM"
    print("✅ Genetic MoE RAM Governor NPU Routing verified across all 5 test cases!", flush=True)

if __name__ == "__main__":
    print("=" * 80, flush=True)
    print("🧪 RUNNING FAST E2E NPU FLEET & GOVERNOR INTEGRATION TESTS", flush=True)
    print("=" * 80, flush=True)
    test_traced_model_forward_passes()
    test_governor_npu_routing()
    print("=" * 80, flush=True)
    print("🏆 ALL E2E INTEGRATION TESTS PASSED (EXIT CODE 0)", flush=True)
    print("=" * 80, flush=True)
