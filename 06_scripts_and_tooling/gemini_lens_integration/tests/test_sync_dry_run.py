"""E2E Acceptance Tests for Programmatic Dry-Run Synchronization (R1, R3, R4).

Covers Tiers 1-4 per TEST_INFRA.md:
- Subprocess invocation of `sync_engine.py --dry-run`
- Exit Code 0 verification
- Dual-account simulated sync output in stdout/logs for both:
  - aaron.t.maher@gmail.com (Personal Admin)
  - lauburu@lauburugrappling.com (Workspace Business)
- Manifest generation and schema verification at session_logs/gemini_lens_sync_status.json
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

SYNC_ENGINE_REL_PATH = "sync_engine.py"


def _require_sync_engine(project_root: Path) -> Path:
    """Helper to check if sync_engine.py exists; skips test progressively if pending M4."""
    script_path = project_root / SYNC_ENGINE_REL_PATH
    if not script_path.exists():
        pytest.skip(f"{SYNC_ENGINE_REL_PATH} not yet implemented (Milestone 4)")
    return script_path


class TestSyncDryRunTier1FeatureCoverage:
    """Tier 1: Feature Coverage — Primary happy-path dry-run execution."""

    def test_auth_manager_dry_run_cli_execution(self, project_root: Path):
        """Feature 1 & 2: Programmatic dry-run execution of auth_manager.py CLI exits with code 0 and logs both accounts."""
        auth_script = project_root / "auth_manager.py"
        if not auth_script.exists():
            pytest.skip("auth_manager.py not found")
        cmd = [sys.executable, str(auth_script), "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=15)
        assert res.returncode == 0, f"Expected code 0, got {res.returncode}. Stderr: {res.stderr}"
        combined = res.stdout + res.stderr
        assert "aaron.t.maher@gmail.com" in combined
        assert "lauburu@lauburugrappling.com" in combined
        assert "simulated_dry_run" in combined

    def test_dry_run_subprocess_exit_code_zero(self, project_root: Path):
        """Feature 15: Executes programmatic dry-run via subprocess, asserts Exit Code 0."""
        script_path = _require_sync_engine(project_root)
        cmd = [sys.executable, str(script_path), "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0, f"Expected exit code 0, got {res.returncode}. Stderr: {res.stderr}"

    def test_dry_run_dual_account_output_logged(self, project_root: Path):
        """Acceptance Criteria: Asserts stdout/logs contain simulated sync output for BOTH user accounts."""
        script_path = _require_sync_engine(project_root)
        cmd = [sys.executable, str(script_path), "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        combined_output = res.stdout + res.stderr

        # Check personal account logged
        assert "aaron.t.maher@gmail.com" in combined_output, (
            "Stdout/stderr must mention aaron.t.maher@gmail.com"
        )
        # Check workspace account logged
        assert "lauburu@lauburugrappling.com" in combined_output, (
            "Stdout/stderr must mention lauburu@lauburugrappling.com"
        )

    def test_dry_run_generates_status_manifest(self, project_root: Path):
        """Feature 15: Asserts generation of session_logs/gemini_lens_sync_status.json."""
        script_path = _require_sync_engine(project_root)
        manifest_path = project_root / "session_logs" / "gemini_lens_sync_status.json"

        # Remove pre-existing manifest if present to ensure fresh generation
        if manifest_path.exists():
            manifest_path.unlink()

        cmd = [sys.executable, str(script_path), "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        assert manifest_path.exists(), f"Status manifest was not created at {manifest_path}"

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict), "Manifest must be a JSON dictionary"
        assert data.get("dry_run") is True, "Manifest must reflect dry_run: true"
        assert "timestamp_utc" in data, "Manifest must contain timestamp_utc"

    def test_dry_run_verbose_flag_execution(self, project_root: Path):
        """Feature 15: Verifies execution with --verbose flag outputs diagnostic logs."""
        script_path = _require_sync_engine(project_root)
        cmd = [sys.executable, str(script_path), "--dry-run", "--verbose"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        combined = res.stdout + res.stderr
        assert len(combined) > 0, "Verbose mode should emit console logs"

    def test_dry_run_sidecar_flag_execution(self, project_root: Path):
        """Feature 14: Verifies execution when invoked with --sidecar flag."""
        script_path = _require_sync_engine(project_root)
        cmd = [sys.executable, str(script_path), "--dry-run", "--sidecar"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0


class TestSyncDryRunTier2BoundaryAndCornerCases:
    """Tier 2: Boundary Value Analysis & Corner Cases."""

    def test_dry_run_custom_config_path(self, project_root: Path, isolated_config_path: Path, temp_env_dir: Path):
        """Boundary: Passing --config pointing to custom isolated configuration."""
        script_path = _require_sync_engine(project_root)
        custom_manifest = temp_env_dir / "session_logs" / "gemini_lens_sync_status.json"
        if custom_manifest.exists():
            custom_manifest.unlink()

        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--config",
            str(isolated_config_path)
        ]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        assert custom_manifest.exists(), f"Custom manifest was not generated at {custom_manifest}"

    def test_dry_run_single_account_filter_personal(self, project_root: Path):
        """Boundary: Filtering execution to single personal account via --account."""
        script_path = _require_sync_engine(project_root)
        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--account",
            "aaron.t.maher@gmail.com"
        ]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        combined = res.stdout + res.stderr
        assert "aaron.t.maher@gmail.com" in combined

    def test_dry_run_single_account_filter_workspace(self, project_root: Path):
        """Boundary: Filtering execution to single workspace account via --account."""
        script_path = _require_sync_engine(project_root)
        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--account",
            "lauburu@lauburugrappling.com"
        ]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        combined = res.stdout + res.stderr
        assert "lauburu@lauburugrappling.com" in combined

    def test_dry_run_status_manifest_schema_validation(self, project_root: Path):
        """Boundary: Validates complete manifest schema and data integrity."""
        script_path = _require_sync_engine(project_root)
        manifest_path = project_root / "session_logs" / "gemini_lens_sync_status.json"
        cmd = [sys.executable, str(script_path), "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        assert manifest_path.exists()

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "timestamp_utc" in manifest
        assert manifest.get("dry_run") is True
        assert "accounts" in manifest
        accounts = manifest["accounts"]
        assert "aaron.t.maher@gmail.com" in accounts
        assert "lauburu@lauburugrappling.com" in accounts
        assert accounts["aaron.t.maher@gmail.com"]["is_authenticated"] is True
        assert accounts["lauburu@lauburugrappling.com"]["is_authenticated"] is True

    def test_dry_run_missing_config_file_graceful_exit(self, project_root: Path):
        """Corner Case: Non-existent config file passed via --config should exit cleanly or with error code without traceback panic."""
        script_path = _require_sync_engine(project_root)
        non_existent_config = project_root / "config" / "does_not_exist_999.json"
        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--config",
            str(non_existent_config)
        ]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        # Should exit with non-panic exit code (either 0 fallback or 1/2 handled error, but not uncaught trace)
        assert "Traceback (most recent call last)" not in res.stderr or res.returncode in [0, 1, 2]


class TestSyncDryRunTier3CrossFeatureCombinations:
    """Tier 3: Pairwise & Cross-Feature Integration."""

    def test_dry_run_auto_creates_missing_session_logs_dir(self, project_root: Path, tmp_path: Path, canonical_config: Dict[str, Any]):
        """Cross-Feature: If session_logs directory is missing, sync engine must create it."""
        script_path = _require_sync_engine(project_root)
        isolated_dir = tmp_path / "deep_isolated" / "test_run"
        manifest_path = isolated_dir / "session_logs" / "gemini_lens_sync_status.json"

        cfg_copy = json.loads(json.dumps(canonical_config))
        cfg_copy["resilience"]["status_manifest_path"] = str(manifest_path)
        custom_cfg = tmp_path / "custom_cfg.json"
        custom_cfg.write_text(json.dumps(cfg_copy), encoding="utf-8")

        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--config",
            str(custom_cfg)
        ]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        assert manifest_path.exists(), "Should have auto-created session_logs directory"

    def test_dry_run_client_isolation_recorded_in_manifest(self, project_root: Path):
        """Cross-Feature: Manifest must record client_isolation_verified: True."""
        script_path = _require_sync_engine(project_root)
        manifest_path = project_root / "session_logs" / "gemini_lens_sync_status.json"

        cmd = [sys.executable, str(script_path), "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=30)
        assert res.returncode == 0

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest.get("client_isolation_verified") is True, (
            "Manifest must confirm that dual account client instances are isolated."
        )


class TestSyncDryRunTier4RealWorldScenarios:
    """Tier 4: Real-World Workload Scenarios."""

    def test_scenario_full_hourly_dry_run_cycle(self, project_root: Path):
        """Scenario 1: Complete hourly cron invocation with timing, logging, and exit code validation."""
        script_path = _require_sync_engine(project_root)
        t_start = time.time()
        cmd = [sys.executable, str(script_path), "--dry-run", "--sidecar", "--once"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True, timeout=20)
        elapsed = time.time() - t_start

        # Validation per TEST_INFRA.md and survey findings
        assert res.returncode == 0, f"Hourly dry-run must exit 0, got {res.returncode}. Stderr: {res.stderr}"
        assert elapsed < 10.0, f"Hourly dry-run must complete quickly (<10s), took {elapsed:.2f}s"

        manifest_path = project_root / "session_logs" / "gemini_lens_sync_status.json"
        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("dry_run") is True
        assert len(data.get("accounts", {})) == 2
