"""
WhatCable Concurrency Stress & Cache Latency Challenger Test Suite
Milestone M1 Empirical Verification Harness.

Adheres strictly to:
- Cardinal Rule 1 (Zero-Mock Truth Rule)
- PROJECT.md Interface Contracts
- Empirical Challenger Protocol (50 concurrent requests, cache hit vs ?force=true, cached latency < 10ms, schema validation under stress)
"""

import sys
import time
import asyncio
import statistics
from pathlib import Path
from typing import Dict, Any, List
import pytest
import httpx
from concurrent.futures import ThreadPoolExecutor

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.server import app
from starlette.testclient import TestClient


def validate_whatcable_schema(data: Dict[str, Any]) -> None:
    """Strict JSON schema validation for GET /api/whatcable/details."""
    assert isinstance(data, dict), "Response must be a JSON object"
    assert data.get("status") == "success", f"Expected status 'success', got {data.get('status')}"
    assert data.get("engine") == "whatcable_native_hybrid", f"Expected engine 'whatcable_native_hybrid', got {data.get('engine')}"
    assert data.get("engine_source") in (
        "whatcable_cli_and_darwin_iokit",
        "darwin_iokit_fallback"
    ), f"Unknown engine_source: {data.get('engine_source')}"
    assert "timestamp" in data and isinstance(data["timestamp"], (int, float)), "Missing or invalid timestamp"
    assert data.get("is_desktop_mac") is True, "is_desktop_mac must be True on Host L1"

    # Host hardware
    host_hw = data.get("host_hardware")
    assert isinstance(host_hw, dict), "Missing host_hardware object"
    assert "model" in host_hw and isinstance(host_hw["model"], str)
    assert "chip" in host_hw and isinstance(host_hw["chip"], str)
    assert "ports_count" in host_hw and isinstance(host_hw["ports_count"], int)

    # Summary
    summary = data.get("summary")
    assert isinstance(summary, dict), "Missing summary object"
    required_summary_fields = [
        "total_ports",
        "active_ports",
        "cables_detected",
        "emarkers_detected",
        "bottlenecks_detected",
        "max_negotiated_speed_gbps",
        "max_power_rating_watts",
    ]
    for field in required_summary_fields:
        assert field in summary, f"Missing summary field: {field}"
        assert isinstance(summary[field], (int, float)), f"Field {field} must be numeric"

    # Ports
    ports = data.get("ports")
    assert isinstance(ports, list), "ports must be a list"
    assert len(ports) > 0, "ports list cannot be empty on Mac Mini M4 Pro"

    for p in ports:
        assert "port_id" in p and isinstance(p["port_id"], str)
        assert "receptacle" in p and isinstance(p["receptacle"], int)
        assert "port_type" in p and isinstance(p["port_type"], str)
        assert "connection_active" in p and isinstance(p["connection_active"], bool)
        assert "status" in p and isinstance(p["status"], str)
        assert "headline" in p and isinstance(p["headline"], str)
        assert "subtitle" in p and isinstance(p["subtitle"], str)

        transports = p.get("transports")
        assert isinstance(transports, dict), f"Port {p['port_id']} missing transports dict"
        assert "active" in transports and isinstance(transports["active"], list)
        assert "supported" in transports and isinstance(transports["supported"], list)
        assert "provisioned" in transports and isinstance(transports["provisioned"], list)

        # Cable validation if present
        cable = p.get("cable")
        if cable is not None:
            assert isinstance(cable, dict), f"Port {p['port_id']} cable must be dict or None"
            assert "present" in cable and isinstance(cable["present"], bool)
            assert "e_marker" in cable and isinstance(cable["e_marker"], bool)
            assert "vendor_id" in cable and isinstance(cable["vendor_id"], int)
            assert "vendor_name" in cable and isinstance(cable["vendor_name"], str)
            assert "speed_rating" in cable and isinstance(cable["speed_rating"], str)
            assert "max_bandwidth_gbps" in cable and isinstance(cable["max_bandwidth_gbps"], (int, float))
            assert "max_watts" in cable and isinstance(cable["max_watts"], (int, float))
            pd = cable.get("power_delivery")
            if pd is not None:
                assert isinstance(pd, dict)
                assert "max_voltage" in pd
                assert "max_current_amperes" in pd

        # Data link validation if present
        data_link = p.get("data_link")
        if data_link is not None:
            assert isinstance(data_link, dict)
            assert "link_active" in data_link and isinstance(data_link["link_active"], bool)
            assert "negotiated_gbps" in data_link and isinstance(data_link["negotiated_gbps"], (int, float))
            assert "lanes" in data_link and isinstance(data_link["lanes"], int)
            assert "generation" in data_link and isinstance(data_link["generation"], str)

        # Bottleneck validation
        bottleneck = p.get("bottleneck")
        assert isinstance(bottleneck, dict), f"Port {p['port_id']} missing bottleneck dict"
        assert "is_bottleneck" in bottleneck and isinstance(bottleneck["is_bottleneck"], bool)
        assert "severity" in bottleneck and bottleneck["severity"] in ("CRITICAL", "WARNING", "INFO", "OPTIMAL")
        assert "summary" in bottleneck and isinstance(bottleneck["summary"], str)

    # Display ports
    display_ports = data.get("display_ports")
    assert isinstance(display_ports, list), "display_ports must be a list"
    for dp in display_ports:
        assert "port_id" in dp and isinstance(dp["port_id"], str)
        assert "port_number" in dp and isinstance(dp["port_number"], int)
        assert "port_type" in dp and isinstance(dp["port_type"], str)
        assert "displays" in dp and isinstance(dp["displays"], list)
        for d in dp["displays"]:
            assert "monitor_name" in d and isinstance(d["monitor_name"], str)
            assert "rate" in d and isinstance(d["rate"], str)
            assert "lanes" in d and isinstance(d["lanes"], int)
            assert "delivered_gbps" in d and isinstance(d["delivered_gbps"], (int, float))
            assert "needed_gbps" in d and isinstance(d["needed_gbps"], (int, float))
            assert "headroom_gbps" in d and isinstance(d["headroom_gbps"], (int, float))
            assert "bottleneck" in d and isinstance(d["bottleneck"], dict)


# ============================================================================
# 1. HIGH CONCURRENCY STRESS (50 CONCURRENT REQUESTS)
# ============================================================================

@pytest.mark.asyncio
async def test_whatcable_50_concurrent_requests():
    """Fire 50 concurrent requests simultaneously via httpx.AsyncClient using ASGI transport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Pre-warm cache once
        warm_resp = await client.get("/api/whatcable/details")
        assert warm_resp.status_code == 200

        start_time = time.perf_counter()

        async def fetch_one(idx: int):
            t0 = time.perf_counter()
            resp = await client.get("/api/whatcable/details")
            t1 = time.perf_counter()
            return idx, resp.status_code, (t1 - t0) * 1000.0, resp.json()

        tasks = [fetch_one(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        total_wall_ms = (time.perf_counter() - start_time) * 1000.0

    # Analyze results
    latencies = [r[2] for r in results]
    status_codes = [r[1] for r in results]

    assert all(code == 200 for code in status_codes), f"Not all requests returned 200: {status_codes}"
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"

    # Schema validation for every single response
    for idx, code, lat, body in results:
        validate_whatcable_schema(body)

    mean_lat = statistics.mean(latencies)
    median_lat = statistics.median(latencies)
    p95_lat = sorted(latencies)[int(0.95 * len(latencies))]
    max_lat = max(latencies)
    min_lat = min(latencies)

    print(f"\n[50 Concurrent Requests Results]")
    print(f"  Total Wall Clock Time: {total_wall_ms:.2f} ms")
    print(f"  Min Latency:           {min_lat:.2f} ms")
    print(f"  Mean Latency:          {mean_lat:.2f} ms")
    print(f"  Median (p50):          {median_lat:.2f} ms")
    print(f"  p95 Latency:           {p95_lat:.2f} ms")
    print(f"  Max Latency:           {max_lat:.2f} ms")

    # Assert that all responses returned the same cached timestamp
    timestamps = [r[3]["timestamp"] for r in results]
    assert len(set(timestamps)) == 1, "Concurrent requests returned differing timestamps from cache"


# ============================================================================
# 2. CACHE HIT VS FORCE REFRESH (?force=true)
# ============================================================================

@pytest.mark.asyncio
async def test_whatcable_cache_hit_vs_force_refresh():
    """Verify cache hit behavior, force refresh (?force=true), and cache TTL expiry."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Step A: Initial request (force=True to establish clean baseline)
        r0 = await client.get("/api/whatcable/details?force=true")
        assert r0.status_code == 200
        d0 = r0.json()
        validate_whatcable_schema(d0)
        t0 = d0["timestamp"]

        # Step B: Immediate unforced request -> MUST BE CACHE HIT (identical timestamp)
        r1 = await client.get("/api/whatcable/details")
        assert r1.status_code == 200
        d1 = r1.json()
        validate_whatcable_schema(d1)
        t1 = d1["timestamp"]
        assert t1 == t0, f"Expected cache hit (t1={t1} == t0={t0}), but timestamp changed"

        # Step C: Forced request -> MUST RE-PROBE (t2 > t1)
        # Add small pause to ensure clock advances
        await asyncio.sleep(0.05)
        r2 = await client.get("/api/whatcable/details?force=true")
        assert r2.status_code == 200
        d2 = r2.json()
        validate_whatcable_schema(d2)
        t2 = d2["timestamp"]
        assert t2 > t0, f"Expected forced refresh timestamp (t2={t2}) to exceed baseline (t0={t0})"

        # Step D: Immediate unforced request -> MUST CACHE the newly refreshed data
        r3 = await client.get("/api/whatcable/details?force=false")
        assert r3.status_code == 200
        d3 = r3.json()
        validate_whatcable_schema(d3)
        t3 = d3["timestamp"]
        assert t3 == t2, f"Expected cache hit on forced result (t3={t3} == t2={t2})"

        # Step E: Wait for cache TTL expiration (TTL = 3.0s)
        # Sleep for 3.15s to guarantee expiration
        print("\n  [Sleeping 3.15s to verify cache TTL expiration...]")
        await asyncio.sleep(3.15)

        r4 = await client.get("/api/whatcable/details")
        assert r4.status_code == 200
        d4 = r4.json()
        validate_whatcable_schema(d4)
        t4 = d4["timestamp"]
        assert t4 > t3, f"Expected expired cache to refresh automatically (t4={t4} > t3={t3})"
        print(f"  Cache TTL expired as expected: t4 ({t4}) > t3 ({t3})")


# ============================================================================
# 3. LATENCY VERIFICATION (< 10ms for cached responses)
# ============================================================================

@pytest.mark.asyncio
async def test_whatcable_cached_latency_under_10ms():
    """Verify that cached responses are delivered in < 10ms across 100 sequential requests."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Pre-warm cache
        warm_resp = await client.get("/api/whatcable/details")
        assert warm_resp.status_code == 200

        latencies_ms: List[float] = []

        for i in range(100):
            t_start = time.perf_counter()
            resp = await client.get("/api/whatcable/details")
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            latencies_ms.append(t_elapsed_ms)
            assert resp.status_code == 200

        mean_lat = statistics.mean(latencies_ms)
        median_lat = statistics.median(latencies_ms)
        sorted_lat = sorted(latencies_ms)
        p90_lat = sorted_lat[int(0.90 * len(sorted_lat))]
        p95_lat = sorted_lat[int(0.95 * len(sorted_lat))]
        p99_lat = sorted_lat[int(0.99 * len(sorted_lat))]
        max_lat = max(latencies_ms)
        min_lat = min(latencies_ms)

        print(f"\n[100 Sequential Cached Requests Latency Metrics]")
        print(f"  Min:    {min_lat:.3f} ms")
        print(f"  Mean:   {mean_lat:.3f} ms")
        print(f"  Median: {median_lat:.3f} ms")
        print(f"  p90:    {p90_lat:.3f} ms")
        print(f"  p95:    {p95_lat:.3f} ms")
        print(f"  p99:    {p99_lat:.3f} ms")
        print(f"  Max:    {max_lat:.3f} ms")

        # Invariant: Mean and p95 latency for cached requests MUST be < 10.0 ms
        assert mean_lat < 10.0, f"Mean cached latency {mean_lat:.2f} ms exceeds 10ms threshold"
        assert p95_lat < 10.0, f"p95 cached latency {p95_lat:.2f} ms exceeds 10ms threshold"


# ============================================================================
# 4. MIXED CONCURRENCY STRESS (CACHE READS + CONCURRENT FORCE REFRESH)
# ============================================================================

@pytest.mark.asyncio
async def test_whatcable_mixed_cache_stampede_safety():
    """
    Stress-test cache lock under mixed load:
    25 concurrent unforced requests (readers) + 25 concurrent force=True requests (writers).
    Validates thread-safety, absence of race conditions, and strict schema conformance.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Pre-warm
        await client.get("/api/whatcable/details")

        async def worker(idx: int):
            force = (idx % 2 == 1)  # 25 True, 25 False
            url = f"/api/whatcable/details?force={'true' if force else 'false'}"
            t0 = time.perf_counter()
            resp = await client.get(url)
            t1 = time.perf_counter()
            return idx, force, resp.status_code, (t1 - t0) * 1000.0, resp.json()

        tasks = [worker(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 50
        assert all(r[2] == 200 for r in results), "Some requests failed under mixed stress"

        for idx, force, code, lat_ms, body in results:
            validate_whatcable_schema(body)

        reader_lats = [r[3] for r in results if not r[1]]
        writer_lats = [r[3] for r in results if r[1]]

        print(f"\n[Mixed 50 Requests (25 Cached / 25 Forced) Stress]")
        print(f"  Readers (Cached) Mean: {statistics.mean(reader_lats):.2f} ms")
        print(f"  Writers (Forced) Mean: {statistics.mean(writer_lats):.2f} ms")


# ============================================================================
# 5. OS THREAD-POOL CONCURRENCY STRESS (TestClient via 50 Threads)
# ============================================================================

def test_whatcable_50_os_threads_concurrency():
    """Stress test using 50 native OS threads hitting TestClient synchronously."""
    client = TestClient(app)

    # Warm cache
    r_warm = client.get("/api/whatcable/details")
    assert r_warm.status_code == 200

    def thread_worker(thread_id: int):
        t0 = time.perf_counter()
        resp = client.get("/api/whatcable/details")
        lat_ms = (time.perf_counter() - t0) * 1000.0
        return thread_id, resp.status_code, lat_ms, resp.json()

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(thread_worker, i) for i in range(50)]
        results = [f.result() for f in futures]

    assert len(results) == 50
    assert all(r[1] == 200 for r in results), "Not all thread requests returned HTTP 200"

    for tid, code, lat_ms, body in results:
        validate_whatcable_schema(body)

    latencies = [r[2] for r in results]
    print(f"\n[50 OS ThreadPool Concurrency Results]")
    print(f"  Mean Thread Latency: {statistics.mean(latencies):.2f} ms")
    print(f"  p95 Thread Latency:  {sorted(latencies)[int(0.95 * len(latencies))]:.2f} ms")


# ============================================================================
# 6. LIVE HTTP DAEMON STRESS (PORT 4007 OVER LOOPBACK TCP)
# ============================================================================

@pytest.mark.asyncio
async def test_whatcable_live_daemon_port_4007_stress():
    """
    Test the live uvicorn server running on 127.0.0.1:4007:
    1. Sequential cached latency verification (< 10ms over real TCP loopback).
    2. 50 concurrent HTTP requests stress testing throughput, status codes, and schema.
    """
    live_url = "http://127.0.0.1:4007/api/whatcable/details"

    # Verify server is reachable
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            test_resp = await client.get(live_url)
            if test_resp.status_code != 200:
                pytest.skip(f"Live server at {live_url} returned {test_resp.status_code}")
    except Exception as e:
        pytest.skip(f"Live server at {live_url} not reachable: {e}")

    # 1. Sequential Live Cached Latency (< 10ms)
    async with httpx.AsyncClient(timeout=5.0) as client:
        seq_lats = []
        for _ in range(50):
            t0 = time.perf_counter()
            r = await client.get(live_url)
            seq_lats.append((time.perf_counter() - t0) * 1000.0)
            assert r.status_code == 200
        mean_seq_lat = statistics.mean(seq_lats)
        p95_seq_lat = sorted(seq_lats)[int(0.95 * len(seq_lats))]
        print(f"\n[Live HTTP Port 4007 (50 Sequential Cached Requests)]")
        print(f"  Mean Latency: {mean_seq_lat:.3f} ms")
        print(f"  p95 Latency:  {p95_seq_lat:.3f} ms")
        print(f"  Max Latency:  {max(seq_lats):.3f} ms")
        assert mean_seq_lat < 10.0, f"Live sequential cached latency {mean_seq_lat:.2f} ms exceeds 10ms"
        assert p95_seq_lat < 25.0, f"Live p95 sequential cached latency {p95_seq_lat:.2f} ms exceeds 25ms"

    # 2. 50 Concurrent TCP Requests
    async with httpx.AsyncClient(timeout=10.0) as client:
        async def fetch_live(idx: int):
            t0 = time.perf_counter()
            resp = await client.get(live_url)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            return idx, resp.status_code, lat_ms, resp.json()

        start_time = time.perf_counter()
        tasks = [fetch_live(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        total_time_ms = (time.perf_counter() - start_time) * 1000.0

    assert len(results) == 50
    assert all(r[1] == 200 for r in results), "Live server did not return 200 for all 50 concurrent requests"

    latencies = [r[2] for r in results]
    for idx, code, lat_ms, body in results:
        validate_whatcable_schema(body)

    mean_lat = statistics.mean(latencies)
    p95_lat = sorted(latencies)[int(0.95 * len(latencies))]
    min_lat = min(latencies)
    max_lat = max(latencies)

    print(f"\n[Live HTTP Port 4007 (50 Concurrent TCP Requests)]")
    print(f"  Total Wall Clock: {total_time_ms:.2f} ms")
    print(f"  Throughput:       {50 / (total_time_ms / 1000.0):.1f} req/s")
    print(f"  Min Latency:      {min_lat:.2f} ms")
    print(f"  Mean Latency:     {mean_lat:.2f} ms")
    print(f"  p95 Latency:      {p95_lat:.2f} ms")
    print(f"  Max Latency:      {max_lat:.2f} ms")

    # Assert total wall clock time for 50 concurrent TCP requests is well under 500ms
    assert total_time_ms < 500.0, f"Total wall clock {total_time_ms:.2f} ms exceeds 500ms threshold"


if __name__ == "__main__":
    print("Executing WhatCable Empirical Concurrency & Stress Suite...")
    pytest.main(["-v", "-s", __file__])
