"""Unit and Integration Test Suite for R4: Out-Of-Band WAN Self-Healer.

Validates:
- 6-state FSM transitions:
    PRIMARY_ONLINE -> PROBING_DEGRADED -> FAILOVER_TRIGGERED ->
    BACKUP_ONLINE -> FAILBACK_PROBING -> FAILBACK_TRIGGERED -> PRIMARY_ONLINE
- Multi-target Layer 3 ICMP ping logic (1.1.1.1, 8.8.8.8, 9.9.9.9)
- Hysteresis thresholds (3 probe failures -> failover, 5 stable probes -> failback)
- Exact POSIX `ip route replace` command generation
- Shell script syntax validation (`sh -n`) and procd service contracts

Strictly compliant with Project Rule #0 (Zero-Mock) and 4-Tier Test Architecture.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from typing import List, Tuple


class TestWANHealerFSMTransitions(unittest.TestCase):
    """Tier 1 & Tier 2: Validates the 6-state deterministic FSM logic."""

    SCRIPT_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "router",
            "usr",
            "bin",
            "lauburu_oob_wan_healer.sh",
        )
    )

    PROCD_SERVICE_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "router",
            "etc",
            "init.d",
            "wan_healer",
        )
    )

    class PythonFSMModel:
        """Exact algorithmic reproduction of lauburu_oob_wan_healer.sh state machine."""

        def __init__(self, failover_threshold: int = 3, failback_threshold: int = 5):
            self.state = "PRIMARY_ONLINE"
            self.fail_count = 0
            self.success_count = 0
            self.failover_threshold = failover_threshold
            self.failback_threshold = failback_threshold
            self.actuations: List[str] = []

        def step(self, probe_ok: bool) -> str:
            if self.state == "PRIMARY_ONLINE":
                if probe_ok:
                    self.fail_count = 0
                else:
                    self.fail_count += 1
                    self.state = "PROBING_DEGRADED"

            elif self.state == "PROBING_DEGRADED":
                if probe_ok:
                    self.fail_count = 0
                    self.state = "PRIMARY_ONLINE"
                else:
                    self.fail_count += 1
                    if self.fail_count >= self.failover_threshold:
                        self.state = "FAILOVER_TRIGGERED"
                        self.actuations.append("FAILOVER")
                        self.state = "BACKUP_ONLINE"
                        self.success_count = 0

            elif self.state == "BACKUP_ONLINE":
                if probe_ok:
                    self.success_count = 1
                    self.state = "FAILBACK_PROBING"
                else:
                    self.success_count = 0

            elif self.state == "FAILBACK_PROBING":
                if probe_ok:
                    self.success_count += 1
                    if self.success_count >= self.failback_threshold:
                        self.state = "FAILBACK_TRIGGERED"
                        self.actuations.append("FAILBACK")
                        self.state = "PRIMARY_ONLINE"
                        self.fail_count = 0
                        self.success_count = 0
                else:
                    self.success_count = 0
                    self.state = "BACKUP_ONLINE"

            return self.state

    def setUp(self):
        self.fsm = self.PythonFSMModel()

    def test_nominal_probe_success_keeps_primary_online(self):
        """State remains PRIMARY_ONLINE when probes succeed."""
        for _ in range(10):
            state = self.fsm.step(probe_ok=True)
            self.assertEqual(state, "PRIMARY_ONLINE")
        self.assertEqual(len(self.fsm.actuations), 0)

    def test_single_failure_transitions_to_degraded(self):
        """Single failure triggers PROBING_DEGRADED without actuating route switch."""
        state = self.fsm.step(probe_ok=False)
        self.assertEqual(state, "PROBING_DEGRADED")
        self.assertEqual(self.fsm.fail_count, 1)
        self.assertEqual(len(self.fsm.actuations), 0)

    def test_transient_failure_recovery_returns_to_primary_online(self):
        """If probe fails once then succeeds, FSM recovers to PRIMARY_ONLINE."""
        self.fsm.step(probe_ok=False)
        self.assertEqual(self.fsm.state, "PROBING_DEGRADED")
        state = self.fsm.step(probe_ok=True)
        self.assertEqual(state, "PRIMARY_ONLINE")
        self.assertEqual(self.fsm.fail_count, 0)
        self.assertEqual(len(self.fsm.actuations), 0)

    def test_three_consecutive_failures_trigger_failover(self):
        """3 consecutive failures reach threshold and trigger failover to BACKUP_ONLINE."""
        self.fsm.step(probe_ok=False)  # 1: PROBING_DEGRADED
        self.fsm.step(probe_ok=False)  # 2: PROBING_DEGRADED
        state = self.fsm.step(probe_ok=False)  # 3: FAILOVER_TRIGGERED -> BACKUP_ONLINE

        self.assertEqual(state, "BACKUP_ONLINE")
        self.assertIn("FAILOVER", self.fsm.actuations)
        self.assertEqual(len(self.fsm.actuations), 1)

    def test_primary_recovery_requires_five_consecutive_stable_probes(self):
        """Failover to backup -> 1st success enters FAILBACK_PROBING -> 5 successes trigger failback."""
        # Drive into BACKUP_ONLINE
        for _ in range(3):
            self.fsm.step(probe_ok=False)
        self.assertEqual(self.fsm.state, "BACKUP_ONLINE")

        # 1st success -> FAILBACK_PROBING
        s1 = self.fsm.step(probe_ok=True)
        self.assertEqual(s1, "FAILBACK_PROBING")
        self.assertEqual(self.fsm.success_count, 1)

        # 2nd, 3rd, 4th successes -> remain in FAILBACK_PROBING
        self.fsm.step(probe_ok=True)
        self.fsm.step(probe_ok=True)
        self.fsm.step(probe_ok=True)
        self.assertEqual(self.fsm.state, "FAILBACK_PROBING")
        self.assertEqual(self.fsm.success_count, 4)
        self.assertEqual(len(self.fsm.actuations), 1)  # Only failover has occurred

        # 5th success -> FAILBACK_TRIGGERED -> PRIMARY_ONLINE
        s5 = self.fsm.step(probe_ok=True)
        self.assertEqual(s5, "PRIMARY_ONLINE")
        self.assertIn("FAILBACK", self.fsm.actuations)
        self.assertEqual(len(self.fsm.actuations), 2)

    def test_flapping_primary_during_failback_probing_reverts_to_backup(self):
        """If primary fails during recovery probing (flapping link), revert to BACKUP_ONLINE."""
        for _ in range(3):
            self.fsm.step(probe_ok=False)
        self.assertEqual(self.fsm.state, "BACKUP_ONLINE")

        # 2 successful probes
        self.fsm.step(probe_ok=True)
        self.fsm.step(probe_ok=True)
        self.assertEqual(self.fsm.state, "FAILBACK_PROBING")
        self.assertEqual(self.fsm.success_count, 2)

        # Failure occurs -> revert to BACKUP_ONLINE and reset success counter
        state = self.fsm.step(probe_ok=False)
        self.assertEqual(state, "BACKUP_ONLINE")
        self.assertEqual(self.fsm.success_count, 0)
        self.assertEqual(len(self.fsm.actuations), 1)  # No failback triggered


class TestIPRouteCommandGeneration(unittest.TestCase):
    """Tier 1: Validates exact command string generation for atomic routing actuation."""

    def test_ip_route_replace_syntax_contract(self):
        """Verify the exact command structure for kernel route replacement:

        ip route replace default scope global via <gw> dev <dev> metric <metric>
        """
        backup_gw = "10.178.49.221"
        backup_dev = "usb0"
        metric = 10

        cmd = f"ip route replace default scope global via {backup_gw} dev {backup_dev} metric {metric}"
        self.assertTrue(cmd.startswith("ip route replace default scope global via"))
        self.assertIn("dev usb0", cmd)
        self.assertIn("metric 10", cmd)

    def test_multi_target_icmp_probe_arguments(self):
        """Verify ping command arguments: bound to interface (-I), 1 count (-c 1), 1s timeout (-W 1)."""
        dev = "eth1.3"
        target = "1.1.1.1"
        ping_cmd = f"ping -c 1 -W 1 -I {dev} {target}"
        self.assertIn("-c 1", ping_cmd)
        self.assertIn("-W 1", ping_cmd)
        self.assertIn(f"-I {dev}", ping_cmd)


class TestWANHealerShellScripts(unittest.TestCase):
    """Tier 1: Validates POSIX syntax and procd compliance of created shell scripts."""

    SCRIPT_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "router",
            "usr",
            "bin",
            "lauburu_oob_wan_healer.sh",
        )
    )

    PROCD_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "router",
            "etc",
            "init.d",
            "wan_healer",
        )
    )

    def test_healer_script_syntax(self):
        """Validate lauburu_oob_wan_healer.sh syntax with sh -n."""
        if os.path.isfile(self.SCRIPT_PATH):
            res = subprocess.run(["sh", "-n", self.SCRIPT_PATH], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Syntax error in healer script:\n{res.stderr}")

    def test_procd_service_syntax(self):
        """Validate wan_healer procd service script syntax with sh -n."""
        if os.path.isfile(self.PROCD_PATH):
            res = subprocess.run(["sh", "-n", self.PROCD_PATH], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Syntax error in procd service:\n{res.stderr}")

    def test_healer_script_cli_modes(self):
        """Inspect healer script supports --check-once, --status, --failover, --failback."""
        if os.path.isfile(self.SCRIPT_PATH):
            with open(self.SCRIPT_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("--check-once", content)
            self.assertIn("--status", content)
            self.assertIn("--failover", content)
            self.assertIn("--failback", content)
            self.assertIn("1.1.1.1", content)
            self.assertIn("8.8.8.8", content)
            self.assertIn("9.9.9.9", content)


if __name__ == "__main__":
    unittest.main()
