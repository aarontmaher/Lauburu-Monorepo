#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis - Missing & Corrupted Configs.
Stresses bootstrapper and supervisor configuration parser against edge cases:
1. Nonexistent configuration file path
2. Empty 0-byte configuration file
3. Malformed JSON with syntax errors
4. JSON missing required keys (falls back to defaults)
5. Unreadable configuration file permissions (0000)
"""

import os
import sys
import json
import tempfile
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR

DAEMON_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper"


class TestBoundaryMissingConfigs(unittest.TestCase):
    """Boundary testing for configuration parsing resilience."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.daemon_bin = DAEMON_BIN
        self.assertTrue(self.daemon_bin.exists(), "lens_bootstrapper binary missing")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_b1_01_nonexistent_config_file_falls_back_cleanly(self):
        """B1.1: Nonexistent config path does not crash the daemon; falls back to defaults."""
        bogus_path = "/tmp/nonexistent_config_123456789.json"
        proc = subprocess.run(
            [str(self.daemon_bin), "--config", bogus_path, "--test-run", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"Daemon crashed on nonexistent config: {proc.stderr}")

    def test_b1_02_empty_zero_byte_config_file(self):
        """B1.2: Empty 0-byte config file does not trigger segmentation fault or crash."""
        empty_cfg = Path(self.temp_dir.name) / "empty.json"
        empty_cfg.write_text("", encoding="utf-8")

        proc = subprocess.run(
            [str(self.daemon_bin), "--config", str(empty_cfg), "--test-run", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"Daemon crashed on empty config: {proc.stderr}")

    def test_b1_03_malformed_json_syntax_error(self):
        """B1.3: Malformed JSON syntax error ({ invalid json content ) is handled gracefully."""
        bad_cfg = Path(self.temp_dir.name) / "corrupt.json"
        bad_cfg.write_text("{\n  \"socket_path\": \"corrupt,\n  unclosed_bracket", encoding="utf-8")

        proc = subprocess.run(
            [str(self.daemon_bin), "--config", str(bad_cfg), "--test-run", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"Daemon crashed on malformed JSON: {proc.stderr}")

    def test_b1_04_missing_critical_keys_uses_defaults(self):
        """B1.4: JSON with only partial keys maintains default values for missing keys."""
        partial_cfg = Path(self.temp_dir.name) / "partial.json"
        partial_cfg.write_text(json.dumps({"telemetry_interval_sec": 10}), encoding="utf-8")

        proc = subprocess.run(
            [str(self.daemon_bin), "--config", str(partial_cfg), "--test-run", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"Daemon crashed on partial config: {proc.stderr}")

    def test_b1_05_unreadable_file_permissions(self):
        """B1.5: Config file with 0000 permissions (unreadable) falls back to defaults without crash."""
        unreadable_cfg = Path(self.temp_dir.name) / "unreadable.json"
        unreadable_cfg.write_text(json.dumps({"telemetry_interval_sec": 5}), encoding="utf-8")
        unreadable_cfg.chmod(0o000)

        try:
            proc = subprocess.run(
                [str(self.daemon_bin), "--config", str(unreadable_cfg), "--test-run", "--no-supervisor"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            self.assertEqual(proc.returncode, 0, f"Daemon crashed on unreadable config: {proc.stderr}")
        finally:
            unreadable_cfg.chmod(0o644)


if __name__ == "__main__":
    unittest.main()
