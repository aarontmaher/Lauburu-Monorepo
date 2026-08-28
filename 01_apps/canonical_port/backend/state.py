"""
Canonical Backend State Store
Version: 3.0.0-CANONICAL

Thread-safe and asynchronous state store holding live registrations for all 12 spec modules,
telemetry ring buffers, 7-layer physical mesh node states, and health diagnostics.
"""

import collections
import os
import shutil
import threading
import time
from typing import Any, Dict, List, Optional, Union

from .base_module import BaseSpecModule
from .models import (
    GlobalBackendSummary,
    MeshNodeState,
    ModuleHealthStatus,
    SpecModuleMetadata,
    SpecModuleStatus,
    current_utc_time,
)
from .spec_modules import create_all_spec_modules


class BackendStateStore:
    """
    Authoritative Central Backend State Store.
    Maintains active module instances, telemetry history ring buffers, and physical mesh nodes.
    """

    def __init__(self, auto_init_defaults: bool = True) -> None:
        self._lock = threading.RLock()
        self._modules: Dict[str, BaseSpecModule] = {}
        self._telemetry_history: Dict[str, collections.deque] = {}
        self._mesh_nodes: Dict[str, MeshNodeState] = {}
        self._max_history_per_module: int = 100
        self._start_time: float = time.time()

        if auto_init_defaults:
            self.initialize_defaults()

    @property
    def uptime_seconds(self) -> float:
        """Calculate state store elapsed uptime."""
        return max(0.0, time.time() - self._start_time)

    def initialize_defaults(self) -> None:
        """Register all 12 canonical spec modules and seed 7-layer physical mesh nodes."""
        with self._lock:
            # 1. Register all canonical spec modules
            for module in create_all_spec_modules():
                self.register_module(module)

            # 2. Seed 7-layer physical mesh node topology
            mesh_seed = [
                MeshNodeState(
                    node_id="L1_Mac_Node",
                    name="Apple M4 Pro Mac Mini Host",
                    layer="L1",
                    local_ip="192.168.8.230",
                    tailscale_ip="100.119.199.76",
                    ram_total_gb=24.0,
                    ram_ai_cap_gb=21.6,
                    role="Primary Host & Memory Governor",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["canonical_port", "llama_rpc_8081", "seaweedfs", "blackboard_store"],
                ),
                MeshNodeState(
                    node_id="L2_MacBook_Pro",
                    name="Apple M3 Max MacBook Pro",
                    layer="L2",
                    local_ip="192.168.8.127",
                    tailscale_ip="100.103.212.21",
                    ram_total_gb=16.0,
                    ram_ai_cap_gb=14.0,
                    role="Metal GPU RPC & Storage Vault (TB4 DMA 0.27ms)",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["llama_rpc_8082", "model_vault_285gb"],
                ),
                MeshNodeState(
                    node_id="L3_Linux_Head_Node",
                    name="AMD Ryzen 7 5700U Linux Compute Hub",
                    layer="L3",
                    local_ip="192.168.8.224",
                    tailscale_ip="100.101.39.98",
                    ram_total_gb=16.0,
                    ram_ai_cap_gb=13.8,
                    role="Gateway Ingress, Petals DHT Bootstrap & Ray Hub",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["llama_rpc_8083", "petals_dht", "docker_hub"],
                ),
                MeshNodeState(
                    node_id="L4_Linux_Tablet",
                    name="Debian Linux Tablet",
                    layer="L4",
                    local_ip=None,
                    tailscale_ip="100.81.92.125",
                    ram_total_gb=8.0,
                    ram_ai_cap_gb=6.5,
                    role="Mobile Linux Compute & Touch DSP",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["lightweight_biometrics", "petals_worker"],
                ),
                MeshNodeState(
                    node_id="L5_MacBook_Air",
                    name="Apple M4 MacBook Air",
                    layer="L5",
                    local_ip="192.168.8.222",
                    tailscale_ip="100.93.158.96",
                    ram_total_gb=16.0,
                    ram_ai_cap_gb=14.0,
                    role="LoRA Distillation Metal Worker",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["llama_rpc_8084", "lora_worker"],
                ),
                MeshNodeState(
                    node_id="L6_Pixel_10_Pro_XL",
                    name="Google Tensor G5 Pixel 10 Pro XL",
                    layer="L6",
                    local_ip=None,
                    tailscale_ip="100.73.38.87",
                    ram_total_gb=16.0,
                    ram_ai_cap_gb=12.5,
                    role="8K Vision Stream & Edge TPU / UWB 3D Positioning",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["edge_tpu_inference", "uwb_positioning"],
                ),
                MeshNodeState(
                    node_id="L7_Samsung_S20",
                    name="Samsung Exynos 990 Galaxy S20",
                    layer="L7",
                    local_ip=None,
                    tailscale_ip="100.84.40.95",
                    ram_total_gb=12.0,
                    ram_ai_cap_gb=9.0,
                    role="Dedicated Automated UI Tester & OpenClaw Agent",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["router_usb_adb", "openclaw_agent"],
                ),
                MeshNodeState(
                    node_id="GW_GLiNet_Router",
                    name="GL.iNet Core Gateway (GL-MT3600BE)",
                    layer="GW",
                    local_ip="192.168.8.1",
                    tailscale_ip="100.122.185.123",
                    ram_total_gb=1.0,
                    ram_ai_cap_gb=0.0,
                    role="Core Gateway & Hardware USB ADB Bridge",
                    status=ModuleHealthStatus.HEALTHY,
                    active_services=["wireguard_gw", "usb_adb_daemon"],
                ),
            ]
            for node in mesh_seed:
                self._mesh_nodes[node.node_id] = node

    def register_module(self, module: BaseSpecModule) -> None:
        """Register a spec module in the central store."""
        with self._lock:
            self._modules[module.module_id] = module
            if module.module_id not in self._telemetry_history:
                self._telemetry_history[module.module_id] = collections.deque(
                    maxlen=self._max_history_per_module
                )
            # Record initial heartbeat telemetry
            initial_telemetry = module.collect_telemetry()
            self._telemetry_history[module.module_id].append(initial_telemetry)

    def unregister_module(self, module_id: str) -> bool:
        """Unregister a spec module by ID."""
        with self._lock:
            if module_id in self._modules:
                del self._modules[module_id]
                return True
            return False

    def get_module(self, module_id: str) -> Optional[BaseSpecModule]:
        """Lookup module instance by canonical ID or alias."""
        with self._lock:
            # Direct match
            if module_id in self._modules:
                return self._modules[module_id]
            # Normalization match (e.g. '01' -> 'spec-01')
            clean_id = module_id.lower().replace("_", "-")
            if clean_id in self._modules:
                return self._modules[clean_id]
            if not clean_id.startswith("spec-"):
                alt_id = f"spec-{clean_id}"
                if alt_id in self._modules:
                    return self._modules[alt_id]
            return None

    def list_modules(self) -> List[BaseSpecModule]:
        """Return list of all registered module instances."""
        with self._lock:
            return list(self._modules.values())

    def list_module_ids(self) -> List[str]:
        """Return list of all registered module IDs."""
        with self._lock:
            return list(self._modules.keys())

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return real-time status dictionary for every registered module."""
        with self._lock:
            statuses = {}
            for mod_id, mod in self._modules.items():
                try:
                    statuses[mod_id] = mod.get_status()
                except Exception as e:
                    statuses[mod_id] = {
                        "module_id": mod_id,
                        "display_name": mod.display_name,
                        "status": ModuleHealthStatus.OFFLINE.value,
                        "uptime_seconds": round(mod.uptime_seconds, 2),
                        "last_check": current_utc_time().isoformat(),
                        "message": f"Error polling status: {str(e)}",
                        "metrics": {},
                        "active_connections": 0,
                        "error_count": mod.error_count + 1,
                    }
            return statuses

    def get_module_status(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Return real-time status of a specific module."""
        mod = self.get_module(module_id)
        if not mod:
            return None
        return mod.get_status()

    def get_module_schema(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Return telemetry schema for a specific module."""
        mod = self.get_module(module_id)
        if not mod:
            return None
        return mod.get_telemetry_schema()

    def record_telemetry(self, module_id: str, telemetry: Dict[str, Any]) -> None:
        """Append a telemetry record to the module's ring buffer."""
        with self._lock:
            if module_id not in self._telemetry_history:
                self._telemetry_history[module_id] = collections.deque(
                    maxlen=self._max_history_per_module
                )
            if "timestamp" not in telemetry:
                telemetry["timestamp"] = current_utc_time().isoformat()
            self._telemetry_history[module_id].append(telemetry)

    def get_telemetry_history(self, module_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent telemetry history for a module up to the specified limit."""
        with self._lock:
            # Resolve module alias if necessary
            target_id = module_id
            mod = self.get_module(module_id)
            if mod:
                target_id = mod.module_id

            if target_id not in self._telemetry_history:
                return []
            history = list(self._telemetry_history[target_id])
            return history[-limit:]

    def run_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Execute active diagnostic health checks across all registered modules."""
        with self._lock:
            results = {}
            for mod_id, mod in self._modules.items():
                try:
                    results[mod_id] = mod.health_check()
                except Exception as e:
                    results[mod_id] = {
                        "module_id": mod_id,
                        "healthy": False,
                        "status": ModuleHealthStatus.OFFLINE.value,
                        "latency_ms": 0.0,
                        "checks": {"execution": False},
                        "details": {"error": str(e)},
                        "timestamp": current_utc_time().isoformat(),
                        "error_message": str(e),
                    }
            return results

    def get_mesh_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Return status for all 7 physical mesh network nodes."""
        with self._lock:
            return {node_id: node.model_dump() for node_id, node in self._mesh_nodes.items()}

    def execute_module_action(self, module_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action on a target module."""
        mod = self.get_module(module_id)
        if not mod:
            return {
                "success": False,
                "action": action,
                "message": f"Module '{module_id}' not found",
                "data": {},
                "timestamp": current_utc_time().isoformat(),
            }
        return mod.execute_action(action, params)

    def get_global_summary(self) -> Dict[str, Any]:
        """Construct aggregated global backend status summary."""
        with self._lock:
            statuses = self.get_all_statuses()
            healthy_count = sum(1 for s in statuses.values() if s.get("status") == ModuleHealthStatus.HEALTHY.value)
            degraded_count = sum(1 for s in statuses.values() if s.get("status") == ModuleHealthStatus.DEGRADED.value)
            offline_count = sum(1 for s in statuses.values() if s.get("status") == ModuleHealthStatus.OFFLINE.value)

            try:
                free_gb = shutil.disk_usage("/Users/aaron").free / (1024 ** 3)
            except Exception:
                free_gb = 0.0

            obsidian_ok = os.path.isdir("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
            storage_healthy = obsidian_ok and free_gb >= 5.0

            summary = {
                "timestamp": current_utc_time().isoformat(),
                "version": "3.0.0-CANONICAL",
                "uptime_seconds": round(self.uptime_seconds, 2),
                "total_modules": len(self._modules),
                "healthy_modules": healthy_count,
                "degraded_modules": degraded_count,
                "offline_modules": offline_count,
                "storage_healthy": storage_healthy,
                "disk_free_gb": round(free_gb, 2),
                "modules": statuses,
                "mesh_nodes": self.get_mesh_nodes(),
            }
            return summary


# Global singleton instance
_GLOBAL_BACKEND_STATE: Optional[BackendStateStore] = None
_STATE_LOCK = threading.RLock()


def get_backend_state() -> BackendStateStore:
    """Return central BackendStateStore singleton."""
    global _GLOBAL_BACKEND_STATE
    with _STATE_LOCK:
        if _GLOBAL_BACKEND_STATE is None:
            _GLOBAL_BACKEND_STATE = BackendStateStore(auto_init_defaults=True)
        return _GLOBAL_BACKEND_STATE


def reset_backend_state() -> BackendStateStore:
    """Reset and re-instantiate central BackendStateStore singleton (for tests)."""
    global _GLOBAL_BACKEND_STATE
    with _STATE_LOCK:
        _GLOBAL_BACKEND_STATE = BackendStateStore(auto_init_defaults=True)
        return _GLOBAL_BACKEND_STATE
