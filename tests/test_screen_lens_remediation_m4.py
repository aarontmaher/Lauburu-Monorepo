#!/usr/bin/env python3
"""
tests/test_screen_lens_remediation_m4.py
========================================
Integration and unit tests verifying the remediation of Milestone M4:
1. launch_lens_workflow_daemon.sh auto-trainer subprocess: uses sys.executable with MLX, enforces check=True, runs Exit 0.
2. Listening ports: 3035, 3036, 3037, 4003, 4006 all listening and reachable.
3. Harvester RAM tripwire: continuous_mesh_lora_harvester_loop.sh configured to < 20%.
4. Host RAM sanctuary: >= 4.8 GB available.
"""

import os
import re
import socket
import subprocess
import sys
import unittest
import urllib.request
from pathlib import Path


class TestScreenLensRemediationM4(unittest.TestCase):
    REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

    def test_1_python_mlx_available(self):
        """Verify python interpreter has mlx.core installed and Metal GPU available."""
        import mlx.core as mx
        device = mx.default_device()
        self.assertIn("gpu", str(device).lower())
        self.assertTrue(mx.metal.is_available())

    def test_2_workflow_daemon_script_configuration(self):
        """Verify launch_lens_workflow_daemon.sh uses sys.executable and check=True."""
        script_path = self.REPO_ROOT / "01_apps/screen_lens/launch_lens_workflow_daemon.sh"
        self.assertTrue(script_path.exists())
        content = script_path.read_text(encoding="utf-8")
        
        # Verify no forbidden uv run python
        self.assertNotIn("uv run python", content)
        # Verify sys.executable used
        self.assertIn("sys.executable", content)
        # Verify check=True enforced
        self.assertIn("check=True", content)
        # Verify CalledProcessError handling
        self.assertIn("subprocess.CalledProcessError", content)

    def test_3_harvester_loop_ram_tripwire(self):
        """Verify continuous_mesh_lora_harvester_loop.sh tripwire is set to < 20%."""
        script_path = self.REPO_ROOT / "04_data_and_memory/continuous_mesh_lora_harvester_loop.sh"
        self.assertTrue(script_path.exists())
        content = script_path.read_text(encoding="utf-8")
        
        # Verify -lt 20
        self.assertIn('-lt 20', content)
        self.assertNotIn('-lt 15', content)

    def test_4_all_five_ports_listening(self):
        """Verify all 5 required ports are actively listening."""
        ports = [3035, 3036, 3037, 4003, 4006]
        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                res = s.connect_ex(("127.0.0.1", port))
                self.assertEqual(res, 0, f"Port {port} is not listening (connect_ex returned {res})")

    def test_5_http_endpoints_responding(self):
        """Verify HTTP endpoints on 3035, 3036, 3037, 4006 respond with HTTP 200."""
        endpoints = [
            ("http://127.0.0.1:3035/health", 200),
            ("http://127.0.0.1:3036/", 200),
            ("http://127.0.0.1:3037/api/orchestrator/state", 200),
            ("http://127.0.0.1:4006/health", 200),
        ]
        for url, expected_code in endpoints:
            req = urllib.request.Request(url, headers={"User-Agent": "M4RemediationTest/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, expected_code, f"URL {url} returned status {resp.status}")

    def test_6_mlx_qlora_trainer_subprocess_exit_0(self):
        """Verify mlx_lens_qlora_trainer.py executes successfully with Exit 0 via subprocess."""
        trainer_script = self.REPO_ROOT / "02_ai_models_and_inference/mlx_lens_qlora_trainer.py"
        dataset_path = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/screen_lens_perception_workflow.jsonl")
        
        res = subprocess.run(
            [sys.executable, str(trainer_script), str(dataset_path)],
            capture_output=True,
            text=True,
            timeout=30.0,
            check=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Upgraded MLX Training Complete", res.stderr + res.stdout)
        self.assertIn("adapters.npz", res.stdout)

    def test_7_host_ram_sanctuary(self):
        """Verify Mac Mini host preserves >= 4.8 GB free physical RAM (Rule 3)."""
        proc = subprocess.run(
            ["memory_pressure"],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        self.assertEqual(proc.returncode, 0)
        match = re.search(r"System-wide memory free percentage:\s*(\d+)%", proc.stdout)
        self.assertIsNotNone(match)
        pct = int(match.group(1))
        # 20% of 24 GB is 4.8 GB
        self.assertGreaterEqual(pct, 20, f"Host free RAM percentage {pct}% is below 20% sanctuary threshold")


if __name__ == "__main__":
    unittest.main()
