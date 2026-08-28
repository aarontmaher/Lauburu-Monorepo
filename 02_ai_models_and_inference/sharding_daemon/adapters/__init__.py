#!/usr/bin/env python3
"""
02_ai_models_and_inference/sharding_daemon/adapters/__init__.py
==============================================================
Modular Multi-Backend AI Sharding Adapter Suite.
------------------------------------------------
Exports unified backend execution engines for Petals DHT, llama.cpp RPC,
Exo P2P ring pipelines, and HuggingFace Accelerate model parallelism.
"""

from typing import Dict, Type, Optional, Any, List

from .base import (
    BackendAdapter,
    TensorPayload,
    TensorDtype,
    CompressionMode,
    ShardSpec,
    AdapterStatus,
    NF4_QUANT_TABLE,
)
from .petals_adapter import PetalsAdapter, TransformerBlockWeights, DHTPeerBlockRoute
from .llamacpp_adapter import LlamaCppAdapter, GGUFQuantType, GGMLRpcCommand, RPCWorkerNode
from .exo_adapter import ExoAdapter, RingNode, RingStageState, ZenohMessageFrame
from .accelerate_adapter import AccelerateAdapter, LoRAConfig, LoRALayerWeights

# Canonical Backend Adapter Registry
ADAPTER_REGISTRY: Dict[str, Type[BackendAdapter]] = {
    "petals_dht": PetalsAdapter,
    "petals": PetalsAdapter,
    "llamacpp_rpc": LlamaCppAdapter,
    "llamacpp": LlamaCppAdapter,
    "llama_rpc": LlamaCppAdapter,
    "exo_p2p": ExoAdapter,
    "exo": ExoAdapter,
    "accelerate_lora": AccelerateAdapter,
    "accelerate": AccelerateAdapter,
}


def create_adapter(backend_type: str, node_id: str = "mac_host", config: Optional[Dict[str, Any]] = None) -> BackendAdapter:
    """
    Factory method to instantiate a backend sharding adapter by name.
    
    Args:
        backend_type: One of 'petals_dht', 'llamacpp_rpc', 'exo_p2p', 'accelerate_lora' (or aliases).
        node_id: Cluster node identifier (e.g. 'mac_host', 'macbook_pro', 'linux_node', 'pixel_10').
        config: Optional configuration dictionary.

    Returns:
        Instantiated BackendAdapter subclass.
    """
    norm_key = backend_type.lower().strip().replace("-", "_")
    adapter_cls = ADAPTER_REGISTRY.get(norm_key)
    if not adapter_cls:
        raise ValueError(
            f"Unknown backend_type '{backend_type}'. Available backends: {list(ADAPTER_REGISTRY.keys())}"
        )
    return adapter_cls(node_id=node_id, config=config)


def list_available_backends() -> List[str]:
    """Returns canonical list of supported backend engine keys."""
    return sorted(list(set(ADAPTER_REGISTRY.keys())))


__all__ = [
    # Base
    "BackendAdapter",
    "TensorPayload",
    "TensorDtype",
    "CompressionMode",
    "ShardSpec",
    "AdapterStatus",
    "NF4_QUANT_TABLE",
    # Adapters
    "PetalsAdapter",
    "TransformerBlockWeights",
    "DHTPeerBlockRoute",
    "LlamaCppAdapter",
    "GGUFQuantType",
    "GGMLRpcCommand",
    "RPCWorkerNode",
    "ExoAdapter",
    "RingNode",
    "RingStageState",
    "ZenohMessageFrame",
    "AccelerateAdapter",
    "LoRAConfig",
    "LoRALayerWeights",
    # Factory & Registry
    "ADAPTER_REGISTRY",
    "create_adapter",
    "list_available_backends",
]
