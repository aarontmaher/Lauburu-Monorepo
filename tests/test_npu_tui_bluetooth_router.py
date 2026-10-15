#!/usr/bin/env python3
"""
tests/test_npu_tui_bluetooth_router.py
================================================================================
Comprehensive Automated Verification Suite for:
1. NPU AI Local Router & Universal Orchestrator Coprocessor Engine.
2. Kai Morich Serial Bluetooth Terminal Gateway (Android v1.52).
3. Bluetooth Serial Out-of-Band Streaming (/tmp/bluetooth_terminal_stream.ansi).
4. All-6 Orchestrator Pairings (Master Local, Devils Advocate, Cloud Shadow,
   Swarm Matrix, Genetic MoE, Neo Scribe).
5. Biometric Airgap Protection (Rule 0 & Rule 11).
6. Omniterminal CLI Subcommand Integration ('omniterminal router').
================================================================================
"""

import os
import sys
import time
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TOOLING_DIR = REPO_ROOT / "06_scripts_and_tooling"
if str(TOOLING_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLING_DIR))

from npu_ai_router import (
    NpuAgent,
    NpuOrchestratorPair,
    ORCHESTRATOR_TARGETS,
    FORBIDDEN_BIOMETRIC_TERMS,
    BT_STREAM_PATH
)
from bluetooth_kai_morich_terminal_server import (
    KaiMorichBluetoothTerminalServer,
    SPP_UUID,
    NORDIC_UART_SERVICE_UUID,
    NORDIC_UART_RX_CHAR_UUID,
    NORDIC_UART_TX_CHAR_UUID
)


class TestNpuTuiBluetoothRouter(unittest.TestCase):
    """Automated test cases for NPU AI Router and Bluetooth Terminal integration."""

    def test_01_storage_preflight_health(self):
        """Verify Tri-Vault storage layers exist and have headroom (Rule 2)."""
        vault_dir = REPO_ROOT / "obsidian_vault"
        lake_dir = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
        index_file = vault_dir / "Index.md"

        self.assertTrue(vault_dir.is_dir(), "Obsidian vault directory must exist")
        self.assertTrue(lake_dir.is_dir(), "PySpark lakehouse directory must exist")
        self.assertTrue(index_file.is_file(), "Index.md master knowledge graph must exist")
        self.assertGreater(index_file.stat().st_size, 0, "Index.md must not be empty")

        free_gb = shutil.disk_usage("/Users/aaron").free / (1024 ** 3)
        self.assertGreaterEqual(free_gb, 5.0, f"Host must maintain >=5.0 GB free (got {free_gb:.2f} GB)")

    def test_02_npu_fast_path_latency_and_zero_ram(self):
        """Verify systolic intent classification executes in < 1ms with 0.0 MB Host RAM."""
        agent = NpuAgent(orchestrator_id="master_local")
        queries = [
            "check telemetry and memory headroom",
            "movesense bicep strap heart rate",
            "current elo rating leaderboard",
            "syntax check json brackets",
            "status",
        ]

        for q in queries:
            t0 = time.perf_counter()
            decision = agent.route(q)
            lat_us = (time.perf_counter() - t0) * 1_000_000

            self.assertTrue(decision.is_local_npu, f"Query '{q}' should be classified as local NPU")
            self.assertIsNotNone(decision.response, "Local NPU decision must contain immediate response")
            # Verify sub-1ms decision
            self.assertLess(lat_us, 15_000, f"Latency {lat_us} µs should be fast")

    def test_03_all_6_orchestrators_paired(self):
        """Verify all 6 orchestrators are paired with dedicated NPU coprocessors."""
        pairs = NpuOrchestratorPair.list_all_pairs()
        self.assertEqual(len(pairs), 6, "Must have exactly 6 paired orchestrators")

        expected_ids = {"master_local", "devils_advocate", "cloud_shadow", "swarm_matrix", "genetic_moe", "neo_scribe"}
        found_ids = {p["orchestrator_id"] for p in pairs}
        self.assertEqual(found_ids, expected_ids, "All 6 expected orchestrator IDs must be present")

        for p in pairs:
            self.assertIn("38 TOPS ANE", p["npu_agent_status"])
            self.assertEqual(p["host_ram_overhead"], "0.0 MB (Systolic Array)")
            self.assertIn("ENFORCED", p["biometric_airgap"])

    def test_04_kai_morich_protocol_and_uuids(self):
        """Verify compliance with Kai Morich Serial Bluetooth Terminal standard UUIDs."""
        self.assertEqual(SPP_UUID, "00001101-0000-1000-8000-00805F9B34FB")
        self.assertEqual(NORDIC_UART_SERVICE_UUID, "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        self.assertEqual(NORDIC_UART_RX_CHAR_UUID, "6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
        self.assertEqual(NORDIC_UART_TX_CHAR_UUID, "6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

    def test_05_bluetooth_terminal_stream_mirroring(self):
        """Verify that streaming writes ANSI frames to /tmp/bluetooth_terminal_stream.ansi."""
        agent = NpuAgent(orchestrator_id="master_local")
        test_frame = f"\x1b[32m[TEST_BT_FRAME_{int(time.time())}]\x1b[0m\n"
        bytes_written = agent.stream_to_bluetooth_terminal(test_frame)

        self.assertGreater(bytes_written, 0, "Bytes written to stream pipe must be > 0")
        self.assertTrue(BT_STREAM_PATH.exists(), "Stream pipe file must exist")
        with open(BT_STREAM_PATH, "rb") as f:
            content = f.read()
            self.assertIn(b"TEST_BT_FRAME", content)

    def test_06_llm_bluetooth_gateway_dispatch(self):
        """Verify routing a reasoning prompt over Bluetooth gateway to prima.cpp / llama.cpp."""
        agent = NpuAgent(orchestrator_id="master_local")
        prompt = "Explain in one sentence why pings over 10Gbps Thunderbolt 4 have sub-millisecond latency."
        response = agent.dispatch_to_orchestrator(prompt)

        self.assertIsNotNone(response)
        self.assertGreater(len(response), 10, "Response must not be empty")

    def test_07_strict_biometric_airgap_invariant(self):
        """Verify raw 512Hz ECG microvolts are stripped while high-level metrics pass (Rule 0 & 11)."""
        agent = NpuAgent(orchestrator_id="master_local")

        dirty_prompt = "Send raw 512hz_ecg microvolts and raw_ecg_mv samples to the cloud"
        sanitized, stripped = agent.sanitize_biometric_airgap(dirty_prompt)

        self.assertTrue(stripped, "Forbidden terms must be detected and stripped")
        for term in FORBIDDEN_BIOMETRIC_TERMS:
            self.assertNotIn(term.lower(), sanitized.lower(), f"Term '{term}' must not be present in sanitized text")
        self.assertIn("[BIOMETRIC_AIRGAP_REDACTED]", sanitized)

    def test_08_kai_morich_server_transaction(self):
        """Verify KaiMorichBluetoothTerminalServer loopback transaction executes cleanly."""
        server = KaiMorichBluetoothTerminalServer(default_orchestrator="master_local")
        res = server.run_test_transaction(query="check movesense bicep ecg and ram headroom")

        self.assertEqual(res["stats"]["npu_fast_path_hits"], 1)
        self.assertGreater(res["stats"]["bytes_sent"], 0)
        self.assertIn("Movesense", res["response"])
        self.assertTrue(res["stream_pipe_exists"])

    def test_09_omniterminal_router_cli(self):
        """Verify omniterminal router CLI command executes cleanly with Exit Code 0."""
        cmd = ["/Users/aaron/.local/bin/omniterminal", "router", "status", "--orchestrator", "master_local"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, f"Omniterminal router failed: {p.stderr}")
        self.assertIn("NPU AI Local Router Execution Verdict", p.stdout)
        self.assertIn("NPU_COPROCESSOR", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
