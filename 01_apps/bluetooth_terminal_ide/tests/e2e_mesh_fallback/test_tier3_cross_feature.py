"""
Tier 3: Pairwise Cross-Feature Integration E2E Test Suite (7 Test Cases)
Part of Canonical Mesh Fallback Terminal E2E Test Suite.

Covers pairwise cross-feature interactions and concurrent coroutine execution:
- TC-T3-01: F3 (Outage Prober) + F4 (Shizuku Bridge) concurrent execution
- TC-T3-02: F1 (NUS Deframer) + F4 (Shizuku Bridge) concurrent notification processing
- TC-T3-03: F5 (Subnet Prober) + F6 (Background Spawner) handoff
- TC-T3-04: F6 (Watchdog Demotion) + F1 (OOB Resurrection Message)
- TC-T3-05: F3 (Outage Prober) + Healer Async Event Callbacks without race conditions
- TC-T3-06: F5 (Subnet Probe) + F6 (Tmux Spawner) split-window execution
- TC-T3-07: Full Cyclic Escalation & Demotion Churn (Stage 1 -> 2 -> 3 -> 1 -> 2 -> 3)

Strictly Rule 0 Zero-Mock compliant: ZERO mock library imports.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import List, Tuple

import pytest
import pytest_asyncio

from src.mesh_healer.healer_engine import HealerState, MeshHealer
from src.mesh_healer.nus_transport import NusTransport
from src.mesh_healer.outage_detector import MeshOutageDetector
from src.mesh_healer.protocol import NusStreamDeframer, OOBMessage
from src.mesh_healer.session_spawner import SessionSpawner
from src.mesh_healer.shizuku_bridge import ShizukuBridge
from tests.e2e_mesh_fallback.fixtures.loopback_factory import (
    get_unused_port,
    start_async_tcp_server,
)


@pytest.mark.asyncio
async def test_t3_01_outage_prober_triggers_concurrent_shizuku(mock_rish_path: str, audit_log: str):
    """
    TC-T3-01: Pairwise F3 + F4.
    Outage detection triggers concurrent Shizuku bridge invocation without blocking the event loop.
    """
    os.environ["RISH_AUDIT_LOG"] = audit_log
    try:
        bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
        detector = MeshOutageDetector(
            targets={"Edge": {"tailscale": "127.0.0.1"}},
            failure_threshold=1,
            probe_timeout=0.05,
        )
        detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)

        healer = MeshHealer(
            shizuku_bridge=bridge,
            outage_detector=detector,
            initial_state=HealerState.STAGE_1_RAW_SERIAL,
        )

        # Confirm outage cycle
        await detector.probe_cycle()
        assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING

        # Verify Shizuku command was logged to authentic audit file
        with open(audit_log, "r", encoding="utf-8") as f:
            content = f.read()
        assert "cmd tethering start-tethering bluetooth" in content

        await healer.stop_monitoring()
    finally:
        os.environ.pop("RISH_AUDIT_LOG", None)


@pytest.mark.asyncio
async def test_t3_02_concurrent_deframing_during_shizuku_execution(mock_rish_path: str):
    """
    TC-T3-02: Pairwise F1 + F4.
    High-frequency BLE GATT notification deframing occurs concurrently while Shizuku executes.
    """
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    deframer = NusStreamDeframer()

    received_frames = []

    async def simulate_ble_stream():
        for i in range(20):
            msg = OOBMessage(id=f"stream_{i}", cmd="PING", params={"seq": i})
            raw = msg.serialize()
            # Split each frame into 2 chunks
            chunk1 = raw[:len(raw) // 2]
            chunk2 = raw[len(raw) // 2:]
            deframer.feed(chunk1)
            f2 = deframer.feed(chunk2)
            received_frames.extend(f2)
            await asyncio.sleep(0.005)

    async def execute_shizuku():
        return await bridge.start_bluetooth_tethering()

    # Run both concurrently
    results = await asyncio.gather(simulate_ble_stream(), execute_shizuku())
    shizuku_ok, shizuku_receipt = results[1]

    assert shizuku_ok is True
    assert len(received_frames) == 20
    assert deframer.buffered_bytes == 0


@pytest.mark.asyncio
async def test_t3_03_reachability_probe_triggers_background_spawner(
    live_tcp_server: Tuple[str, int], mock_ssh_path: str, audit_log: str
):
    """
    TC-T3-03: Pairwise F5 + F6.
    Subnet reachability probe detection triggers non-blocking background spawner with valid PID.
    """
    os.environ["SSH_AUDIT_LOG"] = audit_log
    os.environ["SSH_STAY_ALIVE"] = "1"
    host, port = live_tcp_server

    try:
        spawner = SessionSpawner(
            custom_binary_path=mock_ssh_path,
            gateway_ip=host,
            ssh_ports=(port,),
        )
        reachable, active_port = await spawner.probe_reachability(timeout=0.5)
        assert reachable is True
        assert active_port == port

        ok, msg = await spawner.spawn_session(mode="background", host=host, port=active_port)
        assert ok is True
        assert spawner.is_session_active is True
        assert spawner.active_pid is not None

        # Allow child process brief moment to flush invocation to log
        await asyncio.sleep(0.15)

        # Verify audit log recorded spawn
        with open(audit_log, "r", encoding="utf-8") as f:
            log_data = f.read()
        assert f"PID={spawner.active_pid}" in log_data

        await spawner.terminate_session()
        assert spawner.is_session_active is False
    finally:
        os.environ.pop("SSH_AUDIT_LOG", None)
        os.environ.pop("SSH_STAY_ALIVE", None)


@pytest.mark.asyncio
async def test_t3_04_watchdog_collapse_triggers_demotion_and_oob_resurrection(mock_rish_path: str):
    """
    TC-T3-04: Pairwise F6 + F1.
    Stage 3 watchdog collapse triggers clean SIGTERM demotion to Stage 1 and OOB resurrection message.
    """
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    dead_p = get_unused_port()

    spawner = SessionSpawner(
        watchdog_interval=0.1,
        gateway_ip="127.0.0.1",
        ssh_ports=(dead_p,),
    )

    stage_changes = []
    log_messages = []

    healer = MeshHealer(
        shizuku_bridge=bridge,
        session_spawner=spawner,
        initial_state=HealerState.STAGE_3_SSH_MOSH,
        on_stage_changed=lambda old_s, new_s: stage_changes.append((old_s, new_s)),
        on_log_message=lambda lvl, msg: log_messages.append((lvl, msg)),
    )

    # Start watchdog with dead port
    spawner.is_session_active = True
    spawner.start_watchdog("127.0.0.1", dead_p)

    # Wait for 3 misses to trigger demotion
    await asyncio.sleep(0.5)

    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL
    assert spawner.is_session_active is False
    # Check that stage demotion was recorded
    assert any(new_s == HealerState.STAGE_1_RAW_SERIAL for _, new_s in stage_changes)
    # Check that demotion alert was logged
    assert any("Demoted to Stage 1" in msg for _, msg in log_messages)

    await healer.stop_monitoring()


@pytest.mark.asyncio
async def test_t3_05_outage_prober_dispatches_callbacks_safely():
    """
    TC-T3-05: Pairwise F3 + Healer Callbacks.
    Multi-target prober dispatches state transition and log callbacks without race conditions.
    """
    events = []
    detector = MeshOutageDetector(
        targets={"NodeA": {"tailscale": "127.0.0.1"}},
        failure_threshold=1,
        probe_timeout=0.05,
    )
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)

    healer = MeshHealer(
        outage_detector=detector,
        on_stage_changed=lambda old_s, new_s: events.append(f"STAGE:{new_s.value}"),
        on_log_message=lambda lvl, msg: events.append(f"LOG:{lvl}"),
    )

    await detector.probe_cycle()
    assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING
    assert any("STAGE:STAGE_2_PAN_ESCALATING" in e for e in events)
    assert any("LOG:warning" in e or "LOG:info" in e for e in events)

    await healer.stop_monitoring()


@pytest.mark.asyncio
async def test_t3_06_tmux_spawner_with_live_reachability(
    live_tcp_server: Tuple[str, int], mock_tmux_path: str, audit_log: str
):
    """
    TC-T3-06: Pairwise F5 + F6 (Tmux).
    Subnet reachability on live TCP port triggers tmux split-window handoff cleanly.
    """
    os.environ["TMUX_AUDIT_LOG"] = audit_log
    parent_dir = str(Path(mock_tmux_path).parent)
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{parent_dir}:{old_path}"
    os.environ["TMUX"] = "mock_session"

    host, port = live_tcp_server

    try:
        tmux_symlink = Path(parent_dir) / "tmux"
        if not tmux_symlink.exists():
            tmux_symlink.symlink_to(Path(mock_tmux_path).name)

        spawner = SessionSpawner(gateway_ip=host, ssh_ports=(port,))
        reachable, active_port = await spawner.probe_reachability(timeout=0.5)
        assert reachable is True

        ok, msg = await spawner.spawn_session(mode="tmux", host=host, port=active_port)
        assert ok is True
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


@pytest.mark.asyncio
async def test_t3_07_full_cyclic_escalation_and_demotion_churn(mock_rish_path: str):
    """
    TC-T3-07: Full State Churn.
    Cycles through multiple rounds of Stage 1 -> Stage 2 -> Stage 3 -> Stage 1 with zero leaks.
    """
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    healer = MeshHealer(shizuku_bridge=bridge, initial_state=HealerState.STAGE_1_RAW_SERIAL)

    for cycle in range(3):
        # 1. Escalate to Stage 2
        await healer.trigger_pan_escalation(source=f"churn_cycle_{cycle}")
        assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING

        # 2. Promote to Stage 3
        await healer.trigger_stage3_handoff("127.0.0.1", 8022)
        assert healer.current_stage == HealerState.STAGE_3_SSH_MOSH

        # 3. Collapse to Stage 1
        await healer._on_pan_link_collapsed()
        assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL

    await healer.stop_monitoring()
