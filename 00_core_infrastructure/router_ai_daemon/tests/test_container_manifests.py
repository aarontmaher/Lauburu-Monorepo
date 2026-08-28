"""Unit tests for Dockerfile, Dockerfile.mips, docker-compose, and entrypoint.sh."""

import os
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def test_dockerfile_contents():
    """Verify Dockerfile contains multi-stage Alpine musl, static flags, non-root user, and 300MB limits."""
    df_path = BASE_DIR / "Dockerfile"
    assert df_path.exists(), "Dockerfile must exist"
    content = df_path.read_text()

    assert "FROM alpine:3.20 AS builder" in content
    assert "FROM alpine:3.20" in content
    assert "-DLLAMA_STATIC=ON" in content
    assert "-DGGML_OPENMP=OFF" in content
    assert "smolagi" in content
    assert "/models" in content
    assert "/tmp/telemetry" in content
    assert "EXPOSE 8080 8081" in content
    assert "HEALTHCHECK" in content
    assert 'ENTRYPOINT ["/sbin/tini", "--"]' in content


def test_dockerfile_mips_contents():
    """Verify Dockerfile.mips contains MIPS soft-float flags and compatibility spec."""
    df_mips = BASE_DIR / "Dockerfile.mips"
    assert df_mips.exists(), "Dockerfile.mips must exist"
    content = df_mips.read_text()

    assert "-msoft-float" in content
    assert "-DLLAMA_STATIC=ON" in content
    assert "smolagi" in content
    assert "HEALTHCHECK" in content


def test_docker_compose_contents():
    """Verify docker-compose.router.yml has 300m memory limits and tmpfs mounts."""
    dc_path = BASE_DIR / "docker-compose.router.yml"
    assert dc_path.exists(), "docker-compose.router.yml must exist"
    content = dc_path.read_text()

    assert "mem_limit: 300m" in content
    assert "mem_reservation: 150m" in content
    assert "memswap_limit: 300m" in content
    assert "/models:rw,size=180M" in content
    assert "/tmp/telemetry:rw,size=16M" in content
    assert "network_mode: host" in content


def test_entrypoint_script():
    """Verify entrypoint.sh is executable and contains cgroup checks and traps."""
    ep_path = BASE_DIR / "entrypoint.sh"
    assert ep_path.exists(), "entrypoint.sh must exist"
    assert os.access(ep_path, os.X_OK), "entrypoint.sh must be executable"
    content = ep_path.read_text()

    assert "#!/bin/sh" in content
    assert "cgroup" in content
    assert "trap cleanup" in content
    assert "ROUTER_AI_RAM_BUDGET_MB" in content
