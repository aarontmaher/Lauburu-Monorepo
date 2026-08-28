#!/usr/bin/env python3
"""Canonical Lauburu Local TUI Verification & Benchmark Harness.

Discovers, verifies, and benchmarks Python Textual, Go Bubble Tea, and Rust Ratatui TUIs
locally against the canonical cloud API quota state schema.
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_STATE_PATH = Path(
    os.getenv(
        "LAUBURU_QUOTA_STATE_PATH",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.json",
    )
)

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON_DIR = BASE_DIR / "python_textual"
GO_DIR = BASE_DIR / "go_bubbletea"
RUST_DIR = BASE_DIR / "rust_ratatui"


@dataclass
class TuiBenchmarkResult:
    framework: str
    target_path: str
    verify_passed: bool
    verify_exit_code: int
    verify_latency_ms: float
    verify_stdout: str
    verify_stderr: str
    smoke_passed: bool
    smoke_exit_code: int
    smoke_latency_ms: float
    memory_rss_mb: float
    schema_valid: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None


class LocalTuiVerifier:
    """Orchestrates local discovery, compilation, execution, and benchmarking of TUIs."""

    def __init__(
        self,
        state_path: Path = DEFAULT_STATE_PATH,
        timeout: float = 2.0,
        poll_interval: float = 2.0,
        auto_build: bool = True,
        verbose: bool = False,
    ):
        self.state_path = state_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.auto_build = auto_build
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[verify_local] {msg}", file=sys.stderr)

    def validate_state_file(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Verify the state file exists and is valid JSON."""
        if not self.state_path.exists():
            return False, None, f"State file not found at {self.state_path}"
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return False, None, "Root JSON must be an object"
            for k in ("version", "providers", "metrics"):
                if k not in data:
                    return False, None, f"Missing required root key: '{k}'"
            return True, data, None
        except Exception as e:
            return False, None, f"Failed to parse state file: {e}"

    def build_go_binary(self) -> Optional[Path]:
        """Discover or build Go binary."""
        bin_dir = GO_DIR / "bin"
        canonical_bin = GO_DIR / "canonical_tui_go"
        tui_bin = bin_dir / "tui_go"
        build_bin = BASE_DIR / "build" / "canonical_tui_go"

        for b in (canonical_bin, tui_bin, build_bin):
            if b.exists() and os.access(b, os.X_OK):
                return b

        main_go = GO_DIR / "main.go"
        if not main_go.exists():
            self._log(f"Go source not found at {main_go}")
            return None

        bin_dir.mkdir(parents=True, exist_ok=True)
        out_bin = bin_dir / "tui_go"

        go_bin = shutil.which("go")
        if not go_bin:
            self._log("Go compiler 'go' not found in PATH")
            return None

        try:
            self._log(f"Building Go binary: go build -o {out_bin} .")
            res = subprocess.run(
                [go_bin, "build", "-o", str(out_bin), "."],
                cwd=str(GO_DIR),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if res.returncode == 0 and out_bin.exists():
                return out_bin
            self._log(f"Go build failed: {res.stderr}")
        except Exception as e:
            self._log(f"Go build error: {e}")

        return None

    def build_rust_binary(self) -> Optional[Path]:
        """Discover or build Rust binary."""
        target_release = RUST_DIR / "target" / "release" / "canonical_tui_rust"
        target_debug = RUST_DIR / "target" / "debug" / "canonical_tui_rust"
        build_bin = BASE_DIR / "build" / "canonical_tui_rust"

        for b in (target_release, target_debug, build_bin):
            if b.exists() and os.access(b, os.X_OK):
                return b

        cargo_toml = RUST_DIR / "Cargo.toml"
        if not cargo_toml.exists():
            self._log(f"Rust Cargo.toml not found at {cargo_toml}")
            return None

        cargo_bin = shutil.which("cargo")
        if not cargo_bin:
            self._log("Rust compiler 'cargo' not found in PATH")
            return None

        try:
            self._log("Building Rust binary with cargo build --release")
            res = subprocess.run(
                [cargo_bin, "build", "--release"],
                cwd=str(RUST_DIR),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if res.returncode == 0 and target_release.exists():
                return target_release
            self._log(f"Cargo release build failed: {res.stderr}")
        except Exception as e:
            self._log(f"Cargo build error: {e}")

        return None

    def _measure_rss_mb(self, pid: int) -> float:
        """Measure peak RSS memory in MB for a given PID."""
        try:
            res = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(pid)],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                rss_kb = float(res.stdout.strip().split()[0])
                return round(rss_kb / 1024.0, 2)
        except Exception:
            pass
        return 0.0

    def _run_pty_smoke(
        self, cmd: List[str], cwd: Optional[Path], timeout: float = 3.0
    ) -> Tuple[bool, int, float, float]:
        """Execute a TUI in a PTY with draining to verify clean startup and timeout exit."""
        master, slave = pty.openpty()
        t0 = time.perf_counter()
        rss_mb = 0.0
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
            os.close(slave)

            # Drain pty output in background thread to prevent buffer block
            def _drain():
                try:
                    while True:
                        r, _, _ = select.select([master], [], [], 0.1)
                        if master in r:
                            data = os.read(master, 2048)
                            if not data:
                                break
                except OSError:
                    pass

            drainer = threading.Thread(target=_drain, daemon=True)
            drainer.start()

            # Measure memory after brief warmup
            time.sleep(0.25)
            if proc.poll() is None:
                rss_mb = self._measure_rss_mb(proc.pid)

            proc.wait(timeout=timeout)
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            passed = proc.returncode == 0
            return passed, proc.returncode, duration_ms, rss_mb
        except subprocess.TimeoutExpired:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            if proc.poll() is None:
                proc.kill()
            return False, -9, duration_ms, rss_mb
        except Exception:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return False, -1, duration_ms, rss_mb
        finally:
            try:
                os.close(master)
            except OSError:
                pass

    def verify_python_tui(self) -> TuiBenchmarkResult:
        """Execute and benchmark Python Textual prototype."""
        app_py = PYTHON_DIR / "app.py"
        if not app_py.exists():
            return TuiBenchmarkResult(
                framework="Python (Textual)",
                target_path=str(app_py),
                verify_passed=False,
                verify_exit_code=-1,
                verify_latency_ms=0.0,
                verify_stdout="",
                verify_stderr="app.py not found",
                smoke_passed=False,
                smoke_exit_code=-1,
                smoke_latency_ms=0.0,
                memory_rss_mb=0.0,
                schema_valid=False,
                details={},
                error_message="python_textual/app.py does not exist",
            )

        cmd_verify = [
            sys.executable,
            str(app_py),
            "--state-path",
            str(self.state_path),
            "--verify",
        ]

        t0 = time.perf_counter()
        try:
            p_verify = subprocess.run(
                cmd_verify,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5.0,
            )
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = p_verify.returncode == 0
        except subprocess.TimeoutExpired:
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = False
            p_verify = subprocess.CompletedProcess(cmd_verify, returncode=-9, stdout="", stderr="Timeout expired")
        except Exception as e:
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = False
            p_verify = subprocess.CompletedProcess(cmd_verify, returncode=-1, stdout="", stderr=str(e))

        schema_valid = verify_passed and ("Passed" in p_verify.stdout or p_verify.returncode == 0)

        # Headless smoke test with --timeout 1 via PTY
        cmd_smoke = [
            sys.executable,
            str(app_py),
            "--state-path",
            str(self.state_path),
            "--timeout",
            "1",
        ]
        smoke_passed, smoke_exit, smoke_lat, mem_mb = self._run_pty_smoke(cmd_smoke, PYTHON_DIR, timeout=3.5)

        return TuiBenchmarkResult(
            framework="Python (Textual)",
            target_path=str(app_py),
            verify_passed=verify_passed,
            verify_exit_code=p_verify.returncode,
            verify_latency_ms=verify_lat,
            verify_stdout=p_verify.stdout,
            verify_stderr=p_verify.stderr,
            smoke_passed=smoke_passed,
            smoke_exit_code=smoke_exit,
            smoke_latency_ms=smoke_lat,
            memory_rss_mb=mem_mb,
            schema_valid=schema_valid,
            details={"type": "python", "script": str(app_py)},
            error_message=None if verify_passed else p_verify.stderr,
        )

    def verify_go_tui(self) -> TuiBenchmarkResult:
        """Execute and benchmark Go Bubble Tea prototype."""
        bin_path = self.build_go_binary()
        main_go = GO_DIR / "main.go"

        if not bin_path or not bin_path.exists():
            go_bin = shutil.which("go")
            if go_bin and main_go.exists():
                exec_cmd_verify = [
                    go_bin,
                    "run",
                    "main.go",
                    "-state-path",
                    str(self.state_path),
                    "-verify",
                ]
                target_str = f"go run {main_go}"
                cwd_dir = GO_DIR
            else:
                return TuiBenchmarkResult(
                    framework="Go (Bubble Tea)",
                    target_path=str(bin_path or main_go),
                    verify_passed=False,
                    verify_exit_code=-1,
                    verify_latency_ms=0.0,
                    verify_stdout="",
                    verify_stderr="Go binary not found and go compiler unavailable",
                    smoke_passed=False,
                    smoke_exit_code=-1,
                    smoke_latency_ms=0.0,
                    memory_rss_mb=0.0,
                    schema_valid=False,
                    details={"missing": True},
                    error_message="Go binary not built and 'go' compiler not found",
                )
        else:
            exec_cmd_verify = [
                str(bin_path),
                "-state-path",
                str(self.state_path),
                "-verify",
            ]
            target_str = str(bin_path)
            cwd_dir = GO_DIR

        t0 = time.perf_counter()
        try:
            p_verify = subprocess.run(
                exec_cmd_verify,
                cwd=str(cwd_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout + 5.0,
            )
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = p_verify.returncode == 0
        except subprocess.TimeoutExpired:
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = False
            p_verify = subprocess.CompletedProcess(exec_cmd_verify, returncode=-9, stdout="", stderr="Timeout expired")
        except Exception as e:
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = False
            p_verify = subprocess.CompletedProcess(exec_cmd_verify, returncode=-1, stdout="", stderr=str(e))

        schema_valid = verify_passed and (p_verify.returncode == 0)

        # Headless smoke test with -timeout 1 and -poll-interval 0.5 via PTY
        if bin_path and bin_path.exists():
            cmd_smoke = [
                str(bin_path),
                "-state-path",
                str(self.state_path),
                "-timeout",
                "1",
                "-poll-interval",
                "0.5",
            ]
        else:
            go_bin = shutil.which("go")
            cmd_smoke = [
                go_bin or "go",
                "run",
                "main.go",
                "-state-path",
                str(self.state_path),
                "-timeout",
                "1",
                "-poll-interval",
                "0.5",
            ]

        smoke_passed, smoke_exit, smoke_lat, mem_mb = self._run_pty_smoke(cmd_smoke, cwd_dir, timeout=3.5)

        return TuiBenchmarkResult(
            framework="Go (Bubble Tea)",
            target_path=target_str,
            verify_passed=verify_passed,
            verify_exit_code=p_verify.returncode,
            verify_latency_ms=verify_lat,
            verify_stdout=p_verify.stdout,
            verify_stderr=p_verify.stderr,
            smoke_passed=smoke_passed,
            smoke_exit_code=smoke_exit,
            smoke_latency_ms=smoke_lat,
            memory_rss_mb=mem_mb,
            schema_valid=schema_valid,
            details={"type": "go", "binary": str(bin_path)},
            error_message=None if verify_passed else p_verify.stderr,
        )

    def verify_rust_tui(self) -> TuiBenchmarkResult:
        """Execute and benchmark Rust Ratatui prototype."""
        bin_path = self.build_rust_binary()
        cargo_toml = RUST_DIR / "Cargo.toml"

        if not bin_path or not bin_path.exists():
            cargo_bin = shutil.which("cargo")
            if cargo_bin and cargo_toml.exists():
                exec_cmd_verify = [
                    cargo_bin,
                    "run",
                    "--release",
                    "--",
                    "--state-path",
                    str(self.state_path),
                    "--verify",
                ]
                target_str = "cargo run --release"
                cwd_dir = RUST_DIR
            else:
                return TuiBenchmarkResult(
                    framework="Rust (Ratatui)",
                    target_path=str(bin_path or cargo_toml),
                    verify_passed=False,
                    verify_exit_code=-1,
                    verify_latency_ms=0.0,
                    verify_stdout="",
                    verify_stderr="Rust binary not found and cargo compiler unavailable",
                    smoke_passed=False,
                    smoke_exit_code=-1,
                    smoke_latency_ms=0.0,
                    memory_rss_mb=0.0,
                    schema_valid=False,
                    details={"missing": True},
                    error_message="Rust binary not built and 'cargo' not found in PATH",
                )
        else:
            exec_cmd_verify = [
                str(bin_path),
                "--state-path",
                str(self.state_path),
                "--verify",
            ]
            target_str = str(bin_path)
            cwd_dir = RUST_DIR

        t0 = time.perf_counter()
        try:
            p_verify = subprocess.run(
                exec_cmd_verify,
                cwd=str(cwd_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout + 5.0,
            )
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = p_verify.returncode == 0
        except subprocess.TimeoutExpired:
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = False
            p_verify = subprocess.CompletedProcess(exec_cmd_verify, returncode=-9, stdout="", stderr="Timeout expired")
        except Exception as e:
            verify_lat = round((time.perf_counter() - t0) * 1000.0, 2)
            verify_passed = False
            p_verify = subprocess.CompletedProcess(exec_cmd_verify, returncode=-1, stdout="", stderr=str(e))

        schema_valid = verify_passed and (p_verify.returncode == 0)

        # Headless smoke test with --timeout 1 via PTY
        if bin_path and bin_path.exists():
            cmd_smoke = [
                str(bin_path),
                "--state-path",
                str(self.state_path),
                "--timeout",
                "1",
            ]
        else:
            cargo_bin = shutil.which("cargo")
            cmd_smoke = [
                cargo_bin or "cargo",
                "run",
                "--release",
                "--",
                "--state-path",
                str(self.state_path),
                "--timeout",
                "1",
            ]

        smoke_passed, smoke_exit, smoke_lat, mem_mb = self._run_pty_smoke(cmd_smoke, cwd_dir, timeout=3.5)

        return TuiBenchmarkResult(
            framework="Rust (Ratatui)",
            target_path=target_str,
            verify_passed=verify_passed,
            verify_exit_code=p_verify.returncode,
            verify_latency_ms=verify_lat,
            verify_stdout=p_verify.stdout,
            verify_stderr=p_verify.stderr,
            smoke_passed=smoke_passed,
            smoke_exit_code=smoke_exit,
            smoke_latency_ms=smoke_lat,
            memory_rss_mb=mem_mb,
            schema_valid=schema_valid,
            details={"type": "rust", "binary": str(bin_path)},
            error_message=None if verify_passed else p_verify.stderr,
        )

    def run_all_verifications(self, target: str = "all") -> Dict[str, TuiBenchmarkResult]:
        """Execute verification across specified or all TUI prototypes."""
        results: Dict[str, TuiBenchmarkResult] = {}

        if target in ("all", "python"):
            results["python"] = self.verify_python_tui()

        if target in ("all", "go"):
            results["go"] = self.verify_go_tui()

        if target in ("all", "rust"):
            results["rust"] = self.verify_rust_tui()

        return results


def print_summary_table(results: Dict[str, TuiBenchmarkResult], state_path: Path) -> None:
    """Print clean terminal comparison table."""
    print("=" * 84)
    print(" 🚀 LAUBURU CANONICAL TUI PROTOTYPES — LOCAL VERIFICATION BENCHMARK")
    print(f" State File: {state_path}")
    print("=" * 84)
    print(f"{'Framework':<18} | {'Verify':<8} | {'Latency':<10} | {'Smoke':<8} | {'RSS (MB)':<10} | {'Status'}")
    print("-" * 84)

    all_passed = True
    for key, res in results.items():
        v_str = "PASS" if res.verify_passed else "FAIL"
        s_str = "PASS" if res.smoke_passed else "FAIL"
        lat_str = f"{res.verify_latency_ms:.1f} ms"
        mem_str = f"{res.memory_rss_mb:.1f} MB" if res.memory_rss_mb > 0 else "N/A"
        overall = "✓ READY" if res.verify_passed else f"✗ ERROR ({res.verify_exit_code})"

        if not res.verify_passed:
            all_passed = False

        print(f"{res.framework:<18} | {v_str:<8} | {lat_str:<10} | {s_str:<8} | {mem_str:<10} | {overall}")

    print("=" * 84)
    if all_passed:
        print(" 🎉 ALL PROTOTYPES VERIFIED SUCCESSFULLY (Exit Code 0)")
    else:
        print(" ⚠ ONE OR MORE PROTOTYPES FAILED VERIFICATION")
    print("=" * 84)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonical Lauburu Local TUI Verification & Benchmark Harness"
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to cloud_api_quota_state.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Execution timeout per TUI in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Poll interval passed to TUIs (default: 2.0)",
    )
    parser.add_argument(
        "--tui",
        choices=["all", "python", "go", "rust"],
        default="all",
        help="Filter specific TUI framework to test (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip automatic compilation of Go/Rust binaries",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verifier = LocalTuiVerifier(
        state_path=args.state_path,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        auto_build=not args.no_build,
        verbose=args.verbose,
    )

    state_valid, state_data, state_err = verifier.validate_state_file()
    if not state_valid and args.verbose:
        print(f"Warning: State file validation note: {state_err}", file=sys.stderr)

    results = verifier.run_all_verifications(target=args.tui)

    if args.json:
        json_output = {
            "state_path": str(args.state_path),
            "state_valid": state_valid,
            "results": {k: asdict(v) for k, v in results.items()},
        }
        print(json.dumps(json_output, indent=2))
    else:
        print_summary_table(results, args.state_path)

    failures = [k for k, v in results.items() if not v.verify_passed]
    if failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
