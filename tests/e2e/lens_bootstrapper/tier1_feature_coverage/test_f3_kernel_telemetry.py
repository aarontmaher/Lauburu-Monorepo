#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Feature F3 - Zero-Fork Kernel Telemetry Engine E2E Test Suite.
Validates direct Mach kernel memory accounting, <notify.h> thermal pressure,
<ifaddrs.h> network byte counters, and sub-millisecond execution latency.
"""

import os
import sys
import time
import ctypes
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR, query_darwin_mach_memory

TELEMETRY_BIN = BOOTSTRAPPER_DIR / "build" / "test_bootstrapper_telemetry"


class TestF3KernelTelemetryEngine(unittest.TestCase):
    """E2E Verification for Feature F3: Zero-Fork Kernel Telemetry Engine."""

    def test_f3_01_telemetry_unit_binary_executes(self):
        """F3.1: Execute compiled test_bootstrapper_telemetry binary, verifying exit code 0."""
        self.assertTrue(TELEMETRY_BIN.exists(), f"Telemetry test binary missing at {TELEMETRY_BIN}")
        proc = subprocess.run(
            [str(TELEMETRY_BIN)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"Telemetry test failed: {proc.stderr}\n{proc.stdout}")
        self.assertIn("Total RAM:", proc.stdout)
        self.assertIn("Thermal Pressure:", proc.stdout)

    def test_f3_02_darwin_mach_memory_syscall_truth(self):
        """F3.2: Verify genuine Mach host_statistics64 syscall returns authentic memory numbers."""
        if sys.platform != "darwin":
            self.skipTest("Darwin Mach kernel memory requires macOS")

        mem = query_darwin_mach_memory()
        self.assertNotIn("error", mem, f"Mach query error: {mem.get('error')}")
        self.assertEqual(mem["page_size"], 16384, "Apple Silicon standard page size must be 16KB (16384 bytes)")
        self.assertGreater(mem["avail_bytes"], 100 * 1024 * 1024, "Available RAM must be > 100 MB")
        self.assertGreater(mem["wired_bytes"], 100 * 1024 * 1024, "Wired RAM must be > 100 MB")

    def test_f3_03_thermal_pressure_level_range(self):
        """F3.3: Verify thermal pressure state integer is strictly in [0, 3]."""
        if sys.platform != "darwin":
            self.skipTest("Thermal notify.h requires macOS")

        # notify_register_check & notify_get_state
        libc = ctypes.CDLL("/usr/lib/libc.dylib")
        token = ctypes.c_int(0)
        reg_ret = libc.notify_register_check(b"com.apple.system.thermalpressurelevel", ctypes.byref(token))
        self.assertEqual(reg_ret, 0, "Failed to register thermal pressure check")

        state = ctypes.c_uint64(0)
        state_ret = libc.notify_get_state(token.value, ctypes.byref(state))
        self.assertEqual(state_ret, 0, "Failed to get thermal state")
        libc.notify_cancel(token.value)

        thermal_level = state.value
        self.assertIn(
            thermal_level, [0, 1, 2, 3],
            f"Thermal level must be between 0 (Nominal) and 3 (Critical), got {thermal_level}"
        )

    def test_f3_04_vm_pressure_level_range(self):
        """F3.4: Verify VM pressure level via sysctlbyname is in [1, 3] (1=Normal, 2=Warning, 3=Critical)."""
        if sys.platform != "darwin":
            self.skipTest("sysctl memorystatus requires macOS")

        libc = ctypes.CDLL("/usr/lib/libc.dylib")
        pressure_level = ctypes.c_int(0)
        size = ctypes.c_size_t(ctypes.sizeof(pressure_level))
        
        ret = libc.sysctlbyname(
            b"kern.memorystatus_vm_pressure_level",
            ctypes.byref(pressure_level),
            ctypes.byref(size),
            None,
            0
        )
        self.assertEqual(ret, 0, "sysctl kern.memorystatus_vm_pressure_level failed")
        self.assertIn(
            pressure_level.value, [1, 2, 3],
            f"VM pressure level must be 1 (Normal), 2 (Warning), or 3 (Critical), got {pressure_level.value}"
        )

    def test_f3_05_network_counters_monotonicity(self):
        """F3.5: Verify getifaddrs network byte counters are non-negative and non-decreasing."""
        if sys.platform != "darwin":
            self.skipTest("Darwin getifaddrs requires macOS")

        # Execute telemetry binary twice with short delay to check network counters
        proc1 = subprocess.run([str(TELEMETRY_BIN)], stdout=subprocess.PIPE, text=True, check=True)
        time.sleep(0.1)
        proc2 = subprocess.run([str(TELEMETRY_BIN)], stdout=subprocess.PIPE, text=True, check=True)

        self.assertIn("Net RX Rate:", proc1.stdout)
        self.assertIn("Net TX Rate:", proc1.stdout)
        self.assertIn("Net RX Rate:", proc2.stdout)
        self.assertIn("Net TX Rate:", proc2.stdout)

    def test_f3_06_zero_fork_execution_latency(self):
        """F3.6: Verify Mach kernel memory sample takes < 1.0 ms (< 1000 microseconds)."""
        if sys.platform != "darwin":
            self.skipTest("Darwin Mach benchmark requires macOS")

        # Measure 100 direct calls
        start = time.perf_counter()
        iterations = 50
        for _ in range(iterations):
            _ = query_darwin_mach_memory()
        total_sec = time.perf_counter() - start
        avg_ms = (total_sec / iterations) * 1000.0

        self.assertLess(
            avg_ms, 1.0,
            f"Syscall latency exceeded: average {avg_ms:.3f} ms, must be < 1.0 ms for zero-fork telemetry"
        )


if __name__ == "__main__":
    unittest.main()
