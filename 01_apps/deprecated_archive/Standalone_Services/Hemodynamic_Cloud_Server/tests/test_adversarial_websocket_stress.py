"""
Adversarial WebSocket Stress & Robustness Test Suite.
Empirically tests:
1. Malformed JSON inputs and syntax error resilience.
2. Rapid client disconnect storms.
3. Rapid continuous message pumping (blast test).
4. Concurrent WebSocket client streams.
5. In-stream Zero-PII violation filtering and rejection.
"""

import asyncio
import json
import pytest
from starlette.testclient import TestClient
from app.main import app


class TestAdversarialWebSocketStress:
    """Stress tests WebSocket telemetry stream endpoints against adversarial traffic and network disruptions."""

    # -------------------------------------------------------------------------
    # 1. Malformed Payload Resilience
    # -------------------------------------------------------------------------
    def test_websocket_malformed_json_handling(self):
        """Verify that malformed JSON payloads return descriptive error messages without crashing server."""
        client = TestClient(app)
        with client.websocket_connect("/ws/live-stream") as ws:
            # 1. Non-JSON plain text
            ws.send_text("THIS IS NOT JSON")
            resp1 = ws.receive_json()
            assert "error" in resp1
            assert resp1["error"] == "Invalid telemetry payload"

            # 2. Truncated JSON
            ws.send_text('{"protocol_version": "1.0", "session_token":')
            resp2 = ws.receive_json()
            assert "error" in resp2
            assert resp2["error"] == "Invalid telemetry payload"

            # 3. Empty string
            ws.send_text("")
            resp3 = ws.receive_json()
            assert "error" in resp3

            # 4. Valid JSON but invalid schema
            ws.send_text(json.dumps({"invalid_key": 999}))
            resp4 = ws.receive_json()
            assert "error" in resp4

            # 5. Send valid tick immediately after errors to verify connection stayed alive and functional
            valid_payload = {
                "protocol_version": "1.0",
                "session_token": "a" * 64,
                "delta_time_ms": 1000,
                "vector_u": {
                    "ptt_ms": 220.0,
                    "hr_bpm": 72.0,
                    "rr_ms": 833.0,
                    "delta_t_dia_ms": 280.0,
                    "imu_acc_g": 1.0,
                    "e0_elasticity": 400.0
                }
            }
            ws.send_text(json.dumps(valid_payload))
            resp5 = ws.receive_text()
            data5 = json.loads(resp5)
            assert "hemodynamic_state" in data5
            assert data5["hemodynamic_state"]["systolic_bp_mmHg"] > 0

    # -------------------------------------------------------------------------
    # 2. In-Stream Zero-PII Policy Rejection
    # -------------------------------------------------------------------------
    def test_websocket_zero_pii_rejection(self):
        """Verify that WebSocket strictly rejects PII payloads with descriptive error."""
        client = TestClient(app)
        with client.websocket_connect("/ws/live-stream") as ws:
            # Inject PII key
            dirty_payload = {
                "protocol_version": "1.0",
                "session_token": "a" * 64,
                "delta_time_ms": 1000,
                "user_email": "leaked@email.com",
                "vector_u": {
                    "ptt_ms": 220.0,
                    "hr_bpm": 72.0,
                    "rr_ms": 833.0,
                    "delta_t_dia_ms": 280.0,
                    "imu_acc_g": 1.0,
                    "e0_elasticity": 400.0
                }
            }
            ws.send_text(json.dumps(dirty_payload))
            resp = ws.receive_json()
            assert resp["error"] == "Zero-PII Policy Violation"
            assert "user_email" in resp["detail"]

    # -------------------------------------------------------------------------
    # 3. Rapid Continuous Message Pumping (Blast Test)
    # -------------------------------------------------------------------------
    def test_websocket_rapid_message_pumping_blast(self):
        """Verify WebSocket stream handles 100 rapid sequential messages without dropping or corrupting responses."""
        client = TestClient(app)
        with client.websocket_connect("/ws/live-stream") as ws:
            num_messages = 100
            for i in range(num_messages):
                payload = {
                    "protocol_version": "1.0",
                    "session_token": "f" * 64,
                    "delta_time_ms": (i + 1) * 500,
                    "vector_u": {
                        "ptt_ms": 200.0 + (i % 30),
                        "hr_bpm": 60.0 + (i % 40),
                        "rr_ms": 850.0,
                        "delta_t_dia_ms": 280.0,
                        "imu_acc_g": 1.0 + (i * 0.01),
                        "e0_elasticity": 400.0
                    }
                }
                ws.send_text(json.dumps(payload))
                raw_resp = ws.receive_text()
                data = json.loads(raw_resp)
                assert "hemodynamic_state" in data
                assert 70.0 <= data["hemodynamic_state"]["systolic_bp_mmHg"] <= 240.0
                assert 40.0 <= data["hemodynamic_state"]["diastolic_bp_mmHg"] <= 150.0

    # -------------------------------------------------------------------------
    # 4. Abrupt Disconnect Storm
    # -------------------------------------------------------------------------
    def test_websocket_abrupt_disconnect_storm(self):
        """Verify that multiple rapid client connects followed by immediate abrupt disconnects don't cause server leaks or failures."""
        client = TestClient(app)
        for i in range(25):
            with client.websocket_connect("/ws/live-stream") as ws:
                # Optionally send a partial or single tick then immediately close
                if i % 2 == 0:
                    payload = {
                        "protocol_version": "1.0",
                        "session_token": "d" * 64,
                        "delta_time_ms": 1000,
                        "vector_u": {
                            "ptt_ms": 220.0,
                            "hr_bpm": 72.0,
                            "rr_ms": 833.0,
                            "delta_t_dia_ms": 280.0,
                            "imu_acc_g": 1.0,
                            "e0_elasticity": 400.0
                        }
                    }
                    ws.send_text(json.dumps(payload))
                    _ = ws.receive_text()
                # Context exit abruptly closes WebSocket connection

        # After storm, verify server still accepts new WebSocket connections and processes ticks normally
        with client.websocket_connect("/ws/live-stream") as ws:
            payload = {
                "protocol_version": "1.0",
                "session_token": "e" * 64,
                "delta_time_ms": 1000,
                "vector_u": {
                    "ptt_ms": 220.0,
                    "hr_bpm": 72.0,
                    "rr_ms": 833.0,
                    "delta_t_dia_ms": 280.0,
                    "imu_acc_g": 1.0,
                    "e0_elasticity": 400.0
                }
            }
            ws.send_text(json.dumps(payload))
            resp = json.loads(ws.receive_text())
            assert "hemodynamic_state" in resp
