import sys
import os
import asyncio
import logging
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../01_apps/edge_compute_and_ai/lauburu_compute_hub/services")))

from movesense_ingestion import get_movesense_daemon

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("movesense_api_daemon")

daemon = get_movesense_daemon()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try connecting to physical device on startup without blocking
    asyncio.create_task(daemon.connect(auto_scan=True))
    yield
    await daemon.disconnect()

app = FastAPI(lifespan=lifespan)

@app.get("/api/sensors/status")
def get_sensors_status():
    state = daemon.get_state()
    ms_connected = state.get("is_streaming", False)
    metrics = state.get("metrics", {})
    
    return {
        "connected_count": 1 if ms_connected else 0,
        "sensors": {
            "movesense": {
                "connected": ms_connected,
                "heart_rate": metrics.get("heart_rate_bpm"),
                "rmssd": metrics.get("rmssd_ms"),
                "dfa_alpha1": metrics.get("dfa_alpha1")
            }
        },
        "raw_state": state
    }

@app.post("/api/sensors/connect")
async def connect_sensor():
    result = await daemon.connect(auto_scan=True)
    return result

@app.post("/api/sensors/disconnect")
async def disconnect_sensor():
    result = await daemon.disconnect()
    return result

if __name__ == "__main__":
    logger.info("Starting Movesense API Daemon on Port 4000...")
    uvicorn.run("movesense_api_daemon:app", host="0.0.0.0", port=4000, reload=False)
