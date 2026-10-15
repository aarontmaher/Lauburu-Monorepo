"""
Distillation Package for Autonomous 24/7 AI Training Optimization Engine.

Provides:
- Multi-schema Dataset Ingestion & Tokenized DataLoaders (F5)
- Multi-tier Exact SHA-256 and SimHash Deduplicators (F6)
- Cross-Family Tokenizer Alignment & Dynamic Chat Formatters (F7, F8)
- 80/20 Stratified Anti-Catastrophic Forgetting Replay Buffers (F9)
- AST Compiler Gates & Rule #0 Zero-Mock Validators (F10)
- MPS Bradley-Terry DPO Loss Engine (F11)
"""

from .ast_compiler_gate import ASTCompilerGate
from .dataset_loader import (
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
from .dpo_loss_mps import DPOLossMPS, compute_token_log_probs
from .replay_buffer import (
    CANONICAL_ANCHOR_DOMAINS,
    DomainReservoir,
    StratifiedReplayBuffer,
)
from .sample_deduplicator import (
    SampleDeduplicator,
    SimHash,
    extract_canonical_text,
    normalize_text,
)
from .tokenizer_aligner import (
    KNOWN_PROFILES,
    DynamicChatFormatter,
    TokenizerAligner,
    TokenizerMismatchError,
    TokenizerProfile,
    TokenizerValidationResult,
    detect_model_family,
)

__all__ = [
    # F5: Dataset Ingestion
    "DPORecord",
    "SFTRecord",
    "MultiSchemaNormalizer",
    "DatasetIngestionEngine",
    "ContinuousDPODataset",
    "ContinuousSFTDataset",
    "DPODataCollator",
    "SFTDataCollator",
    "get_dpo_dataloader",
    "get_sft_dataloader",
    "get_dataloader",
    # F6: Deduplication
    "normalize_text",
    "extract_canonical_text",
    "SimHash",
    "SampleDeduplicator",
    # F7 & F8: Tokenizer Alignment & Formatting
    "TokenizerMismatchError",
    "TokenizerProfile",
    "KNOWN_PROFILES",
    "detect_model_family",
    "DynamicChatFormatter",
    "TokenizerValidationResult",
    "TokenizerAligner",
    # F9: Replay Buffer
    "CANONICAL_ANCHOR_DOMAINS",
    "DomainReservoir",
    "StratifiedReplayBuffer",
    # F10: AST Gate
    "ASTCompilerGate",
    # F11: DPO Loss
    "compute_token_log_probs",
    "DPOLossMPS",
]
