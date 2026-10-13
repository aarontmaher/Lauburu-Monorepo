import os
import sys
import pytest
import json

# Ensure self_healing_hub/src is on sys.path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import api_server

def test_telemetry_logging():
    """Verify structured telemetry logging helpers."""
    log_entry = api_server.log_telemetry("UNIT_TEST_EVENT", {"detail_key": "detail_val"}, level="INFO")
    assert log_entry["event_type"] == "UNIT_TEST_EVENT"
    assert log_entry["level"] == "INFO"
    assert log_entry["details"]["detail_key"] == "detail_val"

    logs = api_server.get_telemetry_logs(limit=10)
    assert len(logs) > 0
    assert any(l.get("event_type") == "UNIT_TEST_EVENT" for l in logs)

    summary = api_server.get_telemetry_summary()
    assert "total_logs" in summary
    assert "level_counts" in summary
    assert summary["total_logs"] > 0

def test_microsecond_latency_benchmarks():
    """Verify microsecond latency benchmarks execution."""
    benchmarks = api_server.run_microsecond_latency_benchmarks()
    assert benchmarks["status"] == "COMPLETED"
    assert "benchmarks_us" in benchmarks
    assert "telemetry_logging_us" in benchmarks["benchmarks_us"]
    assert "device_registry_lookup_us" in benchmarks["benchmarks_us"]
    assert "json_serialization_us" in benchmarks["benchmarks_us"]

    cached = api_server.get_latency_benchmarks()
    assert cached["status"] == "COMPLETED"

def test_api_server_flask_endpoints():
    """Verify Flask API endpoints and response time headers."""
    client = api_server.app.test_client()

    # Test /api/benchmarks/latency
    res_bench = client.get("/api/benchmarks/latency")
    assert res_bench.status_code == 200
    assert "X-Response-Time-Us" in res_bench.headers
    data_bench = res_bench.get_json()
    assert data_bench["status"] == "COMPLETED"

    # Test /api/telemetry/logs
    res_telemetry = client.get("/api/telemetry/logs?limit=5")
    assert res_telemetry.status_code == 200
    assert "X-Response-Time-Us" in res_telemetry.headers
    data_telemetry = res_telemetry.get_json()
    assert data_telemetry["status"] == "SUCCESS"
    assert "logs" in data_telemetry
    assert "summary" in data_telemetry

def test_push_biometrics_endpoint():
    """Verify /api/telemetry/push_biometrics endpoint."""
    client = api_server.app.test_client()
    res = client.post("/api/telemetry/push_biometrics", json={"heart_rate_bpm": 72, "spo2": 98})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "SUCCESS"
    assert data["heart_rate_bpm"] == 72
