import uvicorn
from fastapi import FastAPI
import subprocess
import os

app = FastAPI(title="S20 Hermes Nexus", version="1.0")

@app.get("/health")
def health():
    return {"status": "ok", "device": "Samsung S20 Hermes Control Center"}

@app.post("/action")
def run_action(payload: dict):
    # Pass to hermes_code_action_dispatcher
    return {"status": "dispatched", "payload": payload}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
