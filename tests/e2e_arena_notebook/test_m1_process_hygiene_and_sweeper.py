"""
Test Suite for Milestone M1: Process Hygiene, Sweeper Daemon, and Headless Mandates.
Verifies:
1. Playwright Sweeper Daemon process scanning, TTL calculation, and two-stage termination.
2. Active vs stale process filtering.
3. Strict non-interactive Matplotlib Agg backend enforcement and plt.show() safety.
4. Concurrency limits (max_workers=2).
5. Headless browser options (--headless=new).
"""

import ast
import concurrent.futures
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

import pytest
import matplotlib
import matplotlib.pyplot as plt

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    SWEEPER_DAEMON_PATH,
    SWEEPER_LOG_PATH,
    MAX_TEST_WORKERS,
    PLAYWRIGHT_HEADLESS_ARGS,
    assert_headless_browser_options,
)

# Import daemon functions
sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling" / "daemons"))
from playwright_sweeper_daemon import (
    parse_etime,
    is_target_process,
    scan_processes_ps,
    scan_processes_psutil,
    scan_processes,
    is_process_alive,
    terminate_process,
    sweep_once,
    ProcessInfo,
    SweeperDaemon,
    TARGET_PATTERNS,
    EXCLUDE_PATTERNS,
)


class TestSweeperEtimeParser:
    """Unit tests for POSIX etime format parsing."""

    def test_parse_etime_empty(self):
        assert parse_etime("") == 0.0
        assert parse_etime("   ") == 0.0

    def test_parse_etime_seconds_only(self):
        assert parse_etime("45") == 45.0
        assert parse_etime("0") == 0.0

    def test_parse_etime_mm_ss(self):
        assert parse_etime("05:30") == 330.0
        assert parse_etime("00:15") == 15.0
        assert parse_etime("59:59") == 3599.0

    def test_parse_etime_hh_mm_ss(self):
        assert parse_etime("01:00:00") == 3600.0
        assert parse_etime("02:15:30") == 8130.0
        assert parse_etime("23:59:59") == 86399.0

    def test_parse_etime_days_hh_mm_ss(self):
        assert parse_etime("1-00:00:00") == 86400.0
        assert parse_etime("3-02:10:05") == 3 * 86400.0 + 2 * 3600.0 + 10 * 60.0 + 5.0

    def test_parse_etime_invalid(self):
        assert parse_etime("invalid") == 0.0
        assert parse_etime("1:2:3:4") == 0.0


class TestSweeperProcessMatching:
    """Unit tests for target process identification."""

    def test_matches_playwright_patterns(self):
        assert is_target_process("node", "/path/to/playwright/driver", 12345)
        assert is_target_process("node", "ms-playwright/chromium-1155/chrome", 12345)
        assert is_target_process("python", "-m playwright test", 12345)

    def test_matches_chrome_patterns(self):
        assert is_target_process("Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", 12345)
        assert is_target_process("chromium", "/usr/bin/chromium --headless=new", 12345)
        assert is_target_process("chromedriver", "/usr/local/bin/chromedriver", 12345)
        assert is_target_process("chrome-headless-shell", "/path/to/chrome-headless-shell", 12345)

    def test_ignores_current_process(self):
        current_pid = os.getpid()
        assert not is_target_process("Google Chrome", "test chrome", current_pid)

    def test_ignores_non_target_binaries(self):
        assert not is_target_process("python3", "pytest tests/e2e", 12345)
        assert not is_target_process("bash", "/bin/bash -c echo hello", 12345)
        assert not is_target_process("zsh", "-i", 12345)
        assert not is_target_process("launchd", "/sbin/launchd", 1)

    def test_respects_exclusions(self):
        assert not is_target_process("remoting_me2me_host", "/Library/PrivilegedHelperTools/ChromeRemoteDesktopHost", 12345)
        assert not is_target_process("code", "/Applications/Visual Studio Code.app", 12345)
        assert not is_target_process("antigravity", "antigravity daemon", 12345)
        assert not is_target_process("python", "python playwright_sweeper_daemon.py", 12345)


class TestSweeperScanningAndTermination:
    """Integration tests for process scanning and two-stage termination."""

    def test_scan_processes_returns_valid_structure(self):
        procs = scan_processes()
        assert isinstance(procs, list)
        for p in procs:
            assert isinstance(p, ProcessInfo)
            assert isinstance(p.pid, int)
            assert p.pid > 0
            assert isinstance(p.age_seconds, (int, float))
            assert p.age_seconds >= 0.0
            d = p.to_dict()
            assert "pid" in d and "age_seconds" in d and "cmdline" in d

    def test_is_process_alive_utility(self):
        assert is_process_alive(os.getpid())
        assert not is_process_alive(9999999)

    def test_stale_process_lifecycle_and_termination(self, temp_test_dir):
        """Spawn a simulated process, trigger sweep with TTL=0, verify termination."""
        # Launch a dummy sleep process
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pid = proc.pid
        assert is_process_alive(pid)

        try:
            # Explicitly terminate using terminate_process (two-stage SIGTERM -> SIGKILL)
            success = terminate_process(pid, sigterm_timeout=1.0)
            assert success is True
            assert not is_process_alive(pid)
        finally:
            if is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

    def test_active_process_preserved_by_sweeper(self):
        """Verify that an active process with age < TTL is preserved."""
        # Spawn a short-lived process with a target keyword in custom target patterns
        test_pattern = "sweeper_active_test_probe"
        proc = subprocess.Popen(
            [sys.executable, "-c", f"import time; # {test_pattern}\ntime.sleep(15)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pid = proc.pid
        assert is_process_alive(pid)

        try:
            # Sweep with high TTL (300s) targeting our probe pattern
            result = sweep_once(
                ttl=300.0,
                dry_run=False,
                target_patterns=[test_pattern],
                exclude_patterns=[],
            )
            # Process should be in active_details, NOT terminated
            assert is_process_alive(pid)
            assert any(p["pid"] == pid for p in result["active_details"])
            assert pid not in result["terminated_pids"]
        finally:
            if is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

    def test_stale_process_terminated_by_sweeper(self):
        """Verify that a process with age >= TTL is detected and terminated."""
        test_pattern = "sweeper_stale_test_probe"
        proc = subprocess.Popen(
            [sys.executable, "-c", f"import time; # {test_pattern}\ntime.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pid = proc.pid
        assert is_process_alive(pid)

        try:
            # Sweep with TTL=0.0 to simulate an expired process
            result = sweep_once(
                ttl=0.0,
                dry_run=False,
                target_patterns=[test_pattern],
                exclude_patterns=[],
            )
            assert pid in result["terminated_pids"]
            assert not is_process_alive(pid)
        finally:
            if is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

    def test_dry_run_mode_does_not_kill(self):
        """Verify that dry_run=True identifies stale processes without killing them."""
        test_pattern = "sweeper_dryrun_test_probe"
        proc = subprocess.Popen(
            [sys.executable, "-c", f"import time; # {test_pattern}\ntime.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pid = proc.pid
        assert is_process_alive(pid)

        try:
            result = sweep_once(
                ttl=0.0,
                dry_run=True,
                target_patterns=[test_pattern],
                exclude_patterns=[],
            )
            # Reported as terminated in dry-run summary
            assert pid in result["terminated_pids"]
            # But process must still be running!
            assert is_process_alive(pid)
        finally:
            if is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass


class TestDaemonCLIAndLogging:
    """Verification of CLI interface and logging."""

    def test_daemon_script_exists_and_executable(self):
        assert SWEEPER_DAEMON_PATH.exists(), f"Sweeper daemon missing at {SWEEPER_DAEMON_PATH}"
        assert os.access(SWEEPER_DAEMON_PATH, os.X_OK), "Sweeper daemon script must be executable"

    def test_daemon_status_cli(self):
        res = subprocess.run(
            [sys.executable, str(SWEEPER_DAEMON_PATH), "--status"],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert "PLAYWRIGHT & CHROME PROCESS STATUS" in res.stdout

    def test_daemon_dry_run_cli(self, temp_test_dir):
        custom_log = temp_test_dir / "custom_sweeper.log"
        res = subprocess.run(
            [
                sys.executable,
                str(SWEEPER_DAEMON_PATH),
                "--once",
                "--dry-run",
                "--log-file",
                str(custom_log),
                "-v",
            ],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert custom_log.exists()
        log_content = custom_log.read_text(encoding="utf-8")
        assert "Sweep completed" in log_content

    def test_sweeper_log_file_integrity(self):
        if SWEEPER_LOG_PATH.exists():
            log_content = SWEEPER_LOG_PATH.read_text(encoding="utf-8")
            assert len(log_content) > 0
            assert "PlaywrightSweeper" in log_content


class TestProcessHygieneFixturesAndMandates:
    """Verification of pytest fixtures enforcing process hygiene, headless browser, and Matplotlib Agg."""

    def test_matplotlib_agg_backend_enforced(self):
        assert matplotlib.get_backend().lower() == "agg"
        assert os.environ.get("MPLBACKEND") == "Agg"

    def test_plt_show_does_not_spawn_gui_window(self):
        """Ensure plt.show() executes safely without raising or spawning GUI."""
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3], [4, 5, 6])
        # Call plt.show() - must not error or pop up
        plt.show()
        # Verify clean state
        assert len(plt.get_fignums()) == 0

    def test_playwright_headless_fixtures_conform_to_mandate(
        self,
        playwright_headless_options,
        playwright_browser_args,
    ):
        assert playwright_headless_options["headless"] is True
        assert "--headless=new" in playwright_headless_options["args"]
        assert "--headless=new" in playwright_browser_args
        assert assert_headless_browser_options(playwright_headless_options) is True

    def test_assert_headless_browser_options_catches_violations(self):
        # Non-headless flag
        with pytest.raises(AssertionError):
            assert_headless_browser_options({"headless": False, "args": ["--headless=new"]})

        # Missing --headless=new arg
        with pytest.raises(AssertionError):
            assert_headless_browser_options({"headless": True, "args": ["--no-sandbox"]})

    def test_concurrency_max_workers_fixture(self, max_workers, capped_thread_pool):
        assert max_workers == MAX_TEST_WORKERS == 2
        assert capped_thread_pool._max_workers == 2

        # Verify concurrent task execution respects worker limit
        results = []
        def task(x):
            time.sleep(0.01)
            return x * 2

        futures = [capped_thread_pool.submit(task, i) for i in range(4)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

        assert sorted(results) == [0, 2, 4, 6]
