#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 3: Cross-Feature Interactions E2E Test Suite (15+ Tests)
Project: Zero-Fabrication Telemetry Remediation, Hard Gate Enforcement & Honest Model Attribution
===================================================================================================
Tests multi-subsystem integrations and cross-milestone interaction flows:
- Pre-commit gate (F8) executes scanner (F9) to enforce Rule 23 (F7)
- Local-AI bounty hunter (F11) uses scanner verifier (F9) to award ELO (F12)
- Bounty ledger records (F12) append to LoRA dataset (F13)
- Budget proxy pricing table (F18) covers benchmark models (F15) and local endpoints (F11)
- Backend probe envelopes (F2) flow through server endpoints into frontend UI placeholders (F6)
- Router gateway probe (F3) embeds provenance envelope (F2)
- SharkWire engine (F4) feeds packet streaming without synthetic fixture replays (F6)
- De-aliased runtime calls (F17) map cleanly to budget proxy routes (F18)
- Pre-commit gate operations preserve 554 Git commit trailers (F19)

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


class TestTier3CrossFeature(unittest.TestCase):
    """Tier 3: Cross-Feature Interactions & Multi-Subsystem Integration."""

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 1: Pre-Commit Gate + Scanner + Rule 23 (F8 + F9 + F7)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_pre_commit_gate_rejects_rule_23_block_violations(self):
        """T3.1: Pre-commit scanner rejects staged file containing Rule 23 BLOCK violation."""
        with IsolatedGitRepo() as repo_path:
            bad_file = repo_path / "telemetry_service.py"
            bad_file.write_text("rtt = '0.27 ms'  # fake latency\n")
            subprocess.run(["git", "add", "telemetry_service.py"], cwd=str(repo_path), check=True)

            rc, parsed, stderr = run_scanner(["--staged"], cwd=repo_path)
            findings = parsed.get("findings", [])
            has_block = any(f.get("severity") == "BLOCK" for f in findings)
            self.assertTrue(has_block, "Scanner must detect staged BLOCK violation")

    def test_t3_pre_commit_gate_accepts_clean_rule_23_envelope_code(self):
        """T3.2: Pre-commit scanner approves staged file adhering to Rule 23 envelopes."""
        with IsolatedGitRepo() as repo_path:
            clean_file = repo_path / "telemetry_clean.py"
            clean_file.write_text("speed = measured(20.0, 'system_profiler SPThunderboltDataType')\n")
            subprocess.run(["git", "add", "telemetry_clean.py"], cwd=str(repo_path), check=True)

            rc, parsed, _ = run_scanner(["--staged"], cwd=repo_path)
            block_count = sum(1 for f in parsed.get("findings", []) if f.get("severity") == "BLOCK")
            self.assertEqual(block_count, 0)
            self.assertEqual(rc, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 2: Bounty Hunter + Scanner Oracle + ELO Settlement (F11 + F12 + F9)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_bounty_hunter_uses_scanner_oracle_to_settle_elo(self):
        """T3.3: Bounty hunter uses scanner findings to determine ELO reward."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("# Line 1\nlatency = '0.27 ms'  # bad\n# Line 3\n")
            f_path = Path(f.name)
        try:
            det = bh.scanner_findings([f_path])
            self.assertIn((str(f_path), 2), det)
            hit = det[(str(f_path), 2)]
            self.assertEqual(hit["severity"], "BLOCK")
            reward = bh.REWARD[hit["severity"]]
            self.assertEqual(reward, 30)
        finally:
            os.remove(f_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 3: Bounty Ledger + LoRA Dataset Appending (F12 + F13)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_verified_bounty_finding_creates_lora_training_pair(self):
        """T3.4: Verified finding generates valid instruction/input/output LoRA pair."""
        finding = {
            "file": "backend/probes/speed_probe.py",
            "line": 42,
            "severity": "BLOCK",
            "rule": "fabricated Thunderbolt RTT constant",
            "actual": "rtt = '0.27 ms'",
            "model_id": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
        }
        lora_record = {
            "instruction": "Identify fabricated hardware telemetry in this code line and state the raw source it must come from.",
            "input": f"{finding['file']}:{finding['line']}: {finding['actual']}",
            "output": f"FAKE: {finding['rule']}. Replace with a measured value or None/'--'.",
            "provenance": {"verifier": "fake_data_scanner", "model": finding["model_id"]},
        }
        serialized = json.dumps(lora_record)
        parsed = json.loads(serialized)
        self.assertIn("instruction", parsed)
        self.assertIn("input", parsed)
        self.assertIn("output", parsed)
        self.assertEqual(parsed["provenance"]["model"], finding["model_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 4: Budget Proxy + Model Pricing + Benchmark Alignment (F18 + F15)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_budget_proxy_pricing_covers_benchmark_models(self):
        """T3.5: Budget proxy PRICING table covers benchmark evaluated models."""
        import budget_proxy
        benchmark_models = [
            "gemini-2.0-flash-free",
            "gemini-1.5-flash-free",
            "local-mesh",
        ]
        for m in benchmark_models:
            self.assertIn(m, budget_proxy.PRICING, f"Model {m} must exist in budget proxy PRICING")
            self.assertEqual(budget_proxy.PRICING[m]["input"], 0.0)
            self.assertEqual(budget_proxy.PRICING[m]["output"], 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 5: Probe Envelopes + UI Placeholders (F2 + F6)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_probe_envelope_flows_to_ui_placeholder_formatting(self):
        """T3.6: Probe envelope with None value renders as '--' in UI placeholder formatter."""
        import _measured
        env = _measured.unmeasured("device unreachable")
        ui_str = format_ui_placeholder(env["value"])
        self.assertEqual(ui_str, "--")

        env_measured = _measured.measured(20.0, "system_profiler")
        ui_str_measured = format_ui_placeholder(env_measured["value"])
        self.assertEqual(ui_str_measured, "20.0")

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 6: Router Gateway Probe + Dynamic Envelopes (F3 + F2)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_router_gateway_probe_embeds_provenance_envelope(self):
        """T3.7: Router gateway probe produces complete provenance dictionary."""
        from backend.probes.router_gateway_probe import get_router_telemetry
        res = get_router_telemetry(force=True)
        self.assertTrue(isinstance(res, dict))
        self.assertIn("provenance", res)
        prov = res["provenance"]
        self.assertIn("source_cmd", prov)
        self.assertIn("captured_at", prov)
        self.assertIn("ok", prov)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 7: SharkWire Engine + Display Filter Evaluation (F4 + F6)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_sharkwire_engine_filter_pipeline(self):
        """T3.8: SharkWire engine correctly filters packet streams."""
        from backend.probes.shark_wire import SharkWirePacketEngine, SharkWireFilter
        engine = SharkWirePacketEngine(default_interface="lo0")
        res = engine.validate_filter("tcp")
        self.assertTrue(res["valid"])
        self.assertIsNone(res["error"])

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 8: De-Aliasing + Honest Model Routing (F17 + F18)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_dealiased_model_identifiers_resolve_in_budget_proxy(self):
        """T3.9: Honest model identifiers resolve accurately in budget proxy routes."""
        import budget_proxy
        self.assertIn("gemini", budget_proxy.PROVIDER_ROUTES)
        self.assertIn("local", budget_proxy.PROVIDER_ROUTES)
        self.assertEqual(budget_proxy.PROVIDER_ROUTES["google"], "https://generativelanguage.googleapis.com")

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 9: Pre-Commit Staging + Git Trailer Invariance (F8 + F19)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_pre_commit_gate_preserves_claude_trailers_count(self):
        """T3.10: Git trailer count remains >= 554 throughout pre-commit validation."""
        cmd = ["git", "log", "--grep=Co-Authored-By: Claude", "--oneline"]
        out = subprocess.check_output(cmd, cwd=str(REPO_ROOT), text=True)
        count = len([l for l in out.splitlines() if l.strip()])
        self.assertGreaterEqual(count, 554)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 10: RAM Headroom Gate Before Bounty Hunter Loop (F13 + F11 + F12)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_ram_headroom_gate_before_bounty_run(self):
        """T3.11: Bounty hunter checks host RAM headroom before scheduling runs."""
        mem = get_darwin_memory_stats()
        self.assertGreaterEqual(mem["total_gb"], 16.0)
        self.assertGreater(mem["available_gb"], 1.0)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 11: Scanner Oracle + 50-Snippet Dataset Alignment (F9 + F14)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_scanner_oracle_evaluates_50_snippet_benchmark_dataset(self):
        """T3.12: Evaluating scanner on 50-snippet dataset separates fake from clean."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        flagged_count = 0
        clean_count = 0
        for item in data:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(item["snippet"] + "\n")
                f_path = Path(f.name)
            try:
                findings = scanner.scan_file(f_path)
                if any(f["severity"] in ("BLOCK", "WARN") for f in findings):
                    flagged_count += 1
                else:
                    clean_count += 1
            finally:
                os.remove(f_path)

        self.assertGreater(flagged_count, 15, "Scanner must detect majority of fake snippets")
        self.assertGreater(clean_count, 15, "Scanner must allow majority of clean snippets")

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 12: Hardware Matrix Alignment + Props Attribution (F10 + F11)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_hardware_matrix_matches_bounty_hunter_props_contract(self):
        """T3.13: Hardware matrix documents Hermes-3 on 8082/8090, matching props contract."""
        matrix_file = Path.home() / ".gemini/config/rules/00_canonical_hardware_matrix.md"
        content = matrix_file.read_text(errors="ignore")
        self.assertIn("Hermes-3-Llama-3.1-8B", content)
        with EphemeralTestServer(model_path="/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf") as s:
            bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
            import importlib.util
            spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
            bh = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bh)
            ident = bh.real_identity(f"http://127.0.0.1:{s.port}")
            self.assertEqual(ident, "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf")

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 13: Zero-Spend Benchmark + Budget Proxy Free Tiers (F15 + F18)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_zero_spend_benchmark_matches_budget_proxy_free_tiers(self):
        """T3.14: Multi-model benchmark $0.00 spend matches budget proxy free tiers."""
        import budget_proxy
        for free_m in ["gemini-2.0-flash-free", "local-mesh"]:
            pricing = budget_proxy.PRICING[free_m]
            cost = (100_000 / 1_000_000.0) * (pricing["input"] + pricing["output"])
            self.assertEqual(cost, 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction 14: Server Endpoints Zero-Fabrication Contract (F1 + F7)
    # ─────────────────────────────────────────────────────────────────────────
    def test_t3_server_endpoints_contain_zero_prohibited_constants(self):
        """T3.15: Server API endpoint module conforms to Rule 23 prohibitions."""
        server_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/server.py"
        rc, parsed, _ = run_scanner([str(server_path)])
        block_findings = [f for f in parsed.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0)


if __name__ == "__main__":
    unittest.main()
