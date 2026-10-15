"""
Dynamic RAM Governor & Memory Sentinel for Apple Silicon Metal Unified Memory.

Enforces strict host RAM safety thresholds (dynamic cap <= 90%, min headroom >= 2.50 GB),
tracks real-time system memory telemetry via psutil, and executes cache reclamation via
`gc.collect()` and `torch.mps.empty_cache()`.
"""

import gc
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

import psutil
import torch

logger = logging.getLogger(__name__)


class MemoryStatusTier(str, Enum):
    """Memory pressure tier categorization."""
    TIER_1_OPTIMAL = "TIER_1_OPTIMAL"       # Usage < 70%
    TIER_2_BALANCED = "TIER_2_BALANCED"     # 70% <= Usage < 85%
    TIER_3_RESTRICTED = "TIER_3_RESTRICTED" # 85% <= Usage <= 90% (and headroom >= min_headroom)
    TIER_4_CRITICAL = "TIER_4_CRITICAL"     # Usage > 90% or headroom < min_headroom


class MemoryGovernorError(RuntimeError):
    """Raised when memory headroom drops below safety floor or critical thresholds are violated."""
    pass


@dataclass(frozen=True)
class MemoryMetrics:
    """Snapshot of system memory state and safety parameters."""
    total_ram_gb: float
    used_ram_gb: float
    available_ram_gb: float
    usage_pct: float
    dynamic_cap_gb: float
    free_headroom_gb: float
    is_safe: bool
    status_tier: MemoryStatusTier
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ram_gb": round(self.total_ram_gb, 4),
            "used_ram_gb": round(self.used_ram_gb, 4),
            "available_ram_gb": round(self.available_ram_gb, 4),
            "usage_pct": round(self.usage_pct, 2),
            "dynamic_cap_gb": round(self.dynamic_cap_gb, 4),
            "free_headroom_gb": round(self.free_headroom_gb, 4),
            "is_safe": self.is_safe,
            "status_tier": self.status_tier.value,
            "timestamp": self.timestamp,
        }


class DynamicRAMGovernor:
    """
    Real-time Dynamic RAM Governor and Memory Sentinel.
    
    Invariants:
    - Max Host RAM Dynamic Cap <= 90.0% of physical RAM (e.g. 21.60 GB on 24.0 GB host)
    - Minimum Free Headroom Floor >= 2.50 GB
    - Governing Equation:
        Free Headroom = Dynamic Cap (GB) - Used RAM (GB)
        Safe <=> (Free Headroom >= min_headroom_gb) AND (System Usage % <= max_ram_ratio * 100)
    """

    DEFAULT_MAX_RAM_RATIO = 0.90
    DEFAULT_MIN_HEADROOM_GB = 2.50
    BYTES_IN_GB = 1024 ** 3

    def __init__(
        self,
        max_ram_ratio: float = DEFAULT_MAX_RAM_RATIO,
        min_headroom_gb: float = DEFAULT_MIN_HEADROOM_GB,
        vmem_provider: Optional[Callable[[], Any]] = None,
    ) -> None:
        """
        Initialize the Dynamic RAM Governor.
        
        Args:
            max_ram_ratio: Maximum allowable total RAM usage ratio (e.g., 0.90 for 90%).
            min_headroom_gb: Minimum allowable free memory headroom in Gigabytes (e.g., 2.50 GB).
            vmem_provider: Optional callable returning a psutil.virtual_memory-like object for testing.
        """
        if not (0.0 < max_ram_ratio <= 1.0):
            raise ValueError(f"max_ram_ratio must be in range (0.0, 1.0], got {max_ram_ratio}")
        if min_headroom_gb < 0.0:
            raise ValueError(f"min_headroom_gb must be non-negative, got {min_headroom_gb}")

        self.max_ram_ratio = float(max_ram_ratio)
        self.min_headroom_gb = float(min_headroom_gb)
        self._vmem_provider = vmem_provider or psutil.virtual_memory

    def get_metrics(self) -> MemoryMetrics:
        """
        Sample real-time memory metrics from the host operating system.
        
        Returns:
            MemoryMetrics containing accurate, unmocked memory status.
        """
        vmem = self._vmem_provider()
        now = time.time()

        total_gb = float(vmem.total) / self.BYTES_IN_GB
        used_gb = float(vmem.used) / self.BYTES_IN_GB
        available_gb = float(vmem.available) / self.BYTES_IN_GB
        usage_pct = float(vmem.percent)

        dynamic_cap_gb = total_gb * self.max_ram_ratio
        free_headroom_gb = max(0.0, dynamic_cap_gb - used_gb)

        # Rule #0 Dynamic Cap & Headroom Safety Invariant
        max_usage_pct = self.max_ram_ratio * 100.0
        is_safe = (free_headroom_gb >= self.min_headroom_gb) and (usage_pct <= max_usage_pct)

        # Classify status tier
        if not is_safe or usage_pct > max_usage_pct:
            tier = MemoryStatusTier.TIER_4_CRITICAL
        elif usage_pct >= 85.0:
            tier = MemoryStatusTier.TIER_3_RESTRICTED
        elif usage_pct >= 70.0:
            tier = MemoryStatusTier.TIER_2_BALANCED
        else:
            tier = MemoryStatusTier.TIER_1_OPTIMAL

        return MemoryMetrics(
            total_ram_gb=total_gb,
            used_ram_gb=used_gb,
            available_ram_gb=available_gb,
            usage_pct=usage_pct,
            dynamic_cap_gb=dynamic_cap_gb,
            free_headroom_gb=free_headroom_gb,
            is_safe=is_safe,
            status_tier=tier,
            timestamp=now,
        )

    def check_headroom(self) -> bool:
        """
        Interface contract for M1 <-> M2/M3:
        Returns True if free headroom >= min_headroom_gb and total RAM usage <= dynamic cap.
        """
        metrics = self.get_metrics()
        return metrics.is_safe

    def reclaim_memory(self) -> Dict[str, Any]:
        """
        Reclaim memory by triggering Python garbage collection and clearing PyTorch MPS cache.
        
        Interface contract:
        - Calls gc.collect()
        - Calls torch.mps.empty_cache() if MPS is available
        - Also handles CUDA if available for cross-platform robustness
        
        Returns:
            Dictionary with garbage collection statistics.
        """
        unreachable_objects = gc.collect()
        mps_cleared = False
        cuda_cleared = False

        if hasattr(torch, "backends") and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                try:
                    torch.mps.empty_cache()
                    mps_cleared = True
                except Exception as e:
                    logger.warning(f"Failed to clear PyTorch MPS cache: {e}")

        if hasattr(torch, "cuda") and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                cuda_cleared = True
            except Exception as e:
                logger.warning(f"Failed to clear PyTorch CUDA cache: {e}")

        return {
            "unreachable_objects_collected": unreachable_objects,
            "mps_cache_cleared": mps_cleared,
            "cuda_cache_cleared": cuda_cleared,
            "timestamp": time.time(),
        }

    def enforce_safety_limits(
        self,
        auto_reclaim: bool = True,
        max_wait_seconds: float = 0.0,
        poll_interval: float = 0.1,
    ) -> MemoryMetrics:
        """
        Enforce memory safety limits before proceeding with training steps.
        
        If memory headroom is violated and auto_reclaim is True, attempts memory reclamation.
        If still violated after optional wait period, raises MemoryGovernorError.
        
        Args:
            auto_reclaim: Whether to automatically call reclaim_memory() on pressure.
            max_wait_seconds: Maximum seconds to wait for memory pressure to subside.
            poll_interval: Polling interval in seconds when waiting.
            
        Returns:
            Current MemoryMetrics after enforcement.
            
        Raises:
            MemoryGovernorError: If memory headroom remains below floor.
        """
        metrics = self.get_metrics()
        if metrics.is_safe:
            return metrics

        if auto_reclaim:
            logger.info("Memory pressure detected; triggering proactive memory reclamation...")
            self.reclaim_memory()
            metrics = self.get_metrics()
            if metrics.is_safe:
                return metrics

        # If still unsafe, wait up to max_wait_seconds
        start_time = time.time()
        while not metrics.is_safe and (time.time() - start_time) < max_wait_seconds:
            time.sleep(poll_interval)
            if auto_reclaim:
                self.reclaim_memory()
            metrics = self.get_metrics()

        if not metrics.is_safe:
            msg = (
                f"Memory Governor Violation: Host RAM usage is {metrics.usage_pct:.1f}% "
                f"(max allowable {self.max_ram_ratio * 100:.1f}%), free headroom is "
                f"{metrics.free_headroom_gb:.2f} GB (minimum required {self.min_headroom_gb:.2f} GB). "
                f"Status Tier: {metrics.status_tier.value}."
            )
            logger.error(msg)
            raise MemoryGovernorError(msg)

        return metrics
