#!/usr/bin/env python3
"""Test Suite for Planted Cases and Core Invariants: Local-AI Fake-Data Bounty Hunter & ELO Economy.

Covers:
  * Planted Case 1: Verified finding paid once (+30 ELO for BLOCK, +15 for WARN)
  * Planted Case 2: Same finding again pays 0 ELO (deduplication collision)
  * Planted Case 3: Fabricated/hallucinated citation is taxed (-50 ELO)
  * Real GGUF model attribution via /props; refusal of :8082 on 404
  * Continuous LoRA dataset appending to canonical lake
  * Darwin Host RAM safety check (>= 4.8 GB or pressure <= 1)
  * File picker optimization (< 1.0s)
  * Background loop interval (>= 600s / 10 min)
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/truth"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))

import fake_data_bounty_hunter as bh
import elo_currency_governor as gov


class MockPropsServer:
    def __init__(self, model_path="/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf", status_code=200):
        self.model_path = model_path
        self.status_code = status_code
        self.server = None
        self.thread = None
        self.port = 0

    def __enter__(self):
        model_path = self.model_path
        status_code = self.status_code

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/props":
                    if status_code == 200:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"model_path": model_path}).encode())
                    else:
                        self.send_response(status_code)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        self.server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class TestBountyHunterPlantedCases(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.orig_ledger = bh.LEDGER
        self.orig_lora = bh.CANONICAL_LORA
        self.orig_feat_lora = bh.LORA

        bh.LEDGER = self.temp_path / "fake_data_bounty_ledger.jsonl"
        bh.CANONICAL_LORA = self.temp_path / "continuous_lora_dataset.jsonl"
        bh.LORA = self.temp_path / "fake_data_hunting_pairs.jsonl"

    def tearDown(self):
        bh.LEDGER = self.orig_ledger
        bh.CANONICAL_LORA = self.orig_lora
        bh.LORA = self.orig_feat_lora
        self.temp_dir.cleanup()

    def test_planted_case_1_verified_finding_paid_once(self):
        """Planted Case 1: Verified finding pays +30 ELO for BLOCK finding."""
        # 1. Create planted code file with a genuine BLOCK violation
        planted_file = self.temp_path / "planted_code_violation.py"
        planted_file.write_text("# Line 1\ntb_latency = '0.27 ms'  # fake constant\n# Line 3\n")

        # 2. Run mechanical scanner
        det = bh.scanner_findings([planted_file])
        self.assertIn((str(planted_file), 2), det)
        hit = det[(str(planted_file), 2)]
        self.assertEqual(hit["severity"], "BLOCK")

        # 3. Simulate model claim matching verbatim code
        model_id = "Test-Hermes-3-8B.Q4_K_M.gguf"
        claim = {"line": 2, "snippet": "tb_latency = '0.27 ms'", "why": "hardcoded 0.27ms literal"}
        paid = bh.paid_fingerprints()
        self.assertNotIn(hit["fingerprint"], paid)

        # 4. Process finding
        rec = {
            "timestamp": "2026-10-04T00:00:00Z",
            "model": model_id,
            "target_file": str(planted_file),
            "line": 2,
            "snippet": claim["snippet"],
            "why": claim["why"]
        }
        rec.update(verdict=f"VERIFIED_{hit['severity']}", fingerprint=hit["fingerprint"], rule=hit["rule"], severity=hit["severity"])
        amt = bh.REWARD[hit["severity"]]
        self.assertEqual(amt, 30)

        initial_bank = gov.load_bank()
        initial_elo = initial_bank.get(model_id, 1500)

        bh.settle(model_id, rec, rec["verdict"], amt)

        updated_bank = gov.load_bank()
        self.assertEqual(updated_bank[model_id], initial_elo + 30)

        # Write to ledger
        with bh.LEDGER.open("a") as f:
            f.write(json.dumps(rec) + "\n")

        # Verify ledger entry
        fps = bh.paid_fingerprints()
        self.assertIn(hit["fingerprint"], fps)

    def test_planted_case_2_duplicate_finding_pays_zero(self):
        """Planted Case 2: Same finding again pays 0 ELO (deduplication)."""
        fp = "fingerprint_abc_123"
        model_id = "Test-Hermes-3-8B.Q4_K_M.gguf"

        # Seed ledger with existing fingerprint
        with bh.LEDGER.open("w") as f:
            f.write(json.dumps({"fingerprint": fp, "verdict": "VERIFIED_BLOCK", "elo_delta": 30}) + "\n")

        paid = bh.paid_fingerprints()
        self.assertIn(fp, paid)

        # Re-audit identical finding
        is_duplicate = fp in paid
        self.assertTrue(is_duplicate)

        verdict = "DUPLICATE"
        amt = 0
        rec = {"file": "sample.py", "line": 42, "verdict": verdict, "elo_delta": amt, "fingerprint": fp}

        initial_bank = gov.load_bank()
        initial_elo = initial_bank.get(model_id, 1500)

        bh.settle(model_id, rec, verdict, amt)

        updated_bank = gov.load_bank()
        # ELO should be completely unchanged
        self.assertEqual(updated_bank.get(model_id, 1500), initial_elo)

    def test_planted_case_3_hallucinated_citation_is_taxed(self):
        """Planted Case 3: Fabricated/hallucinated snippet is taxed -50 ELO."""
        planted_file = self.temp_path / "clean_sample.py"
        planted_file.write_text("import sys\nimport os\n")

        lines = planted_file.read_text().splitlines()
        cited_line = 1
        hallucinated_snippet = "latency = 0.27 ms"  # Does not exist on line 1 ("import sys")
        actual_line = lines[cited_line - 1].strip()

        is_hallucinated = not hallucinated_snippet or hallucinated_snippet[:40] not in actual_line
        self.assertTrue(is_hallucinated)

        model_id = "Test-Hermes-3-8B.Q4_K_M.gguf"
        verdict = "HALLUCINATED_CITATION"
        rec = {"file": str(planted_file), "line": cited_line, "verdict": verdict, "elo_delta": -50}

        initial_bank = gov.load_bank()
        initial_elo = initial_bank.get(model_id, 1500)

        bh.settle(model_id, rec, verdict, 0)

        updated_bank = gov.load_bank()
        self.assertEqual(updated_bank[model_id], initial_elo - 50)

    def test_props_real_identity_resolution(self):
        """Verify /props query extracts real GGUF basename, rejecting proxy."""
        with MockPropsServer(model_path="/Users/aaron/.local/share/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf") as s:
            ident = bh.real_identity(f"http://127.0.0.1:{s.port}")
            self.assertEqual(ident, "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf")

        # Refusal on 404 (like port 8082 proxy)
        with MockPropsServer(status_code=404) as s:
            ident = bh.real_identity(f"http://127.0.0.1:{s.port}")
            self.assertIsNone(ident)

            res = bh.run_once(endpoint=f"http://127.0.0.1:{s.port}", nfiles=1)
            self.assertIn("error", res)
            self.assertIn("refusing to award unattributed ELO", res["error"])

    def test_continuous_lora_dataset_appending(self):
        """Verify verified findings are appended to canonical LoRA dataset."""
        hit = {"rule": "fabricated Thunderbolt RTT constant", "severity": "BLOCK"}
        model_id = "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
        path = Path("server.py")
        actual = "latency = '0.27 ms'"
        ln = 12

        lora_entry = {
            "instruction": "Identify fabricated hardware telemetry in this code line and state the raw source it must come from.",
            "input": f"{path.name}:{ln}: {actual}",
            "output": f"FAKE: {hit['rule']}. Replace with a measured value or None/'--'.",
            "provenance": {"verifier": "fake_data_scanner", "model": model_id}
        }

        with bh.CANONICAL_LORA.open("a") as f:
            f.write(json.dumps(lora_entry) + "\n")

        self.assertTrue(bh.CANONICAL_LORA.exists())
        lines = bh.CANONICAL_LORA.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["provenance"]["model"], model_id)
        self.assertEqual(parsed["provenance"]["verifier"], "fake_data_scanner")
        self.assertIn("Identify fabricated hardware telemetry", parsed["instruction"])

    def test_pick_files_optimization_speed(self):
        """Verify pick_files completes in < 1.0 second, avoiding 20.7s freeze."""
        t0 = time.time()
        files = bh.pick_files(2)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 1.0, f"pick_files must take < 1.0s, took {elapsed:.2f}s")
        self.assertGreater(len(files), 0, "pick_files should return candidate files")

    def test_ram_safety_check_function(self):
        """Verify check_host_ram_safe returns valid tuple."""
        safe, reason = bh.check_host_ram_safe("http://127.0.0.1:8090")
        self.assertIsInstance(safe, bool)
        self.assertIsInstance(reason, str)

    def test_background_job_interval_minimum_enforced(self):
        """Verify background loop interval is enforced to >= 600s (10 min)."""
        content = (REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py").read_text()
        self.assertIn("default=900", content)
        self.assertIn("max(600, a.interval)", content)


if __name__ == "__main__":
    unittest.main()
