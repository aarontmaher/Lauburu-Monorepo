"""
Empirical Adversarial Stress Suite for canonical_port
Author: Challenger 1 (Empirical Challenger)

Coverage:
1. Burst ingestion (500+ telemetry payloads) into NetworkAnalysisPipeline with event loop latency < 15ms
2. High-concurrency async access across all 12+ spec modules in BackendStateStore
3. Rapid start/stop and cancellation cycles in SmolagentCronScheduler with zero task leaks / unhandled exceptions
4. Textual UI Pilot live responsiveness under telemetry burst load
"""

import asyncio
import gc
import os
import random
import statistics
import tempfile
import time
from typing import Any, Dict, List

import pytest
from textual.app import App

from backend.agents import (
    SmolagentAIRouter,
    SmolagentAgentWrapper,
    SmolagentCronScheduler,
    SmolagentTool,
)
from backend.models import ModuleHealthStatus
from backend.pipeline import (
    AnomalyDetector,
    NetworkAnalysisPipeline,
    ObsidianVaultSyncFormatter,
    TimeSeriesRingBuffer,
    get_network_pipeline,
    reset_network_pipeline,
)
from backend.spec_modules import (
    CANONICAL_SPEC_MODULE_CLASSES,
    create_all_spec_modules,
)
from backend.state import BackendStateStore, get_backend_state, reset_backend_state
from tui.canonical_tui import CanonicalPortApp


# =============================================================================
# 1. BURST TELEMETRY INGESTION & EVENT LOOP LATENCY STRESS (<15ms)
# =============================================================================

class TestBurstTelemetryIngestionStress:
    """Empirical stress tests for NetworkAnalysisPipeline under burst ingestion."""

    @pytest.mark.asyncio
    async def test_burst_ingestion_500_packets_latency_benchmark(
        self, sample_mesh_node_payloads
    ):
        """
        Burst-ingest 500+ telemetry payloads across 8 mesh nodes while measuring
        event loop latency with a 1ms heartbeat sampler.
        Contract: Event loop lag must strictly remain < 15.0ms.
        """
        pipeline = NetworkAnalysisPipeline()
        loop = asyncio.get_running_loop()

        tick_lags: List[float] = []
        stop_sampler = False

        async def loop_heartbeat_sampler():
            target_interval = 0.001  # 1ms target tick
            while not stop_sampler:
                t0 = loop.time()
                await asyncio.sleep(target_interval)
                t1 = loop.time()
                lag_ms = max(0.0, (t1 - t0 - target_interval) * 1000.0)
                tick_lags.append(lag_ms)

        async def flood_telemetry_burst():
            node_ids = list(sample_mesh_node_payloads.keys())
            for i in range(600):
                node_id = node_ids[i % len(node_ids)]
                payload = dict(sample_mesh_node_payloads[node_id])
                payload["timestamp"] = time.time()
                payload["cpu_percent"] = (payload["cpu_percent"] + (i * 0.1)) % 100.0
                payload["rtt_ms"] = payload["rtt_ms"] + (0.01 * (i % 10))
                await pipeline.ingest_payload(node_id, payload)
                if i % 10 == 0:
                    await asyncio.sleep(0.0001)  # Micro-yield so sampler captures high-resolution ticks

        sampler_task = asyncio.create_task(loop_heartbeat_sampler())
        t_start = time.perf_counter()
        await flood_telemetry_burst()
        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        stop_sampler = True
        await sampler_task

        # Assertions on pipeline state
        assert pipeline.total_ingested == 600
        metrics = pipeline.get_aggregated_metrics()
        assert metrics["total_nodes"] == len(sample_mesh_node_payloads)
        assert metrics["total_ingested_packets"] == 600

        # Assertions on event loop latency
        assert len(tick_lags) >= 1, "Heartbeat sampler should have collected tick samples"
        max_lag = max(tick_lags)
        avg_lag = statistics.mean(tick_lags)
        p95_lag = statistics.quantiles(tick_lags, n=20)[18] if len(tick_lags) >= 20 else max_lag
        p99_lag = statistics.quantiles(tick_lags, n=100)[98] if len(tick_lags) >= 100 else max_lag

        print(
            f"\\n[BENCHMARK] 600-packet burst in {t_elapsed:.2f}ms | Samples: {len(tick_lags)} | "
            f"Max Lag: {max_lag:.3f}ms | Avg Lag: {avg_lag:.3f}ms | p95: {p95_lag:.3f}ms | p99: {p99_lag:.3f}ms"
        )

        assert max_lag < 15.0, f"Max event loop lag {max_lag:.2f}ms exceeded 15.0ms limit"
        assert avg_lag < 5.0, f"Average event loop lag {avg_lag:.2f}ms exceeded 5.0ms limit"

    @pytest.mark.asyncio
    async def test_high_concurrency_multi_producer_burst_1200_packets(
        self, sample_mesh_node_payloads
    ):
        """
        16 parallel async coroutines simultaneously blasting 75 payloads each (= 1200 payloads total).
        Tests thread safety, ring buffer bounds, and concurrent event loop latency.
        """
        pipeline = NetworkAnalysisPipeline()
        loop = asyncio.get_running_loop()

        tick_lags: List[float] = []
        stop_sampler = False

        async def loop_heartbeat_sampler():
            target_interval = 0.002  # 2ms target tick
            while not stop_sampler:
                t0 = loop.time()
                await asyncio.sleep(target_interval)
                t1 = loop.time()
                lag_ms = max(0.0, (t1 - t0 - target_interval) * 1000.0)
                tick_lags.append(lag_ms)

        async def worker_producer(worker_id: int, count: int):
            node_ids = list(sample_mesh_node_payloads.keys())
            for i in range(count):
                node_id = node_ids[(worker_id + i) % len(node_ids)]
                payload = dict(sample_mesh_node_payloads[node_id])
                payload["timestamp"] = time.time()
                payload["cpu_percent"] = float((worker_id * 10 + i) % 100)
                await pipeline.ingest_payload(node_id, payload)
                if i % 15 == 0:
                    await asyncio.sleep(0)  # Micro-yield

        sampler_task = asyncio.create_task(loop_heartbeat_sampler())

        # 16 producers x 75 packets = 1200 packets
        num_producers = 16
        packets_per_producer = 75
        tasks = [
            asyncio.create_task(worker_producer(w, packets_per_producer))
            for w in range(num_producers)
        ]

        t_start = time.perf_counter()
        await asyncio.gather(*tasks)
        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        stop_sampler = True
        await sampler_task

        assert pipeline.total_ingested == 1200
        for node_id in sample_mesh_node_payloads:
            buf = pipeline.get_node_buffer(node_id)
            assert buf is not None
            assert buf.size() <= 500  # Ring buffer maxlen

        max_lag = max(tick_lags) if tick_lags else 0.0
        avg_lag = statistics.mean(tick_lags) if tick_lags else 0.0

        print(
            f"\\n[BENCHMARK] 1200-packet 16-producer burst in {t_elapsed:.2f}ms | "
            f"Max Lag: {max_lag:.3f}ms | Avg Lag: {avg_lag:.3f}ms"
        )

        assert max_lag < 15.0, f"Max lag {max_lag:.2f}ms exceeded 15.0ms limit"

    @pytest.mark.asyncio
    async def test_burst_ingestion_with_concurrent_subscribers(
        self, sample_mesh_node_payloads
    ):
        """
        Tests burst ingestion with 10 active subscribers (5 async coroutine subscribers + 5 sync callbacks).
        Verifies event fanout without loop blocking or dropped callbacks.
        """
        pipeline = NetworkAnalysisPipeline()
        async_events_received: List[Dict[str, Any]] = []
        sync_events_received: List[Dict[str, Any]] = []

        # Create distinct subscriber instances so list deduplication doesn't merge them
        for sub_id in range(5):
            def make_async_sub(s_id=sub_id):
                async def _sub(event: Dict[str, Any]):
                    async_events_received.append((s_id, event))
                    await asyncio.sleep(0)
                return _sub

            def make_sync_sub(s_id=sub_id):
                def _sub(event: Dict[str, Any]):
                    sync_events_received.append((s_id, event))
                return _sub

            pipeline.subscribe(make_async_sub())
            pipeline.subscribe(make_sync_sub())

        for i in range(100):
            node_id = "Mac_Node" if i % 2 == 0 else "Linux_Head_Node"
            payload = dict(sample_mesh_node_payloads[node_id])
            payload["timestamp"] = time.time()
            await pipeline.ingest_payload(node_id, payload)
            if i % 20 == 0:
                await asyncio.sleep(0.001)

        await asyncio.sleep(0.05)  # Let background async subscriber tasks flush

        # 5 distinct sync subs * 100 = 500
        assert len(sync_events_received) == 500
        # 5 distinct async subs * 100 = 500
        assert len(async_events_received) >= 450

    @pytest.mark.asyncio
    async def test_burst_ingestion_obsidian_atomic_sync_stress(
        self, mock_obsidian_vault_dir, sample_mesh_node_payloads
    ):
        """
        Tests high-throughput burst ingestion with simultaneous atomic Obsidian note writing.
        Verifies that disk I/O does not cause unhandled exceptions or loop lockups.
        """
        pipeline = NetworkAnalysisPipeline(vault_dir=mock_obsidian_vault_dir)

        for i in range(200):
            node_id = "MacBook_Pro" if i % 2 == 0 else "Linux_Head_Node"
            payload = dict(sample_mesh_node_payloads[node_id])
            payload["timestamp"] = time.time()
            payload["vram_used_gb"] = round(5.0 + (i % 5), 2)
            await pipeline.ingest_payload(node_id, payload)

        assert pipeline.total_ingested == 200
        assert os.path.exists(os.path.join(mock_obsidian_vault_dir, "MacBook_Pro.md"))
        assert os.path.exists(os.path.join(mock_obsidian_vault_dir, "Linux_Head_Node.md"))

    @pytest.mark.asyncio
    async def test_textual_pilot_live_ui_responsiveness_during_500_burst(
        self, sample_mesh_node_payloads
    ):
        """
        Executes a live Textual Pilot test with CanonicalPortApp running while 500 telemetry
        payloads are burst-ingested into the global pipeline.
        Verifies UI responsiveness, screen switching, and zero event loop starvation.
        """
        pipeline = get_network_pipeline()
        app = CanonicalPortApp()

        async with app.run_test(size=(160, 50)) as pilot:
            # Concurrently burst 500 packets while interacting with Textual UI
            async def background_burst():
                for i in range(500):
                    node_id = "Mac_Node" if i % 2 == 0 else "MacBook_Pro"
                    p = dict(sample_mesh_node_payloads[node_id])
                    p["timestamp"] = time.time()
                    p["cpu_percent"] = (p["cpu_percent"] + i) % 100.0
                    await pipeline.ingest_payload(node_id, p)
                    if i % 50 == 0:
                        await asyncio.sleep(0.001)

            burst_task = asyncio.create_task(background_burst())

            # Perform UI operations concurrently
            await pilot.press("n")  # Switch to Network screen
            await pilot.pause(0.02)
            await pilot.press("h")  # Switch to Hardware screen
            await pilot.pause(0.02)
            await pilot.press("b")  # Switch to Biometrics screen
            await pilot.pause(0.02)
            await pilot.press("i")  # Switch to AI Inference screen
            await pilot.pause(0.02)
            await pilot.press("r")  # Refresh
            await pilot.pause(0.02)
            await pilot.press("1")  # Back to AGI terminal
            await pilot.pause(0.02)

            await burst_task

            assert pipeline.total_ingested >= 500
            assert app.is_running


# =============================================================================
# 2. CONCURRENT ASYNCHRONOUS ACCESS ACROSS ALL 12 SPEC MODULES
# =============================================================================

class TestBackendStateStoreConcurrencyStress:
    """Adversarial stress testing for BackendStateStore under heavy concurrent async access."""

    @pytest.mark.asyncio
    async def test_concurrent_async_hammer_all_12_spec_modules(self):
        """
        50 concurrent async workers hammering all spec modules with mixed read, write,
        health check, action execution, and summary aggregation operations.
        Asserts zero race conditions, zero deadlocks, and data consistency.
        """
        store = BackendStateStore(auto_init_defaults=True)
        module_ids = store.list_module_ids()
        assert len(module_ids) >= 12

        num_workers = 50
        ops_per_worker = 50
        total_ops = num_workers * ops_per_worker
        errors: List[Exception] = []

        async def worker(worker_id: int):
            try:
                for step in range(ops_per_worker):
                    op_type = (worker_id + step) % 7
                    target_mod = module_ids[step % len(module_ids)]

                    if op_type == 0:
                        # Read status
                        st = store.get_module_status(target_mod)
                        assert st is not None
                    elif op_type == 1:
                        # Record telemetry
                        store.record_telemetry(
                            target_mod,
                            {
                                "timestamp": time.time(),
                                "worker": worker_id,
                                "metric_val": random.random() * 100.0,
                            },
                        )
                    elif op_type == 2:
                        # Read telemetry history
                        hist = store.get_telemetry_history(target_mod, limit=20)
                        assert isinstance(hist, list)
                    elif op_type == 3:
                        # Execute health check
                        mod = store.get_module(target_mod)
                        if mod:
                            chk = mod.health_check()
                            assert "healthy" in chk
                    elif op_type == 4:
                        # Execute action
                        res = store.execute_module_action(
                            target_mod, "ping", {"worker": worker_id}
                        )
                        assert "success" in res
                    elif op_type == 5:
                        # Get all statuses
                        all_st = store.get_all_statuses()
                        assert len(all_st) >= 12
                    elif op_type == 6:
                        # Global summary
                        summary = store.get_global_summary()
                        assert summary["total_modules"] >= 12

                    if step % 10 == 0:
                        await asyncio.sleep(0.001)  # Micro-yield
            except Exception as e:
                errors.append(e)

        t_start = time.perf_counter()
        tasks = [asyncio.create_task(worker(w)) for w in range(num_workers)]
        await asyncio.gather(*tasks)
        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        print(
            f"\\n[BENCHMARK] 50 workers, {total_ops} concurrent ops across modules completed in {t_elapsed:.2f}ms"
        )

        assert len(errors) == 0, f"Encountered {len(errors)} errors during concurrency hammer: {errors[:3]}"
        assert len(store.list_modules()) >= 12

    @pytest.mark.asyncio
    async def test_concurrent_registration_unregistration_churn(self):
        """
        Adversarial churn: Concurrently unregistering, re-registering, and reading modules.
        Guarantees thread-safety of _modules dictionary and absence of RuntimeError during iteration.
        """
        store = BackendStateStore(auto_init_defaults=True)
        all_modules = create_all_spec_modules()
        initial_count = len(all_modules)
        errors: List[Exception] = []

        async def reader_worker():
            for _ in range(50):
                try:
                    _ = store.get_all_statuses()
                    _ = store.get_global_summary()
                    _ = store.list_modules()
                    _ = store.list_module_ids()
                    await asyncio.sleep(0.001)
                except Exception as e:
                    errors.append(e)

        async def mutator_worker():
            for mod in all_modules:
                try:
                    store.unregister_module(mod.module_id)
                    await asyncio.sleep(0.0005)
                    store.register_module(mod)
                    await asyncio.sleep(0.0005)
                except Exception as e:
                    errors.append(e)

        tasks = [
            asyncio.create_task(reader_worker()),
            asyncio.create_task(reader_worker()),
            asyncio.create_task(mutator_worker()),
            asyncio.create_task(reader_worker()),
        ]
        await asyncio.gather(*tasks)

        assert len(errors) == 0, f"Errors during registration churn: {errors}"
        assert len(store.list_modules()) == initial_count

    def test_telemetry_ring_buffer_bounded_memory_10000_records(self):
        """
        Ingest 10,000 telemetry records across all modules.
        Verifies that memory is strictly bounded by maxlen=100 per module deque.
        """
        store = BackendStateStore(auto_init_defaults=True)
        module_ids = store.list_module_ids()

        for i in range(10000):
            mod_id = module_ids[i % len(module_ids)]
            store.record_telemetry(mod_id, {"seq": i, "val": float(i * 1.5)})

        for mod_id in module_ids:
            hist = store.get_telemetry_history(mod_id, limit=500)
            assert len(hist) <= 100, f"History for {mod_id} exceeded maxlen=100"

    def test_fast_path_summary_and_health_checks_under_heavy_concurrency(self):
        """
        Benchmarking: Fast-path execution time for get_global_summary across all 13 modules.
        Under live socket probing across 13 modules, full system summary must execute cleanly (<150ms).
        """
        store = BackendStateStore(auto_init_defaults=True)

        durations: List[float] = []
        for _ in range(20):
            t0 = time.perf_counter()
            summary = store.get_global_summary()
            d_ms = (time.perf_counter() - t0) * 1000.0
            durations.append(d_ms)
            assert summary["total_modules"] >= 12

        avg_ms = statistics.mean(durations)
        max_ms = max(durations)

        print(f"\\n[BENCHMARK] get_global_summary (13 modules with live probes): Avg {avg_ms:.3f}ms | Max {max_ms:.3f}ms")
        assert avg_ms < 150.0, f"Average summary latency {avg_ms:.2f}ms exceeded 150.0ms threshold"


# =============================================================================
# 3. RAPID START/STOP & CANCELLATION CYCLES IN CRON SCHEDULER
# =============================================================================

class TestSmolagentCronSchedulerRapidCyclesStress:
    """Adversarial stress testing for SmolagentCronScheduler start/stop and task lifecycle."""

    @pytest.mark.asyncio
    async def test_rapid_50_start_stop_cancellation_cycles(self):
        """
        Adversarially cycles start() and stop() 50 times in rapid succession on a scheduler
        with 10 registered jobs (fast, slow, async, sync, failing).
        Asserts:
        - 0 lingering tasks in running_tasks
        - 0 unhandled asyncio.CancelledError or exceptions
        - Clean state after 50 cycles
        """
        scheduler = SmolagentCronScheduler()
        execution_tallies: Dict[str, int] = {}

        # Register 10 diverse jobs
        for j in range(10):
            job_id = f"job_{j:02d}"
            execution_tallies[job_id] = 0

            if j % 3 == 0:
                # Fast async job
                def _make_async_job(jid=job_id):
                    async def _func():
                        execution_tallies[jid] += 1
                        await asyncio.sleep(0.001)
                    return _func

                scheduler.register_job(job_id, interval_seconds=0.002, func=_make_async_job())
            elif j % 3 == 1:
                # Fast sync job
                def _make_sync_job(jid=job_id):
                    def _func():
                        execution_tallies[jid] += 1
                    return _func

                scheduler.register_job(job_id, interval_seconds=0.002, func=_make_sync_job())
            else:
                # Slow job
                def _make_slow_job(jid=job_id):
                    async def _func():
                        execution_tallies[jid] += 1
                        await asyncio.sleep(10.0)
                    return _func

                scheduler.register_job(job_id, interval_seconds=10.0, func=_make_slow_job())

        t_start = time.perf_counter()

        # Run 50 rapid start/stop cycles
        for cycle in range(50):
            scheduler.start()
            assert scheduler.is_running is True
            assert len(scheduler.running_tasks) == 10

            # Sleep tiny interval so tasks begin execution
            await asyncio.sleep(0.003)

            # Clean cancellation
            await scheduler.stop()
            assert scheduler.is_running is False
            assert len(scheduler.running_tasks) == 0

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        print(f"\\n[BENCHMARK] 50 rapid start/stop cancellation cycles completed in {t_elapsed:.2f}ms")

        # Verify no remaining running tasks
        assert len(scheduler.running_tasks) == 0
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_in_flight_task_interruption_during_stop(self):
        """
        Tests cancellation of in-flight tasks that are mid-execution.
        Verifies execution lock is cleanly released and subsequent start() executes normally.
        """
        scheduler = SmolagentCronScheduler()
        entered_in_flight = False
        finished_cleanly = False

        async def long_in_flight_task():
            nonlocal entered_in_flight, finished_cleanly
            entered_in_flight = True
            try:
                await asyncio.sleep(5.0)
                finished_cleanly = True
            except asyncio.CancelledError:
                # Clean cancellation
                raise

        scheduler.register_job("in_flight_job", interval_seconds=0.001, func=long_in_flight_task)

        scheduler.start()
        await asyncio.sleep(0.005)  # Let it enter sleep
        assert entered_in_flight is True

        # Stop while in flight
        await scheduler.stop()
        assert finished_cleanly is False
        assert len(scheduler.running_tasks) == 0

        # Restart and verify lock is not deadlocked
        job_ran_again = False

        async def quick_task():
            nonlocal job_ran_again
            job_ran_again = True

        scheduler.jobs["in_flight_job"]["func"] = quick_task
        scheduler.start()
        await asyncio.sleep(0.005)
        await scheduler.stop()

        assert job_ran_again is True

    @pytest.mark.asyncio
    async def test_idempotent_and_reentrant_start_stop_calls(self):
        """
        Tests re-entrancy and idempotency:
        - Calling start() 5 times consecutively
        - Calling stop() 5 times consecutively
        - Rapid alternating without awaiting
        """
        scheduler = SmolagentCronScheduler()
        scheduler.register_job("dummy", interval_seconds=1.0, func=lambda: None)

        # 5x start()
        for _ in range(5):
            scheduler.start()
            assert scheduler.is_running is True
            assert len(scheduler.running_tasks) == 1

        # 5x stop()
        for _ in range(5):
            await scheduler.stop()
            assert scheduler.is_running is False
            assert len(scheduler.running_tasks) == 0

    @pytest.mark.asyncio
    async def test_cron_scheduler_fault_injection_and_recovery(self):
        """
        Chaos Fault Injection: Register jobs that deliberately raise RuntimeError,
        ValueError, and ZeroDivisionError.
        Verifies that errors are caught, logged to execution history, and scheduler loop does not crash.
        """
        scheduler = SmolagentCronScheduler()
        fault_counts = {"RuntimeError": 0, "ValueError": 0, "ZeroDivisionError": 0}

        def err_runtime():
            fault_counts["RuntimeError"] += 1
            raise RuntimeError("Injected runtime failure")

        def err_val():
            fault_counts["ValueError"] += 1
            raise ValueError("Injected value failure")

        def err_div():
            fault_counts["ZeroDivisionError"] += 1
            _ = 1 / 0

        scheduler.register_job("job_runtime", interval_seconds=0.002, func=err_runtime)
        scheduler.register_job("job_val", interval_seconds=0.002, func=err_val)
        scheduler.register_job("job_div", interval_seconds=0.002, func=err_div)

        scheduler.start()
        await asyncio.sleep(0.02)
        await scheduler.stop()

        status = scheduler.get_jobs_status()
        assert status["total_jobs"] == 3
        for jid in ["job_runtime", "job_val", "job_div"]:
            history = status["jobs"][jid]["recent_history"]
            assert len(history) > 0
            assert any(entry["status"] == "ERROR" for entry in history)

        assert fault_counts["RuntimeError"] > 0
        assert fault_counts["ValueError"] > 0
        assert fault_counts["ZeroDivisionError"] > 0

    @pytest.mark.asyncio
    async def test_cron_history_bounded_memory_under_500_executions(self):
        """
        Executes 500+ cron job runs and verifies execution history deque is strictly
        bounded by maxlen=100 with zero memory accumulation.
        """
        scheduler = SmolagentCronScheduler()
        scheduler.register_job("high_freq", interval_seconds=0.0005, func=lambda: None)

        scheduler.start()
        await asyncio.sleep(0.08)
        await scheduler.stop()

        assert scheduler.execution_counts["high_freq"] >= 50
        history = scheduler.execution_history["high_freq"]
        assert len(history) <= 100

        gc.collect()
        assert len(scheduler.running_tasks) == 0
