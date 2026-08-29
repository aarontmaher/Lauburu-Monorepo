"""
Qwen Math Trend Optimizer Configuration.
========================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/core/config.py
"""

from dataclasses import dataclass
from pathlib import Path

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

@dataclass
class MathOptimizerConfig:
    host_physical_ram_gb: float = 24.0
    governor_ceiling_pct: float = 0.90
    min_headroom_safety_gb: float = 2.50
    lora_dataset_path: Path = WORKSPACE_ROOT / "04_data_and_memory/lora_datasets/qwen_math_optimization_trends.jsonl"
    transport_stats_path: Path = WORKSPACE_ROOT / "02_ai_models_and_inference/benchmarks/live_transport_stats.json"
