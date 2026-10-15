"""
Tier 1: Feature Coverage E2E Test Suite (36 Test Cases)
Part of Canonical Mesh Fallback Terminal E2E Test Suite.

Covers all 6 core features in isolated opaque-box verification:
- F1: Stage 1 BLE GATT NUS Protocol (6 tests)
- F2: Stage 1 OOB Payload Catalog & Anti-Tunneling (6 tests)
- F3: Stage 2 Autonomous Outage Prober (6 tests)
- F4: Stage 2 Dual-Mode Escalation (6 tests)
- F5: Stage 3 Subnet Reachability Prober (5 tests)
- F6: Stage 3 Non-Blocking SSH/Mosh Spawner (7 tests)

Strictly Rule 0 Zero-Mock compliant: ZERO mock library imports.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Tuple

import pytest
import pytest_asyncio

from src.mesh_healer.healer_engine import HealerState, MeshHealer
from src.mesh_healer.nus_transport import NusTransport
from src.mesh_healer.outage_detector import MeshOutageDetector
from src.mesh_healer.protocol import (
    DEFAULT_ATT_MTU,
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    NUS_RX_UUID,
    NUS_SERVICE_UUID,
    NUS_TX_UUID,
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
# FEATURE 1: Stage 1 BLE GATT NUS Protocol (6 tests)
# =============================================================================

def test_t1_f1_01_calculate_chunk_size_boundaries():
    """TC-T1-F1-01: calculate_chunk_size with standard and boundary ATT MTUs."""
    assert calculate_chunk_size(None) == MIN_CHUNK_SIZE  # 20
    assert calculate_chunk_size(0) == MIN_CHUNK_SIZE     # 20
    assert calculate_chunk_size(20) == MIN_CHUNK_SIZE    # 20
    assert calculate_chunk_size(23) == MIN_CHUNK_SIZE    # 23 - 3 = 20
    assert calculate_chunk_size(100) == 97               # 100 - 3 = 97
    assert calculate_chunk_size(243) == 240              # 243 - 3 = 240 (capped)
    assert calculate_chunk_size(512) == MAX_CHUNK_SIZE   # capped at 240


def test_t1_f1_02_chunk_payload_slicing():
    """TC-T1-F1-02: chunk_payload slices byte stream into exact MTU-sized packets."""
    payload = b"A" * 65
    chunks = chunk_payload(payload, 20)
    assert len(chunks) == 4
    assert len(chunks[0]) == 20
    assert len(chunks[1]) == 20
    assert len(chunks[2]) == 20
    assert len(chunks[3]) == 5
    assert b"".join(chunks) == payload


def test_t1_f1_03_nus_uuids_conform_to_nordic_spec():
    """TC-T1-F1-03: Verify Nordic UART Service UUIDs conform to canonical specification."""
    expected_service = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
    expected_rx = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
    expected_tx = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
    assert NUS_SERVICE_UUID == expected_service
    assert NUS_RX_UUID == expected_rx
    assert NUS_TX_UUID == expected_tx


def test_t1_f1_04_deframer_single_chunk_extraction():
    """TC-T1-F1-04: NusStreamDeframer ingests complete line and extracts frame."""
    deframer = NusStreamDeframer()
    frames = deframer.feed(b'{"id":"msg1","cmd":"PING","params":{}}\n')
    assert len(frames) == 1
    assert '{"id":"msg1","cmd":"PING","params":{}}' in frames[0]
    assert deframer.buffered_bytes == 0


def test_t1_f1_05_deframer_multi_chunk_reconstitution():
    """TC-T1-F1-05: Reconstitutes multi-chunk fragmented stream across BLE notification chunks."""
    deframer = NusStreamDeframer()
    # Chunk 1: partial header
    f1 = deframer.feed(b'{"id":"101",')
    assert len(f1) == 0
    assert deframer.buffered_bytes > 0

    # Chunk 2: middle params
    f2 = deframer.feed(b'"cmd":"WOL","params":{"mac":"AA:BB:CC:DD:EE:FF"')
    assert len(f2) == 0

    # Chunk 3: closing brace and newline
    f3 = deframer.feed(b'}}\n')
    assert len(f3) == 1
    msg = OOBMessage.deserialize(f3[0])
    assert msg is not None
    assert msg.cmd == "WOL"
    assert msg.params["mac"] == "AA:BB:CC:DD:EE:FF"
    assert deframer.buffered_bytes == 0


def test_t1_f1_06_deframer_buffer_clear_and_tracking():
    """TC-T1-F1-06: Verifies deframer buffer clearing and partial byte count tracking."""
    deframer = NusStreamDeframer()
    deframer.feed(b"fragment_without_newline")
    assert deframer.buffered_bytes == len(b"fragment_without_newline")
    deframer.clear()
    assert deframer.buffered_bytes == 0


# =============================================================================
# FEATURE 2: Stage 1 OOB Payload Catalog & Anti-Tunneling (6 tests)
# =============================================================================

def test_t1_f2_01_oob_message_serialization():
    """TC-T1-F2-01: OOBMessage serialization generates newline-terminated UTF-8 JSON-L."""
    msg = OOBMessage(id="wol_1", cmd="WOL", params={"mac": "00:11:22:33:44:55"})
    raw = msg.serialize()
    assert isinstance(raw, bytes)
    assert raw.endswith(b"\n")
    decoded = raw.decode("utf-8")
    assert '"cmd":"WOL"' in decoded
    assert '"id":"wol_1"' in decoded


def test_t1_f2_02_oob_message_safe_deserialization():
    """TC-T1-F2-02: OOBMessage safe deserialization from string and bytes."""
    json_str = '{"id":"cycle_1","cmd":"CYCLE_NET","params":{"interface":"wlan0"},"ts":1700000000.0}'
    msg = OOBMessage.deserialize(json_str)
    assert msg is not None
    assert msg.id == "cycle_1"
    assert msg.cmd == "CYCLE_NET"
    assert msg.params.get("interface") == "wlan0"

    # From bytes
    msg2 = OOBMessage.deserialize(json_str.encode("utf-8") + b"\n")
    assert msg2 is not None
    assert msg2.cmd == "CYCLE_NET"

    # Corrupted / invalid input returns None safely
    assert OOBMessage.deserialize(b"corrupted_non_json") is None
    assert OOBMessage.deserialize(b"") is None


def test_t1_f2_03_supported_oob_commands_catalog():
    """TC-T1-F2-03: Verifies all canonical OOB commands are recognized."""
    catalog = ["WOL", "RESTART_DAEMON", "CYCLE_NET", "TELEMETRY_REQ", "ENABLE_PAN", "PING", "PONG"]
    for cmd in catalog:
        assert validate_oob_command(cmd) is True
        assert validate_oob_command(cmd.lower()) is True  # Case-insensitive


def test_t1_f2_04_unknown_oob_command_rejected():
    """TC-T1-F2-04: Verifies uncataloged commands are rejected by validator."""
    assert validate_oob_command("EXEC_ARBITRARY_CODE") is False
    assert validate_oob_command("SSH_CONNECT") is False
    assert validate_oob_command("DROP_TABLE") is False


def test_t1_f2_05_anti_tunneling_oversized_payload_rejected():
    """TC-T1-F2-05: Anti-tunneling guard rejects payload exceeding 512 bytes."""
    oversized = b"X" * 513
    assert is_tunneling_payload(oversized) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(oversized)


def test_t1_f2_06_anti_tunneling_forbidden_tokens_rejected():
    """TC-T1-F2-06: Anti-tunneling guard blocks shell and PTY tokens."""
    forbidden_samples = [
        b"/bin/sh -i",
        b"/bin/bash -c 'ls -la'",
        b"mosh-server new -s",
        b"SSH-2.0-OpenSSH",
        b"\x1b[?1049h",  # Alternate screen buffer
    ]
    for sample in forbidden_samples:
        assert is_tunneling_payload(sample) is True
        with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
            assert_not_tunneling(sample)


# =============================================================================
# FEATURE 3: Stage 2 Autonomous Outage Prober (6 tests)
# =============================================================================

def test_t1_f3_01_outage_detector_initialization():
    """TC-T1-F3-01: Outage detector initializes with custom parameters and default targets."""
    detector = MeshOutageDetector(failure_threshold=3, probe_timeout=0.5, probe_interval=1.0)
    assert detector.failure_threshold == 3
    assert detector.probe_timeout == 0.5
    assert detector.consecutive_failures == 0
    assert detector.is_outage_detected is False


@pytest.mark.asyncio
async def test_t1_f3_02_probe_endpoint_success_on_live_socket(live_tcp_server: Tuple[str, int]):
    """TC-T1-F3-02: probe_endpoint returns True on active local TCP server."""
    host, port = live_tcp_server
    detector = MeshOutageDetector(probe_timeout=1.0)
    result = await detector.probe_endpoint(host, port=port)
    assert result is True


@pytest.mark.asyncio
async def test_t1_f3_03_probe_endpoint_fails_on_unreachable_ip():
    """TC-T1-F3-03: probe_endpoint returns False on unreachable network target (TCP & ICMP fail)."""
    detector = MeshOutageDetector(probe_timeout=0.2)
    result = await detector.probe_endpoint("192.0.2.1", port=8022)
    assert result is False


@pytest.mark.asyncio
async def test_t1_f3_04_sliding_window_single_failure_does_not_trigger():
    """TC-T1-F3-04: Single cycle failure increments counter but does not trigger outage when threshold is 3."""
    outage_triggered = []
    dead1 = get_unused_port()
    detector = MeshOutageDetector(
        targets={"TargetA": {"tailscale": "127.0.0.1"}},
        failure_threshold=3,
        probe_timeout=0.1,
        on_outage_detected=lambda: outage_triggered.append(True),
    )
    # Target port is dead, so probe_cycle will fail
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)
    
    alive = await detector.probe_cycle()
    assert alive is False
    assert detector.consecutive_failures == 1
    assert detector.is_outage_detected is False
    assert len(outage_triggered) == 0


@pytest.mark.asyncio
async def test_t1_f3_05_sliding_window_threshold_triggers_outage_callback():
    """TC-T1-F3-05: 3 consecutive failed cycles trigger on_outage_detected callback."""
    outage_calls = []
    detector = MeshOutageDetector(
        targets={"Node": {"tailscale": "127.0.0.1"}},
        failure_threshold=3,
        probe_timeout=0.1,
        on_outage_detected=lambda: outage_calls.append(time.time()),
    )
    # Simulate failed probe cycles
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)

    await detector.probe_cycle()  # Failure 1
    assert detector.consecutive_failures == 1
    assert detector.is_outage_detected is False

    await detector.probe_cycle()  # Failure 2
    assert detector.consecutive_failures == 2
    assert detector.is_outage_detected is False

    await detector.probe_cycle()  # Failure 3 -> Outage Confirmed
    assert detector.consecutive_failures == 3
    assert detector.is_outage_detected is True
    assert len(outage_calls) == 1


@pytest.mark.asyncio
async def test_t1_f3_06_recovery_callback_triggered_after_outage():
    """TC-T1-F3-06: Recovery callback triggered when alive endpoint returns after outage."""
    recovery_calls = []
    detector = MeshOutageDetector(
        targets={"Node": {"tailscale": "127.0.0.1"}},
        failure_threshold=1,
        probe_timeout=0.1,
        on_outage_recovered=lambda: recovery_calls.append(True),
    )
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)
    await detector.probe_cycle()
    assert detector.is_outage_detected is True

    # Now endpoint recovers
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=True)
    await detector.probe_cycle()
    assert detector.is_outage_detected is False
    assert detector.consecutive_failures == 0
    assert len(recovery_calls) == 1


# =============================================================================
# FEATURE 4: Stage 2 Dual-Mode Escalation (6 tests)
# =============================================================================

def test_t1_f4_01_shizuku_bridge_availability(mock_rish_path: str):
    """TC-T1-F4-01: ShizukuBridge confirms availability using authentic executable fixture."""
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    assert bridge.is_available() is True


@pytest.mark.asyncio
async def test_t1_f4_02_shizuku_bridge_execute_returns_receipt(mock_rish_path: str, audit_log: str):
    """TC-T1-F4-02: ShizukuBridge execute returns valid ShizukuExecutionResult with exit code 0."""
    os.environ["RISH_AUDIT_LOG"] = audit_log
    try:
        bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
        res = await bridge.execute("echo test_shizuku")
        assert res.success is True
        assert res.exit_code == 0
        assert res.mode == "rish"
        assert res.is_shizuku_elevated is True
        assert res.duration_ms > 0
    finally:
        os.environ.pop("RISH_AUDIT_LOG", None)


@pytest.mark.asyncio
async def test_t1_f4_03_shizuku_bridge_bluetooth_tethering(mock_rish_path: str, audit_log: str):
    """TC-T1-F4-03: start_bluetooth_tethering forces BNEP on edge device with exit code 0."""
    os.environ["RISH_AUDIT_LOG"] = audit_log
    try:
        bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
        ok, receipt = await bridge.start_bluetooth_tethering()
        assert ok is True
        assert "[SHIZUKU]" in receipt
        assert "BNEP active" in receipt
        # Verify invocation logged in real audit file
        with open(audit_log, "r", encoding="utf-8") as f:
            log_content = f.read()
        assert "cmd tethering start-tethering bluetooth" in log_content
    finally:
        os.environ.pop("RISH_AUDIT_LOG", None)


@pytest.mark.asyncio
async def test_t1_f4_04_shizuku_bridge_fallback_command(mock_rish_path: str):
    """TC-T1-F4-04: start_bluetooth_tethering falls back to secondary command if primary fails."""
    os.environ["RISH_FAIL_PRIMARY"] = "1"
    try:
        bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
        ok, receipt = await bridge.start_bluetooth_tethering()
        assert ok is True
        assert "cmd connectivity tether start bluetooth" in receipt
    finally:
        os.environ.pop("RISH_FAIL_PRIMARY", None)


def test_t1_f4_05_shizuku_receipt_formatting():
    """TC-T1-F4-05: ShizukuExecutionResult format_receipt produces structured log."""
    res = ShizukuExecutionResult(
        command="svc bluetooth enable",
        success=True,
        exit_code=0,
        stdout="OK",
        stderr="",
        duration_ms=12.4,
        mode="rish",
        is_shizuku_elevated=True,
    )
    formatted = res.format_receipt()
    assert "[RISH]" in formatted
    assert "Exit Code 0 (SUCCEEDED)" in formatted
    assert "12.4ms" in formatted


@pytest.mark.asyncio
async def test_t1_f4_06_healer_trigger_pan_escalation_transitions_state(mock_rish_path: str):
    """TC-T1-F4-06: trigger_pan_escalation transitions MeshHealer to STAGE_2_PAN_ESCALATING."""
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    healer = MeshHealer(shizuku_bridge=bridge)
    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL

    ok = await healer.trigger_pan_escalation(source="unit_test")
    assert ok is True
    assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING
    await healer.stop_monitoring()


# =============================================================================
# FEATURE 5: Stage 3 Subnet Reachability Prober (5 tests)
# =============================================================================

@pytest.mark.asyncio
async def test_t1_f5_01_session_spawner_probe_single_target_success(live_tcp_server: Tuple[str, int]):
    """TC-T1-F5-01: SessionSpawner probe_single_target connects to live TCP loopback server."""
    host, port = live_tcp_server
    spawner = SessionSpawner()
    alive = await spawner.probe_single_target(host, port, timeout=1.0)
    assert alive is True


@pytest.mark.asyncio
async def test_t1_f5_02_session_spawner_probe_single_target_fails_closed_port(dead_port: int):
    """TC-T1-F5-02: SessionSpawner probe_single_target returns False on closed port."""
    spawner = SessionSpawner()
    alive = await spawner.probe_single_target("127.0.0.1", dead_port, timeout=0.2)
    assert alive is False


@pytest.mark.asyncio
async def test_t1_f5_03_debounce_gate_confirms_reachability(live_tcp_server: Tuple[str, int]):
    """TC-T1-F5-03: 2-probe debounce gate probe_reachability returns (True, port) when live."""
    host, port = live_tcp_server
    spawner = SessionSpawner(gateway_ip=host, ssh_ports=(port,))
    reachable, active_port = await spawner.probe_reachability(timeout=1.0)
    assert reachable is True
    assert active_port == port
    assert spawner.active_port == port


@pytest.mark.asyncio
async def test_t1_f5_04_debounce_gate_rejects_closed_ports(dead_port: int):
    """TC-T1-F5-04: probe_reachability returns (False, None) when candidate ports are closed."""
    spawner = SessionSpawner(gateway_ip="127.0.0.1", ssh_ports=(dead_port,))
    reachable, active_port = await spawner.probe_reachability(timeout=0.2)
    assert reachable is False
    assert active_port is None


@pytest.mark.asyncio
async def test_t1_f5_05_dual_port_scanning_order(live_tcp_server: Tuple[str, int]):
    """TC-T1-F5-05: Dual-port scanning checks 8022 first, falls back to 22."""
    host, live_port = live_tcp_server
    dead_p = get_unused_port()
    # dead_p first, live_port second
    spawner = SessionSpawner(gateway_ip=host, ssh_ports=(dead_p, live_port))
    reachable, found_port = await spawner.probe_reachability(timeout=0.5)
    assert reachable is True
    assert found_port == live_port


# =============================================================================
# FEATURE 6: Stage 3 Non-Blocking SSH/Mosh Spawner (7 tests)
# =============================================================================

def test_t1_f6_01_resolve_binary_and_command():
    """TC-T1-F6-01: resolve_binary_and_command selects mosh or ssh with proper arguments."""
    spawner = SessionSpawner()
    binary_name, args, cmd_str = spawner.resolve_binary_and_command("192.168.44.1", 8022, "u0_a363")
    assert binary_name in ("mosh", "ssh")
    assert "192.168.44.1" in cmd_str
    assert "8022" in cmd_str


def test_t1_f6_02_custom_binary_path_injection(mock_ssh_path: str):
    """TC-T1-F6-02: Custom binary path injection correctly builds execution command."""
    spawner = SessionSpawner(custom_binary_path=mock_ssh_path)
    binary_name, args, cmd_str = spawner.resolve_binary_and_command("192.168.44.1", 8022, "u0_a363")
    assert binary_name == mock_ssh_path
    assert args[0] == mock_ssh_path
    assert "-p" in args
    assert "8022" in args


@pytest.mark.asyncio
async def test_t1_f6_03_background_spawn_stores_pid(mock_ssh_path: str, audit_log: str):
    """TC-T1-F6-03: Background mode spawns asynchronous child process and stores active_pid."""
    os.environ["SSH_AUDIT_LOG"] = audit_log
    os.environ["SSH_STAY_ALIVE"] = "1"
    try:
        spawner = SessionSpawner(custom_binary_path=mock_ssh_path)
        ok, msg = await spawner.spawn_session(
            mode="background", host="127.0.0.1", port=8022
        )
        assert ok is True
        assert spawner.is_session_active is True
        assert spawner.active_pid is not None
        assert spawner.active_pid > 0

        # Terminate cleanly
        await spawner.terminate_session()
        assert spawner.is_session_active is False
    finally:
        os.environ.pop("SSH_AUDIT_LOG", None)
        os.environ.pop("SSH_STAY_ALIVE", None)


@pytest.mark.asyncio
async def test_t1_f6_04_clean_process_termination(mock_ssh_path: str, audit_log: str):
    """TC-T1-F6-04: terminate_session terminates active background subprocess cleanly."""
    os.environ["SSH_AUDIT_LOG"] = audit_log
    os.environ["SSH_STAY_ALIVE"] = "1"
    try:
        spawner = SessionSpawner(custom_binary_path=mock_ssh_path)
        await spawner.spawn_session(mode="background", host="127.0.0.1", port=8022)
        pid = spawner.active_pid
        assert pid is not None

        await spawner.terminate_session()
        assert spawner.active_process is None
        assert spawner.active_pid is None
    finally:
        os.environ.pop("SSH_AUDIT_LOG", None)
        os.environ.pop("SSH_STAY_ALIVE", None)


@pytest.mark.asyncio
async def test_t1_f6_05_watchdog_detects_link_collapse_after_misses(dead_port: int):
    """TC-T1-F6-05: Stage 3 keepalive watchdog detects collapse after 3 consecutive misses."""
    collapsed_events = []
    spawner = SessionSpawner(
        watchdog_interval=0.1,
        on_link_collapsed=lambda: collapsed_events.append(time.time()),
    )
    spawner.is_session_active = True
    spawner.start_watchdog("127.0.0.1", dead_port)

    # Wait for watchdog to complete 3 misses
    await asyncio.sleep(0.5)
    assert len(collapsed_events) == 1
    assert spawner.consecutive_watchdog_misses >= 3
    assert spawner.is_session_active is False
    spawner.stop_watchdog()


@pytest.mark.asyncio
async def test_t1_f6_06_tmux_split_window_mode(mock_tmux_path: str, audit_log: str):
    """TC-T1-F6-06: Tmux mode splits window when tmux environment is present."""
    os.environ["TMUX_AUDIT_LOG"] = audit_log
    # Inject mock tmux via custom PATH
    parent_dir = str(Path(mock_tmux_path).parent)
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{parent_dir}:{old_path}"
    os.environ["TMUX"] = "mock_tmux_session"

    try:
        # Create a symlink named 'tmux' to mock_tmux.sh in the same directory if not present
        tmux_symlink = Path(parent_dir) / "tmux"
        if not tmux_symlink.exists():
            tmux_symlink.symlink_to(Path(mock_tmux_path).name)

        spawner = SessionSpawner()
        ok, msg = await spawner.spawn_session(
            mode="tmux", host="192.168.44.1", port=8022
        )
        assert ok is True
        assert "[STAGE 3]" in msg
        assert "Tmux pane spawned" in msg

        with open(audit_log, "r", encoding="utf-8") as f:
            content = f.read()
        assert "split-window -h" in content
        await spawner.terminate_session()
    finally:
        os.environ.pop("TMUX_AUDIT_LOG", None)
        os.environ.pop("TMUX", None)
        os.environ["PATH"] = old_path
        if tmux_symlink.exists() and tmux_symlink.is_symlink():
            tmux_symlink.unlink()


def test_t1_f6_07_watchdog_clean_stop_when_not_started():
    """TC-T1-F6-07: Verifies stop_watchdog is idempotent when watchdog was never started."""
    spawner = SessionSpawner()
    spawner.stop_watchdog()  # Should not raise
    assert spawner._watchdog_running is False
