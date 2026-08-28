"""
tests/integration/test_cli.py
Integration tests for the canonical-sync CLI interface: verify, heal, sync, status, info.
Tests both direct function execution and real subprocess invocations.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict
import pytest

from canonical_sync_engine.cli.main import main


@pytest.fixture(autouse=True)
def setup_cli_env(mock_vault_sandbox: Dict[str, Path], monkeypatch):
    """Configures environment variables to redirect default vault paths to the sandbox."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(mock_vault_sandbox["obsidian"]))
    monkeypatch.setenv("PYSPARK_DATASET_PATH", str(mock_vault_sandbox["pyspark"]))
    monkeypatch.setenv("PYSPARK_MEMORY_PATH", str(mock_vault_sandbox["memory"]))
    monkeypatch.setenv("GIT_REPO_PATH", str(mock_vault_sandbox["git"]))
    monkeypatch.setenv("GDRIVE_MOUNT_PATH", str(mock_vault_sandbox["gdrive_mount"]))
    monkeypatch.setenv("GDRIVE_FALLBACK_PATH", str(mock_vault_sandbox["gdrive_cache"]))
    monkeypatch.setenv("CANONICAL_SYNC_MIN_HEADROOM_GB", "1.0")
    monkeypatch.setenv("CANONICAL_SYNC_ENV", "test")


def test_cli_main_no_args_shows_help(capsys):
    """Asserts that invoking main with no arguments prints help and returns 0."""
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage: canonical-sync" in captured.out or "usage: canonical-sync" in captured.err


def test_cli_version(capsys):
    """Asserts that --version prints the program version."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "canonical-sync" in captured.out or "canonical-sync" in captured.err


def test_cli_verify_healthy(capsys):
    """Asserts verify command passes on a healthy sandbox."""
    exit_code = main(["verify"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Storage Health Report: HEALTHY" in captured.out
    assert "Obsidian Vault: HEALTHY" in captured.out


def test_cli_verify_json(capsys):
    """Asserts verify --json outputs parseable JSON report."""
    exit_code = main(["verify", "--json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["is_healthy"] is True
    assert data["obsidian_healthy"] is True
    assert data["pyspark_healthy"] is True
    assert data["git_healthy"] is True
    assert data["gdrive_healthy"] is True


def test_cli_verify_full_scan(capsys):
    """Asserts verify --full performs remote mesh scanning."""
    exit_code = main(["verify", "--full", "--json"])
    captured = capsys.readouterr()
    assert exit_code in [0, 1]  # Remote nodes may be unreachable in sandbox
    data = json.loads(captured.out)
    assert "node_reports" in data
    assert len(data["node_reports"]) > 0


def test_cli_heal_command(mock_vault_sandbox: Dict[str, Path], capsys):
    """Asserts heal command executes pre-flight healing and reports actions."""
    # Induce missing index.md
    index_md = mock_vault_sandbox["obsidian"] / "Index.md"
    if index_md.exists():
        index_md.unlink()

    exit_code = main(["heal"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert index_md.exists()
    assert "Pre-Flight Self-Healing" in captured.out

    # Run again with --json
    exit_code_json = main(["heal", "--json"])
    captured_json = capsys.readouterr()
    assert exit_code_json == 0
    data = json.loads(captured_json.out)
    assert data["status"] == "success"
    assert "healed_actions" in data


def test_cli_sync_inline_json_payload(mock_vault_sandbox: Dict[str, Path], capsys):
    """Asserts sync command successfully ingests inline JSON and writes across 4 vaults."""
    payload_str = json.dumps({"test_key": "test_val", "score": 99.5})
    exit_code = main([
        "sync",
        "--type", "truth_audit",
        "--title", "CLI Sync Inline Test",
        "--payload", payload_str,
        "--source", "Mac_Node",
        "--tags", "cli,inline,test",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Overall Status:           SUCCESS" in captured.out
    assert "All 4 Vaults Succeeded:   True" in captured.out
    assert "[pyspark ] SUCCESS" in captured.out
    assert "[obsidian] SUCCESS" in captured.out
    assert "[git     ] SUCCESS" in captured.out
    assert "[gdrive  ] SUCCESS" in captured.out


def test_cli_sync_file_payload_with_at_prefix(tmp_path: Path, capsys):
    """Asserts sync command accepts '@filename' file references for payload."""
    payload_file = tmp_path / "custom_payload.json"
    payload_file.write_text(json.dumps({"experiment": "E1", "passed": True}), encoding="utf-8")

    exit_code = main([
        "sync",
        "--type", "ai_debate_consensus",
        "--title", "CLI Sync At-File Test",
        "--payload", f"@{payload_file}",
        "--id", "art-cli-at-file-001",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Overall Status:           SUCCESS" in captured.out
    assert "Artifact ID:              art-cli-at-file-001" in captured.out


def test_cli_sync_direct_filepath_payload(tmp_path: Path, capsys):
    """Asserts sync command accepts direct file paths without '@' prefix."""
    payload_file = tmp_path / "direct_payload.json"
    payload_file.write_text(json.dumps({"decision": "Approve", "quorum": 4}), encoding="utf-8")

    exit_code = main([
        "sync",
        "--type", "architectural_decision",
        "--title", "CLI Sync Direct File Test",
        "--payload", str(payload_file),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Overall Status:           SUCCESS" in captured.out


def test_cli_sync_json_output(capsys):
    """Asserts sync --json produces valid QuadVaultSyncResult JSON."""
    exit_code = main([
        "sync",
        "--type", "telemetry_record",
        "--title", "CLI Sync JSON Mode Test",
        "--payload", '{"cpu_pct": 12.5, "vram_mb": 4096}',
        "--json",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["success"] is True
    assert data["all_vaults_succeeded"] is True
    assert "vault_results" in data
    assert "pyspark" in data["vault_results"]
    assert "obsidian" in data["vault_results"]
    assert "git" in data["vault_results"]
    assert "gdrive" in data["vault_results"]


def test_cli_sync_invalid_type_failure(capsys):
    """Asserts invalid artifact type returns non-zero error."""
    exit_code = main([
        "sync",
        "--type", "invalid_type_name_xyz",
        "--title", "Should Fail",
        "--payload", '{"a": 1}',
    ])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid artifact type" in captured.err


def test_cli_sync_invalid_json_payload_failure(capsys):
    """Asserts invalid JSON string returns non-zero error."""
    exit_code = main([
        "sync",
        "--type", "truth_audit",
        "--title", "Bad JSON",
        "--payload", 'not valid json at all',
    ])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Failed to parse payload" in captured.err


def test_cli_sync_missing_payload_file_failure(capsys):
    """Asserts non-existent file reference with @ returns non-zero error."""
    exit_code = main([
        "sync",
        "--type", "truth_audit",
        "--title", "Missing File",
        "--payload", "@non_existent_path_file_9999.json",
    ])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Failed to parse payload" in captured.err


def test_cli_status_human_and_json(capsys):
    """Asserts status subcommand outputs valid human and JSON overviews."""
    # Human-readable
    exit_code = main(["status"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Canonical Storage Status" in captured.out
    assert "Quad-Vault Status:" in captured.out

    # JSON mode
    exit_code_json = main(["status", "--json"])
    captured_json = capsys.readouterr()
    assert exit_code_json == 0
    data = json.loads(captured_json.out)
    assert "fast_path_healthy" in data
    assert "disk_free_gb" in data
    assert "vaults" in data
    assert "pyspark" in data["vaults"]


def test_cli_info_human_and_json(capsys):
    """Asserts info subcommand outputs configuration and mesh node lists."""
    # Human-readable
    exit_code = main(["info"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Canonical Sync Engine Configuration" in captured.out
    assert "Vault Paths:" in captured.out
    assert "Mesh Nodes Configured:" in captured.out

    # JSON mode
    exit_code_json = main(["info", "--json"])
    captured_json = capsys.readouterr()
    assert exit_code_json == 0
    data = json.loads(captured_json.out)
    assert "obsidian_vault_path" in data
    assert "pyspark_dataset_path" in data
    assert "mesh_nodes" in data


def test_cli_subprocess_invocation(mock_vault_sandbox: Dict[str, Path]):
    """
    Asserts CLI can be invoked as a real subprocess via `python3 -m canonical_sync_engine.cli.main`.
    """
    env = os.environ.copy()
    env["OBSIDIAN_VAULT_PATH"] = str(mock_vault_sandbox["obsidian"])
    env["PYSPARK_DATASET_PATH"] = str(mock_vault_sandbox["pyspark"])
    env["PYSPARK_MEMORY_PATH"] = str(mock_vault_sandbox["memory"])
    env["GIT_REPO_PATH"] = str(mock_vault_sandbox["git"])
    env["GDRIVE_MOUNT_PATH"] = str(mock_vault_sandbox["gdrive_mount"])
    env["GDRIVE_FALLBACK_PATH"] = str(mock_vault_sandbox["gdrive_cache"])
    env["CANONICAL_SYNC_MIN_HEADROOM_GB"] = "1.0"
    env["CANONICAL_SYNC_ENV"] = "test"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent.parent)

    # 1. Test status --json via subprocess
    proc_status = subprocess.run(
        [sys.executable, "-m", "canonical_sync_engine.cli.main", "status", "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert proc_status.returncode == 0
    status_data = json.loads(proc_status.stdout)
    assert status_data["fast_path_healthy"] is True

    # 2. Test sync --json via subprocess
    proc_sync = subprocess.run(
        [
            sys.executable,
            "-m",
            "canonical_sync_engine.cli.main",
            "sync",
            "--type", "truth_audit",
            "--title", "Subprocess E2E CLI Sync",
            "--payload", '{"subprocess_key": "sub_value", "success": true}',
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert proc_sync.returncode == 0
    sync_data = json.loads(proc_sync.stdout)
    assert sync_data["success"] is True
    assert sync_data["all_vaults_succeeded"] is True
