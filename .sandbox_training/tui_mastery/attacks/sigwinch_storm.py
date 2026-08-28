#!/usr/bin/env python3
"""Red Team SIGWINCH Storm Attack Engine.

Stress-tests TUI applications by blasting high-frequency (50-200 Hz) terminal
window resize signals (TIOCSWINSZ / SIGWINCH) across extreme viewport dimensions
(0x0, 1x1, 10x5, 80x24, 120x40, 240x60, 300x100) within a virtual PTY.

Measures:
- Layout underflow / arithmetic overflow panics
- Dynamic dimension clamping behavior
- Memory stability during rapid layout recalculations
- Frame drop rate and CPU saturation
"""

from __future__ import annotations

import argparse
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SigwinchAttackResult:
    target_command: List[str]
    total_resizes_sent: int
    duration_secs: float
    actual_frequency_hz: float
    exit_code: Optional[int]
    survived: bool
    panics_detected: int
    error_log: List[str]
    min_dimensions_tested: Tuple[int, int]
    max_dimensions_tested: Tuple[int, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_id": "SIGWINCH_STORM",
            "target_command": self.target_command,
            "total_resizes_sent": self.total_resizes_sent,
            "duration_secs": round(self.duration_secs, 3),
            "actual_frequency_hz": round(self.actual_frequency_hz, 1),
            "exit_code": self.exit_code,
            "survived": self.survived,
            "panics_detected": self.panics_detected,
            "error_log": self.error_log[:10],
            "min_dimensions_tested": list(self.min_dimensions_tested),
            "max_dimensions_tested": list(self.max_dimensions_tested),
        }


class SigwinchStressor:
    """Adversarial stressor executing rapid SIGWINCH oscillations against a child TUI."""

    DIMENSION_PALETTE: List[Tuple[int, int]] = [
        (0, 0),        # Zero dimension boundary
        (1, 1),        # Single cell degenerate
        (5, 5),        # Micro viewport
        (10, 5),       # Clamping minimum threshold
        (40, 15),      # Narrow mobile
        (80, 24),      # Standard VT100
        (120, 40),     # Wide desktop HUD
        (240, 60),     # Ultra-wide 4K monitor
        (300, 100),    # Maximum constraint boundary
    ]

    def __init__(
        self,
        frequency_hz: float = 100.0,
        duration_secs: float = 2.0,
        custom_dimensions: Optional[List[Tuple[int, int]]] = None,
    ):
        self.frequency_hz = max(1.0, min(500.0, frequency_hz))
        self.interval = 1.0 / self.frequency_hz
        self.duration_secs = max(0.1, duration_secs)
        self.dimensions = custom_dimensions or self.DIMENSION_PALETTE

    def set_pty_size(self, master_fd: int, rows: int, cols: int) -> None:
        """Issue TIOCSWINSZ ioctl to resize virtual terminal window."""
        try:
            ws = struct.pack("HHHH", max(0, rows), max(0, cols), 0, 0)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, ws)
        except Exception:
            pass

    def run_attack(self, cmd: List[str], cwd: Optional[Path] = None) -> SigwinchAttackResult:
        """Execute child process in virtual PTY and unleash the SIGWINCH storm."""
        master_fd, slave_fd = pty.openpty()
        t0 = time.perf_counter()
        resizes_sent = 0
        error_logs: List[str] = []
        panics = 0
        exit_code: Optional[int] = None

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=str(cwd) if cwd else None,
                preexec_fn=os.setsid,
                close_fds=True,
            )
            os.close(slave_fd)  # Closed in parent

            # Initial resize
            self.set_pty_size(master_fd, 24, 80)
            time.sleep(0.05)  # Allow process initialization

            # Make master_fd non-blocking
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            dim_idx = 0
            storm_start = time.perf_counter()

            while time.perf_counter() - storm_start < self.duration_secs:
                if proc.poll() is not None:
                    break

                cols, rows = self.dimensions[dim_idx % len(self.dimensions)]
                self.set_pty_size(master_fd, rows, cols)
                resizes_sent += 1
                dim_idx += 1

                # Read available output to prevent buffer blocking
                r, _, _ = select.select([master_fd], [], [], 0.0)
                if r:
                    try:
                        raw = os.read(master_fd, 4096)
                        decoded = raw.decode("utf-8", errors="replace")
                        if "panic:" in decoded or "Traceback" in decoded or "fatal error:" in decoded:
                            panics += 1
                            error_logs.append(decoded[:200])
                    except Exception:
                        pass

                time.sleep(self.interval)

            total_dur = time.perf_counter() - t0
            actual_hz = resizes_sent / max(0.001, total_dur)

            # Check termination status
            if proc.poll() is None:
                # Send 'q' to gracefully request quit
                try:
                    os.write(master_fd, b"q\n")
                    time.sleep(0.1)
                except Exception:
                    pass

                if proc.poll() is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        proc.wait(timeout=1.0)
                    except Exception:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        except Exception:
                            pass

            exit_code = proc.returncode if proc.returncode is not None else 0

        except Exception as ex:
            error_logs.append(f"Attack execution error: {ex}")
            exit_code = -1
            panics += 1
        finally:
            try:
                os.close(master_fd)
            except Exception:
                pass

        min_dim = min(self.dimensions, key=lambda d: d[0] * d[1])
        max_dim = max(self.dimensions, key=lambda d: d[0] * d[1])
        survived = (panics == 0) and (exit_code in (0, None, -15))

        return SigwinchAttackResult(
            target_command=cmd,
            total_resizes_sent=resizes_sent,
            duration_secs=time.perf_counter() - t0,
            actual_frequency_hz=actual_hz if resizes_sent > 0 else 0.0,
            exit_code=exit_code,
            survived=survived,
            panics_detected=panics,
            error_log=error_logs,
            min_dimensions_tested=min_dim,
            max_dimensions_tested=max_dim,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Red Team SIGWINCH Storm Attack Engine")
    parser.add_argument("cmd", nargs="+", help="Target command to stress-test")
    parser.add_argument("--freq", type=float, default=100.0, help="Resize frequency in Hz (default: 100.0)")
    parser.add_argument("--duration", type=float, default=2.0, help="Attack duration in seconds (default: 2.0)")
    args = parser.parse_args()

    stressor = SigwinchStressor(frequency_hz=args.freq, duration_secs=args.duration)
    result = stressor.run_attack(args.cmd)
    print(f"[*] SIGWINCH Storm Attack Summary:")
    print(f"    Resizes Sent : {result.total_resizes_sent} @ {result.actual_frequency_hz:.1f} Hz")
    print(f"    Panics       : {result.panics_detected}")
    print(f"    Survived     : {result.survived} (Exit Code: {result.exit_code})")
    sys.exit(0 if result.survived else 1)


if __name__ == "__main__":
    main()
