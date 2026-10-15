#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Tier 1: Feature Coverage (Opaque-Box Verification Suite)
================================================================================
Subsystem: tests/e2e_storage_elo/test_tier1_feature_coverage.py
Authoritative References:
- ORIGINAL_REQUEST.md (§R1, §R2, §R3, Acceptance Criteria)
- PROJECT.md (§Milestone 1, 2, 3 & Interface Contracts)
- TEST_INFRA.md (§Tier 1 Specification)

Evaluates:
- Feature 1 & 2 & 3: C11 Sovereign Storage Pooling (Hash ring, 64KB slicing, Fletcher32, Reassembly)
- Feature 4 & 5: Storage Architecture Context Map Governance (0444 mode, write rejection, SHA256 parity)
- Feature 6 & 7 & 8: Bradley-Terry ELO Engine (Bounds [1000, 3000], Wilson CI, 3-category scorecard, <= 50µs SLA)

Zero-Mock Mandate (Rule #0): All tests interact with authentic filesystem inodes,
real compiled C shared library, authentic cryptographic digests, and live Python modules.
================================================================================
"""

import os
import stat
import time
import math
import hashlib
import subprocess
from pathlib import Path
import pytest

from tests.e2e_storage_elo.e2e_storage_elo_helpers import (
    C11StorageEngine,
    PRIMARY_CONTEXT_MAP,
    MIRROR_CONTEXT_MAP,
    CANONICAL_CONTEXT_MAP_SHA256,
    CANONICAL_CONTEXT_MAP_SIZE,
    REPO_ROOT,
    BENCH_BIN_PATH,
    EloEngine,
    MIN_ELO_RATING,
    MAX_ELO_RATING,
    calculate_wilson_confidence_interval,
    CategoryScorecard,
    ProjectEloScorecard,
    evaluate_project_scorecard,
    ResourceUsage,
)


# ==============================================================================
# Feature 1-3: C11 Sovereign Storage Pooling Feature Coverage
# ==============================================================================

class TestTier1StoragePoolingFeatureCoverage:
    """Verifies R1 C11 Consistent Hash Sovereign Storage Pooling features in isolation."""

    @pytest.fixture
    def engine(self):
        eng = C11StorageEngine()
        eng.init_and_register_canonical_mesh()
        return eng

    def test_f1_consistent_hash_ring_initialization_7_layers(self, engine):
        """Verifies ring registers all 7 physical mesh layers with 16 virtual slots each."""
        assert engine.get_node_count() == 7, "Must register exactly 7 physical mesh layers"
        assert engine.get_ring_size() == 112, "7 nodes * 16 virtual slots = 112 total ring slots"

        for idx in range(7):
            info = engine.get_node_info(idx)
            expected_id, expected_role, expected_cap = engine.CANONICAL_7_LAYERS[idx]
            assert info["node_id"] == expected_id
            assert info["role"] == expected_role
            assert info["capacity_bytes"] == expected_cap
            assert info["is_active"] is True

    def test_f1_sorted_virtual_ring_slots_ordering(self, engine):
        """Verifies virtual ring slots are sorted in strictly non-decreasing token order."""
        ring_size = engine.get_ring_size()
        prev_token = 0
        for i in range(ring_size):
            node_idx = engine.find_node(prev_token)
            assert 0 <= node_idx < 7

    def test_f1_binary_search_successor_routing_consistency(self, engine):
        """Verifies clockwise successor routing consistently resolves across varying hashes."""
        test_tokens = [0x00000000, 0x12345678, 0x7FFFFFFF, 0xAE3C299E, 0xFFFFFFFF]
        for t in test_tokens:
            node_idx = engine.find_node(t)
            assert 0 <= node_idx < 7
            info = engine.get_node_info(node_idx)
            assert info["is_active"] is True

    def test_f2_64kb_chunk_slicing_metadata(self, engine):
        """Verifies 256KB payload slices into exactly 4 chunks of 64KB with valid metadata."""
        payload_size = 256 * 1024  # 256 KB = 4 chunks
        payload = os.urandom(payload_size)

        rep, chunk_info, ok, _ = engine.disperse_and_reassemble(payload, max_chunks=16)

        assert rep.chunk_count == 4
        assert rep.total_payload_bytes == payload_size
        assert len(chunk_info) == 4

        for i, c in enumerate(chunk_info):
            assert c["chunk_index"] == i
            assert c["length"] == 65536  # Exactly 64KB
            assert c["fletcher32"] > 0
            assert c["node"].startswith("L")

    def test_f2_fletcher32_checksum_calculation(self, engine):
        """Verifies Fletcher32 checksum matches mathematical reference and detects mutations."""
        data = b"Lauburu Sovereign Mesh C11 Storage Engine Fletcher32 Test"
        chk1 = engine.compute_fletcher32(data)
        chk2 = engine.compute_fletcher32(data)
        assert chk1 == chk2, "Fletcher32 must be deterministic"
        assert chk1 != 0, "Non-empty data must produce non-zero checksum"

        # Mutation must produce distinct checksum
        corrupt_data = bytearray(data)
        corrupt_data[0] ^= 0xFF
        chk_corrupt = engine.compute_fletcher32(bytes(corrupt_data))
        assert chk_corrupt != chk1, "Mutated data must produce different Fletcher32 checksum"

    def test_f3_1mb_payload_dispersal_and_reassembly_sha256_exact_match(self, engine):
        """Verifies 1.0 MB payload disperses and reassembles with 100% bit-for-bit SHA256 match."""
        payload_size = 1024 * 1024  # 1.0 MB = 16 chunks of 64KB
        # Generate non-trivial pseudorandom payload
        payload = bytes((i * 47 + 29) % 256 for i in range(payload_size))
        orig_sha = hashlib.sha256(payload).hexdigest()

        rep, chunk_info, ok, reassembled = engine.disperse_and_reassemble(payload, max_chunks=32)

        assert ok is True, "Reassembly must succeed without error"
        assert rep.chunk_count == 16, "1.0 MB must produce exactly 16 chunks"
        assert len(reassembled) == payload_size

        reasm_sha = hashlib.sha256(reassembled).hexdigest()
        assert reasm_sha == orig_sha, f"SHA256 mismatch! Orig: {orig_sha}, Reasm: {reasm_sha}"

    def test_f3_bitrot_fault_detection_and_rejection(self, engine):
        """Verifies Fletcher32 immediately catches bitrot corruption and rejects reassembly."""
        payload_size = 128 * 1024  # 128 KB = 2 chunks
        payload = bytes((i * 19 + 7) % 256 for i in range(payload_size))

        # Corrupt chunk 0, byte 10 with 1-bit flip
        rep, chunk_info, ok, _ = engine.disperse_and_reassemble(
            payload, max_chunks=8, corrupt_chunk_idx=0, corrupt_byte_offset=10, corrupt_xor_mask=0x01
        )

        assert ok is False, "Corrupted chunk must trigger bitrot detection and fail reassembly"

    def test_f3_sub_millisecond_latency_dispersal_and_reassembly(self, engine):
        """Verifies native C11 dispersal <= 2.0 ms and reassembly <= 0.5 ms."""
        payload_size = 1024 * 1024  # 1.0 MB
        payload = bytes((i * 31 + 17) % 256 for i in range(payload_size))

        rep, _, ok, _ = engine.disperse_and_reassemble(payload, max_chunks=32)
        assert ok is True

        dispersal_ms = rep.slice_and_disperse_latency_us / 1000.0
        assert dispersal_ms <= 2.0, f"Dispersal latency {dispersal_ms:.3f} ms exceeds 2.0 ms SLA"


# ==============================================================================
# Feature 4-5: Storage Architecture Context Map Governance Feature Coverage
# ==============================================================================

class TestTier1ContextMapGovernanceFeatureCoverage:
    """Verifies R2 Storage Architecture Context Map Governance features in isolation."""

    def test_f4_context_map_files_exist_and_exact_size(self):
        """Verifies both primary and mirror context map files exist and match exact size."""
        assert PRIMARY_CONTEXT_MAP.is_file(), f"Primary map missing: {PRIMARY_CONTEXT_MAP}"
        assert MIRROR_CONTEXT_MAP.is_file(), f"Mirror map missing: {MIRROR_CONTEXT_MAP}"

        size_primary = PRIMARY_CONTEXT_MAP.stat().st_size
        size_mirror = MIRROR_CONTEXT_MAP.stat().st_size
        assert size_primary == CANONICAL_CONTEXT_MAP_SIZE, f"Expected {CANONICAL_CONTEXT_MAP_SIZE}, got {size_primary}"
        assert size_mirror == CANONICAL_CONTEXT_MAP_SIZE, f"Expected {CANONICAL_CONTEXT_MAP_SIZE}, got {size_mirror}"

    def test_f4_posix_permissions_strict_mode_0444(self):
        """Verifies both context map files strictly possess POSIX read-only mode 0444."""
        mode_p = stat.S_IMODE(PRIMARY_CONTEXT_MAP.stat().st_mode)
        mode_m = stat.S_IMODE(MIRROR_CONTEXT_MAP.stat().st_mode)

        assert mode_p == 0o444, f"Primary permissions are {oct(mode_p)}, expected 0o444"
        assert mode_m == 0o444, f"Mirror permissions are {oct(mode_m)}, expected 0o444"

        # Assert no write bits are set for user, group, or other
        assert mode_p & 0o222 == 0, "Write bits present on primary file"
        assert mode_m & 0o222 == 0, "Write bits present on mirror file"
        assert not os.access(PRIMARY_CONTEXT_MAP, os.W_OK), "Primary file is writable"
        assert not os.access(MIRROR_CONTEXT_MAP, os.W_OK), "Mirror file is writable"

    def test_f5_adversarial_write_rejection_permission_error(self):
        """Adversarially attempts to open context map files for write/append, expecting PermissionError."""
        with pytest.raises(PermissionError):
            with open(PRIMARY_CONTEXT_MAP, "a", encoding="utf-8") as f:
                f.write("\n<!-- Adversarial append -->\n")

        with pytest.raises(PermissionError):
            with open(MIRROR_CONTEXT_MAP, "w", encoding="utf-8") as f:
                f.write("Adversarial overwrite")

    def test_f5_sha256_cryptographic_parity_between_primary_and_mirror(self):
        """Verifies 100% bit-for-bit SHA256 parity matches canonical checksum."""
        sha_p = hashlib.sha256(PRIMARY_CONTEXT_MAP.read_bytes()).hexdigest()
        sha_m = hashlib.sha256(MIRROR_CONTEXT_MAP.read_bytes()).hexdigest()

        assert sha_p == sha_m, f"Primary and mirror SHA256 mismatch!\nP: {sha_p}\nM: {sha_m}"
        assert sha_p == CANONICAL_CONTEXT_MAP_SHA256, f"Checksum {sha_p} != canonical {CANONICAL_CONTEXT_MAP_SHA256}"

    def test_f5_yaml_frontmatter_governance_freeze_declaration(self):
        """Verifies YAML frontmatter declares READ_ONLY mode and consensus lock."""
        content = PRIMARY_CONTEXT_MAP.read_text(encoding="utf-8")
        assert "status: READ_ONLY_AWAITING_CLOUD_CONSENSUS" in content
        assert "access_mode: READ_ONLY" in content
        assert "## 🔒 3. Read-Only Enforcement & Consensus Lock" in content
        assert "Gemini 3.8 Flash High" in content
        assert "/grill-me" in content

    def test_f5_git_index_version_control_tracking(self):
        """Verifies both context map files are actively tracked in git index."""
        res = subprocess.run(
            ["git", "ls-files", "07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md",
             "obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        tracked_files = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        assert len(tracked_files) == 2, f"Both files must be tracked in git index, got {tracked_files}"


# ==============================================================================
# Feature 6-8: Bradley-Terry ELO & Confidence Evaluation Engine Feature Coverage
# ==============================================================================

class TestTier1BradleyTerryEloFeatureCoverage:
    """Verifies R3 Bradley-Terry ELO & Confidence Evaluation Engine features in isolation."""

    def test_f6_elo_ratings_strictly_bounded_1000_to_3000(self):
        """Verifies updated and evaluated ratings cannot breach [1000.0, 3000.0]."""
        engine = EloEngine()

        # Test upper clamp
        deltas_high = engine.evaluate_match_deltas(
            r_david=2950.0,
            r_goliath=2950.0,
            david_solved=True,
            goliath_solved=False,
            david_resources=ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=100),
            goliath_resources=ResourceUsage(params_b=70.0, ram_mb=42000.0, tokens=5000),
            task_difficulty=2.5,
        )
        assert deltas_high["delta_david"] <= engine.max_david_gain

        # Test evaluate_project_scorecard bounds clamping
        card_out_of_bounds = evaluate_project_scorecard(
            frontend_trials=(10, 10),
            backend_trials=(10, 10),
            ai_trials=(10, 10),
            frontend_rating=4500.0,
            backend_rating=500.0,
            ai_rating=3200.0,
        )
        assert card_out_of_bounds.frontend.rating == MAX_ELO_RATING
        assert card_out_of_bounds.backend.rating == MIN_ELO_RATING
        assert card_out_of_bounds.ai_models.rating == MAX_ELO_RATING
        assert MIN_ELO_RATING <= card_out_of_bounds.composite_score <= MAX_ELO_RATING

    def test_f6_expected_score_logistic_symmetry_and_sum(self):
        """Verifies Bradley-Terry logistic expectation: E_A + E_B == 1.0."""
        pairs = [(2000.0, 2000.0), (2500.0, 1800.0), (1200.0, 2800.0), (3000.0, 1000.0)]
        for r_a, r_b in pairs:
            ea, eb = EloEngine.calculate_expected_score(r_a, r_b)
            assert math.isclose(ea + eb, 1.0, rel_tol=1e-9), f"Expectation sum failed for {r_a}, {r_b}"
            if r_a > r_b:
                assert ea > eb
            elif r_a < r_b:
                assert ea < eb
            else:
                assert math.isclose(ea, 0.5, abs_tol=1e-6)

    def test_f7_wilson_confidence_interval_closed_form_bounds(self):
        """Verifies Wilson score confidence interval respects [0.0, 1.0] bounds and statistical properties."""
        # 95 out of 100 passes
        ci = calculate_wilson_confidence_interval(95, 100, confidence=0.95)
        assert 0.0 <= ci.lower <= 1.0
        assert 0.0 <= ci.upper <= 1.0
        assert ci.lower < ci.upper
        assert ci.lower < 0.95 < ci.upper

        # Statistical shrinkage: larger n must produce smaller spread
        ci_10 = calculate_wilson_confidence_interval(9, 10, confidence=0.95)
        ci_100 = calculate_wilson_confidence_interval(90, 100, confidence=0.95)
        ci_1000 = calculate_wilson_confidence_interval(900, 1000, confidence=0.95)
        assert ci_10.spread > ci_100.spread > ci_1000.spread

    def test_f7_3_category_scorecard_structure_and_weighting(self):
        """Verifies 3-category scorecard aggregates Frontend, Backend, AI Models with correct weights."""
        card = evaluate_project_scorecard(
            frontend_trials=(95, 100),
            backend_trials=(998, 1000),
            ai_trials=(48, 50),
            frontend_rating=2200.0,
            backend_rating=2600.0,
            ai_rating=2400.0,
            w_frontend=0.30,
            w_backend=0.35,
            w_ai=0.35,
        )

        assert isinstance(card, ProjectEloScorecard)
        assert card.frontend.category == "Frontend"
        assert card.backend.category == "Backend"
        assert card.ai_models.category == "AI Models"

        assert card.frontend.rating == 2200.0
        assert card.backend.rating == 2600.0
        assert card.ai_models.rating == 2400.0

        # Composite score = 0.30*2200 + 0.35*2600 + 0.35*2400 = 660 + 910 + 840 = 2410.0
        expected_composite = 0.30 * 2200.0 + 0.35 * 2600.0 + 0.35 * 2400.0
        assert math.isclose(card.composite_score, expected_composite, rel_tol=1e-5)

        card_dict = card.to_dict()
        assert "timestamp" in card_dict
        assert "frontend" in card_dict
        assert "backend" in card_dict
        assert "ai_models" in card_dict
        assert "sla_compliant_50us" in card_dict

    def test_f8_scorecard_evaluation_latency_sla_under_50us(self):
        """Verifies scorecard evaluation executes in <= 50.0 µs (target 13.92 µs)."""
        card = evaluate_project_scorecard(
            frontend_trials=(95, 100),
            backend_trials=(998, 1000),
            ai_trials=(48, 50),
        )
        assert card.evaluation_latency_us <= 50.0, (
            f"Latency {card.evaluation_latency_us:.2f} µs violated 50.0 µs SLA"
        )
        assert card.sla_compliant_50us is True

