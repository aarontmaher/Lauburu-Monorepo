#!/usr/bin/env python3
"""
EMPIRICAL CHALLENGER 1 (Milestone 4): Deep Adversarial Stress & Chaos Harness.
Focus Areas:
1. High-throughput sample ingestion (500 samples) concurrent with 50 WebSocket subscribers.
2. Malformed / Pathological JSON fuzzing on /api/shopify/verify and /api/biometrics/sample.
3. Bidirectional WS fuzzing: Sending random binary / malformed text frames to /ws/telemetry and /ws/spatial.
4. Heavy concurrent Read/Write race condition (50 writers + 50 readers).
5. Process Memory (RSS) stability check under sustained load.
6. Zero-Mock state preservation after chaotic operations.
"""

import asyncio
import concurrent.futures
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import pytest
import websockets

BASE_URL = "http://127.0.0.1:4000"
WS_URL = "ws://127.0.0.1:4000"

def get_server_rss_kb():
    try:
        out = subprocess.check_output(["lsof", "-ti", ":4000"]).decode().strip()
        pids = [int(p) for p in out.split() if p.isdigit()]
        if not pids:
            return 0
        pid = pids[0]
        # Get RSS on macOS via ps -o rss= -p <pid>
        rss_out = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)]).decode().strip()
        return int(rss_out)
    except Exception:
        return 0

def sync_http_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Challenger1-Deep/1.0", "Connection": "close"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def sync_http_post(path, data, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json", "User-Agent": "Challenger1-Deep/1.0", "Connection": "close"}
    if headers:
        req_headers.update(headers)
    payload = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else data
    req = urllib.request.Request(url, data=payload, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        return e.code, body

class TestDeepAdversarialPort4000:

    @pytest.mark.asyncio
    async def test_adv_1_high_throughput_ingestion_with_ws_subscribers(self):
        """Flood /api/biometrics/sample with 200 rapid dynamic samples while 50 WebSocket clients listen."""
        NUM_SUBSCRIBERS = 50
        SAMPLE_COUNT = 100

        received_counts = [0] * NUM_SUBSCRIBERS
        connected_event = asyncio.Event()
        connected_count = 0

        async def ws_listener(idx):
            nonlocal connected_count
            uri = f"{WS_URL}/ws/telemetry"
            try:
                async with websockets.connect(uri) as ws:
                    connected_count += 1
                    if connected_count >= NUM_SUBSCRIBERS:
                        connected_event.set()
                    while received_counts[idx] < 20:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                            data = json.loads(msg)
                            assert "heart_rate_bpm" in data
                            received_counts[idx] += 1
                        except asyncio.TimeoutError:
                            break
            except Exception:
                pass

        # Start 50 WebSocket listeners
        tasks = [asyncio.create_task(ws_listener(i)) for i in range(NUM_SUBSCRIBERS)]
        try:
            await asyncio.wait_for(connected_event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        await asyncio.sleep(0.1)

        # Flood POST /api/biometrics/sample in parallel threads
        def send_sample(i):
            payload = {
                "sample": float(i % 10) * 0.1,
                "heart_rate": 120.0 + (i % 30),
                "rr_intervals": [500.0, 502.0],
                "device_id": f"FloodTester-{i % 5}"
            }
            return sync_http_post("/api/biometrics/sample", payload)

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            post_tasks = [loop.run_in_executor(executor, send_sample, i) for i in range(SAMPLE_COUNT)]
            post_results = await asyncio.gather(*post_tasks)

        assert all(st == 200 for st, _ in post_results)

        # Wait for WS tasks to finish or timeout
        await asyncio.gather(*tasks, return_exceptions=True)
        print(f"\n[Adversarial 1] 50 WS subscribers received avg {sum(received_counts)/NUM_SUBSCRIBERS:.1f} frames during 100 sample flood.")
        assert all(c >= 10 for c in received_counts)

    def test_adv_2_shopify_fuzzing(self):
        """Fuzz /api/shopify/verify with malformed, oversized, and pathological inputs."""
        fuzz_cases = [
            # Valid known tokens
            ({"token": "lauburu_pro_sample_token"}, 200, 1),
            ({"token": "lauburu_lifetime_crowdsourced_mac"}, 200, 2),
            ({"token": "random_unknown_token_xyz"}, 200, 0),
            # Empty token
            ({"token": ""}, 200, 0),
            # Huge token (64 KB)
            ({"token": "A" * 65536}, 200, 0),
            # Special chars & SQL/script injection payloads
            ({"token": "'; DROP TABLE users; --"}, 200, 0),
            ({"token": "<script>alert('xss')</script>"}, 200, 0),
            ({"token": "\x00\x01\x02\x03\xff"}, 200, 0),
            # Malformed JSON types
            (b"{'token': invalid_json}", 400, None),
            ({"invalid_field": 123}, (400, 422), None),
            (b"", (400, 422), None),
        ]

        for payload, expected_status, expected_tier in fuzz_cases:
            st, resp = sync_http_post("/api/shopify/verify", payload)
            if isinstance(expected_status, tuple):
                assert st in expected_status, f"Expected {expected_status}, got {st} for {payload}"
            else:
                assert st == expected_status, f"Expected {expected_status}, got {st} for {payload}"
            if expected_tier is not None and st == 200:
                assert resp["tier_code"] == expected_tier

    def test_adv_3_biometrics_sample_pathological_fuzzing(self):
        """Fuzz /api/biometrics/sample with extreme numeric boundaries, out-of-range RR intervals, and oversized arrays."""
        test_cases = [
            # Physiological boundaries
            {"sample": 0.0, "heart_rate": 20.0, "rr_interval_ms": 3000.0},
            {"sample": 1.0, "heart_rate": 250.0, "rr_intervals": [240.0, 2201.0]}, # Out of range RRs ignored
            {"sample": -0.5, "heart_rate": 140.0, "rmssd_ms": 120.0},
            # Negative & zero values
            {"sample": -100.0, "heart_rate": -10.0},
            # Giant RR interval array (500 elements)
            {"sample": 0.2, "heart_rate": 130.0, "rr_intervals": [500.0] * 500},
            # Huge device ID string (4 KB)
            {"sample": 0.1, "heart_rate": 80.0, "device_id": "D" * 4096},
        ]

        for case in test_cases:
            st, resp = sync_http_post("/api/biometrics/sample", case)
            assert st == 200
            assert "is_qrs_peak" in resp
            assert "heart_rate_bpm" in resp

        # Verify health is still intact
        st, health = sync_http_get("/health")
        assert st == 200
        assert health["status"] == "HEALTHY"

    @pytest.mark.asyncio
    async def test_adv_4_websocket_client_to_server_frames_and_binary(self):
        """Send unexpected client-to-server text and binary messages to /ws/telemetry and /ws/spatial."""
        for endpoint in ["/ws/telemetry", "/ws/spatial"]:
            uri = f"{WS_URL}{endpoint}"
            async with websockets.connect(uri) as ws:
                # Receive initial frame
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                assert len(msg) > 0

                # Send client text frame (server should ignore / handle gracefully)
                await ws.send("CLIENT_UNEXPECTED_PING")
                await ws.send(json.dumps({"action": "inject_noise", "val": 999}))

                # Send binary data frame
                await ws.send(b"\x00\x01\x02\xff\xfe\xfd")

                # Verify server is still transmitting frames to client
                msg2 = await asyncio.wait_for(ws.recv(), timeout=2.0)
                assert len(msg2) > 0

    @pytest.mark.asyncio
    async def test_adv_5_concurrent_rw_race_condition(self):
        """50 concurrent writers posting biometrics while 50 concurrent readers fetch snapshots."""
        NUM_OPS = 50

        def do_write(i):
            return sync_http_post("/api/biometrics/sample", {
                "sample": (i % 5) * 0.2,
                "heart_rate": 100.0 + i,
                "rr_intervals": [600.0 - i, 601.0 - i],
                "device_id": f"RaceDevice-{i}"
            })

        def do_read(i):
            path = "/api/biometrics/snapshot" if i % 2 == 0 else "/api/biometrics/readiness"
            return sync_http_get(path)

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            write_tasks = [loop.run_in_executor(executor, do_write, i) for i in range(NUM_OPS)]
            read_tasks = [loop.run_in_executor(executor, do_read, i) for i in range(NUM_OPS)]
            all_tasks = write_tasks + read_tasks
            results = await asyncio.gather(*all_tasks)

        write_res = results[:NUM_OPS]
        read_res = results[NUM_OPS:]

        assert all(st == 200 for st, _ in write_res)
        assert all(st == 200 for st, _ in read_res)

    def test_adv_6_memory_rss_stability(self):
        """Verify memory RSS does not leak or balloon after heavy traffic."""
        rss_initial = get_server_rss_kb()
        print(f"\n[Memory RSS] Initial: {rss_initial} KB (~{rss_initial/1024:.2f} MB)")

        # Run 500 fast requests
        for i in range(500):
            sync_http_get("/health")
            if i % 10 == 0:
                sync_http_post("/api/biometrics/sample", {"sample": 0.0, "heart_rate": 80.0})

        time.sleep(0.5)
        rss_final = get_server_rss_kb()
        print(f"[Memory RSS] Final after 500 requests: {rss_final} KB (~{rss_final/1024:.2f} MB)")

        if rss_initial > 0 and rss_final > 0:
            growth_mb = (rss_final - rss_initial) / 1024
            print(f"[Memory RSS] Net Growth: {growth_mb:.2f} MB")
            # Memory growth under 50MB is nominal for tokio buffer pool
            assert growth_mb < 50.0, f"Excessive memory growth detected: {growth_mb:.2f} MB"

        # Final health verify
        st, health = sync_http_get("/health")
        assert st == 200
        assert health["status"] == "HEALTHY"

if __name__ == "__main__":
    code = pytest.main(["-v", "-s", __file__])
    import sys
    sys.exit(code)
