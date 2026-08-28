#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lauburu Red/Blue Adversarial Arena: HuggingFace Training & Reward Package
"""

from .schemas.reward_dataset_schemas import (
    DPOPairwiseRecord,
    SFTTrainingRecord,
    GRPOStep,
    GRPOTrajectoryRecord,
    SmolagentsSwarmTelemetry,
    LoRADatasetSink,
    resolve_lora_dataset_dir
)

from .hf_adversarial_reward_trainer import (
    AdversarialRewardScorer,
    RedRewardBreakdown,
    BlueRewardBreakdown,
    RewardEvaluationResult,
    DPOConfig,
    SFTAnchoredDPOLoss,
    SFTAnchoredDPOTrainer,
    CANONICAL_SECURITY_SURFACES
)

__all__ = [
    "DPOPairwiseRecord",
    "SFTTrainingRecord",
    "GRPOStep",
    "GRPOTrajectoryRecord",
    "SmolagentsSwarmTelemetry",
    "LoRADatasetSink",
    "resolve_lora_dataset_dir",
    "AdversarialRewardScorer",
    "RedRewardBreakdown",
    "BlueRewardBreakdown",
    "RewardEvaluationResult",
    "DPOConfig",
    "SFTAnchoredDPOLoss",
    "SFTAnchoredDPOTrainer",
    "CANONICAL_SECURITY_SURFACES"
]
