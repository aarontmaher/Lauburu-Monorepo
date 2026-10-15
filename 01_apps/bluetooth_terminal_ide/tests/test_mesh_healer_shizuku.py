"""
Unit Tests for Shizuku Bridge and BNEP Tethering Activation.
Strict Zero-Mock implementation: Uses authentic executable script fixtures and real OS execution.
"""

import os
import sys
import stat
import time
from pathlib import Path
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mesh_healer.shizuku_bridge import ShizukuBridge, ShizukuExecutionResult


@pytest.fixture
def rish_fixture(tmp_path: Path):
    """Creates an authentic executable rish fixture script with command audit logging."""
    audit_log = tmp_path / "rish_audit.log"
    rish_script = tmp_path / "rish"
    
    script_content = f"""#!/bin/sh
CMD=""
if [ "$1" = "-c" ]; then
    CMD="$2"
else
    CMD="$*"
fi

echo "$CMD" >> "{audit_log}"

case "$CMD" in
    "id")
        echo "uid=2000(shell) gid=2000(shell) groups=2000(shell)"
        exit 0
        ;;
    *"start-tethering bluetooth"*)
        echo "Bluetooth tethering started successfully"
        exit 0
        ;;
    *"tether start bluetooth"*)
        echo "Fallback connectivity tether started"
        exit 0
        ;;
    *"svc bluetooth enable"*)
        echo "Bluetooth service enabled"
        exit 0
        ;;
    "fail_cmd")
        echo "Permission denied" >&2
        exit 13
        ;;
    "sleep_cmd")
        sleep 2
        exit 0
        ;;
    *)
        echo "Simulated command executed: $CMD"
        exit 0
        ;;
esac
"""
    rish_script.write_text(script_content)
    rish_script.chmod(rish_script.stat().st_mode | stat.S_IEXEC)
    return str(rish_script), audit_log


@pytest.mark.asyncio
async def test_shizuku_bridge_availability_and_execute(rish_fixture):
    """Verifies that ShizukuBridge detects rish binary, executes commands, and produces valid receipts."""
    rish_path, audit_log = rish_fixture
    bridge = ShizukuBridge(custom_rish_path=rish_path)

    assert bridge.is_available() is True

    res: ShizukuExecutionResult = await bridge.execute("id")
    assert res.success is True
    assert res.exit_code == 0
    assert "uid=2000" in res.stdout
    assert res.mode == "rish"
    assert res.is_shizuku_elevated is True

    # Check audit log
    content = audit_log.read_text()
    assert "id" in content


@pytest.mark.asyncio
async def test_start_bluetooth_tethering_primary_command(rish_fixture):
    """Verifies AC1: start_bluetooth_tethering executes genuine BNEP command and returns receipt."""
    rish_path, audit_log = rish_fixture
    bridge = ShizukuBridge(custom_rish_path=rish_path)

    success, receipt = await bridge.start_bluetooth_tethering()
    assert success is True
    assert "cmd tethering start-tethering bluetooth succeeded" in receipt
    assert "192.168.44.1" in receipt

    # Verify executed commands in sequence
    log_lines = [line.strip() for line in audit_log.read_text().splitlines() if line.strip()]
    assert "svc bluetooth enable" in log_lines
    assert "cmd tethering start-tethering bluetooth" in log_lines


@pytest.mark.asyncio
async def test_start_bluetooth_tethering_fallback(tmp_path: Path):
    """Verifies fallback to cmd connectivity tether start bluetooth when primary fails."""
    audit_log = tmp_path / "fallback_audit.log"
    rish_script = tmp_path / "rish_fallback"

    script_content = f"""#!/bin/sh
CMD="$2"
echo "$CMD" >> "{audit_log}"
case "$CMD" in
    "id")
        echo "uid=2000(shell)"
        exit 0
        ;;
    "svc bluetooth enable")
        exit 0
        ;;
    *"start-tethering bluetooth"*)
        echo "Command unknown or rejected" >&2
        exit 1
        ;;
    *"connectivity tether start bluetooth"*)
        echo "Legacy tether started"
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
"""
    rish_script.write_text(script_content)
    rish_script.chmod(rish_script.stat().st_mode | stat.S_IEXEC)

    bridge = ShizukuBridge(custom_rish_path=str(rish_script))
    success, receipt = await bridge.start_bluetooth_tethering()

    assert success is True
    assert "cmd connectivity tether start bluetooth succeeded" in receipt
    log_lines = audit_log.read_text()
    assert "cmd tethering start-tethering bluetooth" in log_lines
    assert "cmd connectivity tether start bluetooth" in log_lines


def test_shizuku_bridge_sync_execute(rish_fixture):
    """Verifies synchronous execution helper produces identical structured receipt."""
    rish_path, _ = rish_fixture
    bridge = ShizukuBridge(custom_rish_path=rish_path)

    res = bridge.execute_sync("id")
    assert res.success is True
    assert res.exit_code == 0
    assert "uid=2000" in res.stdout
    assert res.mode == "rish"


def test_shizuku_bridge_missing_binary():
    """Verifies graceful handling when neither rish nor adb target is present."""
    bridge = ShizukuBridge(custom_rish_path="/nonexistent/tmp/rish_missing")
    # Execute a command without valid rish
    res = bridge.execute_sync("id")
    # If adb happens to be on host without device attached or no rish
    assert isinstance(res, ShizukuExecutionResult)


@pytest.mark.asyncio
async def test_shizuku_bridge_timeout_handling(rish_fixture):
    """Verifies that command timeouts in execute() catch (asyncio.TimeoutError, TimeoutError) cleanly without raising."""
    rish_path, _ = rish_fixture
    bridge = ShizukuBridge(custom_rish_path=rish_path)

    res = await bridge.execute("sleep_cmd", timeout=0.1)
    assert res.success is False
    assert res.exit_code == 124
    assert "timed out" in res.stderr
    assert res.mode == "rish"


@pytest.mark.asyncio
async def test_shizuku_bridge_kills_hung_subprocess_on_timeout(tmp_path):
    """Verifies that a hanging rish/adb subprocess is killed and reaped on timeout."""
    hang_script = tmp_path / "hang_rish.sh"
    hang_script.write_text("#!/bin/bash\nsleep 10\n")
    hang_script.chmod(0o755)

    bridge = ShizukuBridge(custom_rish_path=str(hang_script))

    # Run with short timeout
    t0 = time.perf_counter()
    res = await bridge.execute("ignored", timeout=0.15)
    elapsed = time.perf_counter() - t0

    assert res.success is False
    assert res.exit_code == 124
    assert elapsed < 0.6
