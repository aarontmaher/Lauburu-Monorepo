"""
Shared helper utilities, model loaders, and test fixtures for E2E testing.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_module_from_path(module_name: str, file_path: Union[str, Path]) -> Any:
    """Safely loads a python module from explicit file path without triggering broken sibling __init__ imports."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Module file not found: {p}")

    spec = importlib.util.spec_from_file_location(module_name, str(p))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {module_name} at {p}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


class MockCausalLM(nn.Module):
    """A minimal mock causal LM module for testing tensor operations and loss passes."""

    def __init__(self, vocab_size: int = 1000, hidden_dim: int = 64, num_layers: int = 2):
        super().__init__()
        self.config = type("Config", (), {"vocab_size": vocab_size, "hidden_size": hidden_dim})()
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.layers = nn.ModuleList([nn.Linear(hidden_dim, hidden_dim) for _ in range(num_layers)])
        self.head = nn.Linear(hidden_dim, vocab_size, bias=False)

    def forward(self, input_ids: torch.Tensor, attention_mask: Optional[torch.Tensor] = None, **kwargs) -> Any:
        x = self.embedding(input_ids)
        for layer in self.layers:
            x = torch.relu(layer(x))
        logits = self.head(x)
        output = type("CausalLMOutput", (), {"logits": logits, "loss": None})()
        return output


class MockTokenizer:
    """A deterministic tokenizer mock for vocabulary alignment and chat formatting tests."""

    def __init__(self, vocab_size: int = 32000, name_or_path: str = "qwen2.5-3b"):
        self.vocab_size = vocab_size
        self.name_or_path = name_or_path
        self.pad_token = "<|endoftext|>"
        self.pad_token_id = 0
        self.eos_token = "<|im_end|>"
        self.eos_token_id = 1
        self.bos_token = None
        self.bos_token_id = None
        self.padding_side = "right"
        self.chat_template = None

    def __call__(
        self,
        text: Union[str, List[str]],
        truncation: bool = True,
        max_length: int = 512,
        padding: bool = True,
        return_tensors: Optional[str] = "pt",
    ) -> Dict[str, Any]:
        if isinstance(text, str):
            text = [text]

        seqs = []
        for t in text:
            words = t.split()
            tokens = [abs(hash(w)) % (self.vocab_size - 10) + 2 for w in words]
            if not tokens:
                tokens = [self.eos_token_id]
            if truncation and len(tokens) > max_length:
                tokens = tokens[:max_length]
            seqs.append(tokens)

        max_l = max(len(s) for s in seqs) if seqs else 1
        if padding:
            padded = []
            masks = []
            for s in seqs:
                p_len = max_l - len(s)
                padded.append(s + [self.pad_token_id] * p_len)
                masks.append([1] * len(s) + [0] * p_len)
            input_ids = torch.tensor(padded, dtype=torch.long)
            attention_mask = torch.tensor(masks, dtype=torch.long)
        else:
            input_ids = [torch.tensor(s, dtype=torch.long) for s in seqs]
            attention_mask = [torch.ones_like(ids) for ids in input_ids]
            if len(input_ids) == 1:
                input_ids = input_ids[0]
                attention_mask = attention_mask[0]

        if return_tensors == "pt":
            return {"input_ids": input_ids, "attention_mask": attention_mask}
        return {"input_ids": seqs}

    def convert_tokens_to_ids(self, token: str) -> int:
        if token == self.pad_token:
            return self.pad_token_id
        if token == self.eos_token:
            return self.eos_token_id
        return 2

    def get_vocab(self) -> Dict[str, int]:
        return {self.pad_token: self.pad_token_id, self.eos_token: self.eos_token_id}
