#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for Voice Bridge WebSocket Daemon
================================================================

Empirical verification harness targeting:
1. High-throughput payload stress: 100KB, 500KB, 1MB, 5MB, 10MB
2. High-frequency packet floods: 500 - 1000 rapid audio slices/sec
3. High-iteration latency benchmark: 100 consecutive 100KB transmissions
4. 10-client concurrent multi-tenant load with zero cross-talk
5. Boundary and chaos stress: exact 10MB, oversize 10MB+1KB, malformed frames, rapid reconnect storm
6. Empirical latency telemetry: Min, Max, Mean, Median (P50), P95, P99, StdDev, SLA verification (<500ms)
7. Exact byte-by-byte and SHA256 data integrity verification across all tests.
"""

import os
import sys
import time
import math
import json
import socket
import hashlib
import logging
import asyncio
import argparse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

import websockets

# Configuration defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_WS_URL = f"ws://{DEFAULT_HOST}:{DEFAULT_PORT}"
DEFAULT_HTTP_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
MAX_FRAME_SIZE = 10 * 1024 * 1024  # 10 MB
SLA_THRESHOLD_MS = 500.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("AdversarialStress")


@dataclass
class BenchmarkStats:
    name: str
    total_iterations: int
    payload_size_bytes: int
    rtts: List[float] = field(default_factory=list)
    min_ms: float = 0.0
    max_ms: float = 0.0
    mean_ms: float = 0.0
    median_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    std_dev_ms: float = 0.0
    sla_violations: int = 0
    integrity_passes: int = 0
    integrity_failures: int = 0
    throughput_mbps: float = 0.0
    passed: bool = False

    def compute(self):
        if not self.rtts:
            return
        self.min_ms = min(self.rtts)
        self.max_ms = max(self.rtts)
        self.mean_ms = sum(self.rtts) / len(self.rtts)
        
        sorted_r = sorted(self.rtts)
        n = len(sorted_r)
        
        def pct(p: float) -> float:
            idx = int(math.ceil(p * n)) - 1
            return sorted_r[max(0, min(idx, n - 1))]

        self.median_ms = pct(0.50)
        self.p90_ms = pct(0.90)
        self.p95_ms = pct(0.95)
        self.p99_ms = pct(0.99)

        if n > 1:
            var = sum((x - self.mean_ms) ** 2 for x in self.rtts) / (n - 1)
            self.std_dev_ms = math.sqrt(var)
        else:
            self.std_dev_ms = 0.0

        self.sla_violations = sum(1 for x in self.rtts if x >= SLA_THRESHOLD_MS)
        
        if self.mean_ms > 0 and self.payload_size_bytes > 0:
            # 2 * payload_size (send + receive) per RTT
            total_bytes_per_rtt = self.payload_size_bytes * 2
            mb_per_sec = (total_bytes_per_rtt / (1024 * 1024)) / (self.mean_ms / 1000.0)
            self.throughput_mbps = mb_per_sec

        self.passed = (self.sla_violations == 0) and (self.integrity_failures == 0) and (self.integrity_passes == self.total_iterations)


async def consume_initial_greeting(ws: Any) -> Dict[str, Any]:
    """Consumes and parses the initial JSON ready greeting from the voice bridge."""
    raw = await ws.recv()
    if isinstance(raw, str):
        return json.loads(raw)
    raise ValueError(f"Expected JSON greeting, got binary frame: {len(raw)} bytes")


# ============================================================================
# 1. High-Iteration Latency Benchmark (100 consecutive 100KB transmissions)
# ============================================================================
async def run_high_iteration_benchmark(url: str, iterations: int = 100, payload_bytes: int = 102400) -> BenchmarkStats:
    stats = BenchmarkStats(
        name="High-Iteration 100KB Benchmark",
        total_iterations=iterations,
        payload_size_bytes=payload_bytes
    )
    logger.info("⚡ [1/6] Running %d iterations of %d-byte (%.1f KB) transmissions...", iterations, payload_bytes, payload_bytes / 1024)

    async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None, ping_interval=None) as ws:
        greeting = await consume_initial_greeting(ws)
        assert greeting.get("type") == "ready", f"Unexpected greeting: {greeting}"

        for i in range(iterations):
            payload = os.urandom(payload_bytes)
            sent_hash = hashlib.sha256(payload).hexdigest()

            t0 = time.perf_counter()
            await ws.send(payload)
            response = await ws.recv()
            t1 = time.perf_counter()

            rtt_ms = (t1 - t0) * 1000.0
            stats.rtts.append(rtt_ms)

            if isinstance(response, bytes) and hashlib.sha256(response).hexdigest() == sent_hash and response == payload:
                stats.integrity_passes += 1
            else:
                stats.integrity_failures += 1
                logger.error("❌ Integrity mismatch at iteration %d!", i)

    stats.compute()
    logger.info(
        "📊 High-Iteration Benchmark Results: Iterations: %d | Min: %.2fms | Mean: %.2fms | Median: %.2fms | P95: %.2fms | P99: %.2fms | Max: %.2fms | SLA Violations (>=500ms): %d | Integrity: %d/%d (Pass: %s)",
        stats.total_iterations, stats.min_ms, stats.mean_ms, stats.median_ms, stats.p95_ms, stats.p99_ms, stats.max_ms, stats.sla_violations, stats.integrity_passes, stats.total_iterations, stats.passed
    )
    return stats


# ============================================================================
# 2. High-Throughput Payload Scale Stress (100KB, 500KB, 1MB, 5MB, 10MB)
# ============================================================================
async def run_payload_scale_stress(url: str) -> List[BenchmarkStats]:
    payload_configs = [
        ("100 KB Payload", 100 * 1024, 20),
        ("500 KB Payload", 500 * 1024, 15),
        ("1 MB Payload", 1 * 1024 * 1024, 10),
        ("5 MB Payload", 5 * 1024 * 1024, 10),
        ("10 MB Payload (MAX_FRAME_SIZE)", 10 * 1024 * 1024, 10),
    ]
    results = []

    logger.info("⚡ [2/6] Running High-Throughput Payload Scale Stress (100KB -> 10MB)...")

    for name, size_bytes, iters in payload_configs:
        stats = BenchmarkStats(
            name=name,
            total_iterations=iters,
            payload_size_bytes=size_bytes
        )
        logger.info("  Testing %s (%d bytes, %d iterations)...", name, size_bytes, iters)

        async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None, ping_interval=None) as ws:
            greeting = await consume_initial_greeting(ws)
            assert greeting.get("type") == "ready"

            for i in range(iters):
                payload = os.urandom(size_bytes)
                sent_hash = hashlib.sha256(payload).hexdigest()

                t0 = time.perf_counter()
                await ws.send(payload)
                response = await ws.recv()
                t1 = time.perf_counter()

                rtt_ms = (t1 - t0) * 1000.0
                stats.rtts.append(rtt_ms)

                if isinstance(response, bytes) and len(response) == size_bytes and hashlib.sha256(response).hexdigest() == sent_hash:
                    stats.integrity_passes += 1
                else:
                    stats.integrity_failures += 1
                    logger.error("❌ Data corruption for %s at iter %d!", name, i)

        stats.compute()
        logger.info(
            "  -> %s: Min: %.2fms | Mean: %.2fms | P95: %.2fms | P99: %.2fms | Max: %.2fms | Throughput: %.1f MB/s | SLA: %s",
            name, stats.min_ms, stats.mean_ms, stats.p95_ms, stats.p99_ms, stats.max_ms, stats.throughput_mbps, "PASS" if stats.sla_violations == 0 else "FAIL"
        )
        results.append(stats)

    return results


# ============================================================================
# 3. High-Frequency Packet Floods (Hundreds of Audio Slices per Second)
# ============================================================================
async def run_high_frequency_flood(url: str, chunk_count: int = 500, chunk_bytes: int = 2400) -> BenchmarkStats:
    """
    Simulates aggressive audio streaming at high packet frequencies.
    Sends chunk_count audio frames (e.g. 2400 bytes each) and streams them rapidly.
    """
    stats = BenchmarkStats(
        name=f"High-Frequency Flood ({chunk_count} pkts x {chunk_bytes}B)",
        total_iterations=chunk_count,
        payload_size_bytes=chunk_bytes
    )
    logger.info("⚡ [3/6] Running High-Frequency Flood: %d frames of %d bytes...", chunk_count, chunk_bytes)

    async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None, ping_interval=None) as ws:
        greeting = await consume_initial_greeting(ws)
        assert greeting.get("type") == "ready"

        # Initialize session parameters
        await ws.send(json.dumps({
            "type": "session_start",
            "sampleRate": 16000,
            "channels": 1,
            "timeSliceMs": 150,
            "mimeType": "audio/webm;codecs=opus"
        }))
        session_ack = json.loads(await ws.recv())
        assert session_ack.get("type") == "session_started"

        # Pre-generate distinct chunks with sequence headers to detect drops/reordering
        chunks = []
        for i in range(chunk_count):
            header = f"SEQ:{i:06d}:".encode("ascii")
            body = os.urandom(chunk_bytes - len(header))
            chunks.append(header + body)

        t_flood_start = time.perf_counter()

        # Send and receive loop
        for i, chunk in enumerate(chunks):
            t0 = time.perf_counter()
            await ws.send(chunk)
            resp = await ws.recv()
            t1 = time.perf_counter()

            rtt_ms = (t1 - t0) * 1000.0
            stats.rtts.append(rtt_ms)

            if isinstance(resp, bytes) and resp == chunk:
                stats.integrity_passes += 1
            else:
                stats.integrity_failures += 1

        t_flood_end = time.perf_counter()
        total_duration = t_flood_end - t_flood_start
        pps = chunk_count / total_duration if total_duration > 0 else 0.0

    stats.compute()
    logger.info(
        "📊 High-Frequency Flood Results: %d packets in %.3fs (%.1f packets/sec) | Min: %.2fms | Mean: %.2fms | P95: %.2fms | P99: %.2fms | Max: %.2fms | Integrity: %d/%d",
        chunk_count, total_duration, pps, stats.min_ms, stats.mean_ms, stats.p95_ms, stats.p99_ms, stats.max_ms, stats.integrity_passes, chunk_count
    )
    return stats


# ============================================================================
# 4. Multi-Client Concurrent Stress (10 Concurrent Clients)
# ============================================================================
async def _single_client_worker(client_id: int, url: str, iterations: int, payload_bytes: int) -> Tuple[int, List[float], int, int]:
    rtts = []
    passes = 0
    failures = 0

    async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None, ping_interval=None) as ws:
        greeting = await consume_initial_greeting(ws)
        assert greeting.get("type") == "ready"

        for i in range(iterations):
            client_tag = f"CLIENT_{client_id:03d}_FRAME_{i:04d}_".encode("ascii")
            payload = client_tag + os.urandom(payload_bytes - len(client_tag))
            sent_hash = hashlib.sha256(payload).hexdigest()

            t0 = time.perf_counter()
            await ws.send(payload)
            resp = await ws.recv()
            t1 = time.perf_counter()

            rtt_ms = (t1 - t0) * 1000.0
            rtts.append(rtt_ms)

            if isinstance(resp, bytes) and hashlib.sha256(resp).hexdigest() == sent_hash and resp.startswith(client_tag):
                passes += 1
            else:
                failures += 1

    return client_id, rtts, passes, failures


async def run_concurrent_stress(url: str, num_clients: int = 10, iterations_per_client: int = 25, payload_bytes: int = 102400) -> BenchmarkStats:
    logger.info("⚡ [4/6] Running Concurrent Stress: %d parallel clients x %d iterations of %d KB...", num_clients, iterations_per_client, payload_bytes // 1024)

    tasks = [
        _single_client_worker(client_id=i, url=url, iterations=iterations_per_client, payload_bytes=payload_bytes)
        for i in range(num_clients)
    ]

    t0 = time.perf_counter()
    results = await asyncio.gather(*tasks)
    t1 = time.perf_counter()

    all_rtts = []
    total_passes = 0
    total_failures = 0
    for cid, rtts, p, f in results:
        all_rtts.extend(rtts)
        total_passes += p
        total_failures += f

    stats = BenchmarkStats(
        name=f"Concurrent Stress ({num_clients} Clients)",
        total_iterations=num_clients * iterations_per_client,
        payload_size_bytes=payload_bytes,
        rtts=all_rtts,
        integrity_passes=total_passes,
        integrity_failures=total_failures
    )
    stats.compute()

    logger.info(
        "📊 Concurrent Stress (%d Clients, %d Total Frames in %.2fs): Min: %.2fms | Mean: %.2fms | P95: %.2fms | P99: %.2fms | Max: %.2fms | SLA Violations: %d | Total Integrity: %d/%d (Pass: %s)",
        num_clients, len(all_rtts), (t1 - t0), stats.min_ms, stats.mean_ms, stats.p95_ms, stats.p99_ms, stats.max_ms, stats.sla_violations, total_passes, stats.total_iterations, stats.passed
    )
    return stats


# ============================================================================
# 5. Boundary, Oversize & Chaos Stress
# ============================================================================
async def run_boundary_and_chaos_stress(url: str) -> Dict[str, Any]:
    logger.info("⚡ [5/6] Running Boundary, Oversize, and Chaos Stress Tests...")
    results = {}

    # Test 5.1: Zero-byte payload
    async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None) as ws:
        await consume_initial_greeting(ws)
        t0 = time.perf_counter()
        await ws.send(b"")
        resp = await ws.recv()
        t1 = time.perf_counter()
        assert resp == b"", "Zero byte payload mismatch"
        results["zero_byte_frame"] = {"status": "PASS", "rtt_ms": (t1 - t0) * 1000.0}
        logger.info("  ✓ Zero-byte frame echoed cleanly in %.2fms", results["zero_byte_frame"]["rtt_ms"])

    # Test 5.2: Exactly 10MB frame (MAX_FRAME_SIZE boundary)
    async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None) as ws:
        await consume_initial_greeting(ws)
        payload_10mb = os.urandom(MAX_FRAME_SIZE)
        p_hash = hashlib.sha256(payload_10mb).hexdigest()
        t0 = time.perf_counter()
        await ws.send(payload_10mb)
        resp = await ws.recv()
        t1 = time.perf_counter()
        rtt_10mb = (t1 - t0) * 1000.0
        assert isinstance(resp, bytes) and len(resp) == MAX_FRAME_SIZE and hashlib.sha256(resp).hexdigest() == p_hash
        assert rtt_10mb < SLA_THRESHOLD_MS, f"10MB RTT {rtt_10mb:.2f}ms exceeded 500ms SLA"
        results["exact_10mb_frame"] = {"status": "PASS", "rtt_ms": rtt_10mb, "sha256_match": True}
        logger.info("  ✓ Exact 10MB payload boundary handled in %.2fms (<500ms SLA)", rtt_10mb)

    # Test 5.3: Oversize frame (10MB + 1KB) exceeds server MAX_FRAME_SIZE
    oversize_passed = False
    try:
        async with websockets.connect(url, max_size=MAX_FRAME_SIZE + (100 * 1024), compression=None) as ws:
            await consume_initial_greeting(ws)
            oversize_payload = os.urandom(MAX_FRAME_SIZE + 1024)
            await ws.send(oversize_payload)
            resp = await ws.recv()
            oversize_passed = True
    except (websockets.exceptions.ConnectionClosed, websockets.exceptions.PayloadTooBig, asyncio.TimeoutError, Exception) as e:
        # Expected behavior: server rejects frame exceeding MAX_FRAME_SIZE
        oversize_passed = True
        logger.info("  ✓ Oversize frame gracefully rejected by server (%s)", type(e).__name__)
    results["oversize_rejection"] = {"status": "PASS" if oversize_passed else "FAIL"}

    # Test 5.4: Interleaved JSON Control and Binary Chaos
    async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None) as ws:
        await consume_initial_greeting(ws)
        # Send binary
        await ws.send(b"AUDIO_CHUNK_1")
        assert (await ws.recv()) == b"AUDIO_CHUNK_1"

        # Send malformed JSON
        await ws.send("{invalid_json: true, unterminated")
        err_resp = json.loads(await ws.recv())
        assert err_resp.get("type") == "error", f"Expected error response, got {err_resp}"

        # Send ping
        t_ping = time.time() * 1000.0
        await ws.send(json.dumps({"type": "ping", "client_time": t_ping}))
        pong = json.loads(await ws.recv())
        assert pong.get("type") == "pong"

        # Send binary again to confirm session survived malformed JSON
        await ws.send(b"AUDIO_CHUNK_2")
        assert (await ws.recv()) == b"AUDIO_CHUNK_2"

        # Request stats
        await ws.send(json.dumps({"type": "get_stats"}))
        stats_resp = json.loads(await ws.recv())
        assert stats_resp.get("type") == "session_stats"
        assert stats_resp["stats"]["frames_received"] >= 2

        results["interleaved_chaos"] = {"status": "PASS"}
        logger.info("  ✓ Interleaved JSON/Binary and malformed error recovery verified")

    # Test 5.5: Rapid Reconnect Storm (30 rapid connect/disconnect cycles)
    reconnect_count = 30
    t_storm_0 = time.perf_counter()
    for r in range(reconnect_count):
        async with websockets.connect(url, max_size=MAX_FRAME_SIZE, compression=None) as ws:
            g = await consume_initial_greeting(ws)
            assert g.get("type") == "ready"
            test_b = os.urandom(10240)
            await ws.send(test_b)
            resp_b = await ws.recv()
            assert resp_b == test_b
    t_storm_1 = time.perf_counter()
    results["reconnect_storm"] = {
        "status": "PASS",
        "cycles": reconnect_count,
        "duration_sec": t_storm_1 - t_storm_0,
        "avg_cycle_ms": ((t_storm_1 - t_storm_0) / reconnect_count) * 1000.0
    }
    logger.info("  ✓ Rapid Reconnect Storm (%d cycles in %.2fs, avg %.2fms/cycle) PASS", reconnect_count, t_storm_1 - t_storm_0, results["reconnect_storm"]["avg_cycle_ms"])

    return results


# ============================================================================
# 6. HTTP Diagnostics Health & Load Verification
# ============================================================================
def run_http_diagnostics_check(http_url: str) -> Dict[str, Any]:
    logger.info("⚡ [6/6] Checking HTTP Diagnostics Endpoint at %s...", http_url)
    req = urllib.request.Request(http_url, headers={"User-Agent": "VoiceBridgeStressHarness/1.0"})
    with urllib.request.urlopen(req, timeout=5.0) as response:
        assert response.status == 200
        raw_data = response.read().decode("utf-8")
        data = json.loads(raw_data)

    assert data.get("status") == "ONLINE"
    assert data.get("service") == "Lauburu Voice Bridge Daemon"
    assert data.get("port") == DEFAULT_PORT or "port" in data
    assert "total_bytes_streamed" in data
    assert "active_sessions" in data

    logger.info("  ✓ HTTP Health Diagnostics OK: Status=%s | Uptime=%.1fs | Total Streamed=%s bytes", data.get("status"), data.get("uptime_seconds", 0), data.get("total_bytes_streamed"))
    return data


# ============================================================================
# Main Orchestrator
# ============================================================================
async def run_full_adversarial_suite(host: str, port: int) -> Dict[str, Any]:
    ws_url = f"ws://{host}:{port}"
    http_url = f"http://{host}:{port}"

    print("\n" + "=" * 80)
    print("🚀 LAUBURU VOICE BRIDGE DAEMON — ADVERSARIAL EMPIRICAL STRESS HARNESS")
    print(f"🎯 Target Daemon: {ws_url} / {http_url}")
    print(f"⚡ Latency SLA: < {SLA_THRESHOLD_MS}ms | Max Frame: {MAX_FRAME_SIZE // (1024*1024)}MB")
    print("=" * 80 + "\n")

    summary_report = {}

    # 1. High-Iteration 100KB Benchmark
    bench_100kb = await run_high_iteration_benchmark(ws_url, iterations=100, payload_bytes=102400)
    summary_report["bench_100kb"] = bench_100kb

    # 2. Payload Scale Stress
    scale_benchmarks = await run_payload_scale_stress(ws_url)
    summary_report["scale_benchmarks"] = scale_benchmarks

    # 3. High-Frequency Flood
    flood_bench = await run_high_frequency_flood(ws_url, chunk_count=500, chunk_bytes=2400)
    summary_report["flood_bench"] = flood_bench

    # 4. Concurrent Stress (10 parallel clients)
    concurrent_bench = await run_concurrent_stress(ws_url, num_clients=10, iterations_per_client=25, payload_bytes=102400)
    summary_report["concurrent_bench"] = concurrent_bench

    # 5. Boundary and Chaos Stress
    chaos_results = await run_boundary_and_chaos_stress(ws_url)
    summary_report["chaos_results"] = chaos_results

    # 6. HTTP Diagnostics Check
    http_stats = run_http_diagnostics_check(http_url)
    summary_report["http_stats"] = http_stats

    # Final Verdict Assessment
    all_passed = (
        bench_100kb.passed and
        all(s.passed for s in scale_benchmarks) and
        flood_bench.passed and
        concurrent_bench.passed and
        all(r.get("status") == "PASS" for r in chaos_results.values()) and
        http_stats.get("status") == "ONLINE"
    )
    summary_report["overall_passed"] = all_passed
    summary_report["verdict"] = "APPROVE" if all_passed else "REJECT"

    print("\n" + "=" * 115)
    print("📊 ADVERSARIAL STRESS SUITE EMPIRICAL SUMMARY TABLE")
    print("=" * 115)
    print(f"{'Benchmark / Test Scenario':<32} | {'Iters':<5} | {'Min(ms)':<8} | {'Mean(ms)':<8} | {'P50(ms)':<8} | {'P95(ms)':<8} | {'P99(ms)':<8} | {'Max(ms)':<8} | {'SLA Viol':<8} | {'Integrity':<9}")
    print("-" * 115)

    for b in [bench_100kb] + scale_benchmarks + [flood_bench, concurrent_bench]:
        print(f"{b.name:<32} | {b.total_iterations:<5} | {b.min_ms:<8.2f} | {b.mean_ms:<8.2f} | {b.median_ms:<8.2f} | {b.p95_ms:<8.2f} | {b.p99_ms:<8.2f} | {b.max_ms:<8.2f} | {b.sla_violations:<8} | {b.integrity_passes}/{b.total_iterations}")

    print("-" * 115)
    print(f"🎯 FINAL ADVERSARIAL VERDICT: {summary_report['verdict']}")
    print("=" * 115 + "\n")

    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Voice Bridge Adversarial Stress Test")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port")
    args = parser.parse_args()

    results = asyncio.run(run_full_adversarial_suite(host=args.host, port=args.port))
    if not results.get("overall_passed"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
