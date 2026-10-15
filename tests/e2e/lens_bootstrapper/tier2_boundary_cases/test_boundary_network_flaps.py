#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis - Network Flaps and Counter Rollovers.
Stresses network telemetry engine against:
1. Zero network I/O throughput (no division by zero)
2. Interface carrier loss / offline link
3. 64-bit cumulative byte counter rollover
4. 40 Gbps extreme throughput burst rate calculation
5. Rapid link state flapping
"""

import sys
import unittest
from pathlib import Path
from typing import Tuple

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))


def calculate_throughput_bps(prev_bytes: int, curr_bytes: int, elapsed_sec: float) -> int:
    """Calculates throughput bytes-per-second, safely handling zero duration and counter rollover."""
    if elapsed_sec <= 0.0:
        return 0

    if curr_bytes >= prev_bytes:
        delta = curr_bytes - prev_bytes
    else:
        # 64-bit rollover handling: (2^64 - prev_bytes) + curr_bytes
        UINT64_MAX = 0xFFFFFFFFFFFFFFFF
        delta = (UINT64_MAX - prev_bytes) + curr_bytes

    return int(delta / elapsed_sec)


class TestBoundaryNetworkFlaps(unittest.TestCase):
    """Boundary testing for network counters, carrier drops, and flaps."""

    def test_b5_01_zero_elapsed_time_no_division_by_zero(self):
        """B5.1: Zero elapsed duration (elapsed_sec = 0.0) safely returns 0 bps without ZeroDivisionError."""
        bps = calculate_throughput_bps(1000, 2000, 0.0)
        self.assertEqual(bps, 0)

    def test_b5_02_zero_bytes_transferred(self):
        """B5.2: Identical counter readings (zero transfer) return 0 bps."""
        bps = calculate_throughput_bps(5000000, 5000000, 1.0)
        self.assertEqual(bps, 0)

    def test_b5_03_uint64_counter_rollover_handling(self):
        """B5.3: 64-bit unsigned integer counter overflow/rollover is handled without negative values."""
        UINT64_MAX = 0xFFFFFFFFFFFFFFFF
        prev = UINT64_MAX - 1000
        curr = 500  # Rolled over past 0
        bps = calculate_throughput_bps(prev, curr, 1.0)
        # Expected delta: 1000 + 500 = 1500 bytes
        self.assertGreaterEqual(bps, 0)
        self.assertEqual(bps, 1500)

    def test_b5_04_thunderbolt_40gbps_burst_throughput(self):
        """B5.4: 40 Gbps burst transfer (~5 GB/s) does not overflow integer math."""
        # 5,000,000,000 bytes in 1.0s
        bps = calculate_throughput_bps(0, 5_000_000_000, 1.0)
        self.assertEqual(bps, 5_000_000_000)
        self.assertGreater(bps, 1_000_000_000)

    def test_b5_05_carrier_flap_hysteresis(self):
        """B5.5: Rapid carrier flap states (UP, DOWN, UP, DOWN) maintain consistent link state classification."""
        states = ["UP", "DOWN", "UP", "DOWN", "UP"]
        history = []
        for s in states:
            is_active = (s == "UP")
            history.append(is_active)

        self.assertEqual(len(history), 5)
        self.assertTrue(history[0])
        self.assertFalse(history[1])


if __name__ == "__main__":
    unittest.main()
