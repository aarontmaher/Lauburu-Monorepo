"""
API Endpoints & Integration Test Suite.
Tests all REST endpoints, WebSocket streaming, and Genetic MoE router.
"""

import json
import pytest
from app.core.security import generate_session_token


class TestApiEndpoints:
    def test_health_endpoints(self, client):
        res1 = client.get("/health")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "healthy"
        assert data1["physics_engine_ready"] is True

        res2 = client.get("/api/v1/health")
        assert res2.status_code == 200
        assert res2.json()["status"] == "healthy"

    def test_session_init(self, client):
        res = client.post("/api/v1/session/init", json={"client_nonce": "test_nonce_123"})
        assert res.status_code == 201
        data = res.json()
        assert "session_token" in data
        assert len(data["session_token"]) == 64
        assert data["status"] == "initialized"

    def test_hemodynamic_inversion_with_vector_u(self, client, sample_session_token, sample_valid_vector_u):
        payload = {
            "protocol_version": "1.0.0",
            "session_token": sample_session_token,
            "delta_time_ms": 15000,
            "vector_u": sample_valid_vector_u
        }
        res = client.post("/api/v1/hemodynamics/invert", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["protocol_version"] == "1.0.0"
        assert data["session_token"] == sample_session_token
        
        state = data["hemodynamic_state"]
        assert 70.0 <= state["systolic_bp_mmHg"] <= 240.0
        assert 40.0 <= state["diastolic_bp_mmHg"] <= 150.0
        assert state["systolic_bp_mmHg"] >= state["diastolic_bp_mmHg"] + 15.0
        assert state["pulse_pressure_mmHg"] == state["systolic_bp_mmHg"] - state["diastolic_bp_mmHg"]
        assert state["arterial_compliance"] > 0.0
        assert state["vascular_resistance"] > 0.0
        assert state["pwv_m_s"] > 0.0
        assert 0.0 <= state["confidence_score"] <= 1.0

        insights = data["trend_hunting_insights"]
        assert "endothelial_reserve_status" in insights
        assert "zone2_compliance" in insights

    def test_hemodynamic_inversion_with_telemetry_vector(self, client, sample_session_token, sample_valid_telemetry_vector):
        payload = {
            "protocol_version": "1.0.0",
            "session_token": sample_session_token,
            "delta_time_ms": 30000,
            "telemetry_vector": sample_valid_telemetry_vector
        }
        res = client.post("/api/v1/hemodynamics/invert", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["session_token"] == sample_session_token
        assert data["hemodynamic_state"]["systolic_bp_mmHg"] > 70.0

    def test_batch_inversion(self, client, sample_session_token, sample_valid_vector_u):
        ticks = [
            {"delta_time_ms": 1000, "vector_u": sample_valid_vector_u},
            {"delta_time_ms": 2000, "vector_u": sample_valid_vector_u},
            {"delta_time_ms": 3000, "vector_u": sample_valid_vector_u}
        ]
        payload = {
            "protocol_version": "1.0.0",
            "session_token": sample_session_token,
            "ticks": ticks
        }
        res = client.post("/api/v1/hemodynamics/batch", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_processed"] == 3
        assert len(data["results"]) == 3

    def test_session_summary_lifecycle(self, client, sample_session_token, sample_valid_vector_u):
        # 1. Post a tick to populate session
        payload = {
            "session_token": sample_session_token,
            "delta_time_ms": 10000,
            "vector_u": sample_valid_vector_u
        }
        client.post("/api/v1/hemodynamics/invert", json=payload)

        # 2. Get summary
        res = client.get(f"/api/v1/session/{sample_session_token}/summary")
        assert res.status_code == 200
        summary = res.json()
        assert summary["session_hash"] == sample_session_token
        assert summary["total_ticks"] >= 1
        assert summary["mean_sbp"] > 0.0
        assert summary["mean_dbp"] > 0.0

    def test_rag_query_routing(self, client, sample_session_token):
        # Test DeepSeek reasoning classification
        payload1 = {
            "session_token": sample_session_token,
            "query": "Show me the mathematical proof of arterial stiffness drift and vascular fatigue during Zone 2",
            "top_k": 3
        }
        res1 = client.post("/api/v1/rag/query", json=payload1)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["selected_expert_model"] == "DeepSeek-R1-Distill-Qwen-32B"

        # Test Multi-modal ECG classification
        payload2 = {
            "session_token": sample_session_token,
            "query": "Inspect my ECG waveform and dicrotic notch morphology plot",
            "top_k": 3
        }
        res2 = client.post("/api/v1/rag/query", json=payload2)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["selected_expert_model"] == "Qwen3-VL-32B"

        # Test Structured summary classification
        payload3 = {
            "session_token": sample_session_token,
            "query": "Provide a tabular summary of total workout stats and average duration",
            "top_k": 3
        }
        res3 = client.post("/api/v1/rag/query", json=payload3)
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["selected_expert_model"] == "Qwen2.5-Coder-14B"

    def test_websocket_telemetry_stream(self, client, sample_session_token, sample_valid_vector_u):
        with client.websocket_connect("/ws/live-stream") as ws:
            req_data = {
                "session_token": sample_session_token,
                "delta_time_ms": 1000,
                "vector_u": sample_valid_vector_u
            }
            ws.send_text(json.dumps(req_data))
            resp_text = ws.receive_text()
            resp_data = json.loads(resp_text)
            assert resp_data["session_token"] == sample_session_token
            assert "hemodynamic_state" in resp_data
            assert resp_data["hemodynamic_state"]["systolic_bp_mmHg"] > 70.0
