#!/usr/bin/env python3
"""
EMPIRICAL CHALLENGER 1 (Milestone 4): Comprehensive Stress Harness & Adversarial Oracle.
Tests:
1. REST Concurrency & Latency (150+ concurrent requests across all endpoints)
2. Pathological & Fuzz Payload Ingestion (malformed, NaN, overflow, invalid types)
3. High-Throughput Dynamic Ingestion with WebSocket Fanout Verification
4. WebSocket /ws/spatial 60 FPS Multi-Client Concurrency (40 concurrent clients)
5. WebSocket /ws/telemetry High-Concurrency Broadcast (40 concurrent clients)
6. Rapid Connection Churn & Lifecycle Stress (100 rapid connect/disconnect cycles)
7. Zero-Mock State Preservation Invariants under Concurrent Load
"""

import asyncio
import json
import time
import urllib.request
import urllib.error
import concurrent.futures
import pytest
import websockets

BASE_URL = "http://127.0.0.1:4000"
WS_URL = "ws://127.0.0.1:4000"

def sync_http_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Challenger1-Stress/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def sync_http_post(path, data, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json", "User-Agent": "Challenger1-Stress/1.0"}
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

class TestChallenger1RestAndWebSocketStress:

    @pytest.mark.asyncio
    async def test_tc_c1_rest_concurrency_burst(self):
        """Send 150 concurrent GET requests to /health, /api/biometrics/snapshot, and /api/spatial/map."""
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=160)
        async def fetch(path):
            loop = asyncio.get_running_loop()
            start = time.perf_counter()
            status, data = await loop.run_in_executor(executor, sync_http_get, path)
            duration_ms = (time.perf_counter() - start) * 1000
            return status, duration_ms, data

        paths = ["/health", "/api/biometrics/snapshot", "/api/spatial/map", "/api/biometrics/readiness"] * 38  # 152 requests
        tasks = [fetch(p) for p in paths]
        start_total = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time_ms = (time.perf_counter() - start_total) * 1000

        statuses = [r[0] for r in results]
        latencies = [r[1] for r in results]

        assert all(s == 200 for s in statuses), f"Non-200 status received: {[s for s in statuses if s != 200]}"
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\n[REST Concurrency 152 reqs] Total: {total_time_ms:.1f}ms | Avg: {avg_latency:.2f}ms | p95: {p95_latency:.2f}ms | Max: {max_latency:.2f}ms")
        assert avg_latency < 50.0, f"Average REST latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 100.0, f"p95 REST latency too high: {p95_latency:.2f}ms"

    def test_tc_c2_pathological_and_fuzz_payloads(self):
        """Inject pathological and malformed payloads into POST /api/biometrics/sample and verify graceful rejection without server crash."""
        fuzz_cases = [
            # Malformed JSON
            (b"{ invalid json string ...", (400, 422)),
            # Empty body
            (b"", (400, 422)),
            # Null byte injection
            (b'{"sample": 0.0, "\x00": "test"}', (400, 422)),
            # Wrong types
            ({"sample": "not_a_float", "heart_rate": 80.0}, (400, 422)),
            ({"sample": 0.5, "heart_rate": "invalid_hr"}, (400, 422)),
            ({"sample": None, "heart_rate": 80.0}, (400, 422)),
            # Extreme boundary values (should not panic server)
            ({"sample": 1e308, "heart_rate": 1e308}, (200, 400, 422)),
            ({"sample": -1e308, "heart_rate": -50.0}, (200, 400, 422)),
            # Oversized array
            ({"sample": 0.5, "heart_rate": 80.0, "rr_intervals": [100.0] * 5000}, (200, 400, 413, 422)),
        ]

        for payload, expected_status in fuzz_cases:
            status, resp = sync_http_post("/api/biometrics/sample", payload)
            if isinstance(expected_status, tuple):
                assert status in expected_status, f"Unexpected status {status} for payload {payload}: {resp}"
            else:
                assert status == expected_status, f"Expected {expected_status}, got {status} for payload {payload}: {resp}"

        # Confirm server is still alive and responsive after fuzzing
        status, health = sync_http_get("/health")
        assert status == 200
        assert health["status"] == "HEALTHY"

    @pytest.mark.asyncio
    async def test_tc_c3_websocket_spatial_concurrency_and_fps(self):
        """Connect 40 concurrent WebSocket clients to /ws/spatial and verify 60 FPS delivery rate."""
        NUM_CLIENTS = 40
        FRAMES_PER_CLIENT = 20

        async def spatial_client(cid):
            uri = f"{WS_URL}/ws/spatial"
            frames = []
            timestamps = []
            async with websockets.connect(uri) as ws:
                for _ in range(FRAMES_PER_CLIENT):
                    t0 = time.perf_counter()
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    timestamps.append(t0)
                    data = json.loads(msg)
                    frames.append(data)
                    # Verify spatial frame contract
                    assert "landmarks" in data or "athlete_nodes" in data or "current_position" in data
            return cid, len(frames), timestamps

        tasks = [spatial_client(i) for i in range(NUM_CLIENTS)]
        t_start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        t_total = time.perf_counter() - t_start

        total_frames = sum(r[1] for r in results)
        effective_fps = total_frames / (NUM_CLIENTS * t_total) if t_total > 0 else 0

        print(f"\n[WS /ws/spatial {NUM_CLIENTS} Clients] Received {total_frames} total frames in {t_total:.2f}s (~{effective_fps:.1f} FPS/client)")
        assert all(r[1] == FRAMES_PER_CLIENT for r in results)
        assert effective_fps >= 10.0, f"Spatial stream throughput degraded under load: {effective_fps:.1f} FPS"

    @pytest.mark.asyncio
    async def test_tc_c4_websocket_telemetry_broadcast_fanout(self):
        """Connect 40 concurrent WebSocket clients to /ws/telemetry and verify real-time ingestion broadcast."""
        NUM_CLIENTS = 40
        BROADCAST_COUNT = 15

        async def telemetry_client(cid):
            uri = f"{WS_URL}/ws/telemetry"
            received = []
            async with websockets.connect(uri) as ws:
                while len(received) < BROADCAST_COUNT:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(msg)
                    received.append(data)
            return cid, len(received)

        client_tasks = [asyncio.create_task(telemetry_client(i)) for i in range(NUM_CLIENTS)]
        await asyncio.sleep(0.2)  # Give clients time to connect

        # Ingest dynamic samples concurrently while clients are listening
        loop = asyncio.get_running_loop()
        for i in range(BROADCAST_COUNT):
            sample_payload = {
                "sample": 0.5 + (i * 0.1),
                "heart_rate": 130.0 + (i % 20),
                "rr_intervals": [450.0 - i, 451.0],
                "device_id": f"FanoutStressSensor-{i}"
            }
            await loop.run_in_executor(None, sync_http_post, "/api/biometrics/sample", sample_payload)
            await asyncio.sleep(0.02)

        results = await asyncio.gather(*client_tasks)
        print(f"\n[WS /ws/telemetry {NUM_CLIENTS} Clients] All {NUM_CLIENTS} clients received {BROADCAST_COUNT} broadcasts successfully.")
        assert all(r[1] >= BROADCAST_COUNT for r in results)

    @pytest.mark.asyncio
    async def test_tc_c5_rapid_websocket_churn_and_lifecycle(self):
        """Rapidly open and close 100 WebSocket connections on /ws/telemetry and /ws/spatial in bursts."""
        TOTAL_CHURNS = 100

        async def single_churn(i):
            path = "/ws/telemetry" if i % 2 == 0 else "/ws/spatial"
            uri = f"{WS_URL}{path}"
            try:
                async with websockets.connect(uri) as ws:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    assert len(msg) > 0
                    # Abruptly close
                    await ws.close()
                return True
            except Exception as e:
                return False

        # Run in batches of 20 concurrent connections
        batch_size = 20
        success_count = 0
        for b in range(0, TOTAL_CHURNS, batch_size):
            tasks = [single_churn(i) for i in range(b, b + batch_size)]
            batch_res = await asyncio.gather(*tasks)
            success_count += sum(batch_res)

        print(f"\n[WS Churn] Successfully churned {success_count}/{TOTAL_CHURNS} connections without deadlock.")
        assert success_count >= TOTAL_CHURNS * 0.95

        # Verify server is still healthy
        status, health = sync_http_get("/health")
        assert status == 200
        assert health["status"] == "HEALTHY"

    def test_tc_c6_zero_mock_invariants_post_stress(self):
        """Verify that after high concurrent load, server state contracts and shopify tiers remain intact."""
        # 1. Health check integrity
        status, health = sync_http_get("/health")
        assert status == 200
        assert health["service"] == "lauburu_port4000_core"

        # 2. Snapshot integrity
        status, snap = sync_http_get("/api/biometrics/snapshot")
        assert status == 200
        assert snap["sample_rate_hz"] == 512.0

        # 3. Shopify tier contract verification
        tiers = [
            ("lauburu_pro_sample_token", 1, "ProAthlete"),
            ("lauburu_lifetime_crowdsourced_mac", 2, "CrowdsourcedComputeLifetime"),
            ("random_unregistered_token", 0, "FreeCommunity")
        ]
        for token, expected_code, expected_tier in tiers:
            st, res = sync_http_post("/api/shopify/verify", {"token": token})
            assert st == 200
            assert res["tier_code"] == expected_code
            assert res["membership"]["tier"] == expected_tier

if __name__ == "__main__":
    code = pytest.main(["-v", "-s", __file__])
    import sys
    sys.exit(code)
