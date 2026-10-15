"""
Unit tests for MPS Bradley-Terry DPO Loss Engine (F11).
"""

import unittest

import torch

from src.distillation.dpo_loss_mps import DPOLossMPS, compute_token_log_probs


class TestDPOLossMPS(unittest.TestCase):

    def setUp(self):
        torch.manual_seed(42)
        self.dpo_loss = DPOLossMPS(beta=0.1, clamp_min=-10.0, clamp_max=10.0)

    def test_compute_token_log_probs(self):
        batch_size = 2
        seq_len = 5
        vocab_size = 10

        logits = torch.randn(batch_size, seq_len, vocab_size)
        labels = torch.tensor([
            [1, 2, 3, 4, 5],
            [1, 2, -100, -100, -100],  # partially padded
        ])

        logps = compute_token_log_probs(logits, labels, label_pad_token_id=-100)
        self.assertEqual(logps.shape, (batch_size,))
        self.assertFalse(torch.isnan(logps).any())
        self.assertFalse(torch.isinf(logps).any())
        # Negative log probabilities
        self.assertTrue((logps <= 0).all())

    def test_dpo_loss_forward(self):
        batch_size = 4
        # Policy favors chosen over rejected
        policy_chosen_logps = torch.tensor([-2.0, -1.5, -3.0, -2.5])
        policy_rejected_logps = torch.tensor([-5.0, -6.0, -7.0, -8.0])

        # Reference has neutral preference
        ref_chosen_logps = torch.tensor([-3.0, -3.0, -3.0, -3.0])
        ref_rejected_logps = torch.tensor([-3.0, -3.0, -3.0, -3.0])

        loss, chosen_rewards, rejected_rewards, accuracy = self.dpo_loss(
            policy_chosen_logps=policy_chosen_logps,
            policy_rejected_logps=policy_rejected_logps,
            reference_chosen_logps=ref_chosen_logps,
            reference_rejected_logps=ref_rejected_logps,
        )

        self.assertIsInstance(loss, torch.Tensor)
        self.assertEqual(loss.dim(), 0)  # Scalar
        self.assertGreater(loss.item(), 0.0)
        self.assertFalse(torch.isnan(loss))

        # Chosen rewards should be strictly greater than rejected rewards
        self.assertTrue((chosen_rewards > rejected_rewards).all())
        self.assertEqual(accuracy.item(), 1.0)

    def test_log_ratio_clamping_prevents_nan(self):
        # Extreme log probability differences
        policy_chosen_logps = torch.tensor([1000.0, -1000.0])
        policy_rejected_logps = torch.tensor([-1000.0, 1000.0])
        ref_chosen_logps = torch.tensor([0.0, 0.0])
        ref_rejected_logps = torch.tensor([0.0, 0.0])

        loss, chosen_rewards, rejected_rewards, accuracy = self.dpo_loss(
            policy_chosen_logps=policy_chosen_logps,
            policy_rejected_logps=policy_rejected_logps,
            reference_chosen_logps=ref_chosen_logps,
            reference_rejected_logps=ref_rejected_logps,
        )

        self.assertFalse(torch.isnan(loss))
        self.assertFalse(torch.isinf(loss))

    def test_label_smoothing(self):
        loss_engine_smooth = DPOLossMPS(beta=0.1, label_smoothing=0.1)
        p_c = torch.tensor([-2.0, -2.0])
        p_r = torch.tensor([-4.0, -4.0])
        r_c = torch.tensor([-3.0, -3.0])
        r_r = torch.tensor([-3.0, -3.0])

        loss, _, _, _ = loss_engine_smooth(p_c, p_r, r_c, r_r)
        self.assertGreater(loss.item(), 0.0)
        self.assertFalse(torch.isnan(loss))

    def test_reference_free_dpo(self):
        loss_engine_ref_free = DPOLossMPS(beta=0.1, reference_free=True)
        p_c = torch.tensor([-2.0, -1.0])
        p_r = torch.tensor([-4.0, -5.0])

        loss, c_rewards, r_rewards, acc = loss_engine_ref_free(p_c, p_r)
        self.assertGreater(loss.item(), 0.0)
        self.assertEqual(acc.item(), 1.0)

    def test_compute_loss_from_logits(self):
        batch_size = 2
        seq_len = 6
        vocab_size = 20

        policy_c_logits = torch.randn(batch_size, seq_len, vocab_size, requires_grad=True)
        policy_r_logits = torch.randn(batch_size, seq_len, vocab_size, requires_grad=True)
        ref_c_logits = torch.randn(batch_size, seq_len, vocab_size)
        ref_r_logits = torch.randn(batch_size, seq_len, vocab_size)

        c_labels = torch.randint(0, vocab_size, (batch_size, seq_len))
        r_labels = torch.randint(0, vocab_size, (batch_size, seq_len))

        loss, c_rewards, r_rewards, acc = self.dpo_loss.compute_loss_from_logits(
            policy_chosen_logits=policy_c_logits,
            policy_rejected_logits=policy_r_logits,
            chosen_labels=c_labels,
            rejected_labels=r_labels,
            reference_chosen_logits=ref_c_logits,
            reference_rejected_logits=ref_r_logits,
        )

        self.assertGreater(loss.item(), 0.0)
        # Backward pass check
        loss.backward()
        self.assertIsNotNone(policy_c_logits.grad)
        self.assertFalse(torch.isnan(policy_c_logits.grad).any())

    def test_mps_device_execution(self):
        if torch.backends.mps.is_available():
            device = torch.device("mps")
            p_c = torch.tensor([-2.0, -1.5], device=device)
            p_r = torch.tensor([-5.0, -6.0], device=device)
            r_c = torch.tensor([-3.0, -3.0], device=device)
            r_r = torch.tensor([-3.0, -3.0], device=device)

            loss, c_rewards, r_rewards, acc = self.dpo_loss(p_c, p_r, r_c, r_r)
            self.assertEqual(loss.device.type, "mps")
            self.assertGreater(loss.item(), 0.0)
            self.assertEqual(acc.item(), 1.0)


if __name__ == "__main__":
    unittest.main()
