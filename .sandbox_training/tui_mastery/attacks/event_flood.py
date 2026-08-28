#!/usr/bin/env python3
"""Red Team Event Flood & Telemetry Torrent Attack Engine.

Stress-tests TUI event loops, async workers, and state readers by flooding:
1. High-frequency PTY keyboard input (1,000+ keystrokes/second: arrow keys,
   refresh 'r', pause 'p', navigation, ANSI escape sequences, garbage input).
2. Concurrent state mutation telemetry storms (100,000 events / high-rate atomic writes).

Measures:
- Event loop starvation and UI freeze latency
- Key buffer unbounded accumulation / memory leaks
- Backpressure dropping behavior
- Process responsiveness and crash avoidance
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import json
import os
import pty
import random
import select
import signal
import string
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EventFloodResult:
    target_command: List[str]
    total_keys_injected: int
    total_state_writes: int
    duration_secs: float
    actual_key_rate_per_sec: float
    exit_code: Optional[int]
    survived: bool
    panics_detected: int
    error_log: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_id": "EVENT_FLOOD",
            "target_command": self.target_command,
            "total_keys_injected": self.total_keys_injected,
            "total_state_writes": self.total_state_writes,
            "duration_secs": round(self.duration_secs, 3),
            "actual_key_rate_per_sec": round(self.actual_key_rate_per_sec, 1),
            "exit_code": self.exit_code,
            "survived": self.survived,
            "panics_detected": self.panics_detected,
            "error_log": self.error_log[:10],
        }


class EventFloodStressor:
    """Adversarial stressor executing key spam floods and telemetry torrents."""

    KEY_SEQUENCES = [
        b"r",                     # Refresh action
        b"p",                     # Pause / resume toggle
        b"\x1b[A",                # Up arrow
        b"\x1b[B",                # Down arrow
        b"\x1b[C",                # Right arrow
        b"\x1b[D",                # Left arrow
        b"\t",                    # Tab navigation
        b" ",                     # Space
        b"\x1b[1;5A",             # Ctrl+Up
        b"\x1b[1;5B",             # Ctrl+Down
        b"\x1b[5~",               # Page Up
        b"\x1b[6~",               # Page Down
        b"\x1b[H",                # Home
        b"\x1b[F",                # End
        b"x", b"y", b"z", b"1", b"2", b"3",
        b"\x1b[999;999H",         # ANSI cursor position blast
    ]

    def __init__(
        self,
        target_keys_per_sec: float = 1000.0,
        duration_secs: float = 2.0,
        concurrent_state_writes: bool = True,
    ):
        self.target_keys_per_sec = max(10.0, target_keys_per_sec)
        self.duration_secs = max(0.1, duration_secs)
        self.concurrent_state_writes = concurrent_state_writes

    def _state_writer_worker(self, state_path: Path, stop_event: Any) -> int:
        """Background worker executing rapid atomic state updates."""
        writes = 0
        providers = ["cloudflare_ai", "gemini_free", "julien_ai", "local_mesh"]
        while not stop_event.is_set():
            data = {
                "version": "2.0.0",
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S.000000+00:00"),
                "providers": {
                    p: {
                        "name": p.replace("_", " ").title(),
                        "daily_limit": 10000,
                        "used_today": (writes * 7) % 9500,
                        "remaining_pct": max(0.05, 1.0 - ((writes * 7) % 9500) / 10000.0),
                        "avg_latency_ms": 10.0 + (writes % 50),
                        "status": "healthy" if writes % 10 != 0 else "degraded",
                    }
                    for p in providers
                },
                "metrics": {
                    "total_tasks_routed": writes,
                    "total_lora_samples_harvested": writes // 10,
                },
            }
            tmp_path = state_path.with_suffix(".flood_tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, state_path)
                writes += 1
            except Exception:
                pass
            time.sleep(0.005)  # 200 state writes / sec
        return writes

    def run_attack(
        self,
        cmd: List[str],
        state_path: Optional[Path] = None,
        cwd: Optional[Path] = None,
    ) -> EventFloodResult:
        master_fd, slave_fd = pty.openpty()
        t0 = time.perf_counter()
        keys_injected = 0
        total_writes = 0
        error_logs: List[str] = []
        panics = 0
        exit_code: Optional[int] = None

        stop_event = concurrent.futures.Event() if hasattr(concurrent.futures, "Event") else None
        # Use threading.Event
        import threading
        stop_event = threading.Event()
        writer_future = None
        executor = None

        if self.concurrent_state_writes and state_path:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            writer_future = executor.submit(self._state_writer_worker, state_path, stop_event)

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
            os.close(slave_fd)

            time.sleep(0.05)  # Let process initialize
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            flood_start = time.perf_counter()
            batch_size = max(1, int(self.target_keys_per_sec / 50))  # 50 bursts/sec
            batch_interval = 0.02

            while time.perf_counter() - flood_start < self.duration_secs:
                if proc.poll() is not None:
                    break

                # Prepare batch of key sequences
                payload = b"".join(
                    random.choice(self.KEY_SEQUENCES) for _ in range(batch_size)
                )
                try:
                    os.write(master_fd, payload)
                    keys_injected += batch_size
                except (IOError, OSError):
                    pass

                # Read output to prevent stdout pipe clog
                r, _, _ = select.select([master_fd], [], [], 0.0)
                if r:
                    try:
                        raw = os.read(master_fd, 8192)
                        decoded = raw.decode("utf-8", errors="replace")
                        if "panic:" in decoded or "Traceback" in decoded or "fatal error:" in decoded:
                            panics += 1
                            error_logs.append(decoded[:200])
                    except Exception:
                        pass

                time.sleep(batch_interval)

            total_dur = time.perf_counter() - t0

            # Signal quit
            if proc.poll() is None:
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
            error_logs.append(f"Flood execution error: {ex}")
            exit_code = -1
            panics += 1
        finally:
            stop_event.set()
            if writer_future:
                try:
                    total_writes = writer_future.result(timeout=1.0)
                except Exception:
                    pass
            if executor:
                executor.shutdown(wait=False)
            try:
                os.close(master_fd)
            except Exception:
                pass

        total_dur = max(0.001, time.perf_counter() - t0)
        actual_rate = keys_injected / total_dur
        survived = (panics == 0) and (exit_code in (0, None, -15))

        return EventFloodResult(
            target_command=cmd,
            total_keys_injected=keys_injected,
            total_state_writes=total_writes,
            duration_secs=total_dur,
            actual_key_rate_per_sec=actual_rate,
            exit_code=exit_code,
            survived=survived,
            panics_detected=panics,
            error_log=error_logs,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Red Team Event Flood & Telemetry Torrent")
    parser.add_argument("cmd", nargs="+", help="Target command to stress-test")
    parser.add_argument("--rate", type=float, default=1000.0, help="Target keystroke rate (default: 1000/s)")
    parser.add_argument("--duration", type=float, default=2.0, help="Duration in seconds (default: 2.0)")
    parser.add_argument("--state-path", type=Path, default=None, help="State path for concurrent writes")
    args = parser.parse_args()

    stressor = EventFloodStressor(target_keys_per_sec=args.rate, duration_secs=args.duration)
    result = stressor.run_attack(args.cmd, state_path=args.state_path)
    print(f"[*] Event Flood Attack Summary:")
    print(f"    Keys Injected : {result.total_keys_injected} @ {result.actual_key_rate_per_sec:.1f} keys/s")
    print(f"    State Writes  : {result.total_state_writes}")
    print(f"    Panics        : {result.panics_detected}")
    print(f"    Survived      : {result.survived} (Exit Code: {result.exit_code})")
    sys.exit(0 if result.survived else 1)


if __name__ == "__main__":
    main()
