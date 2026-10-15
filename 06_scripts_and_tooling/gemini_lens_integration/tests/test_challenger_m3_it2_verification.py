"""Empirical Challenge & Verification Suite for Milestone 3 Remediation (Iteration 2).

Authored by challenger_m3_it2_2 (teamwork_preview_challenger).
Empirical verification of:
1. Adverse payload challenge:
   - All entrypoints (sync_notebook, sync_ide_metadata, sync_notebook_and_ide)
   - Across payloads: None, "", 123, {"screen_lens": None}, {"accounts": None}, {"accounts": [None]}, {"ide_context": None}
   - Assert zero unhandled exceptions (0 crashes) across all executions for dry_run=True and dry_run=False.
2. Zero-mock literal verification:
   - Unpopulated payload produces:
     - mesh_health.healthy_services is None
     - spark_status is None
     - workspace_id is None
     - cell source contains "'mesh_health': '--'"
   - Zero occurrences of "10/14" or "3KVuyxqTNZxKVuAAf4tq3bxSOYz" in runtime output or written files.
3. Concurrency verification:
   - Run tests/test_challenger_m3_stress.py to confirm 50+ concurrent threads maintain atomic integrity.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notebook_sync import NotebookSynchronizer


ADVERSE_PAYLOADS = [
    ("none_payload", None),
    ("empty_string_payload", ""),
    ("integer_payload", 123),
    ("screen_lens_none", {"screen_lens": None}),
    ("accounts_none", {"accounts": None}),
    ("accounts_list_with_none", {"accounts": [None]}),
    ("ide_context_none", {"ide_context": None}),
    # Additional adversarial stress payloads
    ("empty_dict_payload", {}),
    ("list_payload", [1, 2, 3]),
    ("float_payload", 3.14159),
    ("screen_lens_string", {"screen_lens": "malformed_string"}),
    ("accounts_mixed_corrupted", {"accounts": [None, 999, "", {}, {"email": None}, {"email": "test@domain.com"}]}),
    ("ide_context_string", {"ide_context": "corrupted_ide_string"}),
    ("mesh_health_none", {"mesh_health": None}),
    ("mesh_health_non_dict", {"mesh_health": 42}),
]


@pytest.fixture
def isolated_sync_env(tmp_path: Path):
    """Provides an isolated environment with fresh notebook and metadata paths."""
    env_dir = tmp_path / "it2_challenger_env"
    env_dir.mkdir(parents=True, exist_ok=True)
    nb_path = env_dir / "lens_global_orchestrator.ipynb"
    idea_dir = env_dir / ".idea"
    idea_dir.mkdir(parents=True, exist_ok=True)
    meta_path = idea_dir / "lens_context.json"
    options_dir = env_dir / "options"
    options_dir.mkdir(parents=True, exist_ok=True)
    try:
        sync = NotebookSynchronizer(
            repo_root=env_dir,
            notebook_path=nb_path,
            metadata_path=meta_path,
            options_dir=options_dir,
        )
    except TypeError:
        sync = NotebookSynchronizer(
            repo_root=env_dir,
            notebook_path=nb_path,
            metadata_path=meta_path,
        )
        sync.options_dir = options_dir
    # Isolate from live host PyCharm port
    sync.pycharm_port = 63399
    return {
        "env_dir": env_dir,
        "nb_path": nb_path,
        "meta_path": meta_path,
        "options_dir": options_dir,
        "sync": sync,
    }


class TestAdversePayloadChallenge:
    """Challenge 1: Adverse payload execution against all entrypoints with 0 crashes."""

    @pytest.mark.parametrize("case_name,payload", ADVERSE_PAYLOADS)
    def test_sync_notebook_adverse_payload_dry_run(self, isolated_sync_env, case_name: str, payload: Any):
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook(payload=payload, dry_run=True)
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("dry_run") is True

    @pytest.mark.parametrize("case_name,payload", ADVERSE_PAYLOADS)
    def test_sync_notebook_adverse_payload_disk_write(self, isolated_sync_env, case_name: str, payload: Any):
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook(payload=payload, dry_run=False)
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("dry_run") is False
        assert isolated_sync_env["nb_path"].exists()
        # Verify notebook is valid JSON
        with open(isolated_sync_env["nb_path"], "r", encoding="utf-8") as f:
            nb_json = json.load(f)
        assert "cells" in nb_json
        assert len(nb_json["cells"]) >= 2

    @pytest.mark.parametrize("case_name,payload", ADVERSE_PAYLOADS)
    def test_sync_ide_metadata_adverse_payload_dry_run(self, isolated_sync_env, case_name: str, payload: Any):
        sync = isolated_sync_env["sync"]
        res = sync.sync_ide_metadata(payload=payload, dry_run=True)
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("dry_run") is True

    @pytest.mark.parametrize("case_name,payload", ADVERSE_PAYLOADS)
    def test_sync_ide_metadata_adverse_payload_disk_write(self, isolated_sync_env, case_name: str, payload: Any):
        sync = isolated_sync_env["sync"]
        res = sync.sync_ide_metadata(payload=payload, dry_run=False)
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("dry_run") is False
        assert isolated_sync_env["meta_path"].exists()
        # Verify metadata is valid JSON
        with open(isolated_sync_env["meta_path"], "r", encoding="utf-8") as f:
            meta_json = json.load(f)
        assert meta_json.get("status") == "IN_SYNC"

    @pytest.mark.parametrize("case_name,payload", ADVERSE_PAYLOADS)
    def test_sync_notebook_and_ide_adverse_payload_dry_run(self, isolated_sync_env, case_name: str, payload: Any):
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook_and_ide(payload=payload, dry_run=True)
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("dry_run") is True
        assert res["notebook"]["status"] == "success"
        assert res["ide_metadata"]["status"] == "success"

    @pytest.mark.parametrize("case_name,payload", ADVERSE_PAYLOADS)
    def test_sync_notebook_and_ide_adverse_payload_disk_write(self, isolated_sync_env, case_name: str, payload: Any):
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook_and_ide(payload=payload, dry_run=False)
        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert res.get("dry_run") is False
        assert isolated_sync_env["nb_path"].exists()
        assert isolated_sync_env["meta_path"].exists()


class TestZeroMockLiteralVerification:
    """Challenge 2: Zero-mock literal verification and absence of synthetic strings."""

    def test_unpopulated_payload_sync_ide_metadata(self, isolated_sync_env):
        """Verify unpopulated payload produces mesh_health.healthy_services is None,

        spark_status is None, workspace_id is None, and zero occurrences of '10/14' or '3KVuyxqTNZxKVuAAf4tq3bxSOYz'.
        """
        sync = isolated_sync_env["sync"]
        res = sync.sync_ide_metadata(payload={}, dry_run=True)
        meta_payload = res["payload"]
        mesh_health = meta_payload.get("mesh_health", {})

        assert mesh_health.get("healthy_services") is None, (
            f"Expected mesh_health.healthy_services to be None, got {mesh_health.get('healthy_services')}"
        )
        assert meta_payload.get("spark_status") is None, (
            f"Expected spark_status to be None, got {meta_payload.get('spark_status')}"
        )
        assert meta_payload.get("workspace_id") is None, (
            f"Expected workspace_id to be None, got {meta_payload.get('workspace_id')}"
        )

        res_json = json.dumps(res)
        assert "10/14" not in res_json, "Banned synthetic literal '10/14' found in sync_ide_metadata output!"
        assert "3KVuyxqTNZxKVuAAf4tq3bxSOYz" not in res_json, (
            "Banned synthetic literal '3KVuyxqTNZxKVuAAf4tq3bxSOYz' found in sync_ide_metadata output!"
        )

    def test_unpopulated_payload_sync_notebook(self, isolated_sync_env):
        """Verify unpopulated payload generates sync cell containing "'mesh_health': '--'",

        and zero occurrences of '10/14' or '3KVuyxqTNZxKVuAAf4tq3bxSOYz'.
        """
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook(payload={}, dry_run=False)

        with open(isolated_sync_env["nb_path"], "r", encoding="utf-8") as f:
            nb = json.load(f)

        sync_cell = nb["cells"][1]
        cell_source = "".join(sync_cell["source"])
        assert "'mesh_health': '--'" in cell_source, (
            f"Expected cell source to contain \"'mesh_health': '--'\", got:\n{cell_source}"
        )

        nb_text = json.dumps(nb)
        assert "10/14" not in nb_text, "Banned synthetic literal '10/14' found in sync_notebook output!"
        assert "3KVuyxqTNZxKVuAAf4tq3bxSOYz" not in nb_text, (
            "Banned synthetic literal '3KVuyxqTNZxKVuAAf4tq3bxSOYz' found in sync_notebook output!"
        )

    def test_unpopulated_payload_sync_notebook_and_ide_isolated(self, isolated_sync_env):
        """Verify unpopulated payload in isolated environment produces clean None values,

        cell source "'mesh_health': '--'", and zero occurrences of '10/14' or '3KVuyxqTNZxKVuAAf4tq3bxSOYz'.
        """
        sync = isolated_sync_env["sync"]
        # In isolated environment without live IDE workspace
        res = sync.sync_notebook_and_ide(payload={"ide_context": {}}, dry_run=False)

        meta_payload = res["ide_metadata"]["payload"]
        mesh_health = meta_payload.get("mesh_health", {})

        assert mesh_health.get("healthy_services") is None, (
            f"Expected mesh_health.healthy_services to be None, got {mesh_health.get('healthy_services')}"
        )
        assert meta_payload.get("spark_status") is None, (
            f"Expected spark_status to be None, got {meta_payload.get('spark_status')}"
        )
        assert meta_payload.get("workspace_id") is None, (
            f"Expected workspace_id to be None, got {meta_payload.get('workspace_id')}"
        )

        with open(isolated_sync_env["nb_path"], "r", encoding="utf-8") as f:
            nb = json.load(f)
        cell_source = "".join(nb["cells"][1]["source"])
        assert "'mesh_health': '--'" in cell_source

        res_json = json.dumps(res)
        assert "10/14" not in res_json, "Banned synthetic literal '10/14' found in sync_notebook_and_ide output!"
        assert "3KVuyxqTNZxKVuAAf4tq3bxSOYz" not in res_json, (
            "Banned synthetic literal '3KVuyxqTNZxKVuAAf4tq3bxSOYz' found in sync_notebook_and_ide output!"
        )

    def test_disk_written_files_zero_synthetic_literals(self, isolated_sync_env):
        """Verify written files on disk contain zero occurrences of synthetic literals."""
        sync = isolated_sync_env["sync"]
        sync.sync_notebook_and_ide(payload={"ide_context": {}}, dry_run=False)

        nb_text = isolated_sync_env["nb_path"].read_text(encoding="utf-8")
        assert "10/14" not in nb_text, "Banned literal '10/14' written to notebook on disk!"
        assert "3KVuyxqTNZxKVuAAf4tq3bxSOYz" not in nb_text, "Banned literal written to notebook on disk!"

        meta_text = isolated_sync_env["meta_path"].read_text(encoding="utf-8")
        assert "10/14" not in meta_text, "Banned literal '10/14' written to metadata on disk!"
        assert "3KVuyxqTNZxKVuAAf4tq3bxSOYz" not in meta_text, "Banned literal written to metadata on disk!"

    def test_unpopulated_payload_produces_clean_none_and_dashes(self, isolated_sync_env):
        """Verify unpopulated payload ({}) produces clean None values for workspace_id,

        spark_status, and healthy_services, and dashed placeholder for cell source.
        """
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook_and_ide(payload={}, dry_run=False)
        meta_payload = res["ide_metadata"]["payload"]
        mesh_health = meta_payload.get("mesh_health", {})

        assert meta_payload.get("workspace_id") is None, (
            f"Expected workspace_id to be None, got {meta_payload.get('workspace_id')}"
        )
        assert meta_payload.get("spark_status") is None, (
            f"Expected spark_status to be None, got {meta_payload.get('spark_status')}"
        )
        assert mesh_health.get("healthy_services") is None, (
            f"Expected healthy_services to be None, got {mesh_health.get('healthy_services')}"
        )

        with open(isolated_sync_env["nb_path"], "r", encoding="utf-8") as f:
            nb = json.load(f)
        cell_source = "".join(nb["cells"][1]["source"])
        assert "'mesh_health': '--'" in cell_source

    def test_zero_occurrences_of_synthetic_literals_in_all_outputs(self, isolated_sync_env):
        """Verify zero occurrences of banned synthetic literals '10/14' or

        '3KVuyxqTNZxKVuAAf4tq3bxSOYz' across all return value dictionaries and written files for unpopulated payload.
        """
        sync = isolated_sync_env["sync"]
        res = sync.sync_notebook_and_ide(payload={}, dry_run=False)

        res_json = json.dumps(res)
        for banned in ["10/14", "3KVuyxqTNZxKVuAAf4tq3bxSOYz"]:
            assert banned not in res_json, f"Banned synthetic literal '{banned}' found in return value dictionary!"

        nb_text = isolated_sync_env["nb_path"].read_text(encoding="utf-8")
        meta_text = isolated_sync_env["meta_path"].read_text(encoding="utf-8")
        for banned in ["10/14", "3KVuyxqTNZxKVuAAf4tq3bxSOYz"]:
            assert banned not in nb_text, f"Banned synthetic literal '{banned}' found in written notebook on disk!"
            assert banned not in meta_text, f"Banned synthetic literal '{banned}' found in written metadata on disk!"

    def test_cli_dry_run_zero_synthetic_literals(self, tmp_path: Path):
        """Verify CLI --dry-run with sandboxed offline configuration does not query live host

        Screen Lens daemon or leak host workspace ID, and emits zero synthetic literals.
        """
        offline_options = tmp_path / "offline_options"
        offline_options.mkdir(parents=True, exist_ok=True)
        isolated_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:39999",
                    "ocr_stream_url": "http://127.0.0.1:39999",
                    "hud_mjpeg_url": "http://127.0.0.1:39999",
                    "db_fallback_path": str(tmp_path / "nonexistent.sqlite"),
                },
                "gemini_spark": {
                    "mcp_project_health_url": "http://127.0.0.1:39999/health",
                    "mcp_health_url": "http://127.0.0.1:39999/health",
                    "mcp_sse_url": "http://127.0.0.1:39999/sse",
                    "mcp_messages_url": "http://127.0.0.1:39999/messages",
                },
            },
            "resilience": {
                "connect_timeout_seconds": 0.2,
                "min_ram_sanctuary_gb": 4.8,
            },
            "ide_integration": {
                "pycharm_port": 39999,
                "options_dir": str(offline_options),
                "notebook_target_path": str(tmp_path / "lens_global_orchestrator.ipynb"),
                "metadata_path": str(tmp_path / ".idea" / "lens_context.json"),
            },
        }
        cfg_path = tmp_path / "offline_sync_config.json"
        cfg_path.write_text(json.dumps(isolated_cfg), encoding="utf-8")

        script = PROJECT_ROOT / "notebook_sync.py"
        cmd = [
            sys.executable,
            str(script),
            "--dry-run",
            "--config",
            str(cfg_path),
            "--options-dir",
            str(offline_options),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10.0)
        assert proc.returncode == 0, f"CLI exited with {proc.returncode}: {proc.stderr}"
        assert "10/14" not in proc.stdout, "Banned literal '10/14' found in CLI stdout!"
        assert "3KVuyxqTNZxKVuAAf4tq3bxSOYz" not in proc.stdout, "Banned workspace ID found in CLI stdout!"
