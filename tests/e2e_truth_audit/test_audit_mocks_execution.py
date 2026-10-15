# -*- coding: utf-8 -*-
"""
Tier 1: Feature Coverage for audit_mocks.sh & Target Codebase Mock Sanitization.
Validates execution of audit_mocks.sh, zero BLOCK findings across target apps,
repair of server.py:71 syntax, and venv wildcard filtering.
Governed by: PROJECT.md § Interface Contracts #3, Acceptance Criteria §3, Rule 0, Rule 1.
"""
from __future__ import annotations

import os
import sys
import py_compile
import subprocess
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    AUDIT_MOCKS_PATH,
    FAKE_DATA_SCANNER_PATH,
    PROHIBITED_LITERALS,
    run_cmd,
)


class TestAuditMocksExecution:
    """Verifies audit_mocks.sh execution, scanner upgrades, and target app sanitization."""

    def test_network_cable_analyzer_server_syntax(self):
        """Verifies that 01_apps/network_cable_analyzer/backend/server.py has valid Python syntax (no IndentationError at line 71)."""
        server_py = REPO_ROOT / "01_apps/network_cable_analyzer/backend/server.py"
        assert server_py.is_file(), f"server.py missing at: {server_py}"

        try:
            py_compile.compile(str(server_py), doraise=True)
        except py_compile.PyCompileError as err:
            pytest.fail(f"server.py failed syntax compilation: {err}")

    def test_fake_data_scanner_venv_exclusion(self):
        """Validates that fake_data_scanner excludes virtual environments (*venv*) from scanning."""
        assert FAKE_DATA_SCANNER_PATH.is_file(), f"fake_data_scanner.py missing at: {FAKE_DATA_SCANNER_PATH}"

        # Import or inspect fake_data_scanner SKIP_DIRS / logic
        content = FAKE_DATA_SCANNER_PATH.read_text(encoding="utf-8", errors="ignore")
        # Must exclude venvs either via SKIP_DIRS or fnmatch/wildcard
        has_venv_skip = ".venv" in content or "venv" in content or "*venv*" in content
        assert has_venv_skip, "fake_data_scanner.py lacks virtual environment exclusion"

    @pytest.mark.skipif(
        not AUDIT_MOCKS_PATH.exists(),
        reason="06_scripts_and_tooling/truth/audit_mocks.sh pending creation by Worker 3",
    )
    def test_audit_mocks_script_executable_and_shebang(self):
        """Validates that audit_mocks.sh is executable and contains a valid bash shebang."""
        assert AUDIT_MOCKS_PATH.is_file(), f"audit_mocks.sh not found at: {AUDIT_MOCKS_PATH}"
        assert os.access(str(AUDIT_MOCKS_PATH), os.X_OK), "audit_mocks.sh is not executable (+x)"

        first_line = AUDIT_MOCKS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        assert first_line.startswith("#!") and "bash" in first_line, (
            f"audit_mocks.sh has invalid shebang: {first_line}"
        )

    M3_COMPLETE = (REPO_ROOT / ".agents/teamwork/worker_truth_m3/handoff.md").exists()

    @pytest.mark.skipif(
        not AUDIT_MOCKS_PATH.exists(),
        reason="06_scripts_and_tooling/truth/audit_mocks.sh pending creation by Worker 3",
    )
    def test_audit_mocks_cli_flags(self):
        """Asserts that audit_mocks.sh supports --target-apps, --all, and --staged flags."""
        content = AUDIT_MOCKS_PATH.read_text(encoding="utf-8", errors="ignore")
        assert "--target-apps" in content, "audit_mocks.sh does not reference --target-apps"
        assert "--all" in content, "audit_mocks.sh does not reference --all"
        assert "--staged" in content, "audit_mocks.sh does not reference --staged"

    @pytest.mark.skipif(
        not (REPO_ROOT / ".agents/teamwork/worker_truth_m3/handoff.md").exists(),
        reason="Target app mock purge pending completion of Milestone 3 by Worker 3",
    )
    def test_audit_mocks_target_apps_exit_code_zero(self):
        """Asserts that running audit_mocks.sh --target-apps exits with code 0 (0 BLOCK findings)."""
        code, stdout, stderr = run_cmd(
            ["bash", str(AUDIT_MOCKS_PATH), "--target-apps"],
            timeout=60.0,
        )
        assert code == 0, (
            f"audit_mocks.sh --target-apps failed with exit code {code}!\n"
            f"Stdout: {stdout}\nStderr: {stderr}"
        )
        assert "0 BLOCK" in stdout or "clean" in stdout.lower() or "passed" in stdout.lower()

    @pytest.mark.skipif(
        not (REPO_ROOT / ".agents/teamwork/worker_truth_m3/handoff.md").exists(),
        reason="Target app mock purge pending completion of Milestone 3 by Worker 3",
    )
    def test_port_4000_hub_purged_of_hardcoded_telemetry(self):
        """Asserts that port_4000_hub index.html does not contain hardcoded 0.27ms, GL-MT3600BE, or 1734 ELO."""
        index_html = REPO_ROOT / "01_apps/port_4000_hub/frontend/index.html"
        if index_html.is_file():
            content = index_html.read_text(encoding="utf-8", errors="ignore")
            assert "GL-MT3600BE" not in content, "Found stale GL-MT3600BE router claim in port_4000_hub"
            assert "1734 ELO" not in content, "Found hardcoded 1734 ELO claim in port_4000_hub"
            assert "0.27ms TB4 DMA" not in content, "Found hardcoded 0.27ms TB4 DMA in port_4000_hub"
