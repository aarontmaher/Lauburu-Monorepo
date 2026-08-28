"""
Inference Bridges Package for Canonical Port TUI
Version: 1.0.0-CANONICAL

Exports polymorphic async inference bridges for:
- BaseInferenceBridge (ABC)
- LlamaRpcInferenceBridge (llama.cpp RPC & HTTP)
- ExoInferenceBridge (Exo P2P Ring)
- AccelerateInferenceBridge (HuggingFace Accelerate DDP / MPS)
- PetalsInferenceBridge (Petals DHT Swarm)
"""

from .base_bridge import BaseInferenceBridge
from .llama_bridge import LlamaRpcInferenceBridge
from .exo_bridge import ExoInferenceBridge
from .accelerate_bridge import AccelerateInferenceBridge
from .petals_bridge import PetalsInferenceBridge
from .gemini_bridge import GeminiBridge
from .cloudflare_bridge import CloudflareBridge
from .julien_bridge import JulienBridge

__all__ = [
    "BaseInferenceBridge",
    "LlamaRpcInferenceBridge",
    "ExoInferenceBridge",
    "AccelerateInferenceBridge",
    "PetalsInferenceBridge",
    "GeminiBridge",
    "CloudflareBridge",
    "JulienBridge",
]
