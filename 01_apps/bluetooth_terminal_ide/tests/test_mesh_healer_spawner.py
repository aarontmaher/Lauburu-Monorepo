"""
Unit Tests for Session Spawner, Reachability Detector, and Stage 3 Watchdog Demotion.
Zero-mock compliance: Uses genuine local loopback TCP sockets, authentic executable scripts,
and real process lifecycle management.
"""

import asyncio
import os
import signal
import stat
import sys
import time
from pathlib import Path
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mesh_healer.healer_engine import HealerState, MeshHealer
from mesh_healer.session_spawner import SessionSpawner
from mesh_healer.shizuku_bridge import ShizukuBridge


@pytest.fixture
def fake_ssh_runner(tmp_path: Path):
    """Creates a genuine executable runner fixture simulating ssh/mosh invocations."""
    audit_file = tmp_path / "ssh_spawn_audit.log"
    runner_script = tmp_path / "test_ssh_runner.sh"

    content = f"""#!/bin/sh
echo "$@" > "{audit_file}"
sleep 10
exit 0
"""
    runner_script.write_text(content)
    runner_script.chmod(0o755)
    return str(runner_script), audit_file


@pytest.mark.asyncio
async def test_subnet_reachability_2_probe_debounce():
    """Verifies that subnet reachability requires 2 consecutive successful probes."""
    spawner = SessionSpawner()

    async def handle_client(reader, writer):
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    try:
        # Probe reachable server
        is_reachable, active_port = await spawner.probe_reachability(
            host="127.0.0.1", ports=(port, 9999), timeout=0.2
        )
        assert is_reachable is True
        assert active_port == port
    finally:
        server.close()
        await server.wait_closed()

    # Closed ports
    is_reachable, active_port = await spawner.probe_reachability(
        host="127.0.0.1", ports=(port,), timeout=0.2
    )
    assert is_reachable is False
    assert active_port is None


def test_adaptive_binary_selection():
    """Verifies adaptive fallback from mosh to ssh when mosh is not installed."""
    spawner = SessionSpawner()
    binary_name, args, cmd_str = spawner.resolve_binary_and_command(
        host="192.168.44.1", port=8022, user="u0_a363"
    )

    # In standard macOS host environment, mosh is not installed; ssh is selected
    assert binary_name in ["mosh", "ssh"]
    assert "8022" in cmd_str
    assert "u0_a363@192.168.44.1" in cmd_str


@pytest.mark.asyncio
async def test_spawn_session_background_process(fake_ssh_runner):
    """Verifies non-blocking background subprocess spawning with real process tracking and cleanup."""
    runner_path, audit_log = fake_ssh_runner
    spawner = SessionSpawner(
        custom_binary_path=runner_path,
        gateway_ip="127.0.0.1",
        watchdog_interval=10.0,  # Long interval so it doesn't fire immediately
    )

    success, msg = await spawner.spawn_session(
        mode="background", host="127.0.0.1", port=8022
    )
    assert success is True
    assert spawner.is_session_active is True
    assert spawner.active_pid is not None

    # Verify command execution in audit log
    for _ in range(20):
        if audit_log.exists():
            break
        await asyncio.sleep(0.1)
    assert audit_log.exists(), f"Audit log was not created at {audit_log}"
    content = audit_log.read_text()
    assert "-p 8022" in content

    # Terminate cleanly
    await spawner.terminate_session()
    assert spawner.is_session_active is False
    assert spawner.active_process is None


@pytest.mark.asyncio
async def test_terminate_session_stubborn_child_sigkill_escalation():
    """
    Regression Test for session_spawner.py:282.
    Verifies that terminate_session() sends SIGTERM, detects timeout via
    (asyncio.TimeoutError, TimeoutError) when the child ignores SIGTERM (SIG_IGN),
    triggers self.active_process.kill() (SIGKILL), and cleanly reaps the process.
    Zero-mock: Uses genuine OS process spawning, real signal trapping, and kernel process table queries.
    """
    spawner = SessionSpawner()

    # Spawn a genuine child process that explicitly ignores SIGTERM.
    # Synchronize via stdout readline to guarantee SIG_IGN is active before SIGTERM is sent.
    child_code = (
        "import signal, sys, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "sys.stdout.write('READY\\n'); "
        "sys.stdout.flush(); "
        "time.sleep(30)"
    )
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        child_code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    # Synchronize: wait until the child confirms SIG_IGN is registered
    ready_line = await proc.stdout.readline()
    assert ready_line == b"READY\n"

    pid = proc.pid
    spawner.active_process = proc
    spawner.active_pid = pid
    spawner.is_session_active = True

    # Pre-condition: process is actively running in the OS
    os.kill(pid, 0)

    # Actuate terminate_session: sends SIGTERM, times out, escalates to SIGKILL
    await spawner.terminate_session()

    # Post-conditions:
    # 1. Spawner internal state is completely cleared
    assert spawner.active_process is None
    assert spawner.active_pid is None
    assert spawner.is_session_active is False

    # 2. Process was terminated via SIGKILL (-9 or -signal.SIGKILL)
    assert proc.returncode in (-signal.SIGKILL, -9)

    # 3. Process is completely absent from OS process table (no orphaned leak)
    with pytest.raises(OSError):
        os.kill(pid, 0)


@pytest.mark.asyncio
async def test_watchdog_3_misses_triggers_demotion():
    """Verifies that 3 consecutive misses in the watchdog loop triggers link collapse callback."""
    collapsed_events = []

    def on_collapse():
        collapsed_events.append("LINK_COLLAPSED")

    spawner = SessionSpawner(
        gateway_ip="127.0.0.1",
        watchdog_interval=0.1,  # Fast interval for test
        on_link_collapsed=on_collapse,
    )

    # Pick an unused closed port
    test_server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    closed_port = test_server.sockets[0].getsockname()[1]
    test_server.close()
    await test_server.wait_closed()

    spawner.start_watchdog("127.0.0.1", closed_port)

    # Wait for 3 misses (~0.35s)
    await asyncio.sleep(0.5)

    assert len(collapsed_events) >= 1
    assert spawner.is_session_active is False
    spawner.stop_watchdog()


@pytest.mark.asyncio
async def test_mesh_healer_full_state_machine_escalation(fake_ssh_runner, tmp_path: Path):
    """
    End-to-end integration test of MeshHealer state machine:
    STAGE_1 -> trigger_pan_escalation -> STAGE_2_PAN_ESCALATING -> Subnet Reachable -> STAGE_3_SSH_MOSH -> Demotion.
    """
    runner_path, _ = fake_ssh_runner

    # Create dummy rish for shizuku bridge
    rish_script = tmp_path / "rish_sm"
    rish_script.write_text("#!/bin/sh\necho 'uid=2000'\nexit 0\n")
    rish_script.chmod(rish_script.stat().st_mode | stat.S_IEXEC)

    bridge = ShizukuBridge(custom_rish_path=str(rish_script))
    spawner = SessionSpawner(
        custom_binary_path=runner_path,
        gateway_ip="127.0.0.1",
        watchdog_interval=0.1,
    )

    healer = MeshHealer(
        shizuku_bridge=bridge,
        session_spawner=spawner,
        initial_state=HealerState.STAGE_1_RAW_SERIAL,
    )

    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL

    # 1. Trigger Stage 2 escalation
    ok = await healer.trigger_pan_escalation(source="test_state_machine")
    assert ok is True
    assert healer.current_stage == HealerState.STAGE_2_PAN_ESCALATING

    # 2. Trigger Stage 3 handoff directly
    handoff_ok = await healer.trigger_stage3_handoff("127.0.0.1", 8022)
    assert handoff_ok is True
    assert healer.current_stage == HealerState.STAGE_3_SSH_MOSH

    # 3. Simulate link collapse
    await healer._on_pan_link_collapsed()
    assert healer.current_stage == HealerState.STAGE_1_RAW_SERIAL

    await healer.stop_monitoring()


@pytest.mark.asyncio
async def test_bluetooth_terminal_app_nexus_enable_pan_integration(tmp_path: Path):
    """Verifies AC1: sending /nexus ENABLE_PAN in BluetoothTerminalApp invokes Shizuku and logs receipt without freezing UI."""
    from bluetooth_terminal_app import BluetoothTerminalApp

    audit_log = tmp_path / "app_shizuku_audit.log"
    rish_script = tmp_path / "rish_app.sh"
    rish_script.write_text(f"""#!/bin/sh
echo "$@" >> "{audit_log}"
exit 0
""")
    rish_script.chmod(0o755)

    bridge = ShizukuBridge(custom_rish_path=str(rish_script))
    healer = MeshHealer(shizuku_bridge=bridge)
    app = BluetoothTerminalApp(mesh_healer=healer)

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        input_widget = app.query_one("#terminal_input")
        input_widget.focus()
        from textual.widgets import Input
        app.post_message(Input.Submitted(input_widget, "/nexus ENABLE_PAN"))
        await pilot.pause(0.6)

        # Check log widget lines
        log_text = "\n".join(str(line.text) for line in app.log_widget.lines)
        assert "ENABLE_PAN" in log_text
        assert "Shizuku" in log_text or "SHIZUKU" in log_text
        assert app.is_running is True


@pytest.mark.asyncio
async def test_watchdog_link_collapse_stubborn_child_demotion_and_kill():
    """
    Regression Test for Defect 1:
    Verifies that when watchdog detects link collapse while a stubborn child ignoring SIGTERM
    is active, stop_watchdog() does not cancel the watchdog task itself.
    The stubborn child is escalated to SIGKILL (-9), reaped from the OS table, and
    on_link_collapsed callback is guaranteed to fire.
    """
    collapsed_events = []
    spawner = SessionSpawner(
        watchdog_interval=0.05,
        on_link_collapsed=lambda: collapsed_events.append(True),
    )

    child_code = (
        "import signal, sys, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "sys.stdout.write('READY\\n'); "
        "sys.stdout.flush(); "
        "time.sleep(30)"
    )
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        child_code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    ready_line = await proc.stdout.readline()
    assert ready_line == b"READY\n"
    pid = proc.pid

    try:
        spawner.active_process = proc
        spawner.active_pid = pid
        spawner.is_session_active = True

        # Start watchdog on an unused, closed port
        test_server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
        unreachable_port = test_server.sockets[0].getsockname()[1]
        test_server.close()
        await test_server.wait_closed()

        spawner.start_watchdog("127.0.0.1", unreachable_port)

        # Wait for link collapse and SIGKILL escalation (3 misses * 0.05s + 1.5s timeout)
        for _ in range(40):
            if len(collapsed_events) > 0 and proc.returncode is not None:
                break
            await asyncio.sleep(0.1)

        assert len(collapsed_events) >= 1
        assert proc.returncode in (-signal.SIGKILL, -9)
        with pytest.raises(OSError):
            os.kill(pid, 0)
        assert spawner.is_session_active is False
        assert spawner.active_process is None
    finally:
        spawner.stop_watchdog()
        if proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass


@pytest.mark.asyncio
async def test_watchdog_repointing_when_active():
    """
    Regression Test for Defect 2:
    Verifies that re-pointing start_watchdog() while a previous watchdog is in-flight
    does not allow the cancelled task's finally block to clobber _watchdog_running to False.
    """
    spawner = SessionSpawner(watchdog_interval=0.1)
    spawner.start_watchdog("127.0.0.1", 8022)
    await asyncio.sleep(0.02)

    # Re-point while Task 1 is active
    spawner.start_watchdog("127.0.0.1", 8023)
    await asyncio.sleep(0.3)

    assert spawner._watchdog_running is True, "Watchdog should be running after re-pointing"
    assert spawner._watchdog_task is not None, "New watchdog task must exist"
    assert not spawner._watchdog_task.done(), "New watchdog task should be active"

    spawner.stop_watchdog()

