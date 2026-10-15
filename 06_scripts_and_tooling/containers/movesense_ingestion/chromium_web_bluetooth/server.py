#!/usr/bin/env python3
"""
Chromium Web Bluetooth Telemetry Bridge Server (:9223)
Serves the Multi-Device Web Bluetooth dashboard (Movesense + AssaultBike FTMS/CPS/CSC)
and forwards live BLE GATT frames directly to the Unified Sovereign Hub (:8084/api/ingest).
"""

import os
import json
import urllib.request
from aiohttp import web

PORT = int(os.environ.get("PORT", "9223"))
HUB_INGEST_URL = os.environ.get("HUB_INGEST_URL", "http://127.0.0.1:8084/api/ingest")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)
STREAM_FILE = os.path.join(DATA_DIR, "movesense_web_bluetooth_stream.jsonl")

routes = web.RouteTableDef()


def forward_to_hub(payload: dict) -> None:
    try:
        req = urllib.request.Request(
            HUB_INGEST_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=1.5) as _:
            pass
    except Exception as exc:
        print(f"[WebBLE Bridge] Forward to {HUB_INGEST_URL} warning: {exc}")


@routes.get("/")
async def handle_index(request):
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    return web.FileResponse(html_path)


@routes.get("/api/health")
async def handle_health(request):
    return web.json_response({
        "status": "healthy",
        "service": "chromium_web_bluetooth_multi_device_bridge",
        "port": PORT,
        "hub_ingest_url": HUB_INGEST_URL,
        "supported_devices": ["Movesense 261030002013", "AssaultBike FTMS/CPS/CSC", "Polar H10"],
    })


@routes.get("/ws/telemetry")
async def handle_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("[WebSocket] Multi-device WebBLE client connected.")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    with open(STREAM_FILE, "a") as f:
                        f.write(json.dumps(data) + "\n")
                    forward_to_hub(data)
                except Exception as e:
                    print(f"[WebSocket] Error processing packet: {e}")
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[WebSocket] Connection closed with error: {ws.exception()}")
    finally:
        print("[WebSocket] Client disconnected.")
    return ws


def main():
    app = web.Application()
    app.add_routes(routes)
    print(f"Starting Multi-Device Web Bluetooth Bridge on http://0.0.0.0:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
