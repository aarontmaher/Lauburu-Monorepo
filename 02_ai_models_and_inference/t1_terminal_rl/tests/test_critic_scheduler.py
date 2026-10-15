"""
test_critic_scheduler.py - Test Suite for PPO Critic Warm-Start & Asymmetric LR Scheduling.

Verifies:
1. Mathematical accuracy of Explained Variance (EV) across perfect, mean, and noisy predictions.
2. 30x learning rate asymmetry invariant (critic_lr = 30x actor_lr).
3. GAE advantage computation (gamma=1.0, lambda=1.0).
4. Critic warm-start threshold convergence (EV >= 0.70) using TerminalValueNetwork.
"""

import pytest
from pathlib import Path
import sys

PKG_DIR = Path(__file__).resolve().parents[2]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from t1_terminal_rl.critic_warmstart_scheduler import (
    CriticWarmstartScheduler,
    WarmstartStatus,
    TORCH_AVAILABLE,
)

if TORCH_AVAILABLE:
    import torch
    from t1_terminal_rl.critic_warmstart_scheduler import TerminalValueNetwork


def test_explained_variance_calculation():
    # Perfect predictions: EV must be 1.0
    targets = [0.1, 0.4, 0.6, 0.9, 0.2, 0.8]
    ev_perfect = CriticWarmstartScheduler.calculate_explained_variance(targets, targets)
    assert ev_perfect == pytest.approx(1.0, abs=1e-6)

    # Predicting the exact mean of targets: EV must be 0.0
    mean_val = sum(targets) / len(targets)
    mean_preds = [mean_val] * len(targets)
    ev_mean = CriticWarmstartScheduler.calculate_explained_variance(mean_preds, targets)
    assert ev_mean == pytest.approx(0.0, abs=1e-6)

    # Random inverse predictions: EV < 0.0
    bad_preds = [10.0, -10.0, 20.0, -5.0, 15.0, -8.0]
    ev_bad = CriticWarmstartScheduler.calculate_explained_variance(bad_preds, targets)
    assert ev_bad < 0.0


def test_asymmetric_learning_rate_ratio():
    actor_lr = 1.0e-6
    scheduler = CriticWarmstartScheduler(
        actor_lr=actor_lr,
        critic_lr_ratio=30.0,
        target_ev=0.70,
    )
    # Critic LR must be exactly 30x actor LR
    assert scheduler.critic_lr == pytest.approx(3.0e-5)
    assert scheduler.critic_lr / scheduler.actor_lr == pytest.approx(30.0)


def test_gae_advantages_calculation():
    scheduler = CriticWarmstartScheduler(gamma=1.0, lam=1.0)

    # 3-step trajectory with rewards [0.0, 0.0, 1.0] and critic values [0.3, 0.5, 0.8]
    rewards = [0.0, 0.0, 1.0]
    values = [0.3, 0.5, 0.8]
    dones = [False, False, True]

    advantages, returns = scheduler.calculate_gae_advantages(
        rewards=rewards,
        values=values,
        next_value=0.0,
        dones=dones,
    )

    # At t=2 (terminal): delta_2 = 1.0 + 0 - 0.8 = 0.2
    # At t=1: delta_1 = 0.0 + 0.8 - 0.5 = 0.3; GAE_1 = 0.3 + 0.2 = 0.5
    # At t=0: delta_0 = 0.0 + 0.5 - 0.3 = 0.2; GAE_0 = 0.2 + 0.5 = 0.7
    assert advantages[2] == pytest.approx(0.2, abs=1e-5)
    assert advantages[1] == pytest.approx(0.5, abs=1e-5)
    assert advantages[0] == pytest.approx(0.7, abs=1e-5)

    # returns = advantage + value: [0.7+0.3, 0.5+0.5, 0.2+0.8] = [1.0, 1.0, 1.0]
    assert returns[0] == pytest.approx(1.0, abs=1e-5)
    assert returns[1] == pytest.approx(1.0, abs=1e-5)
    assert returns[2] == pytest.approx(1.0, abs=1e-5)


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch is required for warm-start tests")
def test_critic_warmstart_convergence():
    torch.manual_seed(42)
    hidden_dim = 16
    num_samples = 128

    # Create linear features and target returns
    features = torch.randn(num_samples, hidden_dim)
    weights = torch.randn(hidden_dim, 1)
    targets = (features @ weights) + 0.05 * torch.randn(num_samples, 1)

    value_net = TerminalValueNetwork(hidden_dim=hidden_dim, mlp_hidden=32)
    scheduler = CriticWarmstartScheduler(
        actor_lr=1e-3,
        critic_lr_ratio=30.0,
        target_ev=0.70,
    )

    status = scheduler.warm_start_critic(
        critic_model=value_net,
        dataloader_or_features=features,
        target_returns=targets,
        max_epochs=20,
    )

    assert status.is_warmed_up is True
    assert status.explained_variance >= 0.70
    assert scheduler.warmed_up is True
