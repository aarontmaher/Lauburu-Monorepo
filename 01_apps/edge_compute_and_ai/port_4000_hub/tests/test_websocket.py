"""
WebSocket live streaming tests for Port 4000 Hub.
Tests bidirectional /ws/telemetry push_tick, ping/pong, and broadcast frame reception.
"""

import json
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from ..server import app
from ..storage.sqlite_manager import get_sqlite_manager


@pytest.fixture(autouse=True)
def override_sqlite_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = get_sqlite_manager(db_path=path)
    yield manager
    try:
        os.remove(path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(path + ext):
                os.remove(path + ext)
    except Exception:
        pass


@pytest.fixture
def client():
    return TestClient(app)


def test_websocket_ping_pong(client):
    """Test websocket connection and ping action."""
    with client.websocket_connect("/ws/telemetry") as ws:
        ws.send_text(json.dumps({"action": "ping"}))
        data = ws.receive_json()
        assert data.get("action") == "pong"
        assert "timestamp" in data


def test_websocket_push_tick_and_broadcast(client):
    """Test pushing a live tick over WebSocket and receiving broadcast."""
    # Create user first
    reg = client.post("/api/auth/register", json={
        "email": "ws_user@lauburu.ai",
        "password": "WsPassword123",
        "name": "WebSocket User"
    })
    session_token = reg.json()["session_token"]

    with client.websocket_connect("/ws/telemetry") as ws:
        tick_frame = {
            "action": "push_tick",
            "session_token": session_token,
            "tick": {
                "epoch_ms": 1787532000000,
                "sensor_type": "movesense",
                "hr_bpm": 138.0,
                "rr_ms": [435.0, 432.0],
                "ecg_sample": 1.18,
                "accel": {"x": 0.04, "y": 0.10, "z": 0.99}
            }
        }
        ws.send_text(json.dumps(tick_frame))
        broadcast = ws.receive_json()

        assert broadcast["type"] == "live_telemetry_broadcast"
        assert broadcast["session_token"] == session_token
        assert broadcast["sensor_type"] == "movesense"
        assert broadcast["biometrics"]["heart_rate_bpm"] == 138.0
        assert "Zone 2" in broadcast["biometrics"]["training_zone"]
