#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Feature F6 - Service Manifests E2E Test Suite.
Validates macOS LaunchAgent plist (plutil syntax, KeepAlive, foreground invariant)
and Linux systemd service unit (sections, restart policies, resource limits).
"""

import os
import sys
import plistlib
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR

PLIST_PATH = BOOTSTRAPPER_DIR / "config" / "com.lauburu.lens-bootstrapper.plist"
SYSTEMD_PATH = BOOTSTRAPPER_DIR / "config" / "lens-bootstrapper.service"


class TestF6ServiceManifests(unittest.TestCase):
    """E2E Verification for Feature F6: Service Manifests."""

    def test_f6_01_plist_exists_and_valid_xml(self):
        """F6.1: Verify LaunchAgent plist exists and passes plutil -lint validation."""
        self.assertTrue(PLIST_PATH.exists(), f"LaunchAgent plist missing at {PLIST_PATH}")
        if sys.platform == "darwin":
            proc = subprocess.run(
                ["/usr/bin/plutil", "-lint", str(PLIST_PATH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.assertEqual(proc.returncode, 0, f"plutil validation failed: {proc.stderr}")
            self.assertIn("OK", proc.stdout)

    def test_f6_02_plist_label_and_arguments(self):
        """F6.2: Verify plist Label and ProgramArguments contain --foreground."""
        with open(PLIST_PATH, "rb") as f:
            data = plistlib.load(f)

        self.assertEqual(data.get("Label"), "com.lauburu.lens-bootstrapper")
        args = data.get("ProgramArguments", [])
        self.assertGreaterEqual(len(args), 2, "ProgramArguments must define executable and flags")
        self.assertIn("--foreground", args, "LaunchAgent MUST run in --foreground mode to prevent launchd respawn loops")

    def test_f6_03_plist_lifecycle_keys(self):
        """F6.3: Verify RunAtLoad is true, KeepAlive is true, and ThrottleInterval is present."""
        with open(PLIST_PATH, "rb") as f:
            data = plistlib.load(f)

        self.assertTrue(data.get("RunAtLoad"), "RunAtLoad must be true")
        self.assertTrue(data.get("KeepAlive"), "KeepAlive must be true")
        self.assertIn("ThrottleInterval", data)

    def test_f6_04_plist_log_redirection(self):
        """F6.4: Verify StandardOutPath and StandardErrorPath are configured to log files."""
        with open(PLIST_PATH, "rb") as f:
            data = plistlib.load(f)

        stdout_path = data.get("StandardOutPath", "")
        stderr_path = data.get("StandardErrorPath", "")
        self.assertTrue(stdout_path.endswith(".log"), "StandardOutPath must be a .log file")
        self.assertTrue(stderr_path.endswith(".log"), "StandardErrorPath must be a .log file")

    def test_f6_05_systemd_unit_exists_and_sections(self):
        """F6.5: Verify Linux systemd unit exists and has [Unit], [Service], and [Install] sections."""
        self.assertTrue(SYSTEMD_PATH.exists(), f"systemd service missing at {SYSTEMD_PATH}")
        content = SYSTEMD_PATH.read_text(encoding="utf-8")
        self.assertIn("[Unit]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)

    def test_f6_06_systemd_restart_and_resource_limits(self):
        """F6.6: Verify Restart=always, RestartSec, LimitNOFILE, and WantedBy in systemd unit."""
        content = SYSTEMD_PATH.read_text(encoding="utf-8")
        self.assertIn("Restart=always", content)
        self.assertIn("RestartSec=", content)
        self.assertIn("LimitNOFILE=", content)
        self.assertIn("WantedBy=multi-user.target", content)


if __name__ == "__main__":
    unittest.main()
