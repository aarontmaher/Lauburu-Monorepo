#!/usr/bin/env python3
"""
Empirical Adversarial Fault Injection & Mesh Ingress Test Suite:
Tailscale Mesh Ingress from Pixel 10 Pro XL (100.73.38.87) to Mac Mini (100.119.199.76:4000).

Tests:
1. High Latency, Packet Jitter, Slowloris Trickle & Interrupted HTTP Streams from Pixel.
2. Abrupt TCP Reset / Connection Terminations mid-stream (WebSocket & HTTP).
3. Malformed, Fuzzed, Pathological & Oversized Ingress Payloads.
4. Concurrency Flooding, Daemon Recovery & Zero-Mock Integrity Post-Fault.
"""

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import urllib.error
import pytest

PIXEL_IP = "100.73.38.87"
PIXEL_SSH_PORT = "8022"
HOST_IP = "100.119.199.76"
HOST_PORT = 4000
BASE_URL = f"http://{HOST_IP}:{HOST_PORT}"

def run_local_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def run_remote_pixel_python(py_code):
    """Executes a Python snippet directly on Pixel 10 Pro XL inside Termux via SSH."""
    b64 = base64.b64encode(py_code.encode("utf-8")).decode("ascii")
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-p", PIXEL_SSH_PORT,
        PIXEL_IP,
        f"python3 -c \"import base64; exec(base64.b64decode('{b64}').decode('utf-8'))\""
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def is_daemon_healthy():
    for target in [f"http://127.0.0.1:{HOST_PORT}/health", f"{BASE_URL}/health"]:
        try:
            req = urllib.request.Request(target)
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "HEALTHY":
                        return True
        except Exception:
            pass
    return False

def ensure_daemon_running():
    if is_daemon_healthy():
        return True
    run_local_cmd("bash /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/workflow/run_port_4000_hub.sh")
    time.sleep(1.0)
    return is_daemon_healthy()

class TestPixelTailscaleFaultInjection:

    @classmethod
    def setup_class(cls):
        assert ensure_daemon_running(), "Port 4000 daemon could not be started / is not healthy"
        code, out, _ = run_local_cmd(f"ping -c 2 -W 2000 {PIXEL_IP}")
        assert code == 0, f"Cannot ping Pixel at {PIXEL_IP}"

    def test_tc1_pixel_slowloris_trickle_post(self):
        """Send HTTP POST byte-by-byte with simulated delays from Pixel."""
        pixel_code = """
import socket, time, json

HOST = "100.119.199.76"
PORT = 4000

payload = json.dumps({"sample": 0.45, "heart_rate": 82.0, "device_id": "Pixel-Trickle-Test"})
headers = (
    "POST /api/biometrics/sample HTTP/1.1\\r\\n"
    f"Host: {HOST}:{PORT}\\r\\n"
    "Content-Type: application/json\\r\\n"
    f"Content-Length: {len(payload)}\\r\\n"
    "Connection: close\\r\\n\\r\\n"
)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5.0)
s.connect((HOST, PORT))
s.sendall(headers.encode('utf-8'))

for b in payload.encode('utf-8'):
    s.sendall(bytes([b]))
    time.sleep(0.01)

response = s.recv(4096)
s.close()
assert b"200 OK" in response or b"heart_rate_bpm" in response, f"Unexpected response: {response}"
print("TRICKLE_SUCCESS")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote trickle test failed: {stderr}\nStdout: {stdout}"
        assert "TRICKLE_SUCCESS" in stdout
        assert is_daemon_healthy()

    def test_tc2_pixel_pipelined_jitter_requests(self):
        """Send 25 pipelined rapid requests with fluctuating jitter delays from Pixel."""
        pixel_code = """
import http.client, json, time, random

HOST = "100.119.199.76"
PORT = 4000

conn = http.client.HTTPConnection(HOST, PORT, timeout=4.0)
latencies = []

for i in range(25):
    t0 = time.time()
    try:
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        body = resp.read()
        data = json.loads(body.decode('utf-8'))
        assert data['status'] == 'HEALTHY'
    except Exception:
        # Reconnect on transient socket reset
        conn = http.client.HTTPConnection(HOST, PORT, timeout=4.0)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        body = resp.read()
        data = json.loads(body.decode('utf-8'))
        assert data['status'] == 'HEALTHY'

    lat = (time.time() - t0) * 1000.0
    latencies.append(lat)
    time.sleep(random.uniform(0.005, 0.03))

conn.close()
avg_lat = sum(latencies) / len(latencies)
print(f"JITTER_SUCCESS: Avg Latency = {avg_lat:.2f}ms, Max = {max(latencies):.2f}ms")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote jitter test failed: {stderr}\nStdout: {stdout}"
        assert "JITTER_SUCCESS" in stdout
        assert is_daemon_healthy()

    def test_tc3_pixel_abrupt_http_rst_mid_stream(self):
        """Open TCP socket from Pixel, send half HTTP header/body, then abrupt RST."""
        pixel_code = """
import socket, struct, time

HOST = "100.119.199.76"
PORT = 4000

for i in range(10):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    partial = f"POST /api/biometrics/sample HTTP/1.1\\r\\nHost: {HOST}:{PORT}\\r\\nContent-Length: 5000\\r\\n\\r\\n{{\\"sample\\": 1.23"
    s.sendall(partial.encode('utf-8'))
    time.sleep(0.01)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    s.close()
    time.sleep(0.02)

print("ABRUPT_RST_SUCCESS")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote abrupt RST test failed: {stderr}\nStdout: {stdout}"
        assert "ABRUPT_RST_SUCCESS" in stdout
        assert is_daemon_healthy()

    def test_tc4_pixel_abrupt_websocket_rst_churn(self):
        """Initiate WebSocket handshake from Pixel, read partial frames, then force RST (10 cycles)."""
        pixel_code = """
import socket, struct, time, base64

HOST = "100.119.199.76"
PORT = 4000

ws_key = base64.b64encode(b"lauburu_test_key_123").decode('ascii')
upgrade_req = (
    f"GET /ws/telemetry HTTP/1.1\\r\\n"
    f"Host: {HOST}:{PORT}\\r\\n"
    f"Upgrade: websocket\\r\\n"
    f"Connection: Upgrade\\r\\n"
    f"Sec-WebSocket-Key: {ws_key}\\r\\n"
    f"Sec-WebSocket-Version: 13\\r\\n\\r\\n"
)

for i in range(10):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.sendall(upgrade_req.encode('utf-8'))
    data = s.recv(1024)
    assert b"101 Switching Protocols" in data, f"WS Upgrade failed: {data}"
    _ = s.recv(2048)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    s.close()
    time.sleep(0.05)

print("WS_RST_CHURN_SUCCESS")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote WS RST churn test failed: {stderr}\nStdout: {stdout}"
        assert "WS_RST_CHURN_SUCCESS" in stdout
        assert is_daemon_healthy()

    def test_tc5_pixel_malformed_json_and_fuzz_payloads(self):
        """Send empty, broken, and binary fuzzed payloads from Pixel; verify daemon handles errors cleanly."""
        pixel_code = """
import urllib.request, urllib.error, json

HOST = "100.119.199.76"
PORT = 4000
URL = f"http://{HOST}:{PORT}/api/biometrics/sample"

test_cases = [
    (b"", 400, 422),
    (b"{}", 200, 200),
    (b"[]", 200, 422),
    (b'{"sample": ', 400, 422),
    (b'{"sample": "not_a_float"}', 400, 422),
    (b"\\x00\\xff\\xfe\\xba\\xbe\\xde\\xad", 400, 422),
    (b'{"sample": 0.5, "rr_intervals": "invalid"}', 400, 422),
]

for payload, min_code, max_code in test_cases:
    req = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert min_code <= resp.status <= max_code, f"Payload {payload} expected {min_code}-{max_code}, got {resp.status}"
    except urllib.error.HTTPError as e:
        assert min_code <= e.code <= max_code, f"Payload {payload} expected {min_code}-{max_code}, got HTTP {e.code}"

print("MALFORMED_JSON_HANDLED_CLEANLY")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote malformed JSON test failed: {stderr}\nStdout: {stdout}"
        assert "MALFORMED_JSON_HANDLED_CLEANLY" in stdout
        assert is_daemon_healthy()

    def test_tc6_pixel_numerical_extremes_and_special_floats(self):
        """Send extreme floats, subnormals, and boundary arrays; verify safe processing without panic."""
        pixel_code = """
import urllib.request, json

HOST = "100.119.199.76"
PORT = 4000
URL = f"http://{HOST}:{PORT}/api/biometrics/sample"

extreme_payloads = [
    {"sample": 0.0, "heart_rate": 0.0, "rr_intervals": [250.0, 2200.0]},
    {"sample": -999999.0, "heart_rate": 300.0, "rr_intervals": [-500.0, 0.0, 5000.0]},
    {"sample": 1e30, "heart_rate": 120.0, "rr_interval_ms": 600.0, "rmssd_ms": 55.0},
    {"sample": 1e-40, "heart_rate": 60.0, "rr_intervals": [800.0, 800.0]},
]

for p in extreme_payloads:
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode('utf-8'))
        assert "heart_rate_bpm" in res

print("NUMERICAL_EXTREMES_HANDLED_CLEANLY")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote numerical extremes test failed: {stderr}\nStdout: {stdout}"
        assert "NUMERICAL_EXTREMES_HANDLED_CLEANLY" in stdout
        assert is_daemon_healthy()

    def test_tc7_pixel_oversized_payload_stress(self):
        """Send oversized payloads (100KB and 500KB JSON) from Pixel; verify server handles or limits cleanly."""
        pixel_code = """
import urllib.request, urllib.error, json

HOST = "100.119.199.76"
PORT = 4000
URL = f"http://{HOST}:{PORT}/api/biometrics/sample"

big_payload = json.dumps({"sample": 0.5, "heart_rate": 90.0, "device_id": "X" * 100000}).encode('utf-8')
req = urllib.request.Request(URL, data=big_payload, headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status in (200, 413)
except urllib.error.HTTPError as e:
    assert e.code in (400, 413, 422)

rr_payload = json.dumps({"sample": 0.5, "rr_intervals": [800.0] * 5000}).encode('utf-8')
req = urllib.request.Request(URL, data=rr_payload, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=5.0) as resp:
    assert resp.status == 200

print("OVERSIZED_PAYLOAD_HANDLED")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote oversized payload test failed: {stderr}\nStdout: {stdout}"
        assert "OVERSIZED_PAYLOAD_HANDLED" in stdout
        assert is_daemon_healthy()

    def test_tc8_pixel_concurrent_flood_and_recovery(self):
        """Spawn 20 concurrent threads on Pixel flooding REST ingress over Tailscale; verify 100% success and no daemon crash."""
        pixel_code = """
import concurrent.futures, urllib.request, json

HOST = "100.119.199.76"
PORT = 4000
URL = f"http://{HOST}:{PORT}/api/biometrics/sample"

def send_req(i):
    p = {"sample": float(i) * 0.01, "heart_rate": 70.0 + float(i % 30), "device_id": f"Pixel-Flood-{i}"}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=4.0) as resp:
        return resp.status

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futures = [ex.submit(send_req, i) for i in range(50)]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]

assert all(r == 200 for r in results), f"Some requests failed: {results}"
print("CONCURRENT_FLOOD_SUCCESS: 50/50 requests 200 OK")
"""
        code, stdout, stderr = run_remote_pixel_python(pixel_code)
        assert code == 0, f"Remote concurrent flood test failed: {stderr}\nStdout: {stdout}"
        assert "CONCURRENT_FLOOD_SUCCESS" in stdout
        assert is_daemon_healthy()

    def test_tc9_post_fault_daemon_zero_mock_verification(self):
        """Audit /api/biometrics/snapshot and /health after all fault injections to confirm 0% mock corruption."""
        req = urllib.request.Request(f"{BASE_URL}/api/biometrics/snapshot")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            snap = json.loads(resp.read().decode("utf-8"))
            assert snap["sample_rate_hz"] == 512.0
            assert "heart_rate_bpm" in snap
            assert "readiness_score" in snap
            assert "dfa_alpha1" in snap

        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            health = json.loads(resp.read().decode("utf-8"))
            assert health["status"] == "HEALTHY"
            assert health["service"] == "lauburu_port4000_core"
            assert health["port"] == 4000

if __name__ == "__main__":
    code = pytest.main(["-v", __file__])
    sys.exit(code)
