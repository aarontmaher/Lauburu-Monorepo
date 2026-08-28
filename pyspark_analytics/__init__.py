"""
pyspark_analytics - PySpark time-series analytics, organic DPO streaming,
Rule #0 zero-mock verification, and local GGUF Q4_K_M weight export automation.
"""

from .dfa_alpha1 import compute_dfa_alpha1, aggregate_dfa_metrics
from .zero_mock import ZeroMockVerifier, RuleZeroError
from .dpo_streamer import OrganicDPOStreamer
from .gguf_exporter import GGUFQ4KMExporter

__all__ = [
    "compute_dfa_alpha1",
    "aggregate_dfa_metrics",
    "ZeroMockVerifier",
    "RuleZeroError",
    "OrganicDPOStreamer",
    "GGUFQ4KMExporter",
]
