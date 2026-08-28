"""
canonical_sync_engine.verification.headroom
Disk headroom and inode capacity validator enforcing Rule 6.1 thresholds (>= 10.0 GB).
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


@dataclass
class HeadroomStatus:
    """Detailed diagnostic status for filesystem headroom and inode capacity."""
    is_sufficient: bool
    free_gb: float
    total_gb: float
    used_gb: float
    percent_used: float
    percent_free: float
    path: str
    min_headroom_gb: float
    inode_free: Optional[int] = None
    inode_total: Optional[int] = None
    inode_percent_free: Optional[float] = None
    violation_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Union[str, float, int, bool, None]]:
        return {
            "is_sufficient": self.is_sufficient,
            "free_gb": round(self.free_gb, 2),
            "total_gb": round(self.total_gb, 2),
            "used_gb": round(self.used_gb, 2),
            "percent_used": round(self.percent_used, 2),
            "percent_free": round(self.percent_free, 2),
            "path": self.path,
            "min_headroom_gb": self.min_headroom_gb,
            "inode_free": self.inode_free,
            "inode_total": self.inode_total,
            "inode_percent_free": self.inode_percent_free,
            "violation_message": self.violation_message,
        }


def check_disk_headroom(
    path: Union[str, Path] = "/Users/aaron",
    min_headroom_gb: float = 10.0,
    min_inode_percent: float = 5.0,
) -> HeadroomStatus:
    """
    Checks if the target filesystem has >= min_headroom_gb free space and sufficient inodes.
    """
    target_path = str(Path(path).expanduser().resolve())
    lookup_path = target_path
    
    # Resolve target directory or closest existing parent
    while not os.path.exists(lookup_path) and lookup_path != os.path.dirname(lookup_path):
        lookup_path = os.path.dirname(lookup_path)
    if not os.path.exists(lookup_path):
        lookup_path = "/"
        
    usage = shutil.disk_usage(lookup_path)
    total_gb = round(usage.total / (1024.0 ** 3), 3)
    free_gb = round(usage.free / (1024.0 ** 3), 3)
    used_gb = round(usage.used / (1024.0 ** 3), 3)
    
    pct_used = round((used_gb / total_gb * 100.0) if total_gb > 0 else 0.0, 2)
    pct_free = round((free_gb / total_gb * 100.0) if total_gb > 0 else 0.0, 2)
    
    # Inode inspection on POSIX
    inode_free = None
    inode_total = None
    inode_pct_free = None
    inode_violation = False
    
    if hasattr(os, "statvfs"):
        try:
            st = os.statvfs(lookup_path)
            if st.f_files > 0:
                inode_total = st.f_files
                inode_free = st.f_favail
                inode_pct_free = round((inode_free / inode_total * 100.0), 2)
                if inode_pct_free < min_inode_percent:
                    inode_violation = True
        except Exception:
            pass
            
    is_space_sufficient = free_gb >= min_headroom_gb
    is_sufficient = is_space_sufficient and not inode_violation
    
    violation_msg = None
    if not is_space_sufficient:
        violation_msg = (
            f"Disk free space ({free_gb:.2f} GB) on '{target_path}' is below required "
            f"headroom threshold of {min_headroom_gb:.2f} GB (Total: {total_gb:.2f} GB, Used: {pct_used}%)."
        )
    elif inode_violation:
        violation_msg = (
            f"Available inodes ({inode_pct_free}%) on '{target_path}' is below required "
            f"threshold of {min_inode_percent}% (Free inodes: {inode_free}/{inode_total})."
        )
        
    return HeadroomStatus(
        is_sufficient=is_sufficient,
        free_gb=free_gb,
        total_gb=total_gb,
        used_gb=used_gb,
        percent_used=pct_used,
        percent_free=pct_free,
        path=target_path,
        min_headroom_gb=min_headroom_gb,
        inode_free=inode_free,
        inode_total=inode_total,
        inode_percent_free=inode_pct_free,
        violation_message=violation_msg,
    )


def check_multi_mount_headroom(
    paths: List[Union[str, Path]],
    min_headroom_gb: float = 10.0,
) -> Dict[str, HeadroomStatus]:
    """Inspects multiple paths across mounts and returns a dictionary of statuses."""
    return {str(p): check_disk_headroom(p, min_headroom_gb=min_headroom_gb) for p in paths}


class HeadroomValidator:
    """Stateful headroom validator across multiple monitored paths."""

    def __init__(
        self,
        min_headroom_gb: float = 10.0,
        paths: Optional[List[Union[str, Path]]] = None,
    ):
        self.min_headroom_gb = min_headroom_gb
        self.paths = paths or ["/Users/aaron"]

    def validate(self) -> Dict[str, HeadroomStatus]:
        return check_multi_mount_headroom(self.paths, min_headroom_gb=self.min_headroom_gb)

    def check(self) -> Tuple[bool, float, List[str]]:
        """
        Returns:
            Tuple of (is_all_sufficient, lowest_free_gb, list_of_violations)
        """
        statuses = self.validate()
        violations: List[str] = []
        lowest_free = float("inf")
        all_ok = True

        for st in statuses.values():
            if st.free_gb < lowest_free:
                lowest_free = st.free_gb
            if not st.is_sufficient:
                all_ok = False
                if st.violation_message:
                    violations.append(st.violation_message)

        if lowest_free == float("inf"):
            lowest_free = 0.0

        return all_ok, lowest_free, violations
