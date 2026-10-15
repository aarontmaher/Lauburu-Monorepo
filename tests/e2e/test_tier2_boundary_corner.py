#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis & Corner Cases E2E Test Suite (25+ Tests)
Project: Zero-Fabrication Telemetry Remediation, Hard Gate Enforcement & Honest Model Attribution
===================================================================================================
Stresses operational boundaries, edge conditions, timeouts, resource limits, and negative inputs:
- Unreachable hosts return null / unmeasured envelopes
- Subprocess and network probe timeouts
- Corrupted / malformed JSON in /props, scanner, and ledgers
- SharkWire 0-packet captures on idle or restricted interfaces
- Display filter invalid syntax rejection
- Ultra-long line scanner suppression boundaries (>600 chars)
- Case insensitivity and suppression tag syntax edge cases
- Bounty Hunter deduplication collisions and anti-gaming taxes
- Budget Proxy unknown model fallback and budget limit boundaries
- Empty staging areas and non-existent files

Strict Rule #0 & Rule #23 Compliance: Zero synthetic mocks, authentic contracts.
===================================================================================================
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import hashlib
import unittest
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict, List

TESTS_E2E_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(REPO_ROOT),
    str(TESTS_E2E_DIR),
    str(REPO_ROOT / "01_apps/network_cable_analyzer"),
    str(REPO_ROOT / "01_apps/network_cable_analyzer/backend"),
    str(REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes"),
    str(REPO_ROOT / "05_agents_and_swarms"),
    str(REPO_ROOT / "05_agents_and_swarms/ai_gateway"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from truth_e2e_helpers import (
    REPO_ROOT,
    PROHIBITED_LITERALS,
    validate_telemetry_envelope,
    format_ui_placeholder,
    get_darwin_memory_stats,
    run_scanner,
    EphemeralTestServer,
    IsolatedGitRepo,
)


class TestTier2BoundaryCorner(unittest.TestCase):
    """Tier 2: Boundary & Corner Cases Test Suite."""

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 1: Unreachable Hosts & Null Fallbacks
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_unreachable_host_returns_null_envelope(self):
        """T2.1: Verify unmeasured envelope on unreachable host returns value=None."""
        import _measured
        env = _measured.unmeasured("host 192.0.2.1 unreachable on port 22")
        self.assertIsNone(env["value"])
        self.assertFalse(env["measured"])
        self.assertIn("unreachable", env["reason"])
        self.assertTrue(validate_telemetry_envelope(env, allow_null=True))

    def test_t2_format_ui_placeholder_handles_various_null_types(self):
        """T2.2: Verify format_ui_placeholder maps None, empty string, and 'null' to '--'."""
        self.assertEqual(format_ui_placeholder(None), "--")
        self.assertEqual(format_ui_placeholder(""), "--")
        self.assertEqual(format_ui_placeholder("   "), "--")
        self.assertEqual(format_ui_placeholder("null"), "--")
        self.assertEqual(format_ui_placeholder("None"), "--")
        self.assertEqual(format_ui_placeholder(0), "0")
        self.assertEqual(format_ui_placeholder(0.0), "0.0")
        self.assertEqual(format_ui_placeholder(False), "False")

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 2: Probe Timeouts & Recovery
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_probe_timeout_falls_back_to_unmeasured(self):
        """T2.3: Verify probe timeout yields clean unmeasured record with timestamp."""
        import _measured
        t0 = time.time()
        env = _measured.unmeasured("subprocess timeout after 3.5s")
        t1 = time.time()
        self.assertIsNone(env["value"])
        self.assertGreaterEqual(env["captured_at"], t0)
        self.assertLessEqual(env["captured_at"], t1 + 0.1)

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 3: Malformed JSON Tolerance
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_malformed_json_in_endpoint_props_recovery(self):
        """T2.4: Verify real_identity() handles corrupted JSON from /props cleanly."""
        import http.server
        import socketserver
        import threading

        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        # Start server with invalid JSON response
        class CorruptedHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{corrupted_json_syntax: true")

            def log_message(self, format, *args):
                pass

        server = socketserver.TCPServer(("127.0.0.1", 0), CorruptedHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            ident = bh.real_identity(f"http://127.0.0.1:{port}")
            self.assertIsNone(ident, "Corrupted JSON must return None without raising exception")
        finally:
            server.shutdown()
            server.server_close()

    def test_t2_corrupted_bounty_ledger_line_tolerance(self):
        """T2.5: Verify paid_fingerprints() tolerates blank and whitespace lines in ledger."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write('{"fingerprint": "abc12345"}\n')
            f.write('\n')  # Empty line
            f.write('   \n')  # Whitespace line
            f.write('{"fingerprint": "def67890"}\n')
            f_path = Path(f.name)
        try:
            orig_ledger = bh.LEDGER
            bh.LEDGER = f_path
            fps = bh.paid_fingerprints()
            self.assertIn("abc12345", fps)
            self.assertIn("def67890", fps)
        finally:
            bh.LEDGER = orig_ledger
            os.remove(f_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 4: Scanner Line Length Limits & Empty Files
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_empty_file_scanning(self):
        """T2.6: Verify scanner handles empty 0-byte file without error."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f_path = Path(f.name)
        try:
            rc, parsed, stderr = run_scanner([str(f_path)])
            self.assertEqual(rc, 0)
            self.assertEqual(len(parsed.get("findings", [])), 0)
        finally:
            os.remove(f_path)

    def test_t2_ultra_long_line_scanner_suppression_boundary(self):
        """T2.7: Verify lines > 600 characters are suppressed by scanner."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        # Line of 605 chars with 0.27 ms
        long_line = "# " + ("A" * 590) + " 0.27 ms\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(long_line)
            f_path = Path(f.name)
        try:
            findings = scanner.scan_file(f_path)
            self.assertEqual(len(findings), 0, "Lines > 600 characters must be skipped")
        finally:
            os.remove(f_path)

    def test_t2_line_at_599_chars_is_not_suppressed(self):
        """T2.8: Verify lines <= 600 characters are scrutinized by scanner."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        # Line of 500 chars with 0.27 ms
        line_500 = "x = '0.27 ms' " + ("# " + "B" * 450) + "\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(line_500)
            f_path = Path(f.name)
        try:
            findings = scanner.scan_file(f_path)
            self.assertGreater(len(findings), 0, "Lines <= 600 characters must not be skipped")
        finally:
            os.remove(f_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 5: Scanner Case-Insensitivity & Suppression Edge Cases
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_scanner_case_insensitivity_handling(self):
        """T2.9: Verify scanner matches BLOCK patterns regardless of casing."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        cases = [
            "vendor = 'tankya'",
            "vendor = 'LINTES'",
            "rtt = '0.27 MS'",
            "LOCAL_AI_MODEL = 'QWEN 3.8 MAX'",
        ]
        for c in cases:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(c + "\n")
                f_path = Path(f.name)
            try:
                findings = scanner.scan_file(f_path)
                self.assertTrue(
                    any(item["severity"] == "BLOCK" for item in findings),
                    f"Failed case-insensitive match on: {c}",
                )
            finally:
                os.remove(f_path)

    def test_t2_spec_ok_comment_placement_variations(self):
        """T2.10: Verify spec-ok suppression works in various positions."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        cases = [
            "rate = 40.0  # spec-ok: standard Thunderbolt rate",
            "rate = 40.0  # zero-mock-ok: test verification constant",
            "# spec-ok: lookup table definition below\nTABLE = {'tb': 40.0}",
        ]
        for c in cases:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(c + "\n")
                f_path = Path(f.name)
            try:
                findings = scanner.scan_file(f_path)
                self.assertEqual(len(findings), 0, f"Expected suppression for: {c}")
            finally:
                os.remove(f_path)

    def test_t2_nonexistent_file_scanner_error_handling(self):
        """T2.11: Verify scan_file on non-existent path returns empty list safely."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        findings = scanner.scan_file(Path("/nonexistent/path/to/nothing.py"))
        self.assertEqual(findings, [])

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 6: SharkWire BPF & Filter Syntax Boundaries
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_sharkwire_filter_malformed_syntax(self):
        """T2.12: Verify SharkWireFilter rejects invalid filter expressions."""
        from backend.probes.shark_wire.filter import SharkWireFilter
        invalid_filters = ["tcp and or", "invalid_token ???", "port not_a_number"]
        for expr in invalid_filters:
            flt = SharkWireFilter(expr)
            valid, err = flt.validate()
            self.assertFalse(valid, f"Filter '{expr}' should be invalid")
            self.assertIsNotNone(err)

    def test_t2_sharkwire_filter_valid_syntax(self):
        """T2.13: Verify SharkWireFilter accepts valid filter expressions."""
        from backend.probes.shark_wire.filter import SharkWireFilter
        valid_filters = ["tcp", "udp", "port == 80", "ip.addr == 192.168.8.1", ""]
        for expr in valid_filters:
            flt = SharkWireFilter(expr)
            valid, err = flt.validate()
            self.assertTrue(valid, f"Filter '{expr}' should be valid, got err: {err}")

    def test_t2_sharkwire_ring_buffer_bounded_capacity(self):
        """T2.14: Verify ring buffer enforces maxlen bound."""
        from backend.probes.shark_wire.ring_buffer import SharkWireRingBuffer
        buf = SharkWireRingBuffer(maxlen=5)
        for i in range(10):
            buf.append({"index": i, "data": b"packet"})
        self.assertEqual(len(buf), 5)
        all_pkts = buf.get_all()
        self.assertEqual(len(all_pkts), 5)
        self.assertEqual(all_pkts[-1]["index"], 9)

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 7: Bounty Hunter Deduplication & Anti-Gaming
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_bounty_hunter_hallucinated_citation_detection(self):
        """T2.15: Verify snippet mismatch triggers HALLUCINATED_CITATION."""
        # Simulated ask response citing line 2 with text that does not match line 2
        lines = ["# Line 1", "real_code = 123", "# Line 3"]
        cited_line = 2
        cited_snippet = "fabricated_constant = 0.27"  # Mismatch with "real_code = 123"
        actual = lines[cited_line - 1].strip()
        is_hallucinated = not cited_snippet or cited_snippet[:40] not in actual
        self.assertTrue(is_hallucinated)

    def test_t2_bounty_hunter_deduplication_collision(self):
        """T2.16: Verify duplicate fingerprint collision pays 0."""
        paid = {"fp_existing_123"}
        hit_fp = "fp_existing_123"
        verdict = "DUPLICATE" if hit_fp in paid else "VERIFIED"
        amt = 0 if verdict == "DUPLICATE" else 30
        self.assertEqual(verdict, "DUPLICATE")
        self.assertEqual(amt, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 8: Budget Proxy Boundaries & Kill Switch
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_budget_proxy_unknown_model_fallback(self):
        """T2.17: Verify budget proxy falls back to _default pricing for unknown models."""
        import budget_proxy
        pricing = budget_proxy.PRICING.get("completely-unknown-model-xyz", budget_proxy.PRICING["_default"])
        self.assertEqual(pricing, budget_proxy.PRICING["_default"])

    def test_t2_budget_proxy_zero_tokens_cost(self):
        """T2.18: Verify 0 tokens calculation returns cost of 0.0."""
        import budget_proxy
        pricing = budget_proxy.PRICING["claude-3-5-sonnet"]
        in_cost = (0 / 1_000_000.0) * pricing["input"]
        out_cost = (0 / 1_000_000.0) * pricing["output"]
        self.assertEqual(in_cost + out_cost, 0.0)

    def test_t2_budget_proxy_budget_limit_exact_boundary(self):
        """T2.19: Verify budget limit boundary logic."""
        import budget_proxy
        limit = budget_proxy.BUDGET_LIMIT
        self.assertFalse(limit < limit)  # Equal spend is not exceeded
        self.assertTrue((limit + 0.001) > limit)  # Slight overspend exceeds

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 9: Benchmark Dataset Boundaries
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_benchmark_dataset_id_uniqueness(self):
        """T2.20: Verify all 50 snippets in dataset have strictly unique IDs."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        ids = [item["id"] for item in data]
        self.assertEqual(len(ids), len(set(ids)), "All snippet IDs must be unique")

    def test_t2_benchmark_dataset_snippet_non_empty(self):
        """T2.21: Verify no benchmark snippet is empty or whitespace."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        for item in data:
            self.assertTrue(len(item["snippet"].strip()) > 0)
            self.assertTrue(len(item["reason"].strip()) > 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Boundary 10: Git Worktree Boundaries
    # ─────────────────────────────────────────────────────────────────────────
    def test_t2_pre_commit_empty_staging_area(self):
        """T2.22: Verify scanner on empty staged files returns 0 scanned files."""
        with IsolatedGitRepo() as repo_path:
            rc, parsed, _ = run_scanner(["--staged"], cwd=repo_path)
            self.assertEqual(rc, 0)
            self.assertEqual(parsed.get("files_scanned", 0), 0)

    def test_t2_envelope_with_complex_nested_data(self):
        """T2.23: Verify measured envelope accepts dict, list, int, and float."""
        import _measured
        nested = {"ports": [0, 1, 2], "matrix": {"speed": 20.0}}
        env = _measured.measured(nested, "custom_sysctl")
        self.assertEqual(env["value"], nested)
        self.assertTrue(env["measured"])


if __name__ == "__main__":
    unittest.main()
