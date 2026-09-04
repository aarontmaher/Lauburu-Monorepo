"""
canonical_sync_engine.sync
Exports the Quad-Vault synchronization adapters, Git worktree isolation manager, and base syncer interface.
"""
from __future__ import annotations

from canonical_sync_engine.sync.base import BaseVaultSyncer
from canonical_sync_engine.sync.pyspark_syncer import PySparkVaultSyncer
from canonical_sync_engine.sync.obsidian_syncer import ObsidianVaultSyncer
from canonical_sync_engine.sync.git_syncer import GitVaultSyncer
from canonical_sync_engine.sync.gdrive_syncer import GDriveVaultSyncer
from canonical_sync_engine.sync.git_worktree_manager import (
    GitWorktreeManager,
    create_worktree,
    cleanup_worktree,
    get_default_worktree_manager,
)

__all__ = [
    "BaseVaultSyncer",
    "PySparkVaultSyncer",
    "ObsidianVaultSyncer",
    "GitVaultSyncer",
    "GDriveVaultSyncer",
    "GitWorktreeManager",
    "create_worktree",
    "cleanup_worktree",
    "get_default_worktree_manager",
]
