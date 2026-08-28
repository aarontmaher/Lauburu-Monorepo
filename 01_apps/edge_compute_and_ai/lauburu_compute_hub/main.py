"""
main.py - Lauburu Compute Hub & Dynamic Telemetry WebSocket Server
Strict Rule #0 Compliance: Zero-Mock Real-Time Telemetry Pipeline.
Streams genuine 1-2 Hz multi-subsystem telemetry frames to LiveDeviceSentinelHUD and dashboard clients.
"""

import asyncio
import logging
from typing import List, Set, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from telemetry_poller import HostTelemetryPoller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("LauburuComputeHub")

poller = HostTelemetryPoller(node_id="host_mac_m4", is_local=True)


class TelemetryConnectionManager:
    """
    Manages active WebSocket client connections and delivers dynamic telemetry broadcast frames.
    Handles dead client pruning and clean disconnects.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"⚡ WebSocket client connected. Total active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"🔌 WebSocket client disconnected. Total active clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: dict):
        """Asynchronously broadcasts a JSON frame to all active connected clients."""
        if not self.active_connections:
            return
            
        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Error broadcasting to WebSocket client: {e}")
                dead_connections.add(connection)
                
        for dead in dead_connections:
            self.disconnect(dead)


manager = TelemetryConnectionManager()
_broadcast_task: Optional[asyncio.Task] = None


async def telemetry_broadcast_loop():
    """
    Continuous 1 Hz async background telemetry broadcast loop.
    Calls blocking host OS pollers in a background threadpool using asyncio.to_thread.
    """
    logger.info("🚀 Starting 1 Hz dynamic telemetry broadcast loop...")
    while True:
        try:
            if manager.active_connections:
                # Capture authentic, fluctuating hardware snapshot in worker thread
                snapshot = await asyncio.to_thread(poller.poll_full_host_snapshot)
                
                # Deliver formatted telemetry frame
                payload = {
                    "type": "telemetry_frame",
                    "data": snapshot,
                    "timestamp": snapshot.get("timestamp"),
                    "node_id": snapshot.get("node_id", "host_mac_m4"),
                    "cpu_usage_pct": snapshot.get("cpu_usage_pct"),
                    "ram_usage_pct": snapshot.get("ram_usage_pct"),
                    "thermal_celsius": snapshot.get("thermal_celsius"),
                    "gpu_usage_pct": snapshot.get("gpu_usage_pct"),
                    "status": snapshot.get("status", "healthy")
                }
                await manager.broadcast_json(payload)
        except asyncio.CancelledError:
            logger.info("Telemetry broadcast loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in telemetry broadcast loop: {e}", exc_info=True)
            
        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _broadcast_task
    _broadcast_task = asyncio.create_task(telemetry_broadcast_loop())
    yield
    # Shutdown
    if _broadcast_task:
        _broadcast_task.cancel()
        try:
            await _broadcast_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Lauburu Compute Hub & Telemetry Pipeline",
    version="2.0.0",
    description="Real-Time 1Hz Dynamic Telemetry Streaming & Movesense BLE Tether Hub",
    lifespan=lifespan
)

# Enable CORS for localhost dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/telemetry")
@app.websocket("/ws/live_telemetry")
@app.websocket("/ws/ingest")
async def websocket_telemetry_stream(websocket: WebSocket):
    """
    Primary WebSocket streaming endpoint for LiveDeviceSentinelHUD and dashboard clients.
    Broadcasts authentic 1 Hz metric frames.
    """
    await manager.connect(websocket)
    try:
        # Immediately send initial snapshot upon connection
        initial_snapshot = await asyncio.to_thread(poller.poll_full_host_snapshot)
        await websocket.send_json({
            "type": "telemetry_frame",
            "data": initial_snapshot,
            **initial_snapshot
        })

        while True:
            # Keepalive listener: wait for client ping / commands
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if msg == "ping":
                    await websocket.send_text("pong")
                elif msg == "poll":
                    snap = await asyncio.to_thread(poller.poll_full_host_snapshot)
                    await websocket.send_json({"type": "telemetry_frame", "data": snap, **snap})
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket client session error: {e}")
        manager.disconnect(websocket)


@app.get("/api/node/telemetry")
@app.get("/api/telemetry")
async def get_node_telemetry_rest():
    """
    REST fallback endpoint for remote Tailscale RPC mesh polling and HTTP clients.
    Strict Rule #0: returns genuine real-time hardware telemetry snapshot.
    """
    snapshot = await asyncio.to_thread(poller.poll_full_host_snapshot)
    return snapshot


@app.get("/api/telemetry/node/{node_id}")
async def get_specific_node_telemetry(
    node_id: str,
    tailscale_ip: Optional[str] = None,
    online: bool = True
):
    """
    Context-aware node telemetry query.
    If local host: returns live host metrics.
    If remote: polls remote node over Tailscale RPC or returns strict nulls if offline.
    """
    if node_id in ["host_mac_m4", "layer1_host_mac", "local", "localhost"]:
        return await asyncio.to_thread(poller.poll_full_host_snapshot)
        
    if not online or not tailscale_ip:
        remote_poller = HostTelemetryPoller(node_id=node_id, is_local=False)
        return remote_poller.capture_remote_snapshot(is_reachable=False)

    remote_poller = HostTelemetryPoller(node_id=node_id, is_local=False)
    return await asyncio.to_thread(remote_poller.poll_remote_node, node_id, tailscale_ip)


def main():
    """Server entrypoint on Port 8000."""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=False)


if __name__ == "__main__":
    main()
