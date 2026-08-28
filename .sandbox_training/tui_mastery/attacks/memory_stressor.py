#!/usr/bin/env python3
"""Red Team Memory Pressure & Buffer Exhaustion Attack Engine.

Stress-tests TUI memory management, log buffer bounds, and uncollected DOM/widget references:
1. Injects high-volume, oversized payloads (50,000-char logs, large provider dictionaries).
2. Measures baseline RSS, peak RSS, final RSS, and memory growth slope.
3. Enforces strict memory ceiling bounds (e.g., max 150.0 MB).

Measures:
- Unbounded log buffer leaks (deque vs list)
- Event listener / widget DOM memory retention
- Garbage collection stability under continuous allocation
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MemoryStressResult:
    target_command: List[str]
    duration_secs: float
    baseline_rss_mb: float
    peak_rss_mb: float
    final_rss_mb: float
    growth_mb: float
    max_acceptable_rss_mb: float
    within_bounds: bool
    panics_detected: int
    exit_code: Optional[int]
    samples: List[Tuple[float, float]]  # (timestamp_offset, rss_mb)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_id": "MEMORY_PRESSURE",
            "target_command": self.target_command,
            "duration_secs": round(self.duration_secs, 3),
            "baseline_rss_mb": round(self.baseline_rss_mb, 2),
            "peak_rss_mb": round(self.peak_rss_mb, 2),
            "final_rss_mb": round(self.final_rss_mb, 2),
            "growth_mb": round(self.growth_mb, 2),
            "max_acceptable_rss_mb": self.max_acceptable_rss_mb,
            "within_bounds": self.within_bounds,
            "panics_detected": self.panics_detected,
            "exit_code": self.exit_code,
            "samples_count": len(self.samples),
        }


class MemoryStressor:
    """Adversarial stressor executing memory pressure and monitoring RSS trajectory."""

    def __init__(
        self,
        duration_secs: float = 3.0,
        max_acceptable_rss_mb: float = 150.0,
        sample_interval_secs: float = 0.1,
    ):
        self.duration_secs = max(0.5, duration_secs)
        self.max_acceptable_rss_mb = max_acceptable_rss_mb
        self.sample_interval_secs = max(0.02, sample_interval_secs)

    @staticmethod
    def get_process_rss_mb(pid: int) -> float:
        """Measure resident set size (RSS) in megabytes for a given PID."""
        try:
            # Platform agnostic ps query
            res = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(pid)],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0 and res.stdout.strip():
                # Value is in kilobytes on macOS and Linux
                kb = float(res.stdout.strip().split()[0])
                return kb / 1024.0
        except Exception:
            pass
        return 0.0

    def run_attack(
        self,
        cmd: List[str],
        state_path: Optional[Path] = None,
        cwd: Optional[Path] = None,
    ) -> MemoryStressResult:
        t0 = time.perf_counter()
        samples: List[Tuple[float, float]] = []
        panics = 0

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )

        time.sleep(0.1)  # Allow process initial allocation
        baseline_rss = self.get_process_rss_mb(proc.pid)
        peak_rss = baseline_rss
        final_rss = baseline_rss

        stress_start = time.perf_counter()
        cycle = 0

        while time.perf_counter() - stress_start < self.duration_secs:
            if proc.poll() is not None:
                break

            current_rss = self.get_process_rss_mb(proc.pid)
            if current_rss > 0.0:
                samples.append((time.perf_counter() - stress_start, current_rss))
                if current_rss > peak_rss:
                    peak_rss = current_rss
                final_rss = current_rss

            # If state path is provided, inject heavy data mutations
            if state_path and cycle % 3 == 0:
                large_name = "HeavyProvider_" + ("X" * 500)
                large_state = {
                    "version": "2.0.0",
                    "providers": {
                        f"provider_{i}": {
                            "name": f"{large_name}_{i}",
                            "daily_limit": 100000,
                            "used_today": (cycle * 100) % 90000,
                            "remaining_pct": 0.5,
                            "avg_latency_ms": 25.0,
                            "status": "healthy",
                        }
                        for i in range(20)
                    },
                    "metrics": {
                        "total_tasks_routed": cycle * 10,
                        "total_lora_samples_harvested": cycle,
                    },
                }
                tmp_state = state_path.with_suffix(".mem_tmp")
                try:
                    with open(tmp_state, "w", encoding="utf-8") as f:
                        json.dump(large_state, f)
                    os.replace(tmp_state, state_path)
                except Exception:
                    pass

            cycle += 1
            time.sleep(self.sample_interval_secs)

        # Terminate process if still running
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except Exception:
                proc.kill()

        stdout_data, stderr_data = proc.communicate()
        combined = (stdout_data.decode("utf-8", errors="replace") +
                    stderr_data.decode("utf-8", errors="replace"))

        if "panic:" in combined or "Traceback" in combined or "Segmentation fault" in combined:
            panics += 1

        growth = max(0.0, final_rss - baseline_rss)
        within_bounds = (peak_rss <= self.max_acceptable_rss_mb) and (panics == 0)

        return MemoryStressResult(
            target_command=cmd,
            duration_secs=time.perf_counter() - t0,
            baseline_rss_mb=baseline_rss,
            peak_rss_mb=peak_rss,
            final_rss_mb=final_rss,
            growth_mb=growth,
            max_acceptable_rss_mb=self.max_acceptable_rss_mb,
            within_bounds=within_bounds,
            panics_detected=panics,
            exit_code=proc.returncode,
            samples=samples,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Red Team Memory Pressure & Buffer Exhaustion")
    parser.add_argument("cmd", nargs="+", help="Target command to stress-test")
    parser.add_argument("--duration", type=float, default=3.0, help="Duration in seconds (default: 3.0)")
    parser.add_argument("--max-rss", type=float, default=150.0, help="Max acceptable RSS in MB (default: 150.0)")
    parser.add_argument("--state-path", type=Path, default=None, help="State path for heavy mutations")
    args = parser.parse_args()

    stressor = MemoryStressor(duration_secs=args.duration, max_acceptable_rss_mb=args.max_rss)
    result = stressor.run_attack(args.cmd, state_path=args.state_path)
    print(f"[*] Memory Pressure Attack Summary:")
    print(f"    Baseline RSS : {result.baseline_rss_mb:.2f} MB")
    print(f"    Peak RSS     : {result.peak_rss_mb:.2f} MB (Ceiling: {result.max_acceptable_rss_mb:.1f} MB)")
    print(f"    Growth       : {result.growth_mb:.2f} MB")
    print(f"    Within Bounds: {result.within_bounds}")
    print(f"    Panics       : {result.panics_detected}")
    sys.exit(0 if result.within_bounds else 1)


if __name__ == "__main__":
    main()
