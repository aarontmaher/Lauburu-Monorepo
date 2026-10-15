"""
Unit Tests for Native PyTorch In-Memory TIES/DARE/SLERP Tensor Merger (Feature F13).
Verifies pure mathematical tensor operations, sign consensus, disjoint merging,
energy conservation in DARE, SLERP spherical manifolds, and state dict merging.
"""

import math
import tempfile
import unittest
from pathlib import Path

import torch

from src.weight_merging.native_ties_dare_merger import (
    NativeTensorMerger,
    dare_drop_and_rescale,
    disjoint_merge,
    elect_signs,
    merge_adapters,
    merge_state_dicts,
    merge_tensors,
    slerp_tensors,
    trim_tensor_topk,
)


class TestNativeTensorMerger(unittest.TestCase):
    """Test suite for native tensor merging mathematical operations."""

    def test_trim_tensor_topk_basic_retention(self):
        """trim_tensor_topk retains top-k elements by absolute magnitude."""
        t = torch.tensor([1.0, 5.0, 2.0, 10.0, 0.5])
        trimmed = trim_tensor_topk(t, density=0.4)
        self.assertEqual(trimmed[3].item(), 10.0)
        self.assertEqual(trimmed[1].item(), 5.0)
        self.assertEqual(trimmed[0].item(), 0.0)
        self.assertEqual(trimmed[2].item(), 0.0)
        self.assertEqual(trimmed[4].item(), 0.0)

    def test_trim_tensor_topk_negative_magnitudes(self):
        """trim_tensor_topk ranks by absolute value, retaining negative signs."""
        t = torch.tensor([-10.0, 1.0, -0.5, 8.0])
        trimmed = trim_tensor_topk(t, density=0.5)
        self.assertEqual(trimmed[0].item(), -10.0)
        self.assertEqual(trimmed[3].item(), 8.0)
        self.assertEqual(trimmed[1].item(), 0.0)
        self.assertEqual(trimmed[2].item(), 0.0)

    def test_trim_tensor_topk_density_zero_and_one(self):
        """Density 0.0 zeroes all; density 1.0 retains all."""
        t = torch.tensor([1.0, 2.0, 3.0, 4.0])
        self.assertTrue((trim_tensor_topk(t, density=0.0) == 0.0).all())
        self.assertTrue(torch.equal(trim_tensor_topk(t, density=1.0), t))

    def test_trim_tensor_topk_2d_matrix(self):
        """trim_tensor_topk operates properly on 2D matrices."""
        mat = torch.tensor([
            [10.0, 1.0],
            [2.0, 20.0]
        ])
        trimmed = trim_tensor_topk(mat, density=0.5)
        self.assertEqual(trimmed[0, 0].item(), 10.0)
        self.assertEqual(trimmed[1, 1].item(), 20.0)
        self.assertEqual(trimmed[0, 1].item(), 0.0)
        self.assertEqual(trimmed[1, 0].item(), 0.0)

    def test_elect_signs_consensus(self):
        """elect_signs computes sign(sum(w_i * delta_i))."""
        d1 = torch.tensor([1.0, -2.0, 3.0])
        d2 = torch.tensor([2.0, 1.0, 1.0])
        signs = elect_signs([d1, d2], weights=[1.0, 1.0])
        self.assertTrue(torch.equal(signs, torch.tensor([1.0, -1.0, 1.0])))

    def test_elect_signs_weighted(self):
        """elect_signs accounts for weights."""
        d1 = torch.tensor([-2.0])
        d2 = torch.tensor([1.0])
        # d1 has weight 1.0, d2 has weight 3.0 -> sum = -2 + 3 = +1 -> sign = +1
        signs = elect_signs([d1, d2], weights=[1.0, 3.0])
        self.assertEqual(signs[0].item(), 1.0)

    def test_elect_signs_exact_tie(self):
        """Opposing equal magnitude deltas resolve sign to 0.0."""
        d1 = torch.tensor([5.0])
        d2 = torch.tensor([-5.0])
        signs = elect_signs([d1, d2], weights=[1.0, 1.0])
        self.assertEqual(signs[0].item(), 0.0)

    def test_elect_signs_empty_or_mismatch_error(self):
        """elect_signs raises ValueError on empty list or weight length mismatch."""
        with self.assertRaises(ValueError):
            elect_signs([])
        with self.assertRaises(ValueError):
            elect_signs([torch.tensor([1.0])], weights=[1.0, 2.0])

    def test_disjoint_merge_agreement(self):
        """disjoint_merge averages only parameters that match sign consensus."""
        d1 = torch.tensor([2.0, -4.0])
        d2 = torch.tensor([4.0, 2.0])
        signs = torch.tensor([1.0, -1.0])
        merged = disjoint_merge([d1, d2], signs, weights=[1.0, 1.0])
        self.assertAlmostEqual(merged[0].item(), 3.0, places=4)
        self.assertAlmostEqual(merged[1].item(), -4.0, places=4)

    def test_disjoint_merge_empty_error(self):
        """disjoint_merge raises ValueError on empty deltas."""
        with self.assertRaises(ValueError):
            disjoint_merge([], torch.tensor([1.0]))

    def test_dare_drop_and_rescale_energy_conservation(self):
        """DARE drops weights and rescales by 1/density."""
        t = torch.ones(1000)
        rescaled = dare_drop_and_rescale(t, density=0.5, seed=42)
        non_zero = rescaled[rescaled != 0]
        self.assertTrue((non_zero == 2.0).all())
        self.assertAlmostEqual(rescaled.mean().item(), 1.0, places=1)

    def test_dare_drop_and_rescale_density_boundaries(self):
        """density=0.0 zeroes all; density=1.0 leaves all unchanged."""
        t = torch.tensor([3.0, 4.0])
        self.assertTrue((dare_drop_and_rescale(t, density=0.0) == 0.0).all())
        self.assertTrue(torch.equal(dare_drop_and_rescale(t, density=1.0), t))

    def test_slerp_tensors_orthogonal_interpolation(self):
        """slerp_tensors interpolates smoothly along spherical manifold."""
        v0 = torch.tensor([1.0, 0.0])
        v1 = torch.tensor([0.0, 1.0])
        res = slerp_tensors(v0, v1, t=0.5)
        expected = math.sqrt(2) / 2
        self.assertAlmostEqual(res[0].item(), expected, places=4)
        self.assertAlmostEqual(res[1].item(), expected, places=4)

    def test_slerp_tensors_boundaries(self):
        """slerp_tensors at t=0.0 returns v0; at t=1.0 returns v1."""
        v0 = torch.tensor([1.0, 2.0, 3.0])
        v1 = torch.tensor([4.0, 5.0, 6.0])
        self.assertTrue(torch.equal(slerp_tensors(v0, v1, t=0.0), v0))
        self.assertTrue(torch.equal(slerp_tensors(v0, v1, t=1.0), v1))

    def test_slerp_tensors_shape_mismatch_error(self):
        """slerp_tensors raises ValueError on mismatched tensor shapes."""
        v0 = torch.tensor([1.0, 2.0])
        v1 = torch.tensor([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            slerp_tensors(v0, v1, t=0.5)

    def test_merge_tensors_ties_and_dare_ties(self):
        """merge_tensors runs ties and dare_ties cleanly."""
        base = torch.tensor([10.0, 20.0, 30.0])
        d1 = torch.tensor([2.0, -4.0, 6.0])
        d2 = torch.tensor([4.0, 1.0, 2.0])

        merged_ties = merge_tensors(base, [d1, d2], method="ties", density=0.6)
        self.assertEqual(merged_ties.shape, base.shape)
        self.assertEqual(merged_ties.dtype, base.dtype)

        merged_dare = merge_tensors(base, [d1, d2], method="dare_ties", density=0.6, seed=123)
        self.assertEqual(merged_dare.shape, base.shape)

    def test_merge_tensors_zero_delta(self):
        """Merging zero delta returns exact base tensor."""
        base = torch.randn(4, 4)
        zero_delta = torch.zeros(4, 4)
        merged = merge_tensors(base, [zero_delta], method="ties", density=0.6)
        self.assertTrue(torch.equal(merged, base))

    def test_merge_state_dicts(self):
        """merge_state_dicts handles multi-key state dictionaries."""
        base_sd = {
            "layer1.weight": torch.ones(4, 4),
            "layer1.bias": torch.zeros(4),
            "layer2.weight": torch.full((4, 4), 2.0),
        }
        delta_sd1 = {
            "layer1.weight": torch.full((4, 4), 0.5),
            "layer1.bias": torch.full((4,), 0.2),
        }
        delta_sd2 = {
            "layer1.weight": torch.full((4, 4), 0.3),
            "layer1.bias": torch.full((4,), 0.4),
        }

        merged_sd = merge_state_dicts(
            base_sd=base_sd,
            delta_sds=[delta_sd1, delta_sd2],
            method="ties",
            density=1.0,
        )

        self.assertIn("layer1.weight", merged_sd)
        self.assertIn("layer2.weight", merged_sd)
        # layer2 was untouched
        self.assertTrue(torch.equal(merged_sd["layer2.weight"], base_sd["layer2.weight"]))

    def test_merge_adapters_end_to_end(self):
        """merge_adapters runs full workflow with dictionaries and save output."""
        base_sd = {"weight": torch.randn(8, 8)}
        adapter1 = {"weight": base_sd["weight"] + torch.randn(8, 8) * 0.1}
        adapter2 = {"weight": base_sd["weight"] + torch.randn(8, 8) * 0.1}

        with tempfile.TemporaryDirectory() as tmp_dir:
            merged = merge_adapters(
                base_model_path=base_sd,
                adapter_paths=[adapter1, adapter2],
                output_dir=tmp_dir,
                method="dare_ties",
                density=0.7,
            )
            self.assertIn("weight", merged)
            self.assertTrue(Path(tmp_dir).exists())


if __name__ == "__main__":
    unittest.main()
