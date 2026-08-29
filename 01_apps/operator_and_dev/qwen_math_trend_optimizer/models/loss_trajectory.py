"""
Loss Trajectory Forecasting & Optimal Learning Rate Scaling.
============================================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/models/loss_trajectory.py
"""

import math
from typing import Dict, List, Optional
from ..core.models import LossTrajectoryForecast

def compute_loss_trajectory(steps: Optional[List[int]] = None) -> LossTrajectoryForecast:
    """Calculates closed-form loss trajectory using L(t) = 0.42 + 1.76 * exp(-0.0008 * t)."""
    t_samples = steps or [100, 500, 1000, 2500, 5000]
    samples = {
        f"step_{t}": round(0.42 + 1.76 * math.exp(-0.0008 * t), 4)
        for t in t_samples
    }
    lr = compute_optimal_learning_rate(batch_size=2, grad_accum=1)
    return LossTrajectoryForecast(
        step_samples=samples,
        optimal_learning_rate=lr,
        formula="L(t) = 0.42 + 1.76 * exp(-0.0008 * t)"
    )

def compute_optimal_learning_rate(batch_size: int = 2, grad_accum: int = 1) -> float:
    """Calculates optimal learning rate scaling: eta = 1e-4 * sqrt(batch * accum / 4)."""
    effective_batch = batch_size * grad_accum
    return round(1e-4 * math.sqrt(effective_batch / 4.0), 6)
