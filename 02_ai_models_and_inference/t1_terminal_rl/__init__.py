"""
t1_terminal_rl - Clean-Room Implementation of T1 Terminal Agent Reinforcement Learning.

Based on arXiv:2609.11042:
- TITO: Token-In, Token-Out trajectory assembly with 0.0000% loss-region drift.
- R3: Sparse MoE Rollout Routing Replay avoiding inference vs training divergence.
- Dense Verification Reward: Globally normalized R = min(1.0, P / 20).
- PPO Critic Warm-Start: Value pre-training (EV >= 0.70) with 30x learning rate ratio.
"""

from .tito_assembler import (
    TurnType,
    TurnSegment,
    TITOTrajectory,
    TITOAssembler,
)
from .r3_routing_replay import (
    LayerRoutingRecord,
    R3RoutingCache,
)
from .dense_verification_reward import (
    AssertionResult,
    RewardOutput,
    DenseVerificationRewardCalculator,
)
from .critic_warmstart_scheduler import (
    WarmstartStatus,
    CriticWarmstartScheduler,
)
from .terminal_rl_orchestrator import (
    RolloutTask,
    TrajectoryBatch,
    TerminalRLOrchestrator,
)

__all__ = [
    "TurnType",
    "TurnSegment",
    "TITOTrajectory",
    "TITOAssembler",
    "LayerRoutingRecord",
    "R3RoutingCache",
    "AssertionResult",
    "RewardOutput",
    "DenseVerificationRewardCalculator",
    "WarmstartStatus",
    "CriticWarmstartScheduler",
    "RolloutTask",
    "TrajectoryBatch",
    "TerminalRLOrchestrator",
]
