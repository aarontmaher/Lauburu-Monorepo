"""
critic_warmstart_scheduler.py - PPO Critic Warm-Start, Explained Variance & GAE Engine.

Implements the PPO Value Function (Critic) warm-start scheduling and 30x asymmetric
learning rate ratio from the T1 paper (arXiv:2609.11042). Resolves GRPO's degenerate
zero-advantage failure mode on hard long-horizon tasks and ensures stable Generalized
Advantage Estimation (GAE) across multi-turn trajectories.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class WarmstartStatus:
    epoch: int
    explained_variance: float
    loss: float
    target_ev: float = 0.70
    is_warmed_up: bool = False
    message: str = ""


class CriticWarmstartScheduler:
    """
    Manages the critic warm-start phase, computes explained variance,
    enforces the 30x learning rate asymmetry, and computes GAE advantages.
    """

    DEFAULT_TARGET_EV: float = 0.70
    DEFAULT_ACTOR_LR: float = 1.0e-6
    DEFAULT_CRITIC_LR_RATIO: float = 30.0  # Critic LR = 30x Actor LR = 3.0e-5
    DEFAULT_GAMMA: float = 1.0
    DEFAULT_LAMBDA: float = 1.0

    def __init__(
        self,
        actor_lr: float = DEFAULT_ACTOR_LR,
        critic_lr_ratio: float = DEFAULT_CRITIC_LR_RATIO,
        target_ev: float = DEFAULT_TARGET_EV,
        gamma: float = DEFAULT_GAMMA,
        lam: float = DEFAULT_LAMBDA,
    ):
        self.actor_lr = actor_lr
        self.critic_lr = actor_lr * critic_lr_ratio
        self.target_ev = target_ev
        self.gamma = gamma
        self.lam = lam
        self.warmed_up = False

    @staticmethod
    def calculate_explained_variance(
        predictions: Sequence[float],
        targets: Sequence[float],
    ) -> float:
        """
        EV = 1 - Var(targets - predictions) / Var(targets)
        EV = 1.0 is perfect prediction.
        EV <= 0.0 means predictions are worse than or equal to predicting the mean.
        """
        n = len(targets)
        if n < 2:
            return 0.0

        mean_target = sum(targets) / n
        var_target = sum((y - mean_target) ** 2 for y in targets) / n

        if var_target < 1e-12:
            # Targets have zero variance (e.g. all 0 or all 1)
            # If predictions match targets exactly, EV=1.0; otherwise 0.0
            error_var = sum((y - p) ** 2 for y, p in zip(targets, predictions)) / n
            return 1.0 if error_var < 1e-8 else 0.0

        errors = [y - p for y, p in zip(targets, predictions)]
        mean_error = sum(errors) / n
        var_error = sum((e - mean_error) ** 2 for e in errors) / n

        ev = 1.0 - (var_error / var_target)
        return float(ev)

    def calculate_gae_advantages(
        self,
        rewards: Sequence[float],
        values: Sequence[float],
        next_value: float = 0.0,
        dones: Optional[Sequence[bool]] = None,
    ) -> Tuple[List[float], List[float]]:
        """
        Computes Generalized Advantage Estimation (GAE) with gamma=1.0, lambda=1.0.
        Returns (advantages, target_returns).
        """
        t_steps = len(rewards)
        if len(values) != t_steps:
            raise ValueError(f"Values length ({len(values)}) must match rewards length ({t_steps})")

        if dones is None:
            dones = [False] * (t_steps - 1) + [True]

        advantages = [0.0] * t_steps
        last_gae = 0.0

        for t in reversed(range(t_steps)):
            is_done = dones[t]
            v_next = next_value if t == t_steps - 1 else values[t + 1]
            non_terminal = 0.0 if is_done else 1.0

            delta = rewards[t] + self.gamma * v_next * non_terminal - values[t]
            last_gae = delta + self.gamma * self.lam * non_terminal * last_gae
            advantages[t] = last_gae

        returns = [adv + val for adv, val in zip(advantages, values)]
        return advantages, returns

    if TORCH_AVAILABLE:
        def warm_start_critic(
            self,
            critic_model: nn.Module,
            dataloader_or_features: Union[torch.Tensor, Any],
            target_returns: torch.Tensor,
            optimizer: Optional[optim.Optimizer] = None,
            max_epochs: int = 15,
        ) -> WarmstartStatus:
            """
            Pre-warms the critic model until EV >= target_ev or max_epochs is reached.
            """
            if optimizer is None:
                optimizer = optim.AdamW(critic_model.parameters(), lr=self.critic_lr, weight_decay=1e-4)

            criterion = nn.MSELoss()
            critic_model.train()

            features = dataloader_or_features
            targets = target_returns.float()
            if targets.dim() == 1:
                targets = targets.unsqueeze(-1)

            final_ev = 0.0
            final_loss = 0.0

            for epoch in range(1, max_epochs + 1):
                optimizer.zero_grad()
                pred_v = critic_model(features)
                loss = criterion(pred_v, targets)
                loss.backward()
                optimizer.step()

                final_loss = float(loss.item())
                preds_np = pred_v.detach().cpu().squeeze().tolist()
                targets_np = targets.detach().cpu().squeeze().tolist()

                if not isinstance(preds_np, list):
                    preds_np = [preds_np]
                if not isinstance(targets_np, list):
                    targets_np = [targets_np]

                ev = self.calculate_explained_variance(preds_np, targets_np)
                final_ev = ev

                if ev >= self.target_ev:
                    self.warmed_up = True
                    return WarmstartStatus(
                        epoch=epoch,
                        explained_variance=round(ev, 4),
                        loss=round(final_loss, 6),
                        target_ev=self.target_ev,
                        is_warmed_up=True,
                        message=f"Warm-start threshold satisfied (EV={ev:.4f} >= {self.target_ev:.2f}) at epoch {epoch}",
                    )

            self.warmed_up = (final_ev >= self.target_ev)
            return WarmstartStatus(
                epoch=max_epochs,
                explained_variance=round(final_ev, 4),
                loss=round(final_loss, 6),
                target_ev=self.target_ev,
                is_warmed_up=self.warmed_up,
                message=f"Max epochs reached (EV={final_ev:.4f}, target={self.target_ev:.2f})",
            )


if TORCH_AVAILABLE:
    class TerminalValueNetwork(nn.Module):
        """
        Lightweight value network for state-action representation scoring.
        Maps pooled token representations to a scalar state-value estimate.
        """

        def __init__(self, hidden_dim: int = 128, mlp_hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(hidden_dim, mlp_hidden),
                nn.ReLU(),
                nn.Linear(mlp_hidden, mlp_hidden // 2),
                nn.ReLU(),
                nn.Linear(mlp_hidden // 2, 1),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            if x.dim() == 3:
                # Average pooling over sequence length
                x = x.mean(dim=1)
            return self.net(x)
else:
    class TerminalValueNetwork:
        pass
