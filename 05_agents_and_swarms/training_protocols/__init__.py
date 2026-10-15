"""
High-ROI AI Training Protocols Package
Lauburu Sovereign Mesh Ecosystem
"""

try:
    from .high_roi_protocol_registry import (
        TrainingProtocolID,
        ProtocolStatus,
        ProtocolDefinition,
        HighROIProtocolRegistry,
        GLOBAL_PROTOCOL_REGISTRY
    )
    from .grpo_rule_based_trainer import GRPORuleBasedRewardEngine, GRPOGroupSample
    from .dpo_debate_distiller import DPODebateDistiller, DPOPreferencePair
    from .frontier_benchmarking_arena import FrontierBenchmarkingArena, BenchmarkEvaluationResult
except (ImportError, ValueError):
    import sys
    from pathlib import Path
    pkg_dir = str(Path(__file__).parent)
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)
    from high_roi_protocol_registry import (
        TrainingProtocolID,
        ProtocolStatus,
        ProtocolDefinition,
        HighROIProtocolRegistry,
        GLOBAL_PROTOCOL_REGISTRY
    )
    from grpo_rule_based_trainer import GRPORuleBasedRewardEngine, GRPOGroupSample
    from dpo_debate_distiller import DPODebateDistiller, DPOPreferencePair
    from frontier_benchmarking_arena import FrontierBenchmarkingArena, BenchmarkEvaluationResult

__all__ = [
    "TrainingProtocolID",
    "ProtocolStatus",
    "ProtocolDefinition",
    "HighROIProtocolRegistry",
    "GLOBAL_PROTOCOL_REGISTRY",
    "GRPORuleBasedRewardEngine",
    "GRPOGroupSample",
    "DPODebateDistiller",
    "DPOPreferencePair",
    "FrontierBenchmarkingArena",
    "BenchmarkEvaluationResult",
]
