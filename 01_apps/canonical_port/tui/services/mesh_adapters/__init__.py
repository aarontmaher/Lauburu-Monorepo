"""
Canonical Port Distributed AI Mesh CLI Adapters Package
Exposes unified CLI adapters and typed models for Tailscale, Speedify, Exo, Accelerate, and llama.cpp.
"""

from .tailscale_adapter import (
    TailscaleAdapter,
    TailscalePeerInfo,
    TailscalePingResult,
    TailscaleStatusResult
)
from .speedify_adapter import (
    SpeedifyAdapter,
    SpeedifyAdapterInfo,
    SpeedifyStats,
    SpeedifyStatusResult
)
from .exo_adapter import (
    ExoAdapter,
    ExoPeerInfo,
    ExoShardMapping,
    ExoBenchmarkResult,
    ExoTopologyResult
)
from .accelerate_adapter import (
    AccelerateAdapter,
    AccelerateEnvInfo,
    AccelerateJobInfo,
    AccelerateStatusResult
)
from .llama_rpc_adapter import (
    LlamaRpcAdapter,
    LlamaRpcTarget,
    LlamaServerHealth,
    LlamaRpcClusterStatus
)

__all__ = [
    # Tailscale
    "TailscaleAdapter",
    "TailscalePeerInfo",
    "TailscalePingResult",
    "TailscaleStatusResult",
    # Speedify
    "SpeedifyAdapter",
    "SpeedifyAdapterInfo",
    "SpeedifyStats",
    "SpeedifyStatusResult",
    # Exo
    "ExoAdapter",
    "ExoPeerInfo",
    "ExoShardMapping",
    "ExoBenchmarkResult",
    "ExoTopologyResult",
    # Accelerate
    "AccelerateAdapter",
    "AccelerateEnvInfo",
    "AccelerateJobInfo",
    "AccelerateStatusResult",
    # llama.cpp RPC
    "LlamaRpcAdapter",
    "LlamaRpcTarget",
    "LlamaServerHealth",
    "LlamaRpcClusterStatus",
]
