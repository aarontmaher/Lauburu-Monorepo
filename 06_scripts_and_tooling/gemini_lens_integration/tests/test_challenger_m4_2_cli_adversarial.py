"""Empirical Adversarial Stress Test Suite for Milestone 4 (sync_engine.py & CLI).

Authored by challenger_m4_it2_2 (Milestone 4 Iteration 2 Challenger 2:
Live Mode Mutation Gating, CLI Corner Cases, Execution Timing, and Concurrency).

Evaluates:
1. Challenge 1: Live mode unauthenticated account gating (--account invalid_email@domain.com).
   - Asserts exit code 1.
   - Asserts failure manifest generated and schema valid.
   - Asserts 0 target notebook files or IDE metadata modified/created on disk.
2. Challenge 2: CLI subprocess boundary & corner cases.
   - Non-existent config paths (--config).
   - Corrupted JSON config files.
   - Invalid unrecognized CLI flags.
   - Empty string arguments.
   - Corrupted notebook files.
   - Non-existent notebook and options directory paths.
   - Multi-flag combinations (--dry-run, --sidecar, --once, --verbose).
3. Challenge 3: Execution timing.
   - Verifies hourly dry-run cycle completes in strictly < 10.0 seconds.
   - Verifies sidecar hourly mode completes in strictly < 10.0 seconds.
4. Challenge 4: High-concurrency subprocess dry-runs (20+ concurrent processes).
   - Spawns 25 simultaneous subprocesses executing sync_engine.py --dry-run.
   - Asserts 100% exit code 0, 100% valid JSON manifests, zero manifest corruption.
   - Spawns 20 concurrent mixed account-filtered subprocesses.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent.parent
SYNC_ENGINE_PATH = PROJECT_ROOT / "sync_engine.py"
PYTHON_EXE = sys.executable


def _compute_file_sha256(path: Path) -> str:
    """Computes SHA256 checksum of a file on disk."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# Challenge 1: Live Mode Unauthenticated Account Gating & Zero Disk Mutation
# =============================================================================

class TestChallenge1LiveUnauthenticatedAccounts:
    """Challenge 1: Assert live mode unauthenticated account fails safely with zero disk mutation."""

    def test_live_mode_invalid_email_exit_code_and_failure_manifest(self):
        """Asserts --account invalid_email@domain.com exits 1 and emits failure manifest."""
        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--account",
            "invalid_email@domain.com",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # 1. Exit code must strictly be 1
        assert res.returncode == 1, (
            f"Expected exit code 1 for unauthenticated live run, got {res.returncode}. "
            f"Stdout: {res.stdout}, Stderr: {res.stderr}"
        )

        # 2. Stderr must warn about unauthenticated accounts
        assert "No target accounts could be authenticated" in res.stderr

        # 3. Stdout must contain valid parseable JSON manifest
        try:
            manifest = json.loads(res.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Stdout did not contain valid JSON: {exc}. Raw stdout: {res.stdout}")

        assert isinstance(manifest, dict)
        assert manifest.get("dry_run") is False
        assert manifest.get("authenticated_accounts") == 0
        assert manifest.get("total_accounts") == 2

        # 4. Assert notebook_sync was completely bypassed
        nb_sync = manifest.get("notebook_sync", {})
        assert nb_sync.get("status") == "auth_failed"
        assert nb_sync.get("cell_action") == "bypassed_auth_failed"
        assert nb_sync.get("notebook_modified") is False
        assert nb_sync.get("metadata_modified") is False
        assert "error" in nb_sync

        # 5. Assert account details in manifest
        accts = manifest.get("accounts", {})
        assert "invalid_email@domain.com" in accts
        invalid_acct = accts["invalid_email@domain.com"]
        assert invalid_acct.get("is_authenticated") is False
        assert invalid_acct.get("auth_method") == "none"

    def test_live_mode_unauthenticated_zero_disk_mutation_production_notebook(self):
        """Asserts zero bytes created or modified on production notebook during invalid live run."""
        prod_notebook = REPO_ROOT / "lens_global_orchestrator.ipynb"
        assert prod_notebook.exists(), f"Production notebook not found at {prod_notebook}"

        sha_before = _compute_file_sha256(prod_notebook)
        size_before = prod_notebook.stat().st_size
        mtime_before = prod_notebook.stat().st_mtime

        meta_path = REPO_ROOT / ".idea" / "lens_context.json"
        meta_sha_before = _compute_file_sha256(meta_path) if meta_path.exists() else None

        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--account",
            "fake_intruder@attacker.com",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert res.returncode == 1

        # Check notebook integrity
        sha_after = _compute_file_sha256(prod_notebook)
        size_after = prod_notebook.stat().st_size
        mtime_after = prod_notebook.stat().st_mtime

        assert sha_after == sha_before, "Production notebook SHA256 was mutated!"
        assert size_after == size_before, "Production notebook size was modified!"
        assert mtime_after == mtime_before, "Production notebook mtime was modified!"

        # Check .idea metadata integrity
        if meta_sha_before is not None:
            meta_sha_after = _compute_file_sha256(meta_path)
            assert meta_sha_after == meta_sha_before, "IDE metadata was modified!"

    def test_live_mode_unauthenticated_isolated_environment_zero_mutation(self, tmp_path: Path):
        """Asserts zero mutations to isolated target notebook and metadata paths."""
        isolated_nb = tmp_path / "test_orchestrator.ipynb"
        isolated_meta = tmp_path / ".idea" / "lens_context.json"
        isolated_meta.parent.mkdir(parents=True, exist_ok=True)

        # Create clean target notebook
        nb_data = {
            "cells": [
                {"cell_type": "markdown", "metadata": {}, "source": ["# Test Header\n"]}
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        with open(isolated_nb, "w", encoding="utf-8") as f:
            json.dump(nb_data, f, indent=2)

        nb_sha_before = _compute_file_sha256(isolated_nb)

        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--account",
            "unauthorized@unauthenticated.net",
            "--notebook",
            str(isolated_nb),
            "--metadata",
            str(isolated_meta),
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert res.returncode == 1

        # Assert isolated notebook was NOT touched
        nb_sha_after = _compute_file_sha256(isolated_nb)
        assert nb_sha_after == nb_sha_before

        # Assert isolated metadata file was NOT created
        assert not isolated_meta.exists()

    def test_live_mode_multiple_nonexistent_accounts_fail_safe(self):
        """Asserts various arbitrary invalid emails fail safely with exit code 1."""
        test_emails = [
            "nobody@domain.invalid",
            "admin@notreal.org",
            "random_user_12345@corp.local",
        ]
        for email in test_emails:
            cmd = [PYTHON_EXE, str(SYNC_ENGINE_PATH), "--account", email]
            res = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert res.returncode == 1
            manifest = json.loads(res.stdout)
            assert manifest["authenticated_accounts"] == 0
            assert manifest["notebook_sync"]["status"] == "auth_failed"


# =============================================================================
# Challenge 2: CLI Subprocess Boundary & Corner Cases
# =============================================================================

class TestChallenge2CLIBoundaryAndCornerCases:
    """Challenge 2: Assert robust handling of CLI boundary conditions and corrupt files."""

    def test_cli_nonexistent_config_path(self):
        """Asserts non-existent config path causes graceful exit with code 1."""
        nonexistent_path = "/tmp/nonexistent_gemini_lens_config_982341.json"
        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--config",
            nonexistent_path,
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 1
        assert "Configuration file not found" in res.stderr
        # Must not crash with an uncaught Python traceback on stdout
        assert "Traceback" not in res.stdout

    def test_cli_corrupted_json_config(self, tmp_path: Path):
        """Asserts corrupted JSON config file is handled gracefully with exit code 1."""
        corrupt_cfg = tmp_path / "corrupt_config.json"
        corrupt_cfg.write_text("{\n  \"resilience\": [unclosed bracket and bad syntax", encoding="utf-8")

        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--config",
            str(corrupt_cfg),
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 1
        assert "Fatal error" in res.stderr or "JSONDecodeError" in res.stderr

    def test_cli_invalid_unrecognized_argument(self):
        """Asserts invalid unrecognized CLI flag causes argparse exit code 2."""
        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--completely-bogus-unsupported-flag-xyz",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 2
        assert "unrecognized arguments" in res.stderr

    def test_cli_empty_string_account_flag(self, tmp_path: Path):
        """Vulnerability Audit: Passing empty string --account '' in live mode must not bypass filtering.

        Expected: Exits 1 (since empty string is not a valid authenticated account) and zero mutations.
        Actual (Vulnerability): 'if account_filter:' evaluates '' as falsy, falling back to all active accounts,
        authenticating them live, mutating target notebook, and returning exit code 0.
        """
        isolated_nb = tmp_path / "test_orchestrator.ipynb"
        isolated_meta = tmp_path / "lens_context.json"
        isolated_nb.write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}', encoding="utf-8")
        sha_before = _compute_file_sha256(isolated_nb)

        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--account",
            "",
            "--notebook",
            str(isolated_nb),
            "--metadata",
            str(isolated_meta),
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Expected secure behavior: Empty account filter should fail authentication and exit 1
        assert res.returncode == 1, (
            f"VULNERABILITY CONFIRMED: --account '' bypassed filter, exited 0, and mutated disk!\n"
            f"Stdout: {res.stdout}\nStderr: {res.stderr}"
        )
        assert _compute_file_sha256(isolated_nb) == sha_before, (
            "VULNERABILITY CONFIRMED: Notebook was mutated when --account '' was passed!"
        )

    def test_cli_whitespace_account_flag(self, tmp_path: Path):
        """Asserts whitespace-only --account '   ' exits 1 with zero disk mutations."""
        isolated_nb = tmp_path / "test_orchestrator.ipynb"
        isolated_meta = tmp_path / "lens_context.json"
        isolated_nb.write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}', encoding="utf-8")
        sha_before = _compute_file_sha256(isolated_nb)

        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--account",
            "   ",
            "--notebook",
            str(isolated_nb),
            "--metadata",
            str(isolated_meta),
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 1, (
            f"Expected exit code 1 for whitespace --account '   ', got {res.returncode}."
        )
        assert "Error: --account cannot be empty" in res.stderr
        assert _compute_file_sha256(isolated_nb) == sha_before, (
            "Notebook was mutated when whitespace --account was passed!"
        )
        assert not isolated_meta.exists(), "Metadata file was created on whitespace account!"

    def test_cli_corrupted_notebook_file_dry_run(self, tmp_path: Path):
        """Asserts corrupted notebook file during dry-run is handled without uncaught crash."""
        corrupt_nb = tmp_path / "corrupted.ipynb"
        corrupt_nb.write_text("THIS IS NOT JSON AT ALL @#$%^&*", encoding="utf-8")

        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--dry-run",
            "--notebook",
            str(corrupt_nb),
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Dry-run should complete cleanly and return valid JSON
        assert res.returncode == 0
        manifest = json.loads(res.stdout)
        assert manifest["dry_run"] is True
        assert manifest["authenticated_accounts"] == 2

    def test_cli_nonexistent_notebook_path_dry_run(self):
        """Asserts non-existent notebook path in dry-run completes gracefully."""
        bogus_nb = "/tmp/does_not_exist_notebook_776655.ipynb"
        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--dry-run",
            "--notebook",
            bogus_nb,
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0
        manifest = json.loads(res.stdout)
        assert manifest["dry_run"] is True

    def test_cli_nonexistent_options_dir_dry_run(self):
        """Asserts non-existent options directory in dry-run completes gracefully."""
        bogus_opts = "/tmp/does_not_exist_options_dir_443322"
        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--dry-run",
            "--options-dir",
            bogus_opts,
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0
        manifest = json.loads(res.stdout)
        assert manifest["dry_run"] is True

    def test_cli_multi_flag_combinations_dry_run(self):
        """Asserts complex multi-flag combinations execute deterministically."""
        cmd = [
            PYTHON_EXE,
            str(SYNC_ENGINE_PATH),
            "--dry-run",
            "--sidecar",
            "--once",
            "--verbose",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0
        manifest = json.loads(res.stdout)
        assert manifest["dry_run"] is True
        assert manifest["mode"] == "sidecar"
        assert manifest["authenticated_accounts"] == 2


# =============================================================================
# Challenge 3: Execution Timing (< 10.0 Seconds)
# =============================================================================

class TestChallenge3ExecutionTiming:
    """Challenge 3: Assert hourly dry-run cycle completes in strictly < 10.0 seconds."""

    def test_hourly_dry_run_cycle_timing_under_ten_seconds(self):
        """Measures execution duration over 5 sequential runs; asserts all < 10.0s."""
        durations: List[float] = []

        for i in range(5):
            t0 = time.perf_counter()
            res = subprocess.run(
                [PYTHON_EXE, str(SYNC_ENGINE_PATH), "--dry-run"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=15,
            )
            elapsed = time.perf_counter() - t0
            durations.append(elapsed)

            assert res.returncode == 0, f"Run {i} failed: {res.stderr}"
            assert elapsed < 10.0, f"Run {i} took {elapsed:.3f}s (exceeded 10.0s ceiling!)"

            manifest = json.loads(res.stdout)
            internal_elapsed = manifest.get("execution_time_seconds", 0.0)
            assert internal_elapsed < 10.0

        max_dur = max(durations)
        min_dur = min(durations)
        avg_dur = sum(durations) / len(durations)

        # Strict assertion against required 10.0s ceiling
        assert max_dur < 10.0, f"Max duration {max_dur:.3f}s exceeded 10.0s"
        # Typical execution should be well under 2.0s
        assert avg_dur < 3.0, f"Average execution duration {avg_dur:.3f}s is abnormally slow"

    def test_sidecar_hourly_mode_timing_under_ten_seconds(self):
        """Asserts --sidecar --once --dry-run completes in < 10.0 seconds."""
        t0 = time.perf_counter()
        res = subprocess.run(
            [PYTHON_EXE, str(SYNC_ENGINE_PATH), "--dry-run", "--sidecar", "--once"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        elapsed = time.perf_counter() - t0

        assert res.returncode == 0
        assert elapsed < 10.0, f"Hourly sidecar dry run took {elapsed:.3f}s (exceeded 10.0s)"

        manifest = json.loads(res.stdout)
        assert manifest["execution_time_seconds"] < 10.0


# =============================================================================
# Challenge 4: High-Concurrency Subprocess Dry-Runs (20+ Processes)
# =============================================================================

class TestChallenge4ConcurrentDryRuns:
    """Challenge 4: Assert 20+ concurrent subprocess dry-runs execute without deadlocks or corruption."""

    def test_concurrent_twenty_plus_subprocess_dry_runs(self):
        """Launches 25 concurrent subprocesses; asserts all exit 0, emit valid JSON, and leave manifest intact."""
        num_concurrent = 25
        manifest_file = PROJECT_ROOT / "session_logs" / "gemini_lens_sync_status.json"

        def _run_dry_run_subprocess(proc_id: int) -> Tuple[int, int, str, str, float]:
            t0 = time.perf_counter()
            cmd = [PYTHON_EXE, str(SYNC_ENGINE_PATH), "--dry-run"]
            res = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            elapsed = time.perf_counter() - t0
            return proc_id, res.returncode, res.stdout, res.stderr, elapsed

        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(_run_dry_run_subprocess, i)
                for i in range(num_concurrent)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        total_wall_clock = time.perf_counter() - t_start

        # 1. Assert all 25 returned exit code 0
        for proc_id, code, stdout, stderr, dur in results:
            assert code == 0, (
                f"Subprocess #{proc_id} failed with exit code {code}.\n"
                f"Stderr: {stderr}\nStdout: {stdout}"
            )
            assert dur < 15.0, f"Subprocess #{proc_id} took {dur:.2f}s"

            # 2. Assert each stdout is valid parseable JSON manifest
            try:
                manifest_out = json.loads(stdout)
            except json.JSONDecodeError as exc:
                pytest.fail(f"Subprocess #{proc_id} stdout was not valid JSON: {exc}\n{stdout}")

            assert manifest_out.get("dry_run") is True
            assert manifest_out.get("authenticated_accounts") == 2
            assert manifest_out.get("client_isolation_verified") is True

        # 3. Assert on-disk status manifest is valid parseable JSON (no corruption from atomic replaces)
        assert manifest_file.exists(), f"Manifest file missing at {manifest_file}"
        with open(manifest_file, "r", encoding="utf-8") as f:
            disk_manifest = json.load(f)

        assert isinstance(disk_manifest, dict)
        assert disk_manifest.get("dry_run") is True
        assert disk_manifest.get("authenticated_accounts") == 2

        # 4. Assert total wall-clock time for all 25 concurrent executions is reasonable
        assert total_wall_clock < 20.0, (
            f"All {num_concurrent} concurrent processes took {total_wall_clock:.2f}s (too slow)"
        )

    def test_concurrent_mixed_filtered_dry_runs(self):
        """Launches 20 concurrent subprocesses with mixed account filters."""
        tasks: List[Tuple[int, Optional[str]]] = []
        for i in range(10):
            tasks.append((i, "aaron.t.maher@gmail.com"))
        for i in range(10, 20):
            tasks.append((i, "lauburu@lauburugrappling.com"))

        def _run_filtered(proc_id: int, acct: Optional[str]) -> Tuple[int, int, str, str]:
            cmd = [PYTHON_EXE, str(SYNC_ENGINE_PATH), "--dry-run"]
            if acct:
                cmd.extend(["--account", acct])
            res = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return proc_id, res.returncode, res.stdout, res.stderr

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_run_filtered, pid, acct) for pid, acct in tasks]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for pid, code, stdout, stderr in results:
            assert code == 0, f"Filtered process #{pid} failed with code {code}. Stderr: {stderr}"
            manifest = json.loads(stdout)
            assert manifest["dry_run"] is True
            assert manifest["authenticated_accounts"] == 1
