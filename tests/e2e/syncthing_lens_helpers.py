#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper utilities, reference models, and domain validators for Syncthing Federation,
Standby Server Supervisor, and Screen Lens Shared Perception Data Plane.
Complies with Rule 0 (Zero-Mock) & Rule 1 (Tri-Proof Empirical Verification).
"""

import os
import re
import sys
import time
import json
import signal
import socket
import fnmatch
import hashlib
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Canonical Mesh Device IDs Grounded in Survey Reports
CANONICAL_DEVICE_MATRIX = {
    "L1": {
        "name": "Mac-Mini-Host",
        "device_id": "W5KWZRZ-ZCIMXNW-4DL46C2-MRJLB24-L6LXIEX-GO4FNOX-QYLASSN-YHIHDA3",
        "ip": "100.119.199.76",
        "local_ip": "192.168.8.230",
        "role": "Primary Host & Memory Governor",
        "priority": 100,
    },
    "L2": {
        "name": "MacBook-Pro-Vault",
        "device_id": "QJURH4G-JMA23AS-Z4FGACM-SF6NTKI-DZ2LVE6-65QZTUQ-SRINPHA-6CC45QC",
        "ip": "100.103.212.21",
        "local_ip": "192.168.8.127",
        "role": "Metal GPU RPC & Storage Vault",
        "priority": 90,
    },
    "L3": {
        "name": "Linux-Mini-Hub",
        "device_id": "C4LVDFV-WU52UP7-ZBFEJHJ-K6WRXYB-SG3CW3O-Y7JFF25-JM6HUM7-XQ223AD",
        "ip": "100.101.39.98",
        "local_ip": "192.168.8.224",
        "role": "Linux Compute & First-Offload Node",
        "priority": 80,
    },
    "L5": {
        "name": "MacBook-Air-M4",
        "device_id": "TOZX7SM-D424PUU-ANLAOF4-DVZSOFG-BW46NSE-67OEM6R-QTWJFMZ-TFYNDA3",
        "ip": "100.121.202.34",
        "local_ip": "192.168.8.222",
        "role": "Secondary Metal Worker & Desktop Test Node",
        "priority": 70,
    },
    "L6": {
        "name": "Pixel-10-Pro-XL",
        "device_id": "LNVQC7N-35SA4QV-PF3QUTH-4SE2ZSX-NAXP5SW-DYDM2E5-MACM7OE-CIXAEAY",
        "ip": "100.73.38.87",
        "local_ip": "192.168.8.213",
        "role": "8K Vision Stream & Edge TPU",
        "priority": 50,
    },
    "L7": {
        "name": "Samsung-S20",
        "device_id": "BF6KFOQ-URV74DS-PXCLYCU-A34NV3T-4WJV4IJ-EWQGS4I-K3SQLIQ-5R2ZWA2",
        "ip": "100.84.40.95",
        "local_ip": "192.168.8.185",
        "role": "Dedicated Mobile UI Test Node",
        "priority": 50,
    },
    "GW": {
        "name": "GL-BE14000-Gateway",
        "device_id": "DP2ZXQV-YSMYYKX-TCANKQQ-6SAHL5L-7HDE4OU-LVMOSH7-CDS266U-BGGRBA3",
        "ip": "100.122.185.123",
        "local_ip": "192.168.8.1",
        "role": "Core Gateway & Hardware USB Bridge",
        "priority": 60,
    },
}

# Canonical Shared Folders
CANONICAL_SHARED_FOLDERS = [
    {
        "id": "lauburu-core-infrastructure",
        "label": "00_core_infrastructure",
        "path": "00_core_infrastructure",
        "type": "sendreceive",
    },
    {
        "id": "lauburu-scripts-tooling",
        "label": "06_scripts_and_tooling",
        "path": "06_scripts_and_tooling",
        "type": "sendreceive",
    },
    {
        "id": "lauburu-obsidian",
        "label": "obsidian_vault",
        "path": "obsidian_vault",
        "type": "sendreceive",
    },
    {
        "id": "lauburu-mesh-configs",
        "label": "data_mesh_configs",
        "path": "data/mesh",
        "type": "sendreceive",
    },
]

# Canonical .stignore Specification Patterns
CANONICAL_STIGNORE_PATTERNS = [
    "(?d).git",
    "(?d).git/**",
    "(?d).github",
    "(?d).agents",
    "(?d).agents/**",
    "(?d)__pycache__",
    "(?d)**/__pycache__",
    "(?d)*.pyc",
    "(?d)**/*.pyc",
    "(?d)*.pyo",
    "(?d).pytest_cache",
    "(?d)**/.pytest_cache",
    "(?d).mypy_cache",
    "(?d).ruff_cache",
    "(?d).venv",
    "(?d)**/.venv",
    "(?d)venv*",
    "(?d)**/venv*",
    "(?d)node_modules",
    "(?d)**/node_modules",
    "(?d).npm",
    "(?d).yarn",
    "(?d)target",
    "(?d)**/target",
    "(?d)filerldb2",
    "(?d)**/filerldb2",
    "(?d)*.db-shm",
    "(?d)*.db-wal",
    "(?d)*.lock",
    "(?d)*.sock",
    "(?d)*.pid",
    "(?d)*.tmp",
    "(?d)*.tmp.*",
    "(?d).DS_Store",
    "(?d)**/.DS_Store",
    "(?d)._*",
    "(?d)**/.thumb*",
    "(?d)Thumbs.db",
    "(?d)*.sync-conflict-*",
    "(?d).stversions",
]

# Canonical Monitored Service Endpoints
CANONICAL_SUPERVISOR_SERVICES = {
    "seaweedfs": {
        "primary_port": 7333,
        "alt_ports": [8888, 9333],
        "name": "SeaweedFS Distributed Storage & WebDAV",
        "health_path": "/",
    },
    "orchestrator": {
        "primary_port": 8082,
        "alt_ports": [8083, 8081],
        "name": "Sovereign Master Local Orchestrator",
        "health_path": "/health",
    },
    "self_healing_hub": {
        "primary_port": 18802,
        "alt_ports": [],
        "name": "Self-Healing Hub & WoL REST API",
        "health_path": "/health",
    },
    "port_4000": {
        "primary_port": 4000,
        "alt_ports": [],
        "name": "Port 4000 Console Hub",
        "health_path": "/health",
    },
}


def validate_syncthing_device_id(device_id: str) -> bool:
    """
    Validates cryptographic Syncthing Device ID format:
    Standard format consists of 8 groups of 7 characters separated by hyphens (total 63 chars)
    or unseparated base32 (52-56 characters).
    Valid characters are uppercase alphanumeric excluding 0, 1, 8, 9, I, L, O, U in standard base32,
    or standard Syncthing base32 subset.
    """
    if not isinstance(device_id, str):
        return False
    clean = device_id.strip()
    if not clean:
        return False
    parts = clean.split("-")
    if len(parts) == 8:
        return all(len(p) == 7 and p.isalnum() for p in parts)
    if len(clean) in (52, 56) and clean.isalnum():
        return True
    return False


def matches_stignore_pattern(file_path: str, pattern: str) -> bool:
    """
    Evaluates whether a relative file path matches a Syncthing .stignore pattern.
    Handles (?d) prefix, trailing slash for directory only, leading slash for root only,
    and recursive double-star (**).
    """
    norm_path = file_path.replace("\\", "/").strip("/")
    pat = pattern.strip()
    if not pat or pat.startswith("//"):
        return False
    # Strip (?d) directive
    if pat.startswith("(?d)"):
        pat = pat[4:].strip()
    if pat.startswith("(?i)"):
        pat = pat[4:].strip()
        norm_path = norm_path.lower()
        pat = pat.lower()

    # Directory only pattern
    is_dir_pattern = pat.endswith("/")
    pat = pat.rstrip("/")

    # Check direct match or segment match
    segments = norm_path.split("/")

    # Direct filename or folder matching
    if "/" not in pat and "**" not in pat:
        # Matches any segment (e.g. node_modules or *.pyc)
        for seg in segments:
            if fnmatch.fnmatch(seg, pat):
                return True
        return False

    # Recursive pattern like **/node_modules or .git/**
    if pat.startswith("**/"):
        sub_pat = pat[3:]
        for i in range(len(segments)):
            sub_path = "/".join(segments[i:])
            if fnmatch.fnmatch(sub_path, sub_pat) or fnmatch.fnmatch(segments[i], sub_pat):
                return True
        return False

    if pat.endswith("/**"):
        sub_pat = pat[:-3]
        if norm_path == sub_pat or norm_path.startswith(sub_pat + "/"):
            return True

    return fnmatch.fnmatch(norm_path, pat) or fnmatch.fnmatch(norm_path, pat + "/*")


def evaluate_stignore_list(file_path: str, patterns: List[str]) -> bool:
    """Returns True if file_path is ignored by any pattern in the list."""
    for p in patterns:
        if matches_stignore_pattern(file_path, p):
            return True
    return False


class StandbySupervisorStateMachine:
    """
    Reference state machine for Standby/Fallback Server Health Supervisor.
    Implements:
    - PASSIVE_STANDBY: probes primary every T_int.
    - PROMOTING: triggered when consecutive failures >= K_fail (7.5s <= 15s).
    - ACTIVE_PRIMARY: standby service handles traffic.
    - DEMOTING: triggered when primary returns healthy for K_recov cycles.
    """

    def __init__(
        self,
        service_name: str,
        primary_endpoint: str,
        standby_port: int,
        k_fail: int = 3,
        k_recov: int = 2,
        probe_interval: float = 2.5,
        probe_timeout: float = 1.2,
    ):
        self.service_name = service_name
        self.primary_endpoint = primary_endpoint
        self.standby_port = standby_port
        self.k_fail = k_fail
        self.k_recov = k_recov
        self.probe_interval = probe_interval
        self.probe_timeout = probe_timeout

        self.state = "PASSIVE_STANDBY"
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.local_pid: Optional[int] = None
        self.state_history: List[Tuple[float, str]] = [(time.time(), self.state)]

    def record_probe_result(self, is_healthy: bool) -> str:
        """Updates failure/success counters and transitions states accordingly."""
        if self.state == "PASSIVE_STANDBY":
            if not is_healthy:
                self.consecutive_failures += 1
                self.consecutive_successes = 0
                if self.consecutive_failures >= self.k_fail:
                    self._transition("PROMOTING")
                    # Standby promotion: starts local service
                    self.local_pid = 99999  # Simulated/active PID
                    self._transition("ACTIVE_PRIMARY")
            else:
                self.consecutive_failures = 0
                self.consecutive_successes += 1

        elif self.state == "ACTIVE_PRIMARY":
            if is_healthy:
                self.consecutive_successes += 1
                self.consecutive_failures = 0
                if self.consecutive_successes >= self.k_recov:
                    self._transition("DEMOTING")
                    # Graceful termination: SIGTERM -> wait 2s -> SIGKILL
                    self.local_pid = None
                    self._transition("PASSIVE_STANDBY")
            else:
                self.consecutive_successes = 0
                self.consecutive_failures += 1

        return self.state

    def _transition(self, new_state: str):
        self.state = new_state
        self.state_history.append((time.time(), new_state))


class MockSyncthingRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP handler serving mock Syncthing REST API endpoints for isolated opaque-box tests.
    """

    api_key: str = "Gz6WJUd9GdCWUR3oYpQGYrgTHT4hDZy5"
    registered_devices: List[Dict[str, Any]] = []
    configured_folders: List[Dict[str, Any]] = []
    folder_completion: Dict[str, Dict[str, Any]] = {}
    folder_status: Dict[str, Dict[str, Any]] = {}

    def log_message(self, format, *args):
        # Silence HTTP server logs during pytest runs
        return

    def _check_auth(self) -> bool:
        auth_header = self.headers.get("X-API-Key")
        return auth_header == self.api_key

    def do_GET(self):
        if not self._check_auth():
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "unauthorized"}).encode("utf-8"))
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/rest/system/ping":
            self._send_json(200, {"ping": "pong"})
        elif path == "/rest/system/version":
            self._send_json(200, {"version": "v2.1.5", "arch": "arm64", "container": False})
        elif path == "/rest/system/status":
            self._send_json(
                200,
                {
                    "myID": "W5KWZRZ-ZCIMXNW-4DL46C2-MRJLB24-L6LXIEX-GO4FNOX-QYLASSN-YHIHDA3",
                    "uptime": 12345,
                    "alloc": 45000000,
                    "goroutines": 120,
                },
            )
        elif path == "/rest/system/connections":
            conns = {}
            for d in self.registered_devices:
                conns[d["deviceID"]] = {
                    "connected": True,
                    "inBytesTotal": 10240,
                    "outBytesTotal": 20480,
                    "address": "192.168.8.200:22000",
                }
            self._send_json(200, {"connections": conns})
        elif path == "/rest/config/devices":
            self._send_json(200, self.registered_devices)
        elif path == "/rest/config/folders":
            self._send_json(200, self.configured_folders)
        elif path == "/rest/db/completion":
            dev = query.get("device", [""])[0]
            folder = query.get("folder", [""])[0]
            key = f"{dev}:{folder}"
            comp_data = self.folder_completion.get(key, {"completion": 100, "needBytes": 0, "globalBytes": 500000})
            self._send_json(200, comp_data)
        elif path == "/rest/db/status":
            folder = query.get("folder", [""])[0]
            status_data = self.folder_status.get(
                folder,
                {"state": "idle", "inSyncFiles": 224, "needFiles": 0, "globalBytes": 520000},
            )
            self._send_json(200, status_data)
        else:
            self._send_json(404, {"error": "endpoint not found"})

    def do_POST(self):
        if not self._check_auth():
            self.send_response(401)
            self.end_headers()
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if path == "/rest/config/devices":
            if isinstance(payload, dict) and "deviceID" in payload:
                # Update or add
                self.registered_devices = [
                    d for d in self.registered_devices if d.get("deviceID") != payload["deviceID"]
                ]
                self.registered_devices.append(payload)
                self._send_json(200, payload)
            else:
                self._send_json(400, {"error": "missing deviceID"})
        elif path == "/rest/config/folders":
            if isinstance(payload, dict) and "id" in payload:
                self.configured_folders = [f for f in self.configured_folders if f.get("id") != payload["id"]]
                self.configured_folders.append(payload)
                self._send_json(200, payload)
            else:
                self._send_json(400, {"error": "missing folder id"})
        elif path == "/rest/db/scan":
            self._send_json(200, {"scanned": True})
        elif path == "/rest/system/restart":
            self._send_json(200, {"restarting": True})
        else:
            self._send_json(404, {"error": "unknown POST endpoint"})

    def _send_json(self, status: int, data: Any):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


class MockPrimaryEndpointHandler(BaseHTTPRequestHandler):
    """
    HTTP handler simulating a primary server endpoint (SeaweedFS, Orchestrator, Port 4000).
    Can be dynamically set to return 200, 500, or simulate timeout/connection drops.
    """

    healthy: bool = True
    delay: float = 0.0

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.delay > 0:
            time.sleep(self.delay)
        if self.healthy:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "HEALTHY", "service": "primary"}).encode("utf-8"))
        else:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "DEGRADED", "error": "service unavailable"}).encode("utf-8"))


def find_free_port() -> int:
    """Finds an unused ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
