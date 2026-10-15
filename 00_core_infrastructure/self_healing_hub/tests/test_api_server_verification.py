import pytest
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

os.environ["DISABLE_AUTO_GAME_LOOP"] = "1"

import api_server

@pytest.fixture
def client():
    api_server.app.config['TESTING'] = True
    with api_server.app.test_client() as client:
        yield client

def test_dynamic_helpers_and_builders():
    assert api_server._dyn(True) is True
    assert api_server._dyn(False) is False
    assert api_server._dyn(10) == 10.0
    assert isinstance(api_server._dyn(10), float)
    assert api_server._dyn("hello") == "hello"

    pool = api_server._build_pool_item("vault", "/data", 500, 100, 400, 80.0, "HEALTHY")
    assert pool["name"] == "vault"
    assert isinstance(pool["total_gb"], float)

    node = api_server._build_node_item(1, "MacMini", "Host", "127.0.0.1", "M4 Pro", "24GB", "AC", "ONLINE", True, 0.1)
    assert node["layer"] == 1
    assert node["rpc_server"]["online"] is True
    assert node["rpc_server"]["latency_ms"] == 0.1

    transport = api_server._build_transport_item("tb4", "TB4 Bridge", "40 Gbps", 0.28, "ONLINE", "LLM Weights")
    assert transport["id"] == "tb4"
    assert transport["latency_ms"] == 0.28

def test_structured_telemetry_logging():
    initial_summary = api_server.get_telemetry_summary()
    initial_count = initial_summary["total_logs"]

    entry = api_server.log_telemetry("UNIT_TEST_EVENT", {"detail": 123}, level="WARNING")
    assert entry["event"] == "UNIT_TEST_EVENT"
    assert entry["level"] == "WARNING"

    logs = api_server.get_telemetry_logs(limit=10, level="WARNING")
    assert len(logs) >= 1
    assert any(l["event"] == "UNIT_TEST_EVENT" for l in logs)

    summary = api_server.get_telemetry_summary()
    assert summary["total_logs"] == initial_count + 1
    assert summary["level_counts"].get("WARNING", 0) >= 1

def test_run_microsecond_latency_benchmarks():
    benchmarks = api_server.run_microsecond_latency_benchmarks()
    assert benchmarks["status"] == "COMPLETED"
    assert "telemetry_logging_us" in benchmarks["benchmarks"]
    assert "telemetry_retrieval_us" in benchmarks["benchmarks"]
    assert "json_serialization_us" in benchmarks["benchmarks"]
    assert "device_registry_lookup_us" in benchmarks["benchmarks"]
    assert benchmarks["average_latency_us"] > 0
    assert benchmarks["throughput_ops_sec"] > 0

    cached = api_server.get_latency_benchmarks()
    assert cached == benchmarks

def test_flask_request_hooks_and_header(client):
    res = client.get('/api/telemetry/logs')
    assert res.status_code == 200
    assert "X-Response-Time-Us" in res.headers
    time_us = float(res.headers["X-Response-Time-Us"])
    assert time_us >= 0.0

def test_error_boundary_handling(client):
    res = client.get('/non_existent_route_404')
    assert res.status_code == 404
    data = res.get_json()
    assert "error" in data or "status_code" in data
