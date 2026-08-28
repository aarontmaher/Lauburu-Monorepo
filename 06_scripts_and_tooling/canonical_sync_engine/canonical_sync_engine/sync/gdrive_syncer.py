"""
canonical_sync_engine.sync.gdrive_syncer
Google Drive cloud mirror vault adapter: 3-tier resilient resolution and offline VFS cache queuing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import TruthArtifact
from canonical_sync_engine.models.sync_result import VaultSyncResult
from canonical_sync_engine.sync.base import BaseVaultSyncer


class GDriveVaultSyncer(BaseVaultSyncer):
    """
    Synchronizes TruthArtifacts to Google Drive cloud storage using a 3-tier resilient resolution:
      - Tier 1: Native macOS mount (/Volumes/Google Drive/My Drive/...)
      - Tier 2: rclone mount or secondary cloud mount (/mnt/gdrive, /Volumes/GoogleDrive)
      - Tier 3: Local VFS fallback cache (data/gdrive_cache) with pending_sync.jsonl offline queue
    """

    def __init__(self, config: Optional[SyncConfig] = None) -> None:
        super().__init__(config)

    @property
    def vault_name(self) -> str:
        return "gdrive"

    def resolve_destination(self) -> Tuple[Path, str]:
        """
        Resolves the highest-priority active storage tier:
        Returns: (resolved_dir_path, tier_name)
        """
        # Tier 1: Native Google Drive macOS mount
        t1_path = self.config.gdrive_mount_path
        if t1_path.exists() and os.access(str(t1_path), os.W_OK):
            return t1_path / "truth_artifacts", "tier_1_native_mount"

        # Tier 2: rclone mount / secondary mount from env or common mount points
        rclone_env = os.environ.get("RCLONE_MOUNT_PATH")
        if rclone_env:
            t2_candidate = Path(rclone_env).expanduser().resolve()
            if t2_candidate.exists() and os.access(str(t2_candidate), os.W_OK):
                return t2_candidate / "truth_artifacts", "tier_2_rclone_mount"

        for candidate_str in ["/Volumes/GoogleDrive", "/mnt/gdrive"]:
            t2_cand = Path(candidate_str)
            if t2_cand.exists() and os.access(str(t2_cand), os.W_OK):
                return t2_cand / "truth_artifacts", "tier_2_rclone_mount"

        # Tier 3: Local VFS fallback cache
        t3_path = self.config.gdrive_fallback_cache_path / "truth_artifacts"
        t3_path.mkdir(parents=True, exist_ok=True)
        return t3_path, "tier_3_fallback_cache"

    def get_artifact_path(self, artifact_id: str, base_dir: Optional[Path] = None) -> Path:
        """Returns target file path for artifact JSON."""
        safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in artifact_id)
        if base_dir is None:
            base_dir, _ = self.resolve_destination()
        return base_dir / f"{safe_id}.json"

    def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
        """
        Synchronizes artifact to the resolved Google Drive tier.
        If fallback cache is used, enqueues to pending_sync.jsonl.
        """
        with self._measure_time() as timer:
            dest_dir, tier_name = self.resolve_destination()
            target_path = self.get_artifact_path(artifact.artifact_id, base_dir=dest_dir)

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)

                # Atomically write structured JSON
                bytes_written = self._atomic_write_json(target_path, artifact.to_dict(), indent=2)

                # If offline Tier 3 fallback, append to pending_sync queue
                is_offline_queued = (tier_name == "tier_3_fallback_cache")
                if is_offline_queued:
                    queue_file = self.config.gdrive_fallback_cache_path / "pending_sync.jsonl"
                    queue_record = {
                        "artifact_id": artifact.artifact_id,
                        "sha256_hash": artifact.sha256_hash,
                        "timestamp": artifact.timestamp,
                        "source_file": str(target_path),
                        "status": "pending_upload",
                    }
                    queue_line = json.dumps(queue_record, sort_keys=True) + "\n"
                    with open(queue_file, "a", encoding="utf-8") as qf:
                        qf.write(queue_line)
                        qf.flush()

                # Post-write verification
                if not self.verify(artifact):
                    return VaultSyncResult.create_failure(
                        vault_name=self.vault_name,
                        target_path=str(target_path),
                        error="Post-write verification failed: Google Drive mirrored file corrupted or hash mismatch.",
                        latency_ms=timer.elapsed_ms,
                    )

                return VaultSyncResult.create_success(
                    vault_name=self.vault_name,
                    target_path=str(target_path),
                    sha256_hash=artifact.sha256_hash,
                    bytes_written=bytes_written,
                    latency_ms=timer.elapsed_ms,
                    metadata={
                        "tier_used": tier_name,
                        "is_offline_queued": is_offline_queued,
                        "destination_dir": str(dest_dir),
                    },
                )

            except Exception as e:
                return VaultSyncResult.create_failure(
                    vault_name=self.vault_name,
                    target_path=str(target_path),
                    error=f"GDrive vault sync error: {type(e).__name__}: {str(e)}",
                    latency_ms=timer.elapsed_ms,
                )

    def verify(self, artifact: TruthArtifact) -> bool:
        """
        Verifies that the artifact file exists in the active tier (or fallback cache)
        and matches the canonical SHA-256 hash.
        """
        # Check active destination first
        dest_dir, _ = self.resolve_destination()
        target_path = self.get_artifact_path(artifact.artifact_id, base_dir=dest_dir)

        search_paths = [target_path]
        # Also check fallback cache if not currently active
        fallback_path = self.config.gdrive_fallback_cache_path / "truth_artifacts" / f"{artifact.artifact_id}.json"
        if fallback_path not in search_paths:
            search_paths.append(fallback_path)

        for p in search_paths:
            if p.exists() and p.is_file():
                try:
                    content = p.read_text(encoding="utf-8")
                    data = json.loads(content)
                    recon = TruthArtifact.from_dict(data)
                    if (
                        recon.artifact_id == artifact.artifact_id
                        and recon.sha256_hash == artifact.sha256_hash
                        and recon.verify_hash()
                    ):
                        return True
                except Exception:
                    continue
        return False

    def read(self, artifact_id: str) -> Optional[TruthArtifact]:
        """
        Reads and reconstructs a TruthArtifact from Google Drive storage or fallback cache.
        """
        dest_dir, _ = self.resolve_destination()
        search_paths = [
            self.get_artifact_path(artifact_id, base_dir=dest_dir),
            self.config.gdrive_fallback_cache_path / "truth_artifacts" / f"{artifact_id}.json",
            self.config.gdrive_mount_path / "truth_artifacts" / f"{artifact_id}.json",
        ]

        for p in search_paths:
            if p.exists() and p.is_file():
                try:
                    content = p.read_text(encoding="utf-8")
                    data = json.loads(content)
                    recon = TruthArtifact.from_dict(data)
                    if recon.verify_hash():
                        return recon
                except Exception:
                    continue
        return None
