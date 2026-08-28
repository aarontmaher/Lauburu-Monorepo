"""
Canonical App Router & Spec Modules API
Version: 3.0.0-CANONICAL

Provides unified REST routing for all 12 Lauburu Spec Modules,
mesh telemetry streams, and module-specific custom action endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from .models import (
    GlobalBackendSummary,
    MeshNodeState,
    ModuleActionRequest,
    ModuleActionResponse,
    SpecModuleHealthCheckResult,
    SpecModuleMetadata,
    SpecModuleStatus,
    SpecModuleTelemetry,
    TelemetrySchemaDefinition,
    current_utc_time,
)
from .state import BackendStateStore, get_backend_state


def create_app_router(state_store: Optional[BackendStateStore] = None) -> APIRouter:
    """
    Factory creating the canonical /api/v1 APIRouter.
    Binds all 12 spec modules and their sub-routers.
    """
    store = state_store or get_backend_state()
    router = APIRouter(prefix="/api/v1", tags=["Canonical Port API v1"])

    # ========================================================================
    # Global & System Endpoints
    # ========================================================================

    @router.get("/health", response_model=Dict[str, Any], summary="Central Backend Health")
    def get_health() -> Dict[str, Any]:
        """Return central backend health check summary."""
        summary = store.get_global_summary()
        return {
            "status": "HEALTHY" if summary["storage_healthy"] else "DEGRADED",
            "version": summary["version"],
            "uptime_seconds": summary["uptime_seconds"],
            "total_modules": summary["total_modules"],
            "healthy_modules": summary["healthy_modules"],
            "storage_healthy": summary["storage_healthy"],
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/mesh/nodes", summary="7-Layer Physical Mesh Topology")
    def get_mesh_nodes() -> Dict[str, Any]:
        """Return status for all 7 physical mesh network nodes."""
        return {"nodes": store.get_mesh_nodes()}

    # ========================================================================
    # Spec Modules Core Endpoints
    # ========================================================================

    @router.get("/apps", summary="List All 12 Spec Modules")
    def list_apps() -> Dict[str, Any]:
        """Return metadata catalog for all registered spec modules."""
        modules = store.list_modules()
        catalog = [mod.get_metadata().model_dump() for mod in modules]
        return {
            "total_modules": len(catalog),
            "modules": catalog,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/apps/summary", summary="Global Spec Modules Summary")
    def get_apps_summary() -> Dict[str, Any]:
        """Return full global status summary across all 12 spec modules."""
        return store.get_global_summary()

    @router.get("/apps/{module_id}", summary="Spec Module Details")
    def get_app_details(module_id: str) -> Dict[str, Any]:
        """Return metadata and current status for a specific module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return {
            "metadata": mod.get_metadata().model_dump(),
            "status": mod.get_status(),
        }

    @router.get("/apps/{module_id}/status", summary="Spec Module Real-Time Status")
    def get_app_status(module_id: str) -> Dict[str, Any]:
        """Return live real-time status of specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return mod.get_status()

    @router.get("/apps/{module_id}/telemetry", summary="Spec Module Telemetry")
    def get_app_telemetry(
        module_id: str,
        limit: int = Query(20, ge=1, le=100, description="Max history records to return"),
    ) -> Dict[str, Any]:
        """Return recent telemetry history or live snapshot for specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        history = store.get_telemetry_history(mod.module_id, limit=limit)
        current_telemetry = mod.collect_telemetry()
        return {
            "module_id": mod.module_id,
            "current": current_telemetry,
            "history_count": len(history),
            "history": history,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/apps/{module_id}/schema", summary="Spec Module Telemetry Schema")
    def get_app_schema(module_id: str) -> Dict[str, Any]:
        """Return telemetry data schema definition for specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return mod.get_telemetry_schema()

    @router.get("/apps/{module_id}/health", summary="Spec Module Health Check")
    def get_app_health(module_id: str) -> Dict[str, Any]:
        """Execute active diagnostic health check on specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return mod.health_check()

    @router.post("/apps/{module_id}/action", summary="Execute Spec Module Action")
    def post_app_action(module_id: str, request: ModuleActionRequest) -> Dict[str, Any]:
        """Execute an action on specified module with parameters."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        res = mod.execute_action(request.action, request.params)
        return res

    # ========================================================================
    # Network Analysis Pipeline Endpoints
    # ========================================================================
    from .pipeline import get_network_pipeline

    @router.get("/network/metrics", summary="Aggregated 7-Layer Mesh Telemetry")
    def get_network_metrics() -> Dict[str, Any]:
        """Return non-blocking aggregated view of all known mesh nodes."""
        pipeline = get_network_pipeline()
        return pipeline.get_aggregated_metrics()

    @router.get("/network/anomalies", summary="Mesh Network Anomalies Log")
    def get_network_anomalies(
        limit: int = Query(50, ge=1, le=200, description="Max anomalies to return"),
        severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, WARNING, INFO"),
    ) -> Dict[str, Any]:
        """Return recent recorded anomalies across all mesh nodes."""
        pipeline = get_network_pipeline()
        anomalies = pipeline.get_anomalies(limit=limit, severity=severity)
        return {
            "total_anomalies": len(anomalies),
            "severity_filter": severity,
            "anomalies": anomalies,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.post("/network/ingest", summary="Ingest Mesh Telemetry Payload")
    async def post_network_ingest(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronously ingest a telemetry payload for a mesh node."""
        pipeline = get_network_pipeline()
        node_id = payload.get("node_id", "UNKNOWN")
        detected = await pipeline.ingest_payload(node_id, payload)
        return {
            "success": True,
            "node_id": node_id,
            "anomalies_detected": len(detected),
            "anomalies": detected,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.post("/network/obsidian/sync", summary="Trigger Obsidian Vault Telemetry Sync")
    def post_network_obsidian_sync() -> Dict[str, Any]:
        """Trigger Obsidian Vault markdown file synchronization for all nodes."""
        pipeline = get_network_pipeline()
        written = pipeline.sync_vault()
        metrics = pipeline.get_aggregated_metrics()
        anomalies = pipeline.get_anomalies(limit=20)
        daily_path = pipeline.vault_engine.generate_daily_log(metrics, anomalies)
        return {
            "success": True,
            "vault_dir": pipeline.vault_dir,
            "notes_synced": len(written),
            "synced_nodes": list(written.keys()),
            "daily_log_path": daily_path,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/network/buffer/{node_id}", summary="Node Time-Series Buffer")
    def get_network_node_buffer(
        node_id: str,
        limit: int = Query(50, ge=1, le=500, description="Max buffer samples to return"),
    ) -> Dict[str, Any]:
        """Return time-series ring buffer samples and statistics for a specific node."""
        pipeline = get_network_pipeline()
        buf = pipeline.get_node_buffer(node_id)
        if not buf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No buffer found for node '{node_id}'",
            )
        return {
            "node_id": node_id,
            "buffer_size": buf.size(),
            "stats": buf.get_stats(),
            "samples": [
                {"timestamp": t, "rtt_ms": v, "metadata": m}
                for t, v, m in buf.get_recent(limit)
            ],
            "timestamp": current_utc_time().isoformat(),
        }

    # ========================================================================
    # Autonomous Agents & Crons Ecosystem Endpoints
    # ========================================================================
    from .agents import create_agents_router

    agents_router = create_agents_router()
    router.include_router(agents_router)

    # ========================================================================
    # Attach Module-Specific Custom Sub-Routers
    # ========================================================================
    for mod in store.list_modules():
        sub_router = mod.get_routes()
        if sub_router:
            router.include_router(sub_router, prefix="/apps/custom")

    return router


# Module-level default router instance
app_router = create_app_router()
