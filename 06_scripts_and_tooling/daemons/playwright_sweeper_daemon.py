#!/usr/bin/env python3
"""
Playwright & Chrome Sweeper Daemon
==================================
Monitors, tracks, and cleans up stale/dangling Playwright and Chrome/Chromium processes
exceeding the 5-minute (300s) TTL threshold across the Lauburu ecosystem.

Mandates:
1. 300-second (5 min) TTL threshold for target processes.
2. Two-stage termination: SIGTERM -> wait 3s -> SIGKILL.
3. Leaves short-lived/active test processes (< 300s TTL) untouched.
4. Logging to /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/daemons/sweeper.log.
5. Background-safe execution with zero Dock / GUI interaction.
"""

import argparse
import dataclasses
import logging
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Try importing psutil for high-accuracy process inspection; provide standard ps fallback
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore
    HAS_PSUTIL = False

DEFAULT_LOG_PATH = Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/daemons/sweeper.log")
DEFAULT_TTL_SECONDS = 300.0  # 5 minutes
DEFAULT_INTERVAL_SECONDS = 30.0
DEFAULT_SIGTERM_TIMEOUT = 3.0

TARGET_PATTERNS = [
    "playwright",
    "ms-playwright",
    "chromium",
    "Google Chrome",
    "google-chrome",
    "chromedriver",
    "chrome",
]

# Patterns that should NOT be terminated (system daemons, remote desktop, editors, this script)
EXCLUDE_PATTERNS = [
    "playwright_sweeper_daemon.py",
    "sweeper_daemon",
    "antigravity",
    "code",
    "cursor",
    "launchd",
    "zsh",
    "bash",
    "remoting",
    "chromeremotedesktop",
    "chrome-remote-desktop",
    "remoting_me2me_host",
]


@dataclasses.dataclass
class ProcessInfo:
    pid: int
    name: str
    cmdline: str
    age_seconds: float
    create_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cmdline": self.cmdline,
            "age_seconds": round(self.age_seconds, 2),
            "create_time": self.create_time,
        }


def parse_etime(etime_str: str) -> float:
    """
    Parse POSIX/macOS ps 'etime' or 'elapsed' string into seconds.
    Supported formats:
      - mm:ss
      - hh:mm:ss
      - dd-hh:mm:ss
      - dd-h:mm:ss
    """
    etime_str = etime_str.strip()
    if not etime_str:
        return 0.0

    days = 0.0
    if "-" in etime_str:
        day_part, time_part = etime_str.split("-", 1)
        try:
            days = float(day_part)
        except ValueError:
            days = 0.0
    else:
        time_part = etime_str

    parts = time_part.split(":")
    try:
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
        elif len(parts) == 2:
            hours = 0.0
            minutes = float(parts[0])
            seconds = float(parts[1])
        elif len(parts) == 1:
            hours = 0.0
            minutes = 0.0
            seconds = float(parts[0])
        else:
            return 0.0
    except ValueError:
        return 0.0

    return days * 86400.0 + hours * 3600.0 + minutes * 60.0 + seconds


def is_target_process(
    name: str,
    cmdline: str,
    pid: int,
    target_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> bool:
    """
    Determine if a process matches the target Playwright / Chrome process criteria.
    Excludes the current running process and non-target binaries.
    """
    if pid == os.getpid():
        return False

    targets = target_patterns or TARGET_PATTERNS
    excludes = exclude_patterns or EXCLUDE_PATTERNS

    combined = f"{name} {cmdline}".lower()

    # Check exclusions first
    for exc in excludes:
        if exc.lower() in combined:
            return False

    # Check targets
    for target in targets:
        target_lower = target.lower()
        # Word boundary or exact substring check
        if target_lower in combined:
            return True

    return False


def scan_processes_psutil(
    target_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[ProcessInfo]:
    """Scan running processes using psutil."""
    if not HAS_PSUTIL or psutil is None:
        return []

    now = time.time()
    results: List[ProcessInfo] = []

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            info = proc.info
            pid = info.get("pid")
            if pid is None or pid <= 1:
                continue

            name = info.get("name") or ""
            raw_cmdline = info.get("cmdline") or []
            cmdline = " ".join(raw_cmdline) if isinstance(raw_cmdline, list) else str(raw_cmdline)

            if not is_target_process(name, cmdline, pid, target_patterns, exclude_patterns):
                continue

            create_time = info.get("create_time") or now
            age = max(0.0, now - create_time)

            results.append(
                ProcessInfo(
                    pid=pid,
                    name=name,
                    cmdline=cmdline,
                    age_seconds=age,
                    create_time=create_time,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return results


def scan_processes_ps(
    target_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[ProcessInfo]:
    """Scan running processes using POSIX/macOS `ps -eo pid,etime,command` fallback."""
    now = time.time()
    results: List[ProcessInfo] = []

    try:
        output = subprocess.check_output(
            ["ps", "-eo", "pid,etime,command"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        return []

    lines = output.strip().split("\n")
    if not lines:
        return []

    for line in lines[1:]:  # Skip header
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 3:
            continue

        try:
            pid = int(parts[0])
            if pid <= 1:
                continue
            etime_str = parts[1]
            cmdline = parts[2]
            name = Path(cmdline.split()[0]).name if cmdline else ""
        except (ValueError, IndexError):
            continue

        if not is_target_process(name, cmdline, pid, target_patterns, exclude_patterns):
            continue

        age = parse_etime(etime_str)
        create_time = now - age

        results.append(
            ProcessInfo(
                pid=pid,
                name=name,
                cmdline=cmdline,
                age_seconds=age,
                create_time=create_time,
            )
        )

    return results


def scan_processes(
    target_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    prefer_psutil: bool = True,
) -> List[ProcessInfo]:
    """Scan running target processes using psutil if available, otherwise ps."""
    if prefer_psutil and HAS_PSUTIL:
        try:
            return scan_processes_psutil(target_patterns, exclude_patterns)
        except Exception:
            pass
    return scan_processes_ps(target_patterns, exclude_patterns)


def is_process_alive(pid: int) -> bool:
    """
    Check if a process is actively running (not dead or zombie).
    Handles child reaping and psutil zombie status checks.
    """
    if pid <= 0:
        return False

    # Attempt non-blocking reap if process is a child of current process
    try:
        wpid, _ = os.waitpid(pid, os.WNOHANG)
        if wpid == pid:
            return False
    except (ChildProcessError, OSError):
        pass

    # Check via psutil if available
    if HAS_PSUTIL and psutil is not None:
        try:
            p = psutil.Process(pid)
            if p.status() in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
                return False
            return p.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    # POSIX signal 0 fallback
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def terminate_process(
    pid: int,
    sigterm_timeout: float = DEFAULT_SIGTERM_TIMEOUT,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    Two-stage process termination:
    1. Send SIGTERM.
    2. Wait up to `sigterm_timeout` seconds.
    3. If still running, send SIGKILL.
    """
    if not is_process_alive(pid):
        return True

    log = logger or logging.getLogger("PlaywrightSweeper")

    # Stage 1: Send SIGTERM
    try:
        os.kill(pid, signal.SIGTERM)
        log.info(f"Sent SIGTERM to PID {pid}")
    except ProcessLookupError:
        return True
    except PermissionError as e:
        log.error(f"Permission denied sending SIGTERM to PID {pid}: {e}")
        return False

    # Wait for graceful exit
    deadline = time.time() + sigterm_timeout
    while time.time() < deadline:
        if not is_process_alive(pid):
            log.info(f"PID {pid} terminated gracefully after SIGTERM")
            return True
        time.sleep(0.1)

    # Stage 2: Send SIGKILL if still alive
    if is_process_alive(pid):
        try:
            log.warning(f"PID {pid} did not terminate after {sigterm_timeout}s. Escalating to SIGKILL.")
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.2)
            if not is_process_alive(pid):
                log.info(f"PID {pid} successfully killed via SIGKILL")
                return True
            else:
                log.error(f"PID {pid} still alive after SIGKILL")
                return False
        except ProcessLookupError:
            return True
        except PermissionError as e:
            log.error(f"Permission denied sending SIGKILL to PID {pid}: {e}")
            return False

    return True


def setup_logger(log_file: Path, verbose: bool = False) -> logging.Logger:
    """Configure logger with file handler and optional console handler."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("PlaywrightSweeper")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Prevent duplicate handlers
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if verbose or not logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    return logger


def sweep_once(
    ttl: float = DEFAULT_TTL_SECONDS,
    dry_run: bool = False,
    logger: Optional[logging.Logger] = None,
    target_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    prefer_psutil: bool = True,
) -> Dict[str, Any]:
    """
    Execute a single sweep pass:
    - Scans for matching target processes.
    - Identifies stale processes (age >= ttl).
    - Identifies young processes (age < ttl).
    - Terminates stale processes (unless dry_run=True).
    - Returns summary statistics.
    """
    log = logger or logging.getLogger("PlaywrightSweeper")
    targets = scan_processes(
        target_patterns=target_patterns,
        exclude_patterns=exclude_patterns,
        prefer_psutil=prefer_psutil,
    )

    stale: List[ProcessInfo] = []
    active: List[ProcessInfo] = []

    for proc in targets:
        if proc.age_seconds >= ttl:
            stale.append(proc)
        else:
            active.append(proc)

    terminated_pids: List[int] = []
    failed_pids: List[int] = []

    for proc in stale:
        log.warning(
            f"Stale process detected: PID={proc.pid}, Name='{proc.name}', "
            f"Age={proc.age_seconds:.1f}s (TTL={ttl:.1f}s), Cmd='{proc.cmdline[:120]}'"
        )
        if dry_run:
            log.info(f"[DRY-RUN] Would terminate PID {proc.pid}")
            terminated_pids.append(proc.pid)
        else:
            success = terminate_process(proc.pid, logger=log)
            if success:
                terminated_pids.append(proc.pid)
            else:
                failed_pids.append(proc.pid)

    for proc in active:
        log.debug(
            f"Active process kept alive: PID={proc.pid}, Name='{proc.name}', "
            f"Age={proc.age_seconds:.1f}s < TTL={ttl:.1f}s"
        )

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ttl_seconds": ttl,
        "dry_run": dry_run,
        "total_targets_found": len(targets),
        "stale_count": len(stale),
        "active_count": len(active),
        "terminated_pids": terminated_pids,
        "failed_pids": failed_pids,
        "stale_details": [p.to_dict() for p in stale],
        "active_details": [p.to_dict() for p in active],
    }

    log.info(
        f"Sweep completed: {len(targets)} targets evaluated | "
        f"{len(stale)} stale (terminated: {len(terminated_pids)}) | "
        f"{len(active)} active (< {ttl}s kept alive)"
    )

    return summary


class SweeperDaemon:
    """Continuous background daemon loop for Playwright/Chrome sweeping."""

    def __init__(
        self,
        interval: float = DEFAULT_INTERVAL_SECONDS,
        ttl: float = DEFAULT_TTL_SECONDS,
        log_file: Path = DEFAULT_LOG_PATH,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.interval = interval
        self.ttl = ttl
        self.log_file = log_file
        self.dry_run = dry_run
        self.verbose = verbose
        self.running = False
        self.logger = setup_logger(self.log_file, self.verbose)

    def _handle_signal(self, signum, frame):
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received signal {sig_name}. Stopping sweeper daemon...")
        self.running = False

    def run(self):
        """Run the daemon loop until interrupted."""
        self.running = True
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self.logger.info(
            f"Playwright Sweeper Daemon started. Interval={self.interval}s, "
            f"TTL={self.ttl}s, Log={self.log_file}, DryRun={self.dry_run}"
        )

        try:
            while self.running:
                sweep_once(
                    ttl=self.ttl,
                    dry_run=self.dry_run,
                    logger=self.logger,
                )
                # Sleep in increments for responsive interrupt handling
                sleep_start = time.time()
                while self.running and (time.time() - sleep_start) < self.interval:
                    time.sleep(0.5)
        except Exception as e:
            self.logger.exception(f"Unexpected error in sweeper daemon loop: {e}")
        finally:
            self.logger.info("Playwright Sweeper Daemon shut down cleanly.")


def print_status(ttl: float = DEFAULT_TTL_SECONDS):
    """Print current active target processes to stdout."""
    targets = scan_processes()
    print("=" * 80)
    print("  PLAYWRIGHT & CHROME PROCESS STATUS")
    print("=" * 80)
    if not targets:
        print("  No active Playwright or Chrome processes found.")
    else:
        print(f"  Found {len(targets)} matching processes:")
        print(f"  {'PID':<8} {'AGE (s)':<10} {'STATUS':<12} {'NAME':<20} {'COMMAND'}")
        print("  " + "-" * 76)
        for p in targets:
            status = "🔴 STALE" if p.age_seconds >= ttl else "🟢 ACTIVE"
            cmd_preview = (p.cmdline[:45] + "...") if len(p.cmdline) > 45 else p.cmdline
            print(f"  {p.pid:<8} {p.age_seconds:<10.1f} {status:<12} {p.name[:18]:<20} {cmd_preview}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Playwright and Chrome Process Sweeper Daemon (5-minute TTL Enforcement)"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in background daemon loop",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Sweep interval in seconds for daemon mode (default: {DEFAULT_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--ttl",
        type=float,
        default=DEFAULT_TTL_SECONDS,
        help=f"TTL threshold in seconds for terminating stale processes (default: {DEFAULT_TTL_SECONDS})",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help=f"Path to log file (default: {DEFAULT_LOG_PATH})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single sweep cycle and exit (default if --daemon is omitted)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform sweep and identify stale processes without terminating them",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display current running target processes and exit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output to stdout",
    )

    args = parser.parse_args()

    if args.status:
        print_status(ttl=args.ttl)
        sys.exit(0)

    logger = setup_logger(args.log_file, verbose=args.verbose)

    if args.daemon:
        daemon = SweeperDaemon(
            interval=args.interval,
            ttl=args.ttl,
            log_file=args.log_file,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        daemon.run()
    else:
        # Default: single sweep pass
        result = sweep_once(
            ttl=args.ttl,
            dry_run=args.dry_run,
            logger=logger,
        )
        if args.verbose or not args.daemon:
            print(
                f"[Playwright Sweeper] Evaluated {result['total_targets_found']} targets | "
                f"{result['stale_count']} stale | {result['active_count']} active. "
                f"Log: {args.log_file}"
            )


if __name__ == "__main__":
    main()
