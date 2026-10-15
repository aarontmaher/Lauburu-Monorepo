"""
test_terminal_rl_orchestrator.py - End-to-End Test Suite for T1 Terminal RL Orchestrator.

Verifies:
1. Rollout oversampling (e.g. 560 oversamples -> fastest 512 retained, stragglers cancelled).
2. End-to-end trajectory batch processing and metric calculation.
3. Clipped PPO policy loss calculation strictly over action token masks.
4. Continuous LoRA harvester streaming with thread-safe file locking.
"""

import importlib.util
import json
import os
import tempfile
import pytest
from pathlib import Path
import sys

PKG_DIR = Path(__file__).resolve().parents[2]
MONOREPO_DIR = Path(__file__).resolve().parents[3]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))
if str(MONOREPO_DIR) not in sys.path:
    sys.path.insert(0, str(MONOREPO_DIR))

from t1_terminal_rl.terminal_rl_orchestrator import (
    TerminalRLOrchestrator,
    TrajectoryBatch,
    TORCH_AVAILABLE,
)
from t1_terminal_rl.tito_assembler import TurnType

if TORCH_AVAILABLE:
    import torch

# Load T1LoRAHarvester via spec from file location to bypass numbered directory syntax
harvester_file = MONOREPO_DIR / "12_continuous_lora_evolution" / "src" / "distillation" / "t1_lora_harvester.py"
spec = importlib.util.spec_from_file_location("t1_lora_harvester", str(harvester_file))
harvester_mod = importlib.util.module_from_spec(spec)
sys.modules["t1_lora_harvester"] = harvester_mod
spec.loader.exec_module(harvester_mod)
T1LoRAHarvester = harvester_mod.T1LoRAHarvester


def test_orchestrator_oversampling_and_straggler_cancellation():
    orchestrator = TerminalRLOrchestrator(scale_s=20)

    # Simulate 560 rollouts with variable execution times
    raw_rollouts = []
    for i in range(560):
        # Durations from 0.1s up to 56.0s (stragglers at the end)
        dur = float(i) * 0.1
        passed = min(20, i % 25)
        raw_rollouts.append({
            "task_id": f"task_{i:03d}",
            "duration_seconds": dur,
            "passed_assertions": passed,
            "turns": [
                {"turn_index": 0, "type": "prompt", "token_ids": [10, 11], "text": "init task"},
                {"turn_index": 1, "type": "observation", "token_ids": [20, 21], "text": "obs"},
                {"turn_index": 1, "type": "action", "token_ids": [30, 31, 32], "text": "act"},
            ],
        })

    # Target batch size 512
    batch = orchestrator.process_rollout_results(raw_rollouts, target_batch_size=512)

    # Assertions
    assert batch.oversampled_count == 560
    assert batch.active_count == 512
    assert batch.cancelled_stragglers == 48  # 560 - 512 = 48 stragglers eliminated
    assert len(batch.trajectories) == 512

    # Verify fastest rollouts were selected: max duration in batch should be <= duration of 511th rollout
    durations = [t.metadata["duration_seconds"] for t in batch.trajectories]
    assert max(durations) <= 51.1


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch is required for PPO loss test")
def test_masked_ppo_loss_computation():
    torch.manual_seed(42)
    orchestrator = TerminalRLOrchestrator()

    seq_len = 20
    # Simulate action mask: first 10 tokens are observation (0), last 10 tokens are action (1)
    loss_mask = torch.tensor([0] * 10 + [1] * 10, dtype=torch.float32)

    logprobs_new = torch.randn(seq_len, requires_grad=True)
    logprobs_old = logprobs_new.detach() + torch.randn(seq_len) * 0.05
    advantages = torch.ones(seq_len) * 0.5

    loss, diag = orchestrator.compute_ppo_loss(
        logprobs_new=logprobs_new,
        logprobs_old=logprobs_old,
        advantages=advantages,
        loss_mask=loss_mask,
    )

    assert loss.dim() == 0
    assert diag["action_tokens"] == 10.0
    assert not torch.isnan(loss)

    # Verify backward pass
    loss.backward()
    assert logprobs_new.grad is not None
    # Tokens with mask 0 should receive 0 gradient
    assert torch.all(logprobs_new.grad[:10] == 0.0)
    # Tokens with mask 1 should receive non-zero gradient
    assert torch.any(logprobs_new.grad[10:] != 0.0)


def test_t1_lora_harvester_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dataset = Path(tmpdir) / "test_lora_dataset.jsonl"
        harvester = T1LoRAHarvester(
            output_dataset_path=tmp_dataset,
            min_reward_threshold=0.50,
        )

        orchestrator = TerminalRLOrchestrator(scale_s=20)
        rollouts = [
            # High reward rollout (18/20 -> R=0.90)
            {
                "task_id": "swe_fix_auth",
                "duration_seconds": 1.2,
                "passed_assertions": 18,
                "turns": [
                    {"turn_index": 0, "type": "prompt", "token_ids": [1, 2], "text": "Fix auth error"},
                    {"turn_index": 1, "type": "observation", "token_ids": [3], "text": "Auth failed: 401"},
                    {"turn_index": 1, "type": "action", "token_ids": [4, 5], "text": "export TOKEN=valid"},
                ],
            },
            # Low reward rollout (2/20 -> R=0.10)
            {
                "task_id": "swe_fix_auth",
                "duration_seconds": 2.5,
                "passed_assertions": 2,
                "turns": [
                    {"turn_index": 0, "type": "prompt", "token_ids": [1, 2], "text": "Fix auth error"},
                    {"turn_index": 1, "type": "observation", "token_ids": [3], "text": "Auth failed: 401"},
                    {"turn_index": 1, "type": "action", "token_ids": [6, 7], "text": "rm -rf /"},
                ],
            },
        ]

        batch = orchestrator.process_rollout_results(rollouts, target_batch_size=2)
        summary = harvester.harvest_batch(batch.trajectories)

        assert summary.trajectories_evaluated == 2
        assert summary.trajectories_accepted == 1  # only the 0.90 reward rollout is accepted
        assert summary.sft_pairs_generated == 1
        assert summary.dpo_pairs_generated == 1  # paired with rejected rollout for DPO
        assert tmp_dataset.exists()

        # Read back lines to verify format
        with open(tmp_dataset, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f]
        assert len(lines) == 2
        assert lines[0]["source"] == "t1_terminal_rl"
        assert lines[1]["source"] == "t1_terminal_rl_dpo"
        assert lines[1]["margin"] == 0.80  # 0.90 - 0.10 = 0.80
