"""
Unit tests for DaemonSupervisor circuit breaking, CronScheduler lifespan integration,
and REPL slash command security in AgiCodingTerminalView.
"""

import os
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from backend.agents.crons.daemon_supervisor import DaemonSupervisor, MAX_RESTART_ATTEMPTS
from backend.agents.cron_scheduler import get_cron_scheduler, SmolagentCronScheduler


@pytest.mark.asyncio
async def test_daemon_supervisor_missing_binary_no_crash():
    """Verify DaemonSupervisor handles missing binaries gracefully without FileNotFoundError."""
    supervisor = DaemonSupervisor()
    # Mock commands with non-existent binary
    fake_cmds = {
        "nonexistent_daemon": {
            "check": ["nonexistent_binary_xyz_123", "--status"],
            "start": ["nonexistent_binary_xyz_123", "--start"],
        }
    }
    with patch.object(supervisor, "_get_daemon_commands", return_value=fake_cmds):
        report = await supervisor.run_monitoring_cycle()
        assert "daemons" in report
        assert report["daemons"]["nonexistent_daemon"] in ("OFFLINE", "FAILED_CIRCUIT_OPEN")


@pytest.mark.asyncio
async def test_daemon_supervisor_circuit_breaker_quarantine():
    """Verify that after MAX_RESTART_ATTEMPTS failures, daemon enters FAILED_CIRCUIT_OPEN state."""
    supervisor = DaemonSupervisor()
    fake_cmds = {
        "failing_daemon": {
            "check": ["nonexistent_binary_check", "--status"],
            "start": ["nonexistent_binary_start", "--start"],
        }
    }
    with patch.object(supervisor, "_get_daemon_commands", return_value=fake_cmds):
        # Simulate 3 cycles with reset last_restart_time to bypass cooldown during test
        for i in range(MAX_RESTART_ATTEMPTS):
            supervisor.last_restart_time["failing_daemon"] = 0.0
            report = await supervisor.run_monitoring_cycle()

        # Next cycle should report FAILED_CIRCUIT_OPEN
        report = await supervisor.run_monitoring_cycle()
        assert report["daemons"]["failing_daemon"] == "FAILED_CIRCUIT_OPEN"
        assert supervisor.restart_counts["failing_daemon"] >= MAX_RESTART_ATTEMPTS


@pytest.mark.asyncio
async def test_daemon_supervisor_container_clean_exit_ignored():
    """Verify that Docker containers with clean exit code 0 are not restarted."""
    supervisor = DaemonSupervisor()
    # Mock docker ps output with one clean exit and one error exit
    mock_docker_output = (
        b"clean_task_container|Exited|Exited (0) 2 hours ago\n"
        b"failed_app_container|Exited|Exited (137) 5 minutes ago\n"
    )

    with patch("shutil.which", return_value="/usr/local/bin/docker"), \
         patch("asyncio.create_subprocess_shell") as mock_proc:
        
        proc_instance = MagicMock()
        proc_instance.communicate = MagicMock(return_value=asyncio.Future())
        proc_instance.communicate.return_value.set_result((mock_docker_output, b""))
        proc_instance.returncode = 0
        proc_instance.wait = MagicMock(return_value=asyncio.Future())
        proc_instance.wait.return_value.set_result(0)
        mock_proc.return_value = proc_instance

        res = await supervisor._check_and_heal_containers()
        assert res.get("clean_task_container") == "EXITED_CLEAN"
        assert res.get("failed_app_container") == "RESTARTED"


def test_cron_scheduler_registration_and_get_instance():
    """Verify CronScheduler registers required system jobs."""
    scheduler = get_cron_scheduler()
    assert isinstance(scheduler, SmolagentCronScheduler)
    assert "network_health_scan" in scheduler.jobs
    assert "obsidian_telemetry_sync" in scheduler.jobs
    assert "self_healing_keepalive" in scheduler.jobs
    assert "lora_dataset_harvester" in scheduler.jobs


def test_repl_slash_commands_key_security(monkeypatch):
    """Verify /key, /key_cf, /account_cf, /key_julien commands set environment variables and mask output."""
    from tui.views.agi_coding_terminal_view import AgiCodingTerminalView

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("JULIEN_API_KEY", raising=False)

    view = AgiCodingTerminalView()
    logs = []
    view._log_terminal = lambda msg: logs.append(msg)

    # Test /key
    view._execute_repl_command("/key sk-gemini-test-secret-12345")
    assert os.environ.get("GEMINI_API_KEY") == "sk-gemini-test-secret-12345"
    assert any("Gemini API Key configured" in l and "sk-...2345" in l for l in logs)

    # Test /key_cf
    view._execute_repl_command("/key_cf cf-secret-token-abcdef1234")
    assert os.environ.get("CLOUDFLARE_API_KEY") == "cf-secret-token-abcdef1234"
    assert any("Cloudflare API Key configured" in l and "cf-...1234" in l for l in logs)

    # Test /account_cf
    view._execute_repl_command("/account_cf acc-id-9988776655")
    assert os.environ.get("CLOUDFLARE_ACCOUNT_ID") == "acc-id-9988776655"
    assert any("Cloudflare Account ID configured" in l and "acc...6655" in l for l in logs)

    # Test /key_julien
    view._execute_repl_command("/key_julien julien-super-secret-key-9999")
    assert os.environ.get("JULIEN_API_KEY") == "julien-super-secret-key-9999"
    assert any("Julien API Key configured" in l and "jul...9999" in l for l in logs)

    # Test unknown slash command
    view._execute_repl_command("/unknown_cmd_xyz")
    assert any("Unknown slash command: /unknown_cmd_xyz" in l for l in logs)
