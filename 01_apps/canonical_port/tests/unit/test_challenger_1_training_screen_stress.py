"""
Adversarial Stress Test Suite: Canonical Port TUI Screen 6 & MPSC Ring Buffer
tests/unit/test_challenger_1_training_screen_stress.py

Empirical Challenger 1 Stress Harness:
  1. High-concurrency MPSC Ring Buffer stress (50 background threads, 50,000 pushes, lock contention, consumer drain).
  2. Telemetry collector background daemon lifecycle (start/stop churn, async ticks, time skew).
  3. Fuzzing & resilience against corrupted / truncated disk files across all 5 AI Gyms and LoRA datasets.
  4. Mathematical & boundary stress for Unicode Braille sparklines and kinematic joint torque.
"""

import os
import sys
import math
import json
import time
import pytest
import tempfile
import threading
import collections
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.training_telemetry_collector import (
    MPSCRingBuffer,
    TrainingTelemetryCollector,
    get_ingestion_loop_telemetry,
    get_gatekeeper_telemetry,
    get_hf_epoch_vram_gate,
    get_red_blue_arena_telemetry,
    get_mesh_healing_telemetry,
    get_stealth_compute_telemetry,
    get_software_dev_game_telemetry,
    get_spatial_grappling_telemetry,
    get_all_gyms_telemetry,
    count_file_lines_buffered,
    calculate_kinematic_torque,
)
from tui.widgets.live_implementation_stream_widget import render_braille_sparkline


# ============================================================================
# 1. HIGH-CONCURRENCY MPSC RING BUFFER ADVERSARIAL STRESS
# ============================================================================

class TestMPSCRingBufferStress:
    """Stress testing the Multi-Producer Single-Consumer (MPSC) bounded ring buffer."""

    def test_50_threads_simultaneous_50k_pushes(self):
        """
        Stress 1.1: 50 concurrent threads pushing 1,000 items each (50,000 total)
        into a bounded ring buffer of capacity 1,000.
        Invariant: Buffer never exceeds capacity, lock never deadlocks, final length == capacity.
        """
        capacity = 1000
        buffer = MPSCRingBuffer(capacity=capacity)
        num_threads = 50
        pushes_per_thread = 1000

        barrier = threading.Barrier(num_threads)
        errors = []

        def worker(thread_id: int):
            try:
                barrier.wait(timeout=5.0)
                for i in range(pushes_per_thread):
                    buffer.push({"thread": thread_id, "seq": i, "val": thread_id * 1000 + i})
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {e}")

        threads = [threading.Thread(target=worker, args=(t,), daemon=True) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Thread errors encountered: {errors}"
        assert len(buffer) == capacity, f"Expected buffer length {capacity}, got {len(buffer)}"

        # Verify drain operates cleanly
        drained = buffer.drain()
        assert len(drained) == capacity
        assert len(buffer) == 0

    def test_concurrent_producers_and_continuous_consumer(self):
        """
        Stress 1.2: 20 concurrent producer threads pushing while a consumer continuously drains.
        Invariant: Total drained items == total items pushed that were not evicted, no lost/corrupted packets.
        """
        buffer = MPSCRingBuffer(capacity=5000)
        num_producers = 20
        pushes_per_producer = 500
        stop_event = threading.Event()
        consumed_items = []
        consumer_lock = threading.Lock()

        def producer_worker(pid: int):
            for i in range(pushes_per_producer):
                buffer.push((pid, i))
                time.sleep(0.0001)

        def consumer_worker():
            while not stop_event.is_set():
                items = buffer.pop_all()
                if items:
                    with consumer_lock:
                        consumed_items.extend(items)
                time.sleep(0.0005)
            # Final drain
            items = buffer.pop_all()
            with consumer_lock:
                consumed_items.extend(items)

        consumer = threading.Thread(target=consumer_worker, daemon=True)
        consumer.start()

        producers = [threading.Thread(target=producer_worker, args=(p,), daemon=True) for p in range(num_producers)]
        for p in producers:
            p.start()
        for p in producers:
            p.join(timeout=10.0)

        time.sleep(0.05)
        stop_event.set()
        consumer.join(timeout=3.0)

        total_expected = num_producers * pushes_per_producer
        with consumer_lock:
            total_consumed = len(consumed_items)

        assert total_consumed == total_expected, f"Expected {total_expected} consumed items, got {total_consumed}"

    def test_push_batch_interleaving_and_capacity_bound(self):
        """
        Stress 1.3: Interleaving single pushes and large batch pushes across 10 threads.
        """
        buffer = MPSCRingBuffer(capacity=500)
        num_threads = 10
        barrier = threading.Barrier(num_threads)

        def worker(tid: int):
            barrier.wait(timeout=3.0)
            # Push batch of 50 items
            buffer.push_batch([f"batch-{tid}-{i}" for i in range(50)])
            # Push 50 single items
            for i in range(50):
                buffer.push(f"single-{tid}-{i}")

        threads = [threading.Thread(target=worker, args=(t,), daemon=True) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(buffer) == 500
        latest = buffer.peek_latest()
        assert latest is not None
        buffer.clear()
        assert len(buffer) == 0
        assert buffer.peek_latest() is None

    def test_zero_and_minimal_capacity_edge_cases(self):
        """
        Stress 1.4: Extreme buffer capacities: 1 element, 0 elements.
        """
        # Capacity 1
        b1 = MPSCRingBuffer(capacity=1)
        b1.push("alpha")
        assert len(b1) == 1
        assert b1.peek_latest() == "alpha"
        b1.push("beta")
        assert len(b1) == 1
        assert b1.peek_latest() == "beta"
        assert b1.drain() == ["beta"]
        assert len(b1) == 0

        # Capacity 0
        b0 = MPSCRingBuffer(capacity=0)
        b0.push("gamma")
        assert len(b0) == 0
        assert b0.peek_latest() is None
        assert b0.drain() == []


# ============================================================================
# 2. TELEMETRY COLLECTOR LIFECYCLE & ASYNC LOOP STRESS
# ============================================================================

class TestCollectorLifecycleAndAsyncStress:
    """Stress testing the collector background daemon and asynchronous polling loop."""

    def test_rapid_thread_start_stop_churn(self):
        """
        Stress 2.1: Rapidly start and stop the background collector thread 50 times.
        Invariant: No thread leaks, no orphaned threads, clean state transitions.
        """
        collector = TrainingTelemetryCollector(buffer_capacity=100)
        for i in range(50):
            collector.start_background_thread(interval_sec=0.01)
            assert collector._thread is not None and collector._thread.is_alive()
            collector.stop_background_thread()
            assert not collector._thread.is_alive()

    @pytest.mark.asyncio
    async def test_async_collect_ticks_burst(self):
        """
        Stress 2.2: 50 rapid asynchronous telemetry collection ticks in asyncio loop.
        """
        collector = TrainingTelemetryCollector(buffer_capacity=200)
        for _ in range(50):
            snap = await collector.async_collect_tick()
            assert "timestamp_iso" in snap
            assert "ingestion_loop" in snap
            assert "gatekeeper" in snap
            assert "hf_epoch_vram_gate" in snap
            assert "gyms" in snap

        assert len(collector.buffer) == 50
        drained = collector.drain()
        assert len(drained) == 50

    def test_line_counter_cache_eviction_and_stress(self, tmp_path):
        """
        Stress 2.3: Generate 120 unique temporary files to trigger the >100 cache eviction in count_file_lines_buffered.
        """
        for i in range(120):
            p = tmp_path / f"test_file_{i}.txt"
            p.write_text(f"line1\nline2\nline3\nline4\nline{i}\n")
            c = count_file_lines_buffered(str(p))
            assert c == 5

        # Re-verify caching returns correct lines without error
        p_check = tmp_path / "test_file_0.txt"
        assert count_file_lines_buffered(str(p_check)) == 5


# ============================================================================
# 3. CORRUPTED & MALFORMED FILE RECOVERY (ZERO-CRASH AUDIT)
# ============================================================================

class TestCorruptedFileRecoveryZeroCrash:
    """Stress testing the collectors against truncated, malformed, non-UTF8, and missing files."""

    def test_red_blue_arena_corrupted_json(self, tmp_path):
        """
        Stress 3.1: Red/Blue Arena given truncated JSON, non-dict root, empty file.
        """
        p_trunc = tmp_path / "arena_trunc.json"
        p_trunc.write_text('{"round": 15, "factions": {"TEAM_LOCAL": ')
        res = get_red_blue_arena_telemetry(override_path=str(p_trunc))
        assert res["mode"] == "TEAM_VS_TEAM_FACTION_WAR"
        assert res["round"] == 0

        p_array = tmp_path / "arena_array.json"
        p_array.write_text('[1, 2, 3, "invalid"]')
        res2 = get_red_blue_arena_telemetry(override_path=str(p_array))
        assert res2["mode"] == "TEAM_VS_TEAM_FACTION_WAR"

    def test_mesh_healing_corrupted_json(self, tmp_path):
        """
        Stress 3.2: Mesh Healing Gym given malformed JSON and negative latencies.
        """
        p_malformed = tmp_path / "mesh_bad.json"
        p_malformed.write_text('{"results": {"node1": "not-a-dict", "node2": {"recovery_time_sec": "invalid"}}}')
        res = get_mesh_healing_telemetry(override_path=str(p_malformed))
        assert res["active_tier"].startswith("Tier 1")
        assert len(res["tiers_available"]) == 5

    def test_stealth_compute_corrupted_json(self, tmp_path):
        """
        Stress 3.3: Stealth Compute Gym given garbage JSON.
        """
        p_bad = tmp_path / "stealth_bad.json"
        p_bad.write_text('{"best_path": null, "fitness": "not-a-float"}')
        res = get_stealth_compute_telemetry(override_path=str(p_bad))
        assert res["yield_latency_ms"] <= 5.0
        assert res["silent_thermal_compliant"] is True

    def test_software_dev_game_corrupted_json(self, tmp_path):
        """
        Stress 3.4: Software Dev Game given non-existent and malformed ranking entries.
        """
        p_bad = tmp_path / "lb_bad.json"
        p_bad.write_text('{"rankings": [{"invalid": true}, "string-entry", null]}')
        res = get_software_dev_game_telemetry(override_path=str(p_bad))
        assert "leaderboard_entries" in res
        assert len(res["leaderboard_entries"]) == 1  # only the dict is processed

    def test_spatial_grappling_corrupted_opml(self, tmp_path):
        """
        Stress 3.5: Spatial Grappling given corrupted / invalid XML OPML files.
        """
        # Truncated XML
        p_xml = tmp_path / "corrupted.opml"
        p_xml.write_text('<?xml version="1.0"?><opml><head><title>Test</title></head><body><outline text="pos"')
        res = get_spatial_grappling_telemetry(override_path=str(p_xml))
        assert res["opml_node_count"] == 955  # Fallback to canonical count
        assert res["current_torque_nm"] > 0

        # Binary garbage XML
        p_bin = tmp_path / "garbage.opml"
        p_bin.write_bytes(b"\x00\xff\xfe\x00\x80\x90\xaa\xbb\xcc\xdd")
        res_bin = get_spatial_grappling_telemetry(override_path=str(p_bin))
        assert res_bin["opml_node_count"] == 955

    def test_ingestion_loop_binary_and_non_utf8_dataset(self, tmp_path):
        """
        Stress 3.6: continuous_lora_dataset.jsonl with corrupted non-UTF-8 bytes and enormous single lines.
        """
        p_data = tmp_path / "continuous_lora_dataset.jsonl"
        # Write 5 valid lines and 2 binary corrupted lines
        content = b'{"instruction": "test 1"}\n\xff\xfe\x00\x12\n{"instruction": "test 2"}\n' + (b"A" * 100000) + b'\n{"instruction": "test 3"}\n'
        p_data.write_bytes(content)

        res = get_ingestion_loop_telemetry(override_path=str(p_data))
        assert res["file_size_bytes"] > 100000
        assert res["record_count"] >= 4
        assert res["primary_dataset_exists"] is True


# ============================================================================
# 4. BRAILLE SPARKLINES & MATHEMATICAL BOUNDARIES STRESS
# ============================================================================

class TestBrailleSparklinesAndMathStress:
    """Stress testing Unicode Braille rendering and joint torque mathematical formulas."""

    def test_braille_sparkline_extreme_boundaries(self):
        """
        Stress 4.1: Unicode Braille sparklines under extreme array conditions.
        """
        # Empty array
        assert render_braille_sparkline([]) == "⠂"

        # Single element
        assert len(render_braille_sparkline([50.0])) >= 1

        # Constant flat values (span = 0)
        flat = render_braille_sparkline([42.0, 42.0, 42.0, 42.0])
        assert len(flat) >= 2
        for char in flat:
            assert ord(char) >= 0x2800

        # Inverted min/max
        inv = render_braille_sparkline([10.0, 20.0, 30.0], min_val=100.0, max_val=0.0)
        assert len(inv) >= 1

        # Massive values
        huge = render_braille_sparkline([1e12, 5e12, 1e13, 2e13])
        assert len(huge) >= 2

        # 10,000 float elements rendering performance
        large_arr = [math.sin(i / 10.0) * 50.0 + 50.0 for i in range(10000)]
        t0 = time.perf_counter()
        spark = render_braille_sparkline(large_arr)
        t1 = time.perf_counter()
        assert len(spark) == 5000
        assert (t1 - t0) < 0.1, f"Rendering 10,000 points took too long: {t1 - t0:.4f}s"

    def test_kinematic_torque_formula_adversarial_angles(self):
        """
        Stress 4.2: Kinematic joint torque tau = 120 * r * |sin(theta)| across boundary angles.
        """
        # 0 degrees -> 0 Nm
        assert calculate_kinematic_torque(0.5, 0.0) == 0.0

        # 180 degrees -> 0 Nm
        assert calculate_kinematic_torque(0.5, 180.0) == 0.0

        # 360 degrees -> 0 Nm
        assert calculate_kinematic_torque(0.5, 360.0) == 0.0

        # 90 degrees -> 120 * 0.5 * 1.0 = 60.0 Nm
        assert calculate_kinematic_torque(0.5, 90.0) == 60.0

        # 270 degrees -> 120 * 0.5 * |-1.0| = 60.0 Nm
        assert calculate_kinematic_torque(0.5, 270.0) == 60.0

        # Negative angle -90 degrees -> 60.0 Nm
        assert calculate_kinematic_torque(0.5, -90.0) == 60.0

        # Zero lever arm -> 0 Nm
        assert calculate_kinematic_torque(0.0, 45.0) == 0.0

        # Huge angle (720 + 90 = 810 deg) -> 60.0 Nm
        assert calculate_kinematic_torque(0.5, 810.0) == 60.0
