"""Unit, Integration, and Stress Test Suite for PyCharm IDE Integration & Notebook Sync.

Milestone 3 Validation Suite:
- Tier 1: Feature Coverage (Workspace detection, Colab offload evaluation, atomic cell injection, IDE metadata sync)
- Tier 2: Boundary Values & Corner Cases (Idempotency, corrupted XML regex fallback, atomic failure rollback, missing file recovery)
- Tier 3: Pairwise Combinations & Pipeline Flow (Consolidated sync_notebook_and_ide, symlink canonicalization)
- Tier 4: Real-World Scenarios (Live Darwin Mach memory probes, live PyCharm detection, CLI entrypoint subprocess execution)
- Tier 5: Adversarial Stress & Concurrency (Multi-threaded race condition safety)
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from notebook_sync import (
    DEFAULT_MIN_RAM_SANCTUARY_GB,
    DEFAULT_REMOTE_JUPYTER_URL,
    SYNC_HEADER_PREFIX,
    SYNC_TAG,
    NotebookSynchronizer,
    probe_darwin_mach_memory,
)


class TestNotebookSyncTier1FeatureCoverage:
    """Tier 1: Feature Coverage — Primary happy-path functionality."""

    def test_notebook_synchronizer_init_defaults(self, repo_root: Path):
        """Verifies default initialization loads repository root and canonical paths."""
        sync = NotebookSynchronizer(repo_root=repo_root)
        assert sync.repo_root == repo_root
        assert sync.notebook_path.name == "lens_global_orchestrator.ipynb"
        assert sync.metadata_path.name == "lens_context.json"
        assert sync.min_ram_sanctuary_gb == DEFAULT_MIN_RAM_SANCTUARY_GB

    def test_workspace_detection_from_mock_options_xml(self, temp_env_dir: Path):
        """Verifies detect_pycharm_workspace parses recentProjects.xml and workspace XML."""
        options_dir = temp_env_dir / "options"
        options_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir = temp_env_dir / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        recent_projects_xml = options_dir / "recentProjects.xml"
        recent_projects_xml.write_text(
            """<application>
  <component name="RecentProjectsManager">
    <option name="additionalInfo">
      <map>
        <entry key="/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo">
          <value>
            <RecentProjectMetaInfo displayName="Lauburu-Monorepo" opened="true" projectWorkspaceId="3KVuyxqTNZxKVuAAf4tq3bxSOYz">
              <option name="build" value="PY-262.10968.92" />
            </RecentProjectMetaInfo>
          </value>
        </entry>
      </map>
    </option>
    <option name="lastOpenedProject" value="/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo" />
  </component>
</application>""",
            encoding="utf-8",
        )

        ws_file = workspace_dir / "3KVuyxqTNZxKVuAAf4tq3bxSOYz.xml"
        ws_file.write_text(
            """<project version="4">
  <component name="FileEditorManager">
    <leaf>
      <file leaf-file-name="lens_global_orchestrator.ipynb">
        <entry file="file://$PROJECT_DIR$/lens_global_orchestrator.ipynb">
          <provider editor-type-id="jupyter-editor" selected="true" />
        </entry>
      </file>
    </leaf>
  </component>
</project>""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        # Isolate from developer's live localhost port 63342
        sync.pycharm_port = 63399
        res = sync.detect_pycharm_workspace(options_dir=options_dir)

        assert res["workspace_id"] == "3KVuyxqTNZxKVuAAf4tq3bxSOYz"
        assert "lens_global_orchestrator.ipynb" in res["open_files"]
        assert res["open_file"] == "lens_global_orchestrator.ipynb"
        assert res["active_tab"] == "lens_global_orchestrator.ipynb"
        assert res["version"] == "PY-262.10968.92"
        assert res["source"] == "options_xml"

    def test_resolve_remote_jupyter_settings_url(self, temp_env_dir: Path):
        """Verifies resolve_jupyter_settings_url extracts remote kernel URL from jupyter-settings.xml."""
        idea_dir = temp_env_dir / ".idea"
        idea_dir.mkdir(parents=True, exist_ok=True)
        settings_xml = idea_dir / "jupyter-settings.xml"
        settings_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="JupyterSettings">
    <option name="defaultConnection">
      <JupyterConnectionParameters>
        <option name="urlString" value="http://100.93.158.96:8889" />
      </JupyterConnectionParameters>
    </option>
  </component>
</project>""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        url = sync.resolve_jupyter_settings_url(jupyter_settings_path=settings_xml)
        assert url == "http://100.93.158.96:8889"

    def test_colab_gpu_offload_evaluation_low_memory(self, temp_env_dir: Path, monkeypatch):
        """Rule 3 Invariant: Free RAM < 4.8 GB triggers Colab offload recommendation."""
        # Mock memory with low RAM (2.4 GB free)
        monkeypatch.setattr(
            "notebook_sync.probe_darwin_mach_memory",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 2.4,
                "free_gb": 2.4,
                "memory_pressure_level": 2,
                "sanctuary_floor_gb": 4.8,
                "sanctuary_preserved": False,
                "platform": "darwin",
            },
        )

        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        offload = sync.check_colab_gpu_offload()

        assert offload["colab_offload_recommended"] is True
        assert offload["should_offload_to_colab"] is True
        assert offload["colab_offload_status"] == "RECOMMENDED"
        assert offload["target_runtime"] == "Google Colab Tesla T4"
        assert "below 4.8 GB sanctuary floor" in offload["reason"]

    def test_colab_gpu_offload_evaluation_healthy_memory(self, temp_env_dir: Path, monkeypatch):
        """Rule 3 Invariant: Free RAM >= 4.8 GB with normal pressure remains on Local Metal GPU."""
        monkeypatch.setattr(
            "notebook_sync.probe_darwin_mach_memory",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 7.5,
                "free_gb": 7.5,
                "memory_pressure_level": 1,
                "sanctuary_floor_gb": 4.8,
                "sanctuary_preserved": True,
                "platform": "darwin",
            },
        )

        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        offload = sync.check_colab_gpu_offload()

        assert offload["colab_offload_recommended"] is False
        assert offload["should_offload_to_colab"] is False
        assert offload["colab_offload_status"] == "READY"
        assert offload["target_runtime"] == "Local Metal GPU"

    def test_atomic_notebook_cell_injection_initial(
        self, mock_free_notebook_path: Path, sample_sync_payload: Dict[str, Any]
    ):
        """Feature 8: Atomically injects sync code cell at index 1 with tag 'lens_synced_context'."""
        sync = NotebookSynchronizer(notebook_path=mock_free_notebook_path)
        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            original_nb = json.load(f)
        orig_count = len(original_nb["cells"])

        res = sync.sync_notebook(payload=sample_sync_payload, notebook_path=mock_free_notebook_path)

        assert res["status"] == "success"
        assert res["dry_run"] is False
        assert res["notebook_modified"] is True
        assert res["cell_action"] == "inserted"
        assert res["sync_cell_index"] == 1

        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            updated_nb = json.load(f)

        assert len(updated_nb["cells"]) == orig_count + 1
        sync_cell = updated_nb["cells"][1]
        assert sync_cell["cell_type"] == "code"
        assert SYNC_TAG in sync_cell["metadata"]["tags"]
        source_text = "".join(sync_cell["source"])
        assert SYNC_HEADER_PREFIX in source_text
        assert "LENS_CONTEXT = {" in source_text
        assert "print(" in source_text

        # Verify root metadata
        assert "lauburu_mesh_sync" in updated_nb["metadata"]
        assert updated_nb["metadata"]["lauburu_mesh_sync"]["active_app"] == "PyCharm"

    def test_sync_ide_metadata_generation(self, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]):
        """Feature 9: Atomically writes .idea/lens_context.json with full schema."""
        meta_file = temp_env_dir / ".idea" / "lens_context.json"
        sync = NotebookSynchronizer(metadata_path=meta_file, repo_root=temp_env_dir)

        res = sync.sync_ide_metadata(payload=sample_sync_payload, metadata_path=meta_file)

        assert res["status"] == "success"
        assert res["metadata_modified"] is True
        assert meta_file.exists()

        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["workspace_id"] == "3KVuyxqTNZxKVuAAf4tq3bxSOYz"
        assert data["active_notebook"] == "lens_global_orchestrator.ipynb"
        assert "timestamp" in data
        assert "timestamp_utc" in data
        assert "colab_offload_status" in data
        assert "dual_accounts" in data
        assert len(data["dual_accounts"]) == 2


class TestNotebookSyncTier2BoundaryAndCornerCases:
    """Tier 2: Boundary Value Analysis & Corner Cases."""

    def test_notebook_cell_update_idempotency(
        self, mock_free_notebook_path: Path, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]
    ):
        """Boundary: Consecutive sync calls update the cell in-place without adding duplicate cells."""
        sync = NotebookSynchronizer(
            notebook_path=mock_free_notebook_path,
            metadata_path=temp_env_dir / ".idea" / "lens_context.json",
            repo_root=temp_env_dir,
        )

        # First sync: inserts cell
        res1 = sync.sync_notebook(payload=sample_sync_payload, notebook_path=mock_free_notebook_path)
        assert res1["cell_action"] == "inserted"
        count_after_first = res1["cell_count"]

        # Second sync: updates existing cell in-place
        payload2 = dict(sample_sync_payload)
        payload2["timestamp_utc"] = "2026-10-11T12:00:00Z"
        res2 = sync.sync_notebook(payload=payload2, notebook_path=mock_free_notebook_path)

        assert res2["cell_action"] == "updated"
        assert res2["sync_cell_index"] == 1
        assert res2["cell_count"] == count_after_first

        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        assert len(nb["cells"]) == count_after_first
        source = "".join(nb["cells"][1]["source"])
        assert "2026-10-11T12:00:00Z" in source

    def test_corrupted_recent_projects_xml_regex_fallback(self, temp_env_dir: Path):
        """Corner Case: If recentProjects.xml has malformed XML, regex parser extracts values cleanly."""
        options_dir = temp_env_dir / "options"
        options_dir.mkdir(parents=True, exist_ok=True)
        recent_xml = options_dir / "recentProjects.xml"
        # Malformed XML (missing closing tags, corrupted middle)
        recent_xml.write_text(
            """<application>
  <component name="RecentProjectsManager">
    <entry key="/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo">
      <RecentProjectMetaInfo opened="true" projectWorkspaceId="3KVuyxqTNZxKVuAAf4tq3bxSOYz">
        <unclosed tag garbage...
""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        sync.pycharm_port = 63399
        res = sync.detect_pycharm_workspace(options_dir=options_dir)

        assert res["workspace_id"] == "3KVuyxqTNZxKVuAAf4tq3bxSOYz"
        assert "Lauburu-Monorepo" in res["active_workspace"]
        assert res["source"] == "options_xml"

    def test_missing_jupyter_settings_xml_graceful_fallback(self, temp_env_dir: Path):
        """Corner Case: Missing jupyter-settings.xml falls back to default URL without crashing."""
        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        non_existent = temp_env_dir / ".idea" / "non_existent.xml"
        url = sync.resolve_jupyter_settings_url(jupyter_settings_path=non_existent)
        assert url == DEFAULT_REMOTE_JUPYTER_URL

    def test_dry_run_preserves_disk_completely(
        self, mock_free_notebook_path: Path, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]
    ):
        """Boundary: dry_run=True modifies zero files on disk."""
        orig_bytes = mock_free_notebook_path.read_bytes()
        meta_file = temp_env_dir / ".idea" / "lens_context.json"
        assert not meta_file.exists()

        sync = NotebookSynchronizer(
            notebook_path=mock_free_notebook_path,
            metadata_path=meta_file,
            repo_root=temp_env_dir,
        )

        res = sync.sync_notebook_and_ide(payload=sample_sync_payload, dry_run=True)

        assert res["dry_run"] is True
        assert res["notebook_modified"] is False
        assert res["metadata_modified"] is False
        assert mock_free_notebook_path.read_bytes() == orig_bytes
        assert not meta_file.exists()

    def test_atomic_write_rollback_on_failure(self, mock_free_notebook_path: Path):
        """Corner Case: If serialization fails, original file remains 100% byte-identical."""
        sync = NotebookSynchronizer(notebook_path=mock_free_notebook_path)
        orig_bytes = mock_free_notebook_path.read_bytes()

        class UnserializableType:
            pass

        bad_payload = {"bad_key": UnserializableType()}

        with pytest.raises(TypeError):
            sync._atomic_write_json(mock_free_notebook_path, {"test": UnserializableType()})

        assert mock_free_notebook_path.read_bytes() == orig_bytes
        # Confirm no temporary files linger in parent directory
        tmp_files = list(mock_free_notebook_path.parent.glob(f".{mock_free_notebook_path.name}.*.tmp"))
        assert len(tmp_files) == 0

    def test_missing_target_notebook_recovery(self, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]):
        """Corner Case: If target notebook does not exist on disk, synchronizer creates valid notebook."""
        target_nb = temp_env_dir / "created_on_demand.ipynb"
        assert not target_nb.exists()

        sync = NotebookSynchronizer(notebook_path=target_nb, repo_root=temp_env_dir)
        res = sync.sync_notebook(payload=sample_sync_payload, notebook_path=target_nb)

        assert res["status"] == "success"
        assert target_nb.exists()

        with open(target_nb, "r", encoding="utf-8") as f:
            nb = json.load(f)

        assert nb["nbformat"] == 4
        assert len(nb["cells"]) >= 2
        assert SYNC_TAG in nb["cells"][1]["metadata"]["tags"]

    def test_file_permissions_preserved_after_atomic_swap(
        self, mock_free_notebook_path: Path, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]
    ):
        """Boundary: File permissions (mode 0o644) are preserved after atomic swap."""
        os.chmod(mock_free_notebook_path, 0o644)
        sync = NotebookSynchronizer(
            notebook_path=mock_free_notebook_path,
            metadata_path=temp_env_dir / ".idea" / "lens_context.json",
            repo_root=temp_env_dir,
        )
        sync.sync_notebook(payload=sample_sync_payload, notebook_path=mock_free_notebook_path)

        mode = mock_free_notebook_path.stat().st_mode & 0o777
        assert oct(mode) == "0o644"


class TestNotebookSyncTier3CrossFeatureCombinations:
    """Tier 3: Pairwise Combinations & Pipeline Flow."""

    def test_sync_notebook_and_ide_pipeline(
        self, mock_free_notebook_path: Path, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]
    ):
        """Cross-Feature: sync_notebook_and_ide coordinates both notebook and IDE metadata atomically."""
        meta_file = temp_env_dir / ".idea" / "lens_context.json"
        sync = NotebookSynchronizer(
            notebook_path=mock_free_notebook_path,
            metadata_path=meta_file,
            repo_root=temp_env_dir,
        )

        res = sync.sync_notebook_and_ide(payload=sample_sync_payload, dry_run=False)

        assert res["status"] == "success"
        assert res["notebook_modified"] is True
        assert res["metadata_modified"] is True
        assert meta_file.exists()

        # Confirm data consistency between notebook and metadata
        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert nb["metadata"]["lauburu_mesh_sync"]["last_sync_utc"] == meta["timestamp_utc"]
        assert meta["active_notebook"] == mock_free_notebook_path.name

    def test_symlink_canonicalization_resolution(self, temp_env_dir: Path):
        """Cross-Feature: Symlink path and realpath are recognized as equivalent workspace."""
        real_dir = temp_env_dir / "real_monorepo"
        real_dir.mkdir(parents=True, exist_ok=True)
        link_dir = temp_env_dir / "symlink_monorepo"

        try:
            link_dir.symlink_to(real_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not permitted in this environment")

        sync = NotebookSynchronizer(repo_root=link_dir)
        assert os.path.samefile(sync.repo_root, real_dir)


class TestNotebookSyncTier4RealWorldScenarios:
    """Tier 4: Real-World Workload Scenarios & Live Probes."""

    def test_live_darwin_mach_memory_probe(self):
        """Live Probe: Probes physical Mach kernel memory metrics on host without mocking."""
        mem = probe_darwin_mach_memory()
        assert isinstance(mem, dict)
        assert "total_ram_gb" in mem
        assert "free_ram_gb" in mem
        assert "sanctuary_floor_gb" in mem
        assert mem["sanctuary_floor_gb"] == 4.8
        assert "sanctuary_preserved" in mem
        assert isinstance(mem["sanctuary_preserved"], bool)

    def test_live_pycharm_workspace_probe_on_host(self, temp_env_dir: Path):
        """Live Probe: Probes host system PyCharm without crashing."""
        sync = NotebookSynchronizer(repo_root=temp_env_dir)
        res = sync.detect_pycharm_workspace()
        assert isinstance(res, dict)
        assert "running" in res
        assert "is_ide_running" in res
        assert "workspace_id" in res
        assert "active_project" in res
        assert "open_files" in res
        assert isinstance(res["open_files"], list)

    def test_cli_dry_run_subprocess_execution(self, canonical_config_path: Path, mock_free_notebook_path: Path):
        """Live Workload: Runs python3 notebook_sync.py --dry-run and verifies pure JSON on stdout."""
        script_path = Path(__file__).resolve().parent.parent / "notebook_sync.py"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(script_path.parent)

        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--config",
            str(canonical_config_path),
            "--notebook",
            str(mock_free_notebook_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10.0)

        assert proc.returncode == 0, f"CLI exited with {proc.returncode}. Stderr: {proc.stderr}"
        stdout_clean = proc.stdout.strip()
        assert stdout_clean.startswith("{") and stdout_clean.endswith("}")

        parsed = json.loads(stdout_clean)
        assert parsed["status"] == "success"
        assert parsed["dry_run"] is True


class TestNotebookSyncTier5AdversarialStressAndConcurrency:
    """Tier 5: Adversarial Stress & Multi-Threaded Concurrency."""

    def test_concurrent_atomic_writes_no_corruption(
        self, mock_free_notebook_path: Path, temp_env_dir: Path, sample_sync_payload: Dict[str, Any]
    ):
        """Stress: 20 concurrent threads writing to target notebook simultaneously via atomic replace."""
        meta_file = temp_env_dir / ".idea" / "lens_context.json"
        sync = NotebookSynchronizer(
            notebook_path=mock_free_notebook_path,
            metadata_path=meta_file,
            repo_root=temp_env_dir,
        )

        def sync_worker(idx: int) -> Dict[str, Any]:
            worker_payload = dict(sample_sync_payload)
            worker_payload["timestamp_utc"] = f"2026-10-11T12:00:{idx:02d}Z"
            return sync.sync_notebook_and_ide(worker_payload, dry_run=False)

        num_threads = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(sync_worker, i) for i in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_threads
        for r in results:
            assert r["status"] == "success"

        # Verify target notebook and metadata JSON files are 100% valid and uncorrupted
        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            final_nb = json.load(f)
        with open(meta_file, "r", encoding="utf-8") as f:
            final_meta = json.load(f)

        assert final_nb["nbformat"] == 4
        # Exactly 1 sync cell exists
        sync_cells = [
            c for c in final_nb["cells"]
            if SYNC_TAG in c.get("metadata", {}).get("tags", [])
        ]
        assert len(sync_cells) == 1
        assert "workspace_id" in final_meta
