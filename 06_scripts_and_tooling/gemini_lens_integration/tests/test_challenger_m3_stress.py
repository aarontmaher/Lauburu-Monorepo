"""Empirical Adversarial Stress Test Suite for Milestone 3 (NotebookSynchronizer).

Authored by challenger_m3_1 (Milestone 3 Challenger 1: Concurrency & Atomic File Safety).
Strictly evaluates:
1. High-concurrency stress test:
   - 50+ concurrent threads attempting simultaneous notebook cell injection and .idea/lens_context.json updates
     on shared and separate notebook paths.
   - Assert zero corrupted JSON files, zero half-written files, and valid JSON structure on disk after all threads finish.
2. Interrupted write simulation:
   - Simulate write failure midway through serialization.
   - Verify that original notebook file remains 100% intact (cryptographic SHA256 identity) and no orphaned temporary files remain.
3. Reader-Writer Race Condition Stress:
   - High-concurrency simultaneous reader and writer threads asserting zero partial reads, zero tearing, and 100% valid JSON at all times.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notebook_sync import (
    DEFAULT_MIN_RAM_SANCTUARY_GB,
    DEFAULT_REMOTE_JUPYTER_URL,
    SYNC_HEADER_PREFIX,
    SYNC_TAG,
    NotebookSynchronizer,
)


def _compute_sha256(file_path: Path) -> str:
    """Computes SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def stress_temp_dir(tmp_path: Path) -> Path:
    """Provides an isolated temporary directory for high-concurrency stress tests."""
    target_dir = tmp_path / "stress_env"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


@pytest.fixture
def baseline_notebook(stress_temp_dir: Path) -> Path:
    """Creates a realistic baseline Jupyter notebook with header and operational code cells."""
    nb_path = stress_temp_dir / "lens_global_orchestrator.ipynb"
    canonical_content = {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "header_markdown_cell_0",
                "metadata": {},
                "source": [
                    "# 👁️ Screen Lens Sovereign: Global Project Orchestrator\n",
                    "**PyCharm 2026.2 Colab Integration Notebook**\n",
                ],
            },
            {
                "cell_type": "code",
                "id": "operational_code_cell_1",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Original Operational Logic\n",
                    "print('[*] Baseline Orchestrator Operational')\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    nb_path.write_text(json.dumps(canonical_content, indent=1), encoding="utf-8")
    return nb_path


@pytest.fixture
def baseline_metadata_file(stress_temp_dir: Path) -> Path:
    """Creates a baseline .idea/lens_context.json file."""
    idea_dir = stress_temp_dir / ".idea"
    idea_dir.mkdir(parents=True, exist_ok=True)
    meta_path = idea_dir / "lens_context.json"
    initial_meta = {
        "timestamp": "2026-10-11T12:00:00Z",
        "timestamp_utc": "2026-10-11T12:00:00Z",
        "status": "INITIAL",
        "workspace_id": "3KVuyxqTNZxKVuAAf4tq3bxSOYz",
        "active_project": str(stress_temp_dir),
    }
    meta_path.write_text(json.dumps(initial_meta, indent=2), encoding="utf-8")
    return meta_path


class TestChallengerHighConcurrencyStress:
    """Empirical Stress Tests: 50+ concurrent threads executing simultaneous updates."""

    def test_high_concurrency_shared_targets_60_threads(
        self, baseline_notebook: Path, baseline_metadata_file: Path, stress_temp_dir: Path
    ):
        """Stress: 60 concurrent threads simultaneously targeting the EXACT SAME notebook and .idea/lens_context.json.

        Verifies:
        - 100% of threads complete successfully with exit status 'success'.
        - Zero corrupted JSON files on disk.
        - Zero half-written or truncated files.
        - Exactly 1 sync cell exists at index 1 (no duplicate cells injected).
        - Markdown header and subsequent operational code cells remain intact.
        - .idea/lens_context.json is 100% valid JSON with valid status.
        - Zero orphaned temporary files (.*.tmp) remain in target directories.
        """
        sync = NotebookSynchronizer(
            notebook_path=baseline_notebook,
            metadata_path=baseline_metadata_file,
            repo_root=stress_temp_dir,
        )

        num_threads = 60
        barrier = threading.Barrier(num_threads)

        def worker_task(worker_id: int) -> Dict[str, Any]:
            # Wait for all threads to be ready to maximize simultaneous lock contention
            barrier.wait(timeout=10.0)
            payload = {
                "timestamp_utc": f"2026-10-11T14:30:{worker_id % 60:02d}.{worker_id:03d}Z",
                "screen_lens": {
                    "active_screen": {
                        "app_name": "PyCharm",
                        "window_title": f"Project Window {worker_id}",
                        "ocr_snippet": f"Concurrency worker {worker_id} OCR snippet",
                    },
                    "mesh_services": {"healthy_count": f"{worker_id}/60 healthy"},
                },
                "colab_offload_recommended": (worker_id % 2 == 0),
                "accounts": ["aaron.t.maher@gmail.com", "lauburu@lauburugrappling.com"],
            }
            return sync.sync_notebook_and_ide(payload, dry_run=False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_threads
        for res in results:
            assert res["status"] == "success"
            assert res["notebook_modified"] is True
            assert res["metadata_modified"] is True

        # 1. Assert notebook is 100% valid JSON
        with open(baseline_notebook, "r", encoding="utf-8") as f:
            nb_data = json.load(f)

        assert nb_data["nbformat"] == 4
        assert "cells" in nb_data
        cells = nb_data["cells"]

        # Exactly 3 cells: [header_markdown, sync_cell, original_code_cell]
        assert len(cells) == 3, f"Expected exactly 3 cells, found {len(cells)}"
        assert cells[0]["cell_type"] == "markdown"
        assert cells[1]["cell_type"] == "code"
        assert SYNC_TAG in cells[1]["metadata"]["tags"]
        sync_cell_source = "".join(cells[1]["source"])
        assert SYNC_HEADER_PREFIX in sync_cell_source
        assert "LENS_CONTEXT =" in sync_cell_source

        # Verify original operational code cell was preserved at index 2
        assert cells[2]["cell_type"] == "code"
        assert "Baseline Orchestrator Operational" in "".join(cells[2]["source"])

        # 2. Assert .idea/lens_context.json is 100% valid JSON
        with open(baseline_metadata_file, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        assert meta_data["status"] == "IN_SYNC"
        assert "workspace_id" in meta_data
        assert "dual_accounts" in meta_data
        assert len(meta_data["dual_accounts"]) == 2

        # 3. Assert zero orphaned .tmp files remain in notebook or .idea directories
        nb_tmp_files = list(baseline_notebook.parent.glob(f".{baseline_notebook.name}.*.tmp"))
        meta_tmp_files = list(baseline_metadata_file.parent.glob(f".{baseline_metadata_file.name}.*.tmp"))
        assert len(nb_tmp_files) == 0, f"Found lingering temporary notebook files: {nb_tmp_files}"
        assert len(meta_tmp_files) == 0, f"Found lingering temporary metadata files: {meta_tmp_files}"

    def test_high_concurrency_separate_targets_50_threads(self, stress_temp_dir: Path):
        """Stress: 50 concurrent threads writing to 50 SEPARATE notebook and metadata paths simultaneously.

        Verifies:
        - All 50 separate notebooks are created and valid Jupyter format.
        - All 50 separate metadata JSON files are created and valid.
        - Zero files corrupted, zero half-written files.
        - Zero orphaned temporary files across the entire directory tree.
        """
        num_threads = 50
        targets: List[Tuple[Path, Path, NotebookSynchronizer]] = []

        for i in range(num_threads):
            worker_dir = stress_temp_dir / f"worker_{i:02d}"
            worker_dir.mkdir(parents=True, exist_ok=True)
            nb_path = worker_dir / f"notebook_{i:02d}.ipynb"
            meta_path = worker_dir / ".idea" / "lens_context.json"
            sync = NotebookSynchronizer(
                notebook_path=nb_path,
                metadata_path=meta_path,
                repo_root=worker_dir,
            )
            targets.append((nb_path, meta_path, sync))

        barrier = threading.Barrier(num_threads)

        def worker_task(idx: int) -> Dict[str, Any]:
            barrier.wait(timeout=10.0)
            nb_path, meta_path, sync = targets[idx]
            payload = {
                "timestamp_utc": f"2026-10-11T14:35:{idx:02d}.000Z",
                "screen_lens": {
                    "active_screen": {
                        "app_name": f"App_{idx}",
                        "window_title": f"Window_{idx}",
                        "ocr_snippet": f"Snippet for worker {idx}",
                    },
                    "mesh_services": {"healthy_count": f"{idx}/50"},
                },
                "accounts": ["aaron.t.maher@gmail.com", "lauburu@lauburugrappling.com"],
            }
            return sync.sync_notebook_and_ide(payload, dry_run=False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_threads
        for res in results:
            assert res["status"] == "success"

        # Verify all 50 notebooks and metadata files
        for nb_path, meta_path, _ in targets:
            assert nb_path.exists(), f"Notebook missing: {nb_path}"
            assert meta_path.exists(), f"Metadata missing: {meta_path}"

            with open(nb_path, "r", encoding="utf-8") as f:
                nb = json.load(f)
            assert nb["nbformat"] == 4
            assert len(nb["cells"]) >= 2
            assert any(SYNC_TAG in c.get("metadata", {}).get("tags", []) for c in nb["cells"])

            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            assert meta["status"] == "IN_SYNC"

            # Assert no lingering .tmp files
            assert len(list(nb_path.parent.glob("*.tmp"))) == 0
            assert len(list(meta_path.parent.glob("*.tmp"))) == 0

    def test_high_concurrency_mixed_shared_and_separate_targets(
        self, baseline_notebook: Path, baseline_metadata_file: Path, stress_temp_dir: Path
    ):
        """Stress: 60 concurrent threads running simultaneously:

        - 30 threads hammering the shared notebook & metadata.
        - 30 threads updating their own isolated notebooks & metadata.
        Verifies zero file corruption across both shared and isolated paths.
        """
        num_shared = 30
        num_isolated = 30
        total_threads = num_shared + num_isolated

        shared_sync = NotebookSynchronizer(
            notebook_path=baseline_notebook,
            metadata_path=baseline_metadata_file,
            repo_root=stress_temp_dir,
        )

        isolated_targets: List[Tuple[Path, Path, NotebookSynchronizer]] = []
        for i in range(num_isolated):
            iso_dir = stress_temp_dir / f"iso_{i:02d}"
            iso_dir.mkdir(parents=True, exist_ok=True)
            iso_nb = iso_dir / f"iso_nb_{i}.ipynb"
            iso_meta = iso_dir / ".idea" / "lens_context.json"
            iso_sync = NotebookSynchronizer(
                notebook_path=iso_nb,
                metadata_path=iso_meta,
                repo_root=iso_dir,
            )
            isolated_targets.append((iso_nb, iso_meta, iso_sync))

        barrier = threading.Barrier(total_threads)

        def mixed_task(worker_id: int) -> Dict[str, Any]:
            barrier.wait(timeout=10.0)
            payload = {
                "timestamp_utc": f"2026-10-11T14:40:{worker_id:02d}.000Z",
                "screen_lens": {
                    "active_screen": {"app_name": "PyCharm", "window_title": f"Mixed Window {worker_id}"},
                },
            }
            if worker_id < num_shared:
                return shared_sync.sync_notebook_and_ide(payload, dry_run=False)
            else:
                iso_idx = worker_id - num_shared
                _, _, sync_inst = isolated_targets[iso_idx]
                return sync_inst.sync_notebook_and_ide(payload, dry_run=False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:
            futures = [executor.submit(mixed_task, i) for i in range(total_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == total_threads

        # Verify shared targets
        with open(baseline_notebook, "r", encoding="utf-8") as f:
            nb = json.load(f)
        assert nb["nbformat"] == 4
        assert len(nb["cells"]) == 3

        with open(baseline_metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["status"] == "IN_SYNC"

        # Verify isolated targets
        for iso_nb, iso_meta, _ in isolated_targets:
            with open(iso_nb, "r", encoding="utf-8") as f:
                json.load(f)
            with open(iso_meta, "r", encoding="utf-8") as f:
                json.load(f)

    def test_high_concurrency_race_condition_readers_and_writers(
        self, baseline_notebook: Path, baseline_metadata_file: Path, stress_temp_dir: Path
    ):
        """Stress: 25 writer threads and 25 reader threads running concurrently.

        Asserts that reader threads NEVER encounter a partially written file, EOF error,
        or malformed JSON during intense concurrent atomic replacements (verifying atomic swap guarantee).
        """
        sync = NotebookSynchronizer(
            notebook_path=baseline_notebook,
            metadata_path=baseline_metadata_file,
            repo_root=stress_temp_dir,
        )

        stop_event = threading.Event()
        read_errors: List[str] = []
        reads_count = [0]
        writes_count = [0]
        lock = threading.Lock()

        def writer_loop(writer_id: int):
            iteration = 0
            while not stop_event.is_set() and iteration < 10:
                iteration += 1
                payload = {
                    "timestamp_utc": f"2026-10-11T14:45:{writer_id:02d}.{iteration:03d}Z",
                    "screen_lens": {
                        "active_screen": {
                            "app_name": "PyCharm",
                            "window_title": f"Writer {writer_id} Iteration {iteration}",
                        }
                    },
                }
                sync.sync_notebook_and_ide(payload, dry_run=False)
                with lock:
                    writes_count[0] += 1
                time.sleep(0.005)

        def reader_loop(reader_id: int):
            while not stop_event.is_set():
                try:
                    with open(baseline_notebook, "r", encoding="utf-8") as f:
                        content = f.read()
                        if not content.strip():
                            read_errors.append(f"Reader {reader_id} read empty notebook file!")
                        else:
                            nb = json.loads(content)
                            if "nbformat" not in nb or "cells" not in nb:
                                read_errors.append(f"Reader {reader_id} read corrupted notebook structure!")

                    with open(baseline_metadata_file, "r", encoding="utf-8") as f:
                        meta_content = f.read()
                        if not meta_content.strip():
                            read_errors.append(f"Reader {reader_id} read empty metadata file!")
                        else:
                            meta = json.loads(meta_content)
                            if "status" not in meta:
                                read_errors.append(f"Reader {reader_id} read corrupted metadata!")
                    with lock:
                        reads_count[0] += 1
                except Exception as exc:
                    read_errors.append(f"Reader {reader_id} encountered exception: {exc}")
                time.sleep(0.002)

        num_writers = 25
        num_readers = 25

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
            writer_futures = [executor.submit(writer_loop, i) for i in range(num_writers)]
            reader_futures = [executor.submit(reader_loop, i) for i in range(num_readers)]

            # Wait for writers to complete their iterations
            for wf in writer_futures:
                wf.result()

            # Signal readers to stop
            stop_event.set()
            for rf in reader_futures:
                rf.result()

        assert writes_count[0] >= num_writers * 10
        assert reads_count[0] > 50
        assert len(read_errors) == 0, f"Encountered read tearing/corruption errors: {read_errors[:5]}"


class TestChallengerInterruptedWriteSimulation:
    """Interrupted write simulation: verifies that write failures midway through serialization

    leave original files 100% byte-identical and leave zero orphaned temporary files.
    """

    def test_interrupted_write_midway_serialization_type_error(
        self, baseline_notebook: Path, stress_temp_dir: Path
    ):
        """Interrupted Write: Injects an unserializable type midway inside the notebook dictionary.

        Verifies:
        - TypeError is raised.
        - Original notebook remains 100% byte-identical (SHA256 verified).
        - Zero orphaned temporary files (.lens_global_orchestrator.ipynb.*.tmp) remain on disk.
        """
        orig_sha256 = _compute_sha256(baseline_notebook)
        orig_bytes = baseline_notebook.read_bytes()

        sync = NotebookSynchronizer(
            notebook_path=baseline_notebook,
            repo_root=stress_temp_dir,
        )

        class UnserializableObject:
            def __repr__(self):
                return "<UnserializableObject>"

        # Construct payload with unserializable object inside cells
        corrupt_nb = {
            "cells": [
                {"cell_type": "markdown", "source": ["# Normal Markdown Header\n"]},
                {"cell_type": "code", "bad_data": UnserializableObject()},
            ],
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        with pytest.raises(TypeError):
            sync._atomic_write_json(baseline_notebook, corrupt_nb)

        # 1. Assert original file remains 100% intact and byte-identical
        assert _compute_sha256(baseline_notebook) == orig_sha256
        assert baseline_notebook.read_bytes() == orig_bytes

        # 2. Assert no orphaned temporary files remain
        tmp_files = list(baseline_notebook.parent.glob(f".{baseline_notebook.name}.*.tmp"))
        assert len(tmp_files) == 0, f"Found orphaned temporary files: {tmp_files}"

    def test_interrupted_write_midway_io_error_simulation(
        self, baseline_notebook: Path, stress_temp_dir: Path
    ):
        """Interrupted Write: Simulates an I/O / disk-full failure midway through file writing.

        Patches json.dump to write partial content and then raise OSError('ENOSPC: No space left on device').
        Verifies:
        - OSError is raised.
        - Original file remains 100% intact and byte-identical (SHA256 verified).
        - Partial temporary file is completely removed by finally: temp_path.unlink().
        """
        orig_sha256 = _compute_sha256(baseline_notebook)
        sync = NotebookSynchronizer(
            notebook_path=baseline_notebook,
            repo_root=stress_temp_dir,
        )

        real_dump = json.dump

        def failing_dump(obj, fp, **kwargs):
            # Write 150 bytes of partial JSON to simulate half-written file
            fp.write('{"partial": "half_written_garbage_before_crash", "cells": [')
            fp.flush()
            raise OSError(28, "No space left on device")

        with patch("json.dump", side_effect=failing_dump):
            with pytest.raises(OSError) as exc_info:
                sync._atomic_write_json(baseline_notebook, {"test": "data"})
            assert "No space left on device" in str(exc_info.value)

        # 1. Assert original notebook unchanged
        assert _compute_sha256(baseline_notebook) == orig_sha256

        # 2. Assert zero orphaned temporary files
        tmp_files = list(baseline_notebook.parent.glob(f".{baseline_notebook.name}.*.tmp"))
        assert len(tmp_files) == 0, f"Lingering temporary files after I/O error: {tmp_files}"

    def test_interrupted_write_on_metadata_file(
        self, baseline_metadata_file: Path, stress_temp_dir: Path
    ):
        """Interrupted Write: Simulates crash while writing .idea/lens_context.json.

        Verifies:
        - Original metadata remains byte-identical.
        - Zero orphaned temporary files remain in .idea/.
        """
        orig_sha256 = _compute_sha256(baseline_metadata_file)
        sync = NotebookSynchronizer(
            metadata_path=baseline_metadata_file,
            repo_root=stress_temp_dir,
        )

        def failing_dump(obj, fp, **kwargs):
            fp.write('{"status": "CORRUPTED_INCOMPLETE_')
            fp.flush()
            raise IOError("Simulated broken pipe / power loss")

        with patch("json.dump", side_effect=failing_dump):
            with pytest.raises(IOError):
                sync._atomic_write_json(baseline_metadata_file, {"status": "NEW"})

        # Assert metadata is identical to baseline
        assert _compute_sha256(baseline_metadata_file) == orig_sha256

        # Assert no temp files
        tmp_files = list(baseline_metadata_file.parent.glob(f".{baseline_metadata_file.name}.*.tmp"))
        assert len(tmp_files) == 0

    def test_interrupted_write_on_nonexistent_target_clean_rollback(
        self, stress_temp_dir: Path
    ):
        """Interrupted Write: Simulates crash when writing a target file that did NOT previously exist.

        Verifies:
        - Target file is not created as a 0-byte or corrupted artifact.
        - Zero orphaned temporary files remain.
        """
        new_target = stress_temp_dir / "never_existed.ipynb"
        assert not new_target.exists()

        sync = NotebookSynchronizer(notebook_path=new_target, repo_root=stress_temp_dir)

        def failing_dump(obj, fp, **kwargs):
            fp.write('{"cells": [')
            raise RuntimeError("Mid-creation serialization failure")

        with patch("json.dump", side_effect=failing_dump):
            with pytest.raises(RuntimeError):
                sync._atomic_write_json(new_target, {"cells": []})

        assert not new_target.exists(), "Target file was erroneously created despite failure!"
        tmp_files = list(stress_temp_dir.glob(".*.tmp"))
        assert len(tmp_files) == 0, f"Found orphaned temp files: {tmp_files}"

    def test_file_permissions_and_mode_preserved_across_replacements(
        self, baseline_notebook: Path, stress_temp_dir: Path
    ):
        """File Safety: Preserves existing file mode permissions (e.g. 0o600 or 0o644)."""
        os.chmod(baseline_notebook, 0o600)
        sync = NotebookSynchronizer(notebook_path=baseline_notebook, repo_root=stress_temp_dir)

        sync._atomic_write_json(baseline_notebook, {"test": "permissions"})

        current_mode = baseline_notebook.stat().st_mode & 0o777
        assert oct(current_mode) == "0o600", f"Expected 0o600, got {oct(current_mode)}"

        # Reset to 0o644
        os.chmod(baseline_notebook, 0o644)
        sync._atomic_write_json(baseline_notebook, {"test": "permissions_644"})
        current_mode = baseline_notebook.stat().st_mode & 0o777
        assert oct(current_mode) == "0o644", f"Expected 0o644, got {oct(current_mode)}"


class TestChallengerAdversarialEdgeCases:
    """Additional Adversarial Stress & Edge Cases."""

    def test_rapid_burst_concurrency_100_sequential_and_parallel_syncs(
        self, baseline_notebook: Path, baseline_metadata_file: Path, stress_temp_dir: Path
    ):
        """Stress: 100 rapid sync operations alternating between sequential and parallel bursts.

        Ensures no file descriptor leaks, no inode exhaustion, and final state remains 100% valid.
        """
        sync = NotebookSynchronizer(
            notebook_path=baseline_notebook,
            metadata_path=baseline_metadata_file,
            repo_root=stress_temp_dir,
        )

        for batch in range(10):
            def burst_worker(b_idx: int):
                payload = {
                    "timestamp_utc": f"2026-10-11T14:50:{batch:02d}.{b_idx:03d}Z",
                    "screen_lens": {"active_screen": {"app_name": "PyCharm", "window_title": f"Burst {batch}-{b_idx}"}},
                }
                return sync.sync_notebook_and_ide(payload, dry_run=False)

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(burst_worker, i) for i in range(10)]
                for f in concurrent.futures.as_completed(futures):
                    assert f.result()["status"] == "success"

        # Final verification
        with open(baseline_notebook, "r", encoding="utf-8") as f:
            nb = json.load(f)
        assert nb["nbformat"] == 4
        assert len(nb["cells"]) == 3

        with open(baseline_metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["status"] == "IN_SYNC"

        tmp_files = list(stress_temp_dir.rglob(".*.tmp"))
        assert len(tmp_files) == 0, f"Found lingering tmp files after 100 burst ops: {tmp_files}"

    def test_offline_recent_projects_xml_build_extraction_without_live_api(
        self, stress_temp_dir: Path
    ):
        """Adversarial Discovery: Verifies XML fallback extracts PyCharm build/version when port 63342 is offline.

        When port 63342 is unreachable (e.g. rate-limited, closed, or CI sandbox),
        detect_pycharm_workspace must extract 'version' / 'pycharm_build' from <option name="build" value="..." />
        in recentProjects.xml rather than returning None.
        """
        options_dir = stress_temp_dir / "options_offline"
        options_dir.mkdir(parents=True, exist_ok=True)
        recent_xml = options_dir / "recentProjects.xml"
        recent_xml.write_text(
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
  </component>
</application>""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(repo_root=stress_temp_dir)
        import urllib.error
        with patch("urllib.request.OpenerDirector.open", side_effect=urllib.error.URLError("Connection refused")):
            res = sync.detect_pycharm_workspace(options_dir=options_dir)

        assert res["version"] == "PY-262.10968.92", f"Expected 'PY-262.10968.92' from XML fallback, got {res.get('version')}"

