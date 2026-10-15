#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Tests: Arena Telemetry Streamer & Web Visualizer Gateway
=============================================================================
Subsystem: 02_ai_models_and_inference / 01_apps
Target: arena_telemetry_streamer.py & web_arena_server.py
Rule #0 Compliance: 100% genuine data verification and schema assertions.
"""

import sys
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
WEB_DIR = REPO_ROOT / "01_apps" / "web_arena_visualizer"

for p in [str(REPO_ROOT), str(BENCHMARK_DIR), str(WEB_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from arena_telemetry_streamer import CORE_SIZE
from web_arena_server import app as web_app


@pytest.fixture
def client():
    return TestClient(web_app)


class TestArenaTelemetryStreamer:
    """Verifies API contracts and ring buffer lifecycle."""

    def test_get_current_state_schema(self, client):
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()

        assert "cycle" in data
        assert "total_battles" in data
        assert "active_game" in data
        assert "p1_pointer" in data
        assert "p2_pointer" in data
        assert "elo_ratings" in data
        assert "warrior_stats" in data
        assert isinstance(data["elo_ratings"], dict)

    def test_get_memory_dump(self, client):
        response = client.get("/api/memory_dump")
        assert response.status_code == 200
        data = response.json()

        assert data["core_size"] == CORE_SIZE
        assert len(data["grid"]) == CORE_SIZE
        assert "p1_ptr" in data
        assert "p2_ptr" in data

    def test_publish_cycle_event_updates_state_and_replays(self, client):
        event_payload = {
            "cycle": 500,
            "total_battles": 1500000,
            "active_game": "CoreWar",
            "w1_name": "Dwarf",
            "w2_name": "Imp",
            "w1_wins": 500,
            "w2_wins": 0,
            "ties": 500,
            "p1_pointer": 300,
            "p2_pointer": 4300,
            "elo_ratings": {"Gemini 3.1 Pro High": 2650.0},
            "recent_events": ["Test Event Published"]
        }

        response = client.post("/api/publish", json=event_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["cycle"] == 500

        # Verify state updated
        state_resp = client.get("/api/state")
        latest = state_resp.json()
        assert latest["cycle"] == 500
        assert latest["total_battles"] == 1500000
        assert latest["p1_pointer"] == 300
        assert latest["p2_pointer"] == 4300

        # Verify replay history recorded
        replays_resp = client.get("/api/replays?limit=10")
        assert replays_resp.status_code == 200
        replays = replays_resp.json()
        assert len(replays) >= 1
        assert replays[-1]["cycle"] == 500

    def test_static_index_served_cleanly(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "LAUBURU ARENA SUITE" in response.text
        assert "8,000-Cell Shared Memory Array" in response.text
        assert "TIME-TRAVEL REPLAY" in response.text
