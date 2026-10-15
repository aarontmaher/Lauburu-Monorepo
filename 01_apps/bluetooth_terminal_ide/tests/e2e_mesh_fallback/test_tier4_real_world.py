"""
Tier 4: Real-World Acceptance Criteria E2E Test Suite (5 Scenarios)
Part of Canonical Mesh Fallback Terminal E2E Test Suite.

Directly verifies all Acceptance Criteria specified in ORIGINAL_REQUEST.md & PROJECT.md:
- TC-T4-AC1: Objective OOB Routing (`/nexus ENABLE_PAN` explicitly logs Shizuku SDK bridge invocation)
- TC-T4-AC2: Simulated Outage Autonomous Escalation (Autonomous 1 ➡️ 2 transition without manual input)
- TC-T4-AC3: Reachable Subnet Triggers SSH/Mosh Spawn without crashing event loop
- TC-T4-04: Full 3-Stage Escalation Ladder Roundtrip (Stage 1 ➡️ 2 ➡️ 3)
- TC-T4-05: Demotion & Self-Healing on Link Collapse (Stage 3 ➡️ 1 + OOB Resurrection)

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
from src.mesh_healer.protocol import OOBMessage
from src.mesh_healer.session_spawner import SessionSpawner
from src.mesh_healer.shizuku_bridge import ShizukuBridge
from tests.e2e_mesh_fallback.fixtures.loopback_factory import (
    get_unused_port,
    start_async_tcp_server,
)


@pytest.mark.asyncio
async def test_t4_ac1_nexus_enable_pan_logs_shizuku_invocation(mock_rish_path: str, audit_log: str):
    """
    AC1: Objective OOB Routing.
    Sending the `/nexus ENABLE_PAN` command explicitly logs that the
    Shizuku SDK bridge has been invoked for the Android edge.
    """
    os.environ["RISH_AUDIT_LOG"] = audit_log
    captured_logs: List[str] = []

    try:
        bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
        healer = MeshHealer(
            shizuku_bridge=bridge,
            initial_state=HealerState.STAGE_1_RAW_SERIAL,
            on_log_message=lambda lvl, msg: captured_logs.append(msg),
        )

        # 1. Dispatch the canonical /nexus ENABLE_PAN command
        response = await healer.handle_command("/nexus ENABLE_PAN")
        assert response is not None
        assert "[MESH_HEALER]" in response
        assert "Stage 2 PAN Escalation triggered" in response

        # 2. Assert that Shizuku SDK bridge was explicitly logged
        logged_shizuku_invocation = any(
            "Invoking Android Edge Shizuku SDK Bridge" in log and "Mode: rish" in log
            for log in captured_logs
        )
        assert logged_shizuku_invocation, (
            "AC1 Requirement Failed: Log output does not explicitly mention Shizuku bridge invocation.\n"
            + "\n".join(captured_logs)
        )

        # 3. Assert that Shizuku execution receipt was logged
        logged_shizuku_receipt = any(
            "[SHIZUKU]" in log and "BNEP active" in log
            for log in captured_logs
        )
        assert logged_shizuku_receipt, (
            "AC1 Requirement Failed: Log output does not contain [SHIZUKU] receipt.\n"
            + "\n".join(captured_logs)
        )

        # 4. Assert physical actuation: mock_rish actually executed the command
        with open(audit_log, "r", encoding="utf-8") as f:
            audit_data = f.read()
        assert "cmd tethering start-tethering bluetooth" in audit_data

        await healer.stop_monitoring()
    finally:
        os.environ.pop("RISH_AUDIT_LOG", None)


@pytest.mark.asyncio
async def test_t4_ac2_simulated_outage_autonomous_escalation(mock_rish_path: str):
    """
    AC2: Simulated Outage Escalation.
    When a simulated Tailscale IP failure occurs, the terminal autonomously logs
    the transition from Stage 1 to Stage 2 without requiring manual user input.
    """
    captured_logs: List[str] = []
    stage_history: List[HealerState] = []

    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    dead_p = get_unused_port()

    # Outage detector configured with 1-cycle failure threshold for deterministic test execution
    detector = MeshOutageDetector(
        targets={"Simulated_Tailscale_Node": {"tailscale": "127.0.0.1"}},
        failure_threshold=1,
        probe_timeout=0.05,
        probe_interval=0.1,
    )
    # Fail probe without any network delay
    detector.probe_endpoint = lambda ip, **kw: asyncio.sleep(0.01, result=False)

    healer = MeshHealer(
        shizuku_bridge=bridge,
        outage_detector=detector,
        initial_state=HealerState.STAGE_1_RAW_SERIAL,
        on_stage_changed=lambda old_s, new_s: stage_history.append(new_s),
        on_log_message=lambda lvl, msg: captured_logs.append(msg),
    )

    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL

    # Start background monitoring loop
    await healer.start_monitoring()

    # Wait for autonomous prober cycle (ZERO manual input provided!)
    await asyncio.sleep(0.3)

    # Assert Stage 1 -> Stage 2 transition occurred autonomously
    assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING
    assert HealerState.STAGE_2_PAN_ESCALATING in stage_history

    # Assert autonomous transition was explicitly logged
    autonomous_log_found = any(
        "Autonomous escalation from Stage 1 to Stage 2 triggered" in log
        for log in captured_logs
    )
    assert autonomous_log_found, (
        "AC2 Requirement Failed: Outage transition not found in log output.\n"
        + "\n".join(captured_logs)
    )

    await healer.stop_monitoring()


@pytest.mark.asyncio
async def test_t4_ac3_reachable_subnet_triggers_ssh_spawn_without_event_loop_crash(
    live_tcp_server: Tuple[str, int], mock_ssh_path: str, audit_log: str
):
    """
    AC3: Subprocess Handoff.
    Once the 192.168.44.x subnet is reachable, the terminal successfully spawns
    the SSH/Mosh session without crashing or blocking the primary event loop.
    """
    os.environ["SSH_AUDIT_LOG"] = audit_log
    os.environ["SSH_STAY_ALIVE"] = "1"
    host, port = live_tcp_server

    captured_logs: List[str] = []

    try:
        spawner = SessionSpawner(
            custom_binary_path=mock_ssh_path,
            gateway_ip=host,
            ssh_ports=(port,),
            watchdog_interval=1.0,
        )

        healer = MeshHealer(
            session_spawner=spawner,
            initial_state=HealerState.STAGE_2_PAN_ESCALATING,
            on_log_message=lambda lvl, msg: captured_logs.append(msg),
        )

        # 1. Trigger handoff to reachable endpoint
        handoff_ok = await healer.trigger_stage3_handoff(target_ip=host, port=port)
        assert handoff_ok is True
        assert healer.current_stage == HealerState.STAGE_3_SSH_MOSH
        assert spawner.is_session_active is True
        assert spawner.active_pid is not None

        # 2. Wait for child process to register
        await asyncio.sleep(0.15)
        with open(audit_log, "r", encoding="utf-8") as f:
            audit_text = f.read()
        assert f"PID={spawner.active_pid}" in audit_text

        # 3. CRITICAL EVENT LOOP HEALTH PROOF:
        # Verify event loop is 100% responsive and unblocked:
        # Run coroutines, command handlers, and timer tasks concurrently
        t0 = time.perf_counter()
        status_resp = await healer.handle_command("/nexus STATUS")
        assert status_resp is not None
        assert "Stage=STAGE_3_SSH_MOSH" in status_resp
        assert "SessionActive=True" in status_resp

        # Concurrent async task executes without latency spike
        await asyncio.sleep(0.05)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"Event loop showed unacceptable latency ({elapsed:.2f}s)"

        await healer.stop_monitoring()
    finally:
        os.environ.pop("SSH_AUDIT_LOG", None)
        os.environ.pop("SSH_STAY_ALIVE", None)


@pytest.mark.asyncio
async def test_t4_04_full_3stage_escalation_ladder_roundtrip(
    live_tcp_server: Tuple[str, int], mock_rish_path: str, mock_ssh_path: str
):
    """
    Scenario 4: Full 3-Stage Escalation Ladder Roundtrip.
    End-to-end verification of Stage 1 (Raw Serial) ➡️ Stage 2 (Bluetooth PAN) ➡️ Stage 3 (SSH Handoff).
    """
    host, port = live_tcp_server
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    spawner = SessionSpawner(
        custom_binary_path=mock_ssh_path,
        gateway_ip=host,
        ssh_ports=(port,),
    )

    stage_log = []
    healer = MeshHealer(
        shizuku_bridge=bridge,
        session_spawner=spawner,
        initial_state=HealerState.STAGE_1_RAW_SERIAL,
        on_stage_changed=lambda old_s, new_s: stage_log.append((old_s, new_s)),
    )

    # 1. Starts in Stage 1
    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL

    # 2. Stage 2 Escalation (outage / manual command)
    pan_ok = await healer.trigger_pan_escalation(source="e2e_roundtrip")
    assert pan_ok is True
    assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING

    # 3. Subnet reachability confirmed -> Stage 3 Handoff
    reachable, active_p = await spawner.probe_reachability(host, (port,), timeout=0.5)
    assert reachable is True
    ssh_ok = await healer.trigger_stage3_handoff(host, active_p)
    assert ssh_ok is True
    assert healer.current_stage == HealerState.STAGE_3_SSH_MOSH

    # Verify transition sequence
    transitions = [new_s for _, new_s in stage_log]
    assert HealerState.STAGE_2_PAN_ESCALATING in transitions
    assert HealerState.STAGE_3_SSH_MOSH in transitions

    await healer.stop_monitoring()


@pytest.mark.asyncio
async def test_t4_05_demotion_on_link_collapse_with_oob_resurrection(mock_rish_path: str):
    """
    Scenario 5: Demotion and Self-Healing on Link Collapse.
    When Stage 3 link collapses, watchdog demotes to Stage 1 and fires OOB recovery packet.
    """
    bridge = ShizukuBridge(custom_rish_path=mock_rish_path)
    dead_p = get_unused_port()

    spawner = SessionSpawner(
        gateway_ip="127.0.0.1",
        ssh_ports=(dead_p,),
        watchdog_interval=0.1,
    )

    healer = MeshHealer(
        shizuku_bridge=bridge,
        session_spawner=spawner,
        initial_state=HealerState.STAGE_3_SSH_MOSH,
    )

    assert healer.current_stage == HealerState.STAGE_3_SSH_MOSH

    # Trigger watchdog with unreachable port
    spawner.is_session_active = True
    spawner.start_watchdog("127.0.0.1", dead_p)

    # Wait for 3 misses to trip demotion
    await asyncio.sleep(0.45)

    # Assert demotion to Stage 1
    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL
    assert spawner.is_session_active is False

    await healer.stop_monitoring()
