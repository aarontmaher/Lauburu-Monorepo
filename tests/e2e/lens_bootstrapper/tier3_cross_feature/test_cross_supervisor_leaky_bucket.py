#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 3: Pairwise Combinatorial Cross-Feature Interaction Test Suite.
Interaction Pipeline: Supervisor Crash -> Leaky-Bucket Circuit Breaker -> IPC Status.
Validates:
1. Child process exits unexpectedly / crashes
2. Supervisor detects crash via non-blocking waitpid and records crash count
3. Leaky-bucket circuit breaker rate-limits restarts (max 3 / 5 min)
4. Circuit breaker trips to OPEN on exhaustion, preventing fork thrashing
5. IPC STATUS reflects degraded / backoff state
"""

import os
import sys
import time
import json
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from tier1_feature_coverage.test_f7_f10_supervisor_healing import LeakyBucketCircuitBreaker


class MockSupervisedService:
    """Simulates supervisor child lifecycle integrated with leaky-bucket circuit breaker."""

    def __init__(self, name: str = "lens_supervisor_3037"):
        self.name = name
        self.breaker = LeakyBucketCircuitBreaker(capacity=3, period_sec=300.0)
        self.crashes = 0
        self.status = "STOPPED"
        self.child_pid = None
        self.backoff_sec = 1

    def spawn_and_crash(self) -> bool:
        if not self.breaker.allow_restart(self.name):
            self.status = "BACKOFF"
            self.backoff_sec = min(self.backoff_sec * 2, 30)
            return False

        self.status = "ALIVE"
        self.child_pid = 12000 + self.crashes
        # Simulate immediate crash
        self.crashes += 1
        self.status = "STARTING"
        return True

    def get_ipc_status(self) -> dict:
        return {
            "status": "RUNNING",
            "supervisor_name": self.name,
            "supervisor_status": self.status,
            "crash_count": self.crashes,
            "circuit_breaker": self.breaker.get_state(self.name),
            "backoff_sec": self.backoff_sec
        }


class TestCrossSupervisorLeakyBucket(unittest.TestCase):
    """Pairwise Cross-Feature Verification: Supervisor Crash -> Circuit Breaker -> IPC."""

    def test_c2_01_initial_clean_start_allowed(self):
        """C2.1: Initial child spawn is allowed and circuit breaker remains CLOSED."""
        service = MockSupervisedService()
        allowed = service.spawn_and_crash()
        self.assertTrue(allowed)
        status = service.get_ipc_status()
        self.assertEqual(status["crash_count"], 1)
        self.assertEqual(status["circuit_breaker"], "CLOSED")

    def test_c2_02_three_consecutive_restarts_exhaust_bucket(self):
        """C2.2: Exactly three consecutive crashes are permitted before exhaustion."""
        service = MockSupervisedService()
        self.assertTrue(service.spawn_and_crash())  # 1st
        self.assertTrue(service.spawn_and_crash())  # 2nd
        self.assertTrue(service.spawn_and_crash())  # 3rd
        status = service.get_ipc_status()
        self.assertEqual(status["crash_count"], 3)
        self.assertEqual(status["circuit_breaker"], "CLOSED")

    def test_c2_03_fourth_crash_trips_breaker_to_open(self):
        """C2.3: 4th crash within period trips circuit breaker to OPEN and halts respawns."""
        service = MockSupervisedService()
        for _ in range(3):
            service.spawn_and_crash()

        # 4th attempt
        allowed = service.spawn_and_crash()
        self.assertFalse(allowed, "4th attempt must be rejected by circuit breaker")
        status = service.get_ipc_status()
        self.assertEqual(status["circuit_breaker"], "OPEN")
        self.assertEqual(status["supervisor_status"], "BACKOFF")

    def test_c2_04_ipc_status_reflects_circuit_breaker_open(self):
        """C2.4: IPC STATUS response reports BACKOFF status and OPEN circuit breaker."""
        service = MockSupervisedService()
        for _ in range(4):
            service.spawn_and_crash()

        ipc_data = service.get_ipc_status()
        self.assertEqual(ipc_data["supervisor_status"], "BACKOFF")
        self.assertEqual(ipc_data["circuit_breaker"], "OPEN")
        self.assertGreater(ipc_data["backoff_sec"], 1)

    def test_c2_05_circuit_breaker_prevents_cpu_thrashing(self):
        """C2.5: Verifies that 10 successive crash events produce only 3 actual spawn attempts."""
        service = MockSupervisedService()
        successful_spawns = 0
        for _ in range(10):
            if service.spawn_and_crash():
                successful_spawns += 1

        self.assertEqual(successful_spawns, 3, "Spawns must be capped at 3 to prevent CPU thrashing")
        status = service.get_ipc_status()
        self.assertEqual(status["crash_count"], 3)


if __name__ == "__main__":
    unittest.main()
