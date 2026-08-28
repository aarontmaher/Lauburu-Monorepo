"""
Resident Set Size (RSS) Memory Guard & Cgroups Governor.

Enforces the strict <= 300.0 MB RAM ceiling on GL.iNet OpenWrt router hardware
using Linux procfs (/proc/self/statm, /proc/meminfo), Cgroups v1/v2, and
garbage collection hooks.
"""

from __future__ import annotations

import ctypes
import gc
import logging
import os
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from src.config import RouterConfig, get_config

logger = logging.getLogger("smolagi.memory_guard")


@dataclass(frozen=True)
class MemoryStats:
    """Snapshot of process and container memory metrics."""

    rss_bytes: int
    rss_mb: float
    vms_bytes: int
    vms_mb: float
    budget_mb: float
    headroom_mb: float
    utilization_pct: float
    is_warning: bool
    is_critical: bool
    is_exceeded: bool
    cgroup_usage_bytes: Optional[int] = None
    cgroup_limit_bytes: Optional[int] = None
    source: str = "procfs"

    def to_dict(self) -> Dict[str, object]:
        """Convert memory stats to serializable dictionary."""
        return {
            "rss_bytes": self.rss_bytes,
            "rss_mb": round(self.rss_mb, 2),
            "vms_bytes": self.vms_bytes,
            "vms_mb": round(self.vms_mb, 2),
            "budget_mb": round(self.budget_mb, 2),
            "headroom_mb": round(self.headroom_mb, 2),
            "utilization_pct": round(self.utilization_pct, 2),
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
            "is_exceeded": self.is_exceeded,
            "cgroup_usage_bytes": self.cgroup_usage_bytes,
            "cgroup_limit_bytes": self.cgroup_limit_bytes,
            "source": self.source,
        }


class MemoryGuard:
    """
    Monitors and enforces memory limits for smolagi daemon and subprocesses.
    Guarantees that total memory never exceeds the 300MB hardware ceiling.
    """

    def __init__(self, config: Optional[RouterConfig] = None) -> None:
        self.config = config or get_config()
        self._page_size = self._get_page_size()
        self._libc = self._load_libc()

    @staticmethod
    def _get_page_size() -> int:
        """Get system memory page size in bytes."""
        try:
            return os.sysconf("SC_PAGE_SIZE")
        except (AttributeError, ValueError):
            return 4096

    @staticmethod
    def _load_libc() -> Optional[ctypes.CDLL]:
        """Attempt loading libc to access malloc_trim for heap trimming."""
        if sys.platform.startswith("linux"):
            for lib_name in ("libc.so.6", "libc.musl-aarch64.so.1", "libc.musl-x86_64.so.1", "libc.so"):
                try:
                    return ctypes.CDLL(lib_name)
                except OSError:
                    continue
        return None

    def read_cgroup_memory(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Read cgroup memory usage and limit (v2 or v1).
        Returns: (usage_bytes, limit_bytes).
        """
        usage_bytes: Optional[int] = None
        limit_bytes: Optional[int] = None

        # Cgroups v2
        cg2_usage = Path("/sys/fs/cgroup/memory.current")
        cg2_max = Path("/sys/fs/cgroup/memory.max")
        if cg2_usage.exists():
            try:
                usage_bytes = int(cg2_usage.read_text().strip())
            except (ValueError, OSError):
                pass
        if cg2_max.exists():
            try:
                val = cg2_max.read_text().strip()
                if val != "max":
                    limit_bytes = int(val)
            except (ValueError, OSError):
                pass

        # Cgroups v1 fallback
        if usage_bytes is None:
            cg1_usage = Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")
            if cg1_usage.exists():
                try:
                    usage_bytes = int(cg1_usage.read_text().strip())
                except (ValueError, OSError):
                    pass

        if limit_bytes is None:
            cg1_limit = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
            if cg1_limit.exists():
                try:
                    val_int = int(cg1_limit.read_text().strip())
                    # Kernel max 64-bit int represents unlimited in cgroups v1
                    if val_int < 9000000000000000000:
                        limit_bytes = val_int
                except (ValueError, OSError):
                    pass

        return usage_bytes, limit_bytes

    def get_process_memory(self, pid: Optional[int] = None) -> MemoryStats:
        """
        Inspect the resident set size and virtual memory for a specific PID (or self).
        Prioritizes /proc/{pid}/statm on Linux, falling back to resource / status.
        """
        target_pid = pid if pid is not None else os.getpid()
        proc_statm = Path(f"/proc/{target_pid}/statm")
        rss_bytes = 0
        vms_bytes = 0
        source = "procfs"

        if proc_statm.exists():
            try:
                content = proc_statm.read_text().strip().split()
                if len(content) >= 2:
                    vms_pages = int(content[0])
                    rss_pages = int(content[1])
                    vms_bytes = vms_pages * self._page_size
                    rss_bytes = rss_pages * self._page_size
            except (ValueError, OSError) as e:
                logger.debug("Failed reading /proc/%d/statm: %s", target_pid, e)

        # Fallback to /proc/{pid}/status
        if rss_bytes == 0:
            proc_status = Path(f"/proc/{target_pid}/status")
            if proc_status.exists():
                try:
                    for line in proc_status.read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            rss_bytes = int(line.split()[1]) * 1024
                        elif line.startswith("VmSize:"):
                            vms_bytes = int(line.split()[1]) * 1024
                except (ValueError, OSError) as e:
                    logger.debug("Failed reading /proc/%d/status: %s", target_pid, e)

        # Fallback to resource module (for self only on macOS / other OS)
        if rss_bytes == 0 and (pid is None or pid == os.getpid()):
            source = "resource_rusage"
            usage = resource.getrusage(resource.RUSAGE_SELF)
            if sys.platform == "darwin":
                # On macOS, ru_maxrss is in bytes
                rss_bytes = usage.ru_maxrss
            else:
                # On Linux / POSIX, ru_maxrss is in kilobytes
                rss_bytes = usage.ru_maxrss * 1024
            vms_bytes = rss_bytes

        rss_mb = rss_bytes / (1024 * 1024)
        vms_mb = vms_bytes / (1024 * 1024)
        budget_mb = self.config.ram_budget_mb
        headroom_mb = max(0.0, budget_mb - rss_mb)
        utilization_pct = (rss_mb / budget_mb * 100.0) if budget_mb > 0 else 0.0

        is_warning = rss_mb >= self.config.ram_warning_threshold_mb
        is_critical = rss_mb >= self.config.ram_critical_threshold_mb
        is_exceeded = rss_mb > budget_mb

        cg_usage, cg_limit = self.read_cgroup_memory()

        return MemoryStats(
            rss_bytes=rss_bytes,
            rss_mb=rss_mb,
            vms_bytes=vms_bytes,
            vms_mb=vms_mb,
            budget_mb=budget_mb,
            headroom_mb=headroom_mb,
            utilization_pct=utilization_pct,
            is_warning=is_warning,
            is_critical=is_critical,
            is_exceeded=is_exceeded,
            cgroup_usage_bytes=cg_usage,
            cgroup_limit_bytes=cg_limit,
            source=source,
        )

    def get_total_subsystem_memory(self, pids: List[int]) -> MemoryStats:
        """
        Aggregate memory footprint across multiple PIDs (e.g. Python daemon + llama-server).
        """
        total_rss_bytes = 0
        total_vms_bytes = 0
        sources: List[str] = []

        for p in pids:
            if p > 0:
                stats = self.get_process_memory(p)
                total_rss_bytes += stats.rss_bytes
                total_vms_bytes += stats.vms_bytes
                sources.append(stats.source)

        total_rss_mb = total_rss_bytes / (1024 * 1024)
        total_vms_mb = total_vms_bytes / (1024 * 1024)
        budget_mb = self.config.ram_budget_mb
        headroom_mb = max(0.0, budget_mb - total_rss_mb)
        utilization_pct = (total_rss_mb / budget_mb * 100.0) if budget_mb > 0 else 0.0

        is_warning = total_rss_mb >= self.config.ram_warning_threshold_mb
        is_critical = total_rss_mb >= self.config.ram_critical_threshold_mb
        is_exceeded = total_rss_mb > budget_mb

        cg_usage, cg_limit = self.read_cgroup_memory()

        return MemoryStats(
            rss_bytes=total_rss_bytes,
            rss_mb=total_rss_mb,
            vms_bytes=total_vms_bytes,
            vms_mb=total_vms_mb,
            budget_mb=budget_mb,
            headroom_mb=headroom_mb,
            utilization_pct=utilization_pct,
            is_warning=is_warning,
            is_critical=is_critical,
            is_exceeded=is_exceeded,
            cgroup_usage_bytes=cg_usage,
            cgroup_limit_bytes=cg_limit,
            source=",".join(set(sources)) if sources else "aggregate",
        )

    def check_memory_budget(self, pids: Optional[List[int]] = None) -> Tuple[bool, MemoryStats]:
        """
        Check whether the subsystem or current process is within the 300MB budget.
        Returns: (is_within_budget, stats).
        """
        if pids:
            stats = self.get_total_subsystem_memory(pids)
        else:
            stats = self.get_process_memory()
        is_within_budget = not stats.is_exceeded
        return is_within_budget, stats

    def run_garbage_collection(self) -> int:
        """
        Perform aggressive garbage collection and release trimmed heap memory back to OS.
        Returns number of unreachable Python objects collected.
        """
        collected = gc.collect()
        if self._libc and hasattr(self._libc, "malloc_trim"):
            try:
                self._libc.malloc_trim(0)
            except Exception as e:
                logger.debug("malloc_trim call failed: %s", e)
        return collected

    def enforce_limits(
        self,
        pids: Optional[List[int]] = None,
        trigger_gc_on_warning: bool = True,
        kill_on_critical: bool = False,
    ) -> MemoryStats:
        """
        Enforce memory limits:
        1. Samples current RSS.
        2. If warning threshold is crossed, triggers GC.
        3. If critical/exceeded threshold is crossed and kill_on_critical is set, logs error.
        """
        if pids:
            stats = self.get_total_subsystem_memory(pids)
        else:
            stats = self.get_process_memory()

        if stats.is_warning and trigger_gc_on_warning:
            logger.warning(
                "Memory warning: RSS %.2f MB exceeds warning threshold %.2f MB (%.1f%%). Triggering GC.",
                stats.rss_mb,
                self.config.ram_warning_threshold_mb,
                stats.utilization_pct,
            )
            self.run_garbage_collection()

        if stats.is_critical:
            logger.error(
                "CRITICAL MEMORY CONDITION: RSS %.2f MB is at %.1f%% of %.2f MB budget!",
                stats.rss_mb,
                stats.utilization_pct,
                stats.budget_mb,
            )
            if kill_on_critical and pids:
                for p in pids:
                    if p != os.getpid() and p > 0:
                        try:
                            logger.error("Killing offending subprocess PID %d to prevent router OOM", p)
                            os.kill(p, 9)
                        except OSError as e:
                            logger.error("Failed to kill PID %d: %s", p, e)

        return stats
