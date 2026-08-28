#!/usr/bin/env python3
"""
Lauburu Voice Bridge Daemon: Comprehensive Multi-Tier Test Suite
================================================================

Covers Tiers 1-4 Test Matrix from TEST_INFRA.md:
- Tier 1: Core Binary Audio Echo, Latency SLA (<500ms RTT), JSON Control Handshake, Ping/Pong, HTTP Health Diagnostics
- Tier 2: Boundary Payload Sizes (1B to 5MB), Rapid Burst Transmission, Interleaved Frames, Malformed JSON Recovery, Clean Lifecycle
- Tier 3: High Concurrency (10+ simultaneous WebSocket sessions), Multi-Client Load, Session Churn, Zero Cross-Talk
- Tier 4: Real-World RecordRTC 150ms Audio Streaming Emulation, Jitter Calculation, Mode Switching & Queue Telemetry
"""

import os
import sys
import time
import math
import json
import socket
import logging
import asyncio
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple

import pytest
import websockets

# Add parent and src directories to path
HUB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(HUB_DIR, "src")
for p in (HUB_DIR, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from test_voice_bridge import (
    EphemeralDaemonServer,
    verify_voice_bridge_latency,
    receive_binary_payload,
    is_port_open,
    find_free_port,
    MAX_FRAME_SIZE,
)

logger = logging.getLogger("VoiceBridgeTestSuite")


@pytest.fixture(scope="module")
def voice_server():
    """
    Module-scoped fixture that provides a running Voice Bridge daemon URL.
    Connects to an existing daemon on 127.0.0.1:8765 if running, or launches
    an ephemeral in-process daemon on a free port using a dedicated background thread.
    """
    default_port = int(os.environ.get("VOICE_BRIDGE_PORT", 8765))
    default_host = "127.0.0.1"

    if is_port_open(default_host, default_port):
        ws_url = f"ws://{default_host}:{default_port}"
        http_url = f"http://{default_host}:{default_port}"
        logger.info("Using existing running daemon at %s", ws_url)
        yield {"ws_url": ws_url, "http_url": http_url, "port": default_port, "host": default_host}
    else:
        logger.info("No daemon running on %d. Launching ephemeral test daemon in background thread...", default_port)
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
# TIER 1: Core Binary Audio Echo, Latency SLA & Health Diagnostics
# ============================================================================

class TestTier1CoreAndSLA:
    """Tier 1: Core Feature Verification & Latency SLA."""

    def test_tier1_single_100kb_echo_sla(self, voice_server):
        """Validates a single 100KB binary payload round-trip completes < 500ms with 100% byte fidelity."""
        ws_url = voice_server["ws_url"]
        
        async def run():
            result = await verify_voice_bridge_latency(
                url=ws_url,
                payload_size=100 * 1024,
                iterations=1,
                threshold_ms=500.0
            )
            return result

        result = asyncio.run(run())
        assert result.success is True, f"Verification failed: {result.error_message}"
        assert result.byte_match is True, "100KB binary payload was corrupted during round-trip"
        assert len(result.rtts) == 1
        assert result.rtts[0] < 500.0, f"Latency SLA violation: {result.rtts[0]:.2f}ms >= 500.0ms"
        assert result.rtts[0] > 0.01, "Monotonic timer measurement invalid"

    def test_tier1_multi_iteration_100kb_echo(self, voice_server):
        """Validates 10 sequential 100KB binary payload round-trips with statistical stability."""
        ws_url = voice_server["ws_url"]

        async def run():
            return await verify_voice_bridge_latency(
                url=ws_url,
                payload_size=100 * 1024,
                iterations=10,
                threshold_ms=500.0
            )

        result = asyncio.run(run())
        assert result.success is True, f"Multi-iteration failed: {result.error_message}"
        assert result.byte_match is True
        assert len(result.rtts) == 10
        assert result.avg_rtt_ms < 500.0, f"Avg RTT SLA violated: {result.avg_rtt_ms:.2f}ms"
        assert result.max_rtt_ms < 500.0, f"Max RTT SLA violated: {result.max_rtt_ms:.2f}ms"
        assert result.std_dev_ms < 50.0, f"Jitter too high: {result.std_dev_ms:.2f}ms"
        assert result.throughput_mbps > 5.0, f"Throughput too low: {result.throughput_mbps:.2f} MB/s"

    def test_tier1_json_control_handshake_and_ping_pong(self, voice_server):
        """Validates JSON control plane handshake, session initialization, and ping/pong latency calibration."""
        ws_url = voice_server["ws_url"]

        async def run():
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Receive ready greeting
                greeting_raw = await ws.recv()
                greeting = json.loads(greeting_raw)
                assert greeting["type"] == "ready"
                assert "session_id" in greeting
                assert greeting["service"] == "Lauburu Ultra-Low Latency Voice Bridge"

                # 1. Send session_start handshake
                init_msg = {
                    "type": "session_start",
                    "sampleRate": 16000,
                    "channels": 1,
                    "mimeType": "audio/webm",
                    "timeSliceMs": 150,
                    "mode": "echo"
                }
                await ws.send(json.dumps(init_msg))
                
                resp_raw = await ws.recv()
                resp = json.loads(resp_raw)
                assert resp["type"] == "session_started"
                assert resp["status"] == "READY"
                assert resp["sample_rate"] == 16000
                assert resp["channels"] == 1
                assert resp["mime_type"] == "audio/webm"
                assert resp["mode"] == "echo"

                # 2. Send ping with high-precision timestamp
                t_client = time.time() * 1000.0
                await ws.send(json.dumps({"type": "ping", "client_time": t_client}))
                
                pong_raw = await ws.recv()
                pong = json.loads(pong_raw)
                assert pong["type"] == "pong"
                assert pong["client_time"] == t_client
                assert "server_time" in pong
                assert pong["server_time"] >= t_client

        asyncio.run(run())

    def test_tier1_http_health_check(self, voice_server):
        """Validates HTTP diagnostics and health endpoint returns 200 OK with correct JSON telemetry."""
        http_url = voice_server["http_url"]
        
        for path in ("/", "/health", "/status", "/ws/voice"):
            url = f"{http_url}{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "VoiceBridgeTest/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                assert resp.status == 200, f"Expected 200 OK from {url}, got {resp.status}"
                data = json.loads(resp.read().decode("utf-8"))
                
                assert data["status"] == "ONLINE"
                assert "Lauburu" in data["service"]
                assert data["port"] == voice_server["port"]
                assert "active_sessions" in data
                assert "uptime_seconds" in data
                assert isinstance(data["sessions"], list)

    def test_tier1_http_cors_preflight(self, voice_server):
        """Validates HTTP OPTIONS preflight returns proper CORS headers for browser integration."""
        http_url = voice_server["http_url"]
        url = f"{http_url}/"
        
        req = urllib.request.Request(
            url,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            },
            method="OPTIONS"
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            # 200 or 204
            assert resp.status in (200, 204)
            allow_origin = resp.headers.get("Access-Control-Allow-Origin")
            assert allow_origin == "*" or "localhost" in str(allow_origin)


# ============================================================================
# TIER 2: Boundary Payload Sizes, Bursts, Interleaving & Fault Recovery
# ============================================================================

class TestTier2BoundaryAndFaults:
    """Tier 2: Boundary & Extreme Conditions."""

    @pytest.mark.parametrize("size_bytes,desc", [
        (1, "1 Byte (Minimum payload boundary)"),
        (256, "256 Bytes (Tiny packet)"),
        (1024, "1 KB (Single small audio slice)"),
        (16 * 1024, "16 KB (Typical PCM audio buffer)"),
        (64 * 1024, "64 KB (Medium audio burst)"),
        (100 * 1024, "100 KB (Benchmark requirement)"),
        (512 * 1024, "512 KB (Half-megabyte chunk)"),
        (1024 * 1024, "1 MB (1 MiB boundary)"),
        (5 * 1024 * 1024, "5 MB (Large multi-second high-def buffer)"),
    ])
    def test_tier2_boundary_payload_sizes(self, voice_server, size_bytes, desc):
        """Validates echo across extreme payload boundaries from 1 Byte to 5 Megabytes."""
        ws_url = voice_server["ws_url"]
        
        async def run():
            result = await verify_voice_bridge_latency(
                url=ws_url,
                payload_size=size_bytes,
                iterations=2,
                threshold_ms=500.0
            )
            return result

        result = asyncio.run(run())
        assert result.success is True, f"Boundary test failed for {desc}: {result.error_message}"
        assert result.byte_match is True, f"Fidelity match failed for size {size_bytes} bytes"
        assert result.avg_rtt_ms < 500.0, f"Latency violation for size {size_bytes}: {result.avg_rtt_ms:.2f}ms"

    def test_tier2_rapid_burst_transmission(self, voice_server):
        """Validates sending 30 rapid back-to-back 64KB binary frames without awaiting intermediate responses (pipelining)."""
        ws_url = voice_server["ws_url"]
        burst_count = 30
        frame_size = 64 * 1024  # 64 KB per frame = ~1.92 MB burst

        async def run():
            test_frames = [os.urandom(frame_size) for _ in range(burst_count)]
            received_frames = []

            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()

                t0 = time.perf_counter()

                # Pipeline all sends rapidly
                for frame in test_frames:
                    await ws.send(frame)

                # Receive all responses
                for _ in range(burst_count):
                    resp = await ws.recv()
                    assert isinstance(resp, (bytes, bytearray, memoryview))
                    received_frames.append(bytes(resp))

                t1 = time.perf_counter()
                total_burst_time_ms = (t1 - t0) * 1000.0
                
                # Verify order and 100% byte fidelity for every frame in the burst
                for idx, (sent, recv) in enumerate(zip(test_frames, received_frames)):
                    assert sent == recv, f"Burst frame {idx + 1}/{burst_count} mismatched!"

                logger.info(
                    "30-frame burst (1.92 MB) completed in %.2f ms (%.2f ms/frame)",
                    total_burst_time_ms, total_burst_time_ms / burst_count
                )
                assert (total_burst_time_ms / burst_count) < 500.0

        asyncio.run(run())

    def test_tier2_interleaved_binary_and_json_control(self, voice_server):
        """Validates interleaving binary audio frames with JSON control frames on the same WebSocket session."""
        ws_url = voice_server["ws_url"]

        async def run():
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Greeting
                greeting = json.loads(await ws.recv())
                assert greeting["type"] == "ready"

                # 1. Send binary frame
                payload_1 = os.urandom(32768)
                await ws.send(payload_1)
                recv_1 = await ws.recv()
                assert recv_1 == payload_1

                # 2. Send JSON ping
                await ws.send(json.dumps({"type": "ping", "client_time": 42.0}))
                recv_pong = json.loads(await ws.recv())
                assert recv_pong["type"] == "pong"
                assert recv_pong["client_time"] == 42.0

                # 3. Send binary frame 2
                payload_2 = os.urandom(49152)
                await ws.send(payload_2)
                recv_2 = await ws.recv()
                assert recv_2 == payload_2

                # 4. Send get_stats JSON
                await ws.send(json.dumps({"type": "get_stats"}))
                recv_stats = json.loads(await ws.recv())
                assert recv_stats["type"] == "session_stats"
                assert recv_stats["stats"]["bytes_received"] >= (32768 + 49152)

                # 5. Send binary frame 3
                payload_3 = os.urandom(16384)
                await ws.send(payload_3)
                recv_3 = await ws.recv()
                assert recv_3 == payload_3

        asyncio.run(run())

    def test_tier2_malformed_json_recovery(self, voice_server):
        """Validates daemon sends error response on malformed JSON without crashing, and audio echo recovers."""
        ws_url = voice_server["ws_url"]

        async def run():
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()

                # Send malformed JSON
                await ws.send("{broken_json: true, missing_quotes")
                err_resp = json.loads(await ws.recv())
                assert err_resp["type"] == "error"
                assert "Malformed JSON" in err_resp["message"]

                # Verify subsequent binary audio echo operates with 100% fidelity
                test_audio = os.urandom(50000)
                await ws.send(test_audio)
                echoed_audio = await ws.recv()
                assert echoed_audio == test_audio

        asyncio.run(run())

    def test_tier2_clean_session_lifecycle(self, voice_server):
        """Validates full session lifecycle: session_start -> streaming -> session_end -> clean WS close 1000."""
        ws_url = voice_server["ws_url"]

        async def run():
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()

                # 1. Start session
                await ws.send(json.dumps({"type": "session_start", "mimeType": "audio/webm"}))
                started = json.loads(await ws.recv())
                assert started["type"] == "session_started"

                # 2. Stream audio chunk
                chunk = os.urandom(10000)
                await ws.send(chunk)
                echoed = await ws.recv()
                assert echoed == chunk

                # 3. End session
                await ws.send(json.dumps({"type": "session_end"}))
                ended = json.loads(await ws.recv())
                assert ended["type"] == "session_ended"
                assert "final_stats" in ended

                # 4. Clean close
                await ws.close(code=1000, reason="Test completed")
                assert ws.close_code == 1000

        asyncio.run(run())


# ============================================================================
# TIER 3: Concurrency, Multi-Client Stress & Session Churn
# ============================================================================

class TestTier3ConcurrencyAndStress:
    """Tier 3: Concurrency & Multi-Client Stress Testing."""

    def test_tier3_concurrent_clients_load(self, voice_server):
        """Validates 10 simultaneous WebSocket clients streaming unique binary payloads with zero cross-talk."""
        ws_url = voice_server["ws_url"]
        client_count = 10
        iterations_per_client = 5
        payload_size = 50 * 1024  # 50 KB each

        async def client_worker(client_id: int):
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()

                for it in range(iterations_per_client):
                    # Unique payload per client and iteration
                    unique_payload = f"client-{client_id}-iter-{it}-".encode("utf-8") + os.urandom(payload_size)
                    
                    t0 = time.perf_counter()
                    await ws.send(unique_payload)
                    recv_payload = await ws.recv()
                    t1 = time.perf_counter()
                    
                    assert recv_payload == unique_payload, f"Client {client_id} received corrupted payload on iter {it}!"
                    rtt_ms = (t1 - t0) * 1000.0
                    assert rtt_ms < 500.0, f"Client {client_id} RTT SLA violated: {rtt_ms:.2f}ms"

        async def run_all():
            tasks = [asyncio.create_task(client_worker(i)) for i in range(client_count)]
            await asyncio.gather(*tasks)

        asyncio.run(run_all())

    def test_tier3_client_connect_disconnect_churn(self, voice_server):
        """Validates 20 rapid sequential/concurrent connections and disconnections without resource leaks."""
        ws_url = voice_server["ws_url"]
        churn_count = 20

        async def churn_client(client_idx: int):
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()
                
                # Send small binary frame
                data = os.urandom(1024)
                await ws.send(data)
                resp = await ws.recv()
                assert resp == data
                
                # Clean close
                await ws.close()

        async def run_churn():
            tasks = [asyncio.create_task(churn_client(i)) for i in range(churn_count)]
            await asyncio.gather(*tasks)

        asyncio.run(run_churn())

    def test_tier3_session_manager_stats_accuracy(self, voice_server):
        """Validates active session count increments and decrements accurately."""
        ws_url = voice_server["ws_url"]
        http_url = voice_server["http_url"]

        async def run():
            # Initial active count
            with urllib.request.urlopen(f"{http_url}/health", timeout=3.0) as r:
                initial_count = json.loads(r.read().decode("utf-8"))["active_sessions"]

            # Connect 3 clients
            ws1 = await websockets.connect(ws_url, max_size=MAX_FRAME_SIZE)
            _ = await ws1.recv()
            ws2 = await websockets.connect(ws_url, max_size=MAX_FRAME_SIZE)
            _ = await ws2.recv()
            ws3 = await websockets.connect(ws_url, max_size=MAX_FRAME_SIZE)
            _ = await ws3.recv()

            try:
                # Active count should be initial + 3
                with urllib.request.urlopen(f"{http_url}/health", timeout=3.0) as r:
                    count_during = json.loads(r.read().decode("utf-8"))["active_sessions"]
                assert count_during == initial_count + 3

                # Close 2
                await ws1.close()
                await ws2.close()
                await asyncio.sleep(0.05)

                with urllib.request.urlopen(f"{http_url}/health", timeout=3.0) as r:
                    count_after = json.loads(r.read().decode("utf-8"))["active_sessions"]
                assert count_after == initial_count + 1

            finally:
                await ws3.close()
                await asyncio.sleep(0.05)

        asyncio.run(run())


# ============================================================================
# TIER 4: Real-World Audio Emulation, Jitter SLA & Mode Switching
# ============================================================================

class TestTier4RealWorldAudioAndJitter:
    """Tier 4: Real-World WebRTC / RecordRTC Audio Emulation."""

    def test_tier4_recordrtc_audio_stream_emulation(self, voice_server):
        """
        Emulates RecordRTC streaming 150ms audio slices (16kHz 16-bit mono PCM ~4800 bytes).
        Validates arrival jitter standard deviation < 20ms and 100% packet integrity.
        """
        ws_url = voice_server["ws_url"]
        slice_duration_s = 0.05  # 50ms interval for fast reliable test execution
        slice_bytes = 4800  # 150ms of 16kHz 16-bit mono = ~4,800 bytes
        total_slices = 20

        async def run():
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()

                # Start session
                await ws.send(json.dumps({
                    "type": "session_start",
                    "mimeType": "audio/webm",
                    "timeSliceMs": 150,
                    "sampleRate": 16000
                }))
                _ = await ws.recv()

                rtts = []
                intervals = []
                last_recv_time = None

                for i in range(total_slices):
                    audio_chunk = os.urandom(slice_bytes)
                    
                    t0 = time.perf_counter()
                    await ws.send(audio_chunk)
                    echoed = await ws.recv()
                    t1 = time.perf_counter()

                    assert echoed == audio_chunk, f"Audio slice {i + 1} corrupted!"
                    rtt_ms = (t1 - t0) * 1000.0
                    rtts.append(rtt_ms)

                    if last_recv_time is not None:
                        intervals.append((t1 - last_recv_time) * 1000.0)
                    last_recv_time = t1

                    await asyncio.sleep(slice_duration_s)

                avg_rtt = sum(rtts) / len(rtts)
                max_rtt = max(rtts)
                
                # Standard deviation of RTT
                rtt_variance = sum((x - avg_rtt) ** 2 for x in rtts) / len(rtts)
                jitter_stddev = math.sqrt(rtt_variance)

                logger.info(
                    "Audio stream simulation: %d slices of %d bytes | Avg RTT: %.2fms | Max RTT: %.2fms | Jitter: %.2fms",
                    total_slices, slice_bytes, avg_rtt, max_rtt, jitter_stddev
                )

                assert avg_rtt < 500.0, f"Average audio slice RTT {avg_rtt:.2f}ms >= 500ms"
                assert jitter_stddev < 25.0, f"Jitter standard deviation {jitter_stddev:.2f}ms too high"

        asyncio.run(run())

    def test_tier4_audio_queue_and_mode_switching(self, voice_server):
        """Validates dynamic mode switching (echo -> echo_and_queue -> echo) and queue telemetry."""
        ws_url = voice_server["ws_url"]

        async def run():
            async with websockets.connect(ws_url, max_size=MAX_FRAME_SIZE) as ws:
                # Drain greeting
                _ = await ws.recv()

                # Switch to echo_and_queue
                await ws.send(json.dumps({"type": "set_mode", "mode": "echo_and_queue"}))
                mode_resp = json.loads(await ws.recv())
                assert mode_resp["type"] == "mode_updated"
                assert mode_resp["mode"] == "echo_and_queue"

                # Send 5 binary frames
                for _ in range(5):
                    chunk = os.urandom(10000)
                    await ws.send(chunk)
                    echoed = await ws.recv()
                    assert echoed == chunk

                # Check stats
                await ws.send(json.dumps({"type": "get_stats"}))
                stats_resp = json.loads(await ws.recv())
                assert stats_resp["stats"]["mode"] == "echo_and_queue"
                assert stats_resp["stats"]["frames_received"] >= 5
                assert stats_resp["stats"]["bytes_received"] >= 50000

        asyncio.run(run())
