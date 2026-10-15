"""
Bradley-Terry Sigmoid Log-Ratio DPO Loss Engine optimized for Apple Silicon MPS.

Computes mathematically stable Direct Preference Optimization (DPO) loss:
  L_DPO = -log sigmoid(beta * (log(pi_theta(yw|x)/pi_ref(yw|x)) - log(pi_theta(yl|x)/pi_ref(yl|x))))

Features:
- Numerically clamped log-ratios to prevent sigmoid saturation and NaN gradients on MPS.
- Support for pre-cached reference log-probabilities or on-the-fly reference computation.
- Computes implicit rewards, reward margins, and batch accuracy metrics.
- Native float16 / bfloat16 / float32 execution across MPS, CPU, and CUDA.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


def compute_token_log_probs(
    logits: torch.Tensor,
    labels: torch.Tensor,
    label_pad_token_id: int = -100,
    average_log_prob: bool = False,
) -> torch.Tensor:
    """
    Computes per-sequence log probabilities from token logits and label masks.
    
    Args:
        logits: Tensor of shape (batch_size, seq_len, vocab_size) or (batch_size, seq_len - 1, vocab_size)
        labels: Tensor of shape (batch_size, seq_len)
        label_pad_token_id: Token ID indicating ignored tokens (default: -100)
        average_log_prob: If True, normalizes by sequence length instead of sum
    
    Returns:
        Tensor of shape (batch_size,) with sequence log probabilities.
    """
    if logits.shape[1] == labels.shape[1]:
        # Logits predict next token, shift by 1
        logits = logits[:, :-1, :]
        labels = labels[:, 1:]

    # Log softmax over vocabulary
    log_probs = F.log_softmax(logits, dim=-1)

    # Replace ignore index in labels with 0 for gather operation
    loss_mask = labels != label_pad_token_id
    clamped_labels = labels.clone()
    clamped_labels[~loss_mask] = 0

    # Gather log prob of actual target tokens
    per_token_logps = torch.gather(log_probs, dim=2, index=clamped_labels.unsqueeze(2)).squeeze(2)

    # Mask out pad / prompt tokens
    masked_logps = per_token_logps * loss_mask.float()

    if average_log_prob:
        seq_lengths = loss_mask.sum(dim=-1).clamp(min=1.0).float()
        return masked_logps.sum(dim=-1) / seq_lengths
    else:
        return masked_logps.sum(dim=-1)


class DPOLossMPS(nn.Module):
    """
    Apple Silicon Metal MPS-optimized Direct Preference Optimization Loss.
    """

    def __init__(
        self,
        beta: float = 0.1,
        label_smoothing: float = 0.0,
        clamp_min: float = -10.0,
        clamp_max: float = 10.0,
        reference_free: bool = False,
    ):
        super().__init__()
        self.beta = beta
        self.label_smoothing = label_smoothing
        self.clamp_min = clamp_min
        self.clamp_max = clamp_max
        self.reference_free = reference_free

    def forward(
        self,
        policy_chosen_logps: torch.Tensor,
        policy_rejected_logps: torch.Tensor,
        reference_chosen_logps: Optional[torch.Tensor] = None,
        reference_rejected_logps: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Computes the Bradley-Terry DPO loss.
        
        Args:
            policy_chosen_logps: (B,) log probabilities of chosen responses under policy pi_theta
            policy_rejected_logps: (B,) log probabilities of rejected responses under policy pi_theta
            reference_chosen_logps: (B,) log probabilities of chosen responses under reference model pi_ref
            reference_rejected_logps: (B,) log probabilities of rejected responses under reference model pi_ref
            
        Returns:
            (loss, chosen_rewards, rejected_rewards, accuracies)
        """
        # Reference log ratios
        if self.reference_free or reference_chosen_logps is None or reference_rejected_logps is None:
            chosen_logratios = policy_chosen_logps
            rejected_logratios = policy_rejected_logps
        else:
            chosen_logratios = policy_chosen_logps - reference_chosen_logps
            rejected_logratios = policy_rejected_logps - reference_rejected_logps

        # Compute difference in log ratios
        logits_diff = self.beta * (chosen_logratios - rejected_logratios)

        # Clamping for numerical stability on MPS (avoids saturation / zero grad / NaN)
        logits_diff = torch.clamp(logits_diff, min=self.clamp_min, max=self.clamp_max)

        # Bradley-Terry loss with optional label smoothing
        if self.label_smoothing > 0.0:
            losses = (
                -F.logsigmoid(logits_diff) * (1.0 - self.label_smoothing)
                - F.logsigmoid(-logits_diff) * self.label_smoothing
            )
        else:
            losses = -F.logsigmoid(logits_diff)

        loss = losses.mean()

        # Compute implicit rewards for metrics & monitoring
        chosen_rewards = (self.beta * chosen_logratios).detach()
        rejected_rewards = (self.beta * rejected_logratios).detach()
        accuracies = (chosen_rewards > rejected_rewards).float().mean().detach()

        return loss, chosen_rewards, rejected_rewards, accuracies

    def compute_loss_from_logits(
        self,
        policy_chosen_logits: torch.Tensor,
        policy_rejected_logits: torch.Tensor,
        chosen_labels: torch.Tensor,
        rejected_labels: torch.Tensor,
        reference_chosen_logits: Optional[torch.Tensor] = None,
        reference_rejected_logits: Optional[torch.Tensor] = None,
        label_pad_token_id: int = -100,
        average_log_prob: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        End-to-end forward step starting directly from raw model logits.
        """
        policy_chosen_logps = compute_token_log_probs(
            policy_chosen_logits, chosen_labels, label_pad_token_id=label_pad_token_id, average_log_prob=average_log_prob
        )
        policy_rejected_logps = compute_token_log_probs(
            policy_rejected_logits, rejected_labels, label_pad_token_id=label_pad_token_id, average_log_prob=average_log_prob
        )

        ref_chosen_logps = None
        ref_rejected_logps = None
        if reference_chosen_logits is not None and reference_rejected_logits is not None:
            ref_chosen_logps = compute_token_log_probs(
                reference_chosen_logits, chosen_labels, label_pad_token_id=label_pad_token_id, average_log_prob=average_log_prob
            )
            ref_rejected_logps = compute_token_log_probs(
                reference_rejected_logits, rejected_labels, label_pad_token_id=label_pad_token_id, average_log_prob=average_log_prob
            )

        return self.forward(
            policy_chosen_logps=policy_chosen_logps,
            policy_rejected_logps=policy_rejected_logps,
            reference_chosen_logps=ref_chosen_logps,
            reference_rejected_logps=ref_rejected_logps,
        )
