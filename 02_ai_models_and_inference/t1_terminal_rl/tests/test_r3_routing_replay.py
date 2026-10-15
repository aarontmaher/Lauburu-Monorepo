"""
test_r3_routing_replay.py - Test Suite for R3 (Rollout Routing Replay).

Verifies:
1. Routing cache recording, lookup, and serialization.
2. 100.0% precision match between replayed expert indices and rollout decisions.
3. Active subnetwork gating normalization across replayed top-K candidates.
4. Backpropagation gradient flow into router weights during replay mode.
"""

import json
import pytest
from pathlib import Path
import sys

PKG_DIR = Path(__file__).resolve().parents[2]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from t1_terminal_rl.r3_routing_replay import (
    LayerRoutingRecord,
    R3RoutingCache,
    TORCH_AVAILABLE,
)

if TORCH_AVAILABLE:
    import torch
    from t1_terminal_rl.r3_routing_replay import R3MoERouter, R3MoELayer


def test_r3_cache_recording_and_serialization():
    cache = R3RoutingCache(num_layers=4, num_experts=64, top_k=4)

    # Record routing for layer 0: tokens 10, 11, 12
    cache.record_routing(
        layer_idx=0,
        token_indices=[10, 11, 12],
        selected_experts=[[1, 5, 12, 40], [2, 6, 15, 33], [0, 8, 22, 59]],
    )

    # Verify retrieval
    exp10 = cache.get_routing(layer_idx=0, token_idx=10)
    assert exp10 == [1, 5, 12, 40]
    exp11 = cache.get_routing(layer_idx=0, token_idx=11)
    assert exp11 == [2, 6, 15, 33]

    # Serialization roundtrip
    cache_dict = cache.to_dict()
    json_str = json.dumps(cache_dict)
    loaded = R3RoutingCache.from_dict(json.loads(json_str))

    assert loaded.num_layers == 4
    assert loaded.num_experts == 64
    assert loaded.top_k == 4
    assert loaded.get_routing(0, 10) == [1, 5, 12, 40]


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch is required for R3 autograd tests")
def test_r3_moe_router_replay_fidelity_and_gradient():
    torch.manual_seed(42)
    hidden_dim = 32
    num_experts = 16
    top_k = 4
    seq_len = 6

    router = R3MoERouter(hidden_dim=hidden_dim, num_experts=num_experts, top_k=top_k, layer_index=0)
    hidden_states = torch.randn(seq_len, hidden_dim, requires_grad=True)

    # 1. Rollout Step: generate rollout routing without cache
    weights_rollout, indices_rollout = router(hidden_states)
    assert weights_rollout.shape == (seq_len, top_k)
    assert indices_rollout.shape == (seq_len, top_k)

    # Record indices in R3RoutingCache
    cache = R3RoutingCache(num_layers=1, num_experts=num_experts, top_k=top_k)
    cache.record_routing(
        layer_idx=0,
        token_indices=list(range(seq_len)),
        selected_experts=indices_rollout.tolist(),
    )

    # Perturb router weights slightly to simulate training parameter drift
    with torch.no_grad():
        router.gate.weight.add_(torch.randn_like(router.gate.weight) * 0.05)

    # 2. Training Step with R3 Replay:
    weights_replay, indices_replay = router(
        hidden_states,
        replay_cache=cache,
        token_offset=0,
    )

    # Assert 100.0% index match with rollout cache despite weight drift
    assert torch.equal(indices_replay, indices_rollout), "Replay indices diverged from cached rollout indices!"

    # Assert gating weights sum to 1.0 across active top-k
    weight_sums = weights_replay.sum(dim=-1)
    assert torch.allclose(weight_sums, torch.ones_like(weight_sums), atol=1e-5)

    # 3. Verify Gradient Flow: Backward pass through replayed active weights
    dummy_loss = (weights_replay * 2.0).sum()
    dummy_loss.backward()

    # Verify that router gate received non-zero gradients
    assert router.gate.weight.grad is not None
    grad_norm = router.gate.weight.grad.norm().item()
    assert grad_norm > 0.0, f"Router gate grad norm must be non-zero, got {grad_norm}"


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch is required for R3 layer tests")
def test_r3_moe_layer_end_to_end():
    torch.manual_seed(123)
    dim = 16
    num_experts = 8
    top_k = 2
    layer = R3MoELayer(hidden_dim=dim, num_experts=num_experts, top_k=top_k, layer_index=0)

    x = torch.randn(4, dim)
    cache = R3RoutingCache(num_layers=1, num_experts=num_experts, top_k=top_k)
    cache.record_routing(0, [0, 1, 2, 3], [[0, 1], [2, 3], [4, 5], [6, 7]])

    out = layer(x, replay_cache=cache)
    assert out.shape == (4, dim)
    assert not torch.isnan(out).any()
