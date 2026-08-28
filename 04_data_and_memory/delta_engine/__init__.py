"""
Delta Engine for Lauburu Monorepo.
Rust-native delta-rs table writer, compaction optimizer, zero-copy HuggingFace mmap loader,
and JSONL migration utilities.
"""
from __future__ import annotations

from .compactor import DeltaCompactor
from .mmap_loader import MemoryMappedDatasetLoader
from .migrator import JSONLToDeltaMigrator
from .schema import (
    DPO_PREFERENCE_ARROW_SCHEMA,
    MESH_TELEMETRY_ARROW_SCHEMA,
    SCHEMA_REGISTRY,
    SFT_TRAINING_ARROW_SCHEMA,
    TRUTH_AUDIT_ARROW_SCHEMA,
    get_schema_by_name,
    normalize_record,
    records_to_arrow_table,
)
from .writer import DeltaDatasetWriter

__all__ = [
    "DeltaDatasetWriter",
    "DeltaCompactor",
    "MemoryMappedDatasetLoader",
    "JSONLToDeltaMigrator",
    "TRUTH_AUDIT_ARROW_SCHEMA",
    "SFT_TRAINING_ARROW_SCHEMA",
    "DPO_PREFERENCE_ARROW_SCHEMA",
    "MESH_TELEMETRY_ARROW_SCHEMA",
    "SCHEMA_REGISTRY",
    "get_schema_by_name",
    "normalize_record",
    "records_to_arrow_table",
]
