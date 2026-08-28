#!/usr/bin/env python3
"""
Lauburu Voice Bridge Daemon: Challenger 2 Empirical Adversarial Stress Harness
=============================================================================

Mission: Adversarially probe edge cases, concurrency, fault tolerance, and network anomalies
on `voice_bridge_daemon.py`:

1. Concurrent Client Multiplexing:
   - Connect 25 concurrent WebSocket clients simultaneously streaming 100KB binary audio chunks.
   - Verify zero cross-talk, no buffer corruption, 100% SHA-256 fidelity, and all RTTs < 500ms SLA.
2. Connection Churn & Abrupt Disconnects:
   - Rapid connect/disconnect cycles and abrupt socket teardowns mid-transmission.
   - Verify daemon gracefully cleans up sessions without crashing, leaking descriptors or leaving zombie tasks.
3. Protocol Fuzzing:
   - Send malformed JSON, non-dict JSON (lists, ints, strings), malformed fields,
     interleaved text/binary frames, zero-byte frames, large payload boundaries, oversized frames.
   - Verify daemon rejects or handles them gracefully without unhandled exceptions.
4. HTTP Diagnostic Verification Under Heavy Load:
   - Probe HTTP GET `/` and GET `/health` concurrently during heavy background streaming load.
   - Verify 200 OK, valid JSON telemetry, and non-blocking sub-100ms HTTP response latency.
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

import pytest
import websockets

# Add source and test paths
HUB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(HUB_DIR, "src")
for p in (HUB_DIR, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from voice_bridge_daemon import run_server, MAX_FRAME_SIZE, session_manager
from test_voice_bridge import EphemeralDaemonServer, is_port_open, find_free_port

logger = logging.getLogger("Challenger2VoiceBridgeStress")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

SLA_THRESHOLD_MS = 500.0


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@pytest.fixture(scope="module")
def voice_server():
    """Module-scoped fixture for pytest runner providing daemon target."""
    default_port = int(os.environ.get("VOICE_BRIDGE_PORT", 8765))
    default_host = "127.0.0.1"

    if is_port_open(default_host, default_port):
        ws_url = f"ws://{default_host}:{default_port}"
        http_url = f"http://{default_host}:{default_port}"
        yield {"ws_url": ws_url, "http_url": http_url, "port": default_port, "host": default_host}
    else:
        free_port = find_free_port()
        server = EphemeralDaemonServer(host=default_host, port=free_port)
        server.start()
        yield {
            "ws_url": server.url,
            "http_url": server.http_url,
            "port": free_port,
            "host": default_host
        }
        server.stop()


# ============================================================================
# 1. CONCURRENT CLIENT MULTIPLEXING (25+ Concurrent Clients, 100KB Chunks)
# ============================================================================

async def run_concurrent_multiplexing_probe(ws_url: str, client_count: int = 25, chunks_per_client: int = 10) -> ScenarioResult:
    """
    Connects client_count concurrent WebSocket clients simultaneously streaming 100KB binary chunks.
    Verifies zero cross-talk, zero corruption, 100% SHA-256 fidelity, and RTT < 500ms.
    """
    chunk_size = 100 * 1024  # 102,400 bytes
    client_results: Dict[int, Dict[str, Any]] = {}

    async def single_client_worker(client_id: int):
        rtts: List[float] = []
        fidelity_pass = True
        cross_talk_detected = False

        async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE, ping_interval=None) as ws:
            # Consume ready greeting
            greeting_raw = await ws.recv()
            greeting = json.loads(greeting_raw)
            if greeting.get("type") != "ready":
                raise ValueError(f"Client {client_id}: unexpected greeting {greeting}")

            for chunk_idx in range(chunks_per_client):
                tag = f"CID:{client_id:04d}:CHUNK:{chunk_idx:04d}:".encode("ascii")
                payload = tag + os.urandom(chunk_size - len(tag))
                sent_sha = hashlib.sha256(payload).hexdigest()

                t0 = time.perf_counter()
                await ws.send(payload)
                resp = await ws.recv()
                t1 = time.perf_counter()

                rtt_ms = (t1 - t0) * 1000.0
                rtts.append(rtt_ms)

                if not isinstance(resp, bytes):
                    fidelity_pass = False
                    break
                if not resp.startswith(tag):
                    cross_talk_detected = True
                    fidelity_pass = False
                    break
                if hashlib.sha256(resp).hexdigest() != sent_sha or resp != payload:
                    fidelity_pass = False
                    break

        client_results[client_id] = {
            "rtts": rtts,
            "fidelity_pass": fidelity_pass,
            "cross_talk_detected": cross_talk_detected,
            "min_rtt": min(rtts) if rtts else 0.0,
            "avg_rtt": sum(rtts) / len(rtts) if rtts else 0.0,
            "max_rtt": max(rtts) if rtts else 0.0,
        }

    t_start = time.perf_counter()
    tasks = [asyncio.create_task(single_client_worker(i)) for i in range(client_count)]
    await asyncio.gather(*tasks)
    t_end = time.perf_counter()

    all_rtts: List[float] = []
    cross_talk_count = 0
    corrupted_count = 0
    sla_violations = 0

    for cid, cr in client_results.items():
        all_rtts.extend(cr["rtts"])
        if cr["cross_talk_detected"]:
            cross_talk_count += 1
        if not cr["fidelity_pass"]:
            corrupted_count += 1
        for r in cr["rtts"]:
            if r >= SLA_THRESHOLD_MS:
                sla_violations += 1

    total_chunks = len(all_rtts)
    avg_rtt = sum(all_rtts) / total_chunks if total_chunks else 0.0
    sorted_rtts = sorted(all_rtts)
    p95_rtt = sorted_rtts[int(math.ceil(0.95 * total_chunks)) - 1] if total_chunks else 0.0
    p99_rtt = sorted_rtts[int(math.ceil(0.99 * total_chunks)) - 1] if total_chunks else 0.0
    min_rtt = min(all_rtts) if all_rtts else 0.0
    max_rtt = max(all_rtts) if all_rtts else 0.0
    total_bytes_streamed = total_chunks * chunk_size * 2
    duration_s = t_end - t_start
    throughput_mb_s = (total_bytes_streamed / (1024 * 1024)) / duration_s if duration_s > 0 else 0.0

    passed = (cross_talk_count == 0) and (corrupted_count == 0) and (sla_violations == 0) and (total_chunks == client_count * chunks_per_client)

    return ScenarioResult(
        name="Concurrent Client Multiplexing (25 Clients x 10 Chunks @ 100KB)",
        passed=passed,
        details={
            "client_count": client_count,
            "chunks_per_client": chunks_per_client,
            "total_chunks": total_chunks,
            "total_bytes_mb": total_bytes_streamed / (1024 * 1024),
            "duration_seconds": round(duration_s, 3),
            "throughput_mb_s": round(throughput_mb_s, 2),
            "min_rtt_ms": round(min_rtt, 3),
            "avg_rtt_ms": round(avg_rtt, 3),
            "p95_rtt_ms": round(p95_rtt, 3),
            "p99_rtt_ms": round(p99_rtt, 3),
            "max_rtt_ms": round(max_rtt, 3),
            "cross_talk_count": cross_talk_count,
            "corrupted_count": corrupted_count,
            "sla_violations": sla_violations,
        },
        error_message=None if passed else f"Cross-talk: {cross_talk_count}, Corrupted: {corrupted_count}, SLA violations: {sla_violations}"
    )


# ============================================================================
# 2. CONNECTION CHURN & ABRUPT DISCONNECTS
# ============================================================================

async def run_connection_churn_and_abrupt_disconnects(ws_url: str, http_url: str) -> ScenarioResult:
    """
    Tests rapid connect/disconnect churn and abrupt TCP socket teardowns mid-transmission.
    Verifies daemon cleans up sessions, does not crash or leak active sessions.
    """
    # Baseline active sessions
    req = urllib.request.Request(f"{http_url}/health", headers={"User-Agent": "Challenger2Probe"})
    with urllib.request.urlopen(req, timeout=3.0) as r:
        baseline_stats = json.loads(r.read().decode("utf-8"))
    baseline_active = baseline_stats.get("active_sessions", 0)

    # 1. Rapid Churn: 40 clients connect, send small frame, and disconnect immediately
    churn_count = 40

    async def single_churn(idx: int):
        async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
            _ = await ws.recv()
            payload = os.urandom(2048)
            await ws.send(payload)
            resp = await ws.recv()
            assert resp == payload
            await ws.close(code=1000)

    t0_churn = time.perf_counter()
    churn_tasks = [asyncio.create_task(single_churn(i)) for i in range(churn_count)]
    await asyncio.gather(*churn_tasks)
    t1_churn = time.perf_counter()

    # 2. Abrupt Disconnects: 15 clients start streaming 200KB frames and abruptly terminate underlying socket mid-flight
    abrupt_count = 15

    async def single_abrupt(idx: int):
        try:
            ws = await websockets.connect(ws_url, max_size=MAX_FRAME_SIZE)
            _ = await ws.recv()
            payload = os.urandom(200 * 1024)
            # Send payload without awaiting echo, then abruptly close transport directly
            await ws.send(payload)
            # Force low-level socket close without WebSocket close handshake
            if hasattr(ws, "transport") and ws.transport:
                ws.transport.close()
            elif hasattr(ws, "protocol") and hasattr(ws.protocol, "transport"):
                ws.protocol.transport.close()
            else:
                await ws.close(code=1006)  # Abnormal closure
        except Exception:
            pass

    abrupt_tasks = [asyncio.create_task(single_abrupt(i)) for i in range(abrupt_count)]
    await asyncio.gather(*abrupt_tasks, return_exceptions=True)

    # Allow daemon async cleanup loop a brief moment to process disconnects
    await asyncio.sleep(0.3)

    # Verify session count returned to baseline
    with urllib.request.urlopen(req, timeout=3.0) as r:
        after_stats = json.loads(r.read().decode("utf-8"))
    after_active = after_stats.get("active_sessions", 0)

    # Verify daemon is fully healthy and accepting new traffic
    verification_passed = False
    async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
        _ = await ws.recv()
        test_payload = os.urandom(100 * 1024)
        t0 = time.perf_counter()
        await ws.send(test_payload)
        resp = await ws.recv()
        t1 = time.perf_counter()
        rtt = (t1 - t0) * 1000.0
        if resp == test_payload and rtt < SLA_THRESHOLD_MS:
            verification_passed = True

    passed = (after_active == baseline_active) and verification_passed

    return ScenarioResult(
        name="Connection Churn (40 clients) & Abrupt Disconnects (15 mid-flight teardowns)",
        passed=passed,
        details={
            "churn_count": churn_count,
            "churn_duration_s": round(t1_churn - t0_churn, 3),
            "abrupt_disconnect_count": abrupt_count,
            "baseline_active_sessions": baseline_active,
            "after_active_sessions": after_active,
            "post_churn_rtt_ms": round(rtt, 3) if verification_passed else None,
            "daemon_healthy": verification_passed
        },
        error_message=None if passed else f"Active sessions leak (before={baseline_active}, after={after_active}) or post-churn echo failed"
    )


# ============================================================================
# 3. PROTOCOL FUZZING & ERROR RECOVERY
# ============================================================================

async def run_protocol_fuzzing_probe(ws_url: str) -> ScenarioResult:
    """
    Probes protocol edge cases: malformed JSON syntax, type coercion anomalies,
    zero-byte frames, interleaved text/binary, 5MB large payload, oversized frame rejection,
    unknown control frames.
    """
    fuzz_results: Dict[str, Any] = {}
    fuzz_anomalies: List[str] = []

    # 3.1: Zero-byte binary frame
    async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
        _ = await ws.recv()
        t0 = time.perf_counter()
        await ws.send(b"")
        resp = await ws.recv()
        t1 = time.perf_counter()
        fuzz_results["zero_byte_frame"] = (resp == b"") and ((t1 - t0) * 1000.0 < SLA_THRESHOLD_MS)

    # 3.2: Malformed Syntax JSON strings
    malformed_syntax_payloads = [
        "{broken json: true",
        "{{{{{{nested unclosed",
        "\x00\x01\x02\x03not_valid_utf8_json",
        "",
    ]
    malformed_syntax_pass = True
    async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
        _ = await ws.recv()
        for mf in malformed_syntax_payloads:
            try:
                await ws.send(mf)
                resp = await ws.recv()
                if isinstance(resp, str):
                    resp_json = json.loads(resp)
                    if resp_json.get("type") != "error":
                        malformed_syntax_pass = False
                else:
                    malformed_syntax_pass = False
            except Exception as e:
                malformed_syntax_pass = False
                fuzz_anomalies.append(f"Syntax fuzzing threw exception: {e}")

        # Confirm session is still alive and responds to 100KB binary echo
        test_chunk = os.urandom(102400)
        await ws.send(test_chunk)
        echo = await ws.recv()
        if echo != test_chunk:
            malformed_syntax_pass = False

    fuzz_results["malformed_syntax_recovery"] = malformed_syntax_pass

    # 3.3: Type Coercion / Non-Dict JSON Schema Fuzzing
    # Test whether non-dict JSON or invalid type fields cause graceful error or session termination
    type_fuzz_payloads = [
        ('{"type": "session_start", "sampleRate": "NOT_AN_INT"}', "invalid int in session_start"),
        ('{"type": "ping", "client_time": "invalid_time_string"}', "string client_time in ping"),
        ('[]', "list root in JSON"),
        ('"pure string not object"', "string root in JSON"),
        ('123456', "int root in JSON"),
        ('null', "null root in JSON"),
    ]
    
    type_fuzz_passed_count = 0
    for tf_payload, tf_desc in type_fuzz_payloads:
        try:
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                _ = await ws.recv()
                await ws.send(tf_payload)
                resp = await ws.recv()
                if isinstance(resp, str):
                    type_fuzz_passed_count += 1
                else:
                    fuzz_anomalies.append(f"Payload '{tf_desc}' returned non-string response: {type(resp)}")
        except Exception as e:
            fuzz_anomalies.append(f"Payload '{tf_desc}' triggered session termination: {type(e).__name__}: {e}")

    fuzz_results["type_fuzz_passed_count"] = type_fuzz_passed_count
    fuzz_results["type_fuzz_total"] = len(type_fuzz_payloads)
    fuzz_results["type_fuzz_anomalies"] = fuzz_anomalies

    # 3.4: Interleaved JSON and Binary Frames
    interleave_passed = True
    async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
        _ = await ws.recv()
        for cycle in range(5):
            # Binary frame
            bin_data = os.urandom(16384)
            await ws.send(bin_data)
            if (await ws.recv()) != bin_data:
                interleave_passed = False

            # JSON ping
            t_now = time.time() * 1000.0
            await ws.send(json.dumps({"type": "ping", "client_time": t_now}))
            pong = json.loads(await ws.recv())
            if pong.get("type") != "pong" or pong.get("client_time") != t_now:
                interleave_passed = False

            # JSON get_stats
            await ws.send(json.dumps({"type": "get_stats"}))
            stats_msg = json.loads(await ws.recv())
            if stats_msg.get("type") != "session_stats":
                interleave_passed = False

    fuzz_results["interleaved_frames"] = interleave_passed

    # 3.5: 5MB Large High-Def Audio Buffer (Within MAX_FRAME_SIZE)
    large_5mb_passed = False
    async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
        _ = await ws.recv()
        large_5mb = os.urandom(5 * 1024 * 1024)
        large_sha = hashlib.sha256(large_5mb).hexdigest()
        t0 = time.perf_counter()
        await ws.send(large_5mb)
        resp_5mb = await ws.recv()
        t1 = time.perf_counter()
        rtt_5mb = (t1 - t0) * 1000.0
        if isinstance(resp_5mb, bytes) and hashlib.sha256(resp_5mb).hexdigest() == large_sha and rtt_5mb < SLA_THRESHOLD_MS:
            large_5mb_passed = True
        fuzz_results["large_5mb_rtt_ms"] = round(rtt_5mb, 2)
    fuzz_results["large_5mb_frame"] = large_5mb_passed

    # 3.6: Oversized Frame (10MB + 1MB) Rejection
    oversize_rejected = False
    try:
        ws_over = await websockets.connect(ws_url, max_size=MAX_FRAME_SIZE + (2 * 1024 * 1024))
        try:
            _ = await ws_over.recv()
            oversized_payload = os.urandom(11 * 1024 * 1024)
            await ws_over.send(oversized_payload)
            _ = await ws_over.recv()
        except Exception:
            oversize_rejected = True
        finally:
            try:
                await ws_over.close()
            except Exception:
                pass
    except (websockets.exceptions.ConnectionClosed, websockets.exceptions.PayloadTooBig, asyncio.TimeoutError, Exception):
        oversize_rejected = True
    fuzz_results["oversize_rejected"] = oversize_rejected

    # 3.7: Unknown Control Opcode Handling
    unknown_ack_passed = False
    async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
        _ = await ws.recv()
        await ws.send(json.dumps({"type": "fuzz_custom_opcode_xyz", "payload": [1, 2, 3]}))
        ack_resp = json.loads(await ws.recv())
        if ack_resp.get("type") == "ack" and ack_resp.get("received_type") == "fuzz_custom_opcode_xyz":
            unknown_ack_passed = True
    fuzz_results["unknown_opcode_ack"] = unknown_ack_passed

    # Assess whether core protocol fuzzing and boundary criteria are met
    core_fuzz_passed = (
        fuzz_results["zero_byte_frame"] is True and
        fuzz_results["malformed_syntax_recovery"] is True and
        fuzz_results["interleaved_frames"] is True and
        fuzz_results["large_5mb_frame"] is True and
        fuzz_results["oversize_rejected"] is True and
        fuzz_results["unknown_opcode_ack"] is True
    )

    return ScenarioResult(
        name="Protocol Fuzzing & Boundary Stress",
        passed=core_fuzz_passed,
        details=fuzz_results,
        error_message=None if core_fuzz_passed else f"Core fuzzing failed: {fuzz_results}"
    )


# ============================================================================
# 4. HTTP DIAGNOSTIC VERIFICATION UNDER HEAVY STREAMING LOAD
# ============================================================================

async def run_http_diagnostic_under_load_probe(ws_url: str, http_url: str) -> ScenarioResult:
    """
    Probes HTTP GET `/` and `/health` endpoints concurrently while background clients
    are actively streaming high-throughput binary audio chunks.
    Verifies 200 OK, valid JSON metrics, and sub-100ms HTTP latency.
    """
    background_clients = 8
    stop_event = asyncio.Event()
    chunks_streamed = 0

    async def background_streamer(cid: int):
        nonlocal chunks_streamed
        async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE, ping_interval=None) as ws:
            _ = await ws.recv()
            chunk = os.urandom(32768)  # 32KB
            while not stop_event.is_set():
                await ws.send(chunk)
                _ = await ws.recv()
                chunks_streamed += 1
                await asyncio.sleep(0.01)

    # Launch background streamers
    streamer_tasks = [asyncio.create_task(background_streamer(i)) for i in range(background_clients)]
    await asyncio.sleep(0.2)  # Allow background load to spin up

    http_rtts: List[float] = []
    http_success_count = 0
    total_http_requests = 50
    endpoints = ["/", "/health", "/status", "/ws/voice"]

    def probe_http_sync(path: str) -> Tuple[bool, float, Optional[Dict[str, Any]]]:
        url = f"{http_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "Challenger2LoadProbe/1.0"})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                status = resp.status
                data = json.loads(resp.read().decode("utf-8"))
                t1 = time.perf_counter()
                rtt_ms = (t1 - t0) * 1000.0
                is_valid = (
                    status == 200 and
                    data.get("status") == "ONLINE" and
                    data.get("active_sessions", 0) >= background_clients
                )
                return is_valid, rtt_ms, data
        except Exception as e:
            t1 = time.perf_counter()
            return False, (t1 - t0) * 1000.0, None

    # Perform concurrent HTTP requests against daemon under load
    loop = asyncio.get_running_loop()
    http_tasks = []
    for i in range(total_http_requests):
        path = endpoints[i % len(endpoints)]
        http_tasks.append(loop.run_in_executor(None, probe_http_sync, path))

    results = await asyncio.gather(*http_tasks)

    # Teardown background streamers
    stop_event.set()
    await asyncio.gather(*streamer_tasks, return_exceptions=True)

    for is_ok, rtt, data in results:
        http_rtts.append(rtt)
        if is_ok:
            http_success_count += 1

    avg_http_rtt = sum(http_rtts) / len(http_rtts) if http_rtts else 0.0
    max_http_rtt = max(http_rtts) if http_rtts else 0.0
    p95_http_rtt = sorted(http_rtts)[int(math.ceil(0.95 * len(http_rtts))) - 1] if http_rtts else 0.0

    passed = (http_success_count == total_http_requests) and (avg_http_rtt < 100.0)

    return ScenarioResult(
        name=f"HTTP Diagnostics Under Load ({total_http_requests} concurrent HTTP probes during {background_clients} streaming clients)",
        passed=passed,
        details={
            "total_http_requests": total_http_requests,
            "http_success_count": http_success_count,
            "background_clients": background_clients,
            "background_chunks_streamed": chunks_streamed,
            "avg_http_rtt_ms": round(avg_http_rtt, 3),
            "p95_http_rtt_ms": round(p95_http_rtt, 3),
            "max_http_rtt_ms": round(max_http_rtt, 3),
        },
        error_message=None if passed else f"HTTP success rate: {http_success_count}/{total_http_requests}, avg RTT: {avg_http_rtt:.2f}ms"
    )


# ============================================================================
# Pytest Integration Test Suite
# ============================================================================

class TestChallenger2AdversarialSuite:
    """Pytest suite encapsulating all 4 adversarial challenger requirements."""

    def test_challenger2_req1_concurrent_client_multiplexing(self, voice_server):
        """Req 1: 25 concurrent clients streaming 100KB binary chunks with zero cross-talk and <500ms RTT."""
        res = asyncio.run(run_concurrent_multiplexing_probe(voice_server["ws_url"], client_count=25, chunks_per_client=10))
        logger.info("Req 1 Result: %s | Details: %s", "PASS" if res.passed else "FAIL", res.details)
        assert res.passed is True, f"Req 1 Failure: {res.error_message}"
        assert res.details["cross_talk_count"] == 0
        assert res.details["corrupted_count"] == 0
        assert res.details["sla_violations"] == 0
        assert res.details["avg_rtt_ms"] < 500.0

    def test_challenger2_req2_churn_and_abrupt_disconnects(self, voice_server):
        """Req 2: 40 connect/disconnect cycles + 15 abrupt TCP teardowns mid-transmission without leaks or crashes."""
        res = asyncio.run(run_connection_churn_and_abrupt_disconnects(voice_server["ws_url"], voice_server["http_url"]))
        logger.info("Req 2 Result: %s | Details: %s", "PASS" if res.passed else "FAIL", res.details)
        assert res.passed is True, f"Req 2 Failure: {res.error_message}"
        assert res.details["daemon_healthy"] is True

    def test_challenger2_req3_protocol_fuzzing_and_boundaries(self, voice_server):
        """Req 3: Malformed JSON, 0-byte frames, 5MB payload, oversize rejection, interleaved frames."""
        res = asyncio.run(run_protocol_fuzzing_probe(voice_server["ws_url"]))
        logger.info("Req 3 Result: %s | Details: %s", "PASS" if res.passed else "FAIL", res.details)
        assert res.passed is True, f"Req 3 Failure: {res.error_message}"
        assert res.details["zero_byte_frame"] is True
        assert res.details["malformed_syntax_recovery"] is True
        assert res.details["interleaved_frames"] is True
        assert res.details["large_5mb_frame"] is True
        assert res.details["oversize_rejected"] is True

    def test_challenger2_req4_http_diagnostics_under_load(self, voice_server):
        """Req 4: 50 concurrent HTTP probes against /, /health, /status during heavy streaming load."""
        res = asyncio.run(run_http_diagnostic_under_load_probe(voice_server["ws_url"], voice_server["http_url"]))
        logger.info("Req 4 Result: %s | Details: %s", "PASS" if res.passed else "FAIL", res.details)
        assert res.passed is True, f"Req 4 Failure: {res.error_message}"
        assert res.details["http_success_count"] == 50
        assert res.details["avg_http_rtt_ms"] < 100.0


# ============================================================================
# Standalone CLI Entrypoint
# ============================================================================

async def run_standalone_challenger2_audit(host: str = "127.0.0.1", port: Optional[int] = None) -> Dict[str, Any]:
    port = port or find_free_port()
    ws_url = f"ws://{host}:{port}"
    http_url = f"http://{host}:{port}"

    print("\n" + "=" * 84)
    print("🛡️  CHALLENGER 2: ADVERSARIAL STRESS & FAULT TOLERANCE AUDIT")
    print(f"🎯 Target Daemon: {ws_url} / {http_url}")
    print(f"⚡ Latency SLA: < {SLA_THRESHOLD_MS}ms | Max Frame Size: {MAX_FRAME_SIZE // (1024*1024)}MB")
    print("=" * 84 + "\n")

    server = EphemeralDaemonServer(host=host, port=port)
    server.start()

    results: List[ScenarioResult] = []

    try:
        # Probe 1: Concurrent Multiplexing
        print("▶ [1/4] Probing Concurrent Client Multiplexing (25 clients x 10 chunks of 100KB)...")
        r1 = await run_concurrent_multiplexing_probe(ws_url, client_count=25, chunks_per_client=10)
        results.append(r1)
        print(f"    Status: {'✅ PASS' if r1.passed else '❌ FAIL'} | Avg RTT: {r1.details['avg_rtt_ms']}ms | P95: {r1.details['p95_rtt_ms']}ms | Throughput: {r1.details['throughput_mb_s']} MB/s | Cross-talk: {r1.details['cross_talk_count']}")

        # Probe 2: Connection Churn & Abrupt Disconnects
        print("▶ [2/4] Probing Connection Churn & Abrupt Socket Teardowns...")
        r2 = await run_connection_churn_and_abrupt_disconnects(ws_url, http_url)
        results.append(r2)
        print(f"    Status: {'✅ PASS' if r2.passed else '❌ FAIL'} | Churn: {r2.details['churn_count']} | Abrupt Teardowns: {r2.details['abrupt_disconnect_count']} | Active Sessions Post-Test: {r2.details['after_active_sessions']}")

        # Probe 3: Protocol Fuzzing & Boundary Stress
        print("▶ [3/4] Probing Protocol Fuzzing, Boundary Frames & Malformed Payloads...")
        r3 = await run_protocol_fuzzing_probe(ws_url)
        results.append(r3)
        print(f"    Status: {'✅ PASS' if r3.passed else '❌ FAIL'} | Zero-Byte: {r3.details['zero_byte_frame']} | Malformed Syntax Recovery: {r3.details['malformed_syntax_recovery']} | 5MB RTT: {r3.details.get('large_5mb_rtt_ms')}ms | Oversize Rejected: {r3.details['oversize_rejected']}")

        # Probe 4: HTTP Diagnostics Under Heavy Load
        print("▶ [4/4] Probing HTTP Diagnostics Under Heavy Background Audio Streaming...")
        r4 = await run_http_diagnostic_under_load_probe(ws_url, http_url)
        results.append(r4)
        print(f"    Status: {'✅ PASS' if r4.passed else '❌ FAIL'} | Success: {r4.details['http_success_count']}/{r4.details['total_http_requests']} | Avg HTTP RTT: {r4.details['avg_http_rtt_ms']}ms | Background Chunks: {r4.details['background_chunks_streamed']}")

    finally:
        server.stop()

    all_passed = all(r.passed for r in results)
    verdict = "APPROVE" if all_passed else "REJECT"

    print("\n" + "=" * 84)
    print("📊 CHALLENGER 2 EMPIRICAL AUDIT RESULTS TABLE")
    print("=" * 84)
    for idx, r in enumerate(results, 1):
        status_icon = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"[{idx}] {r.name:<68} | {status_icon}")
    print("-" * 84)
    print(f"🎯 FINAL EMPIRICAL CHALLENGER VERDICT: {verdict}")
    print("=" * 84 + "\n")

    return {
        "all_passed": all_passed,
        "verdict": verdict,
        "results": [
            {"name": r.name, "passed": r.passed, "details": r.details, "error": r.error_message}
            for r in results
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Challenger 2 Voice Bridge Adversarial Stress Suite")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface")
    parser.add_argument("--port", type=int, default=None, help="Port (defaults to ephemeral)")
    args = parser.parse_args()

    report = asyncio.run(run_standalone_challenger2_audit(host=args.host, port=args.port))
    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
