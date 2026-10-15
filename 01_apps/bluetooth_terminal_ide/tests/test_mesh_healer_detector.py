"""
Unit Tests for Mesh Outage Detector and 3-Cycle Debounce Filter.
Zero-mock compliance: Uses genuine local loopback TCP sockets and non-blocking asyncio.
"""

import asyncio
import os
import signal
import sys
import time
from pathlib import Path
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mesh_healer.outage_detector import MeshOutageDetector


@pytest.mark.asyncio
async def test_outage_detector_single_endpoint_live_and_dead():
    """Verifies TCP connect probe with an authentic local server and closed port."""
    detector = MeshOutageDetector(failure_threshold=3, probe_timeout=0.2)

    # 1. Start live TCP server on loopback
    async def handle_client(reader, writer):
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    try:
        # Live endpoint returns True
        is_live = await detector.probe_endpoint("127.0.0.1", port=port, timeout=0.2)
        assert is_live is True
    finally:
        server.close()
        await server.wait_closed()

    # Closed TCP port with check_ping=False returns False
    is_dead_tcp = await detector.probe_endpoint("127.0.0.1", port=port, timeout=0.2, check_ping=False)
    assert is_dead_tcp is False

    # Unreachable IP (RFC 5737 TEST-NET) with ping enabled returns False
    is_dead_ip = await detector.probe_endpoint("192.0.2.1", port=port, timeout=0.2, check_ping=True)
    assert is_dead_ip is False


@pytest.mark.asyncio
async def test_3_cycle_sliding_window_debounce():
    """Verifies that outage state is triggered strictly after 3 consecutive failed cycles."""
    outage_events = []

    def on_outage():
        outage_events.append("OUTAGE_CONFIRMED")

    # Configure targets pointing to an unreachable port
    unreachable_targets = {
        "node_1": {"tailscale": "127.0.0.1"},
        "node_2": {"nebula": "127.0.0.1"},
    }

    # Find an unused closed port
    test_server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    closed_port = test_server.sockets[0].getsockname()[1]
    test_server.close()
    await test_server.wait_closed()

    # Create detector with custom probe that fails
    detector = MeshOutageDetector(
        targets=unreachable_targets,
        failure_threshold=3,
        probe_timeout=0.1,
        on_outage_detected=on_outage,
    )

    # Override probe_endpoint to probe our closed port
    async def fail_probe(ip, port=closed_port, timeout=0.1):
        return await detector.probe_endpoint(ip, port=closed_port, timeout=0.1)

    detector.probe_endpoint = fail_probe

    # Cycle 1: failure 1/3
    alive = await detector.probe_cycle()
    assert alive is False
    assert detector.consecutive_failures == 1
    assert detector.is_outage_detected is False
    assert len(outage_events) == 0

    # Cycle 2: failure 2/3
    alive = await detector.probe_cycle()
    assert alive is False
    assert detector.consecutive_failures == 2
    assert detector.is_outage_detected is False
    assert len(outage_events) == 0

    # Cycle 3: failure 3/3 -> OUTAGE TRIGGERED
    alive = await detector.probe_cycle()
    assert alive is False
    assert detector.consecutive_failures == 3
    assert detector.is_outage_detected is True
    assert len(outage_events) == 1


@pytest.mark.asyncio
async def test_outage_recovery_callback():
    """Verifies that an active outage is reset when at least one endpoint recovers."""
    recovered_events = []

    def on_recovered():
        recovered_events.append("RECOVERED")

    # Start live TCP server
    async def handle_client(reader, writer):
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    live_port = server.sockets[0].getsockname()[1]

    detector = MeshOutageDetector(
        targets={"live_node": {"tailscale": "127.0.0.1"}},
        failure_threshold=3,
        probe_timeout=0.2,
        on_outage_recovered=on_recovered,
    )
    # Manually simulate previous outage state
    detector.consecutive_failures = 3
    detector.is_outage_detected = True

    try:
        # Override probe to hit live_port
        detector.probe_endpoint = lambda ip, port=live_port, timeout=0.2: MeshOutageDetector.probe_endpoint(
            detector, ip, port=live_port, timeout=0.2
        )

        alive = await detector.probe_cycle()
        assert alive is True
        assert detector.consecutive_failures == 0
        assert detector.is_outage_detected is False
        assert len(recovered_events) == 1
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_concurrent_parallel_gathering():
    """Verifies that multiple endpoints are probed concurrently via asyncio.gather without serial blocking."""
    targets = {f"node_{i}": {"tailscale": "127.0.0.1", "nebula": "127.0.0.1"} for i in range(5)}
    detector = MeshOutageDetector(targets=targets, failure_threshold=3, probe_timeout=0.1)

    start = time.perf_counter()
    await detector.probe_cycle()
    dur = time.perf_counter() - start

    # 10 probes with 0.1s timeout each; if run sequentially it would take >= 1.0s.
    # Concurrent execution finishes in < 0.5s.
    assert dur < 0.6


@pytest.mark.asyncio
async def test_outage_detector_kills_hung_ping_on_timeout(tmp_path: Path):
    """
    Verifies that a hanging ICMP ping subprocess is killed and reaped on timeout.
    Zero-mock: Uses authentic executable script fixture and verified kernel process state.
    """
    hang_ping = tmp_path / "hang_ping.sh"
    hang_ping.write_text("#!/bin/bash\nsleep 10\n")
    hang_ping.chmod(0o755)

    detector = MeshOutageDetector(probe_timeout=0.1)

    t0 = time.perf_counter()
    res = await detector.probe_endpoint(
        "192.0.2.1", port=54321, timeout=0.1, check_ping=True, ping_cmd=[str(hang_ping)]
    )
    elapsed = time.perf_counter() - t0

    assert res is False
    assert elapsed < 0.8
    proc = detector._last_ping_proc
    assert proc is not None
    assert proc.returncode in (-9, -signal.SIGKILL)
    with pytest.raises(OSError):
        os.kill(proc.pid, 0)
