"""
Spec-01: Applications Ecosystem Module
Governs Port 4000 Hub, Movesense Hub (512Hz ECG), Zone 2 Trainer,
Shopify AI Commerce, 3D Spatial Grappling, and Termux Edge.
"""

import os
import socket
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter

from ..base_module import BaseSpecModule
from ..models import ModuleCategory, ModuleHealthStatus, current_utc_time


def probe_socket(host: str, port: int, timeout: float = 0.2) -> bool:
    """Probe if a TCP socket endpoint is actively listening."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


class Spec01AppsEcosystemModule(BaseSpecModule):
    """Spec-01 Applications Ecosystem."""

    module_id: str = "spec-01"
    display_name: str = "Spec-01 Applications Ecosystem"
    spec_version: str = "3.0.0"
    category: ModuleCategory = ModuleCategory.APPS
    description: str = "Port 4000 Hub, Movesense Hub, Zone 2 Trainer, Shopify AI, 3D Grappling, Termux Edge"
    spec_path: Optional[str] = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/README.md"
    dependencies: List[str] = ["spec-00"]
    tags: ["apps", "hub_4000", "movesense", "zone2", "shopify", "grappling_3d", "termux"]

    def __init__(self) -> None:
        super().__init__()
        self._apps_base_dir = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps"
        self._port_4000_hub = 4000
        self._movesense_hub_port = 8080
        self._termux_ssh_port = 8022

    def _discover_apps(self) -> List[Dict[str, Any]]:
        """Inspect and discover active apps on disk."""
        known_apps = [
            {"id": "port_4000_hub", "name": "Port 4000 Unified Web Hub", "dir": "hub_4000", "port": 4000},
            {"id": "movesense_hub", "name": "Movesense 512Hz ECG Hub", "dir": "movesense_hub", "port": 8080},
            {"id": "zone_2", "name": "Zone 2 Endurance Trainer", "dir": "zone_2", "port": 8000},
            {"id": "shopify_ai", "name": "Shopify AI Commerce Interface", "dir": "shopify_ai", "port": 3000},
            {"id": "spatial_grappling", "name": "3D Spatial Grappling Viewer", "dir": "spatial_grappling_3d", "port": 5173},
            {"id": "canonical_port", "name": "Canonical Port Terminal Hub", "dir": "canonical_port", "port": 8000},
        ]
        results = []
        for app in known_apps:
            path = os.path.join(self._apps_base_dir, app["dir"])
            exists = os.path.isdir(path)
            is_listening = probe_socket("127.0.0.1", app["port"]) if app["port"] else False
            results.append({
                "id": app["id"],
                "name": app["name"],
                "directory": path,
                "installed": exists,
                "running": is_listening,
                "port": app["port"],
            })
        return results

    def get_status(self) -> Dict[str, Any]:
        """Return live health and status dict."""
        apps = self._discover_apps()
        hub_online = probe_socket("127.0.0.1", self._port_4000_hub)
        movesense_online = probe_socket("127.0.0.1", self._movesense_hub_port)
        installed_count = sum(1 for a in apps if a["installed"])
        running_count = sum(1 for a in apps if a["running"])

        status = ModuleHealthStatus.HEALTHY if installed_count >= 3 else ModuleHealthStatus.DEGRADED

        metrics = {
            "total_apps_catalog": len(apps),
            "installed_apps_count": installed_count,
            "running_apps_count": running_count,
            "port_4000_hub_online": hub_online,
            "movesense_hub_online": movesense_online,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }

        return {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "status": status.value,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "last_check": current_utc_time().isoformat(),
            "message": f"{installed_count} apps installed, {running_count} active",
            "metrics": metrics,
            "active_connections": running_count,
            "error_count": self.error_count,
            "endpoints": {
                "web_hub": f"http://localhost:{self._port_4000_hub}",
                "movesense_hub": f"http://localhost:{self._movesense_hub_port}",
            },
        }

    def get_telemetry_schema(self) -> Dict[str, Any]:
        """Return telemetry schema."""
        return {
            "module_id": self.module_id,
            "schema_name": "apps_ecosystem_telemetry",
            "version": self.spec_version,
            "description": "Telemetry for Port 4000 Hub and application instances",
            "fields": [
                {"field_name": "total_apps_catalog", "field_type": "integer", "required": True},
                {"field_name": "installed_apps_count", "field_type": "integer", "required": True},
                {"field_name": "running_apps_count", "field_type": "integer", "required": True},
                {"field_name": "port_4000_hub_online", "field_type": "boolean", "required": True},
                {"field_name": "movesense_hub_online", "field_type": "boolean", "required": True},
                {"field_name": "uptime_seconds", "field_type": "float", "unit": "s", "required": True},
            ],
        }

    def health_check(self) -> Dict[str, Any]:
        """Execute active diagnostic health checks."""
        t0 = time.time()
        apps = self._discover_apps()
        installed_count = sum(1 for a in apps if a["installed"])
        latency_ms = (time.time() - t0) * 1000.0

        checks = {
            "apps_directory_present": os.path.isdir(self._apps_base_dir),
            "canonical_port_present": os.path.isdir(os.path.join(self._apps_base_dir, "canonical_port")),
            "minimum_apps_installed": installed_count >= 3,
        }

        healthy = checks["apps_directory_present"] and checks["canonical_port_present"]
        status = ModuleHealthStatus.HEALTHY if healthy else ModuleHealthStatus.DEGRADED

        return {
            "module_id": self.module_id,
            "healthy": healthy,
            "status": status.value,
            "latency_ms": round(latency_ms, 2),
            "checks": checks,
            "details": {"apps": apps},
            "timestamp": current_utc_time().isoformat(),
            "error_message": None if healthy else "Core apps directory missing or corrupt",
        }

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute module action."""
        if action == "list_apps":
            return {
                "success": True,
                "action": action,
                "message": "Apps catalog retrieved",
                "data": {"apps": self._discover_apps()},
                "timestamp": current_utc_time().isoformat(),
            }
        return super().execute_action(action, params)

    def get_routes(self) -> APIRouter:
        """Return dedicated APIRouter for Spec-01."""
        router = APIRouter(prefix="/spec-01", tags=["Spec-01 Apps Ecosystem"])

        @router.get("/apps-catalog")
        def get_apps_catalog():
            return {"apps": self._discover_apps()}

        @router.get("/hub-status")
        def get_hub_status():
            return {
                "port_4000_online": probe_socket("127.0.0.1", self._port_4000_hub),
                "movesense_online": probe_socket("127.0.0.1", self._movesense_hub_port),
            }

        return router
