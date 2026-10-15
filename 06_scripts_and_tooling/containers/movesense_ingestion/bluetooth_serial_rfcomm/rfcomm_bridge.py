#!/usr/bin/env python3
"""
Movesense Bluetooth Serial / RFCOMM Ingestion Bridge
Binds to Linux BlueZ RFCOMM channel or serial port and provides an interactive
WebSocket terminal and web browser interface.
"""

import os
import sys
import glob
import json
import asyncio
from aiohttp import web

PORT = int(os.environ.get("PORT", "8089"))
RFCOMM_DEV = os.environ.get("RFCOMM_DEV", "/dev/rfcomm0")
connected_clients = set()

routes = web.RouteTableDef()

@routes.get("/")
async def handle_index(request):
    html_path = os.path.join(os.path.dirname(__file__), "rfcomm_dashboard.html")
    return web.FileResponse(html_path)

@routes.get("/api/health")
async def handle_health(request):
    rfcomm_exists = os.path.exists(RFCOMM_DEV)
    available_devices = glob.glob("/dev/rfcomm*")
    return web.json_response({
        "status": "healthy",
        "service": "bluetooth_serial_rfcomm_bridge",
        "target_dev": RFCOMM_DEV,
        "device_present": rfcomm_exists,
        "available_rfcomm_devices": available_devices,
        "connected_web_clients": len(connected_clients)
    })

@routes.get("/ws/serial")
async def handle_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)
    print(f"[RFCOMM WS] Web client connected. Total clients: {len(connected_clients)}")

    try:
        # Welcome message
        await ws.send_json({
            "type": "system",
            "message": f"Connected to RFCOMM Serial Bridge. Target device: {RFCOMM_DEV}"
        })

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                action = data.get("action")
                if action == "command":
                    cmd = data.get("command", "")
                    print(f"[RFCOMM TX] Command received: {cmd}")
                    # If physical device exists, write to it
                    if os.path.exists(RFCOMM_DEV):
                        try:
                            with open(RFCOMM_DEV, "w") as dev:
                                dev.write(cmd + "\n")
                        except Exception as e:
                            await ws.send_json({"type": "error", "message": f"Write failed: {e}"})
                    else:
                        await ws.send_json({
                            "type": "system",
                            "message": f"[Dev Node {RFCOMM_DEV} not connected] Echo: {cmd}"
                        })
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[RFCOMM WS] Error: {ws.exception()}")
    finally:
        connected_clients.remove(ws)
        print(f"[RFCOMM WS] Web client disconnected. Total clients: {len(connected_clients)}")
    return ws

async def serial_reader_loop():
    """Background task reading physical RFCOMM device when available."""
    while True:
        if os.path.exists(RFCOMM_DEV):
            try:
                print(f"[RFCOMM] Opening {RFCOMM_DEV}...")
                with open(RFCOMM_DEV, "r", errors="replace") as f:
                    while True:
                        line = f.readline()
                        if not line:
                            break
                        line_str = line.strip()
                        if line_str and connected_clients:
                            payload = {
                                "type": "data",
                                "raw": line_str,
                                "timestamp": asyncio.get_event_loop().time()
                            }
                            msg = json.dumps(payload)
                            await asyncio.gather(
                                *[client.send_str(msg) for client in connected_clients],
                                return_exceptions=True
                            )
            except Exception as e:
                print(f"[RFCOMM] Read error on {RFCOMM_DEV}: {e}")
        await asyncio.sleep(2)

async def start_background_tasks(app):
    app["reader_task"] = asyncio.create_task(serial_reader_loop())

async def cleanup_background_tasks(app):
    app["reader_task"].cancel()
    await app["reader_task"]

def main():
    app = web.Application()
    app.add_routes(routes)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    print(f"Starting Bluetooth Serial / RFCOMM Bridge on http://0.0.0.0:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
