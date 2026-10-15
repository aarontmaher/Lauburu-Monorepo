#!/usr/bin/env python3
"""
Lauburu Sovereign Mesh: Port 4000 Biometrics Hub
Receives payloads from the Pixel 10 (Edge) and broadcasts to WebSockets for:
- Spatial Grappling 3D
- Zone 2 Endurance Tracker
- Readiness Dashboard
"""
import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, Request
import uvicorn

app = FastAPI(title="Lauburu Port 4000 Hub")
clients = set()
LIVE_FILE = "movesense_readiness_live.json"

@app.post("/api/movesense/ingest")
async def ingest_movesense(request: Request):
    payload = await request.json()
    
    # 1. Update the flat JSON file for the Python TUI Dashboard
    with open(LIVE_FILE, "w") as f:
        json.dump(payload, f)
        
    # 2. Broadcast via WebSockets to React Apps (Spatial Grappling & Zone 2)
    dead_clients = set()
    for client in clients:
        try:
            await client.send_json(payload)
        except Exception:
            dead_clients.add(client)
            
    for dc in dead_clients:
        clients.remove(dc)
        
    return {"status": "success", "broadcasted_to": len(clients)}

@app.websocket("/ws/movesense")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text() # Keepalive
    except:
        clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)
