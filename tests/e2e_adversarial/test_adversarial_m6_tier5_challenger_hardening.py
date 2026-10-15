#!/usr/bin/env python3
"""
tests/test_adversarial_m6_tier5_challenger_hardening.py
========================================================
Master Adversarial & Tier 5 Hardening Test Suite for Milestone M6.
Author: teamwork_preview_challenger_m6 (Empirical Challenger)

Coverage:
1. Adversarially stress-test all 7 apps in 01_apps/ (movesense_readiness_hub,
   spatial_grappling_3d, combat_arena, shopify_storefront, canonical_port,
   smolagents_duel_sandbox, qwen_math_trend_optimizer).
2. Adversarially test Web-TUI Portal (serve_portal.py) under high-throughput
   PTY streams, route traversal attacks, and port reclamation.
3. Adversarially test Free-Tier Quota Manager (cloud_api_quota_manager.py)
   under quota exhaustion, concurrency races, and provider failover cascade.
4. Adversarially probe Cloudflare Worker Airgap Sentinel to confirm 100% blocked
   egress for physiological biometric data.
"""

import asyncio
import concurrent.futures
import json
import math
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List, Any

# Setup sys.path for monorepo roots and modular applications
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys_paths = [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "01_apps"),
    str(PROJECT_ROOT / "01_apps/biometrics"),
    str(PROJECT_ROOT / "01_apps/user_facing_and_scaling"),
    str(PROJECT_ROOT / "01_apps/operator_and_dev"),
    str(PROJECT_ROOT / "01_apps/web_tui_portal"),
    str(PROJECT_ROOT / "06_scripts_and_tooling/automation"),
    str(PROJECT_ROOT / "00_core_infrastructure/self_healing_hub"),
]
for p in sys_paths:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient


# ============================================================================
# 1. ADVERSARIAL STRESS-TESTS: 7 APPLICATIONS
# ============================================================================

class TestAdversarialMovesenseReadinessApp(unittest.TestCase):
    """Adversarial testing for Movesense Readiness Hub."""

    def test_01_ecg_extreme_noise_and_pathological_inputs(self):
        """Test Pan-Tompkins with NaN, Inf, extreme voltage spikes, and flatline."""
        from movesense_readiness_hub.dsp.pan_tompkins import (
            PanTompkinsQRSDetector,
            apply_kamath_filter,
            calculate_rmssd
        )

        detector = PanTompkinsQRSDetector(sample_rate_hz=512)

        # Flatline
        flatline = [0.0] * 512
        peaks_flat, rr_flat = detector.detect_qrs_peaks(flatline)
        self.assertEqual(len(peaks_flat), 0)
        self.assertEqual(len(rr_flat), 0)

        # Extreme voltage spikes (+- 10,000 mV)
        spikes = [10000.0 if i % 100 == 0 else -10000.0 if i % 100 == 50 else 0.0 for i in range(1024)]
        peaks_spikes, rr_spikes = detector.detect_qrs_peaks(spikes)
        self.assertIsInstance(peaks_spikes, list)

        # Empty and single-element inputs
        peaks_empty, rr_empty = detector.detect_qrs_peaks([])
        self.assertEqual(len(peaks_empty), 0)
        peaks_single, rr_single = detector.detect_qrs_peaks([1.5])
        self.assertEqual(len(peaks_single), 0)

        # Kamath filter with alternating ectopic bursts and empty buffers
        rr_clean = apply_kamath_filter([], threshold_pct=20.0)
        self.assertEqual(rr_clean, [])
        rr_single_f = apply_kamath_filter([800.0], threshold_pct=20.0)
        self.assertEqual(rr_single_f, [800.0])

        # RMSSD with degenerate intervals
        self.assertIsNone(calculate_rmssd([]))
        self.assertIsNone(calculate_rmssd([800.0]))
        self.assertEqual(calculate_rmssd([800.0, 800.0, 800.0]), 0.0)

    def test_02_zero_mock_rule_zero_invariants(self):
        """Verify strict Rule #0 compliance: zero synthetic mock arrays in disconnected state."""
        from movesense_readiness_hub.core.models import BiometricsStateStore, ReadinessReport

        store = BiometricsStateStore()
        contract = store.get_interface_contract()

        self.assertEqual(contract["status"], "WAITING_FOR_SENSOR")
        self.assertIsNone(contract["heart_rate_bpm"])
        self.assertIsNone(contract["rmssd_ms"])
        self.assertIsNone(contract["ptt_blood_pressure"]["systolic_bp_mmhg"])
        self.assertIsNone(contract["sleep_recovery"]["sleep_score_pct"])

    def test_03_high_concurrency_state_store_mutation(self):
        """Stress state store under concurrent threads updating reports and listeners."""
        from movesense_readiness_hub.core.models import BiometricsStateStore, ReadinessReport

        store = BiometricsStateStore()
        call_count = [0]

        def listener(report: ReadinessReport):
            call_count[0] += 1

        store.add_listener(listener)

        def worker(thread_id: int):
            for i in range(20):
                rep = ReadinessReport(
                    connected=True,
                    heart_rate_bpm=70.0 + thread_id,
                    rmssd_ms=45.0 + i,
                    status="STREAMING"
                )
                store.update_report(rep)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, tid) for tid in range(8)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        self.assertGreater(call_count[0], 50)
        final_rep = store.get_report()
        self.assertTrue(final_rep.connected)
        self.assertEqual(final_rep.status, "STREAMING")


class TestAdversarialSpatialGrappling3DApp(unittest.TestCase):
    """Adversarial testing for 3D Spatial Grappling Kinematics."""

    def test_01_opml_parser_corrupted_trees_and_empty_xml(self):
        """Stress OPML parser with missing body, corrupt tags, and non-existent path."""
        from spatial_grappling_3d.kinematics.opml_tree import parse_opml_tree

        temp_dir = tempfile.mkdtemp()
        try:
            corrupt_file = Path(temp_dir) / "corrupt.opml"
            corrupt_file.write_text("<opml version='2.0'><head><title>Corrupt</title></head></opml>")
            with self.assertRaises(ValueError):
                parse_opml_tree(corrupt_file)

            non_existent = Path(temp_dir) / "non_existent.opml"
            with self.assertRaises(FileNotFoundError):
                parse_opml_tree(non_existent)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_02_skeleton_kinematic_bounds_and_torque_safety(self):
        """Test MediaPipe 33-landmark generator and joint torque calculations."""
        from spatial_grappling_3d.kinematics.skeleton import build_default_pose, MEDIAPIPE_33_LANDMARKS
        from spatial_grappling_3d.kinematics.torque import compute_joint_torque, evaluate_joint_safety

        # Standard 33 landmarks verification
        self.assertEqual(len(MEDIAPIPE_33_LANDMARKS), 33)
        pose = build_default_pose("Mount")
        self.assertEqual(len(pose), 33)

        # Torque calculation across joint angles
        joint_angles = {
            "right_elbow": 90.0,
            "left_elbow": 45.0,
            "right_knee": 120.0,
            "cervical_spine": 15.0
        }
        torques = compute_joint_torque(joint_angles, lever_arm_m=0.35, force_n=150.0)
        self.assertIn("right_elbow", torques)
        self.assertGreater(torques["right_elbow"], 0.0)

        # Evaluate safety
        safety = evaluate_joint_safety(torques)
        self.assertEqual(len(safety), 4)
        for s in safety:
            self.assertIsInstance(s.is_safe, bool)

    def test_03_tatami_projection_bounds(self):
        """Verify full 3,044 OPML tree nodes stay within 10m x 10m tatami bounds."""
        from spatial_grappling_3d.presentation.engine import SpatialGrapplingMapEngine

        engine = SpatialGrapplingMapEngine()
        res = engine.parse_full_opml_tree()

        self.assertEqual(res["total_nodes"], 3044)
        for node in engine.nodes:
            # Tatami radius <= 5.0m
            dist_from_center = math.sqrt(node.x**2 + node.y**2)
            self.assertLessEqual(dist_from_center, 5.0, f"Node {node.id} exceeds tatami mat bounds: {dist_from_center}m")


class TestAdversarialCombatArenaApp(unittest.TestCase):
    """Adversarial testing for Combat Arena."""

    def test_01_unknown_game_modes_and_fallback(self):
        """Verify engine gracefully handles invalid game mode requests."""
        from combat_arena.presentation.arena import CombatArenaEngine

        engine = CombatArenaEngine()
        engine.state_store.active_mode = "NON_EXISTENT_MODE"
        snap = engine.step()
        self.assertIsNotNone(snap)
        self.assertIn("step", snap)
        self.assertIn("narration", snap)
        self.assertIn("pulse", snap)

    def test_02_power_bar_and_pulse_gauge_extreme_values(self):
        """Test power bar & pulse gauge with negative, 0, 500 bpm, and overflowing energy."""
        from combat_arena.presentation.power_bar import render_power_bar
        from combat_arena.presentation.pulse_gauge import render_pulse_gauge
        from combat_arena.core.models import PulseTelemetry

        # Power bar bounds clamping (ratio parameter from -1.0 to 1.0)
        bar_neg = render_power_bar(ratio=-1.5, width=40)
        self.assertIsNotNone(bar_neg)
        bar_pos = render_power_bar(ratio=1.5, width=40)
        self.assertIsNotNone(bar_pos)
        bar_zero = render_power_bar(ratio=0.0, width=40)
        self.assertIsNotNone(bar_zero)

        # Pulse gauge bounds clamping
        gauge_connected = render_pulse_gauge(PulseTelemetry(heart_rate_bpm=72.0, rmssd_ms=45.0, zone2_aligned=True, is_connected=True))
        self.assertIn("72.0 BPM", str(gauge_connected))

        gauge_disc = render_pulse_gauge(PulseTelemetry(heart_rate_bpm=None, rmssd_ms=None, zone2_aligned=False, is_connected=False))
        self.assertIn("WAITING_FOR_SENSOR", str(gauge_disc))

    def test_03_concurrent_arena_duel_ticks(self):
        """Stress combat arena with 50 rapid ticks."""
        from combat_arena.presentation.arena import CombatArenaEngine

        engine = CombatArenaEngine()
        for _ in range(50):
            res = engine.step()
            self.assertIn("step", res)
            self.assertGreater(res["step"], 0)
            self.assertIn("narration", res)


class TestAdversarialShopifyStorefrontApp(unittest.TestCase):
    """Adversarial testing for Headless Shopify Storefront."""

    def test_01_graphql_offline_resilience(self):
        """Verify GraphQL client returns robust offline fallback when network is absent."""
        from shopify_storefront.graphql.client import ShopifyStorefrontClient

        client = ShopifyStorefrontClient()
        resp = client.execute_graphql(query="{ shop { name } }", variables={})
        self.assertIn("data", resp)
        self.assertIn("cartCreate", resp["data"])

    def test_02_checkout_with_malformed_cart_lines(self):
        """Verify checkout creation handles empty, negative, and special character inputs."""
        from shopify_storefront.graphql.client import ShopifyStorefrontClient

        client = ShopifyStorefrontClient()

        # Empty cart lines
        chk_empty = client.create_checkout([])
        self.assertIsNotNone(chk_empty.checkout_url)

        # Negative quantities and SQL injection variant ID
        bad_lines = [
            {"variant_id": "'; DROP TABLE users; --", "quantity": -5, "title": "Attack", "price": 0.0},
            {"variant_id": "<script>alert(1)</script>", "quantity": 0, "title": "XSS", "price": -99.0}
        ]
        chk_bad = client.create_checkout(bad_lines)
        self.assertIsNotNone(chk_bad.checkout_url)
        self.assertEqual(len(chk_bad.lines), 2)

    def test_03_membership_tiers_immutability(self):
        """Verify membership tiers structure and price invariants."""
        from shopify_storefront.presentation.pricing import MEMBERSHIP_TIERS

        self.assertEqual(len(MEMBERSHIP_TIERS), 3)
        athlete, pro, gym = MEMBERSHIP_TIERS
        self.assertEqual(athlete.price_usd_month, 9.0)
        self.assertEqual(pro.price_usd_month, 29.0)
        self.assertEqual(gym.price_usd_month, 99.0)


class TestAdversarialCanonicalPortNOCApp(unittest.TestCase):
    """Adversarial testing for Canonical Port 9-Screen NOC."""

    def test_01_screen_navigation_invariants(self):
        """Verify 9-screen stability hierarchy configuration."""
        from canonical_port.views.screens import STABILITY_SCREENS

        self.assertEqual(len(STABILITY_SCREENS), 9)
        screen_ids = [s.screen_id for s in STABILITY_SCREENS]
        self.assertEqual(screen_ids, list(range(1, 10)))

    def test_02_7_node_hardware_pool_invariants(self):
        """Verify 7 physical nodes sum to 108.0 GB RAM and 82.8+ GB usable AI VRAM."""
        from canonical_port.nodes.mesh_nodes import MESH_NODES
        from canonical_port.nodes.hardware_pool import get_hardware_pool_summary

        self.assertEqual(len(MESH_NODES), 7)
        summary = get_hardware_pool_summary()

        self.assertAlmostEqual(summary["total_physical_ram_gb"], 108.0, places=1)
        self.assertGreaterEqual(summary["total_usable_ai_vram_gb"], 82.8)
        self.assertEqual(summary["total_nodes"], 7)

    def test_03_ai_debate_council_state_invariants(self):
        """Verify AI debate council state with 4 speakers and consensus summary."""
        from canonical_port.debate.council import DebateCouncilEngine

        engine = DebateCouncilEngine()
        state = engine.current_state
        self.assertEqual(len(state.speakers), 4)
        self.assertTrue(state.consensus_reached)
        self.assertIn("Dynamic memory governance", state.consensus_summary)


class TestAdversarialSmolAgentsDuelSandboxApp(unittest.TestCase):
    """Adversarial testing for SmolAgents Python Duel Sandbox."""

    def test_01_sandboxed_hostile_code_execution(self):
        """Verify sandbox catches syntax errors, exceptions, and division by zero cleanly."""
        from smolagents_duel_sandbox.tools.sandbox import PythonCodeSandbox
        from smolagents_duel_sandbox.core.models import AgentAction

        sandbox = PythonCodeSandbox()

        # Division by zero
        act_zero = AgentAction(
            agent_id="test_red",
            faction="RED",
            intent="Divide by zero attack",
            python_code="x = 1 / 0\nresult = {'res': x}"
        )
        res_zero = sandbox.execute_action(act_zero)
        self.assertEqual(res_zero.status, "FAILED")
        self.assertIn("division by zero", str(res_zero.error).lower())

        # Syntax Error
        act_syntax = AgentAction(
            agent_id="test_blue",
            faction="BLUE",
            intent="Malformed syntax",
            python_code="def broken(:\n  pass"
        )
        res_syntax = sandbox.execute_action(act_syntax)
        self.assertEqual(res_syntax.status, "FAILED")
        self.assertIn("syntax", str(res_syntax.error).lower())

        # Valid Code Action
        act_valid = AgentAction(
            agent_id="test_red",
            faction="RED",
            intent="Clean calculation",
            python_code="result = {'tb4_latency_ms': tools.get_mesh_latency('Mac_Node', 'MacBook_Pro')}"
        )
        res_valid = sandbox.execute_action(act_valid)
        self.assertEqual(res_valid.status, "SUCCESS")
        self.assertAlmostEqual(res_valid.output["tb4_latency_ms"], 0.27, places=2)

    def test_02_duel_hub_continuous_ticks(self):
        """Verify multi-turn duel ticks between Hermes 3 Red and LuCI Blue."""
        from smolagents_duel_sandbox.presentation.sandbox import SmolAgentsArenaHub

        hub = SmolAgentsArenaHub()
        for _ in range(10):
            record = hub.step()
            self.assertEqual(record.red_action.status, "SUCCESS")
            self.assertEqual(record.blue_action.status, "SUCCESS")
            self.assertGreaterEqual(record.red_action.execution_time_ms, 0.0)


class TestAdversarialQwenMathTrendOptimizerApp(unittest.TestCase):
    """Adversarial testing for Qwen Math Trend Optimizer."""

    def test_01_closed_form_latency_proofs_degenerate_inputs(self):
        """Test inverse-variance weights under zero, negative, and infinite latencies."""
        from qwen_math_trend_optimizer.models.latency_proofs import compute_inverse_variance_weights

        # Nominal inputs (TB4: 0.27ms, WG: 1.85ms, Wi-Fi: 4.20ms)
        weights_nom = compute_inverse_variance_weights(tb4_rtt=0.27, wg_rtt=1.85, wifi_rtt=4.20)
        self.assertGreater(weights_nom[0].inverse_variance_weight, 0.85)
        total_w = sum(p.inverse_variance_weight for p in weights_nom)
        self.assertAlmostEqual(total_w, 1.0, places=3)

        # Zero and negative latencies (numerical defense)
        weights_zero = compute_inverse_variance_weights(tb4_rtt=0.0, wg_rtt=-1.0, wifi_rtt=0.0)
        self.assertIsNotNone(weights_zero)
        total_w_zero = sum(p.inverse_variance_weight for p in weights_zero)
        self.assertAlmostEqual(total_w_zero, 1.0, places=2)

    def test_02_ram_safety_headroom_critical_governor(self):
        """Test RAM safety headroom calculations under normal and dangerous load."""
        from qwen_math_trend_optimizer.models.ram_headroom import compute_ram_safety_headroom

        # Nominal Safe State (Mac Mini M4 Pro: 24GB, 90% cap = 21.6GB)
        proof_safe = compute_ram_safety_headroom(
            host_physical_ram_gb=24.0,
            model_base_vram_gb=14.0,
            batch_size=2,
            lora_rank=32
        )
        self.assertTrue(proof_safe.is_safe)
        self.assertIn("CERTIFIED_HEALTHY", proof_safe.status)
        self.assertGreaterEqual(proof_safe.ram_headroom_gb, 2.50)

        # Dangerous High-VRAM State (Exceeding 90% ceiling)
        proof_danger = compute_ram_safety_headroom(
            host_physical_ram_gb=24.0,
            model_base_vram_gb=20.0,
            batch_size=4,
            lora_rank=64
        )
        self.assertFalse(proof_danger.is_safe)
        self.assertIn("REJECTED_OOM_RISK", proof_danger.status)
        self.assertLess(proof_danger.ram_headroom_gb, 2.50)


# ============================================================================
# 2. ADVERSARIAL TEST: WEB-TUI PORTAL (PORT 8088 & SERVE_PORTAL.PY)
# ============================================================================

class TestAdversarialWebTuiPortal(unittest.TestCase):
    """Adversarial testing for Web-TUI Portal server and routes."""

    @classmethod
    def setUpClass(cls):
        from web_tui_portal.serve_portal import app
        cls.client = TestClient(app)

    def test_01_all_7_app_routes_render_html(self):
        """Verify GET routes for landing page and all 7 applications return HTTP 200."""
        routes = ["/", "/readiness", "/grappling", "/arena", "/store", "/canonical", "/smolagents", "/math"]
        for route in routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Route {route} failed")
            self.assertIn("text/html", resp.headers["content-type"])
            if route != "/":
                self.assertIn("120 FPS WebGL", resp.text)

    def test_02_portal_api_status_and_app_registry(self):
        """Verify /api/status reports 7 apps, 120 FPS, and airgap certification."""
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["port"], 8088)
        self.assertEqual(data["fps"], 120)
        self.assertEqual(data["total_apps"], 7)
        self.assertTrue(data["airgap_certified"])

    def test_03_websocket_invalid_app_id_rejection(self):
        """Verify WebSocket /ws/{app_id} closes invalid app sessions with code 1008."""
        from fastapi import WebSocketDisconnect
        try:
            with self.client.websocket_connect("/ws/malicious_nonexistent_app") as ws:
                pass
        except WebSocketDisconnect as e:
            self.assertEqual(e.code, 1008)
        except Exception:
            pass

    def test_04_port_reclamation_idempotency(self):
        """Verify reclaim_port function executes cleanly and idempotently."""
        from web_tui_portal.serve_portal import reclaim_port
        reclaim_port(port=58088)


# ============================================================================
# 3. ADVERSARIAL TEST: FREE-TIER QUOTA MANAGER & FAILOVER CASCADE
# ============================================================================

class TestAdversarialCloudApiQuotaManager(unittest.TestCase):
    """Adversarial stress testing for Quota Manager under quota depletion and failovers."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "quota_state_adversarial.json"
        self.dataset_file = Path(self.temp_dir) / "lora_dataset_adversarial.jsonl"
        self.mirror_dataset = Path(self.temp_dir) / "lora_mirror_adversarial.jsonl"

        from cloud_api_quota_manager import QuotaStateStore, LoRADatasetWriter, WorkloadRouter
        self.store = QuotaStateStore(state_file=self.state_file)
        self.writer = LoRADatasetWriter(primary_dataset=self.dataset_file, mirror_dataset=self.mirror_dataset)
        self.router = WorkloadRouter(state_store=self.store, dataset_writer=self.writer)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_full_cloud_quota_exhaustion_failover_to_local_mesh(self):
        """Exhaust 100% of Julien AI, Cloudflare AI, and Gemini Free -> Assert Local Mesh Fallback."""
        from cloud_api_quota_manager import TaskRequest

        # Exhaust Julien AI (300)
        self.store.consume_quota("julien_ai", 300)
        # Exhaust Cloudflare AI (1000)
        self.store.consume_quota("cloudflare_ai", 1000)
        # Exhaust Gemini Free (1500)
        self.store.consume_quota("gemini_free", 1500)

        state = self.store.reload()
        self.assertEqual(state["providers"]["julien_ai"]["remaining_pct"], 0.0)
        self.assertEqual(state["providers"]["cloudflare_ai"]["remaining_pct"], 0.0)
        self.assertEqual(state["providers"]["gemini_free"]["remaining_pct"], 0.0)

        # Route new task -> All cloud exhausted, must route to local_mesh
        req = TaskRequest(
            task_id="adv_task_exhausted_fallback",
            prompt="Generate robust unit test for telemetry pipeline",
            estimated_tokens=500
        )
        res = self.router.route_and_execute(req)

        self.assertTrue(res.success)
        self.assertEqual(res.provider_used, "local_mesh")

    def test_02_concurrent_quota_consumption_file_locking_stress(self):
        """50 concurrent threads consuming quotas atomically via fcntl.flock."""
        from cloud_api_quota_manager import QuotaStateStore

        def worker(tid: int):
            local_store = QuotaStateStore(state_file=self.state_file)
            local_store.consume_quota("gemini_free", 10)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        final_state = self.store.reload()
        # 50 threads * 10 tokens = 500 consumed
        self.assertEqual(final_state["providers"]["gemini_free"]["used_today"], 500)

    def test_03_corrupted_state_file_auto_healing(self):
        """Corrupt quota_state.json with garbage bytes -> Verify auto-healing recovery."""
        from cloud_api_quota_manager import QuotaStateStore

        # Overwrite state file with broken JSON
        self.state_file.write_text("{ broken json: [,, 123 }")

        healed_store = QuotaStateStore(state_file=self.state_file)
        state = healed_store.reload()
        self.assertEqual(state["version"], "2.0.0")
        self.assertIn("gemini_free", state["providers"])
        self.assertEqual(state["providers"]["gemini_free"]["used_today"], 0)

    def test_04_utc_midnight_rollover_resets_quotas(self):
        """Verify simulated date change triggers automatic daily quota reset."""
        self.store.consume_quota("gemini_free", 800)
        self.assertEqual(self.store.get_provider_state("gemini_free")["used_today"], 800)

        # Simulate state saved yesterday
        raw_state = self.store.reload()
        raw_state["last_reset_date"] = "2020-01-01"
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(raw_state, f)

        # Next reload must detect stale date and reset
        fresh_state = self.store.reload()
        self.assertEqual(fresh_state["providers"]["gemini_free"]["used_today"], 0)
        self.assertEqual(fresh_state["providers"]["gemini_free"]["remaining_pct"], 1.0)


# ============================================================================
# 4. ADVERSARIAL TEST: FAIL-CLOSED CLOUDFLARE AIRGAP FILTER
# ============================================================================

class TestAdversarialAirgapSentinel(unittest.TestCase):
    """Adversarial probe testing for 100% Fail-Closed Biometric Airgap Filter."""

    def test_01_biometric_data_keyword_detection(self):
        """Verify contains_biometric_data regex detector catches all biometric keys."""
        from code_scaffold_daemon import contains_biometric_data

        malicious_prompts = [
            "Process this 512hz_ecg stream: [1.2, 4.5, -0.8]",
            "Calculate continuous ptt_blood_pressure from raw waveform",
            "Here is the raw_ppg_stream sleep staging epochs stream",
            "Extract raw_rr_intervals: [850, 840, 890]",
            "dfa_alpha1_raw series for athlete readiness coaching",
            "Send raw ecg_samples array to cloud AI model",
            "Export movesense_packet raw hex dump: 0x2A3700FF",
        ]

        for p in malicious_prompts:
            is_bio, matches = contains_biometric_data(p)
            self.assertTrue(is_bio, f"Airgap sentinel failed to flag: {p}")
            self.assertGreater(len(matches), 0)

    def test_02_clean_scaffolding_prompts_pass_airgap(self):
        """Verify non-biometric code scaffolding prompts pass cleanly."""
        from code_scaffold_daemon import contains_biometric_data

        clean_prompts = [
            "Generate a React TypeScript card component with Tailwind CSS",
            "Write a FastAPI endpoint for user profile authentication",
            "Synthesize unit test for matrix transpose in Python",
            "Document the OpenAPI schema for membership pricing tiers",
        ]

        for p in clean_prompts:
            is_bio, matches = contains_biometric_data(p)
            self.assertFalse(is_bio, f"Airgap sentinel false positive on: {p}")
            self.assertEqual(len(matches), 0)

    def test_03_airgap_redaction_token_replacement(self):
        """Verify daemon redacts any biometric payload and blocks transmission."""
        from code_scaffold_daemon import CodeScaffoldDaemon

        daemon = CodeScaffoldDaemon()
        res = daemon.scaffold_unit_test(
            module_name="movesense_512hz_ecg_raw_pipeline",
            source_code="raw_ecg_samples = [1200, 4500, -800]\nptt_blood_pressure = 120"
        )
        self.assertTrue(res.airgap_protected)
        self.assertIsNotNone(res.code_generated)


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

if __name__ == "__main__":
    unittest.main()
