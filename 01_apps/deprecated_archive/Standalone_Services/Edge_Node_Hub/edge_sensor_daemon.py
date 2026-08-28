import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] edge_hub: %(message)s"
)
logger = logging.getLogger("edge_hub")

# Hub Configuration
HUB_PORT = int(os.environ.get("HUB_PORT", "8086"))
LOCAL_AI_GATEWAY_URL = os.environ.get("LOCAL_AI_GATEWAY_URL", "http://127.0.0.1:8181")
ENABLE_BLE_SCAN = os.environ.get("ENABLE_BLE_SCAN", "true").lower() == "true"

connected_clients: set[WebSocketServerProtocol] = set()

# In-Memory Rolling Telemetry Cache (15-second window for Local AI reasoning)
rolling_telemetry_window: List[Dict[str, Any]] = []
max_window_seconds = 15


async def register_client(websocket: WebSocketServerProtocol):
    connected_clients.add(websocket)
    logger.info("📱 Client app connected to Edge Hub (Total: %d)", len(connected_clients))
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        logger.info("Client app disconnected (Remaining: %d)", len(connected_clients))


async def broadcast_telemetry(frame: Dict[str, Any]):
    """Broadcasts live sensor frame to all connected local sub-apps."""
    global rolling_telemetry_window
    now = time.time()
    frame["timestamp_epoch"] = now

    # Maintain 15-second rolling window for AI trend evaluation
    rolling_telemetry_window.append(frame)
    rolling_telemetry_window = [
        f for f in rolling_telemetry_window if now - f.get("timestamp_epoch", now) <= max_window_seconds
    ]

    if not connected_clients:
        return

    payload = json.dumps(frame)
    websockets_to_remove = set()
    for ws in connected_clients:
        try:
            await ws.send(payload)
        except Exception:
            websockets_to_remove.add(ws)

    for dead_ws in websockets_to_remove:
        connected_clients.discard(dead_ws)


async def movesense_ble_listener():
    """Lightweight BLE Scanner & Movesense Telemetry Decoder."""
    logger.info("Initializing Movesense BLE Interface...")
    try:
        import bleak
        from bleak import BleakScanner, BleakClient

        MOVESENSE_SERVICE_UUID = "34802252-7185-4d5d-b431-b30e393d9e05"
        
        logger.info("Scanning for Movesense Sensors with Service UUID: %s", MOVESENSE_SERVICE_UUID)
        devices = await BleakScanner.discover(timeout=5.0)
        movesense_devices = [d for d in devices if d.name and ("Movesense" in d.name or "Movesense" in str(d.details))]

        if not movesense_devices:
            logger.info("No physical Movesense sensor detected in range. Edge Hub will broadcast live state '--'.")
            return

        target_device = movesense_devices[0]
        logger.info("Connecting to Movesense Sensor: %s (%s)", target_device.name, target_device.address)

        async with BleakClient(target_device.address) as client:
            logger.info("Connected to Movesense. Subscribing to 9-DoF IMU and ECG streams...")
            
            def notification_handler(sender, data: bytearray):
                # Binary decoder for Movesense 2.0 frames
                frame = {
                    "sensor_id": target_device.name,
                    "address": target_device.address,
                    "connected": True,
                    "raw_bytes_len": len(data),
                    "acc_x": float(int.from_bytes(data[0:2], byteorder="little", signed=True)) / 100.0 if len(data) >= 6 else 0.0,
                    "acc_y": float(int.from_bytes(data[2:4], byteorder="little", signed=True)) / 100.0 if len(data) >= 6 else 0.0,
                    "acc_z": float(int.from_bytes(data[4:6], byteorder="little", signed=True)) / 100.0 if len(data) >= 6 else 9.81,
                    "heart_rate": int(data[6]) if len(data) > 6 else None,
                }
                asyncio.create_task(broadcast_telemetry(frame))

            # Subscribe to Movesense notifications
            await client.start_notify(MOVESENSE_SERVICE_UUID, notification_handler)
            while client.is_connected:
                await asyncio.sleep(1)

    except ImportError:
        logger.warning("Bleak BLE library not installed in this environment. Running in IPC broadcast mode.")
    except Exception as e:
        logger.warning("BLE listener encounter: %s. Edge Hub remains active for local IPC/sub-apps.", str(e))


async def main():
    logger.info("🚀 Starting Lauburu Lightweight Edge Hub on Port :%d...", HUB_PORT)
    server = await websockets.serve(register_client, "0.0.0.0", HUB_PORT)
    logger.info("✅ Edge Hub WebSocket Server listening on ws://0.0.0.0:%d/telemetry", HUB_PORT)

    if ENABLE_BLE_SCAN:
        asyncio.create_task(movesense_ble_listener())

    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
