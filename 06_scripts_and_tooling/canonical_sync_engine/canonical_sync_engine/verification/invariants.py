"""
canonical_sync_engine.verification.invariants
Canonical storage invariant validators implementing Rule 6.1.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from canonical_sync_engine.models.health import StorageHealthReport
from canonical_sync_engine.verification.headroom import check_disk_headroom

REQUIRED_OBSIDIAN_WIKILINKS = [
    "[[Index]]",
    "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
    "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
]


@dataclass
class VaultInvariantResult:
    """Invariant validation result for a single vault destination."""
    vault_name: str
    is_healthy: bool
    target_path: str
    violations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_name": self.vault_name,
            "is_healthy": self.is_healthy,
            "target_path": self.target_path,
            "violations": list(self.violations),
            "metadata": dict(self.metadata),
        }


class StorageInvariantValidator:
    """Validates Rule 6.1 storage invariants across all canonical vaults."""

    def __init__(
        self,
        obsidian_path: Optional[Union[str, Path]] = None,
        pyspark_path: Optional[Union[str, Path]] = None,
        pyspark_memory_path: Optional[Union[str, Path]] = None,
        git_path: Optional[Union[str, Path]] = None,
        gdrive_path: Optional[Union[str, Path]] = None,
        gdrive_cache_path: Optional[Union[str, Path]] = None,
        min_headroom_gb: float = 10.0,
    ):
        self.obsidian_path = str(Path(obsidian_path or os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
        )).expanduser().resolve())

        self.pyspark_lora_path = str(Path(pyspark_path or os.environ.get(
            "PYSPARK_DATASET_PATH",
            "/Users/aaron/DFS_UNIFIED/lora_datasets"
        )).expanduser().resolve())

        self.pyspark_memory_path = str(Path(pyspark_memory_path or os.environ.get(
            "PYSPARK_MEMORY_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
        )).expanduser().resolve())

        self.git_repo_path = str(Path(git_path or os.environ.get(
            "GIT_REPO_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
        )).expanduser().resolve())

        self.gdrive_primary_path = str(Path(gdrive_path or os.environ.get(
            "GDRIVE_MOUNT_PATH",
            "/Volumes/Google Drive/My Drive/Lauburu_AI_Memory"
        )).expanduser().resolve())

        self.gdrive_fallback_path = str(Path(gdrive_cache_path or os.environ.get(
            "GDRIVE_FALLBACK_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache"
        )).expanduser().resolve())

        self.min_headroom_gb = min_headroom_gb

    def validate_obsidian(self) -> VaultInvariantResult:
        violations: List[str] = []
        meta: Dict[str, Any] = {}

        if not os.path.exists(self.obsidian_path):
            violations.append(f"Obsidian vault directory missing: {self.obsidian_path}")
            return VaultInvariantResult("obsidian", False, self.obsidian_path, violations, meta)

        if not os.path.isdir(self.obsidian_path):
            violations.append(f"Obsidian vault path is not a directory: {self.obsidian_path}")
            return VaultInvariantResult("obsidian", False, self.obsidian_path, violations, meta)

        if not os.access(self.obsidian_path, os.R_OK | os.W_OK):
            violations.append(f"Obsidian vault directory not read/write accessible: {self.obsidian_path}")

        index_file = os.path.join(self.obsidian_path, "Index.md")
        if not os.path.exists(index_file):
            violations.append(f"Obsidian Index.md missing at: {index_file}")
        else:
            size = os.path.getsize(index_file)
            meta["index_size_bytes"] = size
            if size == 0:
                violations.append("Obsidian Index.md is empty (0 bytes)")
            else:
                try:
                    with open(index_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    meta["wikilinks_found"] = []
                    for link in REQUIRED_OBSIDIAN_WIKILINKS:
                        if link in content:
                            meta["wikilinks_found"].append(link)
                        else:
                            violations.append(f"Obsidian Index.md missing mandatory Wikilink: {link}")
                except Exception as e:
                    violations.append(f"Error reading Obsidian Index.md: {str(e)}")

        return VaultInvariantResult(
            vault_name="obsidian",
            is_healthy=(len(violations) == 0),
            target_path=self.obsidian_path,
            violations=violations,
            metadata=meta,
        )

    def validate_pyspark(self) -> VaultInvariantResult:
        violations: List[str] = []
        meta: Dict[str, Any] = {}

        paths_to_check = [("lora_datasets", self.pyspark_lora_path)]
        if self.pyspark_memory_path:
            paths_to_check.append(("04_data_and_memory", self.pyspark_memory_path))

        for path_name, path in paths_to_check:
            if not os.path.exists(path):
                violations.append(f"PySpark path missing: {path} ({path_name})")
            elif not os.path.isdir(path):
                violations.append(f"PySpark path is not a directory: {path}")
            elif not os.access(path, os.R_OK | os.W_OK):
                violations.append(f"PySpark path not writable: {path}")

        # Validate sample jsonl integrity if files exist
        if os.path.isdir(self.pyspark_lora_path):
            try:
                jsonl_files = [f for f in os.listdir(self.pyspark_lora_path) if f.endswith(".jsonl")]
                meta["jsonl_file_count"] = len(jsonl_files)
                for jf in jsonl_files[:5]:  # Spot check first 5
                    jpath = os.path.join(self.pyspark_lora_path, jf)
                    with open(jpath, "r", encoding="utf-8") as f:
                        for line_idx, line in enumerate(f):
                            if line.strip():
                                json.loads(line)
                            if line_idx > 10:  # Check first 10 lines
                                break
            except Exception as e:
                violations.append(f"Corrupt JSONL format in {self.pyspark_lora_path}: {str(e)}")

        return VaultInvariantResult(
            vault_name="pyspark",
            is_healthy=(len(violations) == 0),
            target_path=self.pyspark_lora_path,
            violations=violations,
            metadata=meta,
        )

    def validate_git(self) -> VaultInvariantResult:
        violations: List[str] = []
        meta: Dict[str, Any] = {}

        if not os.path.exists(self.git_repo_path):
            violations.append(f"Git repo directory missing: {self.git_repo_path}")
            return VaultInvariantResult("git", False, self.git_repo_path, violations, meta)

        dot_git = os.path.join(self.git_repo_path, ".git")
        if not os.path.exists(dot_git):
            violations.append(f"Git repository .git directory not found at: {dot_git}")
            return VaultInvariantResult("git", False, self.git_repo_path, violations, meta)

        # Check index.lock invariant
        lock_file = os.path.join(dot_git, "index.lock")
        if os.path.exists(lock_file):
            lock_age = time.time() - os.path.getmtime(lock_file)
            violations.append(f"Git index lock present ({lock_file}, age: {lock_age:.1f}s)")
            meta["git_lock_present"] = True
            meta["git_lock_age_seconds"] = lock_age
        else:
            meta["git_lock_present"] = False

        return VaultInvariantResult(
            vault_name="git",
            is_healthy=(len(violations) == 0),
            target_path=self.git_repo_path,
            violations=violations,
            metadata=meta,
        )

    def validate_gdrive(self) -> VaultInvariantResult:
        violations: List[str] = []
        meta: Dict[str, Any] = {}

        primary_ok = os.path.exists(self.gdrive_primary_path) and os.access(self.gdrive_primary_path, os.W_OK)
        fallback_ok = os.path.exists(self.gdrive_fallback_path) and os.access(self.gdrive_fallback_path, os.W_OK)

        meta["primary_mount_active"] = primary_ok
        meta["fallback_cache_active"] = fallback_ok

        active_path = self.gdrive_primary_path if primary_ok else self.gdrive_fallback_path

        if not primary_ok and not fallback_ok:
            violations.append(
                f"Google Drive unavailable: primary mount ({self.gdrive_primary_path}) and fallback "
                f"({self.gdrive_fallback_path}) are both inaccessible or unwritable"
            )

        return VaultInvariantResult(
            vault_name="gdrive",
            is_healthy=(len(violations) == 0),
            target_path=active_path,
            violations=violations,
            metadata=meta,
        )

    def validate_all(self) -> StorageHealthReport:
        headroom_status = check_disk_headroom(self.git_repo_path, min_headroom_gb=self.min_headroom_gb)
        obsidian_res = self.validate_obsidian()
        pyspark_res = self.validate_pyspark()
        git_res = self.validate_git()
        gdrive_res = self.validate_gdrive()

        all_violations: List[str] = []
        if not headroom_status.is_sufficient and headroom_status.violation_message:
            all_violations.append(headroom_status.violation_message)

        all_violations.extend(obsidian_res.violations)
        all_violations.extend(pyspark_res.violations)
        all_violations.extend(git_res.violations)
        all_violations.extend(gdrive_res.violations)

        vault_details = {
            "obsidian": obsidian_res.to_dict(),
            "pyspark": pyspark_res.to_dict(),
            "git": git_res.to_dict(),
            "gdrive": gdrive_res.to_dict(),
        }

        is_healthy = (
            headroom_status.is_sufficient
            and obsidian_res.is_healthy
            and pyspark_res.is_healthy
            and git_res.is_healthy
            and gdrive_res.is_healthy
        )

        return StorageHealthReport(
            is_healthy=is_healthy,
            disk_free_gb=headroom_status.free_gb,
            headroom_satisfied=headroom_status.is_sufficient,
            obsidian_healthy=obsidian_res.is_healthy,
            pyspark_healthy=pyspark_res.is_healthy,
            git_healthy=git_res.is_healthy,
            gdrive_healthy=gdrive_res.is_healthy,
            vault_details=vault_details,
            violations=all_violations,
        )

    def check(self) -> Tuple[bool, List[str], Dict[str, bool]]:
        """
        Returns:
            Tuple of (all_invariants_ok, list_of_violations, vault_statuses_dict)
        """
        obs_res = self.validate_obsidian()
        pysp_res = self.validate_pyspark()
        git_res = self.validate_git()
        gdrive_res = self.validate_gdrive()

        violations = (
            obs_res.violations + pysp_res.violations + git_res.violations + gdrive_res.violations
        )
        vault_statuses = {
            "obsidian": obs_res.is_healthy,
            "pyspark": pysp_res.is_healthy,
            "git": git_res.is_healthy,
            "gdrive": gdrive_res.is_healthy,
        }
        all_ok = all(vault_statuses.values())
        return all_ok, violations, vault_statuses
