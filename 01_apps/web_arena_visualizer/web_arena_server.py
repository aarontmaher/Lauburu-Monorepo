#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Web Arena TUI & Canvas Visualizer Server (Port 4005)
================================================================================
Subsystem: 01_apps/web_arena_visualizer/web_arena_server.py
Version: 1.0.0-WEB-ARENA-VISUALIZER-CANONICAL
Lauburu Mesh Ecosystem — 2026
================================================================================
"""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

MONOREPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = MONOREPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
sys.path.insert(0, str(BENCHMARK_DIR))

try:
    from arena_telemetry_streamer import app as streamer_app
except ImportError:
    from .arena_telemetry_streamer import app as streamer_app

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = streamer_app
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    print("🌐 Launching Web Arena Visualizer on http://0.0.0.0:4005")
    uvicorn.run(app, host="0.0.0.0", port=4005)
