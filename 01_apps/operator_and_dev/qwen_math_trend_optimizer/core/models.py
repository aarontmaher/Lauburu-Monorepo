"""
Qwen Math Trend Optimizer Data Models.
======================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/core/models.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class LatencyProof:
    transport_name: str
    rtt_ms: float
    inverse_variance_weight: float
    is_optimal_primary: bool

@dataclass
class RamHeadroomProof:
    host_physical_ram_gb: float
    governor_ceiling_gb: float
    base_model_vram_gb: float
    kv_cache_vram_gb: float
    activation_vram_gb: float
    total_active_vram_gb: float
    ram_headroom_gb: float
    is_safe: bool
    status: str
    equation: str

@dataclass
class LossTrajectoryForecast:
    step_samples: Dict[str, float]
    optimal_learning_rate: float
    formula: str

@dataclass
class CardiacCoherenceMetric:
    hr_bpm: float
    rmssd_ms: float
    coherence_ratio: float
    rsa_synchrony: float
    is_zone2_optimal: bool
