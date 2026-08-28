"""Abliterated 70B Referee & Chaos Engine Package.

Provides:
- AbliteratedReferee (uncensored referee & match orchestrator)
- ScoringMatrix, ScoreBreakdown, calculate_composite_score, calculate_npu_bonus_hours
- ChaosInjector, ChaosEvent (3-tier chaos generator)
- calculate_refusal_ablation (directional refusal vector math)
"""

from .abliterated_referee import AbliteratedReferee, calculate_refusal_ablation
from .chaos_injector import ChaosEvent, ChaosInjector
from .scoring_matrix import (
    DEFAULT_SCORING_WEIGHTS,
    ScoreBreakdown,
    ScoringMatrix,
    calculate_composite_score,
    calculate_npu_bonus_hours,
)

__all__ = [
    "AbliteratedReferee",
    "calculate_refusal_ablation",
    "ScoringMatrix",
    "ScoreBreakdown",
    "DEFAULT_SCORING_WEIGHTS",
    "calculate_composite_score",
    "calculate_npu_bonus_hours",
    "ChaosInjector",
    "ChaosEvent",
]
