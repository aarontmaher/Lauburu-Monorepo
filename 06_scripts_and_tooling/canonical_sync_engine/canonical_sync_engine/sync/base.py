"""
canonical_sync_engine.sync.base
Abstract BaseVaultSyncer interface and common atomic file handling utilities.
"""
from __future__ import annotations

import abc
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import TruthArtifact
from canonical_sync_engine.models.sync_result import VaultSyncResult


class _Timer:
    """Context manager for high-precision latency measurement."""

    def __init__(self) -> None:
        self.start_time: float = time.perf_counter()
        self.end_time: float = 0.0

    def __enter__(self) -> _Timer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.end_time = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Returns the elapsed time in milliseconds."""
        if self.end_time > 0.0:
            return max(0.001, (self.end_time - self.start_time) * 1000.0)
        return max(0.001, (time.perf_counter() - self.start_time) * 1000.0)


class BaseVaultSyncer(abc.ABC):
    """
    Abstract base class for all Quad-Vault synchronization adapters.
    Guarantees consistent sync, verify, read, and atomic write contracts.
    """

    def __init__(self, config: Optional[SyncConfig] = None) -> None:
        self.config = config or SyncConfig.from_env()

    @property
    @abc.abstractmethod
    def vault_name(self) -> str:
        """Returns the canonical name of the vault (e.g. 'pyspark', 'obsidian', 'git', 'gdrive')."""
        pass

    @abc.abstractmethod
    def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
        """
        Synchronizes a TruthArtifact to the target vault storage.
        Must perform format transformation, atomic write, and verification.
        """
        pass

    @abc.abstractmethod
    def verify(self, artifact: TruthArtifact) -> bool:
        """
        Verifies that the artifact exists in the target vault, has valid formatting,
        and its stored content matches the canonical SHA-256 hash.
        """
        pass

    @abc.abstractmethod
    def read(self, artifact_id: str) -> Optional[TruthArtifact]:
        """
        Reads and reconstructs a TruthArtifact from the target vault by its unique artifact_id.
        Returns None if not found or corrupted.
        """
        pass

    def _atomic_write_text(
        self,
        target_path: Path,
        content: str,
        encoding: str = "utf-8",
    ) -> int:
        """
        Atomically writes string content to target_path using a sibling temporary file
        and atomic rename (os.replace). Guarantees zero partial writes.
        Returns number of bytes written.
        """
        target_path = Path(target_path).resolve()
        target_dir = target_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        content_bytes = content.encode(encoding)
        tmp_suffix = f".tmp.{os.getpid()}_{uuid.uuid4().hex[:8]}"
        tmp_file = target_dir / f"{target_path.name}{tmp_suffix}"

        try:
            with open(tmp_file, "wb") as f:
                f.write(content_bytes)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (AttributeError, OSError):
                    pass
            os.replace(tmp_file, target_path)
            return len(content_bytes)
        finally:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    def _atomic_write_json(
        self,
        target_path: Path,
        data: Any,
        indent: Optional[int] = 2,
    ) -> int:
        """
        Atomically writes JSON-serializable data to target_path with sorted keys.
        """
        json_str = json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)
        return self._atomic_write_text(target_path, json_str + "\n")

    def _measure_time(self) -> _Timer:
        """Helper context manager to measure operation latency in milliseconds."""
        return _Timer()
