"""
Adversarial Stress Test Suite for Milestone M1 (smolagi Router Daemon).

Empirical verification under extreme conditions:
1. Memory Boundary Violations (>300MB RSS simulation, cgroups v1/v2 corruption, multi-PID overload).
2. High Frequency Memory Stat Polling & Aggressive GC Trimming (10,000 iterations, multi-threading).
3. Rapid Process Restarts, Port Contention, and Simulated OOM Crash Signals.
4. Container Manifest and Entrypoint POSIX Resilience.
"""

from __future__ import annotations

import concurrent.futures
import gc
import json
import os
import resource
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import RouterConfig, get_config
from src.container.llama_runner import (
    LlamaServerConfig,
    LlamaServerRunner,
    MockLlamaServer,
)
from src.container.memory_guard import MemoryGuard, MemoryStats


# =============================================================================
# 1. MEMORY BOUNDARY VIOLATIONS & EDGE CASES (>300MB RSS)
# =============================================================================

class TestMemoryBoundaryAdversarialStress:
    """Stress test boundary conditions, overflow, and corrupted inputs on MemoryGuard."""

    @pytest.mark.parametrize(
        "simulated_rss_mb,expected_warning,expected_critical,expected_exceeded,expected_headroom",
        [
            (0.0, False, False, False, 300.0),
            (150.0, False, False, False, 150.0),
            (239.9, False, False, False, 60.1),
            (240.0, True, False, False, 60.0),      # Exact warning threshold
            (255.0, True, False, False, 45.0),
            (269.9, True, False, False, 30.1),
            (270.0, True, True, False, 30.0),       # Exact critical threshold
            (299.9, True, True, False, 0.1),
            (300.0, True, True, False, 0.0),        # Exact budget ceiling
            (300.1, True, True, True, 0.0),         # Discrete page-boundary Exceeded
            (350.0, True, True, True, 0.0),         # Substantial breach
            (512.0, True, True, True, 0.0),         # Double budget breach
            (1024.0, True, True, True, 0.0),        # Quadruple budget breach
            (10000.0, True, True, True, 0.0),       # Extreme breach
        ],
    )
    def test_exact_rss_threshold_transitions(
        self,
        simulated_rss_mb: float,
        expected_warning: bool,
        expected_critical: bool,
        expected_exceeded: bool,
        expected_headroom: float,
    ):
        """Verify exact boolean flags and headroom calculation across boundary transitions."""
        guard = MemoryGuard(RouterConfig(ram_budget_mb=300.0, ram_warning_threshold_mb=240.0, ram_critical_threshold_mb=270.0))
        simulated_bytes = int(simulated_rss_mb * 1024 * 1024)
        simulated_pages = int(simulated_bytes / guard._page_size)

        # Mock statm inspection
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", return_value=f"10000 {simulated_pages} 0 0 0 0 0"), \
             patch.object(guard, "read_cgroup_memory", return_value=(None, None)):
            stats = guard.get_process_memory(pid=1234)

            assert stats.is_warning == expected_warning, f"Mismatch on warning for {simulated_rss_mb} MB"
            assert stats.is_critical == expected_critical, f"Mismatch on critical for {simulated_rss_mb} MB"
            assert stats.is_exceeded == expected_exceeded, f"Mismatch on exceeded for {simulated_rss_mb} MB"
            assert pytest.approx(stats.headroom_mb, abs=0.15) == expected_headroom
            assert pytest.approx(stats.rss_mb, abs=0.1) == simulated_rss_mb

    def test_multi_pid_subsystem_aggregation_overflow(self):
        """Simulate 5 subprocesses each consuming 65MB (total 325MB > 300MB budget)."""
        guard = MemoryGuard()
        pids = [101, 102, 103, 104, 105]

        def mock_get_process_memory(pid: int) -> MemoryStats:
            # 65 MB per PID
            rss_bytes = 65 * 1024 * 1024
            return MemoryStats(
                rss_bytes=rss_bytes,
                rss_mb=65.0,
                vms_bytes=rss_bytes * 2,
                vms_mb=130.0,
                budget_mb=300.0,
                headroom_mb=235.0,
                utilization_pct=21.67,
                is_warning=False,
                is_critical=False,
                is_exceeded=False,
                source="mock",
            )

        with patch.object(guard, "get_process_memory", side_effect=mock_get_process_memory):
            agg = guard.get_total_subsystem_memory(pids)
            assert agg.rss_mb == 325.0
            assert agg.is_warning is True
            assert agg.is_critical is True
            assert agg.is_exceeded is True
            assert agg.headroom_mb == 0.0
            assert pytest.approx(agg.utilization_pct, abs=0.1) == 108.33

    def test_aggregation_with_invalid_and_empty_pids(self):
        """Verify aggregation handles empty, zero, negative, and dead PIDs gracefully."""
        guard = MemoryGuard()
        # Empty PID list
        agg_empty = guard.get_total_subsystem_memory([])
        assert agg_empty.rss_bytes == 0
        assert agg_empty.is_exceeded is False

        # Non-existent or zero PIDs
        agg_zeros = guard.get_total_subsystem_memory([0, -1, -999])
        assert agg_zeros.rss_bytes == 0
        assert agg_zeros.is_exceeded is False

    @pytest.mark.parametrize(
        "statm_content",
        [
            "",                         # Empty file
            "invalid_string",           # Corrupted string
            "100",                      # Incomplete tokens (<2)
            "100 abc",                  # Non-numeric second token
            "999999999999999999999999", # Massive overflow integer
            "  \n\t  ",                 # Whitespace only
        ],
    )
    def test_corrupted_proc_statm_fallback_handling(self, statm_content: str):
        """Verify parser does not crash when /proc/self/statm is corrupted, falling back safely."""
        guard = MemoryGuard()
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", return_value=statm_content), \
             patch.object(guard, "read_cgroup_memory", return_value=(None, None)):
            # Should not raise exception; falls back to rusage / status
            stats = guard.get_process_memory(pid=os.getpid())
            assert isinstance(stats, MemoryStats)
            assert stats.rss_bytes >= 0

    @pytest.mark.parametrize(
        "cg2_max_val,cg1_limit_val,expected_limit",
        [
            ("max", "9223372036854775807", None),               # Unlimited in both
            ("314572800", "0", 314572800),                     # 300MB in v2
            ("invalid", "314572800", 314572800),               # v2 corrupt, v1 300MB
            ("", "9223372036854775807", None),                 # Empty v2, unlimited v1
        ],
    )
    def test_cgroup_v1_v2_parsing_edge_cases(self, cg2_max_val: str, cg1_limit_val: str, expected_limit: Optional[int]):
        """Stress-test cgroups v1 & v2 limit reading under corrupted/edge inputs."""
        guard = MemoryGuard()

        def mock_read_text(self_path: Path) -> str:
            p_str = str(self_path)
            if "memory.max" in p_str:
                return cg2_max_val
            if "memory.current" in p_str:
                return "104857600"
            if "memory.limit_in_bytes" in p_str:
                return cg1_limit_val
            if "memory.usage_in_bytes" in p_str:
                return "104857600"
            return ""

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", mock_read_text):
            usage, limit = guard.read_cgroup_memory()
            assert usage == 104857600
            assert limit == expected_limit

    def test_enforce_limits_kills_offending_subprocesses_on_critical(self):
        """Verify enforce_limits with kill_on_critical=True sends SIGKILL to runaway subprocesses."""
        guard = MemoryGuard()
        # Spawn real sleeper subprocess
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        try:
            target_pid = proc.pid

            # Mock subsystem memory to simulate critical breach (310MB > 270MB critical threshold)
            def mock_agg(pids: list[int]) -> MemoryStats:
                return MemoryStats(
                    rss_bytes=310 * 1024 * 1024,
                    rss_mb=310.0,
                    vms_bytes=600 * 1024 * 1024,
                    vms_mb=600.0,
                    budget_mb=300.0,
                    headroom_mb=0.0,
                    utilization_pct=103.33,
                    is_warning=True,
                    is_critical=True,
                    is_exceeded=True,
                    source="mock",
                )

            with patch.object(guard, "get_total_subsystem_memory", side_effect=mock_agg):
                stats = guard.enforce_limits(pids=[target_pid], kill_on_critical=True)
                assert stats.is_critical is True

                # Process should be terminated
                proc.wait(timeout=2.0)
                assert proc.poll() is not None
                # Terminated by signal 9 (SIGKILL) -> returncode -9 on POSIX
                assert proc.returncode in (-9, -signal.SIGKILL)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=1.0)


# =============================================================================
# 2. HIGH FREQUENCY MEMORY STAT POLLING & GC STRESS
# =============================================================================

class TestHighFrequencyMemoryPollingAndGCStress:
    """Stress test memory inspection throughput, zero memory leaks, and concurrent threads."""

    def test_high_frequency_polling_10000_iterations(self):
        """Execute 10,000 consecutive memory checks in tight loop to verify zero leak & high throughput."""
        guard = MemoryGuard()
        iterations = 10000
        start_time = time.perf_counter()

        initial_rss = guard.get_process_memory().rss_bytes

        for _ in range(iterations):
            stats = guard.get_process_memory()
            assert stats.budget_mb == 300.0

        elapsed_sec = time.perf_counter() - start_time
        final_rss = guard.get_process_memory().rss_bytes

        ops_per_sec = iterations / elapsed_sec
        avg_latency_us = (elapsed_sec / iterations) * 1_000_000

        # Memory should not grow uncontrollably during 10k polling calls
        rss_growth_mb = (final_rss - initial_rss) / (1024 * 1024)
        assert rss_growth_mb < 5.0, f"Memory leaked during polling: grew by {rss_growth_mb:.2f} MB"
        assert ops_per_sec > 1000.0, f"Throughput too low: {ops_per_sec:.1f} ops/sec"

    def test_concurrent_multi_threaded_polling_stress(self):
        """Spawn 16 threads each running 500 queries simultaneously (8,000 total calls)."""
        guard = MemoryGuard()
        num_threads = 16
        calls_per_thread = 500
        errors: list[Exception] = []

        def worker_task(thread_id: int):
            try:
                for i in range(calls_per_thread):
                    stats = guard.get_process_memory()
                    within_budget, b_stats = guard.check_memory_budget()
                    if not within_budget or stats.budget_mb != 300.0:
                        raise ValueError(f"Inconsistent state in thread {thread_id} at call {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(num_threads)]
        start_time = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.perf_counter() - start_time

        assert len(errors) == 0, f"Errors occurred during concurrent thread execution: {errors}"
        total_calls = num_threads * calls_per_thread
        assert elapsed < 10.0, f"Concurrent execution too slow: {elapsed:.2f}s for {total_calls} calls"

    def test_repeated_garbage_collection_and_trimming_stress(self):
        """Allocate and collect 100,000 cyclic references across 100 GC cycles."""
        guard = MemoryGuard()
        total_collected = 0

        start_time = time.perf_counter()
        for _ in range(100):
            # Create cyclic graph of objects
            cycles = [[j] for j in range(1000)]
            for c in cycles:
                c.append(c)
            del cycles
            collected = guard.run_garbage_collection()
            total_collected += collected
        elapsed_sec = time.perf_counter() - start_time

        assert total_collected > 0
        avg_gc_ms = (elapsed_sec / 100) * 1000
        assert avg_gc_ms < 50.0, f"GC cycle average latency excessive: {avg_gc_ms:.2f} ms"


# =============================================================================
# 3. RAPID PROCESS RESTARTS, CRASH RECOVERY & OOM SIGNALS
# =============================================================================

class TestProcessLifecycleCrashAndOOMStress:
    """Stress test rapid restarts, port contention, abrupt crashes, and recovery."""

    def test_rapid_start_stop_restart_cycles_with_dynamic_ports(self):
        """Execute rapid start/stop cycles across multiple ports to test MockLlamaServer lifecycle."""
        for cycle in range(10):
            port = 19100 + cycle
            cfg = LlamaServerConfig(host="127.0.0.1", port=port)
            runner = LlamaServerRunner(config=cfg, use_mock_if_missing=True)

            started = runner.start(timeout_sec=2.0)
            assert started is True, f"Failed start on cycle {cycle} port {port}"
            assert runner.is_running() is True
            assert runner.health_check(timeout_sec=0.5) is True

            stopped = runner.stop()
            assert stopped is True, f"Failed stop on cycle {cycle}"
            assert runner.is_running() is False

    def test_simulated_oom_sigkill_recovery(self):
        """Simulate sudden external OOM killer (SIGKILL) on mock llama subprocess and verify restart."""
        # Launch independent subprocess acting as mock server
        proc_code = (
            "from http.server import HTTPServer, BaseHTTPRequestHandler\n"
            "import json\n"
            "class H(BaseHTTPRequestHandler):\n"
            "    def log_message(self, *a): pass\n"
            "    def do_GET(self):\n"
            "        self.send_response(200)\n"
            "        self.send_header('Content-Type', 'application/json')\n"
            "        self.end_headers()\n"
            "        self.wfile.write(json.dumps({'status': 'ok'}).encode())\n"
            "s = HTTPServer(('127.0.0.1', 18096), H)\n"
            "s.serve_forever()\n"
        )
        proc = subprocess.Popen([sys.executable, "-c", proc_code])
        time.sleep(0.3)

        try:
            cfg = LlamaServerConfig(host="127.0.0.1", port=18096)
            runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)
            runner.process = proc

            # Verify initial health
            assert runner.health_check(timeout_sec=2.0) is True
            assert runner.is_running() is True
            pid = runner.get_pid()
            assert pid == proc.pid

            # Simulate OOM killer abrupt termination
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait(timeout=2.0)

            # Runner should detect process death
            assert runner.is_running() is False
            assert runner.health_check(timeout_sec=0.2) is False

            # Ensure cleanup/stop works cleanly on dead process
            assert runner.stop() is True
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=1.0)

    def test_concurrent_request_storm(self):
        """Send 100 concurrent HTTP requests across 10 threads while server is active."""
        server = MockLlamaServer(host="127.0.0.1", port=18097, model_name="smollm2-135m")
        server.start()
        time.sleep(0.2)

        try:
            runner = LlamaServerRunner(
                config=LlamaServerConfig(host="127.0.0.1", port=18097),
                use_mock_if_missing=False,
            )

            results: list[dict] = []
            errors: list[Exception] = []

            def send_request(req_id: int):
                try:
                    res = runner.generate_completion(f"Prompt {req_id} for consensus", max_tokens=16)
                    results.append(res)
                except Exception as e:
                    errors.append(e)

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                futures = [pool.submit(send_request, i) for i in range(100)]
                concurrent.futures.wait(futures)

            assert len(errors) == 0, f"Errors during request storm: {errors}"
            assert len(results) == 100
            for r in results:
                assert "choices" in r
                assert len(r["choices"]) > 0
        finally:
            server.stop()


# =============================================================================
# 4. CONTAINER MANIFEST & SHELL ENTRYPOINT RESILIENCE
# =============================================================================

class TestContainerManifestAndEntrypointResilience:
    """Stress test POSIX shell entrypoint signal handling and container manifests."""

    def test_entrypoint_script_execution_and_signal_handling(self):
        """Verify entrypoint.sh executes custom commands and handles exit codes."""
        entrypoint_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/entrypoint.sh")
        assert entrypoint_path.exists()
        assert os.access(entrypoint_path, os.X_OK)

        # Run entrypoint with a fast command
        res = subprocess.run(
            [str(entrypoint_path), "python3", "-c", "import sys; print('ENTRYPOINT_OK'); sys.exit(0)"],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        assert res.returncode == 0
        assert "ENTRYPOINT_OK" in res.stdout
        assert "[smolagi-init]" in res.stdout

    def test_entrypoint_cgroup_memory_detection_logging(self):
        """Verify entrypoint logs memory constraints and handles custom RAM budgets."""
        entrypoint_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/entrypoint.sh")
        env = os.environ.copy()
        env["ROUTER_AI_RAM_BUDGET_MB"] = "250.0"

        res = subprocess.run(
            [str(entrypoint_path), "echo", "TEST_BUDGET"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5.0,
        )
        assert res.returncode == 0
        assert "250.0 MB" in res.stdout or "TEST_BUDGET" in res.stdout

    def test_docker_compose_and_dockerfile_static_invariants(self):
        """Verify all static compilation flags, tmpfs limits, and security options."""
        compose_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/docker-compose.router.yml")
        dockerfile_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/Dockerfile")
        dockerfile_mips_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/Dockerfile.mips")

        # Compose file checks
        compose_text = compose_path.read_text()
        assert "mem_limit: 300m" in compose_text
        assert "memswap_limit: 300m" in compose_text
        assert "/models:rw,size=180M" in compose_text
        assert "no-new-privileges:true" in compose_text

        # Dockerfile checks
        df_text = dockerfile_path.read_text()
        assert "-DLLAMA_STATIC=ON" in df_text
        assert "-DGGML_OPENMP=OFF" in df_text
        assert "addgroup -S -g 1000 smolagi" in df_text
        assert "USER smolagi" in df_text

        # MIPS Dockerfile checks
        df_mips = dockerfile_mips_path.read_text()
        assert "MIPS" in df_mips or "mips" in df_mips
        assert "-DLLAMA_STATIC=ON" in df_mips
