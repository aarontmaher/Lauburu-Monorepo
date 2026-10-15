# -*- coding: utf-8 -*-
"""
Tier 1: Feature Coverage for truth_enforcer_daemon.sh.
Validates bash syntax, executable flags, CLI modes (--help, --once, --daemon),
Rule 9 compliance (zero-waste native background daemon), and telemetry status emission.
Governed by: PROJECT.md § Interface Contracts #4, Rule 9, Acceptance Criteria §5.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    TRUTH_ENFORCER_PATH,
    OBSIDIAN_VAULT_PATH,
    PROHIBITED_LITERALS,
    run_cmd,
)


@pytest.mark.skipif(
    not TRUTH_ENFORCER_PATH.exists(),
    reason="06_scripts_and_tooling/truth/truth_enforcer_daemon.sh pending creation by Milestone 4",
)
class TestDaemonSyntaxAndMode:
    """Verifies truth_enforcer_daemon.sh syntax, CLI options, and execution behavior."""

    def test_truth_enforcer_daemon_executable_and_shebang(self):
        """Validates that truth_enforcer_daemon.sh is executable and contains a valid bash shebang."""
        assert TRUTH_ENFORCER_PATH.is_file(), f"Daemon script not found at: {TRUTH_ENFORCER_PATH}"
        assert os.access(str(TRUTH_ENFORCER_PATH), os.X_OK), "truth_enforcer_daemon.sh is not executable (+x)"

        first_line = TRUTH_ENFORCER_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        assert first_line.startswith("#!") and "bash" in first_line, (
            f"truth_enforcer_daemon.sh has invalid shebang: {first_line}"
        )

    def test_truth_enforcer_daemon_syntax_validation(self):
        """Validates bash syntax without execution using 'bash -n'."""
        code, stdout, stderr = run_cmd(["bash", "-n", str(TRUTH_ENFORCER_PATH)])
        assert code == 0, f"truth_enforcer_daemon.sh has bash syntax errors!\nStderr: {stderr}"

    def test_truth_enforcer_daemon_rule9_compliance(self):
        """Validates Rule 9: must use native shell sleep loops, zero agentic schedule calls."""
        content = TRUTH_ENFORCER_PATH.read_text(encoding="utf-8", errors="ignore")

        # Must not call the agentic schedule tool
        assert "schedule(" not in content, "truth_enforcer_daemon.sh violates Rule 9 (calls schedule tool)"
        assert "call_mcp_tool" not in content, "truth_enforcer_daemon.sh must be pure native shell"

        # Must support native loop or sleep
        assert "sleep" in content, "Daemon does not contain native sleep throttling"

    def test_truth_enforcer_daemon_help_flag(self):
        """Asserts that truth_enforcer_daemon.sh --help displays usage for --once and --daemon."""
        code, stdout, stderr = run_cmd(["bash", str(TRUTH_ENFORCER_PATH), "--help"])
        assert code == 0, f"--help failed with code {code}: {stderr}"
        assert "--once" in stdout, "Missing --once mode in help documentation"
        assert "--daemon" in stdout or "daemon" in stdout.lower(), "Missing daemon mode in help documentation"

    def test_truth_enforcer_daemon_once_execution(self):
        """Asserts that running truth_enforcer_daemon.sh --once executes cleanly and writes telemetry."""
        status_md = OBSIDIAN_VAULT_PATH / "APPS_AND_FEATURES/TRUTH_ENFORCER_STATUS.md"

        code, stdout, stderr = run_cmd(
            ["bash", str(TRUTH_ENFORCER_PATH), "--once"],
            timeout=30.0,
        )
        assert code == 0, f"truth_enforcer_daemon.sh --once failed with exit code {code}!\nStderr: {stderr}"

        # Status file must exist and be updated
        assert status_md.is_file(), f"Status file not found at: {status_md}"
        status_text = status_md.read_text(encoding="utf-8", errors="ignore")
        assert len(status_text) > 0, "TRUTH_ENFORCER_STATUS.md is empty"
        assert "Truth Enforcer" in status_text or "TRUTH_ENFORCER" in status_text or "Status" in status_text
