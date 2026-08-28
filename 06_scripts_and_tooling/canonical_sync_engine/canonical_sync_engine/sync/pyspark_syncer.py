"""
canonical_sync_engine.sync.pyspark_syncer
PySpark Data Lake vault adapter: thread-safe JSONL streaming append and schema verification.
"""
from __future__ import annotations

import fcntl
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import TruthArtifact
from canonical_sync_engine.models.sync_result import VaultSyncResult
from canonical_sync_engine.sync.base import BaseVaultSyncer


class PySparkVaultSyncer(BaseVaultSyncer):
    """
    Synchronizes TruthArtifacts to the PySpark Data Lake (lora_datasets/ and 04_data_and_memory/).
    Appends line-delimited JSON (JSONL) records atomically and thread-safely to master and
    partitioned dataset stores.
    """

    _append_lock = threading.Lock()

    def __init__(self, config: Optional[SyncConfig] = None) -> None:
        super().__init__(config)

    @property
    def vault_name(self) -> str:
        return "pyspark"

    @property
    def master_jsonl_path(self) -> Path:
        """Returns canonical path to the master truth audit dataset."""
        return self.config.pyspark_dataset_path / "truth_audit_master.jsonl"

    @property
    def partitioned_dir(self) -> Path:
        """Returns directory for partitioned artifact datasets."""
        return self.config.pyspark_dataset_path / "by_type"

    @property
    def artifacts_dir(self) -> Path:
        """Returns directory for standalone artifact jsonl/json files."""
        return self.config.pyspark_dataset_path / "artifacts"

    def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
        """
        Appends the artifact to the master truth audit JSONL dataset and a partitioned
        dataset file with thread-safe and process-safe locking.
        """
        with self._measure_time() as timer:
            master_path = self.master_jsonl_path
            partition_path = self.partitioned_dir / f"{artifact.artifact_type.value}.jsonl"
            artifact_path = self.artifacts_dir / f"{artifact.artifact_id}.jsonl"

            try:
                # Ensure directories exist
                master_path.parent.mkdir(parents=True, exist_ok=True)
                partition_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.parent.mkdir(parents=True, exist_ok=True)

                # Format single-line canonical JSON record
                record_dict = artifact.to_dict()
                line = json.dumps(record_dict, sort_keys=True, ensure_ascii=False) + "\n"
                line_bytes = line.encode("utf-8")
                bytes_written = 0

                # Thread-safe and inter-process-safe append to master
                with self._append_lock:
                    with open(master_path, "a", encoding="utf-8") as f:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        except (OSError, AttributeError):
                            pass
                        try:
                            f.write(line)
                            f.flush()
                            try:
                                os.fsync(f.fileno())
                            except OSError:
                                pass
                        finally:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                            except (OSError, AttributeError):
                                pass
                    bytes_written += len(line_bytes)

                    # Append to partitioned dataset
                    with open(partition_path, "a", encoding="utf-8") as f:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        except (OSError, AttributeError):
                            pass
                        try:
                            f.write(line)
                            f.flush()
                        finally:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                            except (OSError, AttributeError):
                                pass

                # Write individual artifact file atomically
                self._atomic_write_text(artifact_path, line)

                # Also replicate to 04_data_and_memory if path differs and exists
                memory_path = self.config.pyspark_memory_path / "truth_audit_master.jsonl"
                if memory_path.resolve() != master_path.resolve():
                    try:
                        memory_path.parent.mkdir(parents=True, exist_ok=True)
                        with self._append_lock:
                            with open(memory_path, "a", encoding="utf-8") as f:
                                f.write(line)
                                f.flush()
                    except Exception:
                        pass  # Non-fatal secondary mirror

                # Post-sync verification
                if not self.verify(artifact):
                    return VaultSyncResult.create_failure(
                        vault_name=self.vault_name,
                        target_path=str(master_path),
                        error="Post-sync verification failed: artifact not found or hash mismatch in JSONL store.",
                        latency_ms=timer.elapsed_ms,
                    )

                return VaultSyncResult.create_success(
                    vault_name=self.vault_name,
                    target_path=str(master_path),
                    sha256_hash=artifact.sha256_hash,
                    bytes_written=bytes_written,
                    latency_ms=timer.elapsed_ms,
                    metadata={
                        "master_jsonl": str(master_path),
                        "partition_jsonl": str(partition_path),
                        "artifact_file": str(artifact_path),
                    },
                )

            except Exception as e:
                return VaultSyncResult.create_failure(
                    vault_name=self.vault_name,
                    target_path=str(master_path),
                    error=f"PySpark vault sync error: {type(e).__name__}: {str(e)}",
                    latency_ms=timer.elapsed_ms,
                )

    def verify(self, artifact: TruthArtifact) -> bool:
        """
        Scans the master JSONL dataset for the artifact and asserts exact hash and field match.
        """
        master_path = self.master_jsonl_path
        if not master_path.exists() or not master_path.is_file():
            # Check standalone artifact file as fallback
            artifact_path = self.artifacts_dir / f"{artifact.artifact_id}.jsonl"
            if artifact_path.exists() and artifact_path.is_file():
                try:
                    content = artifact_path.read_text(encoding="utf-8").strip()
                    parsed = json.loads(content)
                    recon = TruthArtifact.from_dict(parsed)
                    return recon.sha256_hash == artifact.sha256_hash and recon.verify_hash()
                except Exception:
                    return False
            return False

        try:
            with open(master_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                    except json.JSONDecodeError:
                        continue
                    if data.get("artifact_id") == artifact.artifact_id:
                        recon = TruthArtifact.from_dict(data)
                        if recon.sha256_hash == artifact.sha256_hash and recon.verify_hash():
                            return True
            return False
        except Exception:
            return False

    def read(self, artifact_id: str) -> Optional[TruthArtifact]:
        """
        Reads and returns the TruthArtifact matching artifact_id from the master JSONL.
        """
        master_path = self.master_jsonl_path
        # First check standalone artifact file for fast lookup
        artifact_path = self.artifacts_dir / f"{artifact_id}.jsonl"
        if artifact_path.exists() and artifact_path.is_file():
            try:
                content = artifact_path.read_text(encoding="utf-8").strip()
                data = json.loads(content)
                recon = TruthArtifact.from_dict(data)
                if recon.verify_hash():
                    return recon
            except Exception:
                pass

        if not master_path.exists():
            return None

        try:
            matched_artifact: Optional[TruthArtifact] = None
            with open(master_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                    except json.JSONDecodeError:
                        continue
                    if data.get("artifact_id") == artifact_id:
                        recon = TruthArtifact.from_dict(data)
                        if recon.verify_hash():
                            matched_artifact = recon
            return matched_artifact
        except Exception:
            return None

    def read_all(self) -> List[TruthArtifact]:
        """Reads all valid TruthArtifacts from the master JSONL dataset."""
        master_path = self.master_jsonl_path
        if not master_path.exists():
            return []
        artifacts: List[TruthArtifact] = []
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        recon = TruthArtifact.from_dict(data)
                        if recon.verify_hash():
                            artifacts.append(recon)
                    except Exception:
                        continue
        except Exception:
            return []
        return artifacts
