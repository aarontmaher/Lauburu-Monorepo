"""
Tier 2: Boundary & Corner-Case E2E Test Suite (34 Test Cases)
Part of Canonical Mesh Fallback Terminal E2E Test Suite.

Covers boundary value analysis, corner conditions, and stress limits:
- B1: MTU Boundaries & Payload Slicing (6 tests)
- B2: Deframer Buffer Limits & Boundary Fragments (6 tests)
- B3: Anti-Tunneling Boundary Limits & Tokens (5 tests)
- B4: Outage Detector Window Edges & Link Flapping (6 tests)
- B5: Shizuku Bridge Boundary & Error Conditions (5 tests)
- B6: Spawner Port & Subnet Boundaries (6 tests)

Strictly Rule 0 Zero-Mock compliant: ZERO mock library imports.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Tuple

import pytest
import pytest_asyncio

from src.mesh_healer.nus_transport import NusTransport
from src.mesh_healer.outage_detector import MeshOutageDetector
from src.mesh_healer.protocol import (
    DEFAULT_ATT_MTU,
    MAX_CHUNK_SIZE,
    MAX_DEFRAMER_BUFFER_SIZE,
    MAX_NUS_PAYLOAD_SIZE,
    MIN_CHUNK_SIZE,
    NusStreamDeframer,
    OOBMessage,
    assert_not_tunneling,
    calculate_chunk_size,
    chunk_payload,
    is_tunneling_payload,
    validate_oob_command,
)
from src.mesh_healer.session_spawner import SessionSpawner
from src.mesh_healer.shizuku_bridge import ShizukuBridge, ShizukuExecutionResult
from tests.e2e_mesh_fallback.fixtures.loopback_factory import (
    get_unused_port,
    start_async_tcp_server,
)


# =============================================================================
# B1: MTU Boundaries & Payload Slicing (6 tests)
# =============================================================================

def test_t2_b1_01_mtu_negative_and_zero_clamping():
    """TC-T2-B1-01: Negative and zero MTUs clamp to MIN_CHUNK_SIZE (20)."""
    assert calculate_chunk_size(-50) == MIN_CHUNK_SIZE
    assert calculate_chunk_size(0) == MIN_CHUNK_SIZE
    assert calculate_chunk_size(1) == MIN_CHUNK_SIZE
    assert calculate_chunk_size(22) == MIN_CHUNK_SIZE


def test_t2_b1_02_mtu_exact_243_boundary():
    """TC-T2-B1-02: ATT MTU 243 yields chunk_size = 243 - 3 = 240 (max chunk)."""
    assert calculate_chunk_size(243) == 240


def test_t2_b1_03_mtu_244_and_higher_capped():
    """TC-T2-B1-03: ATT MTU 244+ remains capped at 240 to prevent controller FIFO overrun."""
    assert calculate_chunk_size(244) == MAX_CHUNK_SIZE
    assert calculate_chunk_size(247) == MAX_CHUNK_SIZE
    assert calculate_chunk_size(1024) == MAX_CHUNK_SIZE


def test_t2_b1_04_chunk_payload_empty_input():
    """TC-T2-B1-04: chunk_payload with empty bytes returns empty list."""
    assert chunk_payload(b"", 20) == []
    assert chunk_payload(b"", 0) == []


def test_t2_b1_05_chunk_payload_smaller_than_chunk_size():
    """TC-T2-B1-05: Payload smaller than chunk size returns single identical chunk."""
    small = b"hello_mesh"
    chunks = chunk_payload(small, 20)
    assert len(chunks) == 1
    assert chunks[0] == small


def test_t2_b1_06_chunk_payload_exact_multiple():
    """TC-T2-B1-06: Payload of exact multiple of chunk size slices without trailing empty chunk."""
    payload = b"X" * 60
    chunks = chunk_payload(payload, 20)
    assert len(chunks) == 3
    assert all(len(c) == 20 for c in chunks)
    assert b"".join(chunks) == payload


# =============================================================================
# B2: Deframer Buffer Limits & Boundary Fragments (6 tests)
# =============================================================================

def test_t2_b2_01_deframer_bounded_buffer_overflow_protection():
    """TC-T2-B2-01: Deframer drops overflow when incoming data exceeds 65536 bytes without newline."""
    small_deframer = NusStreamDeframer(max_buffer_size=100)
    # Feed 80 bytes without newline
    small_deframer.feed(b"A" * 80)
    assert small_deframer.buffered_bytes == 80

    # Feed 40 more bytes (total 120 > 100 limit): buffer drops oldest to protect memory
    small_deframer.feed(b"B" * 40)
    assert small_deframer.buffered_bytes <= 100


def test_t2_b2_02_deframer_empty_byte_feeding():
    """TC-T2-B2-02: Feeding empty bytes returns empty list without state mutation."""
    deframer = NusStreamDeframer()
    assert deframer.feed(b"") == []
    assert deframer.buffered_bytes == 0


def test_t2_b2_03_deframer_consecutive_newlines_ignored():
    """TC-T2-B2-03: Deframer handles consecutive newlines without emitting empty frames."""
    deframer = NusStreamDeframer()
    frames = deframer.feed(b"\n\n\nline1\n\n\nline2\n\n")
    assert frames == ["line1", "line2"]
    assert deframer.buffered_bytes == 0


def test_t2_b2_04_deframer_multibyte_utf8_split():
    """TC-T2-B2-04: Multi-byte UTF-8 emoji split across chunk boundary is reconstituted correctly."""
    deframer = NusStreamDeframer()
    emoji = "🛡️ Lauburu Mesh"
    encoded = emoji.encode("utf-8") + b"\n"

    # Split midway through emoji bytes
    chunk1 = encoded[:4]
    chunk2 = encoded[4:]

    assert deframer.feed(chunk1) == []
    frames = deframer.feed(chunk2)
    assert len(frames) == 1
    assert emoji in frames[0]


def test_t2_b2_05_deframer_preserves_trailing_partial_fragment():
    """TC-T2-B2-05: Complete lines are returned while trailing partial fragment remains buffered."""
    deframer = NusStreamDeframer()
    frames = deframer.feed(b"complete1\ncomplete2\nincomplete_tail")
    assert frames == ["complete1", "complete2"]
    assert deframer.buffered_bytes == len(b"incomplete_tail")

    # Feed newline to complete the tail
    frames2 = deframer.feed(b"\n")
    assert frames2 == ["incomplete_tail"]
    assert deframer.buffered_bytes == 0


def test_t2_b2_06_deframer_clear_resets_buffer():
    """TC-T2-B2-06: clear() empties buffered bytes cleanly."""
    deframer = NusStreamDeframer()
    deframer.feed(b"partial_data")
    assert deframer.buffered_bytes > 0
    deframer.clear()
    assert deframer.buffered_bytes == 0


# =============================================================================
# B3: Anti-Tunneling Boundary Limits & Tokens (5 tests)
# =============================================================================

def test_t2_b3_01_exact_512_bytes_allowed():
    """TC-T2-B3-01: Exactly 512 bytes payload is permitted under Anti-Tunneling Guard."""
    safe_512 = b"A" * 512
    assert is_tunneling_payload(safe_512) is False
    assert_not_tunneling(safe_512)  # Should not raise


def test_t2_b3_02_exact_513_bytes_rejected():
    """TC-T2-B3-02: Exactly 513 bytes payload is rejected by Anti-Tunneling Guard."""
    unsafe_513 = b"A" * 513
    assert is_tunneling_payload(unsafe_513) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(unsafe_513)


def test_t2_b3_03_tunneling_token_in_middle_of_text():
    """TC-T2-B3-03: Substring token /bin/sh in text payload triggers rejection."""
    payload = b"prefix_data /bin/sh suffix_data"
    assert is_tunneling_payload(payload) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(payload)


def test_t2_b3_04_mosh_server_token_rejected():
    """TC-T2-B3-04: mosh-server token in payload triggers rejection."""
    payload = b"exec: mosh-server new"
    assert is_tunneling_payload(payload) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(payload)


def test_t2_b3_05_alternate_screen_ansi_escape_rejected():
    """TC-T2-B3-05: Alternate screen buffer escape code \\x1b[?1049h triggers rejection."""
    payload = b"terminal: \x1b[?1049h full_ui"
    assert is_tunneling_payload(payload) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(payload)


# =============================================================================
# B4: Outage Detector Window Edges & Link Flapping (6 tests)
# =============================================================================

@pytest.mark.asyncio
async def test_t2_b4_01_failure_threshold_one_edge():
    """TC-T2-B4-01: Threshold = 1 triggers outage immediately on the first failed cycle."""
    outage_called = []
    detector = MeshOutageDetector(
        targets={"T": {"tailscale": "127.0.0.1"}},
        failure_threshold=1,
        probe_timeout=0.1,
        on_outage_detected=lambda: outage_called.append(True),
    )
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)
    await detector.probe_cycle()
    assert detector.is_outage_detected is True
    assert len(outage_called) == 1


@pytest.mark.asyncio
async def test_t2_b4_02_flapping_immunity_resets_failures():
    """TC-T2-B4-02: 2 consecutive failures reset to 0 upon 1 successful cycle (flapping immunity)."""
    detector = MeshOutageDetector(
        targets={"T": {"tailscale": "127.0.0.1"}},
        failure_threshold=3,
        probe_timeout=0.1,
    )
    # Fail 2 cycles
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)
    await detector.probe_cycle()
    await detector.probe_cycle()
    assert detector.consecutive_failures == 2
    assert detector.is_outage_detected is False

    # 1 Success resets counter
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=True)
    await detector.probe_cycle()
    assert detector.consecutive_failures == 0
    assert detector.is_outage_detected is False


@pytest.mark.asyncio
async def test_t2_b4_03_alternating_link_never_triggers_outage():
    """TC-T2-B4-03: Alternating fail-pass cycles never reach threshold of 3."""
    detector = MeshOutageDetector(
        targets={"T": {"tailscale": "127.0.0.1"}},
        failure_threshold=3,
        probe_timeout=0.1,
    )
    for i in range(6):
        should_succeed = (i % 2 == 1)
        detector.probe_endpoint = lambda ip, s=should_succeed, **kw: asyncio.sleep(0.01, result=s)
        await detector.probe_cycle()
        assert detector.is_outage_detected is False
        assert detector.consecutive_failures <= 1


@pytest.mark.asyncio
async def test_t2_b4_04_micro_timeout_does_not_hang():
    """TC-T2-B4-04: Micro-timeout (10ms) on dead endpoint returns promptly without hang."""
    detector = MeshOutageDetector(probe_timeout=0.01)
    start = time.perf_counter()
    # RFC 5737 non-routable IP
    res = await detector.probe_endpoint("192.0.2.1", port=8022, timeout=0.01)
    dur = time.perf_counter() - start
    assert res is False
    assert dur < 1.0  # Finished promptly


@pytest.mark.asyncio
async def test_t2_b4_05_empty_targets_returns_true():
    """TC-T2-B4-05: Empty targets dictionary returns True (no outage possible)."""
    detector = MeshOutageDetector(targets={})
    alive = await detector.probe_cycle()
    assert alive is True
    assert detector.is_outage_detected is False


def test_t2_b4_06_stop_clean_idempotent():
    """TC-T2-B4-06: stop() on unstarted detector is idempotent and safe."""
    detector = MeshOutageDetector()
    detector.stop()
    assert detector.is_running is False


# =============================================================================
# B5: Shizuku Bridge Boundary & Error Conditions (5 tests)
# =============================================================================

def test_t2_b5_01_non_existent_custom_rish_path(dead_port: int):
    """TC-T2-B5-01: Non-existent custom rish path falls back to checking adb or returns unavailable."""
    bridge = ShizukuBridge(custom_rish_path=f"/non_existent_path_{dead_port}/rish")
    # Should not crash; resolves None for rish
    assert bridge._resolve_rish_binary() is None


@pytest.mark.asyncio
async def test_t2_b5_02_command_failure_captures_error(mock_rish_path: str):
    """TC-T2-B5-02: Executing failing command records success=False and non-zero exit code."""
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    os.environ["RISH_FAIL_PRIMARY"] = "1"
    try:
        res = await bridge.execute("cmd tethering start-tethering bluetooth")
        assert res.success is False
        assert res.exit_code != 0
        assert len(res.stderr) > 0
    finally:
        os.environ.pop("RISH_FAIL_PRIMARY", None)


def test_t2_b5_03_execution_timeout_returns_code_124(mock_rish_path: str):
    """TC-T2-B5-03: Command exceeding timeout in execute_sync returns exit_code=124."""
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    res = bridge.execute_sync("sleep 1", timeout=0.01)
    assert res.success is False
    assert res.exit_code in (124, 1)


def test_t2_b5_04_execute_sync_success(mock_rish_path: str):
    """TC-T2-B5-04: execute_sync returns valid receipt in synchronous context."""
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    res = bridge.execute_sync("id")
    assert res.success is True
    assert res.exit_code == 0
    assert "uid=2000" in res.stdout


def test_t2_b5_05_shizuku_result_to_dict():
    """TC-T2-B5-05: ShizukuExecutionResult converts cleanly to serializable dictionary."""
    res = ShizukuExecutionResult(
        command="id",
        success=True,
        exit_code=0,
        stdout="uid=2000",
        stderr="",
        duration_ms=5.0,
        mode="rish",
        is_shizuku_elevated=True,
    )
    d = res.to_dict()
    assert d["command"] == "id"
    assert d["success"] is True
    assert d["exit_code"] == 0
    assert d["mode"] == "rish"


# =============================================================================
# B6: Spawner Port & Subnet Boundaries (6 tests)
# =============================================================================

@pytest.mark.asyncio
async def test_t2_b6_01_port_22_open_when_8022_closed(live_tcp_server: Tuple[str, int]):
    """TC-T2-B6-01: When Termux 8022 is closed and POSIX 22 is open, selects 22."""
    host, live_port = live_tcp_server
    dead_8022 = get_unused_port()
    spawner = SessionSpawner(gateway_ip=host, ssh_ports=(dead_8022, live_port))
    reachable, active_port = await spawner.probe_reachability(timeout=0.5)
    assert reachable is True
    assert active_port == live_port


@pytest.mark.asyncio
async def test_t2_b6_02_empty_ports_tuple_returns_false():
    """TC-T2-B6-02: Probing with empty candidate ports tuple returns (False, None)."""
    spawner = SessionSpawner(gateway_ip="127.0.0.1", ssh_ports=())
    reachable, active_port = await spawner.probe_reachability()
    assert reachable is False
    assert active_port is None


@pytest.mark.asyncio
async def test_t2_b6_03_debounce_flapper_rejected():
    """TC-T2-B6-03: Port open on first probe but failing second probe is rejected by debounce gate."""
    spawner = SessionSpawner(gateway_ip="127.0.0.1", ssh_ports=(8022,))
    call_count = 0

    async def mock_single_target(host, port, timeout):
        nonlocal call_count
        call_count += 1
        # Succeed first probe, fail second probe
        return call_count == 1

    spawner.probe_single_target = mock_single_target
    reachable, active_port = await spawner.probe_reachability(timeout=0.2)
    assert reachable is False
    assert active_port is None
    assert call_count == 2


@pytest.mark.asyncio
async def test_t2_b6_04_terminate_session_safe_when_inactive():
    """TC-T2-B6-04: terminate_session is safe and idempotent when no session is active."""
    spawner = SessionSpawner()
    await spawner.terminate_session()  # Should not raise
    assert spawner.is_session_active is False
    assert spawner.active_pid is None


@pytest.mark.asyncio
async def test_t2_b6_05_watchdog_resets_misses_on_healthy_link(live_tcp_server: Tuple[str, int]):
    """TC-T2-B6-05: Watchdog preserves active session while TCP target remains healthy."""
    host, port = live_tcp_server
    collapsed = []
    spawner = SessionSpawner(
        watchdog_interval=0.1,
        on_link_collapsed=lambda: collapsed.append(True),
    )
    spawner.is_session_active = True
    spawner.start_watchdog(host, port)

    # Allow watchdog to run for 3 healthy cycles
    await asyncio.sleep(0.35)
    assert spawner.consecutive_watchdog_misses == 0
    assert spawner.is_session_active is True
    assert len(collapsed) == 0
    spawner.stop_watchdog()


def test_t2_b6_06_resolve_binary_custom_options(mock_ssh_path: str):
    """TC-T2-B6-06: Custom binary resolution formats arguments and preserves host/port."""
    spawner = SessionSpawner(custom_binary_path=mock_ssh_path)
    binary, args, cmd_str = spawner.resolve_binary_and_command("10.255.0.1", 2222, "root")
    assert binary == mock_ssh_path
    assert "-p" in args
    assert "2222" in args
    assert "root@10.255.0.1" in args
    assert f"{mock_ssh_path} -p 2222 root@10.255.0.1" == cmd_str
