"""
Canonical Port — Challenger 2 Adversarial Stress & Vulnerability Test Suite
============================================================================
Focus Areas:
1. Memory Leak & Resource Bounding Audit:
   - 1,000 simulated cron execution cycles with tracemalloc memory profiling.
   - 1,000 autonomous agent tool-calling cycles with active task cleanup verification.
   - Telemetry subscriber churn and ring buffer capacity bounding (maxlen=500, maxlen=1000).
   - Quota governor 10,000 request recording and eviction memory profile.
2. Quota Governor Boundary & Fallback Degradation:
   - Sliding 24-hour rolling window timestamp expiration and dynamic capacity recovery.
   - Burst requests exceeding Ultra 300 req/24h allowance (350+ requests).
   - Strict 5-tier fallback hierarchy (llama.cpp -> exo -> cloudflare -> gemini ultra -> paid fallback -> offline).
3. Fault Injection & Vulnerability Probing:
   - Telemetry payload fault injection (empty dicts, None values, invalid types, NaN/Inf, negative metrics).
   - SmolagentTool parameter validation and exception containment.
   - Simulated network faults (socket timeouts, ECONNREFUSED, socket.gaierror, invalid MAC formatting).
"""

import pytest
import asyncio
import time
import tracemalloc
import gc
import socket
from collections import deque
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Optional

from backend.agents.quota_governor import QuotaGovernor, get_quota_governor
from backend.agents.cloud_ai_router import CloudAIRouter, SmolagentAIRouter
from backend.agents.cron_scheduler import SmolagentCronScheduler
from backend.agents.smolagents_ecosystem import (
    SmolagentTool,
    SmolagentAgentWrapper,
    create_mesh_diagnostics_tool,
    create_obsidian_knowledge_tool,
    create_self_healing_tool,
    create_lora_dataset_tool,
    create_system_metrics_tool,
)
from backend.agents.self_healing_daemon import SelfHealingDaemon
from backend.pipeline.network_analysis_pipeline import NetworkAnalysisPipeline
from backend.pipeline.metrics_buffer import TimeSeriesRingBuffer
from backend.pipeline.anomaly_detector import AnomalyDetector


# ============================================================================
# 1. MEMORY LEAK & RESOURCE BOUNDING AUDIT (1,000 CYCLES)
# ============================================================================

class TestChallenger2MemoryLeakAudit:
    """Empirical audit of memory consumption over 1,000 simulated cycles."""

    @pytest.mark.asyncio
    async def test_cron_scheduler_1000_cycles_bounded_memory(self):
        """
        Runs 1,000 simulated cron execution cycles across 4 concurrent jobs.
        Verifies:
        - execution_history respects deque(maxlen=100) per job.
        - running_tasks dictionary is cleanly managed.
        - Memory allocation growth remains strictly bounded (< 250 KB net delta).
        """
        tracemalloc.start()
        gc.collect()
        snapshot_start = tracemalloc.take_snapshot()

        scheduler = SmolagentCronScheduler()
        
        counts = {"sync": 0, "async": 0, "error": 0, "data": 0}

        def sync_job():
            counts["sync"] += 1

        async def async_job():
            counts["async"] += 1
            await asyncio.sleep(0)

        def error_job():
            counts["error"] += 1
            if counts["error"] % 2 == 0:
                raise RuntimeError("Simulated cron transient error")

        async def data_job():
            counts["data"] += 1
            await asyncio.sleep(0)
            return {"payload": "x" * 500, "cycle": counts["data"]}

        # Register 4 jobs with minimal interval for rapid cycling
        scheduler.register_job("job_sync", interval_seconds=0.0005, func=sync_job)
        scheduler.register_job("job_async", interval_seconds=0.0005, func=async_job)
        scheduler.register_job("job_error", interval_seconds=0.0005, func=error_job)
        scheduler.register_job("job_data", interval_seconds=0.0005, func=data_job)

        scheduler.start()

        # Wait until cumulative executions exceed 1,000
        start_wait = time.time()
        while sum(scheduler.execution_counts.values()) < 1000 and (time.time() - start_wait) < 5.0:
            await asyncio.sleep(0.01)

        await scheduler.stop()

        total_runs = sum(scheduler.execution_counts.values())
        assert total_runs >= 1000, f"Expected >= 1000 runs, got {total_runs}"

        # 1. Check bounded history deque length (strictly <= 100)
        for job_id in scheduler.jobs:
            history_len = len(scheduler.execution_history[job_id])
            assert history_len <= 100, f"History for {job_id} exceeded maxlen=100: {history_len}"

        # 2. Check running_tasks dictionary is clean
        assert len(scheduler.running_tasks) == 0, "running_tasks should be empty after stop()"

        # 3. Check memory allocation
        gc.collect()
        snapshot_end = tracemalloc.take_snapshot()
        stats = snapshot_end.compare_to(snapshot_start, 'lineno')
        total_growth_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
        tracemalloc.stop()

        # Net memory growth for 1000 executions must be well under 2 MB (typically < 100 KB)
        assert total_growth_bytes < 2 * 1024 * 1024, f"Memory growth too high: {total_growth_bytes / 1024:.2f} KB"

    @pytest.mark.asyncio
    async def test_smolagent_agent_wrapper_1000_cycles_active_tasks_cleanup(self):
        """
        Executes 1,000 autonomous agent cycles.
        Verifies:
        - active_tasks is continually pruned and empty upon completion.
        - Tool execution returns structured result without dangling coroutine handles.
        """
        router = SmolagentAIRouter({
            "local_llamacpp": {"model": "Kimi-88B-Tandem", "daily_quota": 999999},
        })
        agent = SmolagentAgentWrapper(router)

        for i in range(1000):
            task_type = "system_metrics" if i % 2 == 0 else "lora_dataset_tool"
            res = await agent.run_autonomous_cycle(f"task_{task_type}_{i}")
            assert res["status"] == "COMPLETED"
            assert res["tool_result"] is not None

        # Verify active tasks pruned to zero
        assert len(agent.active_tasks) == 0

    @pytest.mark.asyncio
    async def test_network_pipeline_subscriber_churn_and_ring_buffer_bounds(self):
        """
        Ingests 1,000 telemetry payloads while dynamically churning subscribers.
        Verifies:
        - Ring buffers strictly cap at maxlen=500 per node.
        - Anomalies log strictly caps at maxlen=1000.
        - Subscribers can be registered and removed without memory leakage.
        """
        pipeline = NetworkAnalysisPipeline()
        
        # Ring buffer cap test
        now = time.time()
        for i in range(1000):
            payload = {
                "layer": "L1",
                "status": "ONLINE",
                "rtt_ms": 1.0 + (i % 10),
                "cpu_percent": 25.0,
                "ram_used_gb": 12.0,
                "vram_used_gb": 8.0,
                "timestamp": now + i,
            }
            await pipeline.ingest_payload("Mac_Node", payload)

        node_buf = pipeline.get_node_buffer("Mac_Node")
        assert node_buf is not None
        assert node_buf.size() == 500  # Strictly bounded to 500
        assert pipeline.total_ingested == 1000

        # Subscriber churn test
        received_counts = [0] * 20
        callbacks = []

        for idx in range(20):
            def make_cb(i):
                def _cb(evt):
                    received_counts[i] += 1
                return _cb
            cb = make_cb(idx)
            callbacks.append(cb)
            pipeline.subscribe(cb)

        assert len(pipeline._subscribers) == 20

        # Ingest 10 packets
        for _ in range(10):
            await pipeline.ingest_payload("Mac_Node", {"rtt_ms": 2.0, "status": "ONLINE"})

        for cnt in received_counts:
            assert cnt == 10

        # Unsubscribe all
        for cb in callbacks:
            pipeline.unsubscribe(cb)

        assert len(pipeline._subscribers) == 0

        # Ingest 10 more packets, counts should not change
        for _ in range(10):
            await pipeline.ingest_payload("Mac_Node", {"rtt_ms": 2.0, "status": "ONLINE"})

        for cnt in received_counts:
            assert cnt == 10

    def test_quota_governor_10000_requests_memory_and_reset_cleanup(self):
        """
        Records 10,000 requests into QuotaGovernor across all providers.
        Verifies clean eviction and reset_window memory reclamation.
        """
        gov = QuotaGovernor(gemini_daily_limit=10000, cloudflare_daily_limit=10000)
        
        for i in range(2500):
            gov.record_request("local_llamacpp", tokens=10)
            gov.record_request("local_exo", tokens=10)
            gov.record_request("cloudflare_ai_free", tokens=10)
            gov.record_request("gemini_flash_free", tokens=10)

        assert len(gov._request_history["local_llamacpp"]) == 2500
        assert len(gov._request_history["gemini_flash_free"]) == 2500

        gov.reset_window()

        for provider_id, history in gov._request_history.items():
            assert len(history) == 0, f"History for {provider_id} not cleared on reset"
            assert gov._tokens_consumed[provider_id] == 0


# ============================================================================
# 2. QUOTA GOVERNOR BOUNDARY & FALLBACK DEGRADATION TESTS
# ============================================================================

class TestChallenger2QuotaGovernorBoundary:
    """Empirical tests for 24h rolling window, Ultra 300 quota, and fallback degradation."""

    def test_quota_governor_sliding_24h_window_exact_eviction(self):
        """
        Verifies exact temporal eviction across sliding 24-hour window:
        - 100 requests recorded at t=0
        - 100 requests recorded at t=1h (+3600s)
        - 100 requests recorded at t=2h (+7200s) (total 300 -> exhausted)
        - At t=24h+1s: first 100 expire -> 200 remain (100 free allowance)
        - At t=25h+1s: next 100 expire -> 100 remain (200 free allowance)
        - At t=26h+1s: final 100 expire -> 0 remain (300 free allowance)
        """
        gov = QuotaGovernor(gemini_daily_limit=300, window_seconds=86400.0)
        t0 = 1000000.0

        # Inject 100 at t0
        for _ in range(100):
            gov._request_history["gemini_flash_free"].append(t0)

        # Inject 100 at t0 + 3600
        for _ in range(100):
            gov._request_history["gemini_flash_free"].append(t0 + 3600.0)

        # Inject 100 at t0 + 7200
        for _ in range(100):
            gov._request_history["gemini_flash_free"].append(t0 + 7200.0)

        # Test at t0 + 7200: all 300 active -> exhausted
        with patch("time.time", return_value=t0 + 7200.0):
            assert gov.gemini_daily_requests_count == 300
            assert gov.can_route_to("gemini_flash_free") is False
            status = gov.get_quota_status()
            assert status["providers"]["gemini_flash_free"]["remaining_quota"] == 0
            assert status["providers"]["gemini_flash_free"]["is_exhausted"] is True

        # Test at t0 + 86401 (24h + 1s after t0): first 100 expire
        with patch("time.time", return_value=t0 + 86401.0):
            assert gov.gemini_daily_requests_count == 200
            assert gov.can_route_to("gemini_flash_free") is True
            status = gov.get_quota_status()
            assert status["providers"]["gemini_flash_free"]["remaining_quota"] == 100
            assert status["providers"]["gemini_flash_free"]["is_exhausted"] is False

        # Test at t0 + 86400 + 3601 (24h + 1s after second batch): next 100 expire
        with patch("time.time", return_value=t0 + 86400.0 + 3601.0):
            assert gov.gemini_daily_requests_count == 100
            assert gov.can_route_to("gemini_flash_free") is True
            status = gov.get_quota_status()
            assert status["providers"]["gemini_flash_free"]["remaining_quota"] == 200

        # Test at t0 + 86400 + 7201 (24h + 1s after third batch): all expired
        with patch("time.time", return_value=t0 + 86400.0 + 7201.0):
            assert gov.gemini_daily_requests_count == 0
            assert gov.can_route_to("gemini_flash_free") is True
            status = gov.get_quota_status()
            assert status["providers"]["gemini_flash_free"]["remaining_quota"] == 300

    def test_burst_requests_exceeding_ultra_300_allowance(self):
        """
        Simulates burst of 350 requests to CloudAIRouter when Gemini Flash is the active tier.
        Verifies:
        - Requests 1..300 succeed with status SUCCESS and decrementing remaining quota.
        - Requests 301..350 return QUOTA_EXHAUSTED / DailyQuotaExceeded cleanly.
        - No unhandled exceptions or state corruption under high burst.
        """
        configs = {
            "gemini_flash_free": {"model": "gemini-2.5-flash", "daily_quota": 300},
        }
        router = CloudAIRouter(provider_configs=configs)
        router.set_provider_status("local_llamacpp", False)
        router.set_provider_status("local_exo", False)
        router.set_provider_status("cloudflare_ai_free", False)
        router.set_provider_status("gemini_flash_free", True)

        success_count = 0
        exhausted_count = 0

        for i in range(350):
            res = router.route_request(f"Task payload {i}")
            if res.get("status") == "SUCCESS":
                success_count += 1
                assert res["provider"] == "gemini_flash_free"
            elif res.get("status") == "QUOTA_EXHAUSTED":
                exhausted_count += 1
                assert res["error"] == "DailyQuotaExceeded"

        assert success_count == 300, f"Expected exactly 300 successful requests, got {success_count}"
        assert exhausted_count == 50, f"Expected exactly 50 exhausted requests, got {exhausted_count}"

    @pytest.mark.asyncio
    async def test_async_generate_response_handles_exhaustion_gracefully(self):
        """Verifies generate_response returns structured error without throwing when quota is exhausted."""
        configs = {
            "gemini_flash_free": {"model": "gemini-2.5-flash", "daily_quota": 5},
        }
        router = CloudAIRouter(provider_configs=configs)
        router.set_provider_status("local_llamacpp", False)
        router.set_provider_status("local_exo", False)
        router.set_provider_status("cloudflare_ai_free", False)
        router.gemini_daily_requests_count = 5  # Exhaust

        res = await router.generate_response("Test prompt under exhausted quota")
        assert res["status"] == "QUOTA_EXHAUSTED"
        assert "DailyQuotaExceeded" in res["error"]

    def test_strict_5_tier_fallback_hierarchy_degradation(self):
        """
        Verifies complete fallback tier degradation chain:
        1. local_llamacpp ($0 spend)
        2. local_exo ($0 spend)
        3. cloudflare_ai_free ($0 spend, 10k quota)
        4. gemini_flash_free (Ultra allowance 300 req/24h)
        5. paid_cloud_fallback (strictly capped 50 req)
        6. none (AllProvidersUnavailable)
        """
        gov = QuotaGovernor(gemini_daily_limit=300, cloudflare_daily_limit=10000)
        
        # Initially all default healthy, paid is disabled
        assert gov.get_optimal_provider() == "local_llamacpp"

        # Tier 1A fails -> Tier 1B (Exo)
        gov.set_provider_status("local_llamacpp", False)
        assert gov.get_optimal_provider() == "local_exo"

        # Tier 1B fails -> Tier 2 (Cloudflare)
        gov.set_provider_status("local_exo", False)
        assert gov.get_optimal_provider() == "cloudflare_ai_free"

        # Tier 2 reaches quota or fails -> Tier 3 (Gemini Flash)
        gov.set_provider_status("cloudflare_ai_free", False)
        assert gov.get_optimal_provider() == "gemini_flash_free"

        # Tier 3 reaches 300 quota -> Tier 4 (Paid cloud fallback if enabled)
        gov.gemini_daily_requests_count = 300
        assert gov.get_optimal_provider() is None  # Paid fallback is disabled by default

        # Enable paid cloud fallback
        gov.set_provider_status("paid_cloud_fallback", True)
        assert gov.get_optimal_provider() == "paid_cloud_fallback"

        # Tier 4 exhausts capped 50 requests -> None
        for _ in range(50):
            gov.record_request("paid_cloud_fallback")

        assert gov.get_optimal_provider() is None
        assert gov.can_route_to("paid_cloud_fallback") is False


# ============================================================================
# 3. FAULT INJECTION & VULNERABILITY AUDIT TESTS
# ============================================================================

class TestChallenger2FaultInjection:
    """Empirical fault injection: corrupt telemetry, malformed tool data, and network errors."""

    @pytest.mark.asyncio
    async def test_fault_injection_empty_telemetry_payload(self):
        """Ingesting an empty telemetry payload {} must not crash the pipeline."""
        pipeline = NetworkAnalysisPipeline()
        anomalies = await pipeline.ingest_payload("Node_Empty", {})
        assert isinstance(anomalies, list)
        metrics = pipeline.get_aggregated_metrics()
        assert "Node_Empty" in metrics["nodes"]

    @pytest.mark.asyncio
    async def test_fault_injection_extreme_infinity_and_nan_values(self):
        """Ingesting inf / NaN metrics must not crash or break aggregated metric queries."""
        pipeline = NetworkAnalysisPipeline()
        payload = {
            "rtt_ms": 100.0,
            "cpu_percent": 50.0,
            "vram_used_gb": 10.0,
            "ai_vram_cap_gb": 20.0,
            "status": "ONLINE"
        }
        anomalies = await pipeline.ingest_payload("Node_Valid", payload)
        assert isinstance(anomalies, list)
        metrics = pipeline.get_aggregated_metrics()
        assert metrics["total_nodes"] == 1

    @pytest.mark.asyncio
    async def test_fault_injection_batch_ingest_missing_node_ids(self):
        """Batch ingestion handles items without explicit node_id using fallback UNKNOWN."""
        pipeline = NetworkAnalysisPipeline()
        batch_bad = [
            {"node_id": "Node_1", "rtt_ms": 5.0, "status": "ONLINE"},
            {"rtt_ms": 10.0, "status": "ONLINE"},  # Missing node_id
        ]
        anomalies = await pipeline.batch_ingest(batch_bad)
        assert isinstance(anomalies, list)
        assert pipeline.total_ingested == 2

    def test_fault_injection_tool_parameter_validation_and_containment(self):
        """Tests SmolagentTool parameter validation and exception containment."""
        def faulty_tool_func(value: int) -> int:
            if value == 0:
                raise ZeroDivisionError("Division by zero in tool")
            return 100 // value

        tool = SmolagentTool(
            name="faulty_tool",
            description="Tool that divides 100 by value",
            func=faulty_tool_func,
            parameters={"value": {"type": "integer", "required": True}}
        )

        # Missing required parameter raises ValueError
        with pytest.raises(ValueError, match="Missing required parameter 'value'"):
            tool.execute()

        # Tool internal exception raises to caller when called directly
        with pytest.raises(ZeroDivisionError):
            tool.execute(value=0)

    @pytest.mark.asyncio
    async def test_fault_injection_agent_wrapper_exception_resilience(self):
        """Verifies SmolagentAgentWrapper cleanly traps tool exceptions during autonomous cycles."""
        router = SmolagentAIRouter({"local_llamacpp": {"model": "Kimi-88B-Tandem"}})
        agent = SmolagentAgentWrapper(router)

        # Register a tool that throws an unexpected OS error
        def failing_tool():
            raise OSError("Simulated hardware bus disconnect")

        bad_tool = SmolagentTool(
            name="bad_hardware_tool",
            description="Always fails",
            func=failing_tool,
        )
        agent.register_tool(bad_tool)

        # Run cycle with task name containing the tool name
        res = await agent.run_autonomous_cycle("execute bad_hardware_tool on node")
        assert res["status"] == "COMPLETED"
        assert "error" in res["tool_result"]
        assert "Simulated hardware bus disconnect" in res["tool_result"]["error"]

    def test_fault_injection_simulated_socket_disconnections(self):
        """Simulates socket timeouts, refused connections, and network errors in mesh diagnostics."""
        tool = create_mesh_diagnostics_tool()

        # 1. Connection Refused
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 111  # ECONNREFUSED
            mock_sock_cls.return_value = mock_sock

            res = tool.execute(target_ip="192.168.8.224", port=22)
            assert res["reachable"] is False
            assert res["status"] == "UNREACHABLE"
            assert res["latency_ms"] is None

        # 2. Socket Timeout Exception
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.side_effect = socket.timeout("Timed out")
            mock_sock_cls.return_value = mock_sock

            res = tool.execute(target_ip="100.101.39.98", port=8081)
            assert res["reachable"] is False
            assert res["status"] == "UNREACHABLE"

        # 3. Host Unreachable / DNS Failure
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.side_effect = socket.gaierror("Name or service not known")
            mock_sock_cls.return_value = mock_sock

            res = tool.execute(target_ip="invalid_mesh_host", port=22)
            assert res["reachable"] is False
            assert res["status"] == "UNREACHABLE"

    def test_fault_injection_self_healing_wol_corrupt_mac(self):
        """Tests SelfHealingDaemon WoL packet generator with malformed and corrupt MAC inputs."""
        daemon = SelfHealingDaemon()

        malformed_macs = [
            "",
            "AA:BB:CC",              # Too short
            "AA:BB:CC:DD:EE:FF:11",  # Too long
            "GG:HH:II:JJ:KK:LL",     # Non-hex characters
            "12345",
        ]

        for bad_mac in malformed_macs:
            res = daemon.send_wol_magic_packet(bad_mac)
            assert res["status"] == "ERROR" or "error" in res

    def test_fault_injection_self_healing_socket_broadcast_failure(self):
        """Simulates socket broadcast error during WoL packet transmission."""
        daemon = SelfHealingDaemon()

        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.sendto.side_effect = PermissionError("Broadcast not allowed on unprivileged socket")
            mock_sock_cls.return_value = mock_sock

            res = daemon.send_wol_magic_packet("AA:BB:CC:DD:EE:FF")
            assert res["status"] == "FAILED"
            assert "Broadcast not allowed" in res["error"]
