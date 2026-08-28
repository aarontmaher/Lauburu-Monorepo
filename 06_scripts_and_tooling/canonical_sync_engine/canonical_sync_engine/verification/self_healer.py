"""
canonical_sync_engine.verification.self_healer
Automated pre-flight storage self-healer implementing Rule 6.2.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Union

from canonical_sync_engine.verification.invariants import REQUIRED_OBSIDIAN_WIKILINKS

CANONICAL_INDEX_MD_CONTENT = """---
title: "Lauburu AI Monorepo - Master Knowledge Graph"
tags: [lauburu, root, master_index, swarm, ai_debate]
---
# 🧠 Lauburu AI Monorepo - Master Knowledge Vault
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[Index]]
"""


class StorageSelfHealer:
    """Automated pre-flight self-healing engine per Rule 6.2."""

    def __init__(
        self,
        obsidian_path: Optional[Union[str, Path]] = None,
        pyspark_lora_path: Optional[Union[str, Path]] = None,
        pyspark_memory_path: Optional[Union[str, Path]] = None,
        git_repo_path: Optional[Union[str, Path]] = None,
        gdrive_fallback_path: Optional[Union[str, Path]] = None,
        stale_lock_timeout_sec: float = 10.0,
        cleanup_target_paths: Optional[List[Union[str, Path]]] = None,
    ):
        self.obsidian_path = str(Path(obsidian_path or os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
        )).expanduser().resolve())

        self.pyspark_lora_path = str(Path(pyspark_lora_path or os.environ.get(
            "PYSPARK_DATASET_PATH",
            "/Users/aaron/DFS_UNIFIED/lora_datasets"
        )).expanduser().resolve())

        self.pyspark_memory_path = str(Path(pyspark_memory_path or os.environ.get(
            "PYSPARK_MEMORY_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
        )).expanduser().resolve())

        self.git_repo_path = str(Path(git_repo_path or os.environ.get(
            "GIT_REPO_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
        )).expanduser().resolve())

        self.gdrive_fallback_path = str(Path(gdrive_fallback_path or os.environ.get(
            "GDRIVE_FALLBACK_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache"
        )).expanduser().resolve())

        self.stale_lock_timeout_sec = stale_lock_timeout_sec
        self.cleanup_target_paths = [
            str(Path(p).expanduser().resolve()) for p in (
                cleanup_target_paths or [
                    "/Users/aaron/teamwork_projects",
                    os.path.join(self.git_repo_path, "logs") if self.git_repo_path else "/tmp",
                ]
            )
        ]

    def heal_directories(self) -> List[str]:
        """Creates missing canonical storage directories."""
        actions: List[str] = []
        dirs_to_heal = [
            ("Obsidian Vault", self.obsidian_path),
            ("PySpark Datasets", self.pyspark_lora_path),
            ("PySpark Memory", self.pyspark_memory_path),
            ("Google Drive Fallback VFS", self.gdrive_fallback_path),
        ]
        for name, dir_path in dirs_to_heal:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                actions.append(f"Created missing {name} directory: {dir_path}")
        return actions

    def heal_git_locks(self, force: bool = False) -> List[str]:
        """Removes stale .git/index.lock files."""
        actions: List[str] = []
        if not self.git_repo_path:
            return actions

        lock_file = os.path.join(self.git_repo_path, ".git", "index.lock")
        if os.path.exists(lock_file):
            try:
                mtime = os.path.getmtime(lock_file)
                age = time.time() - mtime
                if force or age >= self.stale_lock_timeout_sec:
                    os.remove(lock_file)
                    actions.append(
                        f"Removed stale git index lock: {lock_file} (age: {age:.1f}s, threshold: {self.stale_lock_timeout_sec}s)"
                    )
                else:
                    actions.append(
                        f"Skipped active git index lock: {lock_file} (age: {age:.1f}s < threshold {self.stale_lock_timeout_sec}s)"
                    )
            except Exception as e:
                actions.append(f"Failed to remove git lock {lock_file}: {str(e)}")
        return actions

    def heal_obsidian_index(self) -> List[str]:
        """Re-creates or updates Obsidian master Index.md with canonical Wikilinks."""
        actions: List[str] = []
        if not self.obsidian_path:
            return actions

        # Ensure vault parent exists first
        if not os.path.exists(self.obsidian_path):
            os.makedirs(self.obsidian_path, exist_ok=True)

        index_path = os.path.join(self.obsidian_path, "Index.md")
        needs_recreate = False

        if not os.path.exists(index_path):
            needs_recreate = True
        elif os.path.getsize(index_path) == 0:
            needs_recreate = True
        else:
            try:
                with open(index_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                missing_links = [l for l in REQUIRED_OBSIDIAN_WIKILINKS if l not in content]
                if missing_links:
                    needs_recreate = True
            except Exception:
                needs_recreate = True

        if needs_recreate:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(CANONICAL_INDEX_MD_CONTENT)
            actions.append(f"Recreated Obsidian master Index.md with canonical Wikilinks at {index_path}")

        return actions

    def heal_disk_headroom(self, min_free_gb: float = 5.0) -> List[str]:
        """Purges transient caches and logs older than 7 days if headroom is below min_free_gb."""
        actions: List[str] = []
        from canonical_sync_engine.verification.headroom import check_disk_headroom

        status = check_disk_headroom(self.git_repo_path or "/Users/aaron", min_headroom_gb=min_free_gb)
        if status.free_gb >= min_free_gb:
            return actions  # Headroom is healthy, no purge required

        purged_items = 0
        now = time.time()
        seven_days_sec = 7 * 86400

        for search_root in self.cleanup_target_paths:
            if not os.path.exists(search_root):
                continue
            for root, dirs, files in os.walk(search_root, topdown=False):
                # Purge __pycache__ and .pytest_cache
                for d in list(dirs):
                    if d in ("__pycache__", ".pytest_cache"):
                        dpath = os.path.join(root, d)
                        try:
                            shutil.rmtree(dpath, ignore_errors=True)
                            purged_items += 1
                        except Exception:
                            pass
                # Purge stale logs
                for f in files:
                    if f.endswith(".log"):
                        fpath = os.path.join(root, f)
                        try:
                            if (now - os.path.getmtime(fpath)) > seven_days_sec:
                                os.remove(fpath)
                                purged_items += 1
                        except Exception:
                            pass

        if purged_items > 0:
            actions.append(f"Purged {purged_items} transient cache directories and stale log files to reclaim headroom")

        return actions

    def heal_all(self, force_git_lock: bool = False, min_free_gb: float = 5.0) -> List[str]:
        """Executes all 4 pre-flight self-healing protocols in order."""
        actions: List[str] = []
        actions.extend(self.heal_directories())
        actions.extend(self.heal_git_locks(force=force_git_lock))
        actions.extend(self.heal_obsidian_index())
        actions.extend(self.heal_disk_headroom(min_free_gb=min_free_gb))
        return actions

    def heal(self) -> List[str]:
        """Convenience execution method for composite verifier."""
        return self.heal_all()


# Alias for cross-module compatibility
PreFlightSelfHealer = StorageSelfHealer
