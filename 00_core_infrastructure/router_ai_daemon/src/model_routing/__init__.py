"""
Autonomous HuggingFace GGUF Discovery & Hot-Swap Engine for smolagi Router AI Daemon.

Provides:
- HFAuth, HFModelDiscovery, DiscoveredModel for secure HF Hub discovery and sub-1B filtering
- SafeModelDownloader, DownloadResult for streaming downloads to tmpfs with SHA-256 verification
- HotSwapProxy, ModelSwapResult, hot_swap_model for zero-downtime atomic model transitions
"""

from src.model_routing.downloader import DownloadResult, SafeModelDownloader
from src.model_routing.hf_discovery import (
    DiscoveredModel,
    HFAuth,
    HFModelDiscovery,
    calculate_projected_ram_mb,
    extract_parameter_count,
    extract_quantization,
    validate_ram_budget,
)
from src.model_routing.hot_swap_proxy import (
    HotSwapProxy,
    ModelSwapResult,
    QueuedRequest,
    get_hot_swap_proxy,
    hot_swap_model,
)

__all__ = [
    "HFAuth",
    "HFModelDiscovery",
    "DiscoveredModel",
    "extract_quantization",
    "extract_parameter_count",
    "calculate_projected_ram_mb",
    "validate_ram_budget",
    "SafeModelDownloader",
    "DownloadResult",
    "HotSwapProxy",
    "ModelSwapResult",
    "QueuedRequest",
    "get_hot_swap_proxy",
    "hot_swap_model",
]
