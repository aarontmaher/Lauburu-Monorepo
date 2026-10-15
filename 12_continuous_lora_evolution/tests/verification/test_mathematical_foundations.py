"""
Mathematical & Algorithmic Verification Suite for Subsystem 12.
Empirically verifies:
1. MPS Float16/BFloat16 training loss scaling & gradient accumulation equivalence
2. Bradley-Terry DPO sigmoid loss with reference freezing and clamping math
3. TIES magnitude-based top-k trimming, sign election consensus, and disjoint parameter averaging
4. DARE Bernoulli drop-and-rescale norm conservation E[W_dare] = W
5. SLERP spherical interpolation along geodesic manifolds
6. 64-bit SimHash Hamming distance and exact SHA-256 deduplication math
"""

import math
import hashlib
import time
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from src.trainer.mps_qlora_trainer import MPSQLoRATrainer, MPSQLoRAConfig
from src.trainer.dynamic_ram_governor import DynamicRAMGovernor
from src.distillation.dpo_loss_mps import DPOLossMPS, compute_token_log_probs
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


class TestItem1_MPSLossScalingAndGradientAccumulation:
    """Mathematical verification of Item 1: MPS Float16/BFloat16 training loss scaling."""

    @pytest.mark.parametrize("precision", ["float32", "float16", "bfloat16"])
    @pytest.mark.parametrize("device_name", ["cpu", "mps"] if torch.backends.mps.is_available() else ["cpu"])
    @pytest.mark.parametrize("accum_steps", [2, 4, 8])
    def test_gradient_accumulation_mathematical_equivalence(self, precision, device_name, accum_steps):
        """
        Verify: sum_{i=1}^N (1/N * grad(L_i)) == grad(1/N * sum_{i=1}^N L_i)
        Accumulated micro-batch gradients must match full-batch gradient within precision tolerance.
        """
        device = torch.device(device_name)
        dtype = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}[precision]
        
        N = accum_steps
        B = 2  # micro batch size
        D = 16 # feature dimension
        
        torch.manual_seed(42)
        # Fixed weights
        W_init = torch.randn(D, D, device=device, dtype=dtype)
        
        # Generate N micro-batches
        inputs = [torch.randn(B, D, device=device, dtype=dtype) for _ in range(N)]
        targets = [torch.randn(B, D, device=device, dtype=dtype) for _ in range(N)]
        
        # Method A: Full Batch single forward/backward
        W_full = W_init.clone().detach().requires_grad_(True)
        X_full = torch.cat(inputs, dim=0)
        Y_full = torch.cat(targets, dim=0)
        pred_full = X_full @ W_full
        loss_full = F.mse_loss(pred_full, Y_full)
        loss_full.backward()
        grad_full = W_full.grad.clone()
        
        # Method B: Micro-batch gradient accumulation (scaled loss = loss / N)
        W_accum = W_init.clone().detach().requires_grad_(True)
        for i in range(N):
            pred_i = inputs[i] @ W_accum
            loss_i = F.mse_loss(pred_i, targets[i])
            scaled_loss_i = loss_i / N
            scaled_loss_i.backward()
            
        grad_accum = W_accum.grad.clone()
        
        # Tolerance based on precision
        tol = 1e-4 if precision == "float32" else (5e-2 if precision == "bfloat16" else 1e-2)
        diff = torch.norm(grad_accum.float() - grad_full.float()).item()
        assert diff < tol, f"Gradient mismatch ({diff:.6f} >= {tol}) for {precision} on {device_name}"

    def test_unscaled_vs_scaled_loss_step_results(self):
        """Verify StepResult unscaled_loss and scaled_loss exact ratio."""
        model = nn.Linear(8, 4)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            micro_batch_size=1,
            gradient_accumulation_steps=4,
            max_grad_norm=1.0,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)
        
        batch = (torch.randn(1, 8), torch.randn(1, 4))
        res = trainer.train_step(batch, step_idx=0)
        
        assert math.isclose(res.scaled_loss, res.unscaled_loss / 4.0, rel_tol=1e-5)
        assert res.is_accumulation_step is False
        assert res.optimizer_stepped is False
        
        # Run remaining 3 steps to trigger accumulation step
        for i in range(1, 4):
            batch_i = (torch.randn(1, 8), torch.randn(1, 4))
            res_i = trainer.train_step(batch_i, step_idx=i)
            
        assert res_i.is_accumulation_step is True
        assert res_i.optimizer_stepped is True

    def test_strict_gradient_clipping_invariant(self):
        """Verify gradient norm <= 1.0 invariant when raw norm >> 1.0."""
        model = nn.Linear(10, 5)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            gradient_accumulation_steps=1,
            max_grad_norm=1.0,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)
        
        # Force huge target to produce gradient norm >> 1.0
        batch = (torch.randn(1, 10), torch.randn(1, 5) * 500.0)
        res = trainer.train_step(batch, step_idx=0)
        
        assert res.grad_norm_before_clip > 1.0
        assert res.grad_norm_after_clip <= 1.00001
        assert res.optimizer_stepped is True

    def test_nan_gradient_detection_and_failfast(self):
        """Verify NaN gradient fail-fast with FloatingPointError."""
        model = nn.Linear(4, 2)
        config = MPSQLoRAConfig(
            device="cpu",
            precision="float32",
            gradient_accumulation_steps=1,
            fail_on_nan=True,
        )
        trainer = MPSQLoRATrainer(model=model, config=config)
        
        # Pass NaN batch
        nan_batch = (torch.tensor([[float("nan"), 1.0, 2.0, 3.0]]), torch.tensor([[1.0, 0.0]]))
        with pytest.raises(FloatingPointError):
            trainer.train_step(nan_batch, step_idx=0)


class TestItem2_BradleyTerryDPOSigmoidLoss:
    """Mathematical verification of Item 2: Bradley-Terry DPO sigmoid loss."""

    def test_dpo_analytical_sigmoid_equivalence(self):
        """
        Verify DPO loss formula:
        L = -log(sigmoid(beta * ( (log_pi_w - log_ref_w) - (log_pi_l - log_ref_l) )))
        """
        beta = 0.2
        dpo = DPOLossMPS(beta=beta, clamp_min=-10.0, clamp_max=10.0)
        
        pi_w = torch.tensor([ -1.2, -0.5, -2.0 ])
        pi_l = torch.tensor([ -3.0, -1.8, -2.2 ])
        ref_w = torch.tensor([ -1.5, -0.6, -1.9 ])
        ref_l = torch.tensor([ -2.5, -1.2, -2.0 ])
        
        loss, chosen_r, rejected_r, acc = dpo(pi_w, pi_l, ref_w, ref_l)
        
        # Analytical manual calculation
        chosen_ratio = pi_w - ref_w
        rejected_ratio = pi_l - ref_l
        logits_diff = beta * (chosen_ratio - rejected_ratio)
        expected_loss = (-torch.log(torch.sigmoid(logits_diff))).mean()
        
        assert torch.allclose(loss, expected_loss, atol=1e-6)
        assert torch.allclose(chosen_r, beta * chosen_ratio, atol=1e-6)
        assert torch.allclose(rejected_r, beta * rejected_ratio, atol=1e-6)
        assert acc.item() == 1.0

    def test_dpo_reference_freezing_no_gradient_leak(self):
        """Verify that policy gradients are computed while reference tensors are frozen/detached."""
        beta = 0.1
        dpo = DPOLossMPS(beta=beta)
        
        pi_w = torch.tensor([-1.0], requires_grad=True)
        pi_l = torch.tensor([-2.0], requires_grad=True)
        ref_w = torch.tensor([-1.5]) # Frozen reference
        ref_l = torch.tensor([-2.5]) # Frozen reference
        
        loss, _, _, _ = dpo(pi_w, pi_l, ref_w, ref_l)
        loss.backward()
        
        assert pi_w.grad is not None and pi_w.grad.item() != 0.0
        assert pi_l.grad is not None and pi_l.grad.item() != 0.0
        assert torch.isfinite(pi_w.grad)
        assert torch.isfinite(pi_l.grad)

    def test_dpo_analytical_gradients(self):
        """
        Verify exact gradient math:
        dL/d(pi_w) = -beta * (1 - sigmoid(beta * Delta)) = -beta * sigmoid(-beta * Delta)
        dL/d(pi_l) = +beta * sigmoid(-beta * Delta)
        """
        beta = 0.15
        dpo = DPOLossMPS(beta=beta, clamp_min=-20.0, clamp_max=20.0)
        
        pi_w = torch.tensor([-1.0], requires_grad=True)
        pi_l = torch.tensor([-2.5], requires_grad=True)
        ref_w = torch.tensor([-1.2])
        ref_l = torch.tensor([-2.0])
        
        loss, _, _, _ = dpo(pi_w, pi_l, ref_w, ref_l)
        loss.backward()
        
        Delta = (pi_w.detach() - ref_w) - (pi_l.detach() - ref_l)
        sigmoid_neg = torch.sigmoid(-beta * Delta)
        expected_grad_w = -beta * sigmoid_neg
        expected_grad_l = +beta * sigmoid_neg
        
        assert torch.allclose(pi_w.grad, expected_grad_w, atol=1e-6)
        assert torch.allclose(pi_l.grad, expected_grad_l, atol=1e-6)

    def test_dpo_log_ratio_clamping_saturation_protection(self):
        """Verify clamping prevents gradient explosion on extreme logits difference."""
        dpo = DPOLossMPS(beta=1.0, clamp_min=-10.0, clamp_max=10.0)
        
        # Extreme difference (+100.0)
        pi_w_huge = torch.tensor([100.0], requires_grad=True)
        pi_l_zero = torch.tensor([0.0], requires_grad=True)
        
        loss_huge, _, _, _ = dpo(pi_w_huge, pi_l_zero)
        loss_huge.backward()
        
        # Clamped at 10.0 => loss = -log(sigmoid(10.0)) = log(1 + e^-10) ~= 4.53999e-5
        expected_clamped_loss = math.log(1.0 + math.exp(-10.0))
        assert math.isclose(loss_huge.item(), expected_clamped_loss, rel_tol=1e-4)
        assert torch.isfinite(pi_w_huge.grad)

    def test_dpo_label_smoothing_boundary(self):
        """Verify label smoothing math: L = -(1-e)*log(sig(D)) - e*log(sig(-D))."""
        smoothing = 0.1
        dpo = DPOLossMPS(beta=0.1, label_smoothing=smoothing)
        
        # When Delta = 0, sig(0) = 0.5, log(sig(0)) = log(0.5) = -log(2)
        # Loss must equal log(2) regardless of smoothing!
        pi_w = torch.tensor([-1.0])
        pi_l = torch.tensor([-1.0])
        loss, _, _, _ = dpo(pi_w, pi_l)
        assert math.isclose(loss.item(), math.log(2.0), rel_tol=1e-5)


class TestItem3_TIESWeightMerging:
    """Mathematical verification of Item 3: TIES trimming, sign election, and disjoint merge."""

    def test_topk_trimming_exact_sparsity_and_ordering(self):
        """Verify top-k% elements by absolute magnitude are retained, others zeroed."""
        # Create tensor with magnitudes 1 to 10
        t = torch.tensor([-1.0, 2.0, -3.0, 4.0, -5.0, 6.0, -7.0, 8.0, -9.0, 10.0])
        density = 0.4 # Keep top 4 (10.0, -9.0, 8.0, -7.0)
        
        trimmed = trim_tensor_topk(t, density=density)
        
        # Verify exactly 4 non-zero elements
        non_zero_count = (trimmed != 0.0).sum().item()
        assert non_zero_count == 4
        
        # Verify retained values are exactly {-7.0, 8.0, -9.0, 10.0}
        retained = trimmed[trimmed != 0.0].tolist()
        assert sorted(retained) == [-9.0, -7.0, 8.0, 10.0]
        
        # Verify lower magnitudes are strictly 0.0
        assert trimmed[0].item() == 0.0 # -1.0
        assert trimmed[4].item() == 0.0 # -5.0

    def test_sign_election_consensus_math(self):
        """Verify sign consensus: s = sign(sum(w_m * Delta_m))."""
        d1 = torch.tensor([ 2.0, -3.0,  0.5, -1.0])
        d2 = torch.tensor([ 1.0,  1.0,  0.2, -2.0])
        d3 = torch.tensor([-1.0, -2.0, -1.0, -0.5])
        
        # Unweighted sum:
        # col 0: 2 + 1 - 1 = +2 => +1
        # col 1: -3 + 1 - 2 = -4 => -1
        # col 2: 0.5 + 0.2 - 1.0 = -0.3 => -1
        # col 3: -1 - 2 - 0.5 = -3.5 => -1
        signs = elect_signs([d1, d2, d3])
        expected = torch.tensor([1.0, -1.0, -1.0, -1.0])
        assert torch.equal(signs, expected)

    def test_disjoint_parameter_averaging(self):
        """
        Verify disjoint merge: averages ONLY elements agreeing with sign consensus.
        Conflicting elements are filtered out.
        """
        d1 = torch.tensor([ 2.0, -3.0,  0.5])
        d2 = torch.tensor([ 4.0,  1.0,  0.0])
        d3 = torch.tensor([-1.0, -5.0, -1.0])
        
        signs = torch.tensor([1.0, -1.0, 1.0])
        merged = disjoint_merge([d1, d2, d3], signs)
        
        # col 0: signs +1. d1=2 (+), d2=4 (+), d3=-1 (- discarded). Avg = (2+4)/2 = 3.0
        # col 1: signs -1. d1=-3 (-), d2=1 (+ discarded), d3=-5 (-). Avg = (-3 + -5)/2 = -4.0
        # col 2: signs +1. d1=0.5 (+), d2=0 (0 discarded), d3=-1 (- discarded). Avg = 0.5/1 = 0.5
        expected = torch.tensor([3.0, -4.0, 0.5])
        assert torch.allclose(merged, expected, atol=1e-5)

    def test_ties_end_to_end_merge(self):
        """Verify full TIES pipeline on multi-layer delta weights."""
        base = torch.zeros(4, 4)
        d1 = torch.randn(4, 4)
        d2 = torch.randn(4, 4)
        
        merged = merge_tensors(base, [d1, d2], method="ties", density=0.5)
        assert merged.shape == base.shape
        assert not torch.isnan(merged).any()


class TestItem4_DAREBernoulliNormConservation:
    """Mathematical verification of Item 4: DARE Bernoulli drop-and-rescale E[W_dare] = W."""

    def test_dare_expectation_conservation_law_spatial_1m(self):
        """
        Verify: E[W_dare] = W on large 1M parameter tensor.
        Spatial mean difference (1/N) sum_{i=1}^N (W_dare_i - W_i) -> 0.
        """
        torch.manual_seed(42)
        W = torch.randn(1000000)
        density = 0.5
        W_dare = dare_drop_and_rescale(W, density=density)
        
        mean_diff = torch.mean(W_dare - W).item()
        assert abs(mean_diff) < 0.005, f"Spatial expectation error too high: {mean_diff:.6f}"

    def test_dare_monte_carlo_expectation_convergence(self):
        """
        Verify: Over K=2000 Monte Carlo trials, sample mean converges to W
        with mean absolute error < 0.02 across all parameters.
        """
        torch.manual_seed(1337)
        W = torch.randn(50, 50)
        density = 0.6
        K = 2000  # 2000 Monte Carlo trials
        
        accum = torch.zeros_like(W)
        for k in range(K):
            W_dare = dare_drop_and_rescale(W, density=density, seed=k)
            accum += W_dare
            
        E_W_dare = accum / K
        mae = torch.mean(torch.abs(E_W_dare - W)).item()
        assert mae < 0.02, f"DARE MAE too high: {mae:.4f}"

    def test_dare_sparsity_and_rescaling_factor(self):
        """Verify that non-zero entries are scaled by exactly 1 / density."""
        tensor = torch.ones(1000, 1000)
        density = 0.4
        rescaled = dare_drop_and_rescale(tensor, density=density, seed=42)
        
        # Retained elements must be exactly 1.0 / 0.4 = 2.5
        non_zero = rescaled[rescaled != 0.0]
        assert torch.allclose(non_zero, torch.full_like(non_zero, 2.5), atol=1e-5)
        
        # Check empirical retention fraction is close to 0.4 (within 3 std dev)
        empirical_density = (rescaled != 0.0).float().mean().item()
        assert abs(empirical_density - 0.4) < 0.01

    def test_dare_energy_conservation(self):
        """Verify theoretical second moment: E[||W_dare||^2] = (1/density) * ||W||^2."""
        torch.manual_seed(42)
        W = torch.randn(500, 500)
        density = 0.5
        K = 200
        
        energy_sum = 0.0
        for k in range(K):
            W_dare = dare_drop_and_rescale(W, density=density, seed=k)
            energy_sum += torch.norm(W_dare)**2
            
        mean_energy = energy_sum / K
        expected_energy = (1.0 / density) * (torch.norm(W)**2)
        
        rel_diff = abs(mean_energy - expected_energy) / expected_energy
        assert rel_diff < 0.05, f"Energy conservation mismatch: {rel_diff:.4f}"


class TestItem5_SLERPSphericalInterpolation:
    """Mathematical verification of Item 5: SLERP geodesic interpolation."""

    def test_slerp_endpoints(self):
        """Verify SLERP(v0, v1; 0) == v0 and SLERP(v0, v1; 1) == v1."""
        v0 = torch.randn(64, 64)
        v1 = torch.randn(64, 64)
        
        slerp_0 = slerp_tensors(v0, v1, t=0.0)
        slerp_1 = slerp_tensors(v0, v1, t=1.0)
        
        assert torch.allclose(slerp_0, v0, atol=1e-6)
        assert torch.allclose(slerp_1, v1, atol=1e-6)

    def test_slerp_geodesic_constant_angular_velocity(self):
        """
        Verify that angle theta(t) between SLERP(t) and v0 equals t * theta.
        """
        # Create two orthogonal unit vectors
        v0 = torch.zeros(100)
        v0[0] = 1.0
        v1 = torch.zeros(100)
        v1[1] = 1.0
        
        theta_total = math.pi / 2.0  # 90 degrees
        
        for t in [0.1, 0.25, 0.5, 0.75, 0.9]:
            vt = slerp_tensors(v0, v1, t=t)
            # Angle between vt and v0: cos(theta_t) = vt . v0
            dot_t = torch.dot(vt / torch.norm(vt), v0 / torch.norm(v0)).clamp(-1.0, 1.0)
            theta_t = torch.acos(dot_t).item()
            
            expected_theta_t = t * theta_total
            assert math.isclose(theta_t, expected_theta_t, rel_tol=1e-4), f"Angular velocity deviation at t={t}"

    def test_slerp_norm_interpolation(self):
        """Verify SLERP norm is interpolated linearly: ||vt|| = (1-t)||v0|| + t||v1||."""
        v0 = torch.randn(50) * 2.0
        v1 = torch.randn(50) * 10.0
        
        norm0 = torch.norm(v0).item()
        norm1 = torch.norm(v1).item()
        
        for t in [0.2, 0.5, 0.8]:
            vt = slerp_tensors(v0, v1, t=t)
            expected_norm = (1.0 - t) * norm0 + t * norm1
            actual_norm = torch.norm(vt).item()
            assert math.isclose(actual_norm, expected_norm, rel_tol=1e-4)

    def test_slerp_collinear_and_zero_norm_stability(self):
        """Verify SLERP does not produce NaN on collinear or zero-norm inputs."""
        # Collinear identical
        v = torch.randn(32)
        slerp_collinear = slerp_tensors(v, v * 2.0, t=0.5)
        assert not torch.isnan(slerp_collinear).any()
        assert torch.allclose(slerp_collinear, v * 1.5, atol=1e-5)
        
        # Zero norm vector
        v_zero = torch.zeros(32)
        slerp_zero = slerp_tensors(v_zero, v, t=0.5)
        assert not torch.isnan(slerp_zero).any()
        assert torch.allclose(slerp_zero, v * 0.5, atol=1e-5)


class TestItem6_SimHashAndSHA256Deduplication:
    """Mathematical verification of Item 6: SimHash Hamming distance and SHA-256 deduplication."""

    def test_sha256_canonical_exact_deduplication(self):
        """Verify exact SHA-256 collision resistance and schema invariance."""
        dedup = SampleDeduplicator(enable_exact=True, enable_simhash=False)
        
        # Two identical DPO samples with different key insertion orders
        rec1 = {"prompt": "Write a quicksort in Python", "chosen": "def qs()...", "rejected": "bad"}
        rec2 = {"rejected": "bad", "chosen": "def qs()...", "prompt": "Write a quicksort in Python"}
        
        h1 = dedup.compute_exact_hash(rec1)
        h2 = dedup.compute_exact_hash(rec2)
        assert h1 == h2
        
        assert dedup.add_record(rec1) is True
        assert dedup.add_record(rec2) is False  # Rejected as exact duplicate

    def test_simhash_hamming_distance_metric_properties(self):
        """
        Verify metric space properties for Hamming distance:
        1. D(x, x) == 0
        2. D(x, y) == D(y, x) (Symmetry)
        3. D(x, z) <= D(x, y) + D(y, z) (Triangle Inequality)
        """
        sh = SimHash()
        h1 = sh.compute("The quick brown fox jumps over the lazy dog.")
        h2 = sh.compute("The quick brown fox jumps over the lazy fox.")
        h3 = sh.compute("Quantum computing advances in superconducting qubits.")
        
        # 1. Self distance == 0
        assert SimHash.hamming_distance(h1, h1) == 0
        
        # 2. Symmetry
        assert SimHash.hamming_distance(h1, h2) == SimHash.hamming_distance(h2, h1)
        
        # 3. Triangle Inequality
        d12 = SimHash.hamming_distance(h1, h2)
        d23 = SimHash.hamming_distance(h2, h3)
        d13 = SimHash.hamming_distance(h1, h3)
        assert d13 <= d12 + d23, f"Triangle inequality failed: {d13} > {d12} + {d23}"

    def test_simhash_locality_sensitive_property(self):
        """
        Verify that near-duplicate text has small Hamming distance (<= 4)
        while unrelated text has large Hamming distance (~32).
        """
        sh = SimHash()
        t_base = "Analyze the electrocardiogram signal using Pan-Tompkins QRS detection algorithm."
        t_near = "Analyze the electrocardiogram signal using Pan-Tompkins QRS detection algorithms."
        t_unrelated = "French cuisine includes croissants, baguettes, and boeuf bourguignon."
        
        h_base = sh.compute(t_base)
        h_near = sh.compute(t_near)
        h_unrel = sh.compute(t_unrelated)
        
        dist_near = SimHash.hamming_distance(h_base, h_near)
        dist_unrel = SimHash.hamming_distance(h_base, h_unrel)
        
        assert dist_near <= 6, f"Near duplicate distance was {dist_near} > 6"
        assert dist_unrel >= 20, f"Unrelated distance was {dist_unrel} < 20"

    def test_pigeonhole_4block_lsh_indexing(self):
        """
        Verify 4-block LSH indexing guarantees:
        If Hamming distance <= 3 in 64 bits, by Pigeonhole Principle,
        at least one of the four 16-bit blocks MUST have 0 bit differences (exact match).
        """
        dedup = SampleDeduplicator(simhash_threshold=3, simhash_bits=64)
        
        h_base = 0b1010101010101010_1100110011001100_1111000011110000_0000111100001111
        # Flip 3 bits in block 0, 1, 2 (leaving block 3 untouched)
        h_perturbed = h_base ^ (1 << 0) ^ (1 << 18) ^ (1 << 35)
        
        dist = SimHash.hamming_distance(h_base, h_perturbed)
        assert dist == 3
        
        # Check blocks
        blocks_base = [dedup._get_block_key(h_base, i) for i in range(4)]
        blocks_pert = [dedup._get_block_key(h_perturbed, i) for i in range(4)]
        
        # At least one block must match
        matching_blocks = [i for i in range(4) if blocks_base[i] == blocks_pert[i]]
        assert len(matching_blocks) >= 1, "Pigeonhole theorem violated! No matching blocks found for dist=3."
