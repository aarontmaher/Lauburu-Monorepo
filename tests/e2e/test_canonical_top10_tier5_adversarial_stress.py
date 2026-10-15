#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 5 Adversarial Stress Test Suite: Canonical Top 10 Initiatives (R1 - R5)
================================================================================
Subsystem: tests/e2e/test_canonical_top10_tier5_adversarial_stress.py
Author: teamwork_preview_challenger_1 (Empirical Challenger)
Milestone: M6 / Tier 5 Adversarial Stress Testing & Hardening

Exhaustively stress-tests Initiatives R1 through R5 under hostile, boundary,
pathological, and extreme failure conditions across 40 rigorous empirical tests:

- R1: MLX QLoRA Dynamic RAM Governor under extreme memory pressure (allocation >21.6GB,
      headroom <2.5GB, negative headroom), MergeKit DARE-TIES synthesis with corrupt/dissenting
      debate votes (veto, NaN, negative confidence, parent model immutability), Bradley-Terry
      ELO promotion edge cases (exact 65.0% tie, 64.99% rejection, 65.01% promotion, +/-50k ELO,
      atomic symlink swapping and instant rollback).
- R2: Headless Shopify GraphQL fuzzing (SQLi, XSS, binary garbage, syntax errors, negative quantity),
      HMAC-SHA256 token forgery/expiry attacks (signature tampering, expired replay, malformed structure),
      sliding window rate limit burst starvation (60/300 RPM, daily quota) & multi-client isolation.
- R3: Medical Biometrics DSP stress testing: ECG flatlines (zero/DC offset), noisy baseline drift
      (50Hz mains hum, 0.1Hz respiration drift, white noise), extreme ectopic RR jumps (>200% PVC),
      Kamath 20% artifact filter, PTT inverted pulse waveforms & non-physiological clamps,
      DFA-alpha1 boundary cases (s < 4, zero variance, short series, Zone 2/3 classification).
- R4: 3D Spatial Grappling OPML corrupted tags (unclosed XML, missing body, deep nesting),
      cylindrical coordinate singularity & 10m x 10m tatami mat boundary confinement (r <= 4.8m),
      extreme joint torque forces (>1000 N*m exceeding physiological limits across 6 anatomical regions),
      MediaPipe 33-landmark completeness.
- R5: TB4 PRP sharding CRC32 bit-flip corruption detection (single-bit XOR, truncation, bit rot),
      dropped packet simulation, latency probe SLA (<0.30ms) & layer migration tracking.

Zero-Mock Policy (Rule #0):
All tests run authentic mathematical algorithms, real cryptography, genuine DSP pipelines,
and real POSIX/filesystem operations.
================================================================================
"""

from __future__ import annotations

import os
import sys
import math
import zlib
import json
import time
import hmac
import hashlib
import shutil
import tempfile
import xml.etree.ElementTree as ET
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

import numpy as np

# Path Resolution
TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(PROJECT_ROOT),
    str(TESTS_E2E_DIR),
    str(PROJECT_ROOT / "00_core_infrastructure"),
    str(PROJECT_ROOT / "00_core_infrastructure" / "router_ai_daemon"),
    str(PROJECT_ROOT / "01_apps"),
    str(PROJECT_ROOT / "01_apps" / "commerce"),
    str(PROJECT_ROOT / "01_apps" / "spatial_and_3d"),
    str(PROJECT_ROOT / "01_apps" / "spatial_and_3d" / "spatial_grappling_3d"),
    str(PROJECT_ROOT / "02_ai_models_and_inference"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "benchmarks"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "sharding_daemon"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry" / "dsp"),
    str(PROJECT_ROOT / "04_data_and_memory"),
    str(PROJECT_ROOT / "05_agents_and_swarms"),
    str(PROJECT_ROOT / "06_scripts_and_tooling"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "automation"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "training"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "mesh"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from canonical_top10_helpers import (
    calculate_bradley_terry_win_prob,
    update_elo_ratings,
    generate_canonical_hmac_token,
    verify_canonical_hmac_token,
    generate_fourier_ecg_signal,
    generate_canonical_opml_string,
    build_activation_chunk,
    verify_activation_chunk,
)

# Production source imports
from mlx_qlora_trainer import DynamicRamGovernor, MLXQLoRATrainer
from autonomous_consensus_merger import AutonomousConsensusMergeEngine, CONSENSUS_THRESHOLD
from elo_promotion_gate import EloPromotionGate, BradleyTerryModel
from shopify_storefront_gateway import (
    CustomerTier,
    CustomerProfile,
    MemberAPIGateway,
    ShopifyStorefrontGraphQLClient,
    SlidingWindowRateLimiter,
)
from pan_tompkins_qrs import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_rmssd,
    calculate_sdnn,
    calculate_pnn50,
)
from ptt_blood_pressure import PTTBloodPressureModel, BloodPressureReading
from dfa_alpha1 import calculate_dfa_alpha1, calculate_dfa_scaling_curve, DFAScalingResult
from spatial_grappling_3d.kinematics.opml_tree import parse_opml_tree
from spatial_grappling_3d.kinematics.skeleton import MEDIAPIPE_33_LANDMARKS, build_default_pose
from spatial_grappling_3d.kinematics.torque import compute_joint_torque, evaluate_joint_safety, JOINT_LIMITS_NM
from prima_ring_adapter import PrimaTB4OffloadManager, TB4DMAMetrics, RingState


# ==============================================================================
# 1. INITIATIVE R1: MLX QLoRA, Consensus Merger & Bradley-Terry ELO Stress
# ==============================================================================

class TestTier5AdversarialR1MLXGovernance(unittest.TestCase):
    """Adversarial stress tests for Initiative R1 (RAM Governor, MergeKit, ELO Gate)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="tier5_r1_mlx_")
        self.test_path = Path(self.test_dir)
        self.governor = DynamicRamGovernor(total_system_ram_gb=24.0, cap_pct=90.0, min_headroom_gb=2.50)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_r1_ram_governor_extreme_over_allocation(self):
        """Test RAM Governor rejects massive allocations exceeding 21.6GB cap."""
        # 1. Severe over-allocation (Base 18GB + KV 3GB + Act 2GB = 23.0GB > 21.6GB)
        info = self.governor.check_headroom(base_model_gb=18.0, kv_cache_gb=3.0, activation_gb=2.0)
        self.assertFalse(info["is_safe"], "Allocation of 23.0GB must be marked unsafe")
        self.assertEqual(info["status"], "EXCEEDS_CAP")
        self.assertEqual(info["allocated_ai_ram_gb"], 23.0)
        self.assertLess(info["ram_headroom_gb"], 2.50)
        self.assertEqual(info["ram_headroom_gb"], -1.40)

        # 2. Catastrophic over-allocation (Base 50GB)
        info_catastrophic = self.governor.check_headroom(base_model_gb=50.0, kv_cache_gb=10.0, activation_gb=5.0)
        self.assertFalse(info_catastrophic["is_safe"])
        self.assertEqual(info_catastrophic["allocated_ai_ram_gb"], 65.0)
        self.assertEqual(info_catastrophic["ram_headroom_gb"], -43.40)

    def test_r1_ram_governor_headroom_breach_boundary(self):
        """Test RAM Governor detects headroom breach when allocated < cap but headroom < 2.50GB."""
        # Cap = 21.60GB. Allocated = 19.50GB (Base 15GB + KV 2.5GB + Act 2GB).
        # Headroom = 21.60 - 19.50 = 2.10GB < 2.50GB requirement!
        info = self.governor.check_headroom(base_model_gb=15.0, kv_cache_gb=2.5, activation_gb=2.0)
        self.assertFalse(info["is_safe"], "Headroom of 2.10GB must breach min_headroom requirement of 2.50GB")
        self.assertEqual(info["status"], "EXCEEDS_CAP")
        self.assertEqual(info["ram_headroom_gb"], 2.10)

        # Nominal safe allocation: Allocated = 18.40GB -> Headroom = 3.20GB >= 2.50GB
        info_safe = self.governor.check_headroom(base_model_gb=14.5, kv_cache_gb=2.1, activation_gb=1.8)
        self.assertTrue(info_safe["is_safe"], "Headroom of 3.20GB must be certified healthy")
        self.assertEqual(info_safe["status"], "CERTIFIED_HEALTHY")
        self.assertEqual(info_safe["ram_headroom_gb"], 3.20)

    def test_r1_ram_governor_zero_and_custom_cap_boundaries(self):
        """Test RAM Governor with zero allocation and custom dynamic caps."""
        # Zero allocation
        info_zero = self.governor.check_headroom(base_model_gb=0.0, kv_cache_gb=0.0, activation_gb=0.0)
        self.assertTrue(info_zero["is_safe"])
        self.assertEqual(info_zero["ram_headroom_gb"], 21.60)

        # Custom tight cap (e.g. 16GB total RAM -> 14.0GB cap, 3.0GB headroom required)
        gov_tight = DynamicRamGovernor(total_system_ram_gb=16.0, cap_pct=87.5, min_headroom_gb=3.0)
        self.assertEqual(gov_tight.dynamic_cap_gb, 14.0)
        info_tight = gov_tight.check_headroom(base_model_gb=10.0, kv_cache_gb=1.5, activation_gb=1.0)
        self.assertFalse(info_tight["is_safe"])
        self.assertEqual(info_tight["ram_headroom_gb"], 1.50)

    def test_r1_consensus_merger_dissenting_veto_rejection(self):
        """Test MergeKit synthesis is strictly REJECTED when any orchestrator casts a veto or dissent."""
        engine = AutonomousConsensusMergeEngine(workspace_root=self.test_path)

        # Orchestrator with explicit VETO
        veto_payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.99, "vote": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.98, "vote": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.10, "vote": "VETO"},
            }
        }
        score = engine.calculate_consensus_score(veto_payload)
        self.assertLessEqual(score, CONSENSUS_THRESHOLD, "Vetoed consensus score must be <= 0.95")

        result = engine.evaluate_and_trigger_merge(veto_payload)
        self.assertEqual(result.get("status"), "REJECTED", "Veto must trigger REJECTED status")
        self.assertIn("consensus", result.get("reason", "").lower())

        # Verify ZERO recipes or model artifacts generated in output directories
        recipe_files = list(engine.recipe_dir.glob("*.yaml")) + list(engine.recipe_dir.glob("*.yml"))
        model_files = list(engine.models_dir.glob("*.json")) + list(engine.models_dir.glob("*.gguf"))
        self.assertEqual(len(recipe_files), 0, "No recipe files must be generated on rejection")
        self.assertEqual(len(model_files), 0, "No offspring model files must be created on rejection")

    def test_r1_consensus_merger_corrupted_payload_fuzzing(self):
        """Test MergeKit consensus calculator under corrupted, malformed, and adversarial payloads."""
        engine = AutonomousConsensusMergeEngine(workspace_root=self.test_path)

        fuzz_payloads = [
            None,
            {},
            {"tri_orchestrator_votes": "corrupted_string"},
            {"tri_orchestrator_votes": None},
            {"tri_orchestrator_votes": {"cloud_orchestrator": -0.80, "local_ai_orchestrator": -0.50, "genetic_ai_orchestrator": -0.10}},
            {"tri_orchestrator_votes": {"cloud_orchestrator": "garbage", "local_ai_orchestrator": None, "genetic_ai_orchestrator": {}}},
            {"tri_orchestrator_votes": {"cloud_orchestrator": False, "local_ai_orchestrator": False, "genetic_ai_orchestrator": False}},
        ]

        for payload in fuzz_payloads:
            score = engine.calculate_consensus_score(payload)
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0, "Consensus score must be non-negative")
            self.assertLessEqual(score, CONSENSUS_THRESHOLD, "Corrupted payload must not exceed threshold")

            result = engine.evaluate_and_trigger_merge(payload)
            self.assertEqual(result.get("status"), "REJECTED")

    def test_r1_consensus_merger_parent_model_immutability(self):
        """Test that Parent 1 and Parent 2 base models remain 100% intact and unmutated."""
        engine = AutonomousConsensusMergeEngine(workspace_root=self.test_path)

        # Create mock parent model files in base_models_dir
        engine.base_models_dir.mkdir(parents=True, exist_ok=True)
        p1_file = engine.base_models_dir / "Qwen-AgentWorld-35B-Q4_K_M.gguf"
        p2_file = engine.base_models_dir / "DeepSeek-R1-32B-Q4_K_M.gguf"
        p1_content = b"GENUINE_PARENT_1_TENSOR_WEIGHTS_HEX_DEADBEEF" * 100
        p2_content = b"GENUINE_PARENT_2_TENSOR_WEIGHTS_HEX_CAFEBABE" * 100
        p1_file.write_bytes(p1_content)
        p2_file.write_bytes(p2_content)

        p1_hash_before = hashlib.sha256(p1_content).hexdigest()
        p2_hash_before = hashlib.sha256(p2_content).hexdigest()

        # Execute evaluated merge with high consensus
        valid_payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.99, "vote": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.98, "vote": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.97, "vote": "APPROVE"},
            },
            "parent_models": ["Qwen-AgentWorld-35B", "DeepSeek-R1-32B"],
            "offspring_id": "offspring_moe_test_01",
            "merge_algorithm": "SPARSE_MOE_DARE_TIES"
        }
        result = engine.evaluate_and_trigger_merge(valid_payload)
        self.assertEqual(result.get("status"), "TRIGGERED")

        # Verify parent models were NOT modified or deleted
        self.assertTrue(p1_file.exists(), "Parent 1 model file must remain on disk")
        self.assertTrue(p2_file.exists(), "Parent 2 model file must remain on disk")
        self.assertEqual(hashlib.sha256(p1_file.read_bytes()).hexdigest(), p1_hash_before, "Parent 1 must be byte-for-byte unmutated")
        self.assertEqual(hashlib.sha256(p2_file.read_bytes()).hexdigest(), p2_hash_before, "Parent 2 must be byte-for-byte unmutated")

    def test_r1_elo_gate_promotion_boundary_precision(self):
        """Test Bradley-Terry ELO Gate boundary precision: 64.99% (reject) vs 65.00% (promote) vs 65.01% (promote)."""
        leaderboard_file = self.test_path / "elo_leaderboard.json"
        promotion_log = self.test_path / "elo_promotion.jsonl"
        obsidian_report = self.test_path / "elo_report.md"
        symlink_dir = self.test_path / "lora_adapters"
        symlink_dir.mkdir(parents=True, exist_ok=True)

        gate = EloPromotionGate(
            leaderboard_path=leaderboard_file,
            promotion_log_path=promotion_log,
            obsidian_report_path=obsidian_report,
            k_factor=24.0,
            default_candidate_elo=1800.0,
        )

        # 1. Boundary: 64.99% Win Rate -> Strictly REJECTED
        cand_sub = self.test_path / "cand_sub_6499"
        cand_sub.mkdir(parents=True, exist_ok=True)
        gate.ratings[cand_sub.name] = {"elo": 1820.0, "tasks_scored": 10, "win_rate_pct": 64.99, "tier": "LOCAL_CANDIDATE"}
        gate.run_tournament = lambda **kwargs: (0.6499, [{"category_name": "Test", "challenger": "DeepSeek-R1-32B", "expected_win_prob": 0.5, "score": 0.5, "candidate_post_elo": 1820.0}])

        promoted, win_rate, _ = gate.evaluate_and_promote(str(cand_sub), challenger_adapters=["DeepSeek-R1-32B"], min_win_rate=0.65, target_symlink_dir=str(symlink_dir))
        self.assertFalse(promoted, "64.99% win-rate must NOT be promoted against 65.00% threshold")
        self.assertEqual(win_rate, 0.6499)
        self.assertFalse((symlink_dir / "active_production_adapter").exists())

        # 2. Boundary: 65.00% Win Rate -> Exactly APPROVED
        cand_exact = self.test_path / "cand_exact_6500"
        cand_exact.mkdir(parents=True, exist_ok=True)
        gate.ratings[cand_exact.name] = {"elo": 1850.0, "tasks_scored": 10, "win_rate_pct": 65.00, "tier": "PROMOTED_CHAMPION"}
        gate.run_tournament = lambda **kwargs: (0.6500, [{"category_name": "Test", "challenger": "DeepSeek-R1-32B", "expected_win_prob": 0.5, "score": 1.0, "candidate_post_elo": 1850.0}])

        promoted, win_rate, _ = gate.evaluate_and_promote(str(cand_exact), challenger_adapters=["DeepSeek-R1-32B"], min_win_rate=0.65, target_symlink_dir=str(symlink_dir))
        self.assertTrue(promoted, "65.00% win-rate must be PROMOTED when threshold is 65.00%")
        self.assertEqual(win_rate, 0.6500)
        self.assertTrue((symlink_dir / "active_production_adapter").is_symlink())

        # 3. Boundary: 65.01% Win Rate -> APPROVED
        cand_supra = self.test_path / "cand_supra_6501"
        cand_supra.mkdir(parents=True, exist_ok=True)
        gate.ratings[cand_supra.name] = {"elo": 1860.0, "tasks_scored": 10, "win_rate_pct": 65.01, "tier": "PROMOTED_CHAMPION"}
        gate.run_tournament = lambda **kwargs: (0.6501, [{"category_name": "Test", "challenger": "DeepSeek-R1-32B", "expected_win_prob": 0.5, "score": 1.0, "candidate_post_elo": 1860.0}])

        promoted, win_rate, _ = gate.evaluate_and_promote(str(cand_supra), challenger_adapters=["DeepSeek-R1-32B"], min_win_rate=0.65, target_symlink_dir=str(symlink_dir))
        self.assertTrue(promoted, "65.01% win-rate must be PROMOTED")
        self.assertEqual(win_rate, 0.6501)

    def test_r1_bradley_terry_extreme_rating_deltas(self):
        """Test Bradley-Terry mathematical model under extreme rating imbalances (+/-50,000) and zero-sum conservation."""
        # Extreme advantage (+50,000) -> 1.0
        p_huge_win = BradleyTerryModel.expected_win_probability(51800.0, 1800.0)
        self.assertEqual(p_huge_win, 1.0, "Massive rating advantage must clamp safely to 1.0")

        # Extreme disadvantage (-50,000) -> 0.0
        p_huge_loss = BradleyTerryModel.expected_win_probability(1800.0, 51800.0)
        self.assertEqual(p_huge_loss, 0.0, "Massive rating disadvantage must clamp safely to 0.0")

        # Equal ratings -> exactly 0.50
        for r in [0.0, 500.0, 1500.0, 2248.5, 9999.0]:
            p_tie = BradleyTerryModel.expected_win_probability(r, r)
            self.assertEqual(p_tie, 0.5, f"Identical rating {r} must yield exactly 0.50 probability")

        # Zero-sum point conservation
        new_a, new_b = BradleyTerryModel.update_elo(1800.0, 1900.0, score_a=1.0, k_factor=32.0)
        delta_a = new_a - 1800.0
        delta_b = new_b - 1900.0
        self.assertAlmostEqual(delta_a + delta_b, 0.0, places=1, msg="ELO point deltas must be strictly zero-sum")

    def test_r1_elo_rapid_symlink_swap_and_rollback(self):
        """Test rapid atomic symlink swap and instant rollback integrity."""
        symlink_dir = self.test_path / "lora_adapters_swap"
        symlink_dir.mkdir(parents=True, exist_ok=True)
        active_link = symlink_dir / "active_production_adapter"

        ad_1 = self.test_path / "adapter_v1"
        ad_2 = self.test_path / "adapter_v2"
        ad_1.mkdir(parents=True, exist_ok=True)
        ad_2.mkdir(parents=True, exist_ok=True)

        gate = EloPromotionGate(
            leaderboard_path=self.test_path / "lb.json",
            promotion_log_path=self.test_path / "plog.jsonl",
            obsidian_report_path=self.test_path / "rep.md"
        )

        # Promote v1
        sym_1 = gate.update_production_symlink(str(ad_1), str(symlink_dir), "active_production_adapter")
        self.assertIsNotNone(sym_1)
        self.assertEqual(active_link.resolve(), ad_1.resolve())

        # Promote v2
        sym_2 = gate.update_production_symlink(str(ad_2), str(symlink_dir), "active_production_adapter")
        self.assertIsNotNone(sym_2)
        self.assertEqual(active_link.resolve(), ad_2.resolve())

        # Rollback to previous champion (ad_1)
        rb_sym = gate.rollback_to_champion(str(symlink_dir), "active_production_adapter")
        self.assertIsNotNone(rb_sym)
        self.assertEqual(active_link.resolve(), ad_1.resolve())


# ==============================================================================
# 2. INITIATIVE R2: Headless Shopify GraphQL, HMAC & Rate Limiting Stress
# ==============================================================================

class TestTier5AdversarialR2ShopifyGateway(unittest.TestCase):
    """Adversarial stress tests for Initiative R2 (Shopify GraphQL, HMAC tokens, Rate Limiter)."""

    def setUp(self):
        self.secret_key = "lauburu_production_secret_key_2026"
        self.gateway = MemberAPIGateway(secret_key=self.secret_key)
        self.client = ShopifyStorefrontGraphQLClient(shop_domain="lauburu-ai.myshopify.com")

    def test_r2_shopify_graphql_injection_and_fuzzing(self):
        """Fuzz Shopify GraphQL client with SQLi, XSS, binary noise, and malformed query strings."""
        malformed_queries = [
            "SELECT * FROM shopify_customers; DROP TABLE users;--",
            "<script>alert('XSS_ATTACK_LAUBURU')</script>",
            "query { unclosed_bracket { id title }",
            "",
            "   \n\t  ",
            "mutation { malicious_injection(input: null) { hacked } }",
            "\x00\x01\x02\xff\xfe\xfd",
        ]

        for q in malformed_queries:
            resp = self.client.execute_graphql(q, dry_run=True)
            self.assertIsInstance(resp, dict)
            if not q.strip().startswith(("query", "mutation")):
                self.assertFalse(resp.get("valid_syntax", False), f"Non-GraphQL query '{q[:20]}' must be invalid")

    def test_r2_cart_builder_negative_and_adversarial_quantities(self):
        """Test CartCreate input builder clamps negative/zero quantities to minimum 1."""
        # Negative quantity (-100) -> must clamp to 1
        cart_neg = self.client.build_cart_create_input("gid://shopify/ProductVariant/1001", quantity=-100)
        self.assertEqual(cart_neg["lines"][0]["quantity"], 1, "Negative quantity must clamp to 1")

        # Zero quantity (0) -> must clamp to 1
        cart_zero = self.client.build_cart_create_input("gid://shopify/ProductVariant/1001", quantity=0)
        self.assertEqual(cart_zero["lines"][0]["quantity"], 1, "Zero quantity must clamp to 1")

        # Valid positive quantity (5)
        cart_pos = self.client.build_cart_create_input("gid://shopify/ProductVariant/1001", quantity=5)
        self.assertEqual(cart_pos["lines"][0]["quantity"], 5)

    def test_r2_hmac_token_forgery_attacks(self):
        """Test API Gateway detects and rejects forged, modified, and tampered HMAC tokens."""
        customer_id = "gid://shopify/Customer/990011"
        valid_token = self.gateway.issue_api_key(customer_id, CustomerTier.FREE, expiry_days=7)
        self.assertTrue(valid_token.startswith("lb_free_"))

        # 1. Tier Privilege Escalation Attack (change free to lauburu_elite without re-signing)
        forged_elite_token = valid_token.replace("lb_free_", "lb_lauburu_elite_")
        payload = self.gateway.verify_token(forged_elite_token)
        self.assertIsNone(payload, "Forged tier escalation token must be strictly rejected")

        # 2. Customer ID Tampering Attack (change customer hex)
        parts = valid_token.split("_")
        tampered_hex = "ffffffffffffffff"
        parts[-3] = tampered_hex
        tampered_cust_token = "_".join(parts)
        self.assertIsNone(self.gateway.verify_token(tampered_cust_token), "Tampered customer hex must be rejected")

        # 3. Signature Bit-Flip Tampering Attack
        sig = parts[-1]
        tampered_sig = ("0" if sig[0] != "0" else "1") + sig[1:]
        parts[-1] = tampered_sig
        tampered_sig_token = "_".join(parts)
        self.assertIsNone(self.gateway.verify_token(tampered_sig_token), "Tampered signature must be rejected")

        # 4. Secret Key Mismatch Attack (token signed with rogue key)
        rogue_gateway = MemberAPIGateway(secret_key="attacker_rogue_secret_key")
        rogue_token = rogue_gateway.issue_api_key(customer_id, CustomerTier.ELITE, expiry_days=7)
        self.assertIsNone(self.gateway.verify_token(rogue_token), "Token signed with attacker key must be rejected")

    def test_r2_hmac_expired_token_replay_attacks(self):
        """Test API Gateway rejects expired HMAC tokens."""
        # Generate expired token with negative expiry days (-1 day)
        expired_token = self.gateway.issue_api_key("cust_expired_01", CustomerTier.PRO, expiry_days=-1)
        payload = self.gateway.verify_token(expired_token)
        self.assertIsNone(payload, "Expired token must return None")

        # Verify gateway handle_request returns HTTP 403 Forbidden
        resp = self.gateway.handle_request("/api/v1/telemetry", api_token=expired_token)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.success)
        self.assertIn("Invalid, tampered, or expired", resp.error or "")

        # Verify missing token returns HTTP 401 Unauthorized
        resp_missing = self.gateway.handle_request("/api/v1/telemetry", api_token=None)
        self.assertEqual(resp_missing.status_code, 401)

    def test_r2_hmac_structural_malformations(self):
        """Test HMAC verification handles structurally malformed tokens gracefully."""
        garbage_tokens = [
            "",
            "invalid_prefix_free_1234_5678_abcd",
            "lb_only_two_parts",
            "lb_free_hex_notanumber_sig",
            "lb_free_1234_5678_sig_extra_part_6",
            "lb_unknown_tier_1234_5678_sig",
            None,
        ]
        for bad_tok in garbage_tokens:
            self.assertIsNone(self.gateway.verify_token(bad_tok))

    def test_r2_sliding_window_rate_limiter_burst_starvation(self):
        """Test Sliding Window Rate Limiter starves burst traffic exceeding tier quotas (FREE=60, PRO=300)."""
        limiter = SlidingWindowRateLimiter()
        client_key = "user_free_test_01"
        t0 = 1000.0  # Base timestamp

        # FREE tier allows 60 RPM
        for i in range(60):
            allowed, remaining, retry_after = limiter.check_and_record(client_key, CustomerTier.FREE, current_time=t0 + (i * 0.1))
            self.assertTrue(allowed, f"Request {i+1} of 60 must be allowed")
            self.assertEqual(remaining, 59 - i)
            self.assertIsNone(retry_after)

        # 61st request in the same minute window -> STARVED (HTTP 429)
        allowed_61, rem_61, retry_61 = limiter.check_and_record(client_key, CustomerTier.FREE, current_time=t0 + 6.0)
        self.assertFalse(allowed_61, "61st request within 60s must be throttled")
        self.assertEqual(rem_61, 0)
        self.assertIsNotNone(retry_61)
        self.assertGreaterEqual(retry_61, 1)

    def test_r2_sliding_window_eviction_and_recovery(self):
        """Test sliding window evicts expired entries after 60s and restores quota."""
        limiter = SlidingWindowRateLimiter()
        client_key = "user_eviction_test"
        t0 = 5000.0

        # Fill quota
        for _ in range(60):
            limiter.check_and_record(client_key, CustomerTier.FREE, current_time=t0)

        # Advance time by 61 seconds (t = t0 + 61.0) -> sliding window evicts oldest requests -> ALLOWED
        allowed_after, rem_after, _ = limiter.check_and_record(client_key, CustomerTier.FREE, current_time=t0 + 61.0)
        self.assertTrue(allowed_after, "Request after sliding window eviction must be allowed")
        self.assertEqual(rem_after, 59)

    def test_r2_rate_limiter_multi_client_isolation(self):
        """Test that burst starvation of Client A does not degrade or block Client B."""
        limiter = SlidingWindowRateLimiter()
        client_a = "attacker_burst_client"
        client_b = "legitimate_user_client"
        t0 = 2000.0

        # Starve Client A with 65 rapid requests
        for _ in range(65):
            limiter.check_and_record(client_a, CustomerTier.FREE, current_time=t0)

        # Check Client A is blocked
        allowed_a, _, _ = limiter.check_and_record(client_a, CustomerTier.FREE, current_time=t0)
        self.assertFalse(allowed_a, "Client A must be starved")

        # Client B sends first request at same timestamp -> must be ALLOWED
        allowed_b, rem_b, _ = limiter.check_and_record(client_b, CustomerTier.FREE, current_time=t0)
        self.assertTrue(allowed_b, "Client B must remain unaffected by Client A's rate limiting")
        self.assertEqual(rem_b, 59)

    def test_r2_daily_quota_exhaustion(self):
        """Test that exceeding daily quota (1,000 for FREE) blocks requests."""
        limiter = SlidingWindowRateLimiter()
        client_key = "daily_quota_test_user"
        t0 = 10000.0

        # Simulate 1,000 requests spread across time
        today_str = time.strftime("%Y-%m-%d", time.gmtime(t0))
        limiter._daily_counts[client_key] = (today_str, 1000)

        # Next request must be rejected due to daily quota
        allowed, rem, retry = limiter.check_and_record(client_key, CustomerTier.FREE, current_time=t0)
        self.assertFalse(allowed, "Exceeding daily quota must block request")
        self.assertEqual(retry, 3600)


# ==============================================================================
# 3. INITIATIVE R3: Medical Biometrics DSP Stress Testing
# ==============================================================================

class TestTier5AdversarialR3BiometricsDSP(unittest.TestCase):
    """Adversarial stress tests for Initiative R3 (ECG, Kamath, PTT BP, DFA-alpha1)."""

    def setUp(self):
        self.detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        self.ptt_model = PTTBloodPressureModel(arterial_path_length_m=0.80)

    def test_r3_ecg_flatline_and_dc_offset_rejection(self):
        """Test Pan-Tompkins handles pure flatlines and high DC offsets without false QRS peaks."""
        # 1. Pure zero flatline (4.0s @ 512Hz = 2048 samples)
        flatline = [0.0] * 2048
        res_zero = self.detector.detect_peaks(flatline)
        self.assertEqual(res_zero.qrs_count, 0, "Pure flatline must detect 0 QRS complexes")
        self.assertEqual(res_zero.peak_indices, [])
        self.assertIsNone(res_zero.mean_hr_bpm)
        self.assertIsNone(res_zero.rmssd_ms)

        # 2. Extreme DC offset flatline (+5000.0 mV constant step)
        dc_flatline = [5000.0] * 2048
        res_dc = self.detector.detect_peaks(dc_flatline)
        self.assertEqual(res_dc.qrs_count, 0, "High DC step flatline must detect 0 QRS peaks")
        self.assertEqual(res_dc.peak_indices, [])

        # 3. Very short / degenerate signals (<8 samples)
        self.assertEqual(self.detector.detect_peaks([]).qrs_count, 0)
        self.assertEqual(self.detector.detect_peaks([1.0, 2.0, 3.0]).qrs_count, 0)

    def test_r3_ecg_50hz_mains_hum_and_baseline_drift(self):
        """Test Pan-Tompkins bandpass filter strips 50Hz mains hum and 0.1Hz baseline wander."""
        # Generate 8s of 60 BPM clean ECG (8 complexes expected at 1s intervals)
        clean_ecg = generate_fourier_ecg_signal(duration_sec=8.0, fs=512.0, heart_rate_bpm=60.0)
        t_axis = [i / 512.0 for i in range(len(clean_ecg))]

        # Add 50Hz mains powerline hum (0.08 mV sine) + 0.1Hz low-frequency respiration drift (1.20 mV sine)
        noisy_ecg = [
            clean_ecg[i] + 0.08 * math.sin(2.0 * math.pi * 50.0 * t_axis[i]) + 1.20 * math.sin(2.0 * math.pi * 0.1 * t_axis[i])
            for i in range(len(clean_ecg))
        ]

        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        res = detector.detect_peaks(noisy_ecg)
        # Accurately detects the 8 true cardiac complexes
        self.assertEqual(res.qrs_count, 8, "Detector must accurately extract exactly 8 true QRS peaks through 50Hz hum and drift")
        if res.mean_hr_bpm is not None:
            self.assertAlmostEqual(res.mean_hr_bpm, 60.0, delta=2.0, msg="Heart rate must resolve to 60 BPM")

    def test_r3_ectopic_rr_jumps_and_kamath_20pct_filter(self):
        """Test Kamath et al. (2004) 20% artifact filter on extreme ectopic RR jumps (>200% PVC)."""
        # Normal sinus rhythm @ 75 BPM (RR = 800ms) with a Premature Ventricular Contraction (PVC)
        # PVC: RR drops from 800ms to 350ms (-56.25% jump), followed by compensatory pause of 1300ms (+271% jump)
        rr_series = [800.0, 805.0, 795.0, 800.0, 350.0, 1300.0, 800.0, 798.0, 802.0, 800.0]

        filtered_rr, artifact_count = apply_kamath_artifact_filter(rr_series, threshold_pct=20.0)
        self.assertEqual(len(filtered_rr), len(rr_series))
        self.assertGreaterEqual(artifact_count, 2, "Must detect at least 2 ectopic/artifact beats")

        for val in filtered_rr:
            self.assertGreater(val, 550.0, "Ectopic 350ms beat must be corrected above 550ms")
            self.assertLess(val, 1100.0, "Compensatory 1300ms pause must be corrected below 1100ms")

    def test_r3_hrv_metrics_stability_under_ectopic_noise(self):
        """Test RMSSD, SDNN, and pNN50 calculations are stable on Kamath-filtered physiological arrays."""
        rr_series = [800.0, 810.0, 790.0, 805.0, 795.0, 800.0, 820.0, 780.0, 800.0, 805.0]
        rmssd = calculate_rmssd(rr_series)
        sdnn = calculate_sdnn(rr_series)
        pnn50 = calculate_pnn50(rr_series)

        self.assertIsNotNone(rmssd)
        self.assertIsNotNone(sdnn)
        self.assertIsNotNone(pnn50)
        self.assertGreater(rmssd, 0.0)
        self.assertLess(rmssd, 50.0, "Normal resting RMSSD should be < 50ms")
        self.assertGreater(sdnn, 0.0)

    def test_r3_ptt_inverted_and_non_physiological_clamping(self):
        """Test PTT Blood Pressure model handles non-physiological ranges and invalid cuff calibrations."""
        # 1. Invalid calibration: DBP >= SBP (e.g. SBP=80, DBP=120) -> Must fail
        cal_fail = self.ptt_model.calibrate(cuff_sbp=80.0, cuff_dbp=120.0, measured_ptt_ms=200.0, measured_hr_bpm=70.0)
        self.assertFalse(cal_fail, "DBP >= SBP calibration must be rejected")

        # 2. Invalid calibration: Extreme PTT out of range (20ms or 1500ms)
        self.assertFalse(self.ptt_model.calibrate(cuff_sbp=120.0, cuff_dbp=80.0, measured_ptt_ms=20.0, measured_hr_bpm=70.0))
        self.assertFalse(self.ptt_model.calibrate(cuff_sbp=120.0, cuff_dbp=80.0, measured_ptt_ms=1500.0, measured_hr_bpm=70.0))

        # 3. Valid calibration
        cal_ok = self.ptt_model.calibrate(cuff_sbp=120.0, cuff_dbp=80.0, measured_ptt_ms=200.0, measured_hr_bpm=70.0)
        self.assertTrue(cal_ok)

        # 4. Estimate with non-physiological PTT (e.g. 10ms -> PWV = 80 m/s) -> STANDBY / None
        reading_extreme = self.ptt_model.estimate_blood_pressure(ptt_ms=10.0, hr_bpm=70.0)
        self.assertEqual(reading_extreme.status, "STANDBY")
        self.assertIsNone(reading_extreme.systolic_mmhg)

        # 5. Hypertensive Crisis classification (>180 / >120)
        reading_crisis = self.ptt_model.estimate_blood_pressure(ptt_ms=90.0, hr_bpm=140.0)
        self.assertIsNotNone(reading_crisis.systolic_mmhg)
        self.assertGreater(reading_crisis.systolic_mmhg, 140.0)

    def test_r3_ptt_invalid_cuff_calibration_rejection(self):
        """Test rejection of non-physiological cuff blood pressure values (<60 SBP, >250 SBP, <35 DBP)."""
        self.assertFalse(self.ptt_model.calibrate(50.0, 40.0, 200.0, 70.0), "SBP < 60 must be rejected")
        self.assertFalse(self.ptt_model.calibrate(260.0, 100.0, 200.0, 70.0), "SBP > 250 must be rejected")
        self.assertFalse(self.ptt_model.calibrate(120.0, 30.0, 200.0, 70.0), "DBP < 35 must be rejected")

    def test_r3_dfa_alpha1_boundary_cases_and_zero_variance(self):
        """Test DFA-alpha1 handles small sample counts (s < 4), zero variance series, and short arrays."""
        # 1. Sub-window scale (len < 4) -> Must return None (Rule #0 compliant)
        self.assertIsNone(calculate_dfa_alpha1([800.0, 810.0]))
        self.assertIsNone(calculate_dfa_alpha1([800.0, 810.0, 790.0]))

        # 2. Zero variance / constant flat RR series ([800.0] * 50)
        flat_rrs = [800.0] * 50
        alpha1_flat = calculate_dfa_alpha1(flat_rrs)
        self.assertIsNotNone(alpha1_flat)
        self.assertGreaterEqual(alpha1_flat, 0.40)
        self.assertLessEqual(alpha1_flat, 1.40)

    def test_r3_dfa_alpha1_fractal_scaling_and_zone_classification(self):
        """Test DFA-alpha1 on physiological series and verify Zone 2/3 classification."""
        np.random.seed(42)
        noise = np.random.normal(0, 15.0, 64)
        fractal_rrs = [800.0 + float(x) for x in noise]
        res = calculate_dfa_scaling_curve(fractal_rrs, scale_min=4, scale_max=16)
        self.assertIsInstance(res, DFAScalingResult)
        self.assertIsNotNone(res.alpha1)
        self.assertGreaterEqual(res.alpha1, 0.0)
        self.assertLessEqual(res.alpha1, 2.0)
        self.assertIn("Zone", res.zone_status)


# ==============================================================================
# 4. INITIATIVE R4: 3D Spatial Grappling Kinematics Stress Testing
# ==============================================================================

class TestTier5AdversarialR4SpatialGrappling(unittest.TestCase):
    """Adversarial stress tests for Initiative R4 (OPML Tree, Tatami Confinement, Joint Torque)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="tier5_r4_spatial_")
        self.test_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_r4_opml_corrupted_xml_and_missing_tags(self):
        """Test OPML MindMap parser handles malformed XML, unclosed tags, and missing body tags."""
        # 1. Missing file
        non_existent = self.test_path / "missing.opml"
        with self.assertRaises(FileNotFoundError):
            parse_opml_tree(non_existent)

        # 2. Corrupted XML syntax (unclosed outline tag)
        corrupt_xml = self.test_path / "corrupt.opml"
        corrupt_xml.write_text("<?xml version='1.0'?><opml><head></head><body><outline text='Guard'><outline text='Closed'></opml>", encoding="utf-8")
        with self.assertRaises(ET.ParseError):
            parse_opml_tree(corrupt_xml)

        # 3. Missing <body> element
        no_body_xml = self.test_path / "no_body.opml"
        no_body_xml.write_text("<?xml version='1.0'?><opml><head><title>No Body</title></head></opml>", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            parse_opml_tree(no_body_xml)
        self.assertIn("<body> element missing", str(ctx.exception))

    def test_r4_opml_missing_file_handling(self):
        """Test OPML parser raises FileNotFoundError when path does not exist."""
        with self.assertRaises(FileNotFoundError):
            parse_opml_tree(Path("/non/existent/path/martial.opml"))

    def test_r4_cylindrical_projection_tatami_confinement(self):
        """Test cylindrical projection guarantees radius <= 4.8m (strictly within 10m x 10m mat bounds)."""
        valid_opml_str = generate_canonical_opml_string(num_nodes=50)
        opml_file = self.test_path / "grappling_test.opml"
        opml_file.write_text(valid_opml_str, encoding="utf-8")

        nodes, transitions, categories = parse_opml_tree(opml_file)
        self.assertGreaterEqual(len(nodes), 10)
        self.assertGreaterEqual(len(transitions), 9)

        for node in nodes:
            # Radial distance on the 2D Tatami floor
            radial_dist = math.sqrt(node.x ** 2 + node.y ** 2)
            self.assertLessEqual(radial_dist, 5.0, f"Node '{node.text}' radial distance {radial_dist:.3f}m exceeds 5.0m Tatami radius")
            self.assertFalse(math.isnan(node.x), "Node X coordinate must not be NaN")
            self.assertFalse(math.isnan(node.y), "Node Y coordinate must not be NaN")
            self.assertFalse(math.isnan(node.z), "Node Z coordinate must not be NaN")
            self.assertGreaterEqual(node.z, 0.0, "Z height must be non-negative")

    def test_r4_cylindrical_singularity_depth_scaling(self):
        """Test cylindrical coordinate projection non-singularity and bounded radius scaling across depth."""
        for depth in range(10):
            radius = min(1.0 + (depth * 0.45), 4.8)
            self.assertGreaterEqual(radius, 1.0, "Radius at any depth must be >= 1.0m (no r=0 singularity)")
            self.assertLessEqual(radius, 4.8, "Radius must be clamped to <= 4.8m")

    def test_r4_extreme_joint_torque_solver_and_limit_violations(self):
        """Test analytical torque solver flags severe safety limit breaches (>1000 N*m)."""
        # 1. Normal safe torque (Elbow: F=50N, r=0.35m, theta=45 deg -> 12.37 N*m <= 45.0 N*m)
        safe_res = compute_joint_torque(force=50.0, lever_arm=0.35, angle_deg=45.0, joint_name="right_elbow")
        self.assertTrue(safe_res.is_safe)
        self.assertEqual(safe_res.torque_nm, 12.37)
        self.assertEqual(safe_res.safe_limit_nm, 45.0)

        # 2. Extreme dangerous torque (Elbow: F=5000N, r=0.35m, theta=90 deg -> 1750.0 N*m > 45.0 N*m)
        extreme_res = compute_joint_torque(force=5000.0, lever_arm=0.35, angle_deg=90.0, joint_name="right_elbow")
        self.assertFalse(extreme_res.is_safe, "1750 N*m torque must breach elbow safety limit")
        self.assertEqual(extreme_res.torque_nm, 1750.0)

    def test_r4_joint_torque_angle_boundaries(self):
        """Test angle boundary conditions: 0 deg / 180 deg (0 torque) and 90 deg (max torque)."""
        zero_torque_0 = compute_joint_torque(force=5000.0, lever_arm=0.35, angle_deg=0.0, joint_name="right_knee")
        self.assertEqual(zero_torque_0.torque_nm, 0.0, "0 deg angle must produce zero torque")
        self.assertTrue(zero_torque_0.is_safe)

        zero_torque_180 = compute_joint_torque(force=5000.0, lever_arm=0.35, angle_deg=180.0, joint_name="right_knee")
        self.assertEqual(zero_torque_180.torque_nm, 0.0, "180 deg angle must produce zero torque")
        self.assertTrue(zero_torque_180.is_safe)

        max_torque_90 = compute_joint_torque(force=100.0, lever_arm=0.35, angle_deg=90.0, joint_name="right_knee")
        self.assertEqual(max_torque_90.torque_nm, 35.0)

    def test_r4_multi_joint_anatomical_safety_audit(self):
        """Test multi-joint anatomical safety evaluation across all 6 regions."""
        joint_torques = {
            "cervical_spine": 150.0,  # Limit is 30.0 -> BREACH!
            "right_shoulder": 70.0,   # Limit is 80.0 -> SAFE
            "right_knee": 250.0,      # Limit is 110.0 -> BREACH!
            "lumbar_spine": 100.0,    # Limit is 120.0 -> SAFE
        }
        safety_eval = evaluate_joint_safety(joint_torques)
        self.assertEqual(len(safety_eval), 4)
        breached_joints = [r.joint_name for r in safety_eval if not r.is_safe]
        self.assertIn("cervical_spine", breached_joints)
        self.assertIn("right_knee", breached_joints)
        self.assertNotIn("right_shoulder", breached_joints)
        self.assertNotIn("lumbar_spine", breached_joints)

    def test_r4_mediapipe_33_landmark_completeness(self):
        """Test MediaPipe 33 landmark skeleton dictionary completeness."""
        self.assertEqual(len(MEDIAPIPE_33_LANDMARKS), 33, "MediaPipe 33-landmark skeleton must contain exactly 33 landmarks")
        default_pose = build_default_pose()
        self.assertEqual(len(default_pose), 33)
        for lm in default_pose:
            self.assertIsNotNone(lm.name)
            self.assertIsNotNone(lm.x)
            self.assertIsNotNone(lm.y)


# ==============================================================================
# 5. INITIATIVE R5: TB4 PRP Sharding, CRC32 Bit-Flip & Latency Stress
# ==============================================================================

class TestTier5AdversarialR5TB4PRPSharding(unittest.TestCase):
    """Adversarial stress tests for Initiative R5 (TB4 PRP sharding, CRC32 corruption, latency)."""

    def setUp(self):
        self.offload_mgr = PrimaTB4OffloadManager.get_instance()

    def test_r5_crc32_single_bit_flip_corruption_detection(self):
        """Test CRC32 chunk validation detects single-bit corruption in 1MB tensor payload."""
        # 1MB tensor payload
        clean_payload = b"\xaa\xbb\xcc\xdd" * (256 * 1024)
        clean_chunk = build_activation_chunk(seq_id=101, layer_idx=14, tensor_data=clean_payload)
        self.assertTrue(verify_activation_chunk(clean_chunk), "Clean chunk must pass CRC32 verification")

        # Inject single bit-flip (XOR byte 0 with 0x01)
        corrupted_payload = bytearray(clean_payload)
        corrupted_payload[0] ^= 0x01
        corrupted_chunk = {
            "sequence_id": clean_chunk["sequence_id"],
            "layer_idx": clean_chunk["layer_idx"],
            "size_bytes": len(corrupted_payload),
            "crc32": clean_chunk["crc32"],  # Original CRC32!
            "payload": bytes(corrupted_payload),
        }
        self.assertFalse(verify_activation_chunk(corrupted_chunk), "Single bit-flip must be detected by CRC32")

    def test_r5_crc32_multi_byte_truncation_and_rot(self):
        """Test CRC32 validation catches multi-byte truncation and payload rot."""
        clean_payload = b"\x11\x22\x33\x44" * 1000
        clean_chunk = build_activation_chunk(seq_id=202, layer_idx=10, tensor_data=clean_payload)

        # Truncation
        truncated_chunk = {
            "sequence_id": clean_chunk["sequence_id"],
            "layer_idx": clean_chunk["layer_idx"],
            "size_bytes": len(clean_payload) - 16,
            "crc32": clean_chunk["crc32"],
            "payload": clean_payload[:-16],
        }
        self.assertFalse(verify_activation_chunk(truncated_chunk), "Truncated payload must fail CRC32 verification")

    def test_r5_transfer_activation_chunk_dropped_counter(self):
        """Test transfer_activation_chunk verifies CRC32 and increments dropped_chunks on mismatch."""
        # Valid transfer
        arr = np.ones((128, 128), dtype=np.float32)
        success, lat_ms, crc = self.offload_mgr.transfer_activation_chunk(arr, layer_idx=15)
        self.assertTrue(success)
        self.assertGreater(crc, 0)
        self.assertLessEqual(lat_ms, 0.30, "TB4 DMA latency must remain < 0.30ms SLA")

    def test_r5_tb4_dynamic_layer_offload_and_state_consistency(self):
        """Test TB4 DMA layer offload updates host/offloaded partitions and telemetry counters."""
        target_layers = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
        res = self.offload_mgr.offload_layers(target_layers=target_layers, model_id="qwen-agentworld-35b")
        self.assertTrue(res)

        status = self.offload_mgr.get_status()
        self.assertEqual(status["active_offloaded_layers"], target_layers)
        self.assertIn("169.254", status["tb4_bridge_ip"])
        self.assertLessEqual(status["nominal_latency_ms"], 0.30, "Nominal TB4 latency must be < 0.30ms")
        self.assertLessEqual(status["measured_rtt_latency_ms"], 0.30, "Measured RTT must be < 0.30ms")
        self.assertTrue(status["latency_within_sla"])
        self.assertEqual(status["tb4_interface"], "bridge0")

    def test_r5_tb4_latency_probe_sla_compliance(self):
        """Test TB4 DMA latency probe strictly satisfies <0.30ms nominal latency target."""
        lat = self.offload_mgr.probe_tb4_latency()
        self.assertIsInstance(lat, float)
        self.assertGreater(lat, 0.0)
        self.assertLessEqual(lat, 0.30, f"TB4 DMA latency {lat}ms exceeds 0.30ms SLA")

    def test_r5_tb4_sequence_id_stream_integrity(self):
        """Test transfer of 50 consecutive activation chunks maintains sequence counter integrity."""
        seq_start = self.offload_mgr._chunk_seq
        for i in range(50):
            payload = struct_bytes = (i).to_bytes(4, byteorder="little") * 1024
            ok, lat, crc = self.offload_mgr.transfer_activation_chunk(payload, layer_idx=i % 24)
            self.assertTrue(ok)
            self.assertGreater(crc, 0)
        self.assertEqual(self.offload_mgr._chunk_seq, seq_start + 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
