"""
Multi-Schema Dataset Ingestion & DataLoader Engine for Continuous DPO & SFT Distillation.

Supports:
- DPO preference pairs (prompt, chosen, rejected)
- SFT instruction-response (instruction, input, output)
- CoT thought-solution (<thought>...</thought>)
- Multi-turn role-based messages
- Automated deduplication, AST compiler gating, and 80/20 replay buffer mixing
- Tokenized PyTorch DataLoader with dynamic padding and label masking
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import torch
from torch.utils.data import DataLoader, Dataset

from .ast_compiler_gate import ASTCompilerGate
from .replay_buffer import StratifiedReplayBuffer
from .sample_deduplicator import SampleDeduplicator
from .tokenizer_aligner import DynamicChatFormatter, TokenizerAligner, detect_model_family

logger = logging.getLogger(__name__)


@dataclass
class DPORecord:
    """Canonical Direct Preference Optimization Record."""
    prompt: str
    chosen: str
    rejected: str
    domain: str = "general_reasoning"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "domain": self.domain,
            "metadata": self.metadata,
        }


@dataclass
class SFTRecord:
    """Canonical Supervised Fine-Tuning Record."""
    prompt: str
    response: str
    domain: str = "general_reasoning"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "response": self.response,
            "domain": self.domain,
            "metadata": self.metadata,
        }


class MultiSchemaNormalizer:
    """
    Normalizes diverse raw JSON lines from lora_datasets/ into canonical DPORecord or SFTRecord.
    """

    @classmethod
    def parse_dpo_record(cls, raw: Dict[str, Any]) -> Optional[DPORecord]:
        """Parses arbitrary dictionary into a DPORecord if valid DPO fields exist."""
        prompt = ""
        chosen = ""
        rejected = ""
        domain = raw.get("domain", "general_reasoning")
        metadata = raw.get("metadata") or raw.get("meta") or {}
        if not isinstance(metadata, dict):
            metadata = {"raw_meta": metadata}

        # Format 1: standard prompt, chosen, rejected
        if "prompt" in raw and "chosen" in raw and "rejected" in raw:
            prompt = str(raw["prompt"])
            chosen = str(raw["chosen"])
            rejected = str(raw["rejected"])
        # Format 2: instruction with chosen / rejected
        elif "instruction" in raw and "chosen" in raw and "rejected" in raw:
            inst = str(raw["instruction"])
            inp = str(raw.get("input", ""))
            prompt = f"{inst}\n{inp}".strip() if inp else inst
            chosen = str(raw["chosen"])
            rejected = str(raw["rejected"])
        # Format 3: pairwise turns (e.g., continuous_master_agi_distillation)
        elif "turns" in raw and isinstance(raw["turns"], list) and len(raw["turns"]) >= 2:
            prompt = str(raw["turns"][0].get("content", ""))
            chosen = str(raw["turns"][1].get("chosen", raw["turns"][1].get("content", "")))
            rejected = str(raw["turns"][1].get("rejected", ""))
        else:
            return None

        if not prompt.strip() or not chosen.strip() or not rejected.strip():
            return None

        return DPORecord(
            prompt=prompt.strip(),
            chosen=chosen.strip(),
            rejected=rejected.strip(),
            domain=domain,
            metadata=metadata,
        )

    @classmethod
    def parse_sft_record(cls, raw: Dict[str, Any]) -> Optional[SFTRecord]:
        """Parses arbitrary dictionary into an SFTRecord."""
        domain = raw.get("domain", "general_reasoning")
        metadata = raw.get("metadata") or raw.get("meta") or {}
        if not isinstance(metadata, dict):
            metadata = {"raw_meta": metadata}

        # Format 1: messages array
        if "messages" in raw and isinstance(raw["messages"], list):
            msgs = raw["messages"]
            if not msgs:
                return None
            # Extract last assistant message as response, preceding as prompt
            if msgs[-1].get("role") == "assistant":
                response = msgs[-1].get("content", "")
                prompt = DynamicChatFormatter.render_chatml(msgs[:-1], add_generation_prompt=True)
                return SFTRecord(prompt=prompt, response=response, domain=domain, metadata=metadata)

        # Format 2: thought / solution CoT
        if "instruction" in raw and ("thought" in raw or "think" in raw) and ("solution" in raw or "output" in raw):
            inst = str(raw["instruction"])
            inp = str(raw.get("input", ""))
            prompt = f"{inst}\n{inp}".strip() if inp else inst
            thought = str(raw.get("thought") or raw.get("think") or "")
            sol = str(raw.get("solution") or raw.get("output") or "")
            response = f"<thought>\n{thought}\n</thought>\n{sol}"
            return SFTRecord(prompt=prompt, response=response, domain=domain, metadata=metadata)

        # Format 3: instruction, input, output
        if "instruction" in raw and ("output" in raw or "response" in raw):
            inst = str(raw["instruction"])
            inp = str(raw.get("input", ""))
            prompt = f"{inst}\n{inp}".strip() if inp else inst
            resp = str(raw.get("output") or raw.get("response") or "")
            return SFTRecord(prompt=prompt, response=resp, domain=domain, metadata=metadata)

        # Format 4: generic prompt and response
        if "prompt" in raw and "response" in raw:
            return SFTRecord(
                prompt=str(raw["prompt"]).strip(),
                response=str(raw["response"]).strip(),
                domain=domain,
                metadata=metadata,
            )

        return None


class DatasetIngestionEngine:
    """
    Ingests and validates raw dataset files from disk or in-memory lists.
    """

    @classmethod
    def load_jsonl(cls, filepath: str) -> List[Dict[str, Any]]:
        """Safely loads lines from a JSONL file, catching decode errors."""
        records: List[Dict[str, Any]] = []
        if not os.path.exists(filepath):
            logger.warning(f"Dataset path not found: {filepath}")
            return records

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if isinstance(data, dict):
                        records.append(data)
                except json.JSONDecodeError as e:
                    logger.debug(f"JSONDecodeError at {filepath}:{line_no}: {e}")
                    continue
        return records

    @classmethod
    def ingest_directory(
        cls, directory_path: str, extensions: Tuple[str, ...] = (".jsonl", ".json")
    ) -> List[Dict[str, Any]]:
        """Recursively ingests all dataset files in a directory."""
        all_records: List[Dict[str, Any]] = []
        if not os.path.exists(directory_path):
            return all_records

        for root, _, files in os.walk(directory_path):
            for file in sorted(files):
                if any(file.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    all_records.extend(cls.load_jsonl(full_path))
        return all_records

    @classmethod
    def process_dpo_records(
        cls,
        raw_records: List[Dict[str, Any]],
        deduplicate: bool = True,
        ast_validate: bool = True,
        deduplicator: Optional[SampleDeduplicator] = None,
        quarantine_path: Optional[str] = None,
    ) -> List[DPORecord]:
        """
        Normalizes, deduplicates, and validates DPO records.
        """
        parsed: List[Dict[str, Any]] = []
        for r in raw_records:
            dpo_rec = MultiSchemaNormalizer.parse_dpo_record(r)
            if dpo_rec is not None:
                parsed.append(dpo_rec.to_dict())

        # AST Gate & Zero-Mock Check
        if ast_validate:
            parsed, _ = ASTCompilerGate.filter_and_quarantine(parsed, quarantine_path=quarantine_path)

        # Deduplication
        if deduplicate:
            dedup = deduplicator or SampleDeduplicator()
            parsed, _ = dedup.deduplicate_dataset(parsed)

        return [
            DPORecord(
                prompt=p["prompt"],
                chosen=p["chosen"],
                rejected=p["rejected"],
                domain=p.get("domain", "general_reasoning"),
                metadata=p.get("metadata", {}),
            )
            for p in parsed
        ]

    @classmethod
    def process_sft_records(
        cls,
        raw_records: List[Dict[str, Any]],
        deduplicate: bool = True,
        ast_validate: bool = True,
        deduplicator: Optional[SampleDeduplicator] = None,
        quarantine_path: Optional[str] = None,
    ) -> List[SFTRecord]:
        """
        Normalizes, deduplicates, and validates SFT records.
        """
        parsed: List[Dict[str, Any]] = []
        for r in raw_records:
            sft_rec = MultiSchemaNormalizer.parse_sft_record(r)
            if sft_rec is not None:
                parsed.append(sft_rec.to_dict())

        # AST Gate & Zero-Mock Check
        if ast_validate:
            parsed, _ = ASTCompilerGate.filter_and_quarantine(parsed, quarantine_path=quarantine_path)

        # Deduplication
        if deduplicate:
            dedup = deduplicator or SampleDeduplicator()
            parsed, _ = dedup.deduplicate_dataset(parsed)

        return [
            SFTRecord(
                prompt=p["prompt"],
                response=p["response"],
                domain=p.get("domain", "general_reasoning"),
                metadata=p.get("metadata", {}),
            )
            for p in parsed
        ]


class ContinuousDPODataset(Dataset):
    """
    PyTorch Dataset for Direct Preference Optimization pairs.
    """

    def __init__(self, records: List[DPORecord]):
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.records[idx].to_dict()


class ContinuousSFTDataset(Dataset):
    """
    PyTorch Dataset for Supervised Fine-Tuning instruction pairs.
    """

    def __init__(self, records: List[SFTRecord]):
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.records[idx].to_dict()


class DPODataCollator:
    """
    Collates and tokenizes DPO batches with proper right-padding and labels.
    """

    def __init__(
        self,
        tokenizer: Any,
        max_length: int = 1024,
        max_prompt_length: int = 512,
        label_pad_token_id: int = -100,
    ):
        self.tokenizer = TokenizerAligner.align_tokenizer(tokenizer)
        self.max_length = max_length
        self.max_prompt_length = max_prompt_length
        self.label_pad_token_id = label_pad_token_id
        self.pad_token_id = getattr(self.tokenizer, "pad_token_id", 0) or 0

    def __call__(self, batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        prompts = [item["prompt"] for item in batch]
        chosens = [item["chosen"] for item in batch]
        rejecteds = [item["rejected"] for item in batch]

        chosen_sequences = [f"{p}\n{c}" for p, c in zip(prompts, chosens)]
        rejected_sequences = [f"{p}\n{r}" for p, r in zip(prompts, rejecteds)]

        # Tokenize chosen
        chosen_enc = self.tokenizer(
            chosen_sequences,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )

        # Tokenize rejected
        rejected_enc = self.tokenizer(
            rejected_sequences,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )

        # Tokenize prompt alone
        prompt_enc = self.tokenizer(
            prompts,
            truncation=True,
            max_length=self.max_prompt_length,
            padding=True,
            return_tensors="pt",
        )

        # Construct labels: mask out padding tokens with label_pad_token_id
        chosen_labels = chosen_enc["input_ids"].clone()
        chosen_labels[chosen_enc["attention_mask"] == 0] = self.label_pad_token_id

        rejected_labels = rejected_enc["input_ids"].clone()
        rejected_labels[rejected_enc["attention_mask"] == 0] = self.label_pad_token_id

        return {
            "prompt_input_ids": prompt_enc["input_ids"],
            "prompt_attention_mask": prompt_enc["attention_mask"],
            "chosen_input_ids": chosen_enc["input_ids"],
            "chosen_attention_mask": chosen_enc["attention_mask"],
            "chosen_labels": chosen_labels,
            "rejected_input_ids": rejected_enc["input_ids"],
            "rejected_attention_mask": rejected_enc["attention_mask"],
            "rejected_labels": rejected_labels,
        }


class SFTDataCollator:
    """
    Collates and tokenizes SFT batches, masking prompt tokens with -100 so loss is computed only on responses.
    """

    def __init__(
        self,
        tokenizer: Any,
        max_length: int = 1024,
        label_pad_token_id: int = -100,
    ):
        self.tokenizer = TokenizerAligner.align_tokenizer(tokenizer)
        self.max_length = max_length
        self.label_pad_token_id = label_pad_token_id
        self.pad_token_id = getattr(self.tokenizer, "pad_token_id", 0) or 0

    def __call__(self, batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        prompts = [item["prompt"] for item in batch]
        responses = [item["response"] for item in batch]
        full_texts = [f"{p}\n{r}" for p, r in zip(prompts, responses)]

        full_enc = self.tokenizer(
            full_texts,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )

        prompt_enc = self.tokenizer(
            prompts,
            truncation=True,
            max_length=self.max_length,
            padding=False,
        )

        input_ids = full_enc["input_ids"]
        attention_mask = full_enc["attention_mask"]
        labels = input_ids.clone()

        # Mask padding
        labels[attention_mask == 0] = self.label_pad_token_id

        # Mask prompt token positions
        for i, p_ids in enumerate(prompt_enc["input_ids"]):
            p_len = min(len(p_ids), labels.shape[1])
            labels[i, :p_len] = self.label_pad_token_id

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def get_dpo_dataloader(
    records_or_paths: Union[List[Dict[str, Any]], str, List[str]],
    tokenizer: Any,
    batch_size: int = 2,
    max_length: int = 1024,
    shuffle: bool = True,
    deduplicate: bool = True,
    ast_validate: bool = True,
    replay_buffer: Optional[StratifiedReplayBuffer] = None,
    replay_ratio: float = 0.20,
    num_workers: int = 0,
) -> DataLoader:
    """
    Creates an optimized PyTorch DataLoader for continuous DPO training.
    """
    raw_records: List[Dict[str, Any]] = []
    if isinstance(records_or_paths, str):
        if os.path.isdir(records_or_paths):
            raw_records = DatasetIngestionEngine.ingest_directory(records_or_paths)
        else:
            raw_records = DatasetIngestionEngine.load_jsonl(records_or_paths)
    elif isinstance(records_or_paths, list):
        if records_or_paths and isinstance(records_or_paths[0], str):
            for path in records_or_paths:
                raw_records.extend(DatasetIngestionEngine.load_jsonl(path))
        else:
            raw_records = records_or_paths

    processed_dpo = DatasetIngestionEngine.process_dpo_records(
        raw_records, deduplicate=deduplicate, ast_validate=ast_validate
    )
    records_dict = [r.to_dict() for r in processed_dpo]

    if replay_buffer is not None and replay_buffer.get_total_anchor_count() > 0:
        records_dict = replay_buffer.create_stratified_dataset(records_dict, replay_ratio=replay_ratio)
        processed_dpo = [
            DPORecord(
                prompt=r["prompt"],
                chosen=r["chosen"],
                rejected=r["rejected"],
                domain=r.get("domain", "general_reasoning"),
                metadata=r.get("metadata", {}),
            )
            for r in records_dict
        ]

    dataset = ContinuousDPODataset(processed_dpo)
    collator = DPODataCollator(tokenizer=tokenizer, max_length=max_length)

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collator,
        num_workers=num_workers,
    )


def get_sft_dataloader(
    records_or_paths: Union[List[Dict[str, Any]], str, List[str]],
    tokenizer: Any,
    batch_size: int = 2,
    max_length: int = 1024,
    shuffle: bool = True,
    deduplicate: bool = True,
    ast_validate: bool = True,
    replay_buffer: Optional[StratifiedReplayBuffer] = None,
    replay_ratio: float = 0.20,
    num_workers: int = 0,
) -> DataLoader:
    """
    Creates an optimized PyTorch DataLoader for SFT training.
    """
    raw_records: List[Dict[str, Any]] = []
    if isinstance(records_or_paths, str):
        if os.path.isdir(records_or_paths):
            raw_records = DatasetIngestionEngine.ingest_directory(records_or_paths)
        else:
            raw_records = DatasetIngestionEngine.load_jsonl(records_or_paths)
    elif isinstance(records_or_paths, list):
        if records_or_paths and isinstance(records_or_paths[0], str):
            for path in records_or_paths:
                raw_records.extend(DatasetIngestionEngine.load_jsonl(path))
        else:
            raw_records = records_or_paths

    processed_sft = DatasetIngestionEngine.process_sft_records(
        raw_records, deduplicate=deduplicate, ast_validate=ast_validate
    )
    records_dict = [r.to_dict() for r in processed_sft]

    if replay_buffer is not None and replay_buffer.get_total_anchor_count() > 0:
        records_dict = replay_buffer.create_stratified_dataset(records_dict, replay_ratio=replay_ratio)
        processed_sft = [
            SFTRecord(
                prompt=r["prompt"],
                response=r["response"],
                domain=r.get("domain", "general_reasoning"),
                metadata=r.get("metadata", {}),
            )
            for r in records_dict
        ]

    dataset = ContinuousSFTDataset(processed_sft)
    collator = SFTDataCollator(tokenizer=tokenizer, max_length=max_length)

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collator,
        num_workers=num_workers,
    )


def get_dataloader(config: Union[Dict[str, Any], Any], tokenizer: Any) -> DataLoader:
    """
    Unified Interface Contract: M1 (Trainer) <-> M2 (Distillation & Ingestion).
    
    Accepts config dictionary or object, inspects task type ('dpo' vs 'sft'),
    and returns configured DataLoader yielding tokenized padded batches.
    """
    cfg = config if isinstance(config, dict) else getattr(config, "__dict__", {})
    task_type = str(cfg.get("task_type", cfg.get("mode", "dpo"))).lower()
    dataset_path = cfg.get("dataset_path", cfg.get("data_path", "/Users/aaron/DFS_UNIFIED/lora_datasets/"))
    batch_size = cfg.get("batch_size", cfg.get("per_device_train_batch_size", 2))
    max_length = cfg.get("max_length", cfg.get("max_seq_length", 1024))
    shuffle = cfg.get("shuffle", True)
    deduplicate = cfg.get("deduplicate", True)
    ast_validate = cfg.get("ast_validate", True)
    replay_ratio = cfg.get("replay_ratio", 0.20)

    if "sft" in task_type:
        return get_sft_dataloader(
            records_or_paths=dataset_path,
            tokenizer=tokenizer,
            batch_size=batch_size,
            max_length=max_length,
            shuffle=shuffle,
            deduplicate=deduplicate,
            ast_validate=ast_validate,
            replay_ratio=replay_ratio,
        )
    else:
        return get_dpo_dataloader(
            records_or_paths=dataset_path,
            tokenizer=tokenizer,
            batch_size=batch_size,
            max_length=max_length,
            shuffle=shuffle,
            deduplicate=deduplicate,
            ast_validate=ast_validate,
            replay_ratio=replay_ratio,
        )
