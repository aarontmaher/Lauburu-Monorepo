"""Pytest fixtures and test helpers for Canonical TUI Prototypes E2E Test Suite.

Provides genuine schema fixtures, state file factories, concurrency lock helpers,
and multi-framework TUI execution runners.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON_APP = BASE_DIR / "python_textual" / "app.py"
GO_DIR = BASE_DIR / "go_bubbletea"
RUST_DIR = BASE_DIR / "rust_ratatui"
MONOREPO_ROOT = BASE_DIR.parent.parent
CANONICAL_STATE_PATH = (
    MONOREPO_ROOT / "04_data_and_memory" / "data" / "cloud_api_quota_state.json"
)


@dataclass
class TuiExecutionResult:
    framework: str
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Provide an isolated temporary directory for test state files."""
    state_dir = tmp_path / "state_workspace"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


@pytest.fixture
def canonical_valid_state_dict() -> Dict[str, Any]:
    """Return a genuine schema dictionary matching cloud_api_quota_state.json."""
    return {
        "version": "2.0.0",
        "last_reset": "2026-08-27T06:00:00.000000+00:00",
        "last_reset_date": "2026-08-27",
        "last_updated": "2026-08-27T12:50:00.000000+00:00",
        "providers": {
            "julien_ai": {
                "name": "Julien AI (Direct)",
                "daily_limit": 300,
                "used_today": 42,
                "remaining_pct": 0.86,
                "avg_latency_ms": 1250.5,
                "last_latency_ms": 1180.0,
                "max_tokens": 8192,
                "consecutive_failures": 0,
                "total_requests": 42,
                "successful_requests": 42,
                "status": "healthy",
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787834500.0,
                "is_local": False,
            },
            "cloudflare_ai": {
                "name": "Cloudflare Workers AI",
                "daily_limit": 1000,
                "used_today": 150,
                "remaining_pct": 0.85,
                "avg_latency_ms": 750.2,
                "last_latency_ms": 710.0,
                "max_tokens": 4096,
                "consecutive_failures": 0,
                "total_requests": 150,
                "successful_requests": 150,
                "status": "healthy",
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787834510.0,
                "is_local": False,
            },
            "gemini_free": {
                "name": "Google Gemini Free Tier",
                "daily_limit": 1500,
                "used_today": 500,
                "remaining_pct": 0.667,
                "avg_latency_ms": 480.0,
                "last_latency_ms": 450.0,
                "max_tokens": 32768,
                "consecutive_failures": 0,
                "total_requests": 500,
                "successful_requests": 500,
                "status": "healthy",
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787834520.0,
                "is_local": False,
            },
            "local_mesh": {
                "name": "Lauburu Local Mesh GPU",
                "daily_limit": 999999,
                "used_today": 12,
                "remaining_pct": 1.0,
                "avg_latency_ms": 320.0,
                "last_latency_ms": 290.0,
                "max_tokens": 16384,
                "consecutive_failures": 0,
                "total_requests": 12,
                "successful_requests": 12,
                "status": "healthy",
                "cooldown_until": 0.0,
                "last_used_timestamp": 1787834530.0,
                "is_local": True,
            },
        },
        "metrics": {
            "total_tasks_routed": 704,
            "cloud_tasks_succeeded": 692,
            "local_mesh_fallback_count": 12,
            "total_lora_samples_harvested": 692,
        },
    }


@pytest.fixture
def exhausted_state_dict(canonical_valid_state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return state where all cloud providers are exhausted."""
    data = json.loads(json.dumps(canonical_valid_state_dict))
    data["providers"]["julien_ai"]["used_today"] = 300
    data["providers"]["julien_ai"]["remaining_pct"] = 0.0
    data["providers"]["julien_ai"]["status"] = "exhausted"

    data["providers"]["cloudflare_ai"]["used_today"] = 1000
    data["providers"]["cloudflare_ai"]["remaining_pct"] = 0.0
    data["providers"]["cloudflare_ai"]["status"] = "exhausted"

    data["providers"]["gemini_free"]["used_today"] = 1500
    data["providers"]["gemini_free"]["remaining_pct"] = 0.0
    data["providers"]["gemini_free"]["status"] = "exhausted"

    data["metrics"]["local_mesh_fallback_count"] = 55
    return data


@pytest.fixture
def massive_state_dict(canonical_valid_state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return state with large integers to test boundary overflow."""
    data = json.loads(json.dumps(canonical_valid_state_dict))
    data["providers"]["local_mesh"]["daily_limit"] = 999999999999
    data["providers"]["local_mesh"]["used_today"] = 123456789012
    data["metrics"]["total_tasks_routed"] = 999999999999
    data["metrics"]["total_lora_samples_harvested"] = 888888888888
    return data


@pytest.fixture
def state_writer() -> Callable[[Path, Any, bool], Path]:
    """Atomic state file writer helper with optional flock lockfile."""

    def _write(
        path: Path, data: Any, with_lock: bool = True, use_json: bool = True
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = path.with_suffix(".tmp")
        lock_file = path.with_suffix(".lock")

        content = json.dumps(data, indent=2) if use_json and isinstance(data, (dict, list)) else str(data)

        if with_lock:
            lock_file.touch()
            with open(lock_file, "r+") as lk:
                try:
                    fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
                except Exception:
                    pass
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_file, path)
                try:
                    fcntl.flock(lk.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
        else:
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, path)

        return path

    return _write


@pytest.fixture
def valid_state_file(
    temp_state_dir: Path,
    canonical_valid_state_dict: Dict[str, Any],
    state_writer: Callable[[Path, Any, bool], Path],
) -> Path:
    """Create a temporary valid state file."""
    p = temp_state_dir / "cloud_api_quota_state.json"
    return state_writer(p, canonical_valid_state_dict, True)


@pytest.fixture
def tui_runner() -> Callable[..., TuiExecutionResult]:
    """Helper to execute TUI prototypes across Python, Go, and Rust."""

    def _run(
        framework: str,
        state_path: Optional[Path] = None,
        verify: bool = False,
        poll_interval: Optional[float] = None,
        timeout: Optional[float] = None,
        extra_args: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        exec_timeout: float = 8.0,
    ) -> TuiExecutionResult:
        cmd: List[str] = []
        framework_lower = framework.lower()

        if "python" in framework_lower:
            cmd = [sys.executable, str(PYTHON_APP)]
            if state_path:
                cmd.extend(["--state-path", str(state_path)])
            if verify:
                cmd.append("--verify")
            if poll_interval is not None:
                cmd.extend(["--poll-interval", str(poll_interval)])
            if timeout is not None:
                cmd.extend(["--timeout", str(timeout)])
            work_dir = cwd or BASE_DIR

        elif "go" in framework_lower:
            go_bin = GO_DIR / "bin" / "tui_go"
            if go_bin.exists():
                cmd = [str(go_bin)]
            else:
                go_compiler = shutil.which("go")
                if go_compiler:
                    cmd = [go_compiler, "run", "main.go"]
                else:
                    cmd = [str(go_bin)]  # Will fail cleanly if missing
            if state_path:
                cmd.extend(["-state-path", str(state_path)])
            if verify:
                cmd.append("-verify")
            if poll_interval is not None:
                cmd.extend(["-poll-interval", str(poll_interval)])
            if timeout is not None:
                cmd.extend(["-timeout", str(timeout)])
            work_dir = cwd or GO_DIR

        elif "rust" in framework_lower:
            rust_bin_rel = RUST_DIR / "target" / "release" / "canonical_tui_rust"
            rust_bin_deb = RUST_DIR / "target" / "debug" / "canonical_tui_rust"
            if rust_bin_rel.exists():
                cmd = [str(rust_bin_rel)]
            elif rust_bin_deb.exists():
                cmd = [str(rust_bin_deb)]
            else:
                cargo_compiler = shutil.which("cargo")
                if cargo_compiler:
                    cmd = [cargo_compiler, "run", "--release", "--"]
                else:
                    cmd = [str(rust_bin_rel)]
            if state_path:
                cmd.extend(["--state-path", str(state_path)])
            if verify:
                cmd.append("--verify")
            if poll_interval is not None:
                cmd.extend(["--poll-interval", str(poll_interval)])
            if timeout is not None:
                cmd.extend(["--timeout", str(timeout)])
            work_dir = cwd or RUST_DIR
        else:
            raise ValueError(f"Unknown framework: {framework}")

        if extra_args:
            cmd.extend(extra_args)

        t0 = time.perf_counter()
        timed_out = False
        try:
            res = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=exec_timeout,
            )
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return TuiExecutionResult(
                framework=framework,
                command=cmd,
                returncode=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_ms=duration_ms,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as te:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return TuiExecutionResult(
                framework=framework,
                command=cmd,
                returncode=-9,
                stdout=te.stdout.decode() if isinstance(te.stdout, bytes) else (te.stdout or ""),
                stderr=te.stderr.decode() if isinstance(te.stderr, bytes) else (te.stderr or "Process timed out"),
                duration_ms=duration_ms,
                timed_out=True,
            )
        except Exception as ex:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return TuiExecutionResult(
                framework=framework,
                command=cmd,
                returncode=-1,
                stdout="",
                stderr=str(ex),
                duration_ms=duration_ms,
                timed_out=False,
            )

    return _run
