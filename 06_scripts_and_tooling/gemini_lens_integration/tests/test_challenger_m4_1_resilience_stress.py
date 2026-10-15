"""Empirical Adversarial Stress Test Suite for Milestone 4 (resilience.py).

Authored by challenger_m4_1 (Milestone 4 Challenger 1: Adversarial Resilience & Queue Stress).
Evaluates:
1. Exponential backoff progression (steps 0-10) with 32.0s ceiling and 1,000-sample jitter envelopes.
2. 60.0s HTTP 429 cooldown state machine, circuit breaker transitions, and RateLimitCooldownError.
3. Offline queue resilience under extreme conditions:
   - Empty files, whitespace-only files, partial JSON, corrupted non-JSON strings, non-dict JSON lines.
   - Partial sender failures and attempt count increments.
   - High-concurrency 50-thread queuing stress and empirical race-condition / data-loss audits.
4. Darwin Mach host RAM sanctuary auditing using authentic Darwin Mach syscalls.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import random
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from resilience import (
    DEFAULT_COOLDOWN_PERIOD_SECONDS,
    DEFAULT_MAX_BACKOFF_SECONDS,
    DEFAULT_MIN_RAM_SANCTUARY_GB,
    CircuitBreakerState,
    MemorySanctuaryViolationError,
    RateLimitCooldownError,
    ResilienceError,
    ResilienceManager,
)


# =============================================================================
# Challenge 1: Exponential Backoff & Jitter Envelopes
# =============================================================================

class TestChallenge1BackoffAndJitter:
    """Challenge 1: Assert strict mathematical backoff progression and jitter boundaries."""

    def test_backoff_step_progression_and_strict_ceiling(self):
        """Asserts step 0, 1, 2, 3, 4, 5, 10 calculations with strict capping at 32.0s."""
        mgr = ResilienceManager(max_retry_backoff=32.0)

        # Mathematical steps: 2^0=1, 2^1=2, 2^2=4, 2^3=8, 2^4=16, 2^5=32, 2^10=1024 -> capped at 32
        steps = [0, 1, 2, 3, 4, 5, 10]
        expected = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 32.0]

        for step, exp in zip(steps, expected):
            calculated = mgr.calculate_backoff(step, base_backoff=1.0, max_backoff=32.0, jitter=False)
            assert calculated == exp, f"Step {step}: expected {exp}s, got {calculated}s"

    def test_jitter_envelope_1000_samples_strictly_positive(self):
        """Asserts jitter stays within [0.5 * delay, 1.5 * delay] and is strictly positive across 1,000 samples."""
        mgr = ResilienceManager(max_retry_backoff=32.0)
        steps = [0, 1, 2, 3, 4, 5, 10]

        for step in steps:
            nominal_delay = min(1.0 * (2.0 ** step), 32.0)
            lower_bound = 0.5 * nominal_delay
            upper_bound = 1.5 * nominal_delay

            samples = [
                mgr.calculate_backoff(step, base_backoff=1.0, max_backoff=32.0, jitter=True)
                for _ in range(1000)
            ]

            assert len(samples) == 1000
            for s in samples:
                assert s > 0.0, f"Jitter sample must be strictly positive: {s}"
                assert lower_bound <= s <= upper_bound, (
                    f"Step {step}: jitter sample {s} outside [{lower_bound}, {upper_bound}]"
                )


# =============================================================================
# Challenge 2: 60s Cooldown State Machine & Circuit Breaker
# =============================================================================

class TestChallenge2CooldownStateMachine:
    """Challenge 2: Assert 60s cooldown state machine and RateLimitCooldownError."""

    def test_cooldown_activation_and_blocking(self):
        """Trigger simulated HTTP 429 via record_rate_limit(60.0) and assert blocking."""
        mgr = ResilienceManager(cooldown_period_seconds=60.0)

        assert mgr.is_cooling_down() is False
        assert mgr.should_dispatch_call() is True
        assert mgr.circuit.state == "CLOSED"

        # Trigger 429 cooldown
        mgr.record_rate_limit(cooldown_seconds=60.0)

        assert mgr.is_cooling_down() is True
        assert mgr.should_dispatch_call() is False
        assert mgr.circuit.state == "OPEN"
        assert mgr.get_cooldown_remaining() > 0.0
        assert mgr.get_cooldown_remaining() <= 60.0

    def test_execute_with_retry_raises_ratelimitcooldownerror(self):
        """Asserts execute_with_retry raises RateLimitCooldownError while cooling down."""
        mgr = ResilienceManager()
        mgr.record_rate_limit(60.0)

        call_executed = False

        def mock_call():
            nonlocal call_executed
            call_executed = True
            return "SUCCESS"

        with pytest.raises(RateLimitCooldownError) as exc_info:
            mgr.execute_with_retry(mock_call)

        assert call_executed is False
        assert "Rate limit cooldown active" in str(exc_info.value)

    def test_cooldown_expiration_and_recovery(self):
        """Asserts cooldown expires when simulated time advances past cooldown_until."""
        mgr = ResilienceManager()
        mgr.record_rate_limit(0.05)  # 50ms cooldown

        assert mgr.is_cooling_down() is True
        time.sleep(0.06)
        assert mgr.is_cooling_down() is False
        assert mgr.should_dispatch_call() is True

        # Now call succeeds
        res = mgr.execute_with_retry(lambda: "recovered", use_jitter=False)
        assert res == "recovered"


# =============================================================================
# Challenge 3: Offline Queue Under Adverse Conditions & Concurrency
# =============================================================================

class TestChallenge3OfflineQueueStress:
    """Challenge 3: Offline queue under corrupted data, partial lines, and concurrency."""

    def test_corrupted_json_lines_partial_lines_interleaved_garbage(self, tmp_path: Path):
        """Asserts corrupt/partial lines are skipped/quarantined without throwing exceptions or blocking valid records."""
        q_path = tmp_path / "corrupt_queue.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        # Adverse file content with corrupted lines, truncated JSON, empty lines, and valid records
        adverse_content = (
            "\n"                                                       # Empty line 1
            "NOT_JSON_GARBAGE_LINE\n"                                  # Plain garbage
            '{"incomplete_json": \n'                                   # Truncated JSON
            '{"record_id": "rec_001", "payload": {"item": "first"}}\n' # Valid record 1
            "   \n"                                                    # Whitespace line
            "[1, 2, 3, 4]\n"                                           # Valid JSON array (not dict)
            '"a raw string"\n'                                         # Valid JSON string (not dict)
            '{"record_id": "rec_002", "payload": {"item": "second"}}\n'# Valid record 2
            "--- EOF CORRUPT MARKER ---\n"                             # EOF corruption
        )
        q_path.write_text(adverse_content, encoding="utf-8")

        received: List[Dict[str, Any]] = []

        def sender(p: Dict[str, Any]) -> bool:
            received.append(p)
            return True

        # Drain must succeed without throwing exceptions
        drained_count = mgr.drain_offline_queue(sender)

        assert drained_count == 2
        assert len(received) == 2
        assert received[0] == {"item": "first"}
        assert received[1] == {"item": "second"}

    def test_empty_and_whitespace_only_queue_files(self, tmp_path: Path):
        """Asserts empty files and whitespace files return 0 without errors."""
        q_path = tmp_path / "empty_q.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        # Empty file
        q_path.touch()
        assert mgr.drain_offline_queue(lambda p: True) == 0

        # Whitespace file
        q_path.write_text("   \n\t\n\n", encoding="utf-8")
        assert mgr.drain_offline_queue(lambda p: True) == 0

    def test_partial_sender_failure_preserves_remaining_records(self, tmp_path: Path):
        """Asserts that if sender fails on record 2, remaining records are preserved with updated attempt counts."""
        q_path = tmp_path / "partial_fail_queue.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        # Queue 3 records
        mgr.queue_offline_payload({"id": "rec1"})
        mgr.queue_offline_payload({"id": "rec2"})
        mgr.queue_offline_payload({"id": "rec3"})

        processed = []

        def flaky_sender(payload: Dict[str, Any]) -> bool:
            if payload.get("id") == "rec2":
                raise ConnectionError("Network collapsed on rec2")
            processed.append(payload.get("id"))
            return True

        drained = mgr.drain_offline_queue(flaky_sender)
        assert drained == 1
        assert processed == ["rec1"]

        # Verify queue still exists and contains rec2 and rec3
        assert q_path.exists()
        lines = [json.loads(l) for l in q_path.read_text(encoding="utf-8").strip().splitlines()]
        assert len(lines) == 2
        assert lines[0]["payload"]["id"] == "rec2"
        assert lines[0]["attempts"] == 2  # incremented attempts
        assert lines[1]["payload"]["id"] == "rec3"

    def test_50_concurrent_threads_queuing_only(self, tmp_path: Path):
        """Asserts 50 concurrent threads appending records produce 100% valid JSONL records."""
        q_path = tmp_path / "50_threads_queue.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        def worker(tid: int):
            for i in range(10):
                mgr.queue_offline_payload({"thread_id": tid, "item": i, "data": "payload_" * 20})

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = q_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 500, f"Expected 500 lines, found {len(lines)}"

        for idx, line in enumerate(lines):
            parsed = json.loads(line)
            assert "record_id" in parsed
            assert "sha256" in parsed
            assert "payload" in parsed
            assert parsed["payload"]["data"].startswith("payload_")

    def test_vulnerability_audit_interleaved_queue_loss_during_drain(self, tmp_path: Path):
        """Adversarial Challenge: Exposes potential data loss if payload is queued during active drain.

        In the un-synchronized implementation, if queue_offline_payload appends to target
        while drain_offline_queue is executing, the replacement or unlinking of target
        can silently delete the newly appended record.
        """
        q_path = tmp_path / "interleaved_audit.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        # Seed 1 record
        mgr.queue_offline_payload({"id": "seed_item"})

        interleaved_loss_detected = False

        def sender_interleaving(payload: Dict[str, Any]) -> bool:
            # During sender execution, simulate another thread queuing a new payload
            mgr.queue_offline_payload({"id": "interleaved_item"})
            return True

        mgr.drain_offline_queue(sender_interleaving)

        # Check if interleaved_item survived
        if not q_path.exists():
            interleaved_loss_detected = True
        else:
            lines = [json.loads(l) for l in q_path.read_text(encoding="utf-8").strip().splitlines()]
            remaining_ids = [l["payload"]["id"] for l in lines]
            if "interleaved_item" not in remaining_ids:
                interleaved_loss_detected = True

        # Assert fix verification: interleaved record MUST survive in queue
        assert interleaved_loss_detected is False, (
            "Interleaved record lost: queue synchronization failed"
        )
        assert q_path.exists(), "Queue file must exist with preserved interleaved item"
        lines = [json.loads(l) for l in q_path.read_text(encoding="utf-8").strip().splitlines()]
        remaining_ids = [l["payload"]["id"] for l in lines]
        assert "interleaved_item" in remaining_ids, "Interleaved item must be preserved in queue"

    def test_50_concurrent_threads_queuing_and_draining_simultaneously(self, tmp_path: Path):
        """Adversarial Challenge: 50 threads (25 producers, 25 consumers) simultaneously queue and drain.

        Asserts 100% record conservation:
        - Exactly 250 items queued (25 threads * 10 items).
        - Exactly 250 items drained with zero dropped records.
        - Zero duplicate drained items.
        - Queue file cleanly unlinked when all items are drained.
        """
        q_path = tmp_path / "50_threads_simultaneous.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        drained_items: List[str] = []
        drained_lock = threading.Lock()

        def sender(payload: Dict[str, Any]) -> bool:
            with drained_lock:
                drained_items.append(payload["id"])
            return True

        stop_event = threading.Event()

        def producer(tid: int):
            for i in range(10):
                mgr.queue_offline_payload({"id": f"p_{tid}_{i}", "data": "stress_data"})
                time.sleep(0.0005)

        def consumer():
            while not stop_event.is_set():
                mgr.drain_offline_queue(sender)
                time.sleep(0.001)
            mgr.drain_offline_queue(sender)

        producers = [threading.Thread(target=producer, args=(t,)) for t in range(25)]
        consumers = [threading.Thread(target=consumer) for _ in range(25)]

        for c in consumers:
            c.start()
        for p in producers:
            p.start()

        for p in producers:
            p.join()

        # Let consumers drain remaining in-flight records
        time.sleep(0.05)
        stop_event.set()
        for c in consumers:
            c.join()

        # Final drain to flush any residue
        mgr.drain_offline_queue(sender)

        expected_count = 25 * 10
        actual_count = len(drained_items)
        unique_count = len(set(drained_items))

        assert actual_count == expected_count, (
            f"Record loss detected: expected {expected_count}, got {actual_count}"
        )
        assert unique_count == expected_count, (
            f"Duplicate records detected: expected {expected_count}, unique was {unique_count}"
        )
        assert not q_path.exists(), "Queue file should be unlinked after all records are drained"

    def test_concurrent_queue_append_during_active_slow_drain(self, tmp_path: Path):
        """Adversarial Challenge: Background thread concurrently appends while active drain is slowly running.

        Verifies that records appended during drain execution are safely preserved and not clobbered.
        """
        q_path = tmp_path / "slow_drain_concurrent_append.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        # Seed initial records
        for i in range(5):
            mgr.queue_offline_payload({"id": f"seed_{i}"})

        drained_in_pass1: List[str] = []
        drained_in_pass2: List[str] = []

        def slow_sender(payload: Dict[str, Any]) -> bool:
            drained_in_pass1.append(payload["id"])
            # Inject simulated slow processing
            time.sleep(0.02)
            return True

        def concurrent_appender():
            time.sleep(0.01)  # wait for drain to start
            for i in range(5):
                mgr.queue_offline_payload({"id": f"concurrent_{i}"})
                time.sleep(0.005)

        appender_thread = threading.Thread(target=concurrent_appender)
        appender_thread.start()

        # Execute first drain pass
        drained_count1 = mgr.drain_offline_queue(slow_sender)
        appender_thread.join()

        # Execute second drain pass to drain newly appended items
        def fast_sender(payload: Dict[str, Any]) -> bool:
            drained_in_pass2.append(payload["id"])
            return True

        drained_count2 = mgr.drain_offline_queue(fast_sender)

        total_drained = drained_in_pass1 + drained_in_pass2
        expected_ids = {f"seed_{i}" for i in range(5)} | {f"concurrent_{i}" for i in range(5)}

        assert len(total_drained) == 10, f"Expected 10 total drained, got {len(total_drained)}"
        assert set(total_drained) == expected_ids, (
            f"Missing or mismatched IDs: expected {expected_ids}, got {set(total_drained)}"
        )
        assert not q_path.exists(), "Queue file must be unlinked after second drain pass"

    def test_corrupt_line_isolation_under_heavily_fragmented_json_lines(self, tmp_path: Path):
        """Adversarial Challenge: Severely fragmented, multi-line, and malformed JSON entries.

        Ensures corrupted lines, non-dict primitives, and fragmented chunks are quarantined/isolated
        while 100% of valid records are successfully dispatched.
        """
        q_path = tmp_path / "fragmented_queue.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        fragmented_content = (
            "   \n"
            "{\"broken_unclosed\": \n"
            "{\n"
            "\"key_without_val\": \n"
            "true\n"
            "42\n"
            "\"plain_string\"\n"
            "[1, 2, 3]\n"
            "null\n"
            "{\"record_id\": \"valid_1\", \"payload\": {\"item\": 101}}\n"
            "{\"half\": 1, \"other_half\": \n"
            "{\"nested_broken\": {\"a\": \n"
            "{\"record_id\": \"valid_2\", \"payload\": {\"item\": 102}}\n"
            "{\"record_id\": \"valid_3\", \"payload\": {\"item\": 103}}\n"
            "--- CORRUPT TRAILER ---\n"
        )
        q_path.write_text(fragmented_content, encoding="utf-8")

        drained_items: List[Dict[str, Any]] = []

        def sender(p: Dict[str, Any]) -> bool:
            drained_items.append(p)
            return True

        drained = mgr.drain_offline_queue(sender)

        assert drained == 3, f"Expected 3 valid drained records, got {drained}"
        assert len(drained_items) == 3
        assert [p["item"] for p in drained_items] == [101, 102, 103]
        assert not q_path.exists(), "Queue should be cleanly unlinked after draining all valid records"

    def test_post_drain_file_replacement_and_toctou_safety(self, tmp_path: Path):
        """Adversarial Challenge: TOCTOU and file replacement resilience.

        Tests non-existent files, 0-byte files, and external file removal
        during drain attempts without raising unhandled exceptions.
        """
        q_path = tmp_path / "toctou_test.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        # 1. Non-existent file
        assert mgr.drain_offline_queue(lambda p: True) == 0

        # 2. 0-byte file
        q_path.touch()
        assert mgr.drain_offline_queue(lambda p: True) == 0
        assert q_path.exists()

        # 3. Valid record seeded, drained cleanly
        mgr.queue_offline_payload({"id": "toctou_item"})
        assert q_path.exists()
        drained = mgr.drain_offline_queue(lambda p: True)
        assert drained == 1
        assert not q_path.exists()

        # 4. Drain again after file unlinked
        assert mgr.drain_offline_queue(lambda p: True) == 0

    def test_concurrent_flaky_sender_with_partial_failures_under_load(self, tmp_path: Path):
        """Adversarial Challenge: 50 concurrent threads with 20% simulated network failure rate.

        Verifies that partial sender failures correctly preserve remaining records,
        increment attempt counts, and allow eventual full recovery with zero lost items.
        """
        q_path = tmp_path / "flaky_load_test.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        drained_items: List[str] = []
        drained_lock = threading.Lock()

        def flaky_sender(payload: Dict[str, Any]) -> bool:
            # 20% transient failure rate
            if random.random() < 0.2:
                return False
            with drained_lock:
                drained_items.append(payload["id"])
            return True

        def perfect_sender(payload: Dict[str, Any]) -> bool:
            with drained_lock:
                drained_items.append(payload["id"])
            return True

        stop_event = threading.Event()

        def producer(tid: int):
            for i in range(10):
                mgr.queue_offline_payload({"id": f"flaky_{tid}_{i}"})
                time.sleep(0.0005)

        def consumer():
            while not stop_event.is_set():
                mgr.drain_offline_queue(flaky_sender)
                time.sleep(0.001)

        producers = [threading.Thread(target=producer, args=(t,)) for t in range(25)]
        consumers = [threading.Thread(target=consumer) for _ in range(25)]

        for c in consumers:
            c.start()
        for p in producers:
            p.start()

        for p in producers:
            p.join()
        time.sleep(0.05)
        stop_event.set()
        for c in consumers:
            c.join()

        # Flush remaining records with perfect sender
        for _ in range(10):
            if not q_path.exists():
                break
            mgr.drain_offline_queue(perfect_sender)

        expected_count = 25 * 10
        actual_count = len(drained_items)
        unique_count = len(set(drained_items))

        assert actual_count == expected_count, (
            f"Record loss with flaky sender: expected {expected_count}, got {actual_count}"
        )
        assert unique_count == expected_count, (
            f"Duplicates with flaky sender: expected {expected_count}, got {unique_count}"
        )
        assert not q_path.exists(), "Queue file should be unlinked after all records are drained"

    def test_concurrent_burst_appends_during_multi_step_slow_drain(self, tmp_path: Path):
        """Adversarial Challenge: 5 concurrent threads burst-queue records during slow drain.

        Verifies 100% data conservation across multiple drain passes with simulated latency.
        """
        q_path = tmp_path / "burst_slow_drain.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        for i in range(10):
            mgr.queue_offline_payload({"id": f"seed_{i}"})

        drained_all: List[str] = []
        drained_lock = threading.Lock()

        def slow_sender(payload: Dict[str, Any]) -> bool:
            with drained_lock:
                drained_all.append(payload["id"])
            time.sleep(0.005)
            return True

        def appender(tid: int):
            for i in range(10):
                mgr.queue_offline_payload({"id": f"burst_{tid}_{i}"})
                time.sleep(0.002)

        threads = [threading.Thread(target=appender, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()

        # Run drain in parallel with appenders
        drain_thread = threading.Thread(target=lambda: mgr.drain_offline_queue(slow_sender))
        drain_thread.start()

        for t in threads:
            t.join()
        drain_thread.join()

        # Final drain pass to flush any records appended after first drain's read
        while q_path.exists():
            mgr.drain_offline_queue(slow_sender)

        expected_count = 10 + (5 * 10)  # 60
        assert len(drained_all) == expected_count, (
            f"Expected {expected_count} records, got {len(drained_all)}"
        )
        assert len(set(drained_all)) == expected_count, (
            f"Duplicate records found: unique {len(set(drained_all))} vs expected {expected_count}"
        )
        assert not q_path.exists(), "Queue file must be unlinked"

    def test_sender_interleaving_with_partial_failure(self, tmp_path: Path):
        """Adversarial Challenge: Interleaved queueing combined with mid-drain failure.

        Verifies that when a sender queues new records and subsequently fails, both the
        interleaved records and remaining un-drained records are preserved with correct attempts.
        """
        q_path = tmp_path / "interleave_fail.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        mgr.queue_offline_payload({"id": "seed_0"})
        mgr.queue_offline_payload({"id": "seed_1"})
        mgr.queue_offline_payload({"id": "seed_2"})

        drained_first_pass: List[str] = []

        def failing_sender(payload: Dict[str, Any]) -> bool:
            pid = payload["id"]
            if pid == "seed_0":
                mgr.queue_offline_payload({"id": "interleaved_after_0"})
                drained_first_pass.append(pid)
                return True
            elif pid == "seed_1":
                mgr.queue_offline_payload({"id": "interleaved_after_1"})
                drained_first_pass.append(pid)
                return True
            elif pid == "seed_2":
                raise ConnectionResetError("Connection reset on seed_2")
            return True

        drained_count = mgr.drain_offline_queue(failing_sender)
        assert drained_count == 2
        assert drained_first_pass == ["seed_0", "seed_1"]

        # Verify queue still exists and contains seed_2, interleaved_after_0, interleaved_after_1
        assert q_path.exists()
        lines = [json.loads(l) for l in q_path.read_text(encoding="utf-8").strip().splitlines()]
        remaining_ids = [l["payload"]["id"] for l in lines]
        assert "seed_2" in remaining_ids
        assert "interleaved_after_0" in remaining_ids
        assert "interleaved_after_1" in remaining_ids

        # Verify seed_2 attempts incremented
        seed_2_rec = next(l for l in lines if l["payload"]["id"] == "seed_2")
        assert seed_2_rec["attempts"] == 2

        # Second drain pass flushes remaining items
        drained_second_pass: List[str] = []
        drained_count2 = mgr.drain_offline_queue(lambda p: drained_second_pass.append(p["id"]) or True)
        assert drained_count2 == 3
        assert set(drained_first_pass + drained_second_pass) == {
            "seed_0", "seed_1", "seed_2", "interleaved_after_0", "interleaved_after_1"
        }
        assert not q_path.exists()

    def test_100_concurrent_threads_extreme_race_contention(self, tmp_path: Path):
        """Adversarial Challenge: 100 concurrent threads (50 producers, 50 consumers).

        1,000 records queued and drained simultaneously under maximal lock contention.
        Asserts 100% record conservation, zero dropped records, zero duplicates.
        """
        q_path = tmp_path / "100_threads_race.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        drained_items: List[str] = []
        drained_lock = threading.Lock()

        def sender(payload: Dict[str, Any]) -> bool:
            with drained_lock:
                drained_items.append(payload["id"])
            return True

        stop_event = threading.Event()

        def producer(tid: int):
            for i in range(20):
                mgr.queue_offline_payload({"id": f"t{tid}_item{i}", "data": "stress_100"})
                time.sleep(0.0001)

        def consumer():
            while not stop_event.is_set():
                mgr.drain_offline_queue(sender)
                time.sleep(0.0005)
            mgr.drain_offline_queue(sender)

        producers = [threading.Thread(target=producer, args=(t,)) for t in range(50)]
        consumers = [threading.Thread(target=consumer) for _ in range(50)]

        for c in consumers:
            c.start()
        for p in producers:
            p.start()

        for p in producers:
            p.join()

        time.sleep(0.05)
        stop_event.set()
        for c in consumers:
            c.join()

        # Final flush
        mgr.drain_offline_queue(sender)

        expected_count = 50 * 20  # 1,000
        assert len(drained_items) == expected_count, (
            f"Record loss under 100 threads: expected {expected_count}, got {len(drained_items)}"
        )
        assert len(set(drained_items)) == expected_count, (
            f"Duplicates under 100 threads: expected {expected_count}, unique {len(set(drained_items))}"
        )
        assert not q_path.exists(), "Queue file must be cleanly unlinked"

    def test_adversarial_fragmented_nested_json_and_extreme_garbage(self, tmp_path: Path):
        """Adversarial Challenge: Multi-level fragmented brackets, broken escapes, non-dict literals.

        Ensures corrupted fragments are isolated/skipped while all valid records are preserved.
        """
        q_path = tmp_path / "extreme_garbage.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        extreme_content = (
            "{{{{{\n"
            "{\"record_id\": \"rec_a\", \"payload\": {\"val\": \"first\"}}\n"
            "[1, 2, {\"bad\": true\n"
            "null\n"
            "true\n"
            "42.195\n"
            "\"isolated string literal\"\n"
            "{\"record_id\": \"rec_b\", \"payload\": {\"val\": \"second\"}}\n"
            "{\"unclosed_key\": \n"
            "{\"nested\": {\"deep\": \n"
            "{\"record_id\": \"rec_c\", \"payload\": {\"val\": \"third\"}}\n"
            "--- EOF TRUNCATED SENTINEL ---\n"
        )
        q_path.write_text(extreme_content, encoding="utf-8")

        drained: List[Dict[str, Any]] = []
        drained_count = mgr.drain_offline_queue(lambda p: drained.append(p) or True)

        assert drained_count == 3
        assert len(drained) == 3
        assert [p["val"] for p in drained] == ["first", "second", "third"]
        assert not q_path.exists(), "Queue file must be unlinked after all valid records drained"

    def test_rapid_consecutive_drains_and_concurrent_toctou(self, tmp_path: Path):
        """Adversarial Challenge: Rapid concurrent drain calls during file removal/recreation.

        Asserts that concurrent drains do not crash on missing/recreated files or produce TOCTOU crashes.
        """
        q_path = tmp_path / "rapid_toctou.jsonl"
        mgr = ResilienceManager(offline_queue_path=q_path)

        stop = threading.Event()
        errors: List[Exception] = []

        def drain_worker():
            while not stop.is_set():
                try:
                    mgr.drain_offline_queue(lambda p: True)
                except Exception as e:
                    errors.append(e)
                time.sleep(0.001)

        def file_mutator():
            for i in range(20):
                mgr.queue_offline_payload({"id": f"toctou_{i}"})
                time.sleep(0.002)

        threads = [threading.Thread(target=drain_worker) for _ in range(10)]
        mutator = threading.Thread(target=file_mutator)

        for t in threads:
            t.start()
        mutator.start()
        mutator.join()

        time.sleep(0.05)
        stop.set()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"TOCTOU exceptions encountered during rapid drains: {errors}"




# =============================================================================
# Challenge 4: Darwin Mach Memory Sanctuary Live Auditing
# =============================================================================

class TestChallenge4DarwinMemorySanctuary:
    """Challenge 4: Assert authentic Darwin Mach kernel memory sanctuary outputs."""

    def test_darwin_mach_memory_sanctuary_structure_and_types(self):
        """Call check_memory_sanctuary(floor_gb=4.8) and assert authentic kernel outputs."""
        mgr = ResilienceManager()
        res = mgr.check_memory_sanctuary(floor_gb=4.8)

        # Assert mandatory keys
        assert "free_ram_gb" in res
        assert "sanctuary_floor_gb" in res
        assert "compliant" in res
        assert "pressure" in res
        assert "total_ram_gb" in res
        assert "used_ram_gb" in res
        assert "platform" in res

        # Assert types
        assert isinstance(res["free_ram_gb"], float)
        assert isinstance(res["sanctuary_floor_gb"], float)
        assert isinstance(res["compliant"], bool)
        assert isinstance(res["pressure"], int)
        assert isinstance(res["total_ram_gb"], float)

        # Assert authentic values on Darwin
        if sys.platform == "darwin":
            assert res["platform"] == "darwin"
            assert res["total_ram_gb"] >= 16.0  # Host has 24GB unified memory
            assert res["sanctuary_floor_gb"] == 4.8
            assert res["pressure"] in (1, 2, 3)
            # Verify compliant logic
            expected_compliant = (res["free_ram_gb"] >= 4.8) and (res["pressure"] <= 1)
            assert res["compliant"] == expected_compliant

    def test_sanctuary_floor_override_boundaries(self):
        """Asserts floor_gb override affects compliance correctly."""
        mgr = ResilienceManager()

        # An impossibly high floor (1000 GB) must always return compliant = False
        res_high = mgr.check_memory_sanctuary(floor_gb=1000.0)
        assert res_high["compliant"] is False
        assert res_high["sanctuary_floor_gb"] == 1000.0
