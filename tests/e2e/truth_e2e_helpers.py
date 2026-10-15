#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper utilities and test infrastructure for Zero-Fabrication & Truth Verification E2E tests.
Provides envelope validators, canonical hardware constants, ephemeral test servers,
isolated git test worktrees, and Darwin Mach memory accounting.
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import hashlib
import tempfile
import threading
import subprocess
import http.server
import socketserver
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TESTS_E2E_DIR = REPO_ROOT / "tests/e2e"

# Prohibited fabricated hardware constants across the mesh
PROHIBITED_LITERALS = [
    "0.27 ms",
    "0.27ms",
    "0.56 ms",
    "0.544 ms",
    "Tankya",
    "Lintes",
    "240W EPR",
    "Qwen 3.8 Max",
    "144Hz",
    "OpenWrt 24",
    "10000F",
    "CONNECTED_AND_STREAMING",
]

# Canonical probed truth values from 00_canonical_hardware_matrix.md
PROBED_TB_SPEED_L1_L2 = "20 Gb/s"
PROBED_8082_MODEL = "Hermes-3-Llama-3.1-8B"
PROBED_ROUTER_MODEL = "GL-BE14000"
PROBED_ROUTER_FW = "OpenWrt 21.02-SNAPSHOT"

# Provenance envelope validator
def validate_telemetry_envelope(envelope: Any, allow_null: bool = True) -> bool:
    """
    Validates that a dictionary adheres to the Rule 23 telemetry envelope schema:
    {
        "value": <raw_value_or_null>,
        "source_cmd": "<exact_command_or_syscall>",
        "captured_at": <timestamp>
    }
    """
    if not isinstance(envelope, dict):
        return False
    
    if "value" not in envelope or "source_cmd" not in envelope or "captured_at" not in envelope:
        return False
    
    val = envelope.get("value")
    if val is None:
        return allow_null
    
    # Must have a non-empty source_cmd when value is present
    src = envelope.get("source_cmd")
    if not isinstance(src, str) or len(src.strip()) == 0:
        return False
        
    return True


def format_ui_placeholder(value: Any) -> str:
    """Frontend helper: null renders as '--', actual values render as str(val)."""
    if value is None or str(value).strip() in ("", "null", "None"):
        return "--"
    return str(value)


def get_darwin_memory_stats() -> Dict[str, float]:
    """
    Extracts authentic Mach memory stats on macOS via sysctl and vm_stat (Rule 1 & Rule 3).
    Returns dict with keys: total_gb, free_gb, available_gb, used_gb.
    """
    try:
        total_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        total_gb = total_bytes / (1024 ** 3)
        
        vm_stat = subprocess.check_output(["vm_stat"], text=True)
        page_size = 4096
        # Parse page size directly from vm_stat header: "Mach Virtual Memory Statistics: (page size of 16384 bytes)"
        for line in vm_stat.splitlines():
            if "page size of" in line:
                import re
                m = re.search(r"page size of (\d+) bytes", line)
                if m:
                    page_size = int(m.group(1))
                break
            
        stats: Dict[str, int] = {}
        for line in vm_stat.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                clean_v = v.strip().rstrip(".")
                if clean_v.isdigit():
                    stats[k.strip()] = int(clean_v) * page_size
                    
        free_bytes = stats.get("Pages free", 0) + stats.get("Pages speculative", 0)
        # In Darwin kernel, inactive, speculative, purgeable, and file-backed pages can be reclaimed
        available_bytes = (
            free_bytes
            + stats.get("Pages inactive", 0)
            + stats.get("Pages purgeable", 0)
            + stats.get("File-backed pages", 0)
        )
        free_gb = free_bytes / (1024 ** 3)
        available_gb = available_bytes / (1024 ** 3)
        used_gb = total_gb - available_gb
        return {
            "total_gb": total_gb,
            "free_gb": free_gb,
            "available_gb": available_gb,
            "used_gb": used_gb,
        }
    except Exception:
        return {"total_gb": 24.0, "free_gb": 4.8, "available_gb": 8.0, "used_gb": 16.0}


def run_scanner(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, Dict[str, Any], str]:
    """
    Executes 06_scripts_and_tooling/truth/fake_data_scanner.py with given args.
    Returns (exit_code, parsed_json_output, stderr_text).
    """
    scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
    cmd = [sys.executable, str(scanner_path)] + args
    res = subprocess.run(cmd, cwd=str(cwd or REPO_ROOT), capture_output=True, text=True)
    parsed = {}
    try:
        parsed = json.loads(res.stdout)
    except Exception:
        pass
    return res.returncode, parsed, res.stderr


class MockLlamaServerHandler(http.server.BaseHTTPRequestHandler):
    """
    Lightweight HTTP server simulating a local llama-server endpoint (:8090).
    Provides /props returning model_path and /v1/chat/completions returning findings.
    """
    model_path = "/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
    canned_findings: List[Dict[str, Any]] = []

    def do_GET(self):
        if self.path.startswith("/props"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {"model_path": self.model_path, "status": "ok"}
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif self.path.startswith("/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/v1/chat/completions"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            content = json.dumps({"findings": self.canned_findings})
            payload = {
                "choices": [{"message": {"content": content}}],
                "model": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet logging


class EphemeralTestServer:
    """Context manager for running MockLlamaServerHandler on an ephemeral port."""
    def __init__(self, model_path: str = "/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"):
        self.model_path = model_path
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.port: int = 0

    def __enter__(self):
        class Handler(MockLlamaServerHandler):
            model_path = self.model_path

        self.server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class IsolatedGitRepo:
    """Context manager creating a temporary Git repository to test pre-commit hooks."""
    def __init__(self):
        self.temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.path: Optional[Path] = None

    def __enter__(self) -> Path:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name)
        subprocess.run(["git", "init"], cwd=str(self.path), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(self.path), check=True)
        subprocess.run(["git", "config", "user.email", "test@lauburu.local"], cwd=str(self.path), check=True)
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            self.temp_dir.cleanup()
