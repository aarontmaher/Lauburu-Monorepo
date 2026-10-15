"""
r3_routing_replay.py - Rollout Routing Replay (R3) for Sparse MoE Architectures.

Implements the R3 mechanism from the T1 paper (arXiv:2609.11042):
Prevents MoE routing divergence between rollout inference kernels (vLLM/SGLang fused Top-K)
and training forward passes (PyTorch/Megatron). During training, the active expert indices
are fixed to the replayed rollout decisions, but gating weights remain fully differentiable
by normalizing softmax strictly across the active expert subset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class LayerRoutingRecord:
    layer_index: int
    # Map token sequence index -> list of selected expert indices (length K)
    token_expert_map: Dict[int, List[int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_index": self.layer_index,
            "token_expert_map": {str(k): v for k, v in self.token_expert_map.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayerRoutingRecord:
        raw_map = data.get("token_expert_map", {})
        return cls(
            layer_index=int(data.get("layer_index", 0)),
            token_expert_map={int(k): v for k, v in raw_map.items()},
        )


@dataclass
class R3RoutingCache:
    num_layers: int
    num_experts: int
    top_k: int
    layers: Dict[int, LayerRoutingRecord] = field(default_factory=dict)

    def record_routing(
        self,
        layer_idx: int,
        token_indices: Sequence[int],
        selected_experts: Union[List[List[int]], Any],
    ) -> None:
        """
        Records the top-K expert selections for tokens at a given layer.
        """
        if layer_idx not in self.layers:
            self.layers[layer_idx] = LayerRoutingRecord(layer_index=layer_idx)

        record = self.layers[layer_idx]
        for t_idx, exp_list in zip(token_indices, selected_experts):
            if hasattr(exp_list, "tolist"):
                exp_list = exp_list.tolist()
            record.token_expert_map[int(t_idx)] = list(exp_list)

    def get_routing(self, layer_idx: int, token_idx: int) -> Optional[List[int]]:
        record = self.layers.get(layer_idx)
        if record:
            return record.token_expert_map.get(token_idx)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_layers": self.num_layers,
            "num_experts": self.num_experts,
            "top_k": self.top_k,
            "layers": [rec.to_dict() for rec in self.layers.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> R3RoutingCache:
        cache = cls(
            num_layers=int(data.get("num_layers", 0)),
            num_experts=int(data.get("num_experts", 0)),
            top_k=int(data.get("top_k", 0)),
        )
        for l_data in data.get("layers", []):
            rec = LayerRoutingRecord.from_dict(l_data)
            cache.layers[rec.layer_index] = rec
        return cache


if TORCH_AVAILABLE:
    class R3MoERouter(nn.Module):
        """
        Sparse MoE Router module supporting standard Top-K routing during rollout
        and R3 (Rollout Routing Replay) during training forward passes.
        """

        def __init__(
            self,
            hidden_dim: int,
            num_experts: int = 256,
            top_k: int = 8,
            layer_index: int = 0,
        ):
            super().__init__()
            self.hidden_dim = hidden_dim
            self.num_experts = num_experts
            self.top_k = top_k
            self.layer_index = layer_index
            self.gate = nn.Linear(hidden_dim, num_experts, bias=False)

        def forward(
            self,
            hidden_states: torch.Tensor,
            replay_cache: Optional[R3RoutingCache] = None,
            token_offset: int = 0,
            loss_mask: Optional[torch.Tensor] = None,
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Args:
                hidden_states: (seq_len, hidden_dim) or (batch, seq_len, hidden_dim)
                replay_cache: Optional cached expert indices from rollout
                token_offset: absolute token offset for indexing into replay_cache
                loss_mask: (seq_len,) 1 for action tokens, 0 for prompt/observation

            Returns:
                weights: (seq_len, top_k) normalized gating weights
                expert_indices: (seq_len, top_k) discrete expert IDs
            """
            orig_shape = hidden_states.shape
            if hidden_states.dim() == 3:
                b, s, d = orig_shape
                hidden_states = hidden_states.view(-1, d)
            else:
                s, d = orig_shape
                b = 1

            # Compute live router logits s(x) \in R^(N x num_experts)
            router_logits = self.gate(hidden_states)

            # Check if we are in R3 replay mode
            if replay_cache is not None and self.layer_index in replay_cache.layers:
                rec = replay_cache.layers[self.layer_index]
                device = hidden_states.device
                indices_list: List[List[int]] = []
                use_fallback = False

                for local_i in range(hidden_states.size(0)):
                    abs_idx = token_offset + local_i
                    cached_exp = rec.token_expert_map.get(abs_idx)
                    if cached_exp is not None and len(cached_exp) == self.top_k:
                        indices_list.append(cached_exp)
                    else:
                        # Fallback to local topk if token is outside action mask or unrecorded
                        _, fallback_idx = torch.topk(router_logits[local_i], self.top_k, dim=-1)
                        indices_list.append(fallback_idx.tolist())

                expert_indices = torch.tensor(indices_list, dtype=torch.long, device=device)

                # Gather live router logits corresponding to the replayed expert indices
                # Shape: (N, top_k)
                selected_logits = torch.gather(router_logits, dim=-1, index=expert_indices)

                # Softmax strictly across the top-K replayed candidates
                # \tilde{g}_{j,k} = exp(s_{j, I_{j,k}}) / \sum exp(s_{j, I_{j,k'}})
                weights = F.softmax(selected_logits, dim=-1)

            else:
                # Standard Rollout Top-K Mode
                topk_weights, expert_indices = torch.topk(router_logits, self.top_k, dim=-1)
                weights = F.softmax(topk_weights, dim=-1)

            return weights, expert_indices

    class R3MoELayer(nn.Module):
        """
        Sparse MoE Layer consisting of R3MoERouter and expert MLPs.
        Demonstrates end-to-end forward/backward with active subnetwork isolation.
        """

        def __init__(
            self,
            hidden_dim: int,
            num_experts: int = 256,
            top_k: int = 8,
            layer_index: int = 0,
        ):
            super().__init__()
            self.hidden_dim = hidden_dim
            self.num_experts = num_experts
            self.top_k = top_k
            self.layer_index = layer_index
            self.router = R3MoERouter(hidden_dim, num_experts, top_k, layer_index)
            # Lightweight mock-free linear expert projections for testability
            self.experts = nn.ModuleList([
                nn.Linear(hidden_dim, hidden_dim, bias=False) for _ in range(num_experts)
            ])

        def forward(
            self,
            x: torch.Tensor,
            replay_cache: Optional[R3RoutingCache] = None,
            token_offset: int = 0,
        ) -> torch.Tensor:
            seq_len, dim = x.shape
            weights, expert_indices = self.router(
                x, replay_cache=replay_cache, token_offset=token_offset
            )

            # Output accumulation: y = \sum_{k=1}^K g_k * Expert_k(x)
            out = torch.zeros_like(x)
            for k in range(self.top_k):
                k_indices = expert_indices[:, k]
                k_weights = weights[:, k].unsqueeze(-1)
                for exp_id in range(self.num_experts):
                    mask = (k_indices == exp_id)
                    if mask.any():
                        selected_x = x[mask]
                        expert_out = self.experts[exp_id](selected_x)
                        out[mask] += k_weights[mask] * expert_out

            return out
else:
    # Minimal Pure Python stub if PyTorch is not loaded
    class R3MoERouter:
        pass

    class R3MoELayer:
        pass
