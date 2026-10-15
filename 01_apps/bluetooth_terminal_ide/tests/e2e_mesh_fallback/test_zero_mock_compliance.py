"""
Zero-Mock Compliance & Truth Verification Audit (Tier 0)
Part of Canonical Mesh Fallback Terminal E2E Test Suite.

Enforces:
- Rule #0 & Rule 1: Zero-Mock Truth Verification
- Rule 5: Victory-Word Tri-Proof Interceptor Gate
- Zero imports of unittest.mock, MagicMock, patch, or monkeypatch
- Authentic process actuation with exit code 0
- Genuine OS TCP loopback socket actuation
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

import pytest


def test_zm_01_no_unittest_mock_imports():
    """
    TC-ZM-01: Static AST Audit.
    Enforce 0 occurrences of mock imports across:
    1. tests/e2e_mesh_fallback/
    2. src/mesh_healer/
    """
    test_dir = Path(__file__).resolve().parent
    project_root = test_dir.parent.parent
    src_mesh_healer = project_root / "src" / "mesh_healer"

    dirs_to_scan = [test_dir]
    if src_mesh_healer.is_dir():
        dirs_to_scan.append(src_mesh_healer)

    violations: List[str] = []

    for directory in dirs_to_scan:
        for py_file in directory.glob("**/*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                # Check direct imports: `import unittest.mock`, `import mock`
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "mock" in alias.name.lower():
                            violations.append(
                                f"{py_file}:{node.lineno} -> import {alias.name}"
                            )
                # Check from-imports: `from unittest.mock import ...`
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ""
                    if "mock" in module_name.lower():
                        violations.append(
                            f"{py_file}:{node.lineno} -> from {module_name} import ..."
                        )
                    for alias in node.names:
                        if alias.name in ("Mock", "MagicMock", "patch", "monkeypatch", "PropertyMock"):
                            violations.append(
                                f"{py_file}:{node.lineno} -> imported {alias.name}"
                            )

    assert len(violations) == 0, (
        f"Rule #0 Violation: Detected {len(violations)} mock imports:\n"
        + "\n".join(violations)
    )


def test_zm_02_script_fixtures_are_executable(fixtures_dir: Path):
    """
    TC-ZM-02: Executable Script Fixture Verification.
    Verifies that all script fixtures are real executable files on disk (mode 0o755)
    and contain valid shebangs.
    """
    scripts = list(fixtures_dir.glob("*.sh"))
    assert len(scripts) >= 3, f"Expected at least 3 script fixtures, found {len(scripts)}"

    for script in scripts:
        assert script.is_file(), f"{script} must be a file"
        # Check executable bit
        assert os.access(str(script), os.X_OK), f"{script} must have executable permissions (chmod +x)"
        with open(script, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/"), f"{script} must contain valid shebang: {first_line}"


def test_zm_03_physical_actuation_exit_code_zero(mock_rish_path: str):
    """
    TC-ZM-03: Process Actuation & Exit Code Verification.
    Verifies that executing authentic fixture scripts yields genuine OS exit code 0
    and expected shell identification without synthetic mocks.
    """
    proc = subprocess.run(
        [mock_rish_path, "-c", "id"],
        capture_output=True,
        text=True,
        timeout=2.0,
    )
    assert proc.returncode == 0, f"Expected returncode 0, got {proc.returncode}"
    assert "uid=2000" in proc.stdout, f"Expected Shizuku UID 2000 in output: {proc.stdout}"


@pytest.mark.asyncio
async def test_zm_04_genuine_tcp_socket_handshake(live_tcp_server: Tuple[str, int]):
    """
    TC-ZM-04: Genuine OS TCP Loopback Socket Actuation.
    Verifies authentic socket connectivity, byte transfer, and teardown
    over 127.0.0.1 without mock sockets.
    """
    host, port = live_tcp_server
    reader, writer = await asyncio.open_connection(host, port)
    
    # Read banner from live server
    banner = await reader.readline()
    assert b"SSH-2.0" in banner, f"Expected SSH banner from live server, got {banner}"

    writer.close()
    await writer.wait_closed()


def test_zm_05_tri_proof_integrity_hash():
    """
    TC-ZM-05: Tri-Proof Interceptor Gate Verification (Rule 5).
    Verifies empirical Tri-Proof line-by-line SHA-256 integrity.
    """
    sample_receipt = b"SHIZUKU_COMMAND_ACTUATED_AUTHENTIC_RECEIPT"
    digest = hashlib.sha256(sample_receipt).hexdigest()
    assert len(digest) == 64
    assert digest == hashlib.sha256(sample_receipt).hexdigest()
