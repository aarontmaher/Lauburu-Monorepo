"""Empirical Verification Gate Suite for Milestone 3 Iteration 3.

Authored by challenger_m3_it3_2 (teamwork_preview_challenger).
Empirical verification of:
1. Hermetic Host State Isolation:
   - sync_notebook_and_ide(payload={}, dry_run=False) in temp dirs with options_dir set.
   - workspace_id is None, spark_status is None, mesh_health.healthy_services is None.
   - Cell source contains "'mesh_health': '--'".
   - Zero occurrences of "3KVuyxqTNZxKVuAAf4tq3bxSOYz" or "10/14" in return dictionary or written files.
2. CLI Dry Run Integrity & Disk Immutability:
   - Run /opt/homebrew/bin/python3 notebook_sync.py --dry-run.
   - Verify pure JSON stdout, exit code 0, zero disk mutations.
3. Adverse Payload Execution:
   - Execute entrypoints with null/malformed payloads (None, "", 123, [None], {"mesh_health": 42}).
   - Assert zero unhandled exceptions for both dry_run=True and dry_run=False.
4. Concurrency Stress:
   - Run 50+ concurrent threads updating notebook and metadata simultaneously.
   - Reader-writer concurrency stress testing atomic replacement and zero tearing.
"""

from __future__ import annotations

import concurrent.futures
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notebook_sync import NotebookSynchronizer


@pytest.fixture
def hermetic_env(tmp_path: Path):
    """Provides a completely isolated environment with sandboxed options and workspace directories."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    nb_path = repo_dir / "lens_global_orchestrator.ipynb"
    idea_dir = repo_dir / ".idea"
    idea_dir.mkdir(parents=True, exist_ok=True)
    meta_path = idea_dir / "lens_context.json"
    options_dir = tmp_path / "custom_options"
    options_dir.mkdir(parents=True, exist_ok=True)

    sync = NotebookSynchronizer(
        repo_root=repo_dir,
        notebook_path=nb_path,
        metadata_path=meta_path,
        options_dir=options_dir,
    )
    sync.pycharm_port = 63399  # isolate from live PyCharm port

    return {
        "repo_dir": repo_dir,
        "nb_path": nb_path,
        "idea_dir": idea_dir,
        "meta_path": meta_path,
        "options_dir": options_dir,
        "sync": sync,
    }


class TestHermeticHostStateIsolation:
    """1. Challenge hermetic host state isolation."""

    def test_unpopulated_payload_isolation(self, hermetic_env):
        sync = hermetic_env["sync"]
        nb_path = hermetic_env["nb_path"]
        meta_path = hermetic_env["meta_path"]

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
            f"Expected mesh_health.healthy_services to be None, got {mesh_health.get('healthy_services')}"
        )

        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        cell_source = "".join(nb["cells"][1]["source"])
        assert "'mesh_health': '--'" in cell_source, (
            f"Expected cell source to contain \"'mesh_health': '--'\", got:\n{cell_source}"
        )

        # Assert zero occurrences of banned synthetic literals
        res_json = json.dumps(res)
        nb_text = nb_path.read_text(encoding="utf-8")
        meta_text = meta_path.read_text(encoding="utf-8")

        for banned in ["3KVuyxqTNZxKVuAAf4tq3bxSOYz", "10/14"]:
            assert banned not in res_json, f"Banned literal '{banned}' found in output dict!"
            assert banned not in nb_text, f"Banned literal '{banned}' found in written notebook!"
            assert banned not in meta_text, f"Banned literal '{banned}' found in written metadata!"


class TestCliDryRunIntegrity:
    """2. Challenge CLI dry run."""

    def test_cli_dry_run_pure_json_exit_zero_zero_mutations(self, tmp_path: Path):
        # We check target paths in current working tree
        repo_root = Path("/Volumes/Lauburu-Monorepo")
        nb_path = repo_root / "lens_global_orchestrator.ipynb"
        meta_path = repo_root / ".idea" / "lens_context.json"

        def get_stat(p: Path):
            if p.exists():
                return (True, p.stat().st_mtime_ns, p.stat().st_size)
            return (False, None, None)

        nb_before = get_stat(nb_path)
        meta_before = get_stat(meta_path)

        cmd = [sys.executable, "notebook_sync.py", "--dry-run"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=15.0)

        assert proc.returncode == 0, f"CLI exited with non-zero code {proc.returncode}: {proc.stderr}"

        # Assert pure JSON stdout
        parsed = json.loads(proc.stdout)
        assert parsed.get("status") == "success"
        assert parsed.get("dry_run") is True
        assert parsed.get("notebook_modified") is False
        assert parsed.get("metadata_modified") is False

        nb_after = get_stat(nb_path)
        meta_after = get_stat(meta_path)

        assert nb_before == nb_after, "Notebook on disk was mutated during dry run!"
        assert meta_before == meta_after, "Metadata on disk was mutated during dry run!"


class TestAdversePayloads:
    """3. Challenge adverse payloads across all entrypoint methods."""

    @pytest.mark.parametrize(
        "payload",
        [
            None,
            "",
            123,
            [None],
            {"mesh_health": 42},
            {"screen_lens": None},
            {"accounts": None},
            {"accounts": [None]},
            {"ide_context": None},
            {},
        ],
    )
    def test_adverse_payloads_zero_unhandled_exceptions(self, hermetic_env, payload: Any):
        sync = hermetic_env["sync"]

        for dry_run in (True, False):
            # 1. sync_notebook
            res_nb = sync.sync_notebook(payload=payload, dry_run=dry_run)
            assert isinstance(res_nb, dict)
            assert res_nb.get("status") == "success"

            # 2. sync_ide_metadata
            res_meta = sync.sync_ide_metadata(payload=payload, dry_run=dry_run)
            assert isinstance(res_meta, dict)
            assert res_meta.get("status") == "success"

            # 3. sync_notebook_and_ide
            res_both = sync.sync_notebook_and_ide(payload=payload, dry_run=dry_run)
            assert isinstance(res_both, dict)
            assert res_both.get("status") == "success"

    def test_adverse_entrypoint_methods(self, hermetic_env):
        sync = hermetic_env["sync"]

        # detect_pycharm_workspace
        for opt in [None, "", hermetic_env["options_dir"]]:
            ws = sync.detect_pycharm_workspace(options_dir=opt if isinstance(opt, (str, Path)) else None)
            assert isinstance(ws, dict)

        # check_colab_gpu_offload
        for val in [0.0, -10.0, 50.0]:
            colab = sync.check_colab_gpu_offload(estimated_task_ram_gb=val)
            assert isinstance(colab, dict)


class TestConcurrencyStress:
    """4. Challenge concurrency with 50+ threads."""

    def test_50_plus_concurrent_threads_updating_notebook_and_metadata(self, hermetic_env):
        sync = hermetic_env["sync"]
        nb_path = hermetic_env["nb_path"]
        meta_path = hermetic_env["meta_path"]
        num_threads = 64

        # Initialize notebook
        baseline_nb = {
            "cells": [
                {"cell_type": "markdown", "id": "m0", "metadata": {}, "source": ["# Initial\n"]},
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(baseline_nb, f)

        def worker(tid: int):
            t_sync = NotebookSynchronizer(
                repo_root=hermetic_env["repo_dir"],
                notebook_path=nb_path,
                metadata_path=meta_path,
                options_dir=hermetic_env["options_dir"],
            )
            t_sync.pycharm_port = 63399
            payload = {
                "thread_id": tid,
                "timestamp_utc": f"2026-10-11T16:30:{tid:02d}.000000+00:00",
            }
            return t_sync.sync_notebook_and_ide(payload=payload, dry_run=False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_threads

        # Validate final state on disk
        with open(nb_path, "r", encoding="utf-8") as f:
            final_nb = json.load(f)

        sync_cells = [
            c for c in final_nb.get("cells", [])
            if any("AUTOGENERATED LAUBURU MESH & LENS TELEMETRY" in line for line in c.get("source", []))
        ]
        assert len(sync_cells) == 1, f"Expected exactly 1 sync cell, got {len(sync_cells)}"

        with open(meta_path, "r", encoding="utf-8") as f:
            final_meta = json.load(f)
        assert final_meta.get("status") == "IN_SYNC"

    def test_reader_writer_race_concurrency(self, hermetic_env):
        nb_path = hermetic_env["nb_path"]
        meta_path = hermetic_env["meta_path"]

        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}, f)

        stop_event = threading.Event()
        read_errors = []
        write_errors = []
        stats = {"reads": 0, "writes": 0}
        lock = threading.Lock()

        def reader():
            while not stop_event.is_set():
                try:
                    if nb_path.exists():
                        with open(nb_path, "r", encoding="utf-8") as f:
                            d = json.load(f)
                            assert isinstance(d, dict)
                    if meta_path.exists():
                        with open(meta_path, "r", encoding="utf-8") as f:
                            m = json.load(f)
                            assert isinstance(m, dict)
                    with lock:
                        stats["reads"] += 1
                except Exception as e:
                    with lock:
                        read_errors.append(str(e))
                time.sleep(0.005)

        def writer(idx: int):
            sync = NotebookSynchronizer(
                repo_root=hermetic_env["repo_dir"],
                notebook_path=nb_path,
                metadata_path=meta_path,
                options_dir=hermetic_env["options_dir"],
            )
            sync.pycharm_port = 63399
            while not stop_event.is_set():
                try:
                    sync.sync_notebook_and_ide(payload={"thread": idx, "time": time.time()}, dry_run=False)
                    with lock:
                        stats["writes"] += 1
                except Exception as e:
                    with lock:
                        write_errors.append(str(e))
                time.sleep(0.01)

        threads = []
        for i in range(20):
            tw = threading.Thread(target=writer, args=(i,))
            tr = threading.Thread(target=reader)
            threads.extend([tw, tr])
            tw.start()
            tr.start()

        time.sleep(2.0)
        stop_event.set()

        for t in threads:
            t.join(timeout=5.0)

        assert len(read_errors) == 0, f"Read errors: {read_errors}"
        assert len(write_errors) == 0, f"Write errors: {write_errors}"
        assert stats["reads"] > 100
        assert stats["writes"] > 20
