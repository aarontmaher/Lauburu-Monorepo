"""
Unit tests for Multi-Tier Sample Deduplicator (F6).
"""

import os
import tempfile
import unittest

from src.distillation.sample_deduplicator import (
    SampleDeduplicator,
    SimHash,
    extract_canonical_text,
    normalize_text,
)


class TestSampleDeduplicator(unittest.TestCase):

    def setUp(self):
        self.deduplicator = SampleDeduplicator(
            enable_exact=True,
            enable_simhash=True,
            simhash_bits=64,
            simhash_threshold=6,
            shingle_size=3,
        )

    def test_normalize_text(self):
        raw = "  Hello   \n\t World!  \r\n"
        normalized = normalize_text(raw)
        self.assertEqual(normalized, "Hello World!")

    def test_extract_canonical_text_dpo(self):
        rec = {
            "prompt": "What is the capital of Australia?",
            "chosen": "Canberra.",
            "rejected": "Sydney.",
            "timestamp": "2026-09-02T05:00:00Z",
        }
        canonical = extract_canonical_text(rec)
        self.assertIn("PROMPT:What is the capital of Australia?", canonical)
        self.assertIn("CHOSEN:Canberra.", canonical)
        self.assertIn("REJECTED:Sydney.", canonical)
        # Non-semantic timestamp should be excluded
        self.assertNotIn("2026-09-02", canonical)

    def test_extract_canonical_text_sft_and_cot(self):
        rec_sft = {
            "instruction": "Explain Pan-Tompkins algorithm.",
            "input": "Sampling rate 512Hz",
            "thought": "First apply bandpass filter...",
            "output": "The Pan-Tompkins algorithm identifies QRS complexes in ECG signals.",
        }
        canonical = extract_canonical_text(rec_sft)
        self.assertIn("INSTRUCTION:Explain Pan-Tompkins algorithm.", canonical)
        self.assertIn("INPUT:Sampling rate 512Hz", canonical)
        self.assertIn("THOUGHT:First apply bandpass filter...", canonical)
        self.assertIn("OUTPUT:The Pan-Tompkins algorithm identifies QRS complexes in ECG signals.", canonical)

    def test_extract_canonical_text_messages(self):
        rec_msgs = {
            "messages": [
                {"role": "user", "content": "Ping router"},
                {"role": "assistant", "content": "192.168.8.1 is alive (0.42ms)"},
            ]
        }
        canonical = extract_canonical_text(rec_msgs)
        self.assertIn("USER:Ping router", canonical)
        self.assertIn("ASSISTANT:192.168.8.1 is alive (0.42ms)", canonical)

    def test_exact_duplicate_rejection(self):
        rec1 = {
            "prompt": "Optimize Metal QLoRA memory allocation.",
            "chosen": "Use dynamic headroom governor and torch.mps.empty_cache().",
            "rejected": "Allocate all available RAM to single tensor.",
        }
        rec2 = {
            "prompt": "  Optimize Metal QLoRA memory allocation. \n",
            "chosen": "Use dynamic headroom governor and torch.mps.empty_cache().  ",
            "rejected": "Allocate all available RAM to single tensor.",
        }

        # First record should be accepted
        added1 = self.deduplicator.add_record(rec1)
        self.assertTrue(added1)

        # Second record (whitespace variant) should be identified as exact duplicate
        is_dup, reason = self.deduplicator.check_duplicate(rec2)
        self.assertTrue(is_dup)
        self.assertEqual(reason, "EXACT_DUPLICATE")

        added2 = self.deduplicator.add_record(rec2)
        self.assertFalse(added2)

    def test_distinct_records_are_unique(self):
        rec1 = {"prompt": "Task A", "chosen": "Good A", "rejected": "Bad A"}
        rec2 = {"prompt": "Task B", "chosen": "Good B", "rejected": "Bad B"}

        self.assertTrue(self.deduplicator.add_record(rec1))
        self.assertTrue(self.deduplicator.add_record(rec2))

        is_dup, reason = self.deduplicator.check_duplicate(rec2)
        self.assertTrue(is_dup)

    def test_simhash_computation_and_hamming_distance(self):
        sh = SimHash(shingle_size=3, num_bits=64)
        t1 = "Autonomous 24/7 AI Training Optimization Engine across 7-Layer Mesh"
        t2 = "Autonomous 24/7 AI Training Optimization Engine across 7-Layer Mesh."  # 1 char diff
        t3 = "Completely disjoint and unrelated textual content about astrophysics"

        h1 = sh.compute(t1)
        h2 = sh.compute(t2)
        h3 = sh.compute(t3)

        dist_near = SimHash.hamming_distance(h1, h2)
        dist_far = SimHash.hamming_distance(h1, h3)

        self.assertLessEqual(dist_near, 6)
        self.assertGreater(dist_far, 10)
        self.assertGreaterEqual(SimHash.similarity(h1, h2), 0.90)

    def test_simhash_near_duplicate_gate(self):
        # Create a fresh deduplicator without exact matching to isolate simhash behavior
        sim_dedup = SampleDeduplicator(
            enable_exact=False,
            enable_simhash=True,
            simhash_threshold=6,
        )

        base_rec = {
            "prompt": "Run continuous DPO distillation on Apple Silicon Metal with beta=0.10.",
            "chosen": "Policy loss converged smoothly with zero NaN gradients.",
            "rejected": "Policy loss diverged with numerical overflow.",
        }
        near_rec = {
            "prompt": "Run continuous DPO distillation on Apple Silicon Metal with beta=0.10!",
            "chosen": "Policy loss converged smoothly with zero NaN gradients.",
            "rejected": "Policy loss diverged with numerical overflow.",
        }

        self.assertTrue(sim_dedup.add_record(base_rec))
        is_dup, reason = sim_dedup.check_duplicate(near_rec)
        self.assertTrue(is_dup)
        self.assertIn("SIMHASH_NEAR_DUPLICATE", reason)

    def test_deduplicate_dataset_batch(self):
        records = [
            {"prompt": "Q1", "chosen": "C1", "rejected": "R1"},
            {"prompt": "Q1", "chosen": "C1", "rejected": "R1"},  # Exact dup
            {"prompt": "Q2", "chosen": "C2", "rejected": "R2"},
            {"prompt": "Q2 ", "chosen": "C2", "rejected": "R2"},  # Exact dup
            {"prompt": "Q3", "chosen": "C3", "rejected": "R3"},
        ]

        unique, stats = self.deduplicator.deduplicate_dataset(records)
        self.assertEqual(len(unique), 3)
        self.assertEqual(stats["total_in"], 5)
        self.assertEqual(stats["exact_duplicates"], 2)
        self.assertEqual(stats["unique_out"], 3)
        self.assertEqual(stats["duplicate_rate_pct"], 40.0)

    def test_state_serialization_and_reloading(self):
        rec = {"prompt": "Persist seen hashes", "chosen": "Yes", "rejected": "No"}
        self.deduplicator.add_record(rec)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.deduplicator.save_state(tmp_path)
            self.assertTrue(os.path.exists(tmp_path))

            # New deduplicator
            new_dedup = SampleDeduplicator()
            new_dedup.load_state(tmp_path)

            # Check that rec is recognized as duplicate in new instance
            is_dup, reason = new_dedup.check_duplicate(rec)
            self.assertTrue(is_dup)
            self.assertEqual(reason, "EXACT_DUPLICATE")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_empty_and_corner_cases(self):
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(self.deduplicator.compute_simhash(""), 0)
        empty_rec = {}
        h = self.deduplicator.compute_exact_hash(empty_rec)
        self.assertIsInstance(h, str)
        self.assertTrue(len(h) > 0)


if __name__ == "__main__":
    unittest.main()
