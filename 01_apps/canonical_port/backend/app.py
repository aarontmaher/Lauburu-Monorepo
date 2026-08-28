"""
Canonical Port FastAPI Application
Version: 3.0.0-CANONICAL

Provides the master FastAPI application instance, lifespan lifecycle manager,
CORS configuration, WebSocket telemetry broadcast hubs, and REST routers for all 12 spec modules.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import current_utc_time
from .router import create_app_router
from .state import BackendStateStore, get_backend_state


class TelemetryWebSocketHub:
    """Manages active WebSocket subscriber connections for real-time telemetry streaming."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for d in disconnected:
                if d in self.active_connections:
                    self.active_connections.remove(d)


ws_hub = TelemetryWebSocketHub()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager governing startup and graceful shutdown."""
    state = get_backend_state()
    # Startup all spec modules
    for module in state.list_modules():
        try:
            await module.startup()
        except Exception:
            pass

    # Start autonomous background cron scheduler
    cron_scheduler = None
    try:
        from .agents.cron_scheduler import get_cron_scheduler
        cron_scheduler = get_cron_scheduler()
        cron_scheduler.start()
    except Exception:
        pass

    yield

    # Stop cron scheduler
    if cron_scheduler is not None:
        try:
            await cron_scheduler.stop()
        except Exception:
            pass

    # Shutdown all spec modules
    for module in state.list_modules():
        try:
            await module.shutdown()
        except Exception:
            pass


def create_app(state_store: BackendStateStore = None) -> FastAPI:
    """FastAPI application factory."""
    store = state_store or get_backend_state()

    app = FastAPI(
        title="Canonical Port Backend API",
        description="Unified 12 Spec Modules, 7-Layer Mesh Telemetry & Autonomous Routing Engine",
        version="3.0.0-CANONICAL",
        lifespan=lifespan,
    )

    # Configure CORS for localhost dashboards & hubs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:4000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:4000",
            "http://127.0.0.1:5173",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach unified /api/v1 router
    router = create_app_router(store)
    app.include_router(router)

    # Root discovery endpoint
    @app.get("/", summary="API Root Manifest")
    def root():
        summary = store.get_global_summary()
        return {
            "name": "Canonical Port Unified Backend",
            "version": "3.0.0-CANONICAL",
            "docs_url": "/docs",
            "api_v1_url": "/api/v1",
            "total_modules": summary["total_modules"],
            "healthy_modules": summary["healthy_modules"],
            "storage_healthy": summary["storage_healthy"],
            "timestamp": current_utc_time().isoformat(),
        }

    # Global Telemetry WebSocket endpoint
    @app.websocket("/ws/telemetry")
    async def websocket_telemetry_endpoint(websocket: WebSocket):
        await ws_hub.connect(websocket)
        try:
            # Send initial summary
            await websocket.send_json(store.get_global_summary())
            while True:
                # Keepalive / receive ping
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "poll":
                    await websocket.send_json(store.get_global_summary())
        except WebSocketDisconnect:
            await ws_hub.disconnect(websocket)
        except Exception:
            await ws_hub.disconnect(websocket)

    # Dedicated Network Pipeline Telemetry WebSocket endpoint
    @app.websocket("/ws/network/telemetry")
    async def websocket_network_telemetry_endpoint(websocket: WebSocket):
        from .pipeline import get_network_pipeline
        pipeline = get_network_pipeline()
        await websocket.accept()
        try:
            await websocket.send_json(pipeline.get_aggregated_metrics())
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
                elif data in ("poll", "metrics"):
                    await websocket.send_json(pipeline.get_aggregated_metrics())
                elif data == "anomalies":
                    await websocket.send_json({"anomalies": pipeline.get_anomalies(limit=50)})
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    # Specific Spec Module Telemetry WebSocket endpoint
    @app.websocket("/ws/apps/{module_id}")
    async def websocket_module_endpoint(websocket: WebSocket, module_id: str):
        mod = store.get_module(module_id)
        if not mod:
            await websocket.close(code=1000)
            return

        await websocket.accept()
        try:
            await websocket.send_json(mod.collect_telemetry())
            while True:
                data = await websocket.receive_text()
                if data in ("poll", "ping"):
                    await websocket.send_json(mod.collect_telemetry())
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    return app


# Module-level default application instance
app = create_app()
