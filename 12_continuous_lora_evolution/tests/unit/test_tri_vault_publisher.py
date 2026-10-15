"""
Unit Tests for Zero-Cost Tri-Vault Synchronization Publisher (Feature F16).
Tests Obsidian markdown note generation, PySpark JSONL dataset appending,
auto-healing of vault directories, and Rule #0 Zero Cloud Spend ($0.00 AUD) enforcement.
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from src.orchestration.tri_vault_publisher import (
    DEFAULT_GIT_REPO,
    DEFAULT_OBSIDIAN_VAULT,
    DEFAULT_PYSPARK_LAKE,
    TriVaultPublisher,
    generate_checkpoint_note,
    log_pyspark_record,
    publish_cycle,
)


class TestTriVaultPublisher(unittest.TestCase):
    """Test suite for Tri-Vault multi-storage publishing."""

    def test_auto_heal_vault_directories(self):
        """auto_heal_vault_directories creates missing Obsidian and PySpark directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            obsidian_dir = Path(tmp_dir) / "obsidian_vault"
            pyspark_dir = Path(tmp_dir) / "lora_datasets"

            publisher = TriVaultPublisher(
                obsidian_vault_dir=obsidian_dir,
                pyspark_lake_dir=pyspark_dir,
            )

            healed = publisher.auto_heal_vault_directories()
            self.assertTrue(obsidian_dir.exists())
            self.assertTrue((obsidian_dir / "05_TRAINING").exists())
            self.assertTrue((obsidian_dir / "04_ANALYTICS").exists())
            self.assertTrue((obsidian_dir / "Index.md").exists())
            self.assertTrue(pyspark_dir.exists())

            # Check Index.md contents
            index_text = (obsidian_dir / "Index.md").read_text(encoding="utf-8")
            self.assertIn("[[Index]]", index_text)
            self.assertIn("[[12_continuous_lora_evolution]]", index_text)

    def test_generate_obsidian_note_schema_and_wikilinks(self):
        """generate_obsidian_note produces valid YAML frontmatter and required Wikilinks."""
        publisher = TriVaultPublisher()
        meta = {
            "name": "qwen38_dare_ties_v1",
            "model_base": "Qwen/Qwen2.5-3B-Instruct",
            "merge_method": "dare_ties",
            "density": 0.65,
            "weight": 0.5,
            "final_train_loss": 0.842,
            "eval_perplexity": 4.12,
            "cloud_cost": 0.0,
        }
        losses = [1.5, 1.2, 0.95, 0.842]
        filename, content = publisher.generate_obsidian_note(meta, losses)

        self.assertEqual(filename, "qwen38_dare_ties_v1.md")
        self.assertIn("title: \"LoRA Evolution Checkpoint: qwen38_dare_ties_v1\"", content)
        self.assertIn("cloud_cost: \"$0.00 AUD\"", content)
        self.assertIn("[[Index]]", content)
        self.assertIn("[[12_continuous_lora_evolution]]", content)
        self.assertIn("[[02_ai_models_and_inference]]", content)
        self.assertIn("final_train_loss: 0.8420", content)

    def test_pyspark_jsonl_append(self):
        """publish_to_pyspark_lake appends valid JSON lines."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pyspark_dir = Path(tmp_dir) / "lora_datasets"
            publisher = TriVaultPublisher(
                obsidian_vault_dir=Path(tmp_dir) / "obsidian",
                pyspark_lake_dir=pyspark_dir,
            )

            record1 = {"cycle": 1, "step": 100, "loss": 0.92, "model_base": "smollm2-1.7b"}
            record2 = {"cycle": 1, "step": 200, "loss": 0.78, "model_base": "smollm2-1.7b"}

            target = publisher.publish_to_pyspark_lake(record1)
            publisher.publish_to_pyspark_lake(record2)

            self.assertTrue(target.exists())
            with open(target, "r", encoding="utf-8") as f:
                lines = f.readlines()

            self.assertEqual(len(lines), 2)
            parsed1 = json.loads(lines[0])
            parsed2 = json.loads(lines[1])
            self.assertEqual(parsed1["loss"], 0.92)
            self.assertEqual(parsed2["loss"], 0.78)
            self.assertEqual(parsed1["cloud_cost"], 0.0)

    def test_publish_cycle_interface_contract(self):
        """publish_cycle runs end-to-end multi-vault publishing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            obsidian_dir = Path(tmp_dir) / "obsidian_vault"
            pyspark_dir = Path(tmp_dir) / "lora_datasets"

            publisher = TriVaultPublisher(
                obsidian_vault_dir=obsidian_dir,
                pyspark_lake_dir=pyspark_dir,
            )

            meta = {
                "name": "llama32_slerp_cycle1",
                "model_base": "Llama-3.2-1B-Instruct",
                "merge_method": "slerp",
                "cloud_cost": 0.0,
            }
            res = publisher.publish_cycle(meta, [1.0, 0.8, 0.6])

            self.assertEqual(res["status"], "SUCCESS")
            self.assertTrue(res["pyspark_row_appended"])
            self.assertEqual(res["cloud_cost"], "$0.00 AUD")
            self.assertTrue(Path(res["obsidian_note"]).exists())
            self.assertTrue(Path(res["pyspark_path"]).exists())

    def test_empty_loss_curves_handling(self):
        """Handles empty loss curves gracefully without division by zero."""
        publisher = TriVaultPublisher()
        meta = {"name": "empty_loss_model"}
        _, note = publisher.generate_obsidian_note(meta, loss_curves=[])
        self.assertIn("final_train_loss: 0.0000", note)

    def test_zero_cost_invariant_enforcement(self):
        """Flags non-zero cloud spend ($50.00) in output note."""
        publisher = TriVaultPublisher()
        meta = {"name": "test_cost", "cloud_cost": 50.0}
        _, note = publisher.generate_obsidian_note(meta)
        self.assertIn("VIOLATION", note)


if __name__ == "__main__":
    unittest.main()
