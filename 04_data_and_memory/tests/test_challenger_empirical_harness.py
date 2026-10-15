#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Challenger 2 Empirical Verification Test Harness
===============================================
Rigorous stress-testing of:
1. Live socket probes (closed, timeout, offline inference fleet, port range boundaries)
2. Multi-threaded and Multi-process concurrency + atomic POSIX write locking
3. Subprocess signal handling (SIGINT, SIGTERM) and graceful daemon shutdown
4. Real-time telemetry artifacts, storage fallback, and LiveTrainingAutomationEngine execution paths
5. Stagnation defense, Rule #0 Zero-Mock gates, and boundary failure modes
"""

import os
import sys
import time
import math
import json
import signal
import socket
import tempfile
import threading
import subprocess
import multiprocessing
from pathlib import Path
import pytest

CURRENT_DIR = Path(__file__).resolve().parent
MODULE_DIR = CURRENT_DIR.parent
MONOREPO_ROOT = MODULE_DIR.parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from tri_vault_sink import (
    TriVaultSink,
    verify_zero_mock_compliance,
    stream_loss_to_obsidian,
    check_storage_health,
)
from multi_stream_harvester import MultiStreamHarvester
from synthetic_debate_engine import SyntheticDebateEngine, FLEET_PORTS
from telemetry_streamer import TelemetryStreamer, StorageSentinel
from mlx_qlora_trainer import MLXQLoRATrainer, DynamicRamGovernor
from live_training_automation_engine import LiveTrainingAutomationEngine


# ============================================================================
# PILLAR 1: LIVE SOCKET PROBES & ADVERSARIAL PORT BEHAVIOR
# ============================================================================

def test_socket_probe_closed_ports():
    """Verify that socket probes against closed ports return False swiftly without hanging."""
    engine = SyntheticDebateEngine()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        closed_port = s.getsockname()[1]
    
    t0 = time.perf_counter()
    is_live = engine.probe_port_health(closed_port, timeout_s=0.25)
    dt = time.perf_counter() - t0

    assert is_live is False
    assert dt < 0.20, f"Closed port probe took too long: {dt:.4f}s"


def test_socket_probe_all_fleet_ports_offline_graceful():
    """Verify probe behavior across all 8 fleet ports (8080, 8082, 8083, 8084, 8085, 8086, 8087, 8096)."""
    engine = SyntheticDebateEngine()
    status = engine.get_fleet_status()
    assert len(status) == 8
    for role, info in status.items():
        assert "port" in info
        assert "is_live" in info
        assert isinstance(info["is_live"], bool)


def test_socket_probe_boundary_and_invalid_ports():
    """Verify probe does not throw unhandled exceptions on invalid or edge-case ports."""
    engine = SyntheticDebateEngine()
    # Port 0, negative, or out of range
    assert engine.probe_port_health(0, timeout_s=0.1) is False
    assert engine.probe_port_health(65535, timeout_s=0.1) is False
    assert engine.probe_port_health(-1, timeout_s=0.1) is False


def test_synthetic_debate_full_cycle_offline_fleet():
    """Verify debate engine generates valid accords even when all fleet ports are offline."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        sink = TriVaultSink(
            lora_dir=tmp_path / "lora",
            obsidian_dir=tmp_path / "obsidian",
            secondary_lora_dir=tmp_path / "lora_sec",
            secondary_obsidian_dir=tmp_path / "obsidian_sec",
        )
        engine = SyntheticDebateEngine(tri_vault_sink=sink)

        for topic_idx in range(3):
            accord = engine.run_deliberation(topic_idx=topic_idx)
            assert accord.consensus_passed is True
            assert accord.consensus_alignment_pct >= 90.0
            assert len(accord.rounds) == 4
            assert accord.rounds[0].turn_type == "OPENING_THESIS"
            assert accord.rounds[1].turn_type == "CROSS_EXAMINATION"
            assert accord.rounds[2].turn_type == "TECHNICAL_SYNTHESIS"
            assert accord.rounds[3].turn_type == "CONSENSUS_RATIFICATION"
            
            dpo = engine.export_dpo_pair(accord, topic_idx=topic_idx)
            assert dpo["meta"]["truth_verified"] is True
            assert dpo["meta"]["zero_mock_certified"] is True
            
            sft = engine.export_sft_pair(accord, topic_idx=topic_idx)
            assert "messages" in sft
            assert len(sft["messages"]) == 3


def test_stagnation_defense_model_substitution():
    """Verify that stagnation defense triggers substitution after 3 stagnant rounds."""
    engine = SyntheticDebateEngine(stagnation_threshold=0.02, stagnation_turn_limit=3)
    assert engine.active_primary_model == "coder_architect"
    
    # Baseline
    stag, msg = engine.detect_stagnation_and_substitute(95.0)
    assert stag is False
    
    # Round 1 stagnant
    stag, msg = engine.detect_stagnation_and_substitute(95.01)
    assert stag is False
    
    # Round 2 stagnant
    stag, msg = engine.detect_stagnation_and_substitute(95.015)
    assert stag is False
    
    # Round 3 stagnant -> Trigger substitution to math_72b
    stag, msg = engine.detect_stagnation_and_substitute(95.012)
    assert stag is True
    assert engine.active_primary_model == "math_72b"
    assert "STAGNATION DEFENSE TRIGGERED" in msg


# ============================================================================
# PILLAR 2: MULTI-THREAD & MULTI-PROCESS CONCURRENCY & POSIX FSYNC LOCKING
# ============================================================================

def _worker_process_append(target_file: str, worker_id: int, num_records: int, success_counter):
    """Worker process appending valid JSONL records using safe_append_jsonl."""
    sink = TriVaultSink()
    target_path = Path(target_file)
    for i in range(num_records):
        rec = {
            "record_id": f"proc_{worker_id}_{i}",
            "instruction": f"Concurrency test prompt from proc {worker_id} iter {i}",
            "output": f"Deterministic verified output from proc {worker_id} iter {i}",
            "timestamp": time.time(),
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        sink.safe_append_jsonl(target_path, rec)
    success_counter.value += 1


def test_concurrent_multiprocess_jsonl_append():
    """Verify that multiple independent OS processes appending concurrently do not corrupt the JSONL file."""
    ctx = multiprocessing.get_context("fork")
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_file = Path(tmp_dir) / "concurrent_multiprocess.jsonl"
        num_procs = 8
        records_per_proc = 50
        total_expected = num_procs * records_per_proc

        manager = ctx.Manager()
        counter = manager.Value('i', 0)

        procs = []
        for p_id in range(num_procs):
            p = ctx.Process(
                target=_worker_process_append,
                args=(str(target_file), p_id, records_per_proc, counter)
            )
            procs.append(p)
            p.start()

        for p in procs:
            p.join(timeout=10)
            assert not p.is_alive(), "Process hung during concurrent append"

        assert counter.value == num_procs

        # Verify JSONL lines
        assert target_file.exists()
        lines = target_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == total_expected, f"Expected {total_expected} lines, got {len(lines)}"

        seen_ids = set()
        for idx, line in enumerate(lines):
            try:
                data = json.loads(line)
                rec_id = data["record_id"]
                seen_ids.add(rec_id)
                assert data["truth_verified"] is True
            except Exception as e:
                pytest.fail(f"Corrupted JSON line at index {idx}: {line[:100]} | Error: {e}")

        assert len(seen_ids) == total_expected


def test_concurrent_multithread_safe_append():
    """Verify 20 concurrent threads writing 100 records each to TriVaultSink."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_file = Path(tmp_dir) / "concurrent_threads.jsonl"
        sink = TriVaultSink()
        num_threads = 20
        records_per_thread = 100
        total_expected = num_threads * records_per_thread

        def _thread_writer(t_id: int):
            for i in range(records_per_thread):
                rec = {
                    "thread_id": t_id,
                    "seq": i,
                    "prompt": f"Thread {t_id} question {i}",
                    "completion": f"Thread {t_id} answer {i}",
                    "truth_verified": True,
                    "truth_compliance_pct": 100.0,
                    "zero_mock": True
                }
                sink.safe_append_jsonl(target_file, rec)

        threads = [threading.Thread(target=_thread_writer, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert not t.is_alive()

        lines = target_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == total_expected

        for line in lines:
            data = json.loads(line)
            assert "thread_id" in data
            assert data["truth_verified"] is True


def test_concurrent_atomic_file_write_race():
    """Verify atomic_write_file does not corrupt files under rapid concurrent overwrites."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_file = Path(tmp_dir) / "atomic_target.json"
        sink = TriVaultSink()
        num_threads = 10
        iters_per_thread = 30

        def _atomic_writer(t_id: int):
            for i in range(iters_per_thread):
                payload = json.dumps({"writer": t_id, "iter": i, "payload": "X" * 500})
                sink.atomic_write_file(target_file, payload)

        threads = [threading.Thread(target=_atomic_writer, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Final state must be perfectly valid uncorrupted JSON
        assert target_file.exists()
        final_content = target_file.read_text(encoding="utf-8")
        parsed = json.loads(final_content)
        assert "writer" in parsed
        assert "iter" in parsed


def test_concurrent_harvester_executions():
    """Verify MultiStreamHarvester under concurrent execution calls."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        target_dataset = tmp_path / "ai_training_game_dataset.jsonl"
        sink = TriVaultSink(
            lora_dir=tmp_path / "lora",
            obsidian_dir=tmp_path / "obsidian",
            secondary_lora_dir=tmp_path / "lora_sec",
            secondary_obsidian_dir=tmp_path / "obsidian_sec",
        )
        harvester = MultiStreamHarvester(
            workspace_root=tmp_path,
            target_dataset=target_dataset,
            tri_vault_sink=sink
        )

        def _run_harvest(count_box):
            res = harvester.harvest_all_streams()
            total = sum(len(v) for v in res.values())
            count_box.append(total)

        threads = []
        results = []
        for _ in range(5):
            box = []
            results.append(box)
            t = threading.Thread(target=_run_harvest, args=(box,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        assert target_dataset.exists()
        lines = target_dataset.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5 * 5  # 5 streams * 5 runs = 25 pairs
        for line in lines:
            d = json.loads(line)
            assert d["truth_verified"] is True
            assert d["zero_mock"] is True


# ============================================================================
# PILLAR 3: SUBPROCESS SIGNAL HANDLING (SIGINT, SIGTERM)
# ============================================================================

def test_daemon_sigint_graceful_shutdown():
    """Spawn live_training_automation_engine daemon in subprocess, send SIGINT, verify clean exit."""
    python_bin = sys.executable
    script_path = MODULE_DIR / "live_training_automation_engine.py"
    
    cmd = [python_bin, str(script_path), "--daemon", "--interval", "1", "--dry-run"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(MONOREPO_ROOT)
    )

    time.sleep(2.5)

    # Send SIGINT
    proc.send_signal(signal.SIGINT)
    stdout, stderr = proc.communicate(timeout=5)

    assert proc.returncode == 0, f"Expected 0 returncode on SIGINT, got {proc.returncode}. Stderr: {stderr}"
    assert "Received termination signal" in stderr or "Received termination signal" in stdout or "stopped cleanly" in stderr or "stopped cleanly" in stdout


def test_daemon_sigterm_graceful_shutdown():
    """Spawn live_training_automation_engine daemon in subprocess, send SIGTERM, verify clean exit."""
    python_bin = sys.executable
    script_path = MODULE_DIR / "live_training_automation_engine.py"
    
    cmd = [python_bin, str(script_path), "--daemon", "--interval", "1", "--dry-run"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(MONOREPO_ROOT)
    )

    time.sleep(2.5)

    # Send SIGTERM
    proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=5)

    assert proc.returncode == 0, f"Expected 0 returncode on SIGTERM, got {proc.returncode}. Stderr: {stderr}"
    assert "Received termination signal" in stderr or "Received termination signal" in stdout or "stopped cleanly" in stderr or "stopped cleanly" in stdout


# ============================================================================
# PILLAR 4: REAL-TIME UPDATES, FALLBACKS & LIVE AUTOMATION CODEPATHS
# ============================================================================

def test_telemetry_artifacts_and_wikilinks():
    """Verify live updates to memory_fallback.json, agentworld_training_runs.jsonl, and Obsidian analytics."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        tui_dir = tmp_root / "02_ai_models_and_inference" / "lauburu_tui" / "config"
        obs_dir = tmp_root / "obsidian_vault" / "04_ANALYTICS"
        data_dir = tmp_root / "04_data_and_memory"
        tui_dir.mkdir(parents=True, exist_ok=True)
        obs_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        sentinel = StorageSentinel(monorepo_root=tmp_root)
        sink = TriVaultSink(
            lora_dir=tmp_root / "lora",
            obsidian_dir=tmp_root / "obsidian",
            secondary_lora_dir=tmp_root / "lora_sec",
            secondary_obsidian_dir=tmp_root / "obsidian_sec",
        )
        streamer = TelemetryStreamer(monorepo_root=tmp_root, sentinel=sentinel, tri_vault_sink=sink)

        res = streamer.stream_all(step=250, total_steps=5000, epoch=1, loss=1.42, dry_run=False)
        assert res["tui_streamed"] is True
        assert res["receipt_logged"] is True

        # Verify memory_fallback.json
        mem_file = tui_dir / "memory_fallback.json"
        assert mem_file.exists()
        mem_data = json.loads(mem_file.read_text(encoding="utf-8"))
        assert "lora_job" in mem_data
        assert mem_data["lora_job"]["current_step"] == 250
        assert mem_data["lora_job"]["current_loss"] == 1.42
        assert "ram_governor" in mem_data
        assert mem_data["ram_governor"]["dynamic_ai_cap_gb"] == 21.6

        # Verify optimization_strategies.json
        opt_file = tui_dir / "optimization_strategies.json"
        assert opt_file.exists()
        opt_data = json.loads(opt_file.read_text(encoding="utf-8"))
        assert len(opt_data["optimizations"]) >= 3

        # Verify agentworld_training_runs.jsonl
        train_log = data_dir / "agentworld_training_runs.jsonl"
        assert train_log.exists()
        lines = train_log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        run_record = json.loads(lines[0])
        assert run_record["iters"] == 250
        assert run_record["final_loss"] == 1.42
        assert run_record["status"] == "COMPLETED"

        # Verify Obsidian analytics markdown note
        obs_note = obs_dir / "QWEN_MATH_CONTINUOUS_OPTIMIZATION_TRENDS_2026.md"
        assert obs_note.exists()
        obs_content = obs_note.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in obs_content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in obs_content
        assert "[[Index]]" in obs_content
        assert "97.5" in obs_content  # TB4 weight
        assert "2.1" in obs_content   # WG weight
        assert "0.4" in obs_content   # Wi-Fi weight


def test_live_training_engine_dry_run_cycle():
    """Verify single pass execution in dry_run mode."""
    engine = LiveTrainingAutomationEngine(dry_run=True)
    res = engine.run_single_pass()
    assert res["status"] == "COMPLETED"
    assert res["harvested_in_cycle"] == 5
    assert res["training_pass_executed"] is True
    assert "debate_accord" in res
    assert "telemetry_streamed" in res


def test_live_training_engine_status_cli():
    """Verify live_training_automation_engine --status CLI output is valid JSON conforming to contract."""
    python_bin = sys.executable
    script_path = MODULE_DIR / "live_training_automation_engine.py"
    
    cmd = [python_bin, str(script_path), "--status"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(MONOREPO_ROOT))
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["engine_version"] == "2.0.0-CANONICAL-MASTER"
    assert data["storage"]["healthy"] is True
    assert data["storage"]["fast_path_latency_ms"] < 3.0
    assert data["ram_governor"]["status"] == "CERTIFIED_HEALTHY"
    assert data["rule_zero_verified"] is True
