"""
Unit tests for 80/20 Stratified Replay Buffer Engine (F9).
"""

import os
import tempfile
import unittest

from src.distillation.replay_buffer import (
    CANONICAL_ANCHOR_DOMAINS,
    DomainReservoir,
    StratifiedReplayBuffer,
)


class TestReplayBuffer(unittest.TestCase):

    def setUp(self):
        self.buffer = StratifiedReplayBuffer(
            reservoir_capacity=100,
            active_ratio=0.80,
            seed=42,
        )

    def test_canonical_domains(self):
        self.assertIn("biometrics_dsp", CANONICAL_ANCHOR_DOMAINS)
        self.assertIn("mesh_healing", CANONICAL_ANCHOR_DOMAINS)
        self.assertIn("code_correctness", CANONICAL_ANCHOR_DOMAINS)
        self.assertIn("system_architecture", CANONICAL_ANCHOR_DOMAINS)
        self.assertIn("general_reasoning", CANONICAL_ANCHOR_DOMAINS)

    def test_domain_inference(self):
        rec_bio = {"prompt": "Filter 512Hz ECG stream with Pan-Tompkins QRS detector."}
        rec_mesh = {"prompt": "Send WoL magic packet to revive offline OpenWrt router node."}
        rec_code = {"prompt": "Fix SyntaxError in Python AST compiler visitor."}
        rec_arch = {"prompt": "Synchronize obsidian vault index with tri-vault storage rule."}
        rec_gen = {"prompt": "Summarize today's team debate consensus."}

        self.assertEqual(self.buffer.infer_domain(rec_bio), "biometrics_dsp")
        self.assertEqual(self.buffer.infer_domain(rec_mesh), "mesh_healing")
        self.assertEqual(self.buffer.infer_domain(rec_code), "code_correctness")
        self.assertEqual(self.buffer.infer_domain(rec_arch), "system_architecture")
        self.assertEqual(self.buffer.infer_domain(rec_gen), "general_reasoning")

    def test_add_and_count_anchors(self):
        self.assertEqual(self.buffer.get_total_anchor_count(), 0)

        self.buffer.add_anchor_sample({"prompt": "ECG sample 1", "chosen": "A", "rejected": "B"}, domain="biometrics_dsp")
        self.buffer.add_anchor_sample({"prompt": "Mesh sample 1", "chosen": "C", "rejected": "D"}, domain="mesh_healing")
        self.buffer.add_anchor_sample({"prompt": "Code sample 1", "chosen": "E", "rejected": "F"}, domain="code_correctness")

        self.assertEqual(self.buffer.get_total_anchor_count(), 3)
        counts = self.buffer.get_domain_counts()
        self.assertEqual(counts["biometrics_dsp"], 1)
        self.assertEqual(counts["mesh_healing"], 1)
        self.assertEqual(counts["code_correctness"], 1)
        self.assertEqual(counts["system_architecture"], 0)

    def test_reservoir_capacity_eviction(self):
        small_res = DomainReservoir(domain="test_domain", max_capacity=3)
        for i in range(5):
            small_res.add({"id": i}, priority=float(i))

        self.assertEqual(len(small_res), 3)
        # Verify sampling works from populated reservoir
        samples = small_res.sample(2)
        self.assertEqual(len(samples), 2)

    def test_sample_stratified_batch_80_20(self):
        # Populate reservoirs
        for i in range(20):
            self.buffer.add_anchor_sample(
                {"id": f"anchor_bio_{i}", "prompt": "ECG", "chosen": "good", "rejected": "bad"},
                domain="biometrics_dsp",
            )
            self.buffer.add_anchor_sample(
                {"id": f"anchor_mesh_{i}", "prompt": "Mesh", "chosen": "good", "rejected": "bad"},
                domain="mesh_healing",
            )

        active_items = [
            {"id": f"active_{i}", "prompt": f"New innovation {i}", "chosen": "win", "rejected": "lose"}
            for i in range(50)
        ]

        batch, meta = self.buffer.sample_stratified_batch(active_items, batch_size=10, active_ratio=0.80)
        self.assertEqual(len(batch), 10)
        self.assertEqual(meta["active"], 8)
        self.assertEqual(meta["replay"], 2)
        self.assertEqual(meta["total"], 10)

    def test_empty_reservoir_fallback(self):
        # Buffer has no anchors
        active_items = [{"id": f"active_{i}"} for i in range(5)]
        batch, meta = self.buffer.sample_stratified_batch(active_items, batch_size=4)

        self.assertEqual(len(batch), 4)
        self.assertEqual(meta["active"], 4)
        self.assertEqual(meta["replay"], 0)

    def test_create_stratified_dataset(self):
        for i in range(10):
            self.buffer.add_anchor_sample(
                {"id": f"anchor_{i}", "domain": "code_correctness"}, domain="code_correctness"
            )

        active_dataset = [{"id": f"active_{i}"} for i in range(40)]
        augmented = self.buffer.create_stratified_dataset(active_dataset, replay_ratio=0.20)

        # 40 active items with 20% replay ratio -> 40 / 0.8 = 50 total (10 replay items injected)
        self.assertEqual(len(augmented), 50)

    def test_state_serialization(self):
        self.buffer.add_anchor_sample({"prompt": "ECG 512Hz"}, domain="biometrics_dsp")
        self.buffer.add_anchor_sample({"prompt": "WoL Port 18802"}, domain="mesh_healing")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.buffer.save_state(tmp_path)
            self.assertTrue(os.path.exists(tmp_path))

            new_buffer = StratifiedReplayBuffer()
            new_buffer.load_state(tmp_path)

            self.assertEqual(new_buffer.get_total_anchor_count(), 2)
            counts = new_buffer.get_domain_counts()
            self.assertEqual(counts["biometrics_dsp"], 1)
            self.assertEqual(counts["mesh_healing"], 1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
