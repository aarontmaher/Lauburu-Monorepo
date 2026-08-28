"""
Unit Tests for Training Telemetry Collector & MPSC Ring Buffer Data Bridge
tests/unit/test_training_telemetry_collector.py

Comprehensive test suite verifying zero-mock physical data collectors and MPSC ring buffer:
  1. MPSCRingBuffer: bounded capacity, push/push_batch, pop_all/drain, peek_latest, multithreaded concurrency.
  2. Ingestion Loop Collector: dynamic file sizing (bytes/MB), buffered line count, growth rates, aux datasets.
  3. Gatekeeper Collector: Devil's Lock Governor integration, lock state, threat level, intercept parsing.
  4. Staged HF Epoch VRAM Gate: memory headroom calculation, Kimi 88B lock detection, gating thresholds.
  5. The 5 Lauburu AI Gyms:
     - Red/Blue Arena (scores, attacks, resistances)
     - Mesh Healing (latency, 5-tier failovers, fault counts)
     - AI Stealth Compute (yield latency, thermal compliance, tensor routes)
     - Software Dev Training Game (13 Subsystem Architects ELO rankings, top 10 priorities)
     - Spatial Grappling 3D (kinematic torque mathematical truth, OPML node counts, Movesense status)
  6. TrainingTelemetryCollector Master Bridge: snapshot aggregation, async loop, thread safety.
"""

import os
import sys
import math
import time
import json
import pytest
import asyncio
import threading
from typing import Dict, Any

# Ensure canonical_port root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.training_telemetry_collector import (
    MPSCRingBuffer,
    count_file_lines_buffered,
    calculate_kinematic_torque,
    get_ingestion_loop_telemetry,
    get_gatekeeper_telemetry,
    get_hf_epoch_vram_gate,
    get_red_blue_arena_telemetry,
    get_mesh_healing_telemetry,
    get_stealth_compute_telemetry,
    get_software_dev_game_telemetry,
    get_spatial_grappling_telemetry,
    get_all_gyms_telemetry,
    TrainingTelemetryCollector,
    training_telemetry_collector,
)


# ============================================================================
# 1. MPSCRingBuffer Unit Tests
# ============================================================================

def test_mpsc_ring_buffer_basic_push_and_pop():
    """Verify basic push, pop_all, peek, and capacity behavior."""
    buf = MPSCRingBuffer(capacity=5)
    assert len(buf) == 0
    assert buf.peek_latest() is None
    assert buf.pop_all() == []

    buf.push({"id": 1})
    buf.push({"id": 2})
    assert len(buf) == 2
    assert buf.peek_latest() == {"id": 2}

    items = buf.pop_all()
    assert len(items) == 2
    assert items[0] == {"id": 1}
    assert items[1] == {"id": 2}
    assert len(buf) == 0
    assert buf.peek_latest() is None


def test_mpsc_ring_buffer_capacity_overflow():
    """Verify ring buffer evicts oldest items when bounded capacity is exceeded."""
    buf = MPSCRingBuffer(capacity=3)
    for i in range(5):
        buf.push(i)

    assert len(buf) == 3
    assert buf.peek_latest() == 4
    drained = buf.drain()
    assert drained == [2, 3, 4]


def test_mpsc_ring_buffer_push_batch_and_clear():
    """Verify push_batch and clear methods."""
    buf = MPSCRingBuffer(capacity=10)
    buf.push_batch(["alpha", "beta", "gamma"])
    assert len(buf) == 3
    assert buf.peek_latest() == "gamma"

    buf.clear()
    assert len(buf) == 0
    assert buf.pop_all() == []


def test_mpsc_ring_buffer_multithreaded_concurrency():
    """Verify thread-safe multi-producer concurrency without data corruption."""
    buf = MPSCRingBuffer(capacity=5000)
    num_threads = 8
    items_per_thread = 250

    def producer(thread_id: int):
        for j in range(items_per_thread):
            buf.push(f"t{thread_id}_{j}")

    threads = [threading.Thread(target=producer, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total_expected = num_threads * items_per_thread
    drained = buf.pop_all()
    assert len(drained) == total_expected
    assert len(buf) == 0


# ============================================================================
# 2. Line Counting & Kinematic Torque Helper Tests
# ============================================================================

def test_count_file_lines_buffered(tmp_path):
    """Verify buffered binary line counting and caching with temp files."""
    test_file = tmp_path / "test_data.jsonl"
    lines = [f'{{"record": {i}}}\n' for i in range(150)]
    test_file.write_text("".join(lines))

    count = count_file_lines_buffered(str(test_file))
    assert count == 150

    # Test missing file
    assert count_file_lines_buffered(str(tmp_path / "non_existent.jsonl")) == 0


def test_calculate_kinematic_torque_math():
    """Verify mathematical calculation of tau = force * r * |sin(theta)|."""
    # Force = 120N, r = 0.35m, theta = 90 deg -> sin(90) = 1.0 -> tau = 42.0 Nm
    torque_90 = calculate_kinematic_torque(lever_arm_m=0.35, angle_deg=90.0, force_n=120.0)
    assert pytest.approx(torque_90, 0.01) == 42.0

    # Force = 120N, r = 0.35m, theta = 0 deg -> sin(0) = 0.0 -> tau = 0.0 Nm
    torque_0 = calculate_kinematic_torque(lever_arm_m=0.35, angle_deg=0.0, force_n=120.0)
    assert torque_0 == 0.0

    # Force = 120N, r = 0.35m, theta = 30 deg -> sin(30) = 0.5 -> tau = 21.0 Nm
    torque_30 = calculate_kinematic_torque(lever_arm_m=0.35, angle_deg=30.0, force_n=120.0)
    assert pytest.approx(torque_30, 0.01) == 21.0

    # Force = 120N, r = 0.40m, theta = 45 deg -> sin(45) = 0.7071 -> tau = 33.94 Nm
    torque_45 = calculate_kinematic_torque(lever_arm_m=0.40, angle_deg=45.0, force_n=120.0)
    assert pytest.approx(torque_45, 0.01) == round(120.0 * 0.40 * math.sin(math.radians(45)), 2)


# ============================================================================
# 3. Ingestion Loop Collector Unit Tests
# ============================================================================

def test_get_ingestion_loop_telemetry_live():
    """Verify live ingestion loop telemetry reading from real filesystem."""
    res = get_ingestion_loop_telemetry()
    assert isinstance(res, dict)
    assert "file_size_bytes" in res
    assert "file_size_mb" in res
    assert "record_count" in res
    assert "growth_rate_bps" in res
    assert "growth_rate_records_per_min" in res
    assert "primary_dataset_path" in res
    assert "primary_dataset_exists" in res
    assert "aux_datasets" in res
    assert "total_aux_datasets_count" in res
    assert "total_dataset_bytes" in res
    assert "total_dataset_mb" in res
    assert "last_updated_iso" in res

    if res["primary_dataset_exists"]:
        assert res["file_size_bytes"] > 0
        assert res["file_size_mb"] > 0
        assert res["record_count"] > 0
        assert res["total_aux_datasets_count"] >= 1


def test_get_ingestion_loop_telemetry_custom_file(tmp_path):
    """Verify ingestion loop collector with custom mock dataset in temp path."""
    fake_file = tmp_path / "custom_lora.jsonl"
    lines = [f'{{"prompt": "task {i}", "completion": "result {i}"}}\n' for i in range(50)]
    fake_file.write_text("".join(lines))

    res = get_ingestion_loop_telemetry(override_path=str(fake_file))
    assert res["primary_dataset_exists"] is True
    assert res["record_count"] == 50
    assert res["file_size_bytes"] == os.path.getsize(str(fake_file))
    assert res["file_size_mb"] == round(res["file_size_bytes"] / (1024.0 * 1024.0), 2)


def test_get_ingestion_loop_telemetry_missing_file(tmp_path):
    """Verify ingestion loop handles non-existent file cleanly without throwing."""
    missing_file = str(tmp_path / "does_not_exist.jsonl")
    res = get_ingestion_loop_telemetry(override_path=missing_file)
    assert res["primary_dataset_exists"] is False
    assert res["file_size_bytes"] == 0
    assert res["record_count"] == 0


# ============================================================================
# 4. Gatekeeper Telemetry Collector Unit Tests
# ============================================================================

def test_get_gatekeeper_telemetry_live():
    """Verify live gatekeeper telemetry queries DevilsLockGovernor and audit logs."""
    res = get_gatekeeper_telemetry()
    assert isinstance(res, dict)
    assert "active_intercepts_count" in res
    assert "lock_state" in res
    assert res["lock_state"] in ["UNLOCKED", "LOCKED", "CONTENTION"]
    assert "resource_cap_active" in res
    assert "active_subagent" in res
    assert "recent_intercepts_log" in res
    assert "threat_level" in res
    assert res["threat_level"] in ["LOW", "ELEVATED", "HIGH"]
    assert "governor_healthy" in res
    assert "last_checked_iso" in res


# ============================================================================
# 5. Staged HuggingFace Epoch & VRAM Gate Unit Tests
# ============================================================================

def test_get_hf_epoch_vram_gate_live():
    """Verify live HF Epoch VRAM gate queries host memory."""
    res = get_hf_epoch_vram_gate()
    assert isinstance(res, dict)
    assert "vram_free_gb" in res
    assert "vram_total_gb" in res
    assert "vram_headroom_pct" in res
    assert "threshold_pct" in res
    assert res["threshold_pct"] == 15.0
    assert "kimi_88b_active" in res
    assert "is_blocked" in res
    assert "gate_status" in res
    assert res["gate_status"] in ["BLOCKED", "UNBLOCKED / READY"]
    assert "status_message" in res


def test_get_hf_epoch_vram_gate_gating_logic():
    """Verify VRAM gate unblocks when headroom >= 15% and blocks when < 15% or Kimi active."""
    # Headroom < 15% -> BLOCKED
    blocked_res = get_hf_epoch_vram_gate(override_free_pct=10.5, override_kimi_active=False)
    assert blocked_res["is_blocked"] is True
    assert blocked_res["gate_status"] == "BLOCKED"
    assert "10.5%" in blocked_res["status_message"]

    # Headroom >= 15% and Kimi inactive -> UNBLOCKED / READY
    ready_res = get_hf_epoch_vram_gate(override_free_pct=35.0, override_kimi_active=False)
    assert ready_res["is_blocked"] is False
    assert ready_res["gate_status"] == "UNBLOCKED / READY"
    assert "UNBLOCKED" in ready_res["status_message"]

    # Headroom >= 15% but Kimi 88B ACTIVE -> BLOCKED
    kimi_blocked_res = get_hf_epoch_vram_gate(override_free_pct=40.0, override_kimi_active=True)
    assert kimi_blocked_res["is_blocked"] is True
    assert kimi_blocked_res["gate_status"] == "BLOCKED"
    assert "Kimi 88B" in kimi_blocked_res["status_message"]


# ============================================================================
# 6. The 5 Lauburu Gyms Unit Tests
# ============================================================================

def test_get_red_blue_arena_telemetry():
    """[Gym 1] Verify Red/Blue Arena telemetry parsing."""
    res = get_red_blue_arena_telemetry()
    assert isinstance(res, dict)
    assert "round" in res
    assert "mode" in res
    assert "global_vram_pool_gb" in res
    assert "team_local_score" in res
    assert "team_cloud_score" in res
    assert "vuln_discovery_rate" in res
    assert "recent_attacks" in res
    assert "resistances" in res
    assert "active_daemons_mesh" in res


def test_get_mesh_healing_telemetry():
    """[Gym 2] Verify Mesh Healing AI Gym telemetry parsing."""
    res = get_mesh_healing_telemetry()
    assert isinstance(res, dict)
    assert "last_recovery_latency_ms" in res
    assert res["last_recovery_latency_ms"] >= 0.0
    assert "active_tier" in res
    assert "tiers_available" in res
    assert len(res["tiers_available"]) == 5
    assert "fault_count" in res
    assert "recent_healing_events" in res
    assert "port_18802_healthy" in res
    assert "wol_status" in res


def test_get_stealth_compute_telemetry():
    """[Gym 3] Verify AI Stealth Compute Arena telemetry parsing."""
    res = get_stealth_compute_telemetry()
    assert isinstance(res, dict)
    assert "yield_latency_ms" in res
    assert res["yield_latency_ms"] <= 5.0  # Must meet sub-5ms foreground yield target
    assert "max_temperature_c" in res
    assert res["max_temperature_c"] <= 58.0  # Silent thermal limit
    assert "tensor_route" in res
    assert isinstance(res["tensor_route"], list)
    assert "doze_whitelisted_apps" in res
    assert "com.termux" in res["doze_whitelisted_apps"]
    assert "silent_thermal_compliant" in res


def test_get_software_dev_game_telemetry():
    """[Gym 4] Verify Software Dev Training Game telemetry parsing."""
    res = get_software_dev_game_telemetry()
    assert isinstance(res, dict)
    assert "overseer" in res
    assert "governance_mode" in res
    assert "leaderboard_entries" in res
    assert "top_10_priorities" in res
    assert "recent_matches" in res

    entries = res["leaderboard_entries"]
    assert len(entries) >= 1
    first = entries[0]
    assert "rank" in first
    assert "spec_id" in first
    assert "elo" in first
    assert "zero_mock_compliance_pct" in first
    assert first["zero_mock_compliance_pct"] == 100.0


def test_get_spatial_grappling_telemetry():
    """[Gym 5] Verify Spatial Grappling 3D telemetry parsing & kinematics."""
    res = get_spatial_grappling_telemetry()
    assert isinstance(res, dict)
    assert "opml_node_count" in res
    assert res["opml_node_count"] >= 955  # Canonical 955+ nodes
    assert "active_positions" in res
    assert "current_torque_nm" in res
    assert res["current_torque_nm"] > 0.0
    assert "joint_torques" in res
    assert "right_elbow" in res["joint_torques"]
    assert "movesense_sync_hz" in res
    assert res["movesense_sync_hz"] in [128, 512]
    assert "movesense_sync_status" in res


def test_get_all_gyms_telemetry():
    """Verify aggregated telemetry for all 5 gyms."""
    all_gyms = get_all_gyms_telemetry()
    assert "red_blue_arena" in all_gyms
    assert "mesh_healing" in all_gyms
    assert "stealth_compute" in all_gyms
    assert "software_dev_game" in all_gyms
    assert "spatial_grappling" in all_gyms


# ============================================================================
# 7. Master Training Telemetry Collector & Async Bridge Tests
# ============================================================================

def test_training_telemetry_collector_snapshot_collection():
    """Verify master collector generates a valid structured snapshot."""
    collector = TrainingTelemetryCollector(buffer_capacity=100)
    snapshot = collector.collect_snapshot()

    assert isinstance(snapshot, dict)
    assert "timestamp_iso" in snapshot
    assert "timestamp_epoch" in snapshot
    assert "ingestion_loop" in snapshot
    assert "gatekeeper" in snapshot
    assert "hf_epoch_vram_gate" in snapshot
    assert "gyms" in snapshot

    # Test push and pop
    collector.push_snapshot()
    assert len(collector.buffer) == 1
    assert collector.peek_latest() is not None

    drained = collector.pop_all()
    assert len(drained) == 1
    assert len(collector.buffer) == 0


@pytest.mark.asyncio
async def test_training_telemetry_collector_async_tick_and_loop():
    """Verify asynchronous collection tick and background loop lifecycle."""
    collector = TrainingTelemetryCollector(buffer_capacity=50)

    # Test single async tick
    snapshot = await collector.async_collect_tick()
    assert snapshot["timestamp_epoch"] > 0
    assert len(collector.buffer) == 1

    # Start loop in background task for a short duration
    loop_task = asyncio.create_task(collector.start_collection_loop(interval_sec=0.05))
    await asyncio.sleep(0.15)
    collector.stop_collection_loop()
    await loop_task

    drained = collector.drain()
    assert len(drained) >= 2


def test_training_telemetry_collector_background_thread():
    """Verify synchronous background thread lifecycle."""
    collector = TrainingTelemetryCollector(buffer_capacity=50)
    collector.start_background_thread(interval_sec=0.05)
    time.sleep(0.15)
    collector.stop_background_thread()

    drained = collector.drain()
    assert len(drained) >= 2
