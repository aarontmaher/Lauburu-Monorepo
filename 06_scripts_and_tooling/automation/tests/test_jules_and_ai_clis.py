#!/usr/bin/env python3
"""
Test Suite for Google Jules API & Multiplexed Local AI Terminal Orchestrator.
Enforces Rule 1 (Zero-Mock), Rule 3 (RAM Sanctuary), and Teacher-Student Distillation.
"""  # noqa: EXE001

import sys
import unittest
import hashlib
from pathlib import Path

# Add automation directory to path
AUTOMATION_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AUTOMATION_DIR))

from jules_api_client import JulesClient, JulesAuth
from multiplexed_ai_terminal_orchestrator import (
    HostSanctuary,
    LocalCliHarvester,
    TerminalMultiplexer,
    PI_BIN,
    JUNIE_BIN,
    TMUX_BIN,
    ZELLIJ_BIN,
)
from jetbrains_lens_automation import screen_lens_inspect_ide_state


class TestJulesAndAiClis(unittest.TestCase):

    def test_jules_auth_and_client_init(self):
        headers, auth_mode = JulesAuth.get_headers()
        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn(auth_mode, ["API_KEY (x-goog-api-key)", "OAUTH2 (Bearer token + user project)", "GEMINI_API_KEY_FALLBACK", "UNAUTHENTICATED"])

        client = JulesClient()
        self.assertTrue(client.headers)
        # Probe sources endpoint live (expect dict response with status_code or sources)
        res = client.list_sources(page_size=1)
        self.assertIsInstance(res, dict)
        self.assertTrue("error" in res or "sources" in res)

    def test_host_sanctuary_ram_headroom(self):
        free_gb = HostSanctuary.get_free_ram_gb()
        self.assertIsInstance(free_gb, float)
        self.assertGreater(free_gb, 0.0)
        safe, verified_gb = HostSanctuary.is_sanctuary_safe(threshold_gb=4.8)
        self.assertIsInstance(safe, bool)
        self.assertAlmostEqual(free_gb, verified_gb, places=1)
        self.assertEqual(safe, free_gb >= 4.8, f"Host Sanctuary free RAM {free_gb:.2f} GB safety check mismatch")

    def test_cli_tools_installed(self):
        self.assertTrue(Path(PI_BIN).exists(), f"Pi CLI missing at {PI_BIN}")
        self.assertTrue(Path(JUNIE_BIN).exists(), f"Junie CLI missing at {JUNIE_BIN}")
        self.assertIsNotNone(TMUX_BIN, "tmux missing")
        self.assertIsNotNone(ZELLIJ_BIN, "zellij missing")

    def test_headless_pty_execution(self):
        res = TerminalMultiplexer.run_headless_pty(["echo", "SOVEREIGN_MESH_TEST_OK"], timeout_sec=5)
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("SOVEREIGN_MESH_TEST_OK", res["clean_output"])
        self.assertGreaterEqual(res["duration_sec"], 0.0)

    def test_ide_state_inspection(self):
        st = screen_lens_inspect_ide_state()
        self.assertIsInstance(st, dict)
        self.assertIn("ide_running", st)
        self.assertIn("processes", st)

    def test_harvester_training_pair_format(self):
        pi_pairs = LocalCliHarvester.harvest_pi_sessions(max_files=10)
        junie_pairs = LocalCliHarvester.harvest_junie_sessions(max_sessions=5)

        for p in (pi_pairs + junie_pairs)[:5]:
            self.assertIn("instruction", p)
            self.assertIn("input", p)
            self.assertIn("metadata", p)
            self.assertIn("sha256", p["metadata"])
            if "output" in p:
                expected_hash = hashlib.sha256(
                    f"{p['instruction']}\n{p['input']}\n{p['output']}".encode("utf-8")
                ).hexdigest()
                self.assertEqual(p["metadata"]["sha256"], expected_hash)
            elif "chosen" in p:
                expected_hash = hashlib.sha256(
                    f"{p['instruction']}\n{p['input']}\n{p['chosen']}\n{p['rejected']}".encode("utf-8")
                ).hexdigest()
                self.assertEqual(p["metadata"]["sha256"], expected_hash)


if __name__ == "__main__":
    unittest.main()
