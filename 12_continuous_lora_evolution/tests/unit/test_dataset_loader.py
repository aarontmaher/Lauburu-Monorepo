"""
Unit tests for Multi-Schema Dataset Ingestion & DataLoader Engine (F5).
"""

import json
import os
import tempfile
import unittest

import torch
from transformers import AutoTokenizer

from src.distillation.dataset_loader import (
    ContinuousDPODataset,
    ContinuousSFTDataset,
    DatasetIngestionEngine,
    DPODataCollator,
    DPORecord,
    MultiSchemaNormalizer,
    SFTDataCollator,
    SFTRecord,
    get_dataloader,
    get_dpo_dataloader,
    get_sft_dataloader,
)
from src.distillation.replay_buffer import StratifiedReplayBuffer
from src.distillation.tokenizer_aligner import TokenizerAligner


class TestDatasetLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load local cached tokenizer or fall back to standard local tokenizer
        try:
            cls.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", local_files_only=True)
        except Exception:
            try:
                cls.tokenizer = AutoTokenizer.from_pretrained("HuggingFaceTB/SmolLM2-135M-Instruct", local_files_only=True)
            except Exception:
                # Minimal tokenizer using BertTokenizer or basic tokenizer
                from transformers import BertTokenizer
                cls.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        TokenizerAligner.align_tokenizer(cls.tokenizer)

    def test_parse_dpo_records_various_schemas(self):
        # Standard DPO
        rec1 = {"prompt": "Prompt 1", "chosen": "Chosen 1", "rejected": "Rejected 1", "domain": "mesh_healing"}
        dpo1 = MultiSchemaNormalizer.parse_dpo_record(rec1)
        self.assertIsNotNone(dpo1)
        self.assertEqual(dpo1.prompt, "Prompt 1")
        self.assertEqual(dpo1.chosen, "Chosen 1")
        self.assertEqual(dpo1.domain, "mesh_healing")

        # Instruction + chosen + rejected
        rec2 = {"instruction": "Inst 2", "input": "Context", "chosen": "Good", "rejected": "Bad"}
        dpo2 = MultiSchemaNormalizer.parse_dpo_record(rec2)
        self.assertIsNotNone(dpo2)
        self.assertEqual(dpo2.prompt, "Inst 2\nContext")

        # Pairwise turns
        rec3 = {
            "turns": [
                {"role": "user", "content": "Question 3"},
                {"role": "assistant", "chosen": "Answer A", "rejected": "Answer B"},
            ]
        }
        dpo3 = MultiSchemaNormalizer.parse_dpo_record(rec3)
        self.assertIsNotNone(dpo3)
        self.assertEqual(dpo3.prompt, "Question 3")
        self.assertEqual(dpo3.chosen, "Answer A")

    def test_parse_sft_records_various_schemas(self):
        # CoT thought/solution
        rec_cot = {
            "instruction": "Solve problem.",
            "thought": "Step by step reasoning...",
            "solution": "Final answer 42.",
        }
        sft1 = MultiSchemaNormalizer.parse_sft_record(rec_cot)
        self.assertIsNotNone(sft1)
        self.assertIn("<thought>", sft1.response)
        self.assertIn("Final answer 42.", sft1.response)

        # Multi-turn messages
        rec_msgs = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi!"},
                {"role": "assistant", "content": "Hello! How can I help you?"},
            ]
        }
        sft2 = MultiSchemaNormalizer.parse_sft_record(rec_msgs)
        self.assertIsNotNone(sft2)
        self.assertEqual(sft2.response, "Hello! How can I help you?")

    def test_ingest_jsonl_file(self):
        records = [
            {"prompt": f"P{i}", "chosen": f"C{i}", "rejected": f"R{i}"}
            for i in range(5)
        ]
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as tmp:
            for r in records:
                tmp.write(json.dumps(r) + "\n")
            # Write a corrupted line to verify fault tolerance
            tmp.write("{malformed json line\n")
            tmp_path = tmp.name

        try:
            loaded = DatasetIngestionEngine.load_jsonl(tmp_path)
            self.assertEqual(len(loaded), 5)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_dpo_collator_and_dataloader(self):
        dpo_records = [
            DPORecord(prompt="Hello", chosen="Good day!", rejected="Go away."),
            DPORecord(prompt="What is 2+2?", chosen="4", rejected="5"),
        ]
        loader = get_dpo_dataloader(
            records_or_paths=[r.to_dict() for r in dpo_records],
            tokenizer=self.tokenizer,
            batch_size=2,
            max_length=128,
            shuffle=False,
            deduplicate=False,
            ast_validate=False,
        )

        batch = next(iter(loader))
        self.assertIn("prompt_input_ids", batch)
        self.assertIn("chosen_input_ids", batch)
        self.assertIn("chosen_labels", batch)
        self.assertIn("rejected_input_ids", batch)
        self.assertIn("rejected_labels", batch)

        self.assertEqual(batch["chosen_input_ids"].shape[0], 2)
        self.assertEqual(batch["rejected_input_ids"].shape[0], 2)

    def test_sft_collator_and_dataloader(self):
        sft_records = [
            SFTRecord(prompt="User: Hi\nAssistant:", response="Hello there!"),
            SFTRecord(prompt="User: 1+1?\nAssistant:", response="2"),
        ]
        loader = get_sft_dataloader(
            records_or_paths=[r.to_dict() for r in sft_records],
            tokenizer=self.tokenizer,
            batch_size=2,
            max_length=128,
            shuffle=False,
            deduplicate=False,
            ast_validate=False,
        )

        batch = next(iter(loader))
        self.assertIn("input_ids", batch)
        self.assertIn("attention_mask", batch)
        self.assertIn("labels", batch)
        self.assertEqual(batch["input_ids"].shape[0], 2)
        # Prompt tokens should be masked with -100 in labels
        self.assertTrue((batch["labels"] == -100).any())

    def test_unified_get_dataloader_contract(self):
        dpo_data = [
            {"prompt": "P", "chosen": "C", "rejected": "R"}
        ]
        config_dpo = {
            "task_type": "dpo",
            "dataset_path": dpo_data,
            "batch_size": 1,
            "max_length": 64,
            "deduplicate": False,
            "ast_validate": False,
        }
        loader_dpo = get_dataloader(config_dpo, tokenizer=self.tokenizer)
        batch_dpo = next(iter(loader_dpo))
        self.assertIn("chosen_input_ids", batch_dpo)

        sft_data = [
            {"instruction": "I", "output": "O"}
        ]
        config_sft = {
            "task_type": "sft",
            "dataset_path": sft_data,
            "batch_size": 1,
            "max_length": 64,
            "deduplicate": False,
            "ast_validate": False,
        }
        loader_sft = get_dataloader(config_sft, tokenizer=self.tokenizer)
        batch_sft = next(iter(loader_sft))
        self.assertIn("input_ids", batch_sft)
        self.assertIn("labels", batch_sft)


if __name__ == "__main__":
    unittest.main()
