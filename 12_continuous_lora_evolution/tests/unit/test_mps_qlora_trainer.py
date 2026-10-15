"""
Unit Tests for Apple Silicon Metal QLoRA Trainer & Memory Governor (Features F1, F2, F3, F4).

Tests:
- F1: MPS Device Resolution, Precision Engine (Float16/BFloat16/Float32), PEFT LoRA Integration
- F2: Gradient Stability, Strict Norm Clipping (<= 1.0), 0 NaN/Inf Assertions
- F3: Micro-Batching, Exact Gradient Accumulation Math, Effective Batch Size, Flush Gradients
- F4: Dynamic RAM Sentinel Integration, Proactive Cache Eviction, Metrics Serialization
- Checkpointing, Multi-format Batches, Evaluation Loop, Full Epoch Fit
"""

import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from src.trainer.dynamic_ram_governor import DynamicRAMGovernor, MemoryMetrics, MemoryStatusTier
from src.trainer.mps_qlora_trainer import (
    EpochResult,
    MPSQLoRAConfig,
    MPSQLoRATrainer,
    StepResult,
    TrainingSummary,
)


class DummyLinearModel(nn.Module):
    """Simple linear model for deterministic unit tests."""
    def __init__(self, in_features: int = 16, out_features: int = 4):
        super().__init__()
        self.fc1 = nn.Linear(in_features, 32)
        self.fc2 = nn.Linear(32, out_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = torch.relu(self.fc1(x))
        return self.fc2(h)


class DummyCausalLM(nn.Module):
    """Emulates a HuggingFace CausalLM model returning an object with .loss."""
    def __init__(self, vocab_size: int = 64, hidden_dim: int = 16):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.lm_head = nn.Linear(hidden_dim, vocab_size)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: torch.Tensor = None,
        attention_mask: torch.Tensor = None,
    ) -> Any:
        emb = self.embedding(input_ids)
        logits = self.lm_head(emb)
        loss = None
        if labels is not None:
            # Shift tokens for autoregressive loss
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = nn.functional.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
            )
        return SimpleNamespace(logits=logits, loss=loss)


class TestMPSQLoRATrainer(unittest.TestCase):
    """Comprehensive test suite for MPSQLoRATrainer."""

    def setUp(self):
        torch.manual_seed(42)
        self.mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        self.target_device = "mps" if self.mps_available else "cpu"

    # -------------------------------------------------------------------------
    # F1: Device Accelerator & Precision Engine Tests
    # -------------------------------------------------------------------------

    def test_device_resolution(self):
        """Verify device resolution selects MPS when available, or falls back to CPU."""
        config = MPSQLoRAConfig(device=self.target_device)
        trainer = MPSQLoRATrainer(config=config)
        self.assertEqual(trainer.device.type, self.target_device)

        # Test fallback for invalid/unavailable device
        trainer_fallback = MPSQLoRATrainer(config=MPSQLoRAConfig(device="non_existent_accelerator"))
        self.assertEqual(trainer_fallback.device.type, "cpu")

    def test_precision_dtypes(self):
        """Verify Float16, BFloat16, and Float32 precision resolution."""
        t_fp16 = MPSQLoRATrainer(config=MPSQLoRAConfig(precision="float16"))
        self.assertEqual(t_fp16.dtype, torch.float16)

        t_bf16 = MPSQLoRATrainer(config=MPSQLoRAConfig(precision="bfloat16"))
        self.assertEqual(t_bf16.dtype, torch.bfloat16)

        t_fp32 = MPSQLoRATrainer(config=MPSQLoRAConfig(precision="float32"))
        self.assertEqual(t_fp32.dtype, torch.float32)

        with self.assertRaises(ValueError):
            MPSQLoRATrainer(config=MPSQLoRAConfig(precision="int8"))

    def test_peft_lora_parameter_isolation(self):
        """Verify PEFT LoRA freezes base model parameters and enables only adapter weights."""
        model = DummyLinearModel(16, 4)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            lora_r=4,
            lora_alpha=8,
            lora_target_modules=["fc1", "fc2"],
            lora_dropout=0.0,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)
        trainer.prepare_peft_lora()

        stats = trainer.get_parameter_stats()
        self.assertGreater(stats["total_params"], 0)
        self.assertGreater(stats["trainable_params"], 0)
        self.assertLess(stats["trainable_params"], stats["total_params"])
        self.assertLess(stats["trainable_pct"], 100.0)

        # Verify base linear weights have requires_grad=False
        for name, param in trainer.model.named_parameters():
            if "lora" not in name.lower():
                self.assertFalse(param.requires_grad, f"Base parameter {name} should be frozen!")

    def test_forward_backward_on_mps_precision(self):
        """Verify forward and backward matmul operations execute with Float16/BFloat16 precision."""
        device = torch.device(self.target_device)
        dtype = torch.float16 if self.mps_available else torch.float32

        model = DummyLinearModel(16, 4)
        config = MPSQLoRAConfig(device=self.target_device, precision="float16" if self.mps_available else "float32")
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.randn(2, 16, dtype=dtype)
        y = torch.randn(2, 4, dtype=dtype)
        step_res = trainer.train_step((x, y), step_idx=0)

        self.assertFalse(math.isnan(step_res.unscaled_loss))
        self.assertGreater(step_res.unscaled_loss, 0.0)

    # -------------------------------------------------------------------------
    # F2: Gradient Stability & Norm Clipper Tests
    # -------------------------------------------------------------------------

    def test_strict_gradient_norm_clipping(self):
        """Verify that gradient norms are strictly clamped to max_grad_norm <= 1.0."""
        # Create a model with huge loss gradient
        model = DummyLinearModel(8, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            max_grad_norm=1.0,
            gradient_accumulation_steps=1,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Large input and target to induce large gradients > 10.0
        x = torch.randn(4, 8) * 100.0
        y = torch.randn(4, 2) * 100.0

        step_res = trainer.train_step((x, y), step_idx=0)
        self.assertTrue(step_res.optimizer_stepped)
        self.assertIsNotNone(step_res.grad_norm_before_clip)
        self.assertIsNotNone(step_res.grad_norm_after_clip)
        
        # Invariant: clipped gradient norm must be <= max_grad_norm + epsilon
        self.assertLessEqual(step_res.grad_norm_after_clip, 1.0001)

    def test_fail_fast_on_nan_loss(self):
        """Verify that NaN loss triggers FloatingPointError when fail_on_nan=True."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(device="cpu", precision="float32", fail_on_nan=True)
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Input with NaNs
        x = torch.tensor([[float("nan"), 1.0, 2.0, 3.0]])
        y = torch.tensor([[1.0, 0.0]])

        with self.assertRaises(FloatingPointError):
            trainer.train_step((x, y), step_idx=0)

    def test_graceful_skip_on_nan_loss_when_not_fail_fast(self):
        """Verify that NaN loss is skipped gracefully when fail_on_nan=False."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(device="cpu", precision="float32", fail_on_nan=False)
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.tensor([[float("nan"), 1.0, 2.0, 3.0]])
        y = torch.tensor([[1.0, 0.0]])

        step_res = trainer.train_step((x, y), step_idx=0)
        self.assertTrue(step_res.skipped_nan_step)
        self.assertFalse(step_res.optimizer_stepped)
        self.assertEqual(trainer.total_skipped_nan_steps, 1)

    def test_non_finite_gradient_detection(self):
        """Verify detection and handling of non-finite gradients (Inf/NaN)."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            fail_on_nan=False,
            gradient_accumulation_steps=1,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Custom loss function injecting inf gradients
        def bad_loss_fn(m, b):
            out = m(b[0])
            # Inject inf manually into a weight gradient after backward
            loss = out.sum()
            return loss

        trainer.loss_fn = bad_loss_fn
        x = torch.randn(1, 4)
        y = torch.randn(1, 2)

        # Hook to corrupt gradient
        def corrupt_grad_hook(grad):
            return torch.full_like(grad, float("inf"))

        handle = model.fc2.weight.register_hook(corrupt_grad_hook)
        try:
            step_res = trainer.train_step((x, y), step_idx=0)
            self.assertTrue(step_res.skipped_nan_step)
            self.assertFalse(step_res.optimizer_stepped)
        finally:
            handle.remove()

    def test_loss_monotonically_decreases_on_fit(self):
        """Verify that training on a fixed synthetic dataset monotonically reduces loss."""
        torch.manual_seed(123)
        model = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            learning_rate=1e-2,
            gradient_accumulation_steps=1,
            max_epochs=10,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Fixed linear relationship: y = sum(x)
        x_data = torch.randn(32, 8)
        y_data = x_data.sum(dim=1, keepdim=True)
        dataset = TensorDataset(x_data, y_data)
        dataloader = DataLoader(dataset, batch_size=8, shuffle=False)

        summary = trainer.fit(dataloader)
        self.assertLess(summary.final_loss, summary.initial_loss)
        self.assertTrue(summary.loss_monotonic_decrease)

    # -------------------------------------------------------------------------
    # F3: Micro-Batching & Gradient Accumulator Tests
    # -------------------------------------------------------------------------

    def test_effective_batch_size_calculation(self):
        """Verify effective batch size equals micro_batch_size * gradient_accumulation_steps."""
        config = MPSQLoRAConfig(micro_batch_size=2, gradient_accumulation_steps=8)
        trainer = MPSQLoRATrainer(config=config)
        self.assertEqual(trainer.effective_batch_size, 16)

    def test_gradient_accumulation_step_execution(self):
        """Verify optimizer only steps on accumulation boundaries."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            gradient_accumulation_steps=4,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.randn(1, 4)
        y = torch.randn(1, 2)

        # Steps 0, 1, 2 should not trigger optimizer step
        r0 = trainer.train_step((x, y), step_idx=0)
        self.assertFalse(r0.is_accumulation_step)
        self.assertFalse(r0.optimizer_stepped)

        r1 = trainer.train_step((x, y), step_idx=1)
        self.assertFalse(r1.is_accumulation_step)
        self.assertFalse(r1.optimizer_stepped)

        r2 = trainer.train_step((x, y), step_idx=2)
        self.assertFalse(r2.is_accumulation_step)
        self.assertFalse(r2.optimizer_stepped)

        # Step 3 (4th micro-batch) MUST trigger accumulation step and optimizer step
        r3 = trainer.train_step((x, y), step_idx=3)
        self.assertTrue(r3.is_accumulation_step)
        self.assertTrue(r3.optimizer_stepped)
        self.assertIsNotNone(r3.grad_norm_after_clip)

    def test_scaled_loss_math_exactness(self):
        """Verify scaled_loss is exactly unscaled_loss / gradient_accumulation_steps."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            gradient_accumulation_steps=5,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.randn(1, 4)
        y = torch.randn(1, 2)
        r = trainer.train_step((x, y), step_idx=0)
        self.assertAlmostEqual(r.scaled_loss, r.unscaled_loss / 5.0, places=5)

    def test_flush_gradients(self):
        """Verify flush_gradients applies unapplied trailing micro-batches."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            gradient_accumulation_steps=4,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.randn(1, 4)
        y = torch.randn(1, 2)

        # Run 2 micro-steps
        trainer.train_step((x, y), step_idx=0)
        trainer.train_step((x, y), step_idx=1)

        # Flush should execute optimizer step
        norm = trainer.flush_gradients()
        self.assertIsNotNone(norm)
        self.assertLessEqual(norm, 1.0001)

    # -------------------------------------------------------------------------
    # F4: Dynamic RAM Governor Integration & Checkpoint Tests
    # -------------------------------------------------------------------------

    def test_ram_governor_enforcement_during_step(self):
        """Verify RAM governor is queried and returns metrics in StepResult."""
        model = DummyLinearModel(4, 2)
        config = MPSQLoRAConfig(device="cpu", precision="float32")
        gov = DynamicRAMGovernor()
        trainer = MPSQLoRATrainer(model=model, config=config, ram_governor=gov)

        x = torch.randn(1, 4)
        y = torch.randn(1, 2)
        step_res = trainer.train_step((x, y), step_idx=0)

        self.assertIsNotNone(step_res.memory_metrics)
        self.assertIsInstance(step_res.memory_metrics, MemoryMetrics)
        self.assertTrue(step_res.memory_metrics.is_safe)

    def test_checkpoint_save_and_load(self):
        """Verify checkpoint saving and loading restores weights and state accurately."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            model = DummyLinearModel(4, 2)
            config = MPSQLoRAConfig(
                device="cpu",
                precision="float32",
                learning_rate=0.01,
            )
            trainer = MPSQLoRATrainer(model=model, config=config)

            x = torch.randn(2, 4)
            y = torch.randn(2, 2)
            trainer.train_step((x, y), step_idx=0)

            # Save checkpoint
            save_path = trainer.save_checkpoint(tmp_dir, metadata={"epoch": 1, "custom_tag": "test"})
            self.assertTrue((Path(tmp_dir) / "trainer_state.json").exists())
            self.assertTrue((Path(tmp_dir) / "model.pt").exists())

            # Load checkpoint into new trainer
            model_loaded = DummyLinearModel(4, 2)
            trainer_new = MPSQLoRATrainer(model=model_loaded, config=config)
            loaded_state = trainer_new.load_checkpoint(tmp_dir)

            self.assertEqual(loaded_state["metadata"]["custom_tag"], "test")
            self.assertEqual(trainer_new.global_step, 1)

    def test_causal_lm_dict_batch_and_evaluation(self):
        """Verify CausalLM forward with dict input and evaluate() method."""
        model = DummyCausalLM(vocab_size=32, hidden_dim=16)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            gradient_accumulation_steps=2,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        # Batch dict format
        input_ids = torch.randint(0, 32, (4, 10))
        labels = input_ids.clone()
        batch = {"input_ids": input_ids, "labels": labels}

        # Step
        r0 = trainer.train_step(batch, step_idx=0)
        self.assertFalse(math.isnan(r0.unscaled_loss))

        # Eval
        dataset = [{"input_ids": input_ids, "labels": labels} for _ in range(3)]
        eval_loader = DataLoader(dataset, batch_size=1)
        eval_metrics = trainer.evaluate(eval_loader)

        self.assertIn("eval_loss", eval_metrics)
        self.assertIn("eval_batches", eval_metrics)
        self.assertEqual(eval_metrics["eval_batches"], 3)
    def test_peft_lora_auto_discover_target_modules(self):
        """Verify prepare_peft_lora automatically discovers linear layers when target_modules is None."""
        model = DummyLinearModel(16, 4)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            lora_r=4,
            lora_alpha=8,
            lora_target_modules=None,  # Not provided
        )
        trainer = MPSQLoRATrainer(model=model, config=config)
        peft_model = trainer.prepare_peft_lora()
        self.assertIsNotNone(peft_model)
        stats = trainer.get_parameter_stats()
        self.assertGreater(stats["trainable_params"], 0)
        self.assertLess(stats["trainable_params"], stats["total_params"])

    def test_bfloat16_precision_execution(self):
        """Verify train_step execution with bfloat16 precision."""
        model = DummyLinearModel(8, 2)
        config = MPSQLoRAConfig(device="cpu", precision="bfloat16", gradient_accumulation_steps=1)
        trainer = MPSQLoRATrainer(model=model, config=config)

        x = torch.randn(2, 8, dtype=torch.bfloat16)
        y = torch.randn(2, 2, dtype=torch.bfloat16)
        step_res = trainer.train_step((x, y), step_idx=0)
        self.assertTrue(step_res.optimizer_stepped)
        self.assertFalse(math.isnan(step_res.unscaled_loss))

    def test_custom_loss_fn(self):
        """Verify custom loss_fn callable is invoked during training and evaluation."""
        model = DummyLinearModel(8, 2)
        config = MPSQLoRAConfig(device="cpu", precision="float32")
        
        loss_calls = 0
        def custom_loss(m, batch):
            nonlocal loss_calls
            loss_calls += 1
            x, y = batch
            preds = m(x)
            return ((preds - y) ** 2).mean()

        trainer = MPSQLoRATrainer(model=model, config=config, loss_fn=custom_loss)
        x = torch.randn(2, 8)
        y = torch.randn(2, 2)
        trainer.train_step((x, y), step_idx=0)
        self.assertEqual(loss_calls, 1)

    def test_parameter_stats_empty_and_all_frozen(self):
        """Verify get_parameter_stats handles empty models or all frozen parameters."""
        empty_trainer = MPSQLoRATrainer()
        stats_empty = empty_trainer.get_parameter_stats()
        self.assertEqual(stats_empty["total_params"], 0)
        self.assertEqual(stats_empty["trainable_params"], 0)

        model = DummyLinearModel(4, 2)
        for p in model.parameters():
            p.requires_grad = False
        trainer = MPSQLoRATrainer(model=model)
        stats = trainer.get_parameter_stats()
        self.assertEqual(stats["trainable_params"], 0)
        self.assertEqual(stats["trainable_pct"], 0.0)

    def test_load_checkpoint_missing_dir_raises(self):
        """Verify load_checkpoint raises FileNotFoundError for missing directory."""
        trainer = MPSQLoRATrainer()
        with self.assertRaises(FileNotFoundError):
            trainer.load_checkpoint("/non/existent/checkpoint/directory")

    def test_multi_epoch_fit_detailed_history(self):
        """Verify fit() across multiple epochs aggregates history and summary correctly."""
        model = DummyLinearModel(8, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            micro_batch_size=2,
            gradient_accumulation_steps=2,
            max_epochs=2,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)

        x_data = torch.randn(8, 8)
        y_data = torch.randn(8, 2)
        dataset = TensorDataset(x_data, y_data)
        loader = DataLoader(dataset, batch_size=2)

        summary = trainer.fit(loader, num_epochs=2)
        self.assertIsInstance(summary, TrainingSummary)
        self.assertEqual(summary.total_epochs, 2)
        self.assertEqual(len(summary.epoch_summaries), 2)
        self.assertEqual(len(trainer.training_history), 2)

    def test_mps_hardware_acceleration_if_available(self):
        """Verify real MPS acceleration when run on Apple Silicon hardware."""
        if not self.mps_available:
            self.skipTest("MPS hardware acceleration not available in this environment.")

        model = DummyLinearModel(16, 4)
        config = MPSQLoRAConfig(device="mps", precision="float16", gradient_accumulation_steps=1)
        trainer = MPSQLoRATrainer(model=model, config=config)
        trainer.prepare_peft_lora()

        self.assertEqual(trainer.device.type, "mps")
        self.assertEqual(trainer.dtype, torch.float16)

        x = torch.randn(4, 16)
        y = torch.randn(4, 4)
        res = trainer.train_step((x, y), step_idx=0)
        self.assertTrue(res.optimizer_stepped)
        self.assertFalse(math.isnan(res.unscaled_loss))
        self.assertLessEqual(res.grad_norm_after_clip, 1.0001)


if __name__ == "__main__":
    unittest.main()
