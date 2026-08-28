"""
canonical_sync_engine.verification.fast_path
High-performance, sub-3ms storage health verification per Rule 6.3.
"""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union


@dataclass(frozen=True)
class FastPathResult:
    """Diagnostic outcome of a fast-path storage health check."""
    is_healthy: bool
    obsidian_ok: bool
    pyspark_ok: bool
    disk_free_gb: float
    duration_ms: float
    headroom_threshold_gb: float = 5.0
    details: Dict[str, Any] = field(default_factory=dict)


def is_storage_healthy(
    obsidian_path: Optional[Union[str, Path]] = None,
    pyspark_path: Optional[Union[str, Path]] = None,
    disk_check_path: Optional[Union[str, Path]] = None,
    min_free_gb: float = 5.0,
) -> bool:
    """
    Sub-3ms boolean fast-path check per Rule 6.3.
    
    Returns True if:
      1. obsidian_path exists and is a directory.
      2. pyspark_path exists and is a directory.
      3. disk free space on disk_check_path >= min_free_gb.
    """
    try:
        obs_p = str(obsidian_path or os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
        ))
        pysp_p = str(pyspark_path or os.environ.get(
            "PYSPARK_DATASET_PATH",
            "/Users/aaron/DFS_UNIFIED/lora_datasets"
        ))
        disk_p = str(disk_check_path or os.environ.get("HEADROOM_CHECK_PATH", "/Users/aaron"))
        
        obs_ok = os.path.isdir(obs_p)
        pysp_ok = os.path.isdir(pysp_p)
        
        stat_target = disk_p if os.path.exists(disk_p) else "/"
        free_bytes = shutil.disk_usage(stat_target).free
        disk_free_gb = free_bytes / (1024.0 ** 3)
        
        return obs_ok and pysp_ok and (disk_free_gb >= min_free_gb)
    except Exception:
        return False


def fast_path_check(
    obsidian_path: Optional[Union[str, Path]] = None,
    pyspark_path: Optional[Union[str, Path]] = None,
    disk_check_path: Optional[Union[str, Path]] = None,
    min_free_gb: float = 5.0,
) -> FastPathResult:
    """
    Detailed fast-path check returning diagnostic metrics and execution duration in milliseconds.
    """
    t_start = time.perf_counter()
    obs_p = str(obsidian_path or os.environ.get(
        "OBSIDIAN_VAULT_PATH",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    ))
    pysp_p = str(pyspark_path or os.environ.get(
        "PYSPARK_DATASET_PATH",
        "/Users/aaron/DFS_UNIFIED/lora_datasets"
    ))
    disk_p = str(disk_check_path or os.environ.get("HEADROOM_CHECK_PATH", "/Users/aaron"))
    
    obs_ok = False
    pysp_ok = False
    disk_free_gb = 0.0
    details: Dict[str, Any] = {}
    
    try:
        obs_ok = os.path.isdir(obs_p)
    except Exception as e:
        details["obsidian_error"] = str(e)
        
    try:
        pysp_ok = os.path.isdir(pysp_p)
    except Exception as e:
        details["pyspark_error"] = str(e)
        
    try:
        stat_target = disk_p if os.path.exists(disk_p) else "/"
        free_bytes = shutil.disk_usage(stat_target).free
        disk_free_gb = round(free_bytes / (1024.0 ** 3), 3)
    except Exception as e:
        details["disk_error"] = str(e)
        
    t_end = time.perf_counter()
    duration_ms = round((t_end - t_start) * 1000.0, 3)
    
    is_healthy = obs_ok and pysp_ok and (disk_free_gb >= min_free_gb)
    
    return FastPathResult(
        is_healthy=is_healthy,
        obsidian_ok=obs_ok,
        pyspark_ok=pysp_ok,
        disk_free_gb=disk_free_gb,
        duration_ms=duration_ms,
        headroom_threshold_gb=min_free_gb,
        details=details,
    )


class FastPathChecker:
    """Stateful fast-path checker class."""
    
    def __init__(
        self,
        obsidian_path: Optional[Union[str, Path]] = None,
        pyspark_path: Optional[Union[str, Path]] = None,
        git_path: Optional[Union[str, Path]] = None,
        min_free_gb: float = 5.0,
    ):
        self.obsidian_path = obsidian_path
        self.pyspark_path = pyspark_path
        self.git_path = git_path
        self.min_free_gb = min_free_gb

    def is_healthy(self) -> bool:
        return is_storage_healthy(
            obsidian_path=self.obsidian_path,
            pyspark_path=self.pyspark_path,
            disk_check_path=self.git_path,
            min_free_gb=self.min_free_gb,
        )

    def check(self) -> FastPathResult:
        return fast_path_check(
            obsidian_path=self.obsidian_path,
            pyspark_path=self.pyspark_path,
            disk_check_path=self.git_path,
            min_free_gb=self.min_free_gb,
        )
