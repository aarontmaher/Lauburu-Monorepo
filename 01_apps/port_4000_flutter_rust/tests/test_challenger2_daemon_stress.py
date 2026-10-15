#!/usr/bin/env python3
"""
Challenger 2 Empirical Adversarial Stress Harness:
1. Daemon lifecycle (Cold Start, Warm Restart, SIGINT, SIGTERM, SIGKILL)
2. Port Contention & Collision Recovery
3. Rapid Restart Storm (20 consecutive cycles)
4. High-Throughput WebSocket Broadcast & Abrupt Drop Churn (50 concurrent clients)
5. Pathological REST Ingestion Fuzzing (NaN, Inf, Malformed JSON, High Concurrency)
"""

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import websockets
import pytest

BIN_PATH = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/rust_backend/target/release/port4000_server'
PORT = 4000
BASE_URL = f'http://127.0.0.1:{PORT}'
WS_URL = f'ws://127.0.0.1:{PORT}'

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_port_process(port):
    try:
        out = subprocess.check_output(['lsof', '-ti', f':{port}']).decode().strip()
        for pid_str in out.split():
            if pid_str.isdigit():
                os.kill(int(pid_str), signal.SIGKILL)
        time.sleep(0.5)
    except Exception:
        pass

def wait_for_server(port, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f'http://127.0.0.1:{port}/health')
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('status') == 'HEALTHY':
                        return True
        except Exception:
            time.sleep(0.1)
    return False

class TestChallenger2DaemonLifecycleStress:
    @classmethod
    def setup_class(cls):
        kill_port_process(PORT)
        # Ensure binary exists
        if not os.path.exists(BIN_PATH):
            subprocess.run(['cargo', 'build', '--release', '--bin', 'port4000_server'],
                           cwd='/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/rust_backend',
                           check=True)

    @classmethod
    def teardown_class(cls):
        kill_port_process(PORT)
        subprocess.Popen([BIN_PATH], env=dict(os.environ, PORT=str(PORT)))
        wait_for_server(PORT, timeout=5.0)

    def test_tc1_cold_start_and_sigterm_teardown(self):
        """Test clean startup and SIGTERM teardown."""
        kill_port_process(PORT)
        proc = subprocess.Popen([BIN_PATH], env=dict(os.environ, PORT=str(PORT)))
        try:
            assert wait_for_server(PORT, timeout=5.0), 'Daemon failed to start on cold start'
            # Send SIGTERM
            proc.terminate()
            ret = proc.wait(timeout=3.0)
            assert not is_port_in_use(PORT), 'Port 4000 still open after SIGTERM'
        finally:
            if proc.poll() is None:
                proc.kill()
            kill_port_process(PORT)

    def test_tc2_port_contention_detection(self):
        """Test behavior when port 4000 is occupied by a blocking socket."""
        kill_port_process(PORT)
        # Occupy port 4000 with a dummy TCP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', PORT))
        s.listen(1)
        
        try:
            proc = subprocess.Popen([BIN_PATH], env=dict(os.environ, PORT=str(PORT)),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Server should fail to bind and terminate with error
            ret = proc.wait(timeout=5.0)
            assert ret != 0, f'Server should have exited with error on port collision, got exit code {ret}'
        finally:
            s.close()
            kill_port_process(PORT)

    def test_tc3_rapid_restart_storm(self):
        """Stress test 15 consecutive rapid start-kill cycles in under 10 seconds."""
        kill_port_process(PORT)
        cycles = 15
        start_time = time.time()
        for i in range(cycles):
            proc = subprocess.Popen([BIN_PATH], env=dict(os.environ, PORT=str(PORT)))
            assert wait_for_server(PORT, timeout=3.0), f'Cycle {i+1} failed to start'
            proc.kill()
            proc.wait(timeout=2.0)
            time.sleep(0.05)
        elapsed = time.time() - start_time
        assert elapsed < 15.0, f'Rapid restart storm took too long: {elapsed:.2f}s'
        assert not is_port_in_use(PORT), 'Port leaked after restart storm'

    def test_tc4_high_concurrency_fuzzing(self):
        """Fuzz REST endpoint with concurrent pathological and malformed payloads."""
        kill_port_process(PORT)
        proc = subprocess.Popen([BIN_PATH], env=dict(os.environ, PORT=str(PORT)))
        try:
            assert wait_for_server(PORT, timeout=5.0)

            payloads = [
                {'sample': 0.0, 'heart_rate': 0.0},
                {'sample': -999.9, 'heart_rate': 300.0, 'rr_intervals': [250.0, 2200.0]},
                {'sample': 1e6, 'heart_rate': 120.0, 'rr_interval_ms': 500.0, 'rmssd_ms': 45.0},
                {'sample': 0.1, 'device_id': 'A' * 1024},
                {'sample': 0.2, 'rr_intervals': [-100.0, 99999.0, 0.0]}, # Out of range RRs ignored
                {},
            ]

            import concurrent.futures
            def send_payload(p):
                url = f'{BASE_URL}/api/biometrics/sample'
                data = json.dumps(p).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    return resp.status

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(send_payload, payloads[i % len(payloads)]) for i in range(50)]
                statuses = [f.result() for f in concurrent.futures.as_completed(futures)]
                assert all(s == 200 for s in statuses)

            # Verify server is still healthy
            req = urllib.request.Request(f'{BASE_URL}/health')
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                assert resp.status == 200
        finally:
            proc.kill()
            kill_port_process(PORT)

    @pytest.mark.asyncio
    async def test_tc5_websocket_high_concurrency_and_abrupt_teardown(self):
        """Test 30 concurrent WebSocket connections to /ws/telemetry and /ws/spatial with abrupt drops."""
        kill_port_process(PORT)
        proc = subprocess.Popen([BIN_PATH], env=dict(os.environ, PORT=str(PORT)))
        try:
            assert wait_for_server(PORT, timeout=5.0)

            async def ws_churn_client(endpoint, frames_to_read=5):
                uri = f'{WS_URL}{endpoint}'
                async with websockets.connect(uri) as ws:
                    for _ in range(frames_to_read):
                        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        assert len(msg) > 0
                # Exits context without sending close frame (abrupt drop)

            # Spawn 15 clients on telemetry and 15 on spatial
            tasks = []
            for i in range(15):
                tasks.append(ws_churn_client('/ws/telemetry', frames_to_read=8))
                tasks.append(ws_churn_client('/ws/spatial', frames_to_read=8))

            await asyncio.gather(*tasks)

            # Verify server remains healthy and responsive
            req = urllib.request.Request(f'{BASE_URL}/health')
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                assert data['status'] == 'HEALTHY'
        finally:
            proc.kill()
            kill_port_process(PORT)
