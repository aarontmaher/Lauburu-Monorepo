"""
terminal_rl_orchestrator.py - T1 Terminal RL Training Loop & Rollout Orchestrator.

Integrates TITO trajectory assembly, R3 sparse MoE routing replay, S=20 dense
verification rewards, and PPO critic warm-start with 30x learning rate scheduling.
Supports rollout oversampling (e.g. 560 -> 512) and straggler cancellation to
ensure high-throughput multi-turn RL.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .tito_assembler import TITOAssembler, TITOTrajectory, TurnType
from .r3_routing_replay import R3RoutingCache, R3MoELayer
from .dense_verification_reward import DenseVerificationRewardCalculator, RewardOutput
from .critic_warmstart_scheduler import CriticWarmstartScheduler, TerminalValueNetwork, WarmstartStatus


@dataclass
class RolloutTask:
    task_id: str
    instruction: str
    max_turns: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrajectoryBatch:
    trajectories: List[TITOTrajectory]
    mean_reward: float
    mean_effective_reward: float
    mean_action_tokens: float
    total_tokens: int
    oversampled_count: int
    active_count: int
    cancelled_stragglers: int


class TerminalRLOrchestrator:
    """
    End-to-End Orchestrator for T1 Terminal Agent Reinforcement Learning.
    """

    def __init__(
        self,
        scale_s: int = 20,
        actor_lr: float = 1.0e-6,
        critic_lr_ratio: float = 30.0,
        target_ev: float = 0.70,
        clip_epsilon: float = 0.2,
        oversample_ratio: float = 1.09375,  # 560 / 512 = ~1.09375
    ):
        self.scale_s = scale_s
        self.actor_lr = actor_lr
        self.critic_lr_ratio = critic_lr_ratio
        self.clip_epsilon = clip_epsilon
        self.oversample_ratio = oversample_ratio

        self.tito_assembler = TITOAssembler()
        self.reward_calculator = DenseVerificationRewardCalculator(scale_s=scale_s)
        self.critic_scheduler = CriticWarmstartScheduler(
            actor_lr=actor_lr,
            critic_lr_ratio=critic_lr_ratio,
            target_ev=target_ev,
        )

    def process_rollout_results(
        self,
        raw_rollouts: List[Dict[str, Any]],
        target_batch_size: int = 512,
    ) -> TrajectoryBatch:
        """
        Sorts rollouts by completion time, selects target_batch_size fastest completions,
        cancels remaining stragglers, and calculates S=20 dense rewards.
        """
        # Sort by completion duration if present, otherwise maintain order
        sorted_rollouts = sorted(
            raw_rollouts,
            key=lambda x: x.get("duration_seconds", 0.0),
        )

        oversampled_total = len(sorted_rollouts)
        selected_rollouts = sorted_rollouts[:target_batch_size]
        stragglers_cancelled = max(0, oversampled_total - len(selected_rollouts))

        trajectories: List[TITOTrajectory] = []
        total_raw_reward = 0.0
        total_eff_reward = 0.0
        total_action_toks = 0
        total_tokens_all = 0

        for r_data in selected_rollouts:
            task_id = r_data.get("task_id", "task_anon")
            turns = r_data.get("turns", [])
            passed_assertions = r_data.get("passed_assertions", 0)
            turn_count = len([t for t in turns if t.get("type") == "action"])

            # Compute S=20 dense reward
            reward_out = self.reward_calculator.calculate_reward(
                passed_assertions=passed_assertions,
                turn_count=max(1, turn_count),
                prior_turn_count=r_data.get("prior_turn_count"),
                prior_passed=r_data.get("prior_passed"),
            )

            traj = self.tito_assembler.assemble_from_turns(
                task_id=task_id,
                turns=turns,
                r3_cache=r_data.get("r3_cache"),
                reward=reward_out.raw_reward,
                metadata={
                    "effective_reward": reward_out.effective_reward,
                    "passed_assertions": passed_assertions,
                    "reward_reason": reward_out.reason,
                    "duration_seconds": r_data.get("duration_seconds", 0.0),
                },
            )
            traj.effective_reward = reward_out.effective_reward
            trajectories.append(traj)

            total_raw_reward += traj.reward
            total_eff_reward += traj.effective_reward
            total_action_toks += traj.action_tokens
            total_tokens_all += traj.total_tokens

        n_traj = max(1, len(trajectories))
        return TrajectoryBatch(
            trajectories=trajectories,
            mean_reward=round(total_raw_reward / n_traj, 4),
            mean_effective_reward=round(total_eff_reward / n_traj, 4),
            mean_action_tokens=round(total_action_toks / n_traj, 2),
            total_tokens=total_tokens_all,
            oversampled_count=oversampled_total,
            active_count=len(trajectories),
            cancelled_stragglers=stragglers_cancelled,
        )

    if TORCH_AVAILABLE:
        def compute_ppo_loss(
            self,
            logprobs_new: torch.Tensor,
            logprobs_old: torch.Tensor,
            advantages: torch.Tensor,
            loss_mask: torch.Tensor,
        ) -> Tuple[torch.Tensor, Dict[str, float]]:
            """
            Computes clipped PPO policy loss strictly over action tokens (loss_mask == 1).
            
            Args:
                logprobs_new: (N,) log-probabilities under current policy
                logprobs_old: (N,) log-probabilities under rollout policy
                advantages: (N,) GAE advantages
                loss_mask: (N,) binary action mask (1 for action tokens, 0 for observation/prompt)
            """
            ratio = torch.exp(logprobs_new - logprobs_old)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2)

            # Apply loss mask
            masked_loss = policy_loss * loss_mask
            num_action_tokens = loss_mask.sum().clamp(min=1.0)
            final_loss = masked_loss.sum() / num_action_tokens

            # Compute diagnostic clip fraction and approximate KL
            with torch.no_grad():
                clipped = (ratio < 1.0 - self.clip_epsilon) | (ratio > 1.0 + self.clip_epsilon)
                clip_frac = (clipped.float() * loss_mask).sum() / num_action_tokens
                approx_kl = (((ratio - 1.0) - (logprobs_new - logprobs_old)) * loss_mask).sum() / num_action_tokens

            diagnostics = {
                "loss": float(final_loss.item()),
                "clip_fraction": float(clip_frac.item()),
                "approx_kl": float(approx_kl.item()),
                "action_tokens": float(num_action_tokens.item()),
            }
            return final_loss, diagnostics
