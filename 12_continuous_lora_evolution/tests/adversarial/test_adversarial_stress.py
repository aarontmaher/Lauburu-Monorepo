"""
Adversarial Stress Test Suite — Challenger 1
Autonomous 24/7 AI Training Optimization Engine (Subsystem 12)

Target Stress Scenarios:
1. Non-finite gradients / NaN values injection (fail-fast vs graceful skipping)
2. Dynamic RAM Governor stress under simulated memory pressure, threshold gating & cache reclamation
3. Corrupted JSONL inputs, 0-byte files, malformed Python code AST gate & quarantine routing
4. Server reload flapping & consecutive health check verification
"""

import json
import math
import os
import shutil
import tempfile
import time
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from src.distillation.ast_compiler_gate import ASTCompilerGate
from src.distillation.dataset_loader import (
    DatasetIngestionEngine,
    DPORecord,
    MultiSchemaNormalizer,
    SFTRecord,
    get_dpo_dataloader,
    get_sft_dataloader,
)
from src.distillation.dpo_loss_mps import DPOLossMPS, compute_token_log_probs
from src.distillation.replay_buffer import StratifiedReplayBuffer
from src.distillation.sample_deduplicator import SampleDeduplicator
from src.distillation.tokenizer_aligner import TokenizerAligner, detect_model_family
from src.orchestration.server_reload_sentinel import (
    PORT_LLAMA_RPC,
    PORT_PRIMA_PRP,
    PORT_PROXY_ROUTER,
    ServerHealthStatus,
    ServerReloadSentinel,
    reload_inference_cluster,
)
from src.trainer.dynamic_ram_governor import (
    DynamicRAMGovernor,
    MemoryGovernorError,
    MemoryMetrics,
    MemoryStatusTier,
)
from src.trainer.mps_qlora_trainer import (
    EpochResult,
    MPSQLoRAConfig,
    MPSQLoRATrainer,
    StepResult,
    TrainingSummary,
)
from tests.e2e.test_helpers import MockCausalLM, MockTokenizer


# ==============================================================================
# Helper Models & Mock Classes for Controlled Adversarial Injection
# ==============================================================================

class SimpleLinearModel(nn.Module):
    """Linear regression model for deterministic autograd testing."""
    def __init__(self, in_features: int = 4, out_features: int = 1):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features, bias=True)
        # Initialize with fixed weights
        nn.init.constant_(self.linear.weight, 1.0)
        nn.init.constant_(self.linear.bias, 0.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


class NonFiniteLossModel(nn.Module):
    """Model that dynamically injects NaN, Inf, or normal outputs on demand."""
    def __init__(self, in_features: int = 4, out_features: int = 1):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)
        self.inject_mode: Optional[str] = None  # "nan_loss", "inf_loss", "neginf_loss"

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.linear(x)
        if self.inject_mode == "nan_loss":
            return out * float("nan")
        elif self.inject_mode == "inf_loss":
            return out * float("inf")
        elif self.inject_mode == "neginf_loss":
            return out * float("-inf")
        return out


def make_mock_vmem(total_gb: float, used_gb: float, percent: Optional[float] = None) -> Any:
    """Creates a mock psutil.virtual_memory struct."""
    bytes_in_gb = 1024 ** 3
    total_bytes = int(total_gb * bytes_in_gb)
    used_bytes = int(used_gb * bytes_in_gb)
    available_bytes = max(0, total_bytes - used_bytes)
    pct = percent if percent is not None else (used_bytes / total_bytes * 100.0)
    return SimpleNamespace(
        total=total_bytes,
        used=used_bytes,
        available=available_bytes,
        percent=pct,
    )


# ==============================================================================
# TEST SUITE 1: Non-Finite Gradients & NaN Values Injection
# ==============================================================================

class TestAdversarialNonFiniteGradients(unittest.TestCase):
    """
    Stress tests for F2 (Gradient Stability) & F11 (DPO Loss MPS):
    - Strict fail-fast on NaN / Inf when fail_on_nan=True
    - Graceful step skipping, gradient zeroing, and weight preservation when fail_on_nan=False
    - Loss clamping in DPOLossMPS against extreme log-ratios (+-1000)
    - Gradient norm clipping bound assertion (<= 1.0) on exploding gradients
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.device = "cpu"  # CPU for deterministic float manipulation in test env

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_adv_1_1_nan_loss_fail_on_nan_raises_floating_point_error(self):
        """Verify FloatingPointError is raised immediately when NaN loss is produced with fail_on_nan=True."""
        model = NonFiniteLossModel(4, 1)
        model.inject_mode = "nan_loss"

        config = MPSQLoRAConfig(
            device=self.device,
            precision="float32",
            fail_on_nan=True,
            gradient_accumulation_steps=1,
            output_dir=self.tmp_dir,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.randn(2, 4)
        y = torch.randn(2, 1)
        batch = (x, y)

        with self.assertRaises(FloatingPointError) as ctx:
            trainer.train_step(batch, step_idx=0)

        self.assertIn("Non-finite loss encountered", str(ctx.exception))
        self.assertEqual(trainer.total_skipped_nan_steps, 0)

    def test_adv_1_2_inf_loss_fail_on_nan_raises_floating_point_error(self):
        """Verify FloatingPointError is raised when positive or negative infinity loss occurs with fail_on_nan=True."""
        for inf_mode in ["inf_loss", "neginf_loss"]:
            model = NonFiniteLossModel(4, 1)
            model.inject_mode = inf_mode

            config = MPSQLoRAConfig(
                device=self.device,
                precision="float32",
                fail_on_nan=True,
                gradient_accumulation_steps=1,
                output_dir=self.tmp_dir,
            )
            trainer = MPSQLoRATrainer(model=model, config=config)

            batch = (torch.randn(2, 4), torch.randn(2, 1))
            with self.assertRaises(FloatingPointError) as ctx:
                trainer.train_step(batch, step_idx=0)
            self.assertIn("Non-finite loss encountered", str(ctx.exception))

    def test_adv_1_3_nan_loss_graceful_skipping_when_fail_on_nan_false(self):
        """Verify graceful step skipping and gradient zeroing when fail_on_nan=False upon NaN loss."""
        model = NonFiniteLossModel(4, 1)
        model.inject_mode = "nan_loss"

        config = MPSQLoRAConfig(
            device=self.device,
            precision="float32",
            fail_on_nan=False,
            gradient_accumulation_steps=1,
            output_dir=self.tmp_dir,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Snapshot weights before step
        orig_weights = model.linear.weight.clone()

        batch = (torch.randn(2, 4), torch.randn(2, 1))
        step_result = trainer.train_step(batch, step_idx=0)

        self.assertTrue(step_result.skipped_nan_step)
        self.assertFalse(step_result.optimizer_stepped)
        self.assertTrue(math.isnan(step_result.unscaled_loss))
        self.assertEqual(trainer.total_skipped_nan_steps, 1)

        # Weights must be exactly unmodified
        torch.testing.assert_close(model.linear.weight, orig_weights)

    def test_adv_1_4_nan_gradient_in_backward_fail_on_nan_true(self):
        """Verify fail-fast on NaN gradients during accumulation boundary when fail_on_nan=True."""
        model = SimpleLinearModel(4, 1)
        config = MPSQLoRAConfig(
            device=self.device,
            precision="float32",
            fail_on_nan=True,
            gradient_accumulation_steps=1,
            output_dir=self.tmp_dir,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Custom loss function that outputs finite loss but injects NaN in backward gradient
        def poisoned_loss_fn(m, batch):
            x, y = batch
            preds = m(x)
            loss = nn.functional.mse_loss(preds, y)
            loss.register_hook(lambda g: torch.full_like(g, float("nan")))
            return loss

        trainer.loss_fn = poisoned_loss_fn
        batch = (torch.randn(2, 4), torch.randn(2, 1))

        with self.assertRaises(FloatingPointError) as ctx:
            trainer.train_step(batch, step_idx=0)

        self.assertIn("Non-finite gradient", str(ctx.exception))

    def test_adv_1_5_nan_gradient_in_backward_graceful_skipping(self):
        """Verify graceful gradient zeroing and weight preservation on NaN gradient when fail_on_nan=False."""
        model = SimpleLinearModel(4, 1)
        config = MPSQLoRAConfig(
            device=self.device,
            precision="float32",
            fail_on_nan=False,
            gradient_accumulation_steps=1,
            output_dir=self.tmp_dir,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Record initial weights
        initial_weight = model.linear.weight.clone().detach()

        def poisoned_loss_fn(m, batch):
            x, y = batch
            preds = m(x)
            loss = nn.functional.mse_loss(preds, y)
            loss.register_hook(lambda g: torch.full_like(g, float("nan")))
            return loss

        trainer.loss_fn = poisoned_loss_fn
        batch = (torch.randn(2, 4), torch.randn(2, 1))

        step_res = trainer.train_step(batch, step_idx=0)

        self.assertTrue(step_res.skipped_nan_step)
        self.assertFalse(step_res.optimizer_stepped)
        self.assertEqual(trainer.total_skipped_nan_steps, 1)
        # Verify model parameters were not corrupted
        torch.testing.assert_close(model.linear.weight, initial_weight)

    def test_adv_1_6_exploding_gradients_strictly_clipped_to_max_norm(self):
        """Verify that enormous gradients (norm > 10,000) are strictly clamped to <= 1.0."""
        model = SimpleLinearModel(4, 1)
        config = MPSQLoRAConfig(
            device=self.device,
            precision="float32",
            max_grad_norm=1.0,
            gradient_accumulation_steps=1,
            output_dir=self.tmp_dir,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Huge inputs to trigger massive gradients
        x = torch.full((2, 4), 10000.0)
        y = torch.full((2, 1), 0.0)
        batch = (x, y)

        step_res = trainer.train_step(batch, step_idx=0)

        self.assertIsNotNone(step_res.grad_norm_before_clip)
        self.assertGreater(step_res.grad_norm_before_clip, 1000.0)
        self.assertIsNotNone(step_res.grad_norm_after_clip)
        self.assertLessEqual(step_res.grad_norm_after_clip, 1.00001)

    def test_adv_1_7_dpo_loss_numerical_clamping_on_extreme_log_ratios(self):
        """Verify DPOLossMPS stays numerically stable and finite with extreme log-ratio deltas (+-1000.0)."""
        dpo_loss_fn = DPOLossMPS(beta=0.1, clamp_min=-10.0, clamp_max=10.0)

        # Extreme case 1: Policy infinitely prefers chosen over rejected
        policy_chosen = torch.tensor([1000.0, 500.0])
        policy_rejected = torch.tensor([-1000.0, -500.0])
        loss, ch_r, rej_r, acc = dpo_loss_fn(policy_chosen, policy_rejected)

        self.assertTrue(torch.isfinite(loss))
        self.assertGreaterEqual(loss.item(), 0.0)
        self.assertEqual(acc.item(), 1.0)

        # Extreme case 2: Policy infinitely prefers rejected over chosen (complete collapse)
        policy_chosen_bad = torch.tensor([-1000.0, -500.0])
        policy_rejected_bad = torch.tensor([1000.0, 500.0])
        loss_bad, ch_r_bad, rej_r_bad, acc_bad = dpo_loss_fn(policy_chosen_bad, policy_rejected_bad)

        self.assertTrue(torch.isfinite(loss_bad))
        self.assertGreater(loss_bad.item(), loss.item())
        self.assertEqual(acc_bad.item(), 0.0)

    def test_adv_1_8_multi_epoch_nan_loss_tolerance_summary(self):
        """Verify multi-batch DataLoader with alternating NaN batches records skipped counts accurately in fit()."""
        model = SimpleLinearModel(4, 1)
        config = MPSQLoRAConfig(
            device=self.device,
            precision="float32",
            fail_on_nan=False,
            gradient_accumulation_steps=1,
            max_epochs=1,
            output_dir=self.tmp_dir,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # 4 batches in dataset
        x_data = torch.randn(8, 4)
        y_data = torch.randn(8, 1)
        dataset = TensorDataset(x_data, y_data)
        dataloader = DataLoader(dataset, batch_size=2, shuffle=False)

        # Step 0: normal, Step 1: NaN loss, Step 2: normal, Step 3: NaN loss
        step_call = 0
        def alternating_loss_fn(m, batch):
            nonlocal step_call
            x, y = batch
            preds = m(x)
            if step_call % 2 == 1:
                loss = nn.functional.mse_loss(preds, y) * float("nan")
            else:
                loss = nn.functional.mse_loss(preds, y)
            step_call += 1
            return loss

        trainer.loss_fn = alternating_loss_fn
        summary = trainer.fit(dataloader, num_epochs=1)

        self.assertEqual(summary.total_skipped_nan_steps, 2)
        self.assertEqual(summary.total_optimizer_steps, 2)
        self.assertEqual(summary.total_micro_steps, 4)


# ==============================================================================
# TEST SUITE 2: Dynamic RAM Governor & Memory Pressure Stress
# ==============================================================================

class TestAdversarialRAMGovernor(unittest.TestCase):
    """
    Stress tests for F4 (Dynamic RAM Governor & Sentinel):
    - Exact threshold gating across all 4 tiers (Optimal, Balanced, Restricted, Critical)
    - Decimal boundary precision on 2.50 GB headroom floor and 90.0% dynamic cap
    - Auto-reclamation trigger on memory pressure
    - Immediate MemoryGovernorError halt preventing OOM in training loops
    """

    def test_adv_2_1_tier_classification_under_simulated_memory_pressures(self):
        """Verify correct status tier classification across varying memory scenarios."""
        # Tier 1: Optimal (<70% usage)
        gov1 = DynamicRAMGovernor(vmem_provider=lambda: make_mock_vmem(24.0, 12.0, 50.0))
        m1 = gov1.get_metrics()
        self.assertEqual(m1.status_tier, MemoryStatusTier.TIER_1_OPTIMAL)
        self.assertTrue(m1.is_safe)

        # Tier 2: Balanced (70% - 85% usage)
        gov2 = DynamicRAMGovernor(vmem_provider=lambda: make_mock_vmem(24.0, 18.0, 75.0))
        m2 = gov2.get_metrics()
        self.assertEqual(m2.status_tier, MemoryStatusTier.TIER_2_BALANCED)
        self.assertTrue(m2.is_safe)

        # Tier 3: Restricted (85% - 90% usage with headroom >= 2.5 GB)
        # 100 GB RAM, Cap = 90 GB. Used = 86 GB (86% usage), Headroom = 4.0 GB (>= 2.5 GB)
        gov3 = DynamicRAMGovernor(vmem_provider=lambda: make_mock_vmem(100.0, 86.0, 86.0))
        m3 = gov3.get_metrics()
        self.assertEqual(m3.status_tier, MemoryStatusTier.TIER_3_RESTRICTED)
        self.assertTrue(m3.is_safe)

        # Tier 4: Critical (>90% usage)
        gov4 = DynamicRAMGovernor(vmem_provider=lambda: make_mock_vmem(24.0, 22.0, 91.67))
        m4 = gov4.get_metrics()
        self.assertEqual(m4.status_tier, MemoryStatusTier.TIER_4_CRITICAL)
        self.assertFalse(m4.is_safe)

    def test_adv_2_2_headroom_floor_boundary_exact_decimal_precision(self):
        """
        Verify boundary condition on 24.0 GB host:
        Dynamic Cap = 24.0 * 0.90 = 21.60 GB.
        - Used = 19.100 GB -> Headroom = 2.500 GB (Safe)
        - Used = 19.101 GB -> Headroom = 2.499 GB (Unsafe -> Critical)
        """
        # Exactly 2.500 GB headroom
        gov_safe = DynamicRAMGovernor(
            max_ram_ratio=0.90,
            min_headroom_gb=2.50,
            vmem_provider=lambda: make_mock_vmem(24.0, 19.100, 79.58),
        )
        m_safe = gov_safe.get_metrics()
        self.assertAlmostEqual(m_safe.free_headroom_gb, 2.50, places=3)
        self.assertTrue(m_safe.is_safe)
        self.assertTrue(gov_safe.check_headroom())

        # 2.499 GB headroom (violation by 0.001 GB / 1 MB)
        gov_unsafe = DynamicRAMGovernor(
            max_ram_ratio=0.90,
            min_headroom_gb=2.50,
            vmem_provider=lambda: make_mock_vmem(24.0, 19.101, 79.59),
        )
        m_unsafe = gov_unsafe.get_metrics()
        self.assertLess(m_unsafe.free_headroom_gb, 2.50)
        self.assertFalse(m_unsafe.is_safe)
        self.assertFalse(gov_unsafe.check_headroom())
        self.assertEqual(m_unsafe.status_tier, MemoryStatusTier.TIER_4_CRITICAL)

    def test_adv_2_3_reclamation_healing_under_memory_pressure(self):
        """Verify enforce_safety_limits triggers memory reclamation and recovers if memory clears."""
        call_count = 0

        def dynamic_vmem():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First check: under pressure (22 GB used out of 24 GB)
                return make_mock_vmem(24.0, 22.0, 91.67)
            else:
                # After reclaim: memory cleared (14 GB used out of 24 GB)
                return make_mock_vmem(24.0, 14.0, 58.33)

        gov = DynamicRAMGovernor(vmem_provider=dynamic_vmem)
        # Should succeed because reclamation clears pressure on 2nd sample
        metrics = gov.enforce_safety_limits(auto_reclaim=True)
        self.assertTrue(metrics.is_safe)
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_1_OPTIMAL)
        self.assertGreaterEqual(call_count, 2)

    def test_adv_2_4_unresolved_memory_pressure_raises_memory_governor_error(self):
        """Verify MemoryGovernorError is raised when memory pressure persists after reclamation."""
        gov = DynamicRAMGovernor(
            max_ram_ratio=0.90,
            min_headroom_gb=2.50,
            vmem_provider=lambda: make_mock_vmem(24.0, 23.0, 95.83),
        )

        with self.assertRaises(MemoryGovernorError) as ctx:
            gov.enforce_safety_limits(auto_reclaim=True, max_wait_seconds=0.05, poll_interval=0.01)

        err_msg = str(ctx.exception)
        self.assertIn("Memory Governor Violation", err_msg)
        self.assertIn("95.8%", err_msg)
        self.assertIn("TIER_4_CRITICAL", err_msg)

    def test_adv_2_5_trainer_step_aborts_immediately_on_memory_governor_violation(self):
        """Verify MPSQLoRATrainer aborts before forward pass when memory governor is critical."""
        gov = DynamicRAMGovernor(
            vmem_provider=lambda: make_mock_vmem(24.0, 23.0, 95.83)
        )
        model = SimpleLinearModel(4, 1)
        config = MPSQLoRAConfig(device="cpu", auto_reclaim_cache=False)
        trainer = MPSQLoRATrainer(model=model, config=config, ram_governor=gov)

        batch = (torch.randn(2, 4), torch.randn(2, 1))
        with self.assertRaises(MemoryGovernorError):
            trainer.train_step(batch, step_idx=0)

    def test_adv_2_6_invalid_parameters_rejected_fast(self):
        """Verify governor constructor rejects invalid ratio and headroom bounds."""
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(max_ram_ratio=0.0)
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(max_ram_ratio=1.1)
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(min_headroom_gb=-0.1)


# ==============================================================================
# TEST SUITE 3: Corrupted Inputs, Malformed Python AST & Quarantine Routing
# ==============================================================================

class TestAdversarialASTAndCorruptedInputs(unittest.TestCase):
    """
    Stress tests for F5 (Dataset Ingestion) & F10 (AST Compiler Gate & Rule #0):
    - 0-byte JSONL files, whitespace-only files
    - Corrupted / truncated JSONL lines, binary gibberish recovery
    - MultiSchemaNormalizer rejection of incomplete / invalid schema records
    - AST Compiler Gate detection of Python syntax errors
    - Rule #0 Zero-Mock anti-pattern detection (MagicMock, fake_ecg, simulate_telemetry, etc.)
    - Rule #0 Empty function/class stub rejection
    - Proper isolation and disk writing to quarantine_anomalies.jsonl
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.quarantine_file = os.path.join(self.tmp_dir, "quarantine_anomalies.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_adv_3_1_zero_byte_and_whitespace_jsonl_ingestion(self):
        """Verify 0-byte file and whitespace-only file are safely loaded as empty lists without crashing."""
        empty_file = os.path.join(self.tmp_dir, "empty.jsonl")
        with open(empty_file, "w") as f:
            pass  # 0 bytes

        ws_file = os.path.join(self.tmp_dir, "whitespace.jsonl")
        with open(ws_file, "w") as f:
            f.write("\n   \n\t\n  \n")

        records_empty = DatasetIngestionEngine.load_jsonl(empty_file)
        records_ws = DatasetIngestionEngine.load_jsonl(ws_file)

        self.assertEqual(records_empty, [])
        self.assertEqual(records_ws, [])

    def test_adv_3_2_corrupted_jsonl_rows_graceful_skipping(self):
        """Verify JSONL loader recovers from broken JSON lines, bad escapes, and binary garbage."""
        corrupted_file = os.path.join(self.tmp_dir, "corrupted.jsonl")
        with open(corrupted_file, "wb") as f:
            # Valid line 1
            f.write(b'{"prompt": "valid prompt 1", "chosen": "c1", "rejected": "r1"}\n')
            # Corrupted line: unclosed brace
            f.write(b'{"prompt": "broken json line\n')
            # Corrupted line: raw binary gibberish
            f.write(b'\x80\x02\x03\xff\xfe\x00\n')
            # Valid line 2
            f.write(b'{"prompt": "valid prompt 2", "chosen": "c2", "rejected": "r2"}\n')
            # Corrupted line: trailing comma
            f.write(b'{"prompt": "bad", "chosen": "bad",}\n')

        records = DatasetIngestionEngine.load_jsonl(corrupted_file)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["prompt"], "valid prompt 1")
        self.assertEqual(records[1]["prompt"], "valid prompt 2")

    def test_adv_3_3_multischema_normalizer_rejects_missing_and_blank_fields(self):
        """Verify normalizer discards records with missing fields, empty strings, or wrong types."""
        invalid_dpos = [
            {},  # empty
            {"prompt": "hello"},  # missing chosen & rejected
            {"prompt": "hello", "chosen": "good"},  # missing rejected
            {"prompt": "  ", "chosen": "good", "rejected": "bad"},  # whitespace prompt
            {"prompt": "hello", "chosen": "", "rejected": "bad"},  # empty chosen
            {"prompt": "hello", "chosen": "good", "rejected": "   "},  # whitespace rejected
            {"turns": [{"role": "user"}]},  # invalid turns format
        ]
        for item in invalid_dpos:
            self.assertIsNone(MultiSchemaNormalizer.parse_dpo_record(item))

        invalid_sfts = [
            {},
            {"prompt": "only prompt"},
            {"messages": []},
            {"messages": [{"role": "user", "content": "hi"}]},  # missing assistant response
            {"instruction": "do this"},  # missing output / thought
        ]
        for item in invalid_sfts:
            self.assertIsNone(MultiSchemaNormalizer.parse_sft_record(item))

    def test_adv_3_4_ast_compiler_gate_detects_malformed_python_syntax(self):
        """Verify AST Compiler Gate flags syntax errors in code snippets."""
        bad_syntax_snippets = [
            "def broken_function(:",  # invalid syntax
            "if True\n    x = 1",  # missing colon
            "print('unclosed string",  # unclosed quote
            "def foo():\nreturn 42",  # invalid indentation
        ]
        for snippet in bad_syntax_snippets:
            is_valid, reason = ASTCompilerGate.validate_code_snippet(snippet)
            self.assertFalse(is_valid)
            self.assertIn("SYNTAX_ERROR", reason)

    def test_adv_3_5_ast_compiler_gate_detects_rule_0_mocks(self):
        """Verify AST Compiler Gate detects Rule #0 prohibited mock/dummy patterns."""
        mock_snippets = [
            ("from unittest.mock import MagicMock\nm = MagicMock()", "MagicMock"),
            ("import unittest.mock\n# test", "unittest.mock"),
            ("fake_ecg = [0.1, 0.2, 0.3]\n# simulated", "fake_ecg"),
            ("def test_it():\n    mock_data = {'temp': 36.5}", "mock_data"),
            ("def run():\n    payload = dummy_payload\n    return payload", "dummy_payload"),
            ("def get_data():\n    simulate_telemetry(100)", "simulate_telemetry"),
            ("fake_tensor = torch.zeros(10)", "fake_tensor"),
        ]
        for snippet, pattern_name in mock_snippets:
            is_valid, reason = ASTCompilerGate.validate_code_snippet(snippet)
            self.assertFalse(is_valid, f"Failed to catch mock pattern '{pattern_name}' in: {snippet}")
            self.assertIn("RULE_0_MOCK_DETECTED", reason)

    def test_adv_3_6_ast_compiler_gate_detects_empty_stubs(self):
        """Verify AST Compiler Gate detects empty function and class stubs."""
        stub_snippets = [
            ("def compute_tensor():\n    pass", "Function 'compute_tensor' contains only pass/ellipsis"),
            ("def calculate_ecg():\n    '''Compute ECG'''\n    ...", "Function 'calculate_ecg' contains only pass/ellipsis"),
            ("class DummyProcessor:\n    pass", "Class 'DummyProcessor' contains empty pass body"),
        ]
        for snippet, expected_err in stub_snippets:
            is_valid, reason = ASTCompilerGate.validate_code_snippet(snippet)
            self.assertFalse(is_valid)
            self.assertIn("RULE_0_EMPTY_STUB", reason)

        # But legitimate custom exceptions should be allowed:
        legit_exception = "class MyCustomError(Exception):\n    pass"
        is_valid, _ = ASTCompilerGate.validate_code_snippet(legit_exception)
        self.assertTrue(is_valid)

    def test_adv_3_7_filter_and_quarantine_routing_integrity(self):
        """Verify compliant records pass through while anomalous records are isolated to quarantine JSONL."""
        records = [
            {
                "prompt": "Write a function to compute factorial.",
                "chosen": "```python\ndef factorial(n: int) -> int:\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n```",
                "rejected": "I don't know.",
                "domain": "coding",
            },
            {
                "prompt": "Write a mock test.",
                "chosen": "```python\nfrom unittest.mock import MagicMock\nm = MagicMock()\n```",
                "rejected": "bad",
                "domain": "testing",
            },
            {
                "prompt": "Write broken python.",
                "chosen": "```python\ndef broken(\n```",
                "rejected": "bad",
                "domain": "coding",
            },
            {
                "prompt": "Write an empty stub.",
                "chosen": "```python\ndef empty_stub():\n    pass\n```",
                "rejected": "bad",
                "domain": "coding",
            },
        ]

        valid, quarantined = ASTCompilerGate.filter_and_quarantine(
            records, quarantine_path=self.quarantine_file
        )

        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["prompt"], "Write a function to compute factorial.")
        self.assertEqual(len(quarantined), 3)

        # Verify disk write to quarantine JSONL
        self.assertTrue(os.path.exists(self.quarantine_file))
        with open(self.quarantine_file, "r") as f:
            q_lines = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(q_lines), 3)
        self.assertIn("RULE_0_MOCK_DETECTED", q_lines[0]["_quarantine_reason"])
        self.assertIn("SYNTAX_ERROR", q_lines[1]["_quarantine_reason"])
        self.assertIn("RULE_0_EMPTY_STUB", q_lines[2]["_quarantine_reason"])

    def test_adv_3_8_dataset_loader_integration_with_quarantine(self):
        """Verify end-to-end get_dpo_dataloader parses valid rows, quarantines bad rows, and tokenizes cleanly."""
        raw_dataset_file = os.path.join(self.tmp_dir, "mixed_dataset.jsonl")
        with open(raw_dataset_file, "w") as f:
            f.write(json.dumps({
                "prompt": "Implement vector norm in Python.",
                "chosen": "```python\nimport math\ndef vec_norm(v: list) -> float:\n    return math.sqrt(sum(x**2 for x in v))\n```",
                "rejected": "norm is sum",
                "domain": "dsp",
            }) + "\n")
            f.write(json.dumps({
                "prompt": "Write simulated code.",
                "chosen": "```python\nfake_ecg = [1, 2, 3]\n```",
                "rejected": "bad",
                "domain": "biometrics",
            }) + "\n")

        tokenizer = MockTokenizer()
        dataloader = get_dpo_dataloader(
            records_or_paths=raw_dataset_file,
            tokenizer=tokenizer,
            batch_size=1,
            deduplicate=False,
            ast_validate=True,
        )

        batches = list(dataloader)
        self.assertEqual(len(batches), 1)  # Only the valid record is tokenized
        batch = batches[0]
        self.assertIn("prompt_input_ids", batch)
        self.assertIn("chosen_input_ids", batch)
        self.assertIn("rejected_input_ids", batch)


# ==============================================================================
# TEST SUITE 4: Server Reload Flapping & Consecutive Health Checks
# ==============================================================================

class TestAdversarialServerReloadFlapping(unittest.TestCase):
    """
    Stress tests for F15 (Inference Server Hot-Reload Sentinel):
    - Rapid flapping status responses (e.g. 200, 500, 200, 200, 500, 200, 200, 200)
    - Consecutive health check reset on any non-200 probe
    - Failure to reach required consecutive probes stays on fallback route (8081)
    - Successful consecutive pass restores primary route (8082)
    - Boundary checking on port parameters
    """

    def test_adv_4_1_flapping_sequence_requires_consecutive_successes(self):
        """Verify that a flapping server resets the consecutive count until 3 contiguous 200 OKs occur."""
        sentinel = ServerReloadSentinel(
            required_consecutive_probes=3,
            probe_interval_sec=0.01,
            max_reload_wait_sec=2.0,
        )

        # Flapping sequence:
        # [200, 500, 200, 200, 500, 200, 200, 200]
        # P1: 200 (count=1)
        # P2: 500 (count=0)
        # P3: 200 (count=1)
        # P4: 200 (count=2)
        # P5: 500 (count=0)
        # P6: 200 (count=1)
        # P7: 200 (count=2)
        # P8: 200 (count=3) -> PASS!
        sequence = [
            {"code": 200, "status": "HEALTHY"},
            {"code": 500, "status": "UNHEALTHY"},
            {"code": 200, "status": "HEALTHY"},
            {"code": 200, "status": "HEALTHY"},
            {"code": 500, "status": "UNHEALTHY"},
            {"code": 200, "status": "HEALTHY"},
            {"code": 200, "status": "HEALTHY"},
            {"code": 200, "status": "HEALTHY"},
        ]
        probe_idx = 0

        def mock_flapping_probe(port: int) -> Dict[str, Any]:
            nonlocal probe_idx
            res = sequence[min(probe_idx, len(sequence) - 1)]
            probe_idx += 1
            return dict(res)

        is_healthy, consecutive_passed, probe_log = sentinel.wait_for_service_health(
            port=PORT_PRIMA_PRP,
            required_consecutive=3,
            timeout_sec=2.0,
            probe_fn=mock_flapping_probe,
        )

        self.assertTrue(is_healthy)
        self.assertEqual(consecutive_passed, 3)
        self.assertEqual(len(probe_log), 8)

    def test_adv_4_2_unstable_flapping_fails_and_maintains_fallback_route(self):
        """Verify that persistent flapping causes reload failure and route remains safely on fallback (8081)."""
        sentinel = ServerReloadSentinel(
            required_consecutive_probes=3,
            probe_interval_sec=0.01,
            max_reload_wait_sec=0.10,
        )

        # Alternating flapping: 200, 503, 200, 503 ... (never reaches 3 consecutive)
        state = False

        def alternating_flapping_probe(port: int) -> Dict[str, Any]:
            nonlocal state
            state = not state
            if state:
                return {"code": 200, "status": "HEALTHY"}
            else:
                return {"code": 503, "status": "UNHEALTHY"}

        result = sentinel.reload_inference_cluster(
            new_gguf_path="models/qwen38_merged.gguf",
            target_port=PORT_PRIMA_PRP,
            probe_fn=alternating_flapping_probe,
        )

        self.assertEqual(result["status"], "FAILED_PRIMARY_RELOAD")
        self.assertIn("failed to reach 3 consecutive healthy probes", result["error"])
        # Crucial safety invariant: Active route MUST stay on fallback port 8081!
        self.assertEqual(sentinel.active_route, PORT_LLAMA_RPC)
        self.assertTrue(sentinel.is_failover_active)

    def test_adv_4_3_successful_reload_restores_primary_route(self):
        """Verify successful hot-reload recovers from startup errors and safely restores route to 8082."""
        sentinel = ServerReloadSentinel(
            required_consecutive_probes=3,
            probe_interval_sec=0.01,
            max_reload_wait_sec=1.0,
        )

        # Sequence: Initial connection refused, then 503 starting up, then 3 consecutive 200 OKs
        seq = [
            {"code": 0, "status": "CONNECTION_REFUSED"},
            {"code": 503, "status": "UNHEALTHY"},
            {"code": 200, "status": "HEALTHY"},
            {"code": 200, "status": "HEALTHY"},
            {"code": 200, "status": "HEALTHY"},
        ]
        seq_idx = 0

        def recovery_probe(port: int) -> Dict[str, Any]:
            nonlocal seq_idx
            res = seq[min(seq_idx, len(seq) - 1)]
            seq_idx += 1
            return dict(res)

        result = sentinel.reload_inference_cluster(
            new_gguf_path="models/smollm2_17b_merged.gguf",
            target_port=PORT_PRIMA_PRP,
            probe_fn=recovery_probe,
        )

        self.assertEqual(result["status"], "RELOADED")
        self.assertIsNone(result["error"])
        self.assertEqual(sentinel.active_route, PORT_PRIMA_PRP)
        self.assertFalse(sentinel.is_failover_active)
        self.assertEqual(result["health_probes_passed"], 3)

    def test_adv_4_4_invalid_inputs_and_port_boundaries(self):
        """Verify validation contracts on invalid model paths and port numbers."""
        sentinel = ServerReloadSentinel()

        # Invalid model paths
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("")
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("model.bin")  # not .gguf

        # Invalid port numbers
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("model.gguf", target_port=0)
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("model.gguf", target_port=70000)

        # Invalid port in probe_health
        bad_port_res = sentinel.probe_health(port=-1)
        self.assertEqual(bad_port_res["status"], "INVALID_PORT")


if __name__ == "__main__":
    unittest.main()
