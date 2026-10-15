"""
Pytest Fixtures for Canonical Mesh Fallback Terminal E2E Test Suite.
Adheres strictly to Rule 0 (Zero-Mock): ZERO mock library imports.
All fixtures use authentic OS scripts, genuine network sockets, and temporary files.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator, Tuple

import pytest

# Ensure app and mesh_healer package are in sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tests.e2e_mesh_fallback.fixtures.loopback_factory import (
    get_unused_port,
    start_async_tcp_server,
    start_sync_tcp_server,
)


@pytest.fixture
def fixtures_dir() -> Path:
    """Returns absolute path to fixtures directory."""
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def mock_rish_path(fixtures_dir: Path) -> str:
    """Returns absolute path to executable mock_rish.sh."""
    p = fixtures_dir / "mock_rish.sh"
    assert p.exists() and os.access(str(p), os.X_OK)
    return str(p)


@pytest.fixture
def mock_ssh_path(fixtures_dir: Path) -> str:
    """Returns absolute path to executable mock_ssh.sh."""
    p = fixtures_dir / "mock_ssh.sh"
    assert p.exists() and os.access(str(p), os.X_OK)
    return str(p)


@pytest.fixture
def mock_mosh_path(fixtures_dir: Path) -> str:
    """Returns absolute path to executable mock_mosh.sh."""
    p = fixtures_dir / "mock_mosh.sh"
    assert p.exists() and os.access(str(p), os.X_OK)
    return str(p)


@pytest.fixture
def mock_tmux_path(fixtures_dir: Path) -> str:
    """Returns absolute path to executable mock_tmux.sh."""
    p = fixtures_dir / "mock_tmux.sh"
    assert p.exists() and os.access(str(p), os.X_OK)
    return str(p)


@pytest.fixture
def audit_log(tmp_path: Path) -> str:
    """Provides a clean temporary audit log file path."""
    log_file = tmp_path / "execution_audit.log"
    return str(log_file)


@pytest.fixture
def dead_port() -> int:
    """Returns an unused TCP port with no server listening."""
    return get_unused_port()


import pytest_asyncio

@pytest_asyncio.fixture
async def live_tcp_server() -> AsyncGenerator[Tuple[str, int], None]:
    """Provides a genuine running TCP server on 127.0.0.1 on an ephemeral port."""
    async with start_async_tcp_server() as (host, port):
        yield host, port


@pytest.fixture
def sync_live_tcp_server() -> Generator[Tuple[str, int], None, None]:
    """Provides a genuine running sync TCP server on 127.0.0.1 on an ephemeral port."""
    with start_sync_tcp_server() as (host, port):
        yield host, port
