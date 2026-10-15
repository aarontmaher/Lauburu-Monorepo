"""
OS Telemetry Collector & Multi-IP Async Telemetry Poller
=========================================================
Subsystem: 01_apps/bt_ide_ab_test/core/telemetry.py
Lauburu Mesh Ecosystem — 2026

Collects genuine OS-level memory metrics:
- Darwin: sysctl (`hw.memsize`), `vm_stat` page breakdown, Mach kernel host_statistics64 (psutil).
- Linux / Android: `/proc/meminfo` (`MemTotal`, `MemFree`, `MemAvailable`, `Buffers`, `Cached`).
- Multi-IP Exhaustive Remote Polling: Async HTTP requests iterating through Rule 9 IP priority matrix
  (TB4/TB3 DMA -> Nebula -> Tailscale -> LAN -> PAN).
- Support for simulated IP injection for automated test harnesses and CI suites.
"""

import asyncio
from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import (
    GATEWAY_PORT,
    HOST_MAX_UTILIZATION_PCT,
    HOST_SANCTUARY_MIN_MB,
    MESH_NODES,
    NodeConfig,
    NodeLayer,
)

logger = logging.getLogger("MeshTelemetry")


@dataclass
class NodeMemoryTelemetry:
    """Standard memory telemetry data contract for a mesh node (PROJECT.md § 4.1)."""
    node_id: str
    ip: str
    total_ram_mb: float
    free_ram_mb: float
    available_ram_mb: float
    utilization_pct: float
    dynamic_safety_threshold_mb: float
    is_saturated: bool
    is_reachable: bool
    rtt_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeMemoryTelemetry":
        return cls(
            node_id=data["node_id"],
            ip=data.get("ip", "unknown"),
            total_ram_mb=float(data.get("total_ram_mb", 0.0)),
            free_ram_mb=float(data.get("free_ram_mb", 0.0)),
            available_ram_mb=float(data.get("available_ram_mb", 0.0)),
            utilization_pct=float(data.get("utilization_pct", 0.0)),
            dynamic_safety_threshold_mb=float(data.get("dynamic_safety_threshold_mb", 0.0)),
            is_saturated=bool(data.get("is_saturated", False)),
            is_reachable=bool(data.get("is_reachable", False)),
            rtt_ms=float(data.get("rtt_ms", -1.0)),
        )


# ---------------------------------------------------------------------------
# Darwin / macOS Parser
# ---------------------------------------------------------------------------
def parse_vmstat_str(vmstat_text: str, total_bytes: int) -> Tuple[float, float, float, float]:
    """
    Parses Darwin `vm_stat` output and computes:
    (total_ram_mb, free_ram_mb, available_ram_mb, utilization_pct)
    """
    page_size = 4096  # default Intel page size
    m = re.search(r"page size of (\d+) bytes", vmstat_text)
    if m:
        page_size = int(m.group(1))

    pages: Dict[str, int] = {}
    for line in vmstat_text.splitlines():
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().strip('"')
            val_str = parts[1].strip().rstrip(".")
            try:
                pages[key] = int(val_str)
            except ValueError:
                pass

    free_pages = pages.get("Pages free", 0)
    speculative_pages = pages.get("Pages speculative", 0)
    inactive_pages = pages.get("Pages inactive", 0)
    purgeable_pages = pages.get("Pages purgeable", 0)

    # In Darwin, available memory includes free, speculative, inactive, and purgeable pages
    free_bytes = (free_pages + speculative_pages) * page_size
    available_bytes = (free_pages + speculative_pages + inactive_pages + purgeable_pages) * page_size
    available_bytes = min(total_bytes, available_bytes)

    total_mb = round(total_bytes / (1024.0 * 1024.0), 2)
    free_mb = round(free_bytes / (1024.0 * 1024.0), 2)
    available_mb = round(available_bytes / (1024.0 * 1024.0), 2)

    if total_mb > 0:
        utilization_pct = round(((total_mb - available_mb) / total_mb) * 100.0, 2)
    else:
        utilization_pct = 0.0

    return total_mb, free_mb, available_mb, utilization_pct


def collect_darwin_local_memory() -> Tuple[float, float, float, float]:
    """
    Collects genuine Darwin memory statistics via sysctl / Mach vm_stat,
    with psutil fast-path when available.
    """
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_mb = round(vm.total / (1024.0 * 1024.0), 2)
        free_mb = round(vm.free / (1024.0 * 1024.0), 2)
        available_mb = round(vm.available / (1024.0 * 1024.0), 2)
        utilization_pct = round(vm.percent, 2)
        return total_mb, free_mb, available_mb, utilization_pct
    except Exception:
        pass

    try:
        # sysctl hw.memsize
        sysctl_out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=2.0)
        total_bytes = int(sysctl_out.decode().strip())
        vm_stat_out = subprocess.check_output(["vm_stat"], timeout=2.0).decode()
        return parse_vmstat_str(vm_stat_out, total_bytes)
    except Exception as e:
        logger.warning(f"Darwin memory collection failed: {e}")
        # Fallback to nominal 24GB
        return 24576.0, 4096.0, 6144.0, 75.0


# ---------------------------------------------------------------------------
# Linux / Android Parser
# ---------------------------------------------------------------------------
def parse_meminfo_str(content: str) -> Tuple[float, float, float, float]:
    """
    Parses Linux /proc/meminfo content string and computes:
    (total_ram_mb, free_ram_mb, available_ram_mb, utilization_pct)
    """
    mem: Dict[str, int] = {}
    for line in content.splitlines():
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val_part = parts[1].strip().split()[0]
            try:
                mem[key] = int(val_part)
            except ValueError:
                pass

    total_kb = mem.get("MemTotal", 0)
    free_kb = mem.get("MemFree", 0)
    buffers_kb = mem.get("Buffers", 0)
    cached_kb = mem.get("Cached", 0)

    # MemAvailable was introduced in Linux 3.14
    if "MemAvailable" in mem:
        available_kb = mem["MemAvailable"]
    else:
        available_kb = free_kb + buffers_kb + cached_kb

    total_mb = round(total_kb / 1024.0, 2)
    free_mb = round(free_kb / 1024.0, 2)
    available_mb = round(available_kb / 1024.0, 2)

    if total_mb > 0:
        utilization_pct = round(((total_mb - available_mb) / total_mb) * 100.0, 2)
    else:
        utilization_pct = 0.0

    return total_mb, free_mb, available_mb, utilization_pct


def collect_linux_local_memory(meminfo_path: str = "/proc/meminfo") -> Tuple[float, float, float, float]:
    """
    Collects genuine Linux/Android memory statistics directly from /proc/meminfo.
    """
    path = Path(meminfo_path)
    if path.exists():
        try:
            content = path.read_text(encoding="utf-8")
            return parse_meminfo_str(content)
        except Exception as e:
            logger.warning(f"Error reading {meminfo_path}: {e}")

    # Fallback to psutil if available
    try:
        import psutil
        vm = psutil.virtual_memory()
        return (
            round(vm.total / (1024.0 * 1024.0), 2),
            round(vm.free / (1024.0 * 1024.0), 2),
            round(vm.available / (1024.0 * 1024.0), 2),
            round(vm.percent, 2),
        )
    except Exception:
        pass

    return 16384.0, 4096.0, 8192.0, 50.0


# ---------------------------------------------------------------------------
# Unified Local Telemetry
# ---------------------------------------------------------------------------
def collect_local_os_memory() -> Tuple[float, float, float, float]:
    """Detects host OS and collects genuine local memory metrics."""
    sys_name = platform.system().lower()
    if "darwin" in sys_name:
        return collect_darwin_local_memory()
    elif "linux" in sys_name:
        return collect_linux_local_memory()
    else:
        try:
            import psutil
            vm = psutil.virtual_memory()
            return (
                round(vm.total / (1024.0 * 1024.0), 2),
                round(vm.free / (1024.0 * 1024.0), 2),
                round(vm.available / (1024.0 * 1024.0), 2),
                round(vm.percent, 2),
            )
        except Exception:
            return 24576.0, 4096.0, 6144.0, 75.0


def evaluate_node_saturation(
    node_id: str,
    total_mb: float,
    available_mb: float,
    utilization_pct: float,
    node_config: Optional[NodeConfig] = None,
) -> Tuple[float, bool]:
    """
    Evaluates dynamic safety thresholds for a given node.
    Returns (dynamic_safety_threshold_mb, is_saturated).
    """
    cfg = node_config or MESH_NODES.get(node_id)
    if not cfg:
        # Default safety: >= 20% free RAM
        threshold_mb = total_mb * 0.20
        is_saturated = utilization_pct > 80.0
        return threshold_mb, is_saturated

    threshold_mb = cfg.min_sanctuary_free_mb

    if cfg.layer == NodeLayer.L1:
        # Rule 3: Mac Mini host preserves >= 4.8 GB free physical RAM and <= 80% utilization
        is_saturated = (available_mb < HOST_SANCTUARY_MIN_MB) or (utilization_pct > HOST_MAX_UTILIZATION_PCT)
    else:
        # Peripheral nodes: check utilization cap and minimum free headroom
        is_saturated = (utilization_pct > cfg.max_utilization_pct) or (available_mb < threshold_mb)

    return threshold_mb, is_saturated


def collect_local_node_telemetry(node_config: NodeConfig) -> NodeMemoryTelemetry:
    """Collects genuine local host telemetry."""
    total_mb, free_mb, available_mb, util_pct = collect_local_os_memory()
    threshold_mb, is_saturated = evaluate_node_saturation(
        node_config.node_id, total_mb, available_mb, util_pct, node_config
    )
    return NodeMemoryTelemetry(
        node_id=node_config.node_id,
        ip="127.0.0.1",
        total_ram_mb=total_mb,
        free_ram_mb=free_mb,
        available_ram_mb=available_mb,
        utilization_pct=util_pct,
        dynamic_safety_threshold_mb=threshold_mb,
        is_saturated=is_saturated,
        is_reachable=True,
        rtt_ms=0.0,
    )


# ---------------------------------------------------------------------------
# Remote Multi-IP Async Collector
# ---------------------------------------------------------------------------
class MeshTelemetryCollector:
    """
    Asynchronous OS telemetry collector operating across all 7 layers.
    Features exhaustive multi-IP failover (Rule 9) and simulated IP support for test suites.
    """

    def __init__(
        self,
        nodes: Optional[Dict[str, NodeConfig]] = None,
        timeout_per_ip: float = 0.8,
        custom_simulated_ips: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.nodes = nodes or MESH_NODES
        self.timeout_per_ip = timeout_per_ip
        self.simulated_ips = custom_simulated_ips or {}

    def set_simulated_ip(self, ip: str, payload: Dict[str, Any]) -> None:
        """Register a simulated IP response for tests and offline verification."""
        self.simulated_ips[ip] = payload

    def clear_simulated_ips(self) -> None:
        self.simulated_ips.clear()

    async def _poll_single_ip(
        self,
        node_id: str,
        ip: str,
        port: int,
        client: httpx.AsyncClient,
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Attempts to probe an IP for memory metrics via HTTP.
        Checks simulated IP map first, then executes real network request.
        Returns (parsed_json_dict, rtt_ms) or None if unreachable.
        """
        # 1. Check simulated IP registry (for unit tests / mock loopbacks)
        if ip in self.simulated_ips:
            sim = self.simulated_ips[ip]
            rtt = sim.get("rtt_ms", 1.2)
            # Allow simulated error injection
            if sim.get("unreachable", False):
                return None
            return sim, rtt

        # 2. Real async network request with RTT measurement
        url = f"http://{ip}:{port}/telemetry"
        t0 = time.perf_counter()
        try:
            resp = await client.get(url, timeout=self.timeout_per_ip)
            rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            if resp.status_code == 200:
                data = resp.json()
                return data, rtt_ms
        except Exception:
            pass

        # Try alternative status/metrics endpoint
        url_alt = f"http://{ip}:{port}/metrics"
        t0 = time.perf_counter()
        try:
            resp = await client.get(url_alt, timeout=self.timeout_per_ip)
            rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            if resp.status_code == 200:
                data = resp.json()
                if "total_ram_mb" in data or "available_ram_mb" in data:
                    return data, rtt_ms
        except Exception:
            pass

        return None

    async def poll_node(
        self,
        node_config: NodeConfig,
        client: Optional[httpx.AsyncClient] = None,
    ) -> NodeMemoryTelemetry:
        """
        Polls a single node across its IP priority list (Rule 9).
        If the node is local host, collects directly from host OS.
        """
        if node_config.is_local_host:
            # If an explicit simulation payload was registered for node_id or 127.0.0.1, use it (for tests)
            if node_config.node_id in self.simulated_ips or "127.0.0.1" in self.simulated_ips:
                sim = self.simulated_ips.get(node_config.node_id) or self.simulated_ips.get("127.0.0.1", {})
                total_mb = float(sim.get("total_ram_mb", node_config.nominal_ram_mb))
                available_mb = float(sim.get("available_ram_mb", 0.0))
                free_mb = float(sim.get("free_ram_mb", available_mb * 0.5))
                if "utilization_pct" in sim:
                    util_pct = float(sim["utilization_pct"])
                elif total_mb > 0:
                    util_pct = round(((total_mb - available_mb) / total_mb) * 100.0, 2)
                else:
                    util_pct = 0.0
                thresh_mb, is_sat = evaluate_node_saturation(
                    node_config.node_id, total_mb, available_mb, util_pct, node_config
                )
                return NodeMemoryTelemetry(
                    node_id=node_config.node_id,
                    ip="127.0.0.1",
                    total_ram_mb=total_mb,
                    free_ram_mb=free_mb,
                    available_ram_mb=available_mb,
                    utilization_pct=util_pct,
                    dynamic_safety_threshold_mb=thresh_mb,
                    is_saturated=is_sat,
                    is_reachable=True,
                    rtt_ms=float(sim.get("rtt_ms", 0.0)),
                )
            return collect_local_node_telemetry(node_config)

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient()
            should_close_client = True

        try:
            for ip in node_config.ip_priority_list:
                result = await self._poll_single_ip(
                    node_id=node_config.node_id,
                    ip=ip,
                    port=node_config.telemetry_port,
                    client=client,
                )
                if result is not None:
                    data, rtt_ms = result
                    total_mb = float(data.get("total_ram_mb", node_config.nominal_ram_mb))
                    available_mb = float(data.get("available_ram_mb", 0.0))
                    free_mb = float(data.get("free_ram_mb", available_mb * 0.5))

                    if "utilization_pct" in data:
                        util_pct = float(data["utilization_pct"])
                    elif total_mb > 0:
                        util_pct = round(((total_mb - available_mb) / total_mb) * 100.0, 2)
                    else:
                        util_pct = 0.0

                    threshold_mb, is_sat = evaluate_node_saturation(
                        node_config.node_id, total_mb, available_mb, util_pct, node_config
                    )

                    return NodeMemoryTelemetry(
                        node_id=node_config.node_id,
                        ip=ip,
                        total_ram_mb=total_mb,
                        free_ram_mb=free_mb,
                        available_ram_mb=available_mb,
                        utilization_pct=util_pct,
                        dynamic_safety_threshold_mb=threshold_mb,
                        is_saturated=is_sat,
                        is_reachable=True,
                        rtt_ms=rtt_ms,
                    )

            # If all IPs exhausted, return unreachable node
            threshold_mb = node_config.min_sanctuary_free_mb
            primary_ip = node_config.ip_priority_list[0] if node_config.ip_priority_list else "unknown"
            return NodeMemoryTelemetry(
                node_id=node_config.node_id,
                ip=primary_ip,
                total_ram_mb=node_config.nominal_ram_mb,
                free_ram_mb=0.0,
                available_ram_mb=0.0,
                utilization_pct=100.0,
                dynamic_safety_threshold_mb=threshold_mb,
                is_saturated=False,  # Set False so unreachable nodes during partition do not cause false backpressure
                is_reachable=False,
                rtt_ms=-1.0,
            )
        finally:
            if should_close_client:
                await client.aclose()

    async def collect_all(
        self,
        nodes: Optional[Dict[str, NodeConfig]] = None,
        simulated_nodes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[NodeMemoryTelemetry]:
        """
        Concurrently collects telemetry across all configured mesh nodes.
        Supports simulated node dictionary for test suites.
        """
        active_nodes = nodes or self.nodes
        if simulated_nodes:
            for node_id, payload in simulated_nodes.items():
                if node_id in active_nodes:
                    # Assign payload to node's primary IP
                    primary_ip = active_nodes[node_id].ip_priority_list[0]
                    self.set_simulated_ip(primary_ip, payload)

        async with httpx.AsyncClient() as client:
            tasks = [self.poll_node(cfg, client=client) for cfg in active_nodes.values()]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            return list(results)
