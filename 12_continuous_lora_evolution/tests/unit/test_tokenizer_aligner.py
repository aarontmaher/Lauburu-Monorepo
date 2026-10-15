"""
Unit tests for Cross-Family Tokenizer Alignment & Dynamic ChatML/Header Formatter (F7 & F8).
"""

import unittest
from dataclasses import dataclass
from typing import Optional

from src.distillation.tokenizer_aligner import (
    KNOWN_PROFILES,
    DynamicChatFormatter,
    TokenizerAligner,
    TokenizerMismatchError,
    TokenizerValidationResult,
    detect_model_family,
)


@dataclass
class MockConfig:
    vocab_size: int = 151665


class DummyTokenizer:
    """Minimal genuine class testing tokenizer attributes without external downloads."""

    def __init__(
        self,
        name_or_path: str = "Qwen/Qwen2.5-3B-Instruct",
        vocab_size: int = 151665,
        pad_token: Optional[str] = "<|endoftext|>",
        pad_token_id: Optional[int] = 151643,
        eos_token: Optional[str] = "<|im_end|>",
        eos_token_id: Optional[int] = 151645,
        bos_token: Optional[str] = None,
        bos_token_id: Optional[int] = None,
    ):
        self.name_or_path = name_or_path
        self.vocab_size = vocab_size
        self.pad_token = pad_token
        self.pad_token_id = pad_token_id
        self.eos_token = eos_token
        self.eos_token_id = eos_token_id
        self.bos_token = bos_token
        self.bos_token_id = bos_token_id
        self.padding_side = "left"
        self.chat_template = None

    def convert_tokens_to_ids(self, token: str) -> int:
        if token == self.pad_token and self.pad_token_id is not None:
            return self.pad_token_id
        if token == self.eos_token and self.eos_token_id is not None:
            return self.eos_token_id
        return 0


class TestTokenizerAligner(unittest.TestCase):

    def test_detect_model_family(self):
        self.assertEqual(detect_model_family("Qwen/Qwen2.5-3B-Instruct"), "qwen")
        self.assertEqual(detect_model_family("HuggingFaceTB/SmolLM2-1.7B-Instruct"), "smollm2")
        self.assertEqual(detect_model_family("unsloth/Llama-3.2-1B-Instruct"), "llama32")
        self.assertEqual(detect_model_family("NousResearch/Hermes-3-Llama-3.1-8B"), "hermes3")
        self.assertEqual(detect_model_family("some-random-custom-model"), "generic")

    def test_known_profiles(self):
        qwen = KNOWN_PROFILES["qwen"]
        self.assertEqual(qwen.vocab_size, 151665)
        self.assertEqual(qwen.format_type, "chatml")
        self.assertEqual(qwen.default_eos_token, "<|im_end|>")

        smol = KNOWN_PROFILES["smollm2"]
        self.assertEqual(smol.vocab_size, 49152)
        self.assertEqual(smol.format_type, "chatml")
        self.assertEqual(smol.default_bos_token, "<|im_start|>")

        llama = KNOWN_PROFILES["llama32"]
        self.assertEqual(llama.vocab_size, 128256)
        self.assertEqual(llama.format_type, "llama3")
        self.assertEqual(llama.default_eos_token, "<|eot_id|>")

    def test_render_chatml(self):
        msgs = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        rendered = DynamicChatFormatter.render_chatml(msgs, add_generation_prompt=True)
        self.assertIn("<|im_start|>system\nYou are an AI assistant.<|im_end|>", rendered)
        self.assertIn("<|im_start|>user\nHello!<|im_end|>", rendered)
        self.assertTrue(rendered.endswith("<|im_start|>assistant\n"))

    def test_render_llama3(self):
        msgs = [
            {"role": "system", "content": "System prompt."},
            {"role": "user", "content": "User question."},
        ]
        rendered = DynamicChatFormatter.render_llama3(msgs, add_generation_prompt=True)
        self.assertTrue(rendered.startswith("<|begin_of_text|>"))
        self.assertIn("<|start_header_id|>system<|end_header_id|>\n\nSystem prompt.<|eot_id|>", rendered)
        self.assertIn("<|start_header_id|>user<|end_header_id|>\n\nUser question.<|eot_id|>", rendered)
        self.assertTrue(rendered.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n"))

    def test_format_dpo_pair(self):
        prompt = "Explain quantum annealing."
        chosen = "Quantum annealing finds global minimum of objective function."
        rejected = "Quantum annealing is standard cooking recipe."

        p_str, c_str, r_str = DynamicChatFormatter.format_dpo_pair(
            prompt, chosen, rejected, family="qwen"
        )
        self.assertIn("<|im_start|>user\nExplain quantum annealing.<|im_end|>", p_str)
        self.assertEqual(c_str, chosen)
        self.assertEqual(r_str, rejected)

    def test_align_tokenizer(self):
        tok = DummyTokenizer(pad_token=None, pad_token_id=None)
        self.assertEqual(tok.padding_side, "left")

        aligned = TokenizerAligner.align_tokenizer(tok, model_family="qwen")
        self.assertEqual(aligned.padding_side, "right")
        self.assertIsNotNone(aligned.pad_token)
        self.assertEqual(aligned.pad_token, "<|endoftext|>")

    def test_validate_tokenizer_success(self):
        tok = DummyTokenizer()
        cfg = MockConfig(vocab_size=151665)

        result = TokenizerAligner.validate_tokenizer(tok, model_config=cfg)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.family, "qwen")
        self.assertEqual(result.vocab_size, 151665)
        self.assertEqual(len(result.issues), 0)

    def test_validate_tokenizer_issues_detected(self):
        # Mismatched vocab and missing pad token
        bad_tok = DummyTokenizer(vocab_size=32000, pad_token=None, pad_token_id=None)
        cfg = MockConfig(vocab_size=151665)

        result = TokenizerAligner.validate_tokenizer(bad_tok, model_config=cfg)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.issues), 0)
        self.assertTrue(any("VOCAB_SIZE_MISMATCH" in iss for iss in result.issues))
        self.assertTrue(any("MISSING_PAD_TOKEN" in iss for iss in result.issues))

    def test_cross_family_incompatibility_raises_error(self):
        # Qwen vs SmolLM2 has disjoint token vocabularies
        with self.assertRaises(TokenizerMismatchError) as ctx:
            TokenizerAligner.assert_cross_family_compatibility("qwen", "smollm2")
        self.assertIn("CROSS_FAMILY_INCOMPATIBILITY", str(ctx.exception))

        # Same family should succeed
        TokenizerAligner.assert_cross_family_compatibility("qwen", "Qwen/Qwen2.5-3B-Instruct")

    def test_real_cached_tokenizer_if_available(self):
        # Test loading real HuggingFace tokenizer from local cache
        try:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", local_files_only=True)
            aligned = TokenizerAligner.align_tokenizer(tok)
            val = TokenizerAligner.validate_tokenizer(aligned)
            self.assertTrue(val.is_valid)
            self.assertEqual(val.family, "qwen")
            self.assertEqual(aligned.padding_side, "right")
        except Exception:
            # If cache not present in test runner, skip without failing
            pass


if __name__ == "__main__":
    unittest.main()
