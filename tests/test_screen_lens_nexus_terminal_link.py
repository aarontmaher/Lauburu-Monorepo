#!/usr/bin/env python3
"""
Test Suite: Screen Lens Sovereign <-> Nexus Terminal Link & Spec-11 Security Gate
Verifies:
- Screen Lens status, OCR inspection, and VLA synchronization via Nexus CLI
- Neo task orchestration via Nexus CLI
- Spec-11 Security Red/Blue Team Zero Leakage Gate
- Nexus Extension Provisioner schema integrity (shells, servers, tunnels, macros)
"""

import os
import sys
import json
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NEXUS_BIN = Path("/Users/aaron/.local/bin/nexus")
AUDITOR_SCRIPT = REPO_ROOT / "06_scripts_and_tooling" / "security" / "spec11_security_auditor.py"
PROVISIONER_SCRIPT = REPO_ROOT / "06_scripts_and_tooling" / "nexus" / "nexus_extension_provisioner.py"

def test_nexus_cli_lens_status():
    """Verify 'nexus lens status' executes with exit code 0 and reports authentic status."""
    res = subprocess.run([str(NEXUS_BIN), "lens", "status"], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, f"lens status failed: {res.stderr}"
    assert "Screen Lens Sovereign Status" in res.stdout
    assert "MJPEG Stream" in res.stdout

def test_nexus_cli_lens_latest():
    """Verify 'nexus lens latest --limit 2' returns sanitized OCR text."""
    res = subprocess.run([str(NEXUS_BIN), "lens", "latest", "--limit", "2"], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, f"lens latest failed: {res.stderr}"
    assert "Screen Lens Sovereign Latest Captures" in res.stdout
    # Spec-11 check: no raw api keys in stdout
    assert "sk-" not in res.stdout or "[REDACTED" in res.stdout

def test_nexus_cli_neo_status():
    """Verify 'nexus neo status' executes with exit code 0."""
    res = subprocess.run([str(NEXUS_BIN), "neo", "status"], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, f"neo status failed: {res.stderr}"
    assert "Neo AI/ML Orchestration Status" in res.stdout

def test_mothership_lens_endpoint():
    """Verify Single-Chat Nexus Mother Ship (/api/chat/nexus/lens) responds with authentic telemetry."""
    req = urllib.request.Request("http://127.0.0.1:4050/api/chat/nexus/lens", headers={"User-Agent": "NexusTest/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data.get("daemon_running") is True
        assert "mjpeg_stream" in data
        assert data.get("spec11_security") == "ACTIVE_SANITIZED"

def test_spec11_security_auditor():
    """Verify Spec-11 Security Red/Blue Team Auditor passes with exit code 0 (COMPLIANT)."""
    assert AUDITOR_SCRIPT.exists(), f"Auditor script missing at {AUDITOR_SCRIPT}"
    res = subprocess.run([sys.executable, str(AUDITOR_SCRIPT)], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"spec-11 audit failed: {res.stdout}\n{res.stderr}"
    assert "COMPLIANT — PROCEED" in res.stdout
    assert "ZERO LEAKAGE" in res.stdout

def test_nexus_provisioner_validation():
    """Verify Nexus Extension Provisioner validates all profiles cleanly."""
    assert PROVISIONER_SCRIPT.exists(), f"Provisioner script missing at {PROVISIONER_SCRIPT}"
    res = subprocess.run([sys.executable, str(PROVISIONER_SCRIPT)], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"provisioner failed: {res.stdout}\n{res.stderr}"
    assert "All 1 servers validated successfully." in res.stdout
    assert "All 4 local shell profiles validated successfully." in res.stdout
    assert "All 2 local servers validated successfully." in res.stdout
    assert "All 15 macros validated successfully." in res.stdout
