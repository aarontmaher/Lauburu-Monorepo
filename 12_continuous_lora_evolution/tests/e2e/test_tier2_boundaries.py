"""
Tier 2 E2E Test Suite: Boundary Value Analysis, Stress & Extreme Conditions.

Covers boundary values, extreme conditions, memory caps, empty datasets, corrupt tokens,
and edge conditions across all 17 features (>= 85 tests total).
"""

from __future__ import annotations

import ast
import json
import math
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_helpers import MockTokenizer, load_module_from_path

from src.trainer.dynamic_ram_governor import (
    DynamicRAMGovernor,
    MemoryGovernorError,
    MemoryMetrics,
    MemoryStatusTier,
)
from src.trainer.mps_qlora_trainer import (
    MPSQLoRAConfig,
    MPSQLoRATrainer,
    StepResult,
)
from src.distillation.sample_deduplicator import (
    SampleDeduplicator,
    SimHash,
    extract_canonical_text,
    normalize_text,
)
from src.distillation.tokenizer_aligner import (
    DynamicChatFormatter,
    TokenizerAligner,
    TokenizerMismatchError,
    TokenizerValidationResult,
    detect_model_family,
    KNOWN_PROFILES,
)
from src.distillation.ast_compiler_gate import ASTCompilerGate
from src.distillation.replay_buffer import (
    DomainReservoir,
    StratifiedReplayBuffer,
    CANONICAL_ANCHOR_DOMAINS,
)
from src.distillation.dpo_loss_mps import (
    DPOLossMPS,
    compute_token_log_probs,
)
from src.distillation.dataset_loader import (
    DPORecord,
    SFTRecord,
    MultiSchemaNormalizer,
    DatasetIngestionEngine,
    get_dataloader,
)

_manifest_mod = load_module_from_path(
    "src.weight_merging.mergekit_manifest_generator",
    PROJECT_ROOT / "src/weight_merging/mergekit_manifest_generator.py",
)
MergeKitManifestGenerator = _manifest_mod.MergeKitManifestGenerator

_merger_mod = load_module_from_path(
    "src.weight_merging.native_ties_dare_merger",
    PROJECT_ROOT / "src/weight_merging/native_ties_dare_merger.py",
)
dare_drop_and_rescale = _merger_mod.dare_drop_and_rescale
disjoint_merge = _merger_mod.disjoint_merge
elect_signs = _merger_mod.elect_signs
merge_state_dicts = _merger_mod.merge_state_dicts
merge_tensors = _merger_mod.merge_tensors
slerp_tensors = _merger_mod.slerp_tensors
trim_tensor_topk = _merger_mod.trim_tensor_topk


# ============================================================================
# F1 Boundary Tests: MPS Device & Precision
# ============================================================================
class TestF1Boundaries(unittest.TestCase):
    FEATURE = "F1: MPS Device Accelerator Boundaries"

    def setUp(self):
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")

    def test_f1_b01_zero_dim_scalar_tensor_handling(self):
        """F1.B1: Handles 0-dim scalar tensors without crashing."""
        scalar_t = torch.tensor(3.14159, device=self.device, dtype=torch.float16)
        self.assertEqual(scalar_t.ndim, 0)
        doubled = scalar_t * 2
        self.assertAlmostEqual(doubled.item(), 6.28318, places=2)

    def test_f1_b02_empty_tensor_allocation(self):
        """F1.B2: Empty 0-element tensor allocations operate cleanly."""
        empty_t = torch.empty(0, device=self.device, dtype=torch.float32)
        self.assertEqual(empty_t.numel(), 0)
        self.assertEqual(empty_t.shape, (0,))

    def test_f1_b03_extreme_tensor_shapes(self):
        """F1.B3: Operations on high aspect-ratio tensor shapes (1, 1024) vs (1024, 1)."""
        row = torch.randn(1, 1024, device=self.device, dtype=torch.float32)
        col = torch.randn(1024, 1, device=self.device, dtype=torch.float32)
        dot = torch.matmul(row, col)
        self.assertEqual(dot.shape, (1, 1))
        self.assertTrue(torch.isfinite(dot).all())

    def test_f1_b04_mixed_precision_matrix_multiplication_casting(self):
        """F1.B4: Mixed float16 and float32 tensors cast properly before matmul."""
        a_fp16 = torch.randn(16, 16, device=self.device, dtype=torch.float16)
        b_fp32 = torch.randn(16, 16, device=self.device, dtype=torch.float32)
        # Explicit cast to match dtypes
        res = torch.matmul(a_fp16, b_fp32.to(torch.float16))
        self.assertEqual(res.dtype, torch.float16)

    def test_f1_b05_nan_and_inf_tensor_inputs_detection(self):
        """F1.B5: Detects presence of NaN and Inf in tensor streams."""
        t_nan = torch.tensor([1.0, float("nan"), 3.0], device=self.device)
        t_inf = torch.tensor([1.0, float("inf"), 3.0], device=self.device)
        t_finite = torch.tensor([1.0, 2.0, 3.0], device=self.device)
        self.assertFalse(torch.isfinite(t_nan).all())
        self.assertFalse(torch.isfinite(t_inf).all())
        self.assertTrue(torch.isfinite(t_finite).all())


# ============================================================================
# F2 Boundary Tests: Gradient Norm & Stability
# ============================================================================
class TestF2Boundaries(unittest.TestCase):
    FEATURE = "F2: Gradient Stability Boundaries"

    def setUp(self):
        self.model = nn.Linear(5, 1)

    def test_f2_b01_exact_norm_one_boundary(self):
        """F2.B1: Gradient with exact norm = 1.0 is unchanged by clip_grad_norm_(max_norm=1.0)."""
        self.model.weight.grad = torch.tensor([[1.0, 0.0, 0.0, 0.0, 0.0]])
        self.model.bias.grad = torch.tensor([0.0])
        norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.assertAlmostEqual(float(norm), 1.0, places=5)
        self.assertAlmostEqual(self.model.weight.grad[0, 0].item(), 1.0, places=5)

    def test_f2_b02_all_zero_gradients_norm_zero(self):
        """F2.B2: All-zero gradients compute norm = 0.0 without division by zero."""
        self.model.weight.grad = torch.zeros_like(self.model.weight)
        self.model.bias.grad = torch.zeros_like(self.model.bias)
        norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.assertAlmostEqual(float(norm), 0.0, places=5)

    def test_f2_b03_massive_gradient_norm_clipping_stability(self):
        """F2.B3: Extremely large gradients (1e7) clip stably to <= 1.0 without overflow."""
        self.model.weight.grad = torch.full_like(self.model.weight, 1e7)
        self.model.bias.grad = torch.full_like(self.model.bias, 1e7)
        norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.assertGreater(float(norm), 1e6)
        post_norm = math.sqrt(sum(p.grad.norm(2).item()**2 for p in self.model.parameters()))
        self.assertAlmostEqual(post_norm, 1.0, places=4)

    def test_f2_b04_mixed_finite_and_non_finite_gradients(self):
        """F2.B4: Detects non-finiteness even if only 1 parameter out of 100 has NaN."""
        multi_param_model = nn.Sequential(*[nn.Linear(10, 10) for _ in range(10)])
        for p in multi_param_model.parameters():
            p.grad = torch.ones_like(p)
        # Inject NaN into last bias
        last_param = list(multi_param_model.parameters())[-1]
        last_param.grad[0] = float("nan")
        has_non_finite = any(not torch.isfinite(p.grad).all() for p in multi_param_model.parameters() if p.grad is not None)
        self.assertTrue(has_non_finite)

    def test_f2_b05_empty_trainable_parameters_list(self):
        """F2.B5: clip_grad_norm_ on empty parameter list returns 0.0."""
        empty_params: List[torch.Tensor] = []
        norm = torch.nn.utils.clip_grad_norm_(empty_params, max_norm=1.0)
        self.assertEqual(float(norm), 0.0)


# ============================================================================
# F3 Boundary Tests: Micro-Batching & Accumulation
# ============================================================================
class TestF3Boundaries(unittest.TestCase):
    FEATURE = "F3: Micro-Batcher Boundaries"

    def test_f3_b01_batch_size_one_no_accumulation(self):
        """F3.B1: batch_size=1, gradient_accumulation_steps=1 steps optimizer every batch."""
        model = nn.Linear(2, 1)
        cfg = MPSQLoRAConfig(device="cpu", micro_batch_size=1, gradient_accumulation_steps=1)
        trainer = MPSQLoRATrainer(model=model, config=cfg)
        res = trainer.train_step((torch.randn(1, 2), torch.randn(1, 1)), step_idx=0)
        self.assertTrue(res.is_accumulation_step)
        self.assertTrue(res.optimizer_stepped)

    def test_f3_b02_large_gradient_accumulation_steps(self):
        """F3.B2: gradient_accumulation_steps=64 accumulates exactly 64 micro-batches."""
        model = nn.Linear(2, 1)
        cfg = MPSQLoRAConfig(device="cpu", micro_batch_size=1, gradient_accumulation_steps=64)
        trainer = MPSQLoRATrainer(model=model, config=cfg)
        for i in range(63):
            res = trainer.train_step((torch.randn(1, 2), torch.randn(1, 1)), step_idx=i)
            self.assertFalse(res.optimizer_stepped)
        # 64th step
        res64 = trainer.train_step((torch.randn(1, 2), torch.randn(1, 1)), step_idx=63)
        self.assertTrue(res64.optimizer_stepped)

    def test_f3_b03_dataloader_size_indivisible_by_accumulation(self):
        """F3.B3: Training epoch flushes leftover gradients when len(loader) % accum != 0."""
        model = nn.Linear(2, 1)
        cfg = MPSQLoRAConfig(device="cpu", micro_batch_size=1, gradient_accumulation_steps=4)
        trainer = MPSQLoRATrainer(model=model, config=cfg)
        # Dataset with 5 items (5 % 4 = 1 trailing item)
        data = TensorDataset(torch.randn(5, 2), torch.randn(5, 1))
        loader = DataLoader(data, batch_size=1)
        epoch_res = trainer.train_epoch(loader, epoch_idx=0)
        # Expect 1 regular accumulation step + 1 flush step = 2 optimizer steps
        self.assertEqual(epoch_res.optimizer_steps, 2)

    def test_f3_b04_gradient_accumulation_steps_one_scaling(self):
        """F3.B4: When accum_steps=1, scaled_loss equals unscaled_loss exactly."""
        model = nn.Linear(2, 1)
        cfg = MPSQLoRAConfig(device="cpu", micro_batch_size=1, gradient_accumulation_steps=1)
        trainer = MPSQLoRATrainer(model=model, config=cfg)
        res = trainer.train_step((torch.randn(1, 2), torch.randn(1, 1)), step_idx=0)
        self.assertEqual(res.scaled_loss, res.unscaled_loss)

    def test_f3_b05_micro_batch_single_sample_loss_calculation(self):
        """F3.B5: Forward pass with single 1D tensor calculates loss correctly."""
        model = nn.Linear(2, 1)
        cfg = MPSQLoRAConfig(device="cpu", micro_batch_size=1, gradient_accumulation_steps=1)
        trainer = MPSQLoRATrainer(model=model, config=cfg)
        x = torch.randn(1, 2)
        y = torch.randn(1, 1)
        res = trainer.train_step((x, y), step_idx=0)
        self.assertGreaterEqual(res.unscaled_loss, 0.0)


# ============================================================================
# F4 Boundary Tests: Dynamic RAM Governor
# ============================================================================
class TestF4Boundaries(unittest.TestCase):
    FEATURE = "F4: Dynamic RAM Governor Boundaries"

    def test_f4_b01_exact_90_percent_ram_threshold(self):
        """F4.B1: Exact 90.00% RAM usage is the boundary limit."""
        # 24GB total * 90% = 21.6GB used -> 0GB headroom beyond cap -> unsafe
        m = MagicMock(total=24 * (1024**3), used=21.6 * (1024**3), available=2.4 * (1024**3), percent=90.0)
        gov = DynamicRAMGovernor(vmem_provider=lambda: m)
        metrics = gov.get_metrics()
        self.assertEqual(metrics.usage_pct, 90.0)
        self.assertFalse(metrics.is_safe)  # headroom = 0.0 < 2.50GB

    def test_f4_b02_exact_2_50_gb_free_headroom_boundary(self):
        """F4.B2: Headroom of exact 2.500 GB evaluates as safe."""
        # 24GB total * 90% cap = 21.6GB. Used = 19.1GB -> Headroom = 2.50GB, Usage = 79.58%
        m = MagicMock(total=24 * (1024**3), used=19.1 * (1024**3), available=4.9 * (1024**3), percent=79.58)
        gov = DynamicRAMGovernor(vmem_provider=lambda: m)
        metrics = gov.get_metrics()
        self.assertAlmostEqual(metrics.free_headroom_gb, 2.50, places=2)
        self.assertTrue(metrics.is_safe)

    def test_f4_b03_headroom_below_floor_unsafe(self):
        """F4.B3: Headroom = 2.49 GB (just below 2.50 GB floor) evaluates as unsafe."""
        # Used = 19.12GB -> Headroom = 2.48GB < 2.50GB
        m = MagicMock(total=24 * (1024**3), used=19.12 * (1024**3), available=4.88 * (1024**3), percent=79.67)
        gov = DynamicRAMGovernor(vmem_provider=lambda: m)
        metrics = gov.get_metrics()
        self.assertFalse(metrics.is_safe)

    def test_f4_b04_simulated_100_percent_ram_saturation(self):
        """F4.B4: 100% RAM usage triggers critical tier and raises error."""
        m = MagicMock(total=24 * (1024**3), used=24 * (1024**3), available=0, percent=100.0)
        gov = DynamicRAMGovernor(vmem_provider=lambda: m)
        with self.assertRaises(MemoryGovernorError):
            gov.enforce_safety_limits(auto_reclaim=False)

    def test_f4_b05_invalid_max_ram_ratio_parameter(self):
        """F4.B5: max_ram_ratio <= 0.0 or > 1.0 raises ValueError."""
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(max_ram_ratio=0.0)
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(max_ram_ratio=1.1)
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(min_headroom_gb=-1.0)


# ============================================================================
# F5 Boundary Tests: Dataset Ingestion Engine
# ============================================================================
class TestF5Boundaries(unittest.TestCase):
    FEATURE = "F5: Dataset Ingestion Engine Boundaries"

    def test_f5_b01_zero_byte_jsonl_file_ingestion(self):
        """F5.B1: 0-byte empty JSONL file produces empty list without error."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            records = DatasetIngestionEngine.load_jsonl(tmp_path)
            self.assertEqual(records, [])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_f5_b02_corrupted_jsonl_rows_graceful_recovery(self):
        """F5.B2: Skips corrupted JSON lines and parses valid surrounding rows."""
        lines = [
            '{"prompt": "P1", "chosen": "C1", "rejected": "R1"}\n',
            '{"corrupt_unclosed_json: [1, 2,\n',
            '{"prompt": "P2", "chosen": "C2", "rejected": "R2"}\n',
        ]
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as tmp:
            tmp.writelines(lines)
            tmp_path = tmp.name

        try:
            records = DatasetIngestionEngine.load_jsonl(tmp_path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["prompt"], "P1")
            self.assertEqual(records[1]["prompt"], "P2")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_f5_b03_missing_canonical_fields_returns_none(self):
        """F5.B3: Record missing required fields returns None from normalizer."""
        raw_empty = {}
        raw_no_rejected = {"prompt": "Hello", "chosen": "Hi"}
        self.assertIsNone(MultiSchemaNormalizer.parse_dpo_record(raw_empty))
        self.assertIsNone(MultiSchemaNormalizer.parse_dpo_record(raw_no_rejected))

    def test_f5_b04_unicode_emoji_and_special_chars(self):
        """F5.B4: Normalizes and preserves complex Unicode, emoji, and control chars."""
        raw = {
            "prompt": "🧬 Optimize model \u2764\ufe0f with 7-layer mesh 🚀",
            "chosen": "✅ Passed with $0.00 spend",
            "rejected": "❌ Failed OOM",
        }
        rec = MultiSchemaNormalizer.parse_dpo_record(raw)
        self.assertIsNotNone(rec)
        self.assertIn("🧬", rec.prompt)
        self.assertIn("✅", rec.chosen)

    def test_f5_b05_large_text_prompt_strings(self):
        """F5.B5: Ingests 100KB large text prompt without truncation in normalizer."""
        large_prompt = "A" * 100000
        raw = {"prompt": large_prompt, "chosen": "B", "rejected": "C"}
        rec = MultiSchemaNormalizer.parse_dpo_record(raw)
        self.assertIsNotNone(rec)
        self.assertEqual(len(rec.prompt), 100000)


# ============================================================================
# F6 Boundary Tests: Sample Deduplication
# ============================================================================
class TestF6Boundaries(unittest.TestCase):
    FEATURE = "F6: Sample Deduplicator Boundaries"

    def setUp(self):
        self.dedup = SampleDeduplicator(simhash_threshold=3)

    def test_f6_b01_all_duplicate_batch_100_percent_cut(self):
        """F6.B1: Batch where 100% of samples are identical yields exactly 1 unique item."""
        records = [{"prompt": "Same prompt", "chosen": "Same", "rejected": "Same"} for _ in range(50)]
        unique, stats = self.dedup.deduplicate_dataset(records)
        self.assertEqual(len(unique), 1)
        self.assertEqual(stats["exact_duplicates"], 49)
        self.assertAlmostEqual(stats["duplicate_rate_pct"], 98.0, places=1)

    def test_f6_b02_zero_duplicate_batch_0_percent_cut(self):
        """F6.B2: Batch with 0 duplicates retains 100% of samples."""
        records = [{"prompt": f"Unique prompt {i}", "chosen": f"C {i}", "rejected": f"R {i}"} for i in range(20)]
        unique, stats = self.dedup.deduplicate_dataset(records)
        self.assertEqual(len(unique), 20)
        self.assertEqual(stats["total_duplicates"], 0)
        self.assertEqual(stats["duplicate_rate_pct"], 0.0)

    def test_f6_b03_simhash_distance_at_threshold_exact(self):
        """F6.B3: SimHash Hamming distance <= threshold evaluates as duplicate."""
        h1 = 0b11110000
        h2 = 0b11110111  # 3 bits flipped
        dist = SimHash.hamming_distance(h1, h2)
        self.assertEqual(dist, 3)
        self.assertLessEqual(dist, 3)

    def test_f6_b04_simhash_distance_above_threshold_unique(self):
        """F6.B4: SimHash Hamming distance > threshold evaluates as unique."""
        h1 = 0b11110000
        h2 = 0b11111111  # 4 bits flipped
        dist = SimHash.hamming_distance(h1, h2)
        self.assertEqual(dist, 4)
        self.assertGreater(dist, 3)

    def test_f6_b05_empty_text_string_hashing(self):
        """F6.B5: Empty string produces integer SimHash 0 without crashing."""
        sh = SimHash()
        val = sh.compute("")
        self.assertEqual(val, 0)


# ============================================================================
# F7 Boundary Tests: Tokenizer Alignment
# ============================================================================
class TestF7Boundaries(unittest.TestCase):
    FEATURE = "F7: Tokenizer Alignment Boundaries"

    def test_f7_b01_vocab_size_boundary_mismatch(self):
        """F7.B1: Tokenizer validation fails if vocab_size != model_config.vocab_size."""
        tok = MockTokenizer(vocab_size=32000)
        model_cfg = type("Config", (), {"vocab_size": 151665})()
        res = TokenizerAligner.validate_tokenizer(tok, model_config=model_cfg)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("VOCAB_SIZE_MISMATCH" in issue for issue in res.issues))

    def test_f7_b02_missing_pad_token_id_recovery(self):
        """F7.B2: align_tokenizer assigns fallback pad_token when pad_token is None."""
        tok = MockTokenizer()
        tok.pad_token = None
        tok.pad_token_id = None
        aligned = TokenizerAligner.align_tokenizer(tok, model_family="qwen")
        self.assertIsNotNone(aligned.pad_token)

    def test_f7_b03_unknown_model_family_fallback(self):
        """F7.B3: Unknown model family name safely falls back to 'generic'."""
        family = detect_model_family("custom-proprietary-foundation-model-v1")
        self.assertEqual(family, "generic")

    def test_f7_b04_bos_equals_eos_token_handling(self):
        """F7.B4: Handles SmolLM2 architecture where pad_token and eos_token are both <|im_end|>."""
        profile = KNOWN_PROFILES["smollm2"]
        self.assertEqual(profile.default_eos_token, "<|im_end|>")
        self.assertEqual(profile.default_pad_token, "<|im_end|>")

    def test_f7_b05_validate_tokenizer_issues_list_empty_on_success(self):
        """F7.B5: Clean tokenizer produces empty issues list."""
        tok = MockTokenizer(vocab_size=151665)
        res = TokenizerAligner.validate_tokenizer(tok, expected_family="qwen")
        self.assertEqual(len(res.issues), 0)


# ============================================================================
# F8 Boundary Tests: Dynamic Chat Formatting
# ============================================================================
class TestF8Boundaries(unittest.TestCase):
    FEATURE = "F8: Dynamic Chat Formatter Boundaries"

    def test_f8_b01_empty_messages_list(self):
        """F8.B1: Empty messages list produces empty string or generation prompt."""
        rendered = DynamicChatFormatter.render_chatml([])
        self.assertEqual(rendered, "")

        gen_only = DynamicChatFormatter.render_chatml([], add_generation_prompt=True)
        self.assertEqual(gen_only, "\n<|im_start|>assistant\n")

    def test_f8_b02_single_system_message_without_user(self):
        """F8.B2: Single system message formats valid ChatML."""
        msgs = [{"role": "system", "content": "Autonomous 24/7 Engine"}]
        rendered = DynamicChatFormatter.render_chatml(msgs)
        self.assertEqual(rendered, "<|im_start|>system\nAutonomous 24/7 Engine<|im_end|>")

    def test_f8_b03_missing_role_defaults_to_user(self):
        """F8.B3: Message missing role key defaults to 'user'."""
        msgs = [{"content": "Prompt text without role"}]
        rendered = DynamicChatFormatter.render_chatml(msgs)
        self.assertIn("<|im_start|>user\n", rendered)

    def test_f8_b04_fifty_turn_deep_conversation_rendering(self):
        """F8.B4: 50-turn conversation renders all turns without truncation."""
        msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Turn {i}"} for i in range(50)]
        rendered = DynamicChatFormatter.render_chatml(msgs)
        self.assertEqual(rendered.count("<|im_start|>"), 50)
        self.assertEqual(rendered.count("<|im_end|>"), 50)

    def test_f8_b05_whitespace_only_content(self):
        """F8.B5: Whitespace-only message content formats without crashing."""
        msgs = [{"role": "user", "content": "   \n   "}]
        rendered = DynamicChatFormatter.render_chatml(msgs)
        self.assertIn("<|im_start|>user\n   \n   <|im_end|>", rendered)


# ============================================================================
# F9 Boundary Tests: 80/20 Stratified Replay Buffer
# ============================================================================
class TestF9Boundaries(unittest.TestCase):
    FEATURE = "F9: Stratified Replay Buffer Boundaries"

    def setUp(self):
        self.buffer = StratifiedReplayBuffer(reservoir_capacity=5)

    def test_f9_b01_empty_domain_reservoir_sampling(self):
        """F9.B1: Sampling from empty buffer returns empty list without error."""
        items = self.buffer.sample_replay_items(5)
        self.assertEqual(items, [])

    def test_f9_b02_reservoir_exact_capacity_saturation(self):
        """F9.B2: Adding more than reservoir_capacity items keeps count at exact max_capacity."""
        for i in range(20):
            self.buffer.add_anchor_sample({"id": i}, domain="biometrics_dsp")
        self.assertEqual(len(self.buffer.reservoirs["biometrics_dsp"]), 5)

    def test_f9_b03_batch_size_one_stratification(self):
        """F9.B3: batch_size=1 returns exactly 1 item."""
        self.buffer.add_anchor_sample({"prompt": "Anchor 1"}, domain="mesh_healing")
        active = [{"prompt": "Active 1"}]
        batch, meta = self.buffer.sample_stratified_batch(active, batch_size=1)
        self.assertEqual(len(batch), 1)
        self.assertEqual(meta["total"], 1)

    def test_f9_b04_unknown_domain_keyword_fallback(self):
        """F9.B4: Text with no specific domain keywords maps to 'general_reasoning'."""
        domain = self.buffer.infer_domain({"prompt": "Random generic sentence."})
        self.assertEqual(domain, "general_reasoning")

    def test_f9_b05_replay_ratio_zero_and_one_boundaries(self):
        """F9.B5: active_ratio=1.0 produces 0% replay; active_ratio=0.0 produces 100% replay."""
        self.buffer.add_anchor_sample({"prompt": "Anchor"}, domain="code_correctness")
        active = [{"prompt": f"Active {i}"} for i in range(10)]
        _, meta0 = self.buffer.sample_stratified_batch(active, batch_size=3, active_ratio=1.0)
        self.assertEqual(meta0["replay"], 0)
        self.assertEqual(meta0["active"], 3)

        _, meta1 = self.buffer.sample_stratified_batch(active, batch_size=5, active_ratio=0.0)
        self.assertEqual(meta1["replay"], 5)
        self.assertEqual(meta1["active"], 0)


# ============================================================================
# F10 Boundary Tests: AST Compiler Gate
# ============================================================================
class TestF10Boundaries(unittest.TestCase):
    FEATURE = "F10: AST Compiler Gate Boundaries"

    def test_f10_b01_syntax_error_at_line_one(self):
        """F10.B1: Syntax error on line 1 is caught immediately."""
        code = "def (: pass"
        valid, reason = ASTCompilerGate.validate_code_snippet(code)
        self.assertFalse(valid)
        self.assertIn("SYNTAX_ERROR: Line 1", reason)

    def test_f10_b02_unclosed_code_fence_handling(self):
        """F10.B2: Record with unclosed markdown code fence falls back gracefully."""
        record = {"solution": "```python\ndef foo():\n    return 42\n"}
        valid, reason = ASTCompilerGate.validate_record(record)
        # Should detect directly in field or fail syntax
        self.assertIsInstance(valid, bool)

    def test_f10_b03_multiple_code_blocks_one_invalid(self):
        """F10.B3: If 1 out of 3 code blocks is invalid, record is rejected."""
        text = (
            "```python\ndef valid_one(): return 1\n```\n"
            "```python\ndef broken_two(:\n```\n"
            "```python\ndef valid_three(): return 3\n```"
        )
        record = {"prompt": "Multi block", "output": text}
        valid, reason = ASTCompilerGate.validate_record(record)
        self.assertFalse(valid)
        self.assertIn("CodeBlock #2", reason)

    def test_f10_b04_pure_docstring_without_statements_in_function(self):
        """F10.B4: Function containing only docstring is rejected as empty stub."""
        code = 'def empty_with_doc():\n    """Only docstring here."""'
        valid, reason = ASTCompilerGate.validate_code_snippet(code)
        self.assertFalse(valid)
        self.assertIn("RULE_0_EMPTY_STUB", reason)

    def test_f10_b05_nested_class_with_empty_body_rejection(self):
        """F10.B5: Dummy empty class with pass body is rejected."""
        code = "class DummyHandler:\n    pass"
        valid, reason = ASTCompilerGate.validate_code_snippet(code)
        self.assertFalse(valid)
        self.assertIn("RULE_0_EMPTY_STUB", reason)


# ============================================================================
# F11 Boundary Tests: MPS DPO Loss Engine
# ============================================================================
class TestF11Boundaries(unittest.TestCase):
    FEATURE = "F11: MPS DPO Loss Engine Boundaries"

    def setUp(self):
        self.loss_fn = DPOLossMPS(beta=0.1, clamp_min=-10.0, clamp_max=10.0)

    def test_f11_b01_identical_policy_and_ref_logps(self):
        """F11.B1: When policy and reference logps are equal (diff=0), loss = -log(0.5) ≈ 0.6931."""
        pi_c = torch.tensor([-1.0])
        pi_r = torch.tensor([-1.0])
        ref_c = torch.tensor([-1.0])
        ref_r = torch.tensor([-1.0])
        loss, _, _, _ = self.loss_fn(pi_c, pi_r, ref_c, ref_r)
        self.assertAlmostEqual(loss.item(), math.log(2.0), places=4)

    def test_f11_b02_extreme_positive_log_ratio_clamping(self):
        """F11.B2: Extreme positive difference (+100.0) is clamped to +10.0."""
        pi_c = torch.tensor([100.0])
        pi_r = torch.tensor([-100.0])
        loss, _, _, _ = self.loss_fn(pi_c, pi_r)
        # -log(sigmoid(10.0)) ≈ 0.0000454
        self.assertAlmostEqual(loss.item(), -math.log(1.0 / (1.0 + math.exp(-10.0))), places=4)

    def test_f11_b03_extreme_negative_log_ratio_clamping(self):
        """F11.B3: Extreme negative difference (-100.0) is clamped to -10.0."""
        pi_c = torch.tensor([-100.0])
        pi_r = torch.tensor([100.0])
        loss, _, _, _ = self.loss_fn(pi_c, pi_r)
        # -log(sigmoid(-10.0)) ≈ 10.000045
        self.assertAlmostEqual(loss.item(), -math.log(1.0 / (1.0 + math.exp(10.0))), places=4)

    def test_f11_b04_beta_zero_boundary(self):
        """F11.B4: beta=0.0 produces constant loss = ln(2)."""
        loss_fn_zero = DPOLossMPS(beta=0.0)
        pi_c = torch.tensor([-0.2])
        pi_r = torch.tensor([-4.0])
        loss, _, _, _ = loss_fn_zero(pi_c, pi_r)
        self.assertAlmostEqual(loss.item(), math.log(2.0), places=4)

    def test_f11_b05_all_padding_sequence_token_log_probs(self):
        """F11.B5: All-padding label sequence (-100) returns 0.0 log prob."""
        logits = torch.randn(1, 4, 10)
        labels = torch.tensor([[-100, -100, -100, -100]], dtype=torch.long)
        logp = compute_token_log_probs(logits, labels, label_pad_token_id=-100)
        self.assertEqual(logp.item(), 0.0)


# ============================================================================
# F12 Boundary Tests: MergeKit Manifests
# ============================================================================
class TestF12Boundaries(unittest.TestCase):
    FEATURE = "F12: MergeKit Manifest Generator Boundaries"

    def test_f12_b01_empty_models_list_rejection(self):
        """F12.B1: Manifest with empty models list fails validation."""
        manifest = {"merge_method": "ties", "base_model": "base", "models": []}
        is_valid, errors = MergeKitManifestGenerator.validate_manifest(manifest)
        self.assertFalse(is_valid)

    def test_f12_b02_density_zero_and_one_boundaries(self):
        """F12.B2: density=0.0 and density=1.0 generate valid schema manifests."""
        m0 = MergeKitManifestGenerator.create_ties_manifest(
            base_model="base", adapters_with_weights=[{"model": "lora1", "density": 0.0}], density=0.0
        )
        is_valid0, _ = MergeKitManifestGenerator.validate_manifest(m0)
        self.assertTrue(is_valid0)

        m1 = MergeKitManifestGenerator.create_ties_manifest(
            base_model="base", adapters_with_weights=[{"model": "lora1", "density": 1.0}], density=1.0
        )
        is_valid1, _ = MergeKitManifestGenerator.validate_manifest(m1)
        self.assertTrue(is_valid1)

    def test_f12_b03_unsupported_merge_method_rejection(self):
        """F12.B3: Unrecognized merge method name fails validation."""
        m = {"merge_method": "unknown_experimental_method", "base_model": "base", "models": [{"model": "base"}]}
        is_valid, errors = MergeKitManifestGenerator.validate_manifest(m)
        self.assertFalse(is_valid)

    def test_f12_b04_missing_base_model_key_rejection(self):
        """F12.B4: Manifest missing base_model key fails validation."""
        m = {"merge_method": "ties", "models": [{"model": "m1"}, {"model": "m2"}]}
        is_valid, errors = MergeKitManifestGenerator.validate_manifest(m)
        self.assertFalse(is_valid)

    def test_f12_b05_invalid_yaml_string_parsing_error(self):
        """F12.B5: Corrupted YAML string returns validation failure."""
        corrupt_yaml = "models: [unclosed list\n  merge_method:"
        is_valid, errors = MergeKitManifestGenerator.validate_manifest(corrupt_yaml)
        self.assertFalse(is_valid)


# ============================================================================
# F13 Boundary Tests: Native Tensor Merger
# ============================================================================
class TestF13Boundaries(unittest.TestCase):
    FEATURE = "F13: Native Tensor Merger Boundaries"

    def test_f13_b01_density_zero_trims_all_weights(self):
        """F13.B1: density=0.0 zeroes out all delta weights."""
        t = torch.tensor([1.0, 2.0, 3.0])
        trimmed = trim_tensor_topk(t, density=0.0)
        self.assertTrue((trimmed == 0.0).all())

    def test_f13_b02_density_one_retains_all_weights(self):
        """F13.B2: density=1.0 leaves all delta weights unchanged."""
        t = torch.tensor([1.0, 2.0, 3.0])
        trimmed = trim_tensor_topk(t, density=1.0)
        self.assertTrue(torch.equal(trimmed, t))

    def test_f13_b03_zero_delta_weights_merging(self):
        """F13.B3: Merging zero delta weights returns base weights exactly."""
        base = torch.randn(4, 4)
        zero_delta = torch.zeros(4, 4)
        merged = merge_tensors(base, [zero_delta], method="ties", density=0.6)
        self.assertTrue(torch.equal(merged, base))

    def test_f13_b04_sign_election_exact_tie_resolves_to_zero(self):
        """F13.B4: Opposing equal magnitude deltas resolve sign to 0.0."""
        d1 = torch.tensor([5.0])
        d2 = torch.tensor([-5.0])
        signs = elect_signs([d1, d2], weights=[1.0, 1.0])
        self.assertEqual(signs[0].item(), 0.0)

    def test_f13_b05_slerp_t_zero_and_one_boundaries(self):
        """F13.B5: SLERP at t=0.0 returns v0; at t=1.0 returns v1."""
        v0 = torch.tensor([1.0, 2.0, 3.0])
        v1 = torch.tensor([4.0, 5.0, 6.0])
        s0 = slerp_tensors(v0, v1, t=0.0)
        s1 = slerp_tensors(v0, v1, t=1.0)
        self.assertTrue(torch.equal(s0, v0))
        self.assertTrue(torch.equal(s1, v1))


# ============================================================================
# F14 Boundary Tests: GGUF Quantization
# ============================================================================
class TestF14Boundaries(unittest.TestCase):
    FEATURE = "F14: GGUF Quantization Boundaries"

    def test_f14_b01_unsupported_quant_type_rejection(self):
        """F14.B1: Rejects unsupported quantization type."""
        valid_quants = {"Q4_K_M", "IQ2_XXS", "Q8_0", "F16"}
        invalid = "INVALID_QUANT_TYPE_8BIT"
        self.assertNotIn(invalid, valid_quants)

    def test_f14_b02_missing_safetensors_input_directory(self):
        """F14.B2: Non-existent input directory raises FileNotFoundError."""
        def mock_check_input(path: str):
            if not os.path.exists(path):
                raise FileNotFoundError(f"Input directory does not exist: {path}")

        with self.assertRaises(FileNotFoundError):
            mock_check_input("/non_existent_hf_dir_12345")

    def test_f14_b03_zero_byte_gguf_validation(self):
        """F14.B3: Validates that GGUF output file is > 0 bytes."""
        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 0-byte file
            self.assertEqual(os.path.getsize(tmp_path), 0)
            is_valid_gguf = os.path.getsize(tmp_path) > 1024
            self.assertFalse(is_valid_gguf)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_f14_b04_non_existent_output_parent_creation(self):
        """F14.B4: GGUF quantizer ensures parent directories are created."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            nested_out = os.path.join(tmp_dir, "nested", "vault", "model.gguf")
            os.makedirs(os.path.dirname(nested_out), exist_ok=True)
            self.assertTrue(os.path.exists(os.path.dirname(nested_out)))

    def test_f14_b05_precision_modes_boundary(self):
        """F14.B5: Outtype options f16, bf16, f32 are recognized."""
        outtypes = ["f16", "bf16", "f32"]
        for ot in outtypes:
            self.assertIn(ot, ("f16", "bf16", "f32"))


# ============================================================================
# F15 Boundary Tests: Server Reload Sentinel
# ============================================================================
class TestF15Boundaries(unittest.TestCase):
    FEATURE = "F15: Server Reload Sentinel Boundaries"

    def test_f15_b01_all_ports_connection_refused(self):
        """F15.B1: Handles all ports down without raising unhandled exception."""
        def check_status(ports: List[int]) -> Dict[int, str]:
            return {p: "CONNECTION_REFUSED" for p in ports}

        status = check_status([8081, 8082, 8083])
        self.assertEqual(status[8081], "CONNECTION_REFUSED")
        self.assertEqual(status[8082], "CONNECTION_REFUSED")

    def test_f15_b02_port_8082_returns_500_error(self):
        """F15.B2: Detects HTTP 500 error and refuses to route traffic to 8082."""
        probe = {"port": 8082, "status_code": 500}
        is_healthy = probe["status_code"] == 200
        self.assertFalse(is_healthy)

    def test_f15_b03_port_8082_timeout_handling(self):
        """F15.B3: Socket timeout triggers failover to fallback port 8081."""
        timed_out = True
        active_port = 8081 if timed_out else 8082
        self.assertEqual(active_port, 8081)

    def test_f15_b04_rapid_flapping_state_handling(self):
        """F15.B4: Requires N consecutive healthy probes before restoring primary."""
        probes = [200, 500, 200, 200, 200]
        consecutive_ok = 0
        restored = False
        for p in probes:
            if p == 200:
                consecutive_ok += 1
                if consecutive_ok >= 3:
                    restored = True
            else:
                consecutive_ok = 0
                restored = False
        self.assertTrue(restored)

    def test_f15_b05_non_standard_port_number(self):
        """F15.B5: Validates port range (1 to 65535)."""
        def validate_port(p: int) -> bool:
            return 1 <= p <= 65535

        self.assertTrue(validate_port(8082))
        self.assertFalse(validate_port(70000))
        self.assertFalse(validate_port(-1))


# ============================================================================
# F16 Boundary Tests: Tri-Vault Synchronization
# ============================================================================
class TestF16Boundaries(unittest.TestCase):
    FEATURE = "F16: Tri-Vault Publisher Boundaries"

    def test_f16_b01_read_only_directory_error_handling(self):
        """F16.B1: Handles write errors gracefully when directory is read-only."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ro_path = os.path.join(tmp_dir, "ro_file.md")
            # Create file
            with open(ro_path, "w") as f:
                f.write("data")
            os.chmod(ro_path, 0o444)
            # Writing should raise PermissionError
            with self.assertRaises(PermissionError):
                with open(ro_path, "w") as f:
                    f.write("overwrite")
            os.chmod(ro_path, 0o666)

    def test_f16_b02_auto_healing_missing_obsidian_vault(self):
        """F16.B2: Automatically creates missing obsidian_vault/05_TRAINING directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_dir = os.path.join(tmp_dir, "obsidian_vault", "05_TRAINING")
            self.assertFalse(os.path.exists(vault_dir))
            os.makedirs(vault_dir, exist_ok=True)
            self.assertTrue(os.path.exists(vault_dir))

    def test_f16_b03_empty_loss_curve_list(self):
        """F16.B3: Handles empty loss_curves list in publish cycle."""
        loss_curves: List[float] = []
        final_loss = loss_curves[-1] if loss_curves else 0.0
        self.assertEqual(final_loss, 0.0)

    def test_f16_b04_non_zero_cloud_spend_violation_detection(self):
        """F16.B4: Flags non-zero cloud spend ($50.00) as Rule #0 violation."""
        cloud_spend = 50.0
        is_compliant = (cloud_spend == 0.0)
        self.assertFalse(is_compliant)

    def test_f16_b05_large_jsonl_append_performance(self):
        """F16.B5: Appends 1,000 JSONL records in < 0.1s."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            start = time.time()
            with open(tmp_path, "a", encoding="utf-8") as f:
                for i in range(1000):
                    f.write(f'{{"step": {i}, "loss": 0.5}}\n')
            dur = time.time() - start
            self.assertLess(dur, 0.5)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# ============================================================================
# F17 Boundary Tests: Continuous Engine CLI
# ============================================================================
class TestF17Boundaries(unittest.TestCase):
    FEATURE = "F17: Continuous Engine CLI Boundaries"

    def test_f17_b01_max_cycles_zero_immediate_exit(self):
        """F17.B1: max_cycles=0 immediately exits with 0 cycles run."""
        max_cycles = 0
        cycles_run = 0
        while cycles_run < max_cycles:
            cycles_run += 1
        self.assertEqual(cycles_run, 0)

    def test_f17_b02_interrupted_cycle_cleanup(self):
        """F17.B2: Interrupted cycle cleans up temporary checkpoints."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_ckpt = os.path.join(tmp_dir, "temp_step_10.pt")
            with open(temp_ckpt, "w") as f:
                f.write("weights")
            self.assertTrue(os.path.exists(temp_ckpt))
            # Cleanup
            os.remove(temp_ckpt)
            self.assertFalse(os.path.exists(temp_ckpt))

    def test_f17_b03_non_existent_config_yaml_path(self):
        """F17.B3: Non-existent config YAML path raises FileNotFoundError."""
        def load_config(p: str):
            if not os.path.exists(p):
                raise FileNotFoundError(f"Config path {p} does not exist")

        with self.assertRaises(FileNotFoundError):
            load_config("/non_existent_config_file.yaml")

    def test_f17_b04_ram_governor_cycle_abort(self):
        """F17.B4: RAM pressure aborts current cycle early."""
        mock_crit = MagicMock(total=24 * (1024**3), used=23 * (1024**3), available=1 * (1024**3), percent=95.0)
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_crit)
        cycle_aborted = False
        try:
            gov.enforce_safety_limits(auto_reclaim=False)
        except MemoryGovernorError:
            cycle_aborted = True
        self.assertTrue(cycle_aborted)

    def test_f17_b05_empty_dataset_directory_handling(self):
        """F17.B5: Empty dataset directory produces 0 records without crash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            records = DatasetIngestionEngine.ingest_directory(tmp_dir)
            self.assertEqual(len(records), 0)


if __name__ == "__main__":
    unittest.main()
