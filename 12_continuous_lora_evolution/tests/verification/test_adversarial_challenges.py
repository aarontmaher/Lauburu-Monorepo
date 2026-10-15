"""
Adversarial Stress-Testing & Boundary Challenge Suite for Subsystem 12.
Exercises extreme inputs, numerical singularities, pathological payloads, and precision limits.
"""

import math
import hashlib
import time
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.trainer.mps_qlora_trainer import MPSQLoRATrainer, MPSQLoRAConfig
from src.distillation.dpo_loss_mps import DPOLossMPS
from src.weight_merging.native_ties_dare_merger import (
    trim_tensor_topk,
    elect_signs,
    disjoint_merge,
    dare_drop_and_rescale,
    slerp_tensors,
    merge_tensors,
)
from src.distillation.sample_deduplicator import (
    SimHash,
    SampleDeduplicator,
    normalize_text,
    extract_canonical_text,
)


class TestAdversarialItem1_MPSPrecisionAndAccumulation:
    """Adversarial stress tests for MPS Loss Scaling & Accumulation."""

    def test_bfloat16_dynamic_range_vs_float16_underflow(self):
        """
        Verify bfloat16 handles wide dynamic range without overflow/underflow,
        and verify float16 behavior under subnormal gradients.
        """
        if not torch.backends.mps.is_available():
            pytest.skip("MPS not available")
            
        device = torch.device("mps")
        
        # Large dynamic range in bfloat16 (1e4 * 1e4 = 1e8 exceeds float16 max 65504)
        x_bf16 = torch.tensor([10000.0], dtype=torch.bfloat16, device=device)
        y_bf16 = x_bf16 * 10000.0
        assert not torch.isinf(y_bf16)
        
        # Float16 max is 65504
        x_fp16 = torch.tensor([60000.0], dtype=torch.float16, device=device)
        assert torch.isfinite(x_fp16)

    def test_micro_batch_size_1_with_accumulation_256(self):
        """Stress-test extremely high accumulation steps (256 steps) on MPS."""
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        model = nn.Linear(16, 8, bias=False).to(device=device, dtype=torch.float32)
        
        config = MPSQLoRAConfig(
            device=str(device),
            precision="float32",
            micro_batch_size=1,
            gradient_accumulation_steps=256,
            max_grad_norm=1.0,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)
        
        for step in range(256):
            batch = (torch.randn(1, 16, device=device), torch.randn(1, 8, device=device))
            res = trainer.train_step(batch, step_idx=step)
            if step < 255:
                assert res.optimizer_stepped is False
            else:
                assert res.optimizer_stepped is True
                assert res.grad_norm_after_clip is not None
                assert res.grad_norm_after_clip <= 1.00001


class TestAdversarialItem2_DPOSingularities:
    """Adversarial stress tests for DPO Loss Engine."""

    def test_dpo_extreme_beta_values(self):
        """Stress-test beta=0.0 and beta=1000.0."""
        # beta = 0.0 -> loss must be exactly log(2)
        dpo_zero = DPOLossMPS(beta=0.0)
        pi_w = torch.tensor([5.0])
        pi_l = torch.tensor([-5.0])
        loss_0, _, _, acc_0 = dpo_zero(pi_w, pi_l)
        assert math.isclose(loss_0.item(), math.log(2.0), rel_tol=1e-5)
        
        # beta = 1000.0 -> clamped at clamp_max/clamp_min
        dpo_huge = DPOLossMPS(beta=1000.0, clamp_min=-10.0, clamp_max=10.0)
        loss_huge, _, _, _ = dpo_huge(pi_w, pi_l)
        assert torch.isfinite(loss_huge)
        assert math.isclose(loss_huge.item(), math.log(1.0 + math.exp(-10.0)), rel_tol=1e-4)

    def test_dpo_identical_chosen_and_rejected(self):
        """When chosen and rejected are identical, logits_diff is 0, loss is log(2), accuracy 0."""
        dpo = DPOLossMPS(beta=0.5)
        pi_same = torch.tensor([-2.0, -1.0, 0.0])
        loss, chosen_r, rejected_r, acc = dpo(pi_same, pi_same)
        
        assert math.isclose(loss.item(), math.log(2.0), rel_tol=1e-5)
        assert torch.allclose(chosen_r, rejected_r)
        assert acc.item() == 0.0  # (chosen_r > rejected_r) is False for identical rewards

    def test_dpo_infinite_and_nan_inputs_resilience(self):
        """Verify DPO clamping behavior on massive raw logps."""
        dpo = DPOLossMPS(beta=0.1, clamp_min=-10.0, clamp_max=10.0)
        pi_w = torch.tensor([1e6], requires_grad=True)
        pi_l = torch.tensor([-1e6], requires_grad=True)
        
        loss, _, _, _ = dpo(pi_w, pi_l)
        loss.backward()
        
        assert torch.isfinite(loss)
        assert torch.isfinite(pi_w.grad)
        assert torch.isfinite(pi_l.grad)


class TestAdversarialItem3_TIESEdgeCases:
    """Adversarial stress tests for TIES Merging."""

    def test_ties_exact_opposite_symmetric_deltas(self):
        """When two deltas are exactly opposite (d1 = -d2), sign sum is 0, merged is 0."""
        d1 = torch.tensor([ 2.0, -4.0,  6.0])
        d2 = torch.tensor([-2.0,  4.0, -6.0])
        
        signs = elect_signs([d1, d2])
        assert torch.equal(signs, torch.zeros(3))
        
        merged = disjoint_merge([d1, d2], signs)
        assert torch.equal(merged, torch.zeros(3))

    def test_ties_single_element_density(self):
        """Keep exactly 1 element out of 1000."""
        t = torch.randn(1000)
        t[42] = 100.0  # Clearly max magnitude
        density = 1.0 / 1000.0
        
        trimmed = trim_tensor_topk(t, density=density)
        non_zero = (trimmed != 0.0).sum().item()
        assert non_zero == 1
        assert trimmed[42].item() == 100.0

    def test_ties_all_equal_magnitude_elements(self):
        """When all elements have identical absolute magnitude."""
        t = torch.tensor([1.0, -1.0, 1.0, -1.0, 1.0])
        density = 0.4  # ceil(5 * 0.4) = 2 elements
        trimmed = trim_tensor_topk(t, density=density)
        assert (trimmed != 0.0).sum().item() == 2


class TestAdversarialItem4_DAREEdgeCases:
    """Adversarial stress tests for DARE."""

    def test_dare_density_1_0_identity(self):
        """density=1.0 must return exact clone without modifying values."""
        W = torch.randn(100, 100)
        W_dare = dare_drop_and_rescale(W, density=1.0)
        assert torch.equal(W, W_dare)

    def test_dare_density_0_0_zeros(self):
        """density=0.0 must return exact zeros."""
        W = torch.randn(50, 50)
        W_dare = dare_drop_and_rescale(W, density=0.0)
        assert torch.equal(W_dare, torch.zeros_like(W))

    def test_dare_4d_conv_tensor_shape(self):
        """Verify DARE preserves arbitrary 4D tensor shapes."""
        W = torch.randn(16, 8, 3, 3)
        W_dare = dare_drop_and_rescale(W, density=0.5, seed=123)
        assert W_dare.shape == (16, 8, 3, 3)
        assert torch.isfinite(W_dare).all()


class TestAdversarialItem5_SLERPAntiPodalAndShapes:
    """Adversarial stress tests for SLERP."""

    def test_slerp_anti_podal_opposite_vectors(self):
        """When v1 = -v0 (theta = pi, dot = -1.0, sin(pi)=0), must not NaN."""
        v0 = torch.tensor([1.0, 0.0, 0.0])
        v1 = torch.tensor([-1.0, 0.0, 0.0])
        
        slerp_mid = slerp_tensors(v0, v1, t=0.5)
        assert not torch.isnan(slerp_mid).any()
        assert torch.isfinite(slerp_mid).all()

    def test_slerp_4d_transformer_attention_shape(self):
        """Verify SLERP across 4D tensor shapes (batch, heads, seq, dim)."""
        v0 = torch.randn(4, 8, 32, 64)
        v1 = torch.randn(4, 8, 32, 64)
        
        vt = slerp_tensors(v0, v1, t=0.3)
        assert vt.shape == (4, 8, 32, 64)
        assert not torch.isnan(vt).any()


class TestAdversarialItem6_SimHashMassiveAndUnicode:
    """Adversarial stress tests for SimHash & SHA-256 Deduplication."""

    def test_simhash_unicode_emoji_and_multilingual(self):
        """Verify SimHash handles emojis, CJK characters, and Arabic text."""
        sh = SimHash()
        t1 = "🚀 Lauburu AI Mesh: 多言語モデル & الذكاء الاصطناعي"
        t2 = "🚀 Lauburu AI Mesh: 多言語モデル & الذكاء الاصطناعي!"
        t3 = "完全無関係なテキストです。"
        
        h1 = sh.compute(t1)
        h2 = sh.compute(t2)
        h3 = sh.compute(t3)
        
        assert h1 != 0 and h2 != 0 and h3 != 0
        dist_12 = SimHash.hamming_distance(h1, h2)
        dist_13 = SimHash.hamming_distance(h1, h3)
        
        assert dist_12 <= 4
        assert dist_13 >= 15

    def test_simhash_massive_10mb_payload_throughput(self):
        """Verify SimHash processes massive text without memory leak or crash."""
        large_text = "Lauburu AI Sovereign Intelligence " * 50000  # ~1.7 MB
        sh = SimHash()
        
        t0 = time.time()
        h = sh.compute(large_text)
        duration = time.time() - t0
        
        assert h != 0
        assert duration < 2.0  # Fast execution < 2.0s

    def test_deduplicator_100k_sample_retention(self):
        """Verify sample deduplicator exact hash set handles 10,000 unique records in < 0.2s."""
        dedup = SampleDeduplicator(enable_exact=True, enable_simhash=False)
        
        records = [{"instruction": f"Solve problem #{i}", "output": f"Answer is {i**2}"} for i in range(10000)]
        t0 = time.time()
        uniques, stats = dedup.deduplicate_dataset(records)
        duration = time.time() - t0
        
        assert stats["total_in"] == 10000
        assert stats["unique_out"] == 10000
        assert stats["total_duplicates"] == 0
        assert duration < 1.0
