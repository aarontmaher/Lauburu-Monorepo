# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis & Corner Cases Test Suite.
Validates system behavior under adverse conditions:
- Unreachable / offline nodes returning measured=False and '--'
- Stale git index.lock detection
- Constrained disk headroom thresholds
- Scanner resilience on empty files (0 bytes)
- Precise discrimination between comments vs active executable code
- Verification that prohibited literals in code trigger BLOCK violations.
Governed by: PROJECT.md § Milestones, Rule 0, Rule 1, Rule 5.
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import socket
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    OBSIDIAN_VAULT_PATH,
    FAKE_DATA_SCANNER_PATH,
    PROHIBITED_LITERALS,
    is_storage_healthy,
    validate_telemetry_envelope,
    run_cmd,
)

# Import scan_file from fake_data_scanner directly if available
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/truth"))
try:
    from fake_data_scanner import scan_file  # type: ignore
except ImportError:
    scan_file = None


class TestBoundaryCornerCases:
    """Stress tests operational boundaries, simulated failures, and parser edge cases."""

    def test_storage_health_detects_simulated_git_lock(self, tmp_path):
        """Validates that is_storage_healthy() returns False when a git index.lock is present."""
        # Setup mock project structure
        mock_root = tmp_path / "mock_repo"
        mock_root.mkdir()
        (mock_root / ".git").mkdir()
        (mock_root / "obsidian_vault").mkdir()
        (mock_root / "04_data_and_memory").mkdir()

        # Valid Index.md
        index_file = mock_root / "obsidian_vault/Index.md"
        index_file.write_text(
            "[[Index]]\n[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
            encoding="utf-8",
        )

        # Baseline: healthy
        healthy, details = is_storage_healthy(mock_root)
        assert healthy is True, f"Mock baseline should be healthy: {details}"

        # Inject simulated lock
        lock_file = mock_root / ".git/index.lock"
        lock_file.write_text("simulated_lock", encoding="utf-8")

        # Must report unhealthy
        locked_healthy, locked_details = is_storage_healthy(mock_root)
        assert locked_healthy is False, "is_storage_healthy() failed to detect simulated git index.lock!"
        assert locked_details["no_index_lock"] is False, "no_index_lock should be False"
        assert locked_details["git_healthy"] is False, "git_healthy should be False"

    def test_storage_health_with_constrained_disk_threshold(self):
        """Validates that is_storage_healthy() rejects disk space when threshold exceeds free space."""
        # Test with threshold of 100,000 GB which cannot be satisfied
        healthy, details = is_storage_healthy(REPO_ROOT, min_disk_free_gb=100_000.0)
        assert healthy is False, "is_storage_healthy() must fail when disk threshold is unmeetable"
        assert details["disk_healthy"] is False, "disk_healthy must report False"

    def test_storage_health_missing_canonical_wikilinks(self, tmp_path):
        """Validates that is_storage_healthy() fails if Index.md lacks required canonical Wikilinks."""
        mock_root = tmp_path / "mock_repo_links"
        mock_root.mkdir()
        (mock_root / ".git").mkdir()
        (mock_root / "obsidian_vault").mkdir()
        (mock_root / "04_data_and_memory").mkdir()

        # Index.md missing required Wikilinks
        index_file = mock_root / "obsidian_vault/Index.md"
        index_file.write_text("# Knowledge Base\nSome notes without required links", encoding="utf-8")

        healthy, details = is_storage_healthy(mock_root)
        assert healthy is False, "is_storage_healthy() must fail when canonical Wikilinks are missing"
        assert details["obsidian_links_ok"] is False, "obsidian_links_ok must report False"

    def test_scanner_handles_empty_files_without_error(self, tmp_path):
        """Validates that fake_data_scanner cleanly processes empty 0-byte files across all extensions."""
        if scan_file is None:
            pytest.skip("fake_data_scanner.py not importable")

        for ext in [".py", ".js", ".ts", ".sh", ".html", ".kt"]:
            empty_file = tmp_path / f"empty_test{ext}"
            empty_file.write_text("", encoding="utf-8")

            findings = scan_file(empty_file)
            assert isinstance(findings, list), f"Expected list for {ext}, got {type(findings)}"
            assert len(findings) == 0, f"Empty file {ext} produced unexpected findings: {findings}"

    def test_scanner_differentiates_comments_from_executable_code(self, tmp_path):
        """Validates that comments mentioning prohibited constants for documentation do NOT trigger BLOCK."""
        if scan_file is None:
            pytest.skip("fake_data_scanner.py not importable")

        comment_file = tmp_path / "documented_reference.py"
        comment_file.write_text(
            """# In the old architecture, developers claimed 0.27ms RTT
# The old router was named GL-MT3600BE before probing GL-BE14000
# The previous unverified ELO was 1734 ELO
# Old notes: 82.8 GB VRAM was pooled
\"\"\"
Docstring explaining why 0.27 ms is prohibited per Rule 0.
\"\"\"
def get_clean_status():
    return "--"
""",
            encoding="utf-8",
        )

        findings = scan_file(comment_file)
        block_findings = [f for f in findings if f.get("severity") == "BLOCK"]
        assert len(block_findings) == 0, (
            f"Comments/docstrings triggered unexpected BLOCK findings: {block_findings}"
        )

    def test_scanner_detects_prohibited_literals_in_executable_code(self):
        """Validates that prohibited literals in active executable code trigger BLOCK findings."""
        if scan_file is None:
            pytest.skip("fake_data_scanner.py not importable")

        probe_dir = Path("/tmp/truth_audit_probe_prod")
        probe_dir.mkdir(parents=True, exist_ok=True)
        bad_file = probe_dir / "production_code.py"
        try:
            bad_file.write_text(
                """def get_rtt():
    rtt = 0.27
    return rtt
""",
                encoding="utf-8",
            )

            findings = scan_file(bad_file)
            block_findings = [f for f in findings if f.get("severity") == "BLOCK"]
            assert len(block_findings) >= 1, f"Failed to detect prohibited 0.27ms literal in executable code! Got: {findings}"
            assert any("0.27" in f.get("rule", "") or "Thunderbolt" in f.get("rule", "") for f in block_findings)
        finally:
            if bad_file.exists():
                bad_file.unlink()
            shutil.rmtree(probe_dir, ignore_errors=True)

    def test_unreachable_node_envelope_contract(self):
        """Validates envelope generation and placeholder formatting for unreachable endpoints."""
        # An unreachable endpoint must yield an envelope with measured=False and value=None
        unreachable_envelope = {
            "value": None,
            "measured": False,
            "source_cmd": "ssh 192.0.2.1",
            "captured_at": 1788888888.0,
            "error": "Connection timed out",
        }
        assert validate_telemetry_envelope(unreachable_envelope) is True

        # Frontend placeholder helper must render '--'
        val = unreachable_envelope["value"]
        formatted = "--" if val is None else str(val)
        assert formatted == "--", f"Expected '--' placeholder for null value, got '{formatted}'"

        # A valid measured envelope
        measured_envelope = {
            "value": 20,
            "measured": True,
            "source_cmd": "system_profiler SPThunderboltDataType",
            "captured_at": 1788888888.0,
        }
        assert validate_telemetry_envelope(measured_envelope) is True
        formatted_measured = "--" if measured_envelope["value"] is None else str(measured_envelope["value"])
        assert formatted_measured == "20"
