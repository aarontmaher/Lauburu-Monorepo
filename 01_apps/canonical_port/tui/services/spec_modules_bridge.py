"""
Canonical Spec Modules TUI Bridge Service
Version: 3.0.0-CANONICAL

Provides non-blocking, thread-safe access to the 12 backend spec modules,
health diagnostics, and telemetry streams for Python Textual TUI screens and widgets.
"""

import logging
import os
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

# Ensure backend package can be imported from root or canonical_port directory
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.base_module import BaseSpecModule
from backend.models import (
    GlobalBackendSummary,
    MeshNodeState,
    ModuleHealthStatus,
    SpecModuleMetadata,
    SpecModuleStatus,
)
from backend.state import BackendStateStore, get_backend_state

logger = logging.getLogger("canonical_port.tui.spec_modules_bridge")


class SpecModulesBridge:
    """
    Bridge connecting Textual TUI screens and views to the central backend state store.
    Ensures zero blocking on the UI event loop and enforces Rule #0 (Zero-Mock).
    """

    def __init__(self, state_store: Optional[BackendStateStore] = None) -> None:
        self._state_store = state_store or get_backend_state()
        self._lock = threading.RLock()
        self._subscribers: List[Callable[[str, Dict[str, Any]], None]] = []

    @property
    def state_store(self) -> BackendStateStore:
        """Access underlying backend state store."""
        return self._state_store

    def get_module(self, module_id: str) -> Optional[BaseSpecModule]:
        """Get live module instance by canonical ID or alias."""
        return self._state_store.get_module(module_id)

    def list_modules(self) -> List[BaseSpecModule]:
        """Return list of all registered spec modules."""
        return self._state_store.list_modules()

    def list_module_ids(self) -> List[str]:
        """Return all registered spec module IDs."""
        return self._state_store.list_module_ids()

    def get_module_status(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve real-time status dictionary for a specific spec module."""
        return self._state_store.get_module_status(module_id)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve live statuses for all 12 spec modules."""
        return self._state_store.get_all_statuses()

    def get_module_schema(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve telemetry schema for a specific spec module."""
        return self._state_store.get_module_schema(module_id)

    def get_module_telemetry(self, module_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent telemetry event history for a spec module."""
        return self._state_store.get_telemetry_history(module_id, limit=limit)

    def run_health_check(self, module_id: str) -> Dict[str, Any]:
        """Execute active diagnostic health check on a specific module."""
        mod = self._state_store.get_module(module_id)
        if not mod:
            return {
                "module_id": module_id,
                "healthy": False,
                "status": ModuleHealthStatus.OFFLINE.value,
                "error_message": f"Module '{module_id}' not found",
            }
        return mod.health_check()

    def run_all_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Execute health checks across all 12 spec modules."""
        return self._state_store.run_health_checks()

    def execute_action(
        self, module_id: str, action: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute an action on a target spec module."""
        return self._state_store.execute_module_action(module_id, action, params or {})

    def get_mesh_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve current status for 7-layer physical mesh nodes."""
        return self._state_store.get_mesh_nodes()

    def get_summary(self) -> Dict[str, Any]:
        """Retrieve global aggregate summary of backend and infrastructure."""
        return self._state_store.get_global_summary()

    def register_telemetry_subscriber(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a subscriber callback for new telemetry events."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def notify_telemetry(self, module_id: str, payload: Dict[str, Any]) -> None:
        """Dispatch telemetry update to registered TUI subscribers."""
        with self._lock:
            subscribers = list(self._subscribers)
        for sub in subscribers:
            try:
                sub(module_id, payload)
            except Exception as e:
                logger.warning(f"Error in telemetry subscriber: {e}")

    def sync_with_blackboard(self, blackboard_store: Any) -> None:
        """Optional synchronization hook with existing TUI BlackboardStore."""
        if not blackboard_store:
            return
        try:
            summary = self.get_summary()
            if hasattr(blackboard_store, "update_spec_modules_summary"):
                blackboard_store.update_spec_modules_summary(summary)
        except Exception as e:
            logger.debug(f"Blackboard sync notice: {e}")


# Global bridge singleton
_GLOBAL_BRIDGE: Optional[SpecModulesBridge] = None
_BRIDGE_LOCK = threading.RLock()


def get_spec_modules_bridge() -> SpecModulesBridge:
    """Return central SpecModulesBridge singleton."""
    global _GLOBAL_BRIDGE
    with _BRIDGE_LOCK:
        if _GLOBAL_BRIDGE is None:
            _GLOBAL_BRIDGE = SpecModulesBridge()
        return _GLOBAL_BRIDGE
