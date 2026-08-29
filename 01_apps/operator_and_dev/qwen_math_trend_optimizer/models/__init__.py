"""
Qwen Math Models Package.
"""

from .latency_proofs import compute_inverse_variance_weights
from .ram_headroom import compute_ram_safety_headroom
from .loss_trajectory import compute_loss_trajectory, compute_optimal_learning_rate
from .cardiac_coherence import compute_cardiac_coherence

__all__ = [
    "compute_inverse_variance_weights",
    "compute_ram_safety_headroom",
    "compute_loss_trajectory",
    "compute_optimal_learning_rate",
    "compute_cardiac_coherence",
]
