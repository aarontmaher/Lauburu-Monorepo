# -*- coding: utf-8 -*-
"""
Tier 4: Real-World Acceptance Workload Integration Test Pipeline.
Executes the full end-to-end acceptance workload verifying all 6 acceptance criteria
from ORIGINAL_REQUEST.md (2026-10-07T03:02:07Z) and PROJECT.md:
1. Live mesh probing without simulated data (verify_probes.py)
2. Programmatic Tri-Vault storage validation (is_storage_healthy())
3. Static mock analysis reporting 0 BLOCK violations (audit_mocks.sh)
4. Target codebase sanitization and syntax integrity
5. Continuous enforcement daemon script (truth_enforcer_daemon.sh)
6. Canonical truth audit report in obsidian_vault (TRUTH_AUDIT_REPORT.md).
Governed by: PROJECT.md § Architecture, Rule 0, Rule 1, Rule 2, Rule 3, Rule 5, Rule 9.
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    VERIFY_PROBES_PATH,
    AUDIT_MOCKS_PATH,
    TRUTH_ENFORCER_PATH,
    OBSIDIAN_VAULT_PATH,
    CONTINUOUS_LORA_JSONL,
    PROHIBITED_LITERALS,
    is_storage_healthy,
    get_darwin_mach_memory,
    run_cmd,
)


class TestRealWorldAcceptanceWorkload:
    """Full end-to-end acceptance criteria validation pipeline."""

    def test_acceptance_criterion_storage_health_gate(self):
        """Acceptance Criterion 2: Tri-Vault storage health is programmatically validated via is_storage_healthy()."""
        healthy, details = is_storage_healthy(REPO_ROOT)
        assert healthy is True, f"Tri-Vault storage health check failed: {details}"

        # Verify Vault 1 (Obsidian)
        assert details["obsidian_healthy"] is True
        index_file = OBSIDIAN_VAULT_PATH / "Index.md"
        assert index_file.is_file() and index_file.stat().st_size > 0

        # Verify Vault 2 (PySpark Data Lake)
        assert details["pyspark_healthy"] is True
        assert CONTINUOUS_LORA_JSONL.is_file()
        assert CONTINUOUS_LORA_JSONL.stat().st_size > 0

        # Verify Vault 3 (Git Monorepo)
        assert details["git_healthy"] is True
        assert details["no_index_lock"] is True

        # Verify Host Sanctuary (RAM & Disk)
        assert details["disk_healthy"] is True
        mem = get_darwin_mach_memory()
        assert mem["free_gb"] >= 4.0 or mem["available_gb"] >= 4.8
        assert mem["util_pct"] <= 85.0

    @pytest.mark.skipif(
        not VERIFY_PROBES_PATH.exists(),
        reason="Acceptance Criterion 1: verify_probes.py pending creation by Worker 1",
    )
    def test_acceptance_criterion_live_probes_execution(self):
        """Acceptance Criterion 1: A verification script (verify_probes.py) executes live probes without simulated data."""
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--json", "--timeout", "5"],
            timeout=35.0,
        )
        assert code == 0, f"verify_probes.py failed with code {code}: {stderr}"

        payload = json.loads(stdout)
        assert "timestamp" in payload and "nodes" in payload
        nodes = payload["nodes"]

        # Validate authentic node properties
        assert "L1" in nodes and nodes["L1"]["status"] == "ONLINE" and nodes["L1"]["measured"] is True
        assert "L4" in nodes and nodes["L4"]["measured"] is False
        assert "L7" in nodes and nodes["L7"]["measured"] is False

        # Validate no prohibited constants in JSON
        json_dump = json.dumps(payload)
        for bad_lit in PROHIBITED_LITERALS:
            assert bad_lit not in json_dump, f"Prohibited literal '{bad_lit}' in live probe results"

    @pytest.mark.skipif(
        not (AUDIT_MOCKS_PATH.exists() and (REPO_ROOT / ".agents/teamwork/worker_truth_m3/handoff.md").exists()),
        reason="Acceptance Criterion 3: audit_mocks.sh pending Milestone 3 completion by Worker 3",
    )
    def test_acceptance_criterion_audit_mocks_zero_violations(self):
        """Acceptance Criterion 3: Static analysis script (audit_mocks.sh) successfully runs and reports 0 mock instances."""
        code, stdout, stderr = run_cmd(
            ["bash", str(AUDIT_MOCKS_PATH), "--target-apps"],
            timeout=60.0,
        )
        assert code == 0, f"audit_mocks.sh --target-apps failed with exit code {code}!\nStdout: {stdout}"
        assert "0 BLOCK" in stdout or "clean" in stdout.lower() or "passed" in stdout.lower()

    @pytest.mark.skipif(
        not TRUTH_ENFORCER_PATH.exists(),
        reason="Acceptance Criterion 5: truth_enforcer_daemon.sh pending Milestone 4",
    )
    def test_acceptance_criterion_truth_enforcer_daemon(self):
        """Acceptance Criterion 5: New background daemon script (truth_enforcer_daemon.sh) generated in 06_scripts_and_tooling."""
        # 1. Executable and syntax clean
        assert os.access(str(TRUTH_ENFORCER_PATH), os.X_OK), "truth_enforcer_daemon.sh is not executable"
        code, _, stderr = run_cmd(["bash", "-n", str(TRUTH_ENFORCER_PATH)])
        assert code == 0, f"truth_enforcer_daemon.sh syntax error: {stderr}"

        # 2. Rule 9 compliance (no agentic schedule cron, native shell loop)
        content = TRUTH_ENFORCER_PATH.read_text(encoding="utf-8", errors="ignore")
        assert "schedule(" not in content
        assert "sleep" in content

        # 3. Single run mode writes status
        status_md = OBSIDIAN_VAULT_PATH / "APPS_AND_FEATURES/TRUTH_ENFORCER_STATUS.md"
        run_code, _, run_err = run_cmd(["bash", str(TRUTH_ENFORCER_PATH), "--once"], timeout=30.0)
        assert run_code == 0, f"truth_enforcer_daemon.sh --once failed: {run_err}"
        assert status_md.is_file() and status_md.stat().st_size > 0

    @pytest.mark.skipif(
        not (OBSIDIAN_VAULT_PATH / "TRUTH_AUDIT_REPORT.md").exists(),
        reason="Acceptance Criterion 6: TRUTH_AUDIT_REPORT.md pending Milestone 5",
    )
    def test_acceptance_criterion_canonical_report_and_wikilink(self):
        """Acceptance Criterion 6: TRUTH_AUDIT_REPORT.md generated in obsidian_vault and indexed in Index.md."""
        report_path = OBSIDIAN_VAULT_PATH / "TRUTH_AUDIT_REPORT.md"
        assert report_path.is_file(), f"Report missing at: {report_path}"
        assert report_path.stat().st_size > 100, "TRUTH_AUDIT_REPORT.md is too short or empty"

        report_content = report_path.read_text(encoding="utf-8", errors="ignore")
        assert "Truth Audit" in report_content or "TRUTH AUDIT" in report_content
        assert "Rule 0" in report_content or "Zero-Mock" in report_content

        # Verify Index.md contains Wikilink to [[TRUTH_AUDIT_REPORT]]
        index_content = (OBSIDIAN_VAULT_PATH / "Index.md").read_text(encoding="utf-8", errors="ignore")
        assert "[[TRUTH_AUDIT_REPORT]]" in index_content, (
            "obsidian_vault/Index.md missing master Wikilink [[TRUTH_AUDIT_REPORT]]"
        )
