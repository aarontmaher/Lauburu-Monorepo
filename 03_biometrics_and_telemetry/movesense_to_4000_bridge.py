import sys
import os
import asyncio
import logging
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../01_apps/edge_compute_and_ai/lauburu_compute_hub/services")))

from movesense_ingestion import get_movesense_daemon

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("movesense_bridge")

daemon = get_movesense_daemon()

async def post_telemetry(payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://127.0.0.1:4000/api/v1/network/ingest", json=payload, timeout=2.0)
        except Exception as e:
            pass

def on_telemetry(state: dict):
    if not state.get("is_streaming"):
        return
    metrics = state.get("metrics", {})
    
    rr_ms = metrics.get("rr_interval_ms")
    rr_intervals = [rr_ms] if rr_ms is not None else []
    
    payload = {
        "sensor_type": "movesense",
        "heart_rate": metrics.get("heart_rate_bpm"),
        "rr_intervals_ms": rr_intervals,
        "ecg_mv": metrics.get("ecg_samples_mv", []),
        "acc_g": {"x": 0.0, "y": 0.0, "z": 1.0}, # Provide a dummy g-force if not in metrics
        "ptt_ms": metrics.get("ptt_ms")
    }
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(post_telemetry(payload))
    except Exception as e:
        logger.error(f"Error scheduling telemetry post: {e}")

async def run_bridge():
    daemon.subscribers.append(on_telemetry)
    logger.info("Auto-scanning and connecting to Movesense via daemon...")
    await daemon.connect(auto_scan=True)
    
    logger.info("Movesense Bridge started. Pushing telemetry to http://127.0.0.1:4000/api/v1/network/ingest")
    
    # Keep the task alive indefinitely
    while True:
        await asyncio.sleep(5.0)
        # Periodically ensure connection
        if not daemon.is_streaming:
            logger.info("Movesense disconnected. Attempting reconnect...")
            await daemon.connect(auto_scan=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_bridge())
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")
