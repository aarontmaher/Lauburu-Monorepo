"""
Canonical Spec Modules & Telemetry Pydantic Data Models
Version: 3.0.0-CANONICAL

Provides strongly typed Pydantic models for all 12 Lauburu spec modules,
telemetry payloads, physical mesh node representations, and health check results.

Strictly follows Rule #0 (Zero-Mock & Zero-Simulated Data):
- Accurate representations of live system states, hardware metrics, and kernel APIs.
- Clean null / None semantics for unreached endpoints.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


def current_utc_time() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


class ModuleHealthStatus(str, Enum):
    """Health classification for spec modules and physical nodes."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    INITIALIZING = "INITIALIZING"
    MAINTENANCE = "MAINTENANCE"


class ModuleCategory(str, Enum):
    """Categorization for Lauburu 12 Spec Modules."""
    INFRASTRUCTURE = "INFRASTRUCTURE"         # spec-00
    APPS = "APPS"                             # spec-01
    INFERENCE = "INFERENCE"                   # spec-02
    BIOMETRICS = "BIOMETRICS"                 # spec-03
    DATA = "DATA"                             # spec-04
    AGENTS = "AGENTS"                         # spec-05
    TOOLING = "TOOLING"                       # spec-06
    DOCS = "DOCS"                             # spec-07
    COMMERCE = "COMMERCE"                     # spec-08
    PRODUCTION = "PRODUCTION"                 # spec-09
    KINEMATICS = "KINEMATICS"                 # spec-10
    SECURITY = "SECURITY"                     # spec-11
    LORA_EVOLUTION = "LORA_EVOLUTION"         # spec-12


class SpecModuleMetadata(BaseModel):
    """Static and declarative metadata describing a spec module."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    module_id: str = Field(..., description="Canonical ID, e.g. 'spec-00', 'spec-01'")
    display_name: str = Field(..., description="Human-readable module title")
    spec_version: str = Field("3.0.0", description="Semantic spec version")
    category: ModuleCategory = Field(..., description="Architecture category")
    description: str = Field("", description="Detailed functional scope")
    spec_path: Optional[str] = Field(None, description="Path to canonical SPEC markdown")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite spec modules")
    enabled: bool = Field(True, description="Whether module is active in current runtime")
    tags: List[str] = Field(default_factory=list, description="Search and routing tags")


class SpecModuleStatus(BaseModel):
    """Dynamic real-time status and operational metrics for a spec module."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    module_id: str
    display_name: str
    status: ModuleHealthStatus = ModuleHealthStatus.INITIALIZING
    uptime_seconds: float = 0.0
    last_check: datetime = Field(default_factory=current_utc_time)
    message: str = "Initialized"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    active_connections: int = 0
    error_count: int = 0
    endpoints: Dict[str, str] = Field(default_factory=dict)


class TelemetryFieldSchema(BaseModel):
    """Field definition for telemetry data schema."""
    field_name: str
    field_type: str
    unit: Optional[str] = None
    description: str = ""
    required: bool = True


class TelemetrySchemaDefinition(BaseModel):
    """Schema descriptor for structured telemetry emitted by a spec module."""
    module_id: str
    schema_name: str
    version: str = "1.0.0"
    fields: List[TelemetryFieldSchema] = Field(default_factory=list)
    description: str = ""


class SpecModuleTelemetry(BaseModel):
    """Structured telemetry event payload emitted by a spec module."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    module_id: str
    timestamp: datetime = Field(default_factory=current_utc_time)
    telemetry_type: str = "heartbeat"
    payload: Dict[str, Any] = Field(default_factory=dict)
    raw_metrics: Dict[str, Union[float, int, str, bool, None]] = Field(default_factory=dict)
    schema_version: str = "1.0.0"


class SpecModuleHealthCheckResult(BaseModel):
    """Individual health check diagnosis result for a spec module."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    module_id: str
    healthy: bool
    status: ModuleHealthStatus
    latency_ms: float = 0.0
    checks: Dict[str, bool] = Field(default_factory=dict)
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=current_utc_time)
    error_message: Optional[str] = None


class ModuleActionRequest(BaseModel):
    """Request envelope for invoking an action on a spec module."""
    action: str = Field(..., description="Action name to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action arguments")


class ModuleActionResponse(BaseModel):
    """Response envelope after invoking an action on a spec module."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    action: str
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=current_utc_time)


class MeshNodeState(BaseModel):
    """Physical 7-layer mesh network node status representation."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_id: str = Field(..., description="Canonical node key (e.g. L1_Mac_Node)")
    name: str = Field(..., description="Display name")
    layer: str = Field(..., description="Physical layer (L1..L7, GW)")
    local_ip: Optional[str] = None
    tailscale_ip: Optional[str] = None
    ram_total_gb: float = 0.0
    ram_ai_cap_gb: float = 0.0
    role: str = ""
    status: ModuleHealthStatus = ModuleHealthStatus.OFFLINE
    ping_ms: Optional[float] = None
    active_services: List[str] = Field(default_factory=list)
    last_seen: datetime = Field(default_factory=current_utc_time)


class GlobalBackendSummary(BaseModel):
    """Global aggregate summary of all 12 spec modules and physical infrastructure."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: datetime = Field(default_factory=current_utc_time)
    version: str = "3.0.0-CANONICAL"
    total_modules: int = 12
    healthy_modules: int = 0
    degraded_modules: int = 0
    offline_modules: int = 0
    modules: Dict[str, SpecModuleStatus] = Field(default_factory=dict)
    mesh_nodes: Dict[str, MeshNodeState] = Field(default_factory=dict)
    storage_healthy: bool = True
    disk_free_gb: float = 0.0
