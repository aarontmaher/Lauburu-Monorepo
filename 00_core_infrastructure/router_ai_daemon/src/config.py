"""
Global Configuration for smolagi Router AI Daemon.

Maintains hardware limits, memory thresholds, process parameters,
paths, and environment overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RouterConfig:
    """Immutable configuration instance for router AI daemon runtime."""

    # -------------------------------------------------------------------------
    # Hardware & Memory Budget Constraints (<= 300.0 MB Hard Ceiling)
    # -------------------------------------------------------------------------
    ram_budget_mb: float = field(
        default_factory=lambda: float(os.getenv("ROUTER_AI_RAM_BUDGET_MB", "300.0"))
    )
    ram_warning_threshold_mb: float = field(
        default_factory=lambda: float(os.getenv("ROUTER_AI_RAM_WARNING_MB", "240.0"))
    )
    ram_critical_threshold_mb: float = field(
        default_factory=lambda: float(os.getenv("ROUTER_AI_RAM_CRITICAL_MB", "270.0"))
    )

    # -------------------------------------------------------------------------
    # Network & Daemon Host/Port Bindings
    # -------------------------------------------------------------------------
    daemon_host: str = field(
        default_factory=lambda: os.getenv("ROUTER_AI_HOST", "127.0.0.1")
    )
    daemon_port: int = field(
        default_factory=lambda: int(os.getenv("ROUTER_AI_PORT", "8080"))
    )
    llama_server_host: str = field(
        default_factory=lambda: os.getenv("LLAMA_SERVER_HOST", "127.0.0.1")
    )
    llama_server_port: int = field(
        default_factory=lambda: int(os.getenv("LLAMA_SERVER_PORT", "8081"))
    )

    # -------------------------------------------------------------------------
    # Default Sub-1B Model Specifications
    # -------------------------------------------------------------------------
    default_model_filename: str = "smollm2-135m-instruct-q4_k_m.gguf"
    default_model_size_mb: float = 105.4
    max_model_size_mb: float = 200.0
    model_path: str = field(
        default_factory=lambda: os.getenv(
            "MODEL_PATH", "/models/smollm2-135m-instruct-q4_k_m.gguf"
        )
    )

    # -------------------------------------------------------------------------
    # llama.cpp Static Inference Parameters (Tuned for 300MB Bound)
    # -------------------------------------------------------------------------
    llama_binary_path: str = field(
        default_factory=lambda: os.getenv(
            "LLAMA_BINARY_PATH", "/usr/local/bin/llama-server"
        )
    )
    context_size: int = 1024
    batch_size: int = 128
    ubatch_size: int = 32
    threads: int = 3
    parallel_slots: int = 1
    cache_type_k: str = "q4_0"
    cache_type_v: str = "q4_0"
    no_mmap: bool = True
    cont_batching: bool = True
    log_disable: bool = True

    # -------------------------------------------------------------------------
    # Volatile Storage Paths (Zero-Flash-Wear Invariant)
    # -------------------------------------------------------------------------
    tmpfs_models_dir: str = field(
        default_factory=lambda: os.getenv("TMPFS_MODELS_DIR", "/models")
    )
    tmpfs_telemetry_dir: str = field(
        default_factory=lambda: os.getenv("TMPFS_TELEMETRY_DIR", "/tmp/telemetry")
    )
    tmpfs_cache_dir: str = field(
        default_factory=lambda: os.getenv("TMPFS_CACHE_DIR", "/tmp/cache")
    )

    # -------------------------------------------------------------------------
    # OpenWrt Host Integration Paths
    # -------------------------------------------------------------------------
    ubus_socket_path: str = field(
        default_factory=lambda: os.getenv(
            "UBUS_SOCKET_PATH", "/var/run/ubus/ubus.sock"
        )
    )
    host_proc_path: str = field(
        default_factory=lambda: os.getenv("HOST_PROC_PATH", "/proc")
    )

    # -------------------------------------------------------------------------
    # Timeouts and Intervals
    # -------------------------------------------------------------------------
    health_check_timeout_sec: float = 2.0
    health_check_interval_sec: float = 5.0
    process_shutdown_timeout_sec: float = 3.0

    def validate(self) -> None:
        """Validate configuration invariants."""
        if self.ram_budget_mb > 300.0:
            raise ValueError(
                f"RAM budget {self.ram_budget_mb} MB exceeds hard ceiling of 300.0 MB"
            )
        if self.ram_warning_threshold_mb >= self.ram_critical_threshold_mb:
            raise ValueError("Warning threshold must be strictly less than critical threshold")
        if self.ram_critical_threshold_mb > self.ram_budget_mb:
            raise ValueError("Critical threshold cannot exceed total RAM budget")


# Singleton instance for easy import across modules
CONFIG = RouterConfig()


def get_config() -> RouterConfig:
    """Return active RouterConfig instance."""
    return CONFIG
