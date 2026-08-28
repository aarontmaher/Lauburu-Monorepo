"""
canonical_sync_engine.sync.git_syncer
Git Monorepo vault adapter: structured JSON worktree staging and credential-safe CLI integration.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import TruthArtifact
from canonical_sync_engine.models.sync_result import VaultSyncResult
from canonical_sync_engine.sync.base import BaseVaultSyncer


class GitVaultSyncer(BaseVaultSyncer):
    """
    Synchronizes TruthArtifacts to the Git Monorepo worktree (04_data_and_memory/core_data/).
    Writes structured JSON files and stages them using the local git CLI without credential exposure.
    """

    def __init__(self, config: Optional[SyncConfig] = None) -> None:
        super().__init__(config)

    @property
    def vault_name(self) -> str:
        return "git"

    @property
    def target_dir(self) -> Path:
        """Directory where structured JSON artifacts are saved in the Git worktree."""
        return self.config.git_repo_path / "04_data_and_memory" / "core_data"

    def get_artifact_path(self, artifact_id: str) -> Path:
        """Returns the target JSON file path for an artifact."""
        safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in artifact_id)
        return self.target_dir / f"{safe_id}.json"

    def _check_and_heal_git_lock(self, git_root: Path) -> bool:
        """
        Checks for .git/index.lock. If stale (> 10 minutes old), clears it.
        Returns True if git lock is clear, False if still locked.
        """
        lock_file = git_root / ".git" / "index.lock"
        if not lock_file.exists():
            return True

        try:
            mtime = lock_file.stat().st_mtime
            age_sec = time.time() - mtime
            if age_sec > 600:  # 10 minutes
                lock_file.unlink(missing_ok=True)
                return True
            return False
        except OSError:
            return not lock_file.exists()

    def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
        """
        Atomically writes the JSON artifact to the Git worktree and stages it with git add.
        """
        with self._measure_time() as timer:
            target_path = self.get_artifact_path(artifact.artifact_id)
            git_root = self.config.git_repo_path

            try:
                # Ensure target directories exist
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Atomically write structured JSON
                bytes_written = self._atomic_write_json(target_path, artifact.to_dict(), indent=2)

                # Post-write hash verification
                if not self.verify(artifact):
                    return VaultSyncResult.create_failure(
                        vault_name=self.vault_name,
                        target_path=str(target_path),
                        error="Post-write verification failed: artifact JSON hash mismatch.",
                        latency_ms=timer.elapsed_ms,
                    )

                # Stage file with local git CLI if inside a git repository
                is_staged = False
                git_dir = git_root / ".git"
                if git_dir.exists():
                    self._check_and_heal_git_lock(git_root)
                    try:
                        # Compute relative path to git root
                        rel_path = target_path.relative_to(git_root)
                        git_bin = shutil.which("git") or "/usr/bin/git"
                        res = subprocess.run(
                            [git_bin, "add", str(rel_path)],
                            cwd=str(git_root),
                            capture_output=True,
                            text=True,
                            timeout=5.0,
                            check=False,
                        )
                        is_staged = (res.returncode == 0)
                    except Exception:
                        is_staged = False

                return VaultSyncResult.create_success(
                    vault_name=self.vault_name,
                    target_path=str(target_path),
                    sha256_hash=artifact.sha256_hash,
                    bytes_written=bytes_written,
                    latency_ms=timer.elapsed_ms,
                    metadata={
                        "git_root": str(git_root),
                        "staged": is_staged,
                        "relative_path": str(target_path.relative_to(git_root)) if target_path.is_relative_to(git_root) else str(target_path),
                    },
                )

            except Exception as e:
                return VaultSyncResult.create_failure(
                    vault_name=self.vault_name,
                    target_path=str(target_path),
                    error=f"Git vault sync error: {type(e).__name__}: {str(e)}",
                    latency_ms=timer.elapsed_ms,
                )

    def verify(self, artifact: TruthArtifact) -> bool:
        """
        Verifies that the artifact JSON exists in the Git worktree and has matching SHA-256 hash.
        """
        target_path = self.get_artifact_path(artifact.artifact_id)
        if not target_path.exists() or not target_path.is_file():
            # Secondary check directly in git_repo_path / core_data
            alt_path = self.config.git_repo_path / "core_data" / f"{artifact.artifact_id}.json"
            if alt_path.exists() and alt_path.is_file():
                target_path = alt_path
            else:
                return False

        try:
            content = target_path.read_text(encoding="utf-8")
            data = json.loads(content)
            reconstructed = TruthArtifact.from_dict(data)
            return (
                reconstructed.artifact_id == artifact.artifact_id
                and reconstructed.sha256_hash == artifact.sha256_hash
                and reconstructed.verify_hash()
            )
        except Exception:
            return False

    def read(self, artifact_id: str) -> Optional[TruthArtifact]:
        """
        Reads and reconstructs a TruthArtifact from the Git worktree JSON file.
        """
        target_path = self.get_artifact_path(artifact_id)
        if not target_path.exists() or not target_path.is_file():
            alt_path = self.config.git_repo_path / "core_data" / f"{artifact_id}.json"
            if alt_path.exists() and alt_path.is_file():
                target_path = alt_path
            else:
                return None

        try:
            content = target_path.read_text(encoding="utf-8")
            data = json.loads(content)
            reconstructed = TruthArtifact.from_dict(data)
            if reconstructed.verify_hash():
                return reconstructed
            return None
        except Exception:
            return None
