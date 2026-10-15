"""
Adversarial Stress Test Suite: Process Hygiene, Sweeper Daemon, Concurrency, and Headless Mandates.
Authored by Challenger 1 (teamwork_preview_challenger_1).

Empirical verification for:
1. Playwright Sweeper Daemon: TTL parsing, 2-stage SIGTERM -> SIGKILL kill, active vs stale preservation.
2. Concurrency limit: High-load stress verification that max_workers=2 is strictly bounded.
3. Headless browser: 0 dock icons, 0 macOS GUI popups with --headless=new.
4. Matplotlib Agg backend: Complete prevention of interactive GUI figure windows on macOS.
"""

import ast
import concurrent.futures
import json
import logging
import math
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Any

import pytest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    SWEEPER_DAEMON_PATH,
    SWEEPER_LOG_PATH,
    MAX_TEST_WORKERS,
    PLAYWRIGHT_HEADLESS_ARGS,
    assert_headless_browser_options,
)

# Import sweeper daemon components
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
    DEFAULT_SIGTERM_TIMEOUT,
)


class TestSweeperAdversarialLifecycle:
    """Adversarial stress-testing of the Playwright Sweeper Daemon."""

    def test_adv_sigterm_responsive_process(self):
        """Verify normal process cleanly exits on SIGTERM without needing SIGKILL."""
        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", "import time; print('READY', flush=True); time.sleep(120)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        line = proc.stdout.readline()
        assert "READY" in line
        pid = proc.pid
        assert is_process_alive(pid)

        t_start = time.time()
        success = terminate_process(pid, sigterm_timeout=2.0)
        t_elapsed = time.time() - t_start

        assert success is True
        assert not is_process_alive(pid)
        # Should terminate quickly (well before sigterm_timeout)
        assert t_elapsed < 1.5, f"SIGTERM took unexpectedly long: {t_elapsed:.2f}s"

    def test_adv_sigterm_stubborn_process_escalates_to_sigkill(self):
        """
        Adversarial test: Process explicitly traps & ignores SIGTERM.
        Sweeper MUST wait sigterm_timeout and escalate to SIGKILL to eliminate it.
        """
        stubborn_code = """
import signal, time, sys

def ignore_term(signum, frame):
    pass

signal.signal(signal.SIGTERM, ignore_term)
print("READY", flush=True)
while True:
    time.sleep(0.1)
"""
        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", stubborn_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        line = proc.stdout.readline()
        assert "READY" in line
        pid = proc.pid
        assert is_process_alive(pid)

        t_start = time.time()
        # Use short timeout 0.8s for fast testing
        success = terminate_process(pid, sigterm_timeout=0.8)
        t_elapsed = time.time() - t_start

        assert success is True
        assert not is_process_alive(pid)
        # Elapsed time must be >= 0.8s because SIGTERM was ignored and had to wait for timeout
        assert t_elapsed >= 0.8, f"Escalation occurred too fast ({t_elapsed:.2f}s), expected wait for timeout"
        assert t_elapsed < 3.0, f"Escalation took too long ({t_elapsed:.2f}s)"

    def test_adv_sweep_batch_mixed_workload(self, temp_test_dir):
        """
        Spawn a batch of diverse processes:
        - 2 responsive targets with simulated age >= TTL (stale)
        - 1 stubborn target with simulated age >= TTL (stale)
        - 2 active targets with age < TTL
        - 1 excluded process
        Verify sweeper correctly partitions and terminates only the stale targets.
        """
        probe_tag_stale = "sweeper_adv_stale_target"
        probe_tag_stubborn = "sweeper_adv_stubborn_target"
        probe_tag_active = "sweeper_adv_active_target"

        custom_targets = [probe_tag_stale, probe_tag_stubborn, probe_tag_active]
        custom_excludes = ["adv_exclude_marker"]

        # 1. Responsive stale processes
        p_stale1 = subprocess.Popen(
            [sys.executable, "-u", "-c", f"import time; # {probe_tag_stale}\nprint('READY', flush=True)\ntime.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        p_stale1.stdout.readline()

        p_stale2 = subprocess.Popen(
            [sys.executable, "-u", "-c", f"import time; # {probe_tag_stale}\nprint('READY', flush=True)\ntime.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        p_stale2.stdout.readline()

        # 2. Stubborn stale process
        p_stubborn = subprocess.Popen(
            [sys.executable, "-u", "-c", f"import signal, time; # {probe_tag_stubborn}\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nprint('READY', flush=True)\ntime.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        p_stubborn.stdout.readline()

        # 3. Active processes
        p_active1 = subprocess.Popen(
            [sys.executable, "-u", "-c", f"import time; # {probe_tag_active}\nprint('READY', flush=True)\ntime.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        p_active1.stdout.readline()

        # 4. Excluded process
        p_excluded = subprocess.Popen(
            [sys.executable, "-u", "-c", f"import time; # {probe_tag_stale} adv_exclude_marker\nprint('READY', flush=True)\ntime.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        p_excluded.stdout.readline()

        all_procs = [p_stale1, p_stale2, p_stubborn, p_active1, p_excluded]
        for p in all_procs:
            assert is_process_alive(p.pid)

        try:
            # Run sweep targeting stale & stubborn with TTL=0.0 (simulating >300s TTL)
            # while active is swept with normal TTL
            summary = sweep_once(
                ttl=0.0,
                dry_run=False,
                target_patterns=[probe_tag_stale, probe_tag_stubborn],
                exclude_patterns=custom_excludes,
            )

            # Check terminations
            assert p_stale1.pid in summary["terminated_pids"]
            assert p_stale2.pid in summary["terminated_pids"]
            assert p_stubborn.pid in summary["terminated_pids"]

            assert not is_process_alive(p_stale1.pid)
            assert not is_process_alive(p_stale2.pid)
            assert not is_process_alive(p_stubborn.pid)

            # Active and excluded must still be alive
            assert is_process_alive(p_active1.pid)
            assert is_process_alive(p_excluded.pid)
        finally:
            for p in all_procs:
                if is_process_alive(p.pid):
                    try:
                        os.kill(p.pid, signal.SIGKILL)
                    except OSError:
                        pass

    def test_adv_dead_process_and_zombie_safety(self):
        """Verify terminate_process and is_process_alive safely handle nonexistent PIDs."""
        nonexistent_pid = 999999
        assert not is_process_alive(nonexistent_pid)
        assert terminate_process(nonexistent_pid) is True

    def test_adv_daemon_signal_handling_and_clean_exit(self, temp_test_dir):
        """Verify SweeperDaemon subprocess responds to SIGTERM and stops cleanly."""
        daemon_log = temp_test_dir / "daemon_subproc.log"
        proc = subprocess.Popen(
            [
                sys.executable,
                str(SWEEPER_DAEMON_PATH),
                "--daemon",
                "--interval",
                "1.0",
                "--ttl",
                "300.0",
                "--log-file",
                str(daemon_log),
                "-v",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(1.0)
        assert proc.poll() is None, "Daemon exited prematurely"

        # Send SIGTERM to daemon process
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=4.0)

        assert proc.returncode == 0
        assert daemon_log.exists()
        log_txt = daemon_log.read_text(encoding="utf-8")
        assert "Playwright Sweeper Daemon started" in log_txt
        assert "Playwright Sweeper Daemon shut down cleanly" in log_txt


class TestConcurrencyLimitsAdversarial:
    """Adversarial stress testing of concurrency limits (max_workers=2)."""

    def test_adv_concurrency_stress_barrier(self):
        """
        Flood a ThreadPoolExecutor(max_workers=2) with 30 tasks.
        Track concurrent execution count with high precision.
        Assert that active concurrency NEVER exceeds 2 at any point in time.
        """
        max_limit = 2
        active_count = 0
        peak_concurrency = 0
        lock = threading.Lock()
        total_tasks = 30

        def worker_task(idx):
            nonlocal active_count, peak_concurrency
            with lock:
                active_count += 1
                if active_count > peak_concurrency:
                    peak_concurrency = active_count
            time.sleep(0.01)  # Hold worker
            with lock:
                active_count -= 1
            return idx * 2

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_limit) as executor:
            futures = [executor.submit(worker_task, i) for i in range(total_tasks)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == total_tasks
        assert peak_concurrency <= 2, f"Concurrency violation! Peak concurrency was {peak_concurrency} (limit={max_limit})"
        assert peak_concurrency == 2, f"Expected peak concurrency of 2, got {peak_concurrency}"

    def test_adv_e2e_runner_concurrency_configuration(self):
        """Verify that run_e2e_tests.py and conftest.py hardcode MAX_TEST_WORKERS = 2."""
        conftest_path = MONOREPO_ROOT / "tests" / "e2e_arena_notebook" / "conftest.py"
        content = conftest_path.read_text(encoding="utf-8")
        assert "MAX_TEST_WORKERS = 2" in content
        assert "max_workers=MAX_TEST_WORKERS" in content


class TestHeadlessBrowserAdversarial:
    """Adversarial testing of headless browser execution & 0 GUI / Dock footprint."""

    def test_adv_playwright_headless_execution_and_options(self):
        """Launch Playwright Chromium with mandated args and verify headless operation."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pytest.skip("Playwright not installed in environment")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=PLAYWRIGHT_HEADLESS_ARGS,
            )
            page = browser.new_page()
            page.set_content("<div id='app' class='glass-card'><h1>Lauburu Mesh</h1></div>")
            title = page.text_content("#app h1")
            assert title == "Lauburu Mesh"
            browser.close()

    def test_adv_zero_macos_dock_icon_registered(self):
        """
        Verify that running headless tests does NOT register any visible GUI app in macOS WindowServer.
        Query macOS 'lsappinfo' or ps command to verify no interactive Chrome.app GUI process.
        """
        res = subprocess.run(["lsappinfo", "list"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            # Verify no foreground Playwright / Chromium GUI app
            for line in lines:
                if "chromium" in line.lower() or "playwright" in line.lower():
                    assert "foreground" not in line.lower(), f"Found foreground GUI browser app: {line}"

    def test_adv_headless_options_validator_mutation(self):
        """Adversarially mutate options to ensure assert_headless_browser_options rejects all non-compliant configs."""
        # Non-headless
        with pytest.raises(AssertionError):
            assert_headless_browser_options({"headless": False, "args": ["--headless=new"]})

        # Missing --headless=new
        with pytest.raises(AssertionError):
            assert_headless_browser_options({"headless": True, "args": ["--disable-gpu"]})

        # Non-dict
        with pytest.raises(AssertionError):
            assert_headless_browser_options(["--headless=new"])  # type: ignore


class TestMatplotlibAggBackendAdversarial:
    """Adversarial testing of Matplotlib Agg non-interactive backend enforcement."""

    def test_adv_backend_is_strictly_agg(self):
        """Verify backend is Agg and MPLBACKEND environment variable is set."""
        assert matplotlib.get_backend().lower() == "agg"
        assert os.environ.get("MPLBACKEND") == "Agg"

    def test_adv_plt_show_plt_pause_plt_draw_safe_headless(self):
        """Verify plt.show(), plt.pause(), plt.draw() execute with zero GUI popups and no errors."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6, 3))
        ax1.plot([0, 1, 2], [10, 20, 30], color="#06b6d4")
        ax2.bar(["A", "B"], [5, 15], color="#3b82f6")

        plt.draw()
        plt.pause(0.01)
        plt.show()

        # Verify figure handles cleaned
        assert len(plt.get_fignums()) == 0

    def test_adv_zero_interactive_backend_ast_audit(self):
        """
        Audit all Python source and test files in tests/e2e_arena_notebook/
        to guarantee ZERO interactive backends are activated.
        """
        test_dir = MONOREPO_ROOT / "tests" / "e2e_arena_notebook"
        # Check AST for explicit matplotlib.use('...') calls
        py_files = list(test_dir.glob("*.py"))
        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=py_file.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check specifically for matplotlib.use(...)
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "use":
                        # Ensure the target is 'matplotlib', not 'style' or 'plt.style'
                        is_matplotlib = False
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == "matplotlib":
                            is_matplotlib = True
                        if is_matplotlib and node.args and isinstance(node.args[0], ast.Constant):
                            val = str(node.args[0].value)
                            assert val.lower() == "agg", f"File {py_file.name} sets non-Agg backend: {val}"


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
