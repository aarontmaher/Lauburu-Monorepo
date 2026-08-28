"""
Base Spec Module Abstract Interface
Version: 3.0.0-CANONICAL

Defines the universal contract for all 12 Lauburu Spec Modules.
Provides standard lifecycle, health check, status inspection, telemetry schema,
and custom route attachment interfaces.
"""

from abc import ABC, abstractmethod
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter

from .models import (
    ModuleCategory,
    ModuleHealthStatus,
    SpecModuleMetadata,
    SpecModuleStatus,
    SpecModuleTelemetry,
    SpecModuleHealthCheckResult,
    TelemetrySchemaDefinition,
    current_utc_time
)


class BaseSpecModule(ABC):
    """
    Abstract base class governing all canonical Lauburu spec modules.
    Every spec module (Spec-00 through Spec-12) must inherit from this class
    and implement the canonical lifecycle and diagnostic methods.
    """

    module_id: str
    display_name: str
    spec_version: str = "3.0.0"
    category: ModuleCategory = ModuleCategory.INFRASTRUCTURE
    description: str = ""
    spec_path: Optional[str] = None
    dependencies: List[str] = []
    enabled: bool = True
    tags: List[str] = []

    def __init__(self) -> None:
        self.start_time: float = time.time()
        self.error_count: int = 0
        self._custom_router: Optional[APIRouter] = None
        self._endpoints: Dict[str, str] = {}

    @property
    def uptime_seconds(self) -> float:
        """Calculate elapsed uptime in seconds."""
        return max(0.0, time.time() - self.start_time)

    def get_metadata(self) -> SpecModuleMetadata:
        """Return declarative metadata for this spec module."""
        return SpecModuleMetadata(
            module_id=self.module_id,
            display_name=self.display_name,
            spec_version=self.spec_version,
            category=self.category,
            description=self.description,
            spec_path=self.spec_path,
            dependencies=self.dependencies,
            enabled=self.enabled,
            tags=self.tags,
        )

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Return real-time health and status dictionary for the module.
        Must follow Rule #0 (Zero-Mock): reflects genuine sockets, files, and state.
        """
        pass

    @abstractmethod
    def get_telemetry_schema(self) -> Dict[str, Any]:
        """
        Return telemetry data schema definition detailing all emitted fields.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Execute active diagnostic checks and return structured health result.
        Returns dict matching SpecModuleHealthCheckResult structure.
        """
        pass

    @abstractmethod
    def get_routes(self) -> APIRouter:
        """
        Return dedicated FastAPI APIRouter for this module's custom sub-endpoints.
        """
        pass

    def collect_telemetry(self) -> Dict[str, Any]:
        """
        Produce a live telemetry event snapshot.
        Default implementation wraps get_status() metrics into standard envelope.
        """
        status_data = self.get_status()
        metrics = status_data.get("metrics", {})
        return {
            "module_id": self.module_id,
            "timestamp": current_utc_time().isoformat(),
            "telemetry_type": "status_heartbeat",
            "payload": status_data,
            "raw_metrics": {k: v for k, v in metrics.items() if isinstance(v, (int, float, bool, str))},
            "schema_version": self.spec_version,
        }

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an imperative module command or action.
        Subclasses should override to handle module-specific actions.
        """
        return {
            "success": False,
            "action": action,
            "message": f"Action '{action}' is not supported by {self.module_id}",
            "data": {},
            "timestamp": current_utc_time().isoformat(),
        }

    async def startup(self) -> None:
        """Asynchronous lifecycle startup hook called on application boot."""
        pass

    async def shutdown(self) -> None:
        """Asynchronous lifecycle cleanup hook called on application exit."""
        pass
