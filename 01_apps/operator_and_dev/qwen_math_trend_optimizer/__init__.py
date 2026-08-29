"""
Qwen Math Telemetry Trend & Optimization Suite.
===============================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer
Version: 1.0.0-CANONICAL

Decoupled mathematical governor calculating closed-form proofs for:
1. Multi-transport latency weighting (TB4 DMA, Tailscale WireGuard, Wi-Fi 7).
2. RAM headroom governor equations under 21.6GB host ceiling.
3. Loss curve trajectory forecasting and optimal learning rate scaling.
4. Cardiac coherence & RSA spectral synchronization metrics.
5. 24/7 LoRA SFT/DPO fine-tuning dataset generation.

Subpackages:
- core: Configs, data models, metrics
- models: Closed-form equations (latency proofs, RAM headroom, loss forecasting, coherence)
- presentation: Autonomous optimizer engine, Textual TUI HUD, dataset logger
"""

from .core import (
    MathOptimizerConfig,
    LatencyProof,
    RamHeadroomProof,
    LossTrajectoryForecast,
    CardiacCoherenceMetric,
)
from .models import (
    compute_inverse_variance_weights,
    compute_ram_safety_headroom,
    compute_loss_trajectory,
    compute_optimal_learning_rate,
    compute_cardiac_coherence,
)
from .presentation import (
    LoraDatasetLogger,
    AutonomousMathTrendOptimizer,
    QwenMathOptimizerApp,
    run_optimizer,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "MathOptimizerConfig",
    "LatencyProof",
    "RamHeadroomProof",
    "LossTrajectoryForecast",
    "CardiacCoherenceMetric",
    "compute_inverse_variance_weights",
    "compute_ram_safety_headroom",
    "compute_loss_trajectory",
    "compute_optimal_learning_rate",
    "compute_cardiac_coherence",
    "LoraDatasetLogger",
    "AutonomousMathTrendOptimizer",
    "QwenMathOptimizerApp",
    "run_optimizer",
]
