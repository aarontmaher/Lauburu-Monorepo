import pytest
import json
import os
import sys

# Ensure module path is set
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

os.environ["DISABLE_AUTO_GAME_LOOP"] = "1"

import api_server

@pytest.fixture
def client():
    api_server.app.config['TESTING'] = True
    with api_server.app.test_client() as client:
        yield client

def test_root_health(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ONLINE"
    assert data["port"] == 5001

def test_telemetry_logs_endpoint(client):
    api_server.log_telemetry("TEST_EVENT", {"foo": "bar"}, level="INFO")
    response = client.get('/api/telemetry/logs')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "SUCCESS"
    assert "logs" in data
    assert "summary" in data
    assert any(log["event"] == "TEST_EVENT" for log in data["logs"])

def test_latency_benchmarks_endpoint(client):
    response = client.get('/api/benchmarks/latency')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "COMPLETED"
    assert "benchmarks" in data
    assert "average_latency_us" in data

    post_resp = client.post('/api/benchmarks/latency')
    assert post_resp.status_code == 200
    post_data = post_resp.get_json()
    assert post_data["status"] == "COMPLETED"

def test_x_response_time_header(client):
    response = client.get('/')
    assert response.status_code == 200
    assert "X-Response-Time-Us" in response.headers

def test_push_biometrics(client):
    payload = {"heart_rate_bpm": 72, "rr_ms": 850}
    response = client.post('/api/telemetry/push_biometrics', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "SUCCESS"
    assert data["heart_rate_bpm"] == 72

def test_push_biometrics_missing_payload(client):
    response = client.post('/api/telemetry/push_biometrics', data="", content_type='application/json')
    assert response.status_code == 400

def test_handle_sampling_profile(client):
    get_resp = client.get('/api/sensor/sampling_profile')
    assert get_resp.status_code == 200

    post_resp = client.post('/api/sensor/sampling_profile', data=json.dumps({"profile": "zone2"}), content_type='application/json')
    assert post_resp.status_code == 200
    data = post_resp.get_json()
    assert data["status"] == "SUCCESS"
    assert data["config"]["profile"] == "zone2"

def test_sensor_ingest_and_status(client):
    ingest_payload = {
        "sensor_type": "movesense",
        "device_name": "Movesense HR+",
        "heart_rate": 68,
        "rmssd": 45.2
    }
    ingest_resp = client.post('/api/sensors/ingest', data=json.dumps(ingest_payload), content_type='application/json')
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.get_json()
    assert ingest_data["status"] == "INGESTED"

    status_resp = client.get('/api/sensors/status')
    assert status_resp.status_code == 200
    status_data = status_resp.get_json()
    assert status_data["sensors"]["movesense"]["connected"] is True
    assert status_data["sensors"]["movesense"]["heart_rate"] == 68

def test_sandboxed_command_execution(client):
    payload = {"command": "echo 'Hello Sandbox'"}
    response = client.post('/api/terminal/sandbox/run', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "Hello Sandbox" in data["stdout"]

def test_sandboxed_destructive_command_blocked(client):
    payload = {"command": "rm -rf /"}
    response = client.post('/api/terminal/sandbox/run', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False

def test_pyspark_spark_metrics(client):
    response = client.get('/api/spark-metrics')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "LIVE_SYNCHRONIZED"
    assert "mesh_topology" in data
    assert "storage_pools" in data
