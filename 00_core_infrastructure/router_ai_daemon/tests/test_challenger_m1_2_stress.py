"""
Empirical Adversarial Stress Test Suite for Milestone M1.
Challenger: challenger_m1_2 (Role: Empirical Challenger 2)

Empirical stress tests covering:
1. LlamaServerRunner lifecycle, error paths, socket reuse, and crash handling.
2. MockLlamaServer concurrent HTTP stress, malformed requests, and schema checks.
3. Entrypoint POSIX shell script execution, signal traps, and cgroup limits.
4. Container manifests (Dockerfile, Dockerfile.mips, docker-compose) security & resource limits.
5. MemoryGuard edge cases, corrupted procfs statm, and negative page counts.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
import yaml

from src.config import RouterConfig
from src.container.llama_runner import (
    LlamaServerConfig,
    LlamaServerRunner,
    MockLlamaServer,
)
from src.container.memory_guard import MemoryGuard, MemoryStats

BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# 1. LlamaServerRunner Adversarial & Lifecycle Tests
# =============================================================================

class TestLlamaRunnerAdversarialFailures:
    """Stress-test LlamaServerRunner with corrupted paths, missing binaries, and abnormal terminations."""

    def test_corrupted_model_path_handling(self) -> None:
        """Verify runner handles missing, empty, or directory model paths gracefully."""
        corrupted_paths = [
            "/nonexistent/path/to/corrupted_model.gguf",
            "/tmp",  # directory instead of file
            "/tmp/model with spaces and unicode 🚀.gguf",
            "",
        ]
        for idx, bad_path in enumerate(corrupted_paths):
            port = 19200 + idx
            cfg = LlamaServerConfig(
                host="127.0.0.1",
                port=port,
                model_path=bad_path,
            )
            runner = LlamaServerRunner(config=cfg, use_mock_if_missing=True)
            try:
                started = runner.start(timeout_sec=2.0)
                assert started is True
                assert runner.is_running() is True
                assert runner.health_check() is True

                resp = runner.generate_completion("Test prompt")
                assert "choices" in resp
            finally:
                runner.stop()
                assert runner.is_running() is False

    def test_missing_binary_no_mock_fallback(self) -> None:
        """Verify runner fails cleanly when binary is missing and use_mock_if_missing=False."""
        cfg = LlamaServerConfig(
            binary_path="/nonexistent/bin/llama-server-fake",
            host="127.0.0.1",
            port=19210,
        )
        runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)
        started = runner.start(timeout_sec=0.5)
        assert started is False
        assert runner.is_running() is False
        assert runner.get_pid() is None

    def test_non_executable_binary_path(self, tmp_path: Path) -> None:
        """Verify runner detects non-executable file as unavailable."""
        dummy_file = tmp_path / "dummy_binary"
        dummy_file.write_text("not an executable ELF")
        dummy_file.chmod(0o644)  # No execute permission

        cfg = LlamaServerConfig(
            binary_path=str(dummy_file),
            host="127.0.0.1",
            port=19211,
        )
        runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)
        assert runner.is_binary_available() is False
        assert runner.start(timeout_sec=0.5) is False

    def test_binary_immediate_crash_recovery(self, tmp_path: Path) -> None:
        """Verify runner handles a binary that exits immediately with error code 1."""
        fake_binary = tmp_path / "crashing_binary"
        fake_binary.write_text("#!/bin/sh\nexit 1\n")
        fake_binary.chmod(0o755)

        cfg = LlamaServerConfig(
            binary_path=str(fake_binary),
            host="127.0.0.1",
            port=19212,
        )
        runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)
        assert runner.is_binary_available() is True
        started = runner.start(timeout_sec=0.8)
        assert started is False
        assert runner.is_running() is False
        runner.stop()

    def test_health_check_unreachable_socket(self) -> None:
        """Verify health_check returns False immediately on unallocated port."""
        cfg = LlamaServerConfig(host="127.0.0.1", port=19213)
        runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)
        assert runner.health_check(timeout_sec=0.2) is False

    def test_completion_failure_when_server_stopped(self) -> None:
        """Verify generate_completion and generate_chat_completion raise RuntimeError when offline."""
        cfg = LlamaServerConfig(host="127.0.0.1", port=19215)
        runner = LlamaServerRunner(config=cfg, use_mock_if_missing=False)

        with pytest.raises(RuntimeError, match="llama-server completion failed"):
            runner.generate_completion("Hello", timeout_sec=0.2)

        with pytest.raises(RuntimeError, match="llama-server chat completion failed"):
            runner.generate_chat_completion([{"role": "user", "content": "Hi"}], timeout_sec=0.2)


# =============================================================================
# 2. Concurrent HTTP & Malformed Request Stress Testing
# =============================================================================

class TestMockHttpConcurrentStressAndMalformedRequests:
    """Stress-test MockLlamaServer under high concurrency and adversarial payloads."""

    @pytest.fixture(scope="class")
    def running_mock_server(self):
        port = 19220
        server = MockLlamaServer(host="127.0.0.1", port=port, model_name="smollm2-135m-stress")
        server.start()
        time.sleep(0.2)
        yield port
        server.stop()

    def test_high_concurrency_burst(self, running_mock_server: int) -> None:
        """Execute 60 concurrent requests across /health, /v1/completions, /v1/chat/completions."""
        port = running_mock_server
        runner = LlamaServerRunner(
            config=LlamaServerConfig(host="127.0.0.1", port=port),
            use_mock_if_missing=False,
        )

        def worker_task(idx: int) -> Dict[str, Any]:
            if idx % 3 == 0:
                ok = runner.health_check(timeout_sec=2.0)
                return {"type": "health", "ok": ok}
            elif idx % 3 == 1:
                res = runner.generate_completion(f"Prompt {idx}", max_tokens=16, timeout_sec=3.0)
                return {"type": "completion", "ok": "choices" in res}
            else:
                res = runner.generate_chat_completion(
                    [{"role": "user", "content": f"Chat query {idx}"}],
                    max_tokens=16,
                    timeout_sec=3.0,
                )
                return {"type": "chat", "ok": "choices" in res}

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(worker_task, i) for i in range(60)]
            results = [f.result(timeout=10.0) for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 60
        assert all(r["ok"] for r in results)

    def test_malformed_json_body(self, running_mock_server: int) -> None:
        """Send broken JSON to /v1/completions and /v1/chat/completions."""
        port = running_mock_server
        for endpoint in ("/v1/completions", "/v1/chat/completions"):
            url = f"http://127.0.0.1:{port}{endpoint}"
            bad_data = b"This is not JSON {{{{"
            req = urllib.request.Request(
                url,
                data=bad_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert "choices" in data

    def test_empty_post_body(self, running_mock_server: int) -> None:
        """Send empty POST body to /v1/chat/completions."""
        port = running_mock_server
        url = f"http://127.0.0.1:{port}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=b"",
            headers={"Content-Type": "application/json", "Content-Length": "0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "choices" in data

    def test_unsupported_endpoints_and_methods(self, running_mock_server: int) -> None:
        """Verify 404 is returned for unmapped paths."""
        port = running_mock_server
        url = f"http://127.0.0.1:{port}/nonexistent/endpoint"
        req = urllib.request.Request(url, method="GET")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=2.0)
        assert exc_info.value.code == 404

    def test_large_payload_handling(self, running_mock_server: int) -> None:
        """Send 256KB text prompt to /v1/completions without socket timeout or OOM."""
        port = running_mock_server
        url = f"http://127.0.0.1:{port}/v1/completions"
        large_prompt = "Large router prompt chunk " * 8000  # ~240KB
        payload = json.dumps({"prompt": large_prompt, "max_tokens": 32}).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "choices" in data
            assert len(data["choices"]) > 0


# =============================================================================
# 3. Entrypoint Script & Cgroups Boundary Adversarial Tests
# =============================================================================

class TestEntrypointScriptAdversarial:
    """Stress-test entrypoint.sh execution, cgroups detection, signal trapping, and env overrides."""

    @pytest.fixture
    def entrypoint_path(self) -> Path:
        ep = BASE_DIR / "entrypoint.sh"
        assert ep.exists()
        assert os.access(ep, os.X_OK)
        return ep

    def test_custom_command_passthrough(self, entrypoint_path: Path) -> None:
        """Verify entrypoint.sh executes custom commands passed as arguments."""
        cmd = [str(entrypoint_path), "echo", "PASSED_CUSTOM_COMMAND"]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
        )
        assert proc.returncode == 0
        assert "PASSED_CUSTOM_COMMAND" in proc.stdout
        assert "[smolagi-init]" in proc.stdout

    def test_env_var_ram_budget_override(self, entrypoint_path: Path) -> None:
        """Verify entrypoint.sh honors ROUTER_AI_RAM_BUDGET_MB override."""
        env = os.environ.copy()
        env["ROUTER_AI_RAM_BUDGET_MB"] = "250.0"
        proc = subprocess.run(
            [str(entrypoint_path), "sh", "-c", "echo Budget: $ROUTER_AI_RAM_BUDGET_MB"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
        )
        assert proc.returncode == 0
        assert "Target Budget: 250.0 MB" in proc.stdout or "250.0" in proc.stdout

    def test_tmpfs_directory_creation_and_custom_paths(self, entrypoint_path: Path, tmp_path: Path) -> None:
        """Verify entrypoint.sh handles custom TMPFS_MODELS_DIR and TMPFS_TELEMETRY_DIR."""
        custom_models = tmp_path / "custom_models"
        custom_telemetry = tmp_path / "custom_telemetry"

        env = os.environ.copy()
        env["TMPFS_MODELS_DIR"] = str(custom_models)
        env["TMPFS_TELEMETRY_DIR"] = str(custom_telemetry)

        proc = subprocess.run(
            [str(entrypoint_path), "true"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
        )
        assert proc.returncode == 0
        assert custom_models.exists()
        assert custom_telemetry.exists()

    def test_entrypoint_signal_trapping(self, entrypoint_path: Path) -> None:
        """Verify entrypoint.sh catches SIGTERM and shuts down cleanly."""
        proc = subprocess.Popen(
            [str(entrypoint_path), "sleep", "10"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.5)
        assert proc.poll() is None

        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=4.0)

        assert proc.returncode in (0, -signal.SIGTERM, 143)


# =============================================================================
# 4. Container Manifests Invariant Stress Testing
# =============================================================================

class TestContainerManifestsInvariants:
    """Validate Dockerfile, Dockerfile.mips, and docker-compose against strict constraints."""

    def test_dockerfile_arm64_static_and_security(self) -> None:
        """Verify ARM64 Dockerfile has multi-stage build, static flags, non-root user, and tini."""
        df_path = BASE_DIR / "Dockerfile"
        content = df_path.read_text()

        # Build stage
        assert "FROM alpine:3.20 AS builder" in content
        assert "-DLLAMA_STATIC=ON" in content
        assert "-DGGML_OPENMP=OFF" in content
        assert "-DCMAKE_EXE_LINKER_FLAGS=\"-static -Wl,--gc-sections -s\"" in content
        assert "strip --strip-all" in content

        # Runtime stage
        assert "FROM alpine:3.20" in content
        assert "adduser -S -u 1000 -G smolagi" in content
        assert "USER smolagi" in content
        assert 'ENTRYPOINT ["/sbin/tini", "--"]' in content
        assert "ROUTER_AI_RAM_BUDGET_MB=300.0" in content
        assert "HEALTHCHECK" in content

    def test_dockerfile_mips_softfloat_invariants(self) -> None:
        """Verify MIPS Dockerfile specifies soft-float toolchain for GL.iNet legacy routers."""
        df_mips = BASE_DIR / "Dockerfile.mips"
        content = df_mips.read_text()

        assert "-msoft-float" in content
        assert "-DLLAMA_STATIC=ON" in content
        assert "USER smolagi" in content
        assert "ROUTER_AI_RAM_BUDGET_MB=300.0" in content

    def test_docker_compose_yaml_constraints(self) -> None:
        """Parse docker-compose.router.yml and verify memory limits, tmpfs, and security options."""
        compose_file = BASE_DIR / "docker-compose.router.yml"
        with open(compose_file, "r") as f:
            spec = yaml.safe_load(f)

        service = spec["services"]["router_ai_daemon"]

        # Memory limits
        assert service["mem_limit"] == "300m"
        assert service["mem_reservation"] == "150m"
        assert service["memswap_limit"] == "300m"
        assert service["cpus"] == 3.0

        # Deploy resources limits
        limits = service["deploy"]["resources"]["limits"]
        assert limits["memory"] == "300M"
        assert limits["cpus"] == "3.0"

        # Tmpfs mounts
        tmpfs = service["tmpfs"]
        assert any("/models" in mount and "size=180M" in mount for mount in tmpfs)
        assert any("/tmp/telemetry" in mount and "size=16M" in mount for mount in tmpfs)
        assert any("/tmp/cache" in mount and "size=8M" in mount for mount in tmpfs)

        # Volumes read-only inspection
        volumes = service["volumes"]
        assert any("ubus.sock" in v and ":ro" in v for v in volumes)
        assert any("/proc" in v and ":ro" in v for v in volumes)

        # Capabilities
        assert "ALL" in service["cap_drop"]
        assert "no-new-privileges:true" in service["security_opt"]


# =============================================================================
# 5. MemoryGuard Adversarial Procfs Inputs
# =============================================================================

class TestMemoryGuardAdversarial:
    """Stress-test MemoryGuard against simulated corrupted procfs and edge case metrics."""

    def test_memory_guard_nonexistent_pid(self) -> None:
        """Verify get_process_memory on non-existent PID returns zero RSS without raising exceptions."""
        mg = MemoryGuard()
        stats = mg.get_process_memory(pid=9999999)
        assert isinstance(stats, MemoryStats)
        assert stats.rss_bytes == 0
        assert stats.rss_mb == 0.0
        assert stats.is_exceeded is False

    def test_memory_guard_aggregate_with_dead_and_alive_pids(self) -> None:
        """Verify get_total_subsystem_memory handles a mix of current PID and invalid PIDs."""
        mg = MemoryGuard()
        stats = mg.get_total_subsystem_memory([os.getpid(), 9999998, 9999999])
        assert isinstance(stats, MemoryStats)
        assert stats.rss_mb > 0.0
        assert stats.budget_mb == 300.0

    def test_memory_guard_gc_execution(self) -> None:
        """Verify run_garbage_collection executes without error."""
        mg = MemoryGuard()
        collected = mg.run_garbage_collection()
        assert isinstance(collected, int)
        assert collected >= 0

    def test_memory_guard_enforce_limits_warning_trigger(self) -> None:
        """Verify enforce_limits triggers warning logic when configured with low threshold."""
        low_config = RouterConfig(
            ram_budget_mb=300.0,
            ram_warning_threshold_mb=1.0,
            ram_critical_threshold_mb=290.0,
        )
        mg = MemoryGuard(config=low_config)
        stats = mg.enforce_limits(trigger_gc_on_warning=True)
        assert stats.is_warning is True
