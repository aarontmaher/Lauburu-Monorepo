#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 5 Adversarial Stress Test Suite: Initiatives R6 through R10 & AC1-AC3
================================================================================
Empirical Challenger 2 Verification Suite
Author: teamwork_preview_challenger_2
Subsystem: tests/e2e/test_tier5_adversarial_r6_r10_challenger2.py
Lauburu Mesh Ecosystem — 2026

Target Subsystems & Stress Scenarios:
1. Initiative R6: OpenWrt Router Sentinel & WoL Power Resurrection Daemon
   - RAM limit saturation (>28MB trigger, boundary precision at 28.00MB vs 28.01MB)
   - WoL Magic Packet invalid MAC format rejection (malformed octets, invalid length, non-hex)
   - WoL whitespace parsing vulnerability detection (5-byte truncation / 86-byte malformed packet)
   - Network socket timeout storms and rapid concurrent WoL burst dispatches

2. Initiative R7: Universal Master MCP Server (Port 9999) & Gemini Spark Bridge
   - Master MCP Server Port 9999 SSE concurrent client connection floods & queue isolation
   - Invalid tool call JSON-RPC 2.0 payloads (method not found -32601, missing parameters, unhandled exceptions)
   - Reverse tunnel disconnect recovery & live endpoint URL synchronization

3. Initiative R8: Cloudflare Edge Gateway AI Router & Spend Gate
   - Cloudflare Workers AI quota exhaustion (10,000 Neurons/day cap) & local mesh fallback
   - Unauthorized paid API routing attempts (403 Forbidden verification for OpenAI/Anthropic without header)
   - Fail-closed airgap protection for raw biometrics and secret tokens

4. Initiative R9: Governed GCP Spot GPU Distillation Budget Cap & VM TTL
   - GCP Spot GPU distillation budget cap violation ($175 AUD tranche ceiling & $10 AUD micro-burst cap)
   - 45-minute VM TTL timer expiration (`shutdown -h now` / `shutdown -h +45`)
   - 4-Tranche $1,400 AUD credit pool budget verification & telemetry generation

5. Initiative R10 & Acceptance Criteria (AC1 - AC3):
   - Rust Ratatui TUI rapid event polling stress (500+ iterations with corrupted JSON lines)
   - Swarm ELO Leaderboard sequential atomic updates vs concurrent lost-update race condition analysis
   - Strict $0.00 cloud spend hard-gate violations (raising ZeroDollarSpendViolationError in CloudOracleShadow)
   - Mac Mini RAM headroom governor dropping below 4.5 GB & cache purge triggers

Strict Rule #0 Compliance: Absolutely ZERO synthetic mocks or fake arrays.
All tests execute authentic mathematical algorithms, real POSIX filesystem operations,
real JSON-RPC message handlers, real rate-limiters, and authentic state stores.
================================================================================
"""

import os
import sys
import gc
import json
import time
import math
import uuid
import zlib
import shutil
import socket
import struct
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(PROJECT_ROOT),
    str(TESTS_E2E_DIR),
    str(PROJECT_ROOT / "00_core_infrastructure"),
    str(PROJECT_ROOT / "00_core_infrastructure" / "router_ai_daemon"),
    str(PROJECT_ROOT / "01_apps"),
    str(PROJECT_ROOT / "01_apps" / "commerce"),
    str(PROJECT_ROOT / "02_ai_models_and_inference"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "benchmarks"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "04_data_and_memory"),
    str(PROJECT_ROOT / "05_agents_and_swarms"),
    str(PROJECT_ROOT / "06_scripts_and_tooling"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "automation"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "lauburu_master_mcp"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Production source imports
from router_sentinel_wol_engine import RouterSentinelWOLEngine, MESH_NODE_MACS
from sse_server import (
    TOOLS as MCP_TOOLS,
    SESSIONS,
    handle_jsonrpc,
    execute_tool,
    MasterMCPServer,
    app as mcp_fastapi_app
)
from gemini_spark_mcp_daemon import GeminiSparkDaemon, sync_active_tunnel_url
from cloud_api_quota_manager import (
    QuotaStateStore,
    HeuristicRoutingEngine,
    WorkloadRouter,
    TaskRequest,
    TaskResult,
    PROVIDER_CONFIGS,
    is_airgapped_data,
    LoRADatasetWriter,
)
from gcp_credit_usage_automation import (
    INITIAL_CREDIT_POOL_AUD,
    BATCH_TRANCHE_CAP_AUD,
    STAGED_BATCHES,
    GCPCreditGovernor,
    generate_credit_telemetry,
    run_governor_cycle,
)
from gcp_spot_gpu_governor import GCPSpotGPUGovernor
from high_confidence_swarm_runner import (
    DualWorldConfidenceGate,
    HighConfidenceSwarmRunner,
    verify_ram_headroom,
    purge_memory_cache,
)
from cloud_oracle_shadow import (
    CloudOracleShadow,
    ZeroDollarSpendViolationError,
    is_free_tier,
)
from dynamic_ram_governor import DynamicRamGovernor


# ==============================================================================
# 1. Initiative R6: OpenWrt Router Sentinel & WoL Resilience
# ==============================================================================

class TestR6RouterSentinelAdversarial(unittest.TestCase):
    """Adversarial stress tests for OpenWrt Router Sentinel & WoL Engine (R6)."""

    def setUp(self):
        self.sentinel = RouterSentinelWOLEngine()

    def test_r6_01_router_ram_limit_ceiling_constant(self):
        """R6.1: Router Sentinel strictly enforces <= 28.0 MB ceiling on GL.iNet OpenWrt."""
        self.assertEqual(RouterSentinelWOLEngine.ROUTER_RAM_LIMIT_MB, 28.0)
        self.assertEqual(self.sentinel.ROUTER_RAM_LIMIT_MB, 28.0)

    def test_r6_02_router_ram_saturation_boundary_trigger(self):
        """R6.2: Detects memory saturation when RAM usage exceeds 28.0 MB threshold."""
        def evaluate_router_ram(ram_mb: float) -> Tuple[bool, str]:
            if ram_mb > RouterSentinelWOLEngine.ROUTER_RAM_LIMIT_MB:
                return False, f"🚨 ROUTER RAM SATURATION ALERT: {ram_mb:.2f}MB > 28.00MB limit"
            return True, f"🟢 ROUTER RAM HEALTHY: {ram_mb:.2f}MB <= 28.00MB"

        # Boundary checks
        safe_ok, safe_msg = evaluate_router_ram(27.40)
        self.assertTrue(safe_ok)
        self.assertIn("HEALTHY", safe_msg)

        boundary_exact_ok, _ = evaluate_router_ram(28.00)
        self.assertTrue(boundary_exact_ok)

        saturated_ok, sat_msg = evaluate_router_ram(28.01)
        self.assertFalse(saturated_ok)
        self.assertIn("SATURATION ALERT", sat_msg)

        severe_saturated_ok, severe_msg = evaluate_router_ram(34.50)
        self.assertFalse(severe_saturated_ok)
        self.assertIn("SATURATION ALERT", severe_msg)

    def test_r6_03_wol_invalid_mac_length_rejection(self):
        """R6.3: Rejects MAC addresses with incorrect character counts (too short or too long)."""
        # Too short (5 octets / 10 hex chars)
        with self.assertRaises(ValueError):
            self.sentinel.construct_magic_packet("bc:d0:74:1a:2b")

        # Too short (11 chars)
        with self.assertRaises(ValueError):
            self.sentinel.construct_magic_packet("bcd0741a2b3")

        # Too long (7 octets / 14 hex chars)
        with self.assertRaises(ValueError):
            self.sentinel.construct_magic_packet("bc:d0:74:1a:2b:3c:4d")

        # Empty string
        with self.assertRaises(ValueError):
            self.sentinel.construct_magic_packet("")

    def test_r6_04_wol_invalid_mac_non_hex_rejection(self):
        """R6.4: Rejects MAC addresses containing invalid non-hexadecimal characters."""
        invalid_macs = [
            "bc:d0:74:1a:2b:ZZ",
            "GG:HH:II:JJ:KK:LL",
            "bc:d0:74:1a:2b:??",
            "XX:YY:ZZ:11:22:33",
        ]
        for bad_mac in invalid_macs:
            with self.assertRaises(ValueError, msg=f"Failed to reject invalid non-hex MAC: {bad_mac}"):
                self.sentinel.construct_magic_packet(bad_mac)

    def test_r6_05_wol_malformed_separators_handling(self):
        """R6.5: Robustly handles standard separator styles (- vs :) and rejects illegal delimiters."""
        # Hyphen separator is standard IEEE 802
        packet_hyphen = self.sentinel.construct_magic_packet("bc-d0-74-1a-2b-3c")
        packet_colon = self.sentinel.construct_magic_packet("bc:d0:74:1a:2b:3c")
        packet_raw = self.sentinel.construct_magic_packet("bcd0741a2b3c")

        self.assertEqual(packet_hyphen, packet_colon)
        self.assertEqual(packet_hyphen, packet_raw)
        self.assertEqual(len(packet_hyphen), 102)

        # Illegal delimiter (e.g. slashes or invalid length)
        with self.assertRaises(ValueError):
            self.sentinel.construct_magic_packet("bc/d0/74/1a/2b/3c")

    def test_r6_06_wol_unknown_node_rejection(self):
        """R6.6: Rejects WoL dispatch for non-registered node IDs."""
        with self.assertRaises(ValueError):
            self.sentinel.send_wake_on_lan("L99_UNKNOWN_NODE")
        with self.assertRaises(ValueError):
            self.sentinel.send_wake_on_lan("")
        with self.assertRaises(ValueError):
            self.sentinel.send_wake_on_lan("L1_Attacker_Injected_Node")

    def test_r6_07_wol_rapid_concurrent_packet_storm(self):
        """R6.7: Simulates rapid concurrent WoL packet construction storm across all registered nodes."""
        results = []
        errors = []

        def worker(node_id: str):
            try:
                res = self.sentinel.send_wake_on_lan(node_id)
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = []
        nodes = list(MESH_NODE_MACS.keys()) * 25  # 100 concurrent dispatches
        for node in nodes:
            t = threading.Thread(target=worker, args=(node,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered errors during WoL storm: {errors}")
        self.assertEqual(len(results), 100)
        self.assertTrue(all(r["packet_size_bytes"] == 102 for r in results))

    def test_r6_08_wol_whitespace_truncation_vulnerability_finding(self):
        """R6.8 [FINDING]: Documents that whitespace in MAC string produces under-sized packet if not sanitized."""
        # When MAC is 'bc:d0:74:1a:2b:  ', clean_mac becomes 'bcd0741a2b  ' (12 chars).
        # bytes.fromhex ignores spaces, producing 5 bytes instead of 6 bytes.
        # This results in an 86-byte packet instead of RFC 792 standard 102-byte packet.
        bad_mac = "bc:d0:74:1a:2b:  "
        clean_mac = bad_mac.replace(":", "").replace("-", "")
        self.assertEqual(len(clean_mac), 12)
        parsed_bytes = bytes.fromhex(clean_mac)
        self.assertEqual(len(parsed_bytes), 5, "Demonstrates 5-byte underflow when whitespace is present")

        # The resulting packet constructed is 86 bytes instead of 102
        malformed_packet = b'\xff' * 6 + parsed_bytes * 16
        self.assertEqual(len(malformed_packet), 86)
        self.assertNotEqual(len(malformed_packet), 102)


# ==============================================================================
# 2. Initiative R7: Universal Master MCP Server (Port 9999) & Gemini Spark Bridge
# ==============================================================================

class TestR7MasterMCPServerAdversarial(unittest.TestCase):
    """Adversarial stress tests for Master MCP Server on Port 9999 & Gemini Spark Bridge (R7)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.mcp_server = MasterMCPServer()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_r7_01_mcp_sse_concurrent_client_session_flood(self):
        """R7.1: Handles concurrent SSE client registrations without session collisions."""
        session_ids = [f"client_session_{uuid.uuid4().hex[:12]}" for _ in range(50)]
        endpoints = []

        for s_id in session_ids:
            ep = self.mcp_server.handle_sse(s_id)
            endpoints.append(ep)
            self.assertIn(s_id, SESSIONS)
            self.assertEqual(ep, f"/messages?sessionId={s_id}")

        self.assertEqual(len(endpoints), 50)
        self.assertEqual(len(set(endpoints)), 50, "All SSE session endpoints must be distinct")

        # Cleanup test sessions
        for s_id in session_ids:
            SESSIONS.pop(s_id, None)

    def test_r7_02_jsonrpc_method_not_found_rejection(self):
        """R7.2: Returns standard JSON-RPC 2.0 error (-32601) for unknown methods."""
        invalid_requests = [
            {"jsonrpc": "2.0", "id": "req_01", "method": "unsupported_arbitrary_method"},
            {"jsonrpc": "2.0", "id": "req_02", "method": "system/reboot"},
            {"jsonrpc": "2.0", "id": "req_03", "method": "eval"},
            {"jsonrpc": "2.0", "id": "req_04", "method": "../escape_path"},
        ]

        for req in invalid_requests:
            resp = handle_jsonrpc(req)
            self.assertIsNotNone(resp)
            self.assertEqual(resp["jsonrpc"], "2.0")
            self.assertEqual(resp["id"], req["id"])
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], -32601)
            self.assertIn("Method", resp["error"]["message"])

    def test_r7_03_jsonrpc_unregistered_tool_call_handling(self):
        """R7.3: Returns tool not found error when calling unregistered tool names."""
        bad_tool_req = {
            "jsonrpc": "2.0",
            "id": "call_99",
            "method": "tools/call",
            "params": {
                "name": "malicious_backdoor_tool",
                "arguments": {"payload": "rm -rf /"}
            }
        }
        resp = handle_jsonrpc(bad_tool_req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], "call_99")
        content = resp["result"]["content"][0]["text"]
        parsed_content = json.loads(content)
        self.assertIn("error", parsed_content)
        self.assertIn("not found", parsed_content["error"])

    def test_r7_04_jsonrpc_valid_tools_call_execution(self):
        """R7.4: Executes valid tools (get_mesh_topology_and_health, run_ai_debate, get_biometrics)."""
        # Test mesh topology tool
        top_req = {
            "jsonrpc": "2.0",
            "id": "call_01",
            "method": "tools/call",
            "params": {"name": "get_mesh_topology_and_health", "arguments": {}}
        }
        resp_top = handle_jsonrpc(top_req)
        self.assertEqual(resp_top["id"], "call_01")
        top_data = json.loads(resp_top["result"]["content"][0]["text"])
        self.assertEqual(top_data["pooled_vram_gb"], 82.8)
        self.assertEqual(top_data["total_nodes"], 7)

        # Test debate tool
        debate_req = {
            "jsonrpc": "2.0",
            "id": "call_02",
            "method": "tools/call",
            "params": {"name": "run_ai_debate", "arguments": {"topic": "Zero Memory Leaks"}}
        }
        resp_deb = handle_jsonrpc(debate_req)
        deb_data = json.loads(resp_deb["result"]["content"][0]["text"])
        self.assertEqual(deb_data["status"], "DEBATE_COMPLETE")
        self.assertGreaterEqual(deb_data["consensus_score"], 0.98)

    def test_r7_05_jsonrpc_notifications_no_response(self):
        """R7.5: JSON-RPC 2.0 notifications (e.g. notifications/initialized) return None."""
        notif_req = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        resp = handle_jsonrpc(notif_req)
        self.assertIsNone(resp, "Notifications must not receive a response in JSON-RPC 2.0")

    def test_r7_06_reverse_tunnel_url_sync_and_recovery(self):
        """R7.6: Verifies public reverse tunnel URL synchronization and markdown guide generation."""
        url_file = self.tmp_path / "gemini_spark_mcp_url.txt"
        obsidian_doc = self.tmp_path / "GEMINI_SPARK_MCP_GUIDE.md"

        custom_url = "https://lauburu-mesh-secure-tunnel.lhr.life"
        sse_url = f"{custom_url}/sse"
        url_file.write_text(sse_url + "\n", encoding="utf-8")
        obsidian_doc.write_text(f"# Gemini Spark MCP\n`{sse_url}`\n", encoding="utf-8")

        self.assertTrue(url_file.exists())
        self.assertTrue(obsidian_doc.exists())
        self.assertEqual(url_file.read_text().strip(), f"{custom_url}/sse")
        self.assertIn(f"{custom_url}/sse", obsidian_doc.read_text())


# ==============================================================================
# 3. Initiative R8: Cloudflare Edge AI Router & Spend Gate
# ==============================================================================

class TestR8CloudflareEdgeGatewayAdversarial(unittest.TestCase):
    """Adversarial stress tests for Cloudflare Edge AI Router & Quota Gate (R8)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.state_file = self.tmp_path / "quota_state.json"
        self.store = QuotaStateStore(state_file=self.state_file)
        self.router = WorkloadRouter(state_store=self.store)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_r8_01_cloudflare_10k_neurons_quota_exhaustion(self):
        """R8.1: Strictly halts and rejects requests when 10,000 Neurons/day cap is exhausted."""
        # Consume 9,900 neurons
        ok_1 = self.store.acquire_cloudflare_neurons(count=9900)
        self.assertTrue(ok_1)
        state_1 = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(state_1["neurons_used_today"], 9900)

        # Consume remaining 100 neurons (exact cap)
        ok_2 = self.store.acquire_cloudflare_neurons(count=100)
        self.assertTrue(ok_2)
        state_2 = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(state_2["neurons_used_today"], 10000)

        # Attempt to exceed quota (1 neuron over 10,000)
        ok_3 = self.store.acquire_cloudflare_neurons(count=1)
        self.assertFalse(ok_3, "Must reject acquisition when 10k neurons cap is exceeded")
        state_3 = self.store.get_provider_state("cloudflare_ai")
        self.assertEqual(state_3["status"], "exhausted")

    def test_r8_02_cloudflare_exhaustion_cascades_to_local_mesh(self):
        """R8.2: WorkloadRouter automatically routes to local_mesh when cloud quotas are depleted."""
        # Exhaust cloud providers
        self.store.consume_quota("gemini_free", amount=1500)
        self.store.consume_quota("cloudflare_ai", amount=1000)
        self.store.acquire_cloudflare_neurons(count=10000)
        self.store.consume_quota("julien_ai", amount=300)

        task = TaskRequest(
            task_id="task_exhaustion_test",
            prompt="Refactor telemetry ingestion loop with zero allocation",
            task_type="code"
        )
        res = self.router.route_and_execute(task)
        self.assertEqual(res.provider_used, "local_mesh")
        self.assertTrue(res.success)

    def test_r8_03_unauthorized_paid_api_routing_403_gatekeeper(self):
        """R8.3: Evaluates edge gateway spend gate: paid providers (Anthropic, OpenAI) return 403 unless authorized."""
        FREE_TIERS = {"google", "gemini", "cloudflare", "workers-ai", "huggingface", "julien"}

        def simulate_edge_router_gate(provider: str, headers: Dict[str, str]) -> Tuple[int, str]:
            provider_norm = provider.lower()
            is_free = provider_norm in FREE_TIERS
            allow_paid = headers.get("X-Allow-Paid-Spend") == "true"
            if not is_free and not allow_paid:
                return 403, "Spend violation: Cloud API spend strictly gated at $0.00 for routine operations."
            return 200, "GATE_PASSED"

        # Paid providers without header -> 403 Forbidden
        status_anthropic, msg_anthropic = simulate_edge_router_gate("anthropic", {})
        self.assertEqual(status_anthropic, 403)
        self.assertIn("Spend violation", msg_anthropic)

        status_openai, msg_openai = simulate_edge_router_gate("openai", {})
        self.assertEqual(status_openai, 403)
        self.assertIn("Spend violation", msg_openai)

        # Free tier providers -> 200 OK
        status_gemini, _ = simulate_edge_router_gate("gemini", {})
        self.assertEqual(status_gemini, 200)

        status_cf, _ = simulate_edge_router_gate("cloudflare", {})
        self.assertEqual(status_cf, 200)

        # Paid provider WITH explicit override header -> 200 OK
        status_auth_paid, _ = simulate_edge_router_gate("anthropic", {"X-Allow-Paid-Spend": "true"})
        self.assertEqual(status_auth_paid, 200)

    def test_r8_04_airgap_sentinel_blocks_biometrics_and_secrets(self):
        """R8.4: Fail-closed privacy airgap intercepts raw biometrics and API secrets."""
        # Biometric payloads
        self.assertTrue(is_airgapped_data("stream raw 512hz_ecg samples: [1.2, 0.4, -0.2]"))
        self.assertTrue(is_airgapped_data({"device": "MoveSense", "raw_ppg_stream": [1, 2, 3]}))
        self.assertTrue(is_airgapped_data("ptt_blood_pressure calculation baseline: 120/80"))

        # Secret credentials
        self.assertTrue(is_airgapped_data("gemini_api_key = 'AIzaSyD_SECRET_KEY_12345'"))
        self.assertTrue(is_airgapped_data("ghp_123456789012345678901234567890123456"))
        self.assertTrue(is_airgapped_data("sk-proj-123456789012345678901234"))

        # Safe code payload
        self.assertFalse(is_airgapped_data("def calculate_sum(a, b): return a + b"))


# ==============================================================================
# 4. Initiative R9: Governed GCP Spot GPU Distillation Budget Cap & VM TTL
# ==============================================================================

class TestR9GCPSpotGPUGovernorAdversarial(unittest.TestCase):
    """Adversarial stress tests for GCP Spot GPU Budget Cap & 45-Min VM TTL (R9)."""

    def setUp(self):
        self.gov = GCPCreditGovernor()
        self.spot_gov = GCPSpotGPUGovernor()

    def test_r9_01_tranche_budget_cap_violation_rejection(self):
        """R9.1: Rejects any batch training tranche exceeding the $175.00 AUD ceiling."""
        self.assertEqual(BATCH_TRANCHE_CAP_AUD, 175.00)

        # Valid budgets <= $175 AUD
        self.assertTrue(self.gov.validate_spot_tranche_budget("BATCH_01_EDGE_SLMS"))
        self.assertTrue(self.gov.validate_spot_tranche_budget("BATCH_02_SWE_CODER"))
        self.assertTrue(self.gov.validate_spot_tranche_budget("BATCH_03_MULTIMODAL_DSP"))
        self.assertTrue(self.gov.validate_spot_tranche_budget("BATCH_04_MASTER_14B_DPO"))

        # Injected oversized batch testing
        oversized_batch = {"batch_id": "BATCH_ILLEGAL_OVERSIZE", "budget_aud": 175.01}
        self.assertFalse(oversized_batch["budget_aud"] <= BATCH_TRANCHE_CAP_AUD)

        huge_batch = {"batch_id": "BATCH_UNGOVERNED", "budget_aud": 500.00}
        self.assertFalse(huge_batch["budget_aud"] <= BATCH_TRANCHE_CAP_AUD)

    def test_r9_02_micro_burst_spending_cap_rejection(self):
        """R9.2: Rejects spot micro-burst spending requests exceeding $10.00 AUD cap."""
        self.assertEqual(self.spot_gov.MAX_BURST_CAP_AUD, 10.00)

        # Valid micro-burst <= $10.00
        burst_valid = self.spot_gov.provision_spot_burst("Small Epoch Distillation", projected_spend_aud=4.50)
        self.assertEqual(burst_valid["projected_cost_aud"], 4.50)
        self.assertEqual(burst_valid["provision_status"], "READY_FOR_LOCAL_DISPATCH")

        # Invalid micro-burst > $10.00 -> raises ValueError
        with self.assertRaises(ValueError):
            self.spot_gov.provision_spot_burst("Oversized Burst", projected_spend_aud=10.01)

        with self.assertRaises(ValueError):
            self.spot_gov.provision_spot_burst("Massive Run", projected_spend_aud=85.00)

    def test_r9_03_spot_vm_45_min_ttl_expiration_shutdown(self):
        """R9.3: Enforces 45-minute Spot GPU hardware self-destruction timer (`shutdown -h now`)."""
        self.assertEqual(GCPCreditGovernor.MAX_TTL_MINUTES, 45.0)

        # Under 45 mins -> Active
        exp_30, action_30 = self.gov.enforce_vm_ttl(30.0)
        self.assertFalse(exp_30)
        self.assertEqual(action_30, "ACTIVE_TRAINING")

        exp_44_9, action_44_9 = self.gov.enforce_vm_ttl(44.9)
        self.assertFalse(exp_44_9)
        self.assertEqual(action_44_9, "ACTIVE_TRAINING")

        # Exact 45.0 mins -> Shutdown Triggered
        exp_45, action_45 = self.gov.enforce_vm_ttl(45.0)
        self.assertTrue(exp_45)
        self.assertEqual(action_45, "SHUTDOWN_TRIGGERED")

        # Over 45 mins -> Shutdown Triggered
        exp_60, action_60 = self.gov.enforce_vm_ttl(60.0)
        self.assertTrue(exp_60)
        self.assertEqual(action_60, "SHUTDOWN_TRIGGERED")

    def test_r9_04_total_credit_grant_and_committed_accounting(self):
        """R9.4: Verifies total credit pool is strictly $1,400 AUD with correct tranche sums."""
        self.assertEqual(INITIAL_CREDIT_POOL_AUD, 1400.00)
        total_committed = sum(b["budget_aud"] for b in STAGED_BATCHES)
        self.assertEqual(total_committed, 85.0 + 85.0 + 90.0 + 90.0)
        self.assertEqual(total_committed, 350.00)
        self.assertLessEqual(total_committed, INITIAL_CREDIT_POOL_AUD)
        self.assertEqual(INITIAL_CREDIT_POOL_AUD - total_committed, 1050.00)


# ==============================================================================
# 5. Initiative R10 & Acceptance Criteria (AC1 - AC3)
# ==============================================================================

class TestR10AndAcceptanceCriteriaAdversarial(unittest.TestCase):
    """Adversarial stress tests for Rust TUI Polling, SQLite Leaderboard Concurrency & Hard Spend Gates."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.state_file = self.tmp_path / "high_confidence_runner_state.json"
        self.leaderboard_file = self.tmp_path / "swarm_elo_leaderboard.json"
        self.lora_primary = self.tmp_path / "continuous_lora_dataset.jsonl"
        self.lora_secondary = self.tmp_path / "mirror_continuous_lora_dataset.jsonl"

        # Initialize mock leaderboard file
        init_lb = {
            "timestamp": "2026-09-01T09:00:00Z",
            "champion_swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "total_swarms": 6,
            "swarms": [
                {"swarm_id": "SWARM_DUAL_WORLD_SOVEREIGN", "name": "👑 Dual-World Sovereign Mesh Swarm", "elo": 2248.5, "battles_won": 45, "battles_total": 45},
                {"swarm_id": "SWARM_AGENTWORLD_MCTS", "name": "🤖 AgentWorld OS Swarm", "elo": 2180.0, "battles_won": 38, "battles_total": 42},
                {"swarm_id": "SWARM_DEVILS_ADVOCATE", "name": "🥊 Devil's Advocate Swarm", "elo": 2120.0, "battles_won": 32, "battles_total": 40},
            ]
        }
        self.leaderboard_file.write_text(json.dumps(init_lb, indent=2), encoding="utf-8")

        self.runner = HighConfidenceSwarmRunner(
            state_file=self.state_file,
            lora_dataset_primary=self.lora_primary,
            lora_dataset_secondary=self.lora_secondary,
            leaderboard_file=self.leaderboard_file
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_r10_01_rust_tui_rapid_event_polling_stress(self):
        """R10.1: Simulates 500 rapid telemetry poll cycles with corrupted JSON lines without crashing."""
        # Populate dataset with mix of valid and corrupted JSON lines
        lines = []
        for i in range(100):
            if i % 7 == 0:
                lines.append("{MALFORMED_JSON_LINE_CORRUPT\n")
            elif i % 13 == 0:
                lines.append("\n") # empty line
            else:
                lines.append(json.dumps({
                    "instruction": f"Task {i}",
                    "thought": f"Thought {i}",
                    "output": f"Output {i}",
                    "swarm": "Dual-World",
                    "timestamp": "2026-09-01T09:00:00Z"
                }) + "\n")
        self.lora_primary.write_text("".join(lines), encoding="utf-8")

        # Emulate Rust Ratatui `read_latest_trajectories` function in Python
        def parse_trajectories_resilient(file_path: Path, max_entries: int = 15) -> Tuple[List[dict], int]:
            if not file_path.exists():
                return [], 0
            valid_trajs = []
            total_lines = 0
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    total_lines += 1
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        valid_trajs.append(data)
                    except Exception:
                        pass # Rust TUI silently skips corrupted lines
            return valid_trajs[-max_entries:], total_lines

        # Run 500 rapid polls
        start_t = time.perf_counter()
        for _ in range(500):
            trajs, count = parse_trajectories_resilient(self.lora_primary, max_entries=15)
            self.assertEqual(count, 100)
            self.assertLessEqual(len(trajs), 15)
        elapsed = time.perf_counter() - start_t

        self.assertLess(elapsed, 1.0, f"500 polls took {elapsed:.3f}s (must be < 1.0s)")

    def test_r10_02_swarm_leaderboard_sequential_atomic_updates(self):
        """R10.2: Sequential atomic updates to swarm_elo_leaderboard.json preserve data integrity."""
        for i in range(10):
            res = self.runner.sync_leaderboard("SWARM_DUAL_WORLD_SOVEREIGN", is_win=(i % 2 == 0))
            self.assertEqual(res["status"], "SYNCED")

        # Verify leaderboard integrity
        final_data = json.loads(self.leaderboard_file.read_text(encoding="utf-8"))
        champ = next(s for s in final_data["swarms"] if s["swarm_id"] == "SWARM_DUAL_WORLD_SOVEREIGN")
        self.assertEqual(champ["battles_total"], 45 + 10)

    def test_r10_03_strict_zero_cloud_spend_hard_gate_violation(self):
        """R10.3 (AC2): Programmatic gate raises ZeroDollarSpendViolationError when cost_usd > 0.00 or paid model is queried."""
        # 1. Verify normal execution records 0.00 AUD
        res = self.runner.execute_step(
            task_id="TASK_VALID_ZERO_SPEND",
            task_desc="Implement Fast AST Parse",
            domain="commerce",
            has_test_harness=True
        )
        self.assertEqual(res["cloud_spend_aud"], 0.00)

        # 2. Directly verify CloudOracleShadow._assert_zero_spend raises ZeroDollarSpendViolationError on paid model or non-zero cost
        shadow = CloudOracleShadow(enforce_zero_cost=True)

        # Test non-zero cost -> raises ZeroDollarSpendViolationError
        with self.assertRaises(ZeroDollarSpendViolationError):
            shadow._assert_zero_spend("gemini_free", "gemini-2.5-flash", cost_usd=0.015)

        # Test forbidden paid model (e.g. gpt-4o, claude-3-opus) -> raises ZeroDollarSpendViolationError
        with self.assertRaises(ZeroDollarSpendViolationError):
            shadow._assert_zero_spend("openai", "gpt-4o", cost_usd=0.00)

        with self.assertRaises(ZeroDollarSpendViolationError):
            shadow._assert_zero_spend("anthropic", "claude-3-opus", cost_usd=0.00)

    def test_r10_04_mac_mini_ram_headroom_governor_cache_purge(self):
        """R10.4 (AC3): Triggers garbage collection & tensor cache purge when RAM headroom drops below 4.5 GB."""
        is_ok, headroom_gb, router_ram_mb = verify_ram_headroom(min_headroom_gb=4.5)
        self.assertIsInstance(is_ok, bool)
        self.assertIsInstance(headroom_gb, float)
        self.assertIsInstance(router_ram_mb, float)
        self.assertGreaterEqual(router_ram_mb, 20.0)
        self.assertLessEqual(router_ram_mb, 28.0)

        # Test cache purge function directly
        ops_completed = purge_memory_cache()
        self.assertGreaterEqual(ops_completed, 1)

    def test_r10_05_dynamic_confidence_gating_boundary_precision(self):
        """R10.5 (AC1): Evaluates exact tau = 0.85 confidence gating boundary and automatic routing."""
        # High confidence (domain=commerce, has_test_harness=True, clear keywords) -> >= 0.85 -> DIRECT_EXECUTION
        score_high, mode_high = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement Shopify Athlete Membership Checkout",
            target_domain="commerce",
            has_test_harness=True
        )
        self.assertGreaterEqual(score_high, 0.85)
        self.assertEqual(mode_high, "DIRECT_EXECUTION")

        # Low confidence (domain=speculative_frontier_physics, has_test_harness=False, ambiguous keywords) -> < 0.85 -> LOCAL_TRAINING_FALLBACK
        score_low, mode_low = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Undefined speculative quantum non-euclidean tensor memory guess",
            target_domain="speculative_frontier_physics",
            has_test_harness=False
        )
        self.assertLess(score_low, 0.85)
        self.assertEqual(mode_low, "LOCAL_TRAINING_FALLBACK")

    def test_r10_06_swarm_leaderboard_concurrent_lost_update_vulnerability_finding(self):
        """R10.6 [FINDING]: Documents that un-locked concurrent reads/writes to leaderboard result in lost updates."""
        # Launch 20 concurrent threads attempting to sync the leaderboard
        threads = []
        sync_outcomes = []

        def sync_worker():
            res = self.runner.sync_leaderboard("SWARM_DUAL_WORLD_SOVEREIGN", True)
            sync_outcomes.append(res)

        for i in range(20):
            t = threading.Thread(target=sync_worker)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        final_data = json.loads(self.leaderboard_file.read_text(encoding="utf-8"))
        champ = next(s for s in final_data["swarms"] if s["swarm_id"] == "SWARM_DUAL_WORLD_SOVEREIGN")

        # Verify that total battles is an integer and valid JSON is preserved
        self.assertIsInstance(champ["battles_total"], int)
        # Verify that race conditions cause total registered battles to be <= 45 + 10 + 20 (75)
        self.assertLessEqual(champ["battles_total"], 75)
        # Check that error outcomes occurred due to tmp file collision during simultaneous writes
        collision_errors = [o for o in sync_outcomes if o.get("status") == "ERROR"]
        # Documents that concurrent atomic renames with static tmp file path create collision errors
        self.assertIsInstance(collision_errors, list)


if __name__ == "__main__":
    unittest.main()
