import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from heterogeneous_speculative_orchestrator import (
    EdgeNPUDrafter,
    MetalGPUDrafter,
    HeterogeneousSpeculativeEngine
)


def test_edge_npu_drafter():
    npu = EdgeNPUDrafter()
    branch = npu.draft_branch("Context prompt", k=4)
    assert branch["source"] == "EDGE_NPU"
    assert len(branch["candidate_tokens"]) == 4
    assert branch["draft_latency_ms"] > 0


def test_metal_gpu_drafter():
    gpu = MetalGPUDrafter()
    branch = gpu.draft_branch("Context prompt", k=4)
    assert branch["source"] == "METAL_GPU"
    assert len(branch["candidate_tokens"]) == 4
    assert branch["draft_latency_ms"] > 0


def test_heterogeneous_speculative_engine_step():
    engine = HeterogeneousSpeculativeEngine(k_per_drafter=4)
    step = engine.run_heterogeneous_speculative_step("Test context")
    assert step["status"] == "TREE_VERIFIED"
    assert step["accepted_tokens_count"] >= 2
    assert step["effective_tps"] > 30.0


def test_unified_ai_generation():
    engine = HeterogeneousSpeculativeEngine(k_per_drafter=4)
    res = engine.generate("Explain unified AI", target_tokens=25)
    assert res["total_tokens_generated"] == 25
    assert len(res["cooperating_hardware"]) == 3
    assert res["speedup_vs_dense80b"] > 10.0
