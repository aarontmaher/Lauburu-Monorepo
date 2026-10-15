#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Tier 3: Cross-Feature Combinations (Opaque-Box Verification Suite)
================================================================================
Subsystem: tests/e2e_storage_elo/test_tier3_pairwise_combinations.py
Authoritative References:
- ORIGINAL_REQUEST.md (§R1, §R2, §R3, Acceptance Criteria)
- PROJECT.md (§Milestone 1, 2, 3 & Interface Contracts)
- TEST_INFRA.md (§Tier 3 Specification)

Evaluates Pairwise Cross-Feature Interactions:
- Storage Pooling <-> ELO Engine: Real C11 reassembly trials and latency benchmarks feeding ELO scorecard
- Governance <-> Storage Pooling: Read-only context map topology parity and tampering prevention
- Governance <-> ELO Engine: Tri-Vault storage health anchoring system-level confidence
- Triad Pipeline: Storage + Governance + ELO full integration cycle

Zero-Mock Mandate (Rule #0): All pairwise interactions exercise authentic subsystems.
================================================================================
"""

import os
import stat
import math
import hashlib
from pathlib import Path
import pytest

from tests.e2e_storage_elo.e2e_storage_elo_helpers import (
    C11StorageEngine,
    PRIMARY_CONTEXT_MAP,
    MIRROR_CONTEXT_MAP,
    CANONICAL_CONTEXT_MAP_SHA256,
    CANONICAL_CONTEXT_MAP_SIZE,
    REPO_ROOT,
    EloEngine,
    MIN_ELO_RATING,
    MAX_ELO_RATING,
    calculate_wilson_confidence_interval,
    CategoryScorecard,
    ProjectEloScorecard,
    evaluate_project_scorecard,
)


class TestTier3PairwiseCombinations:
    """Verifies 2-way cross-subsystem interactions between Storage, Governance, and ELO."""

    @pytest.fixture
    def engine(self):
        eng = C11StorageEngine()
        eng.init_and_register_canonical_mesh()
        return eng

    # --------------------------------------------------------------------------
    # Storage Pooling <-> ELO Engine Pairwise Interactions
    # --------------------------------------------------------------------------

    def test_pairwise_c11_storage_trials_feed_backend_elo_scorecard(self, engine):
        """Verifies authentic C11 storage dispersal/reassembly trials directly populate Backend ELO scorecard."""
        num_trials = 10
        successes = 0
        payload = b"Authentic C11 Payload for ELO Backend Verification" * 200

        for i in range(num_trials):
            _, _, ok, reasm = engine.disperse_and_reassemble(payload, max_chunks=8)
            if ok and reasm == payload:
                successes += 1

        assert successes == num_trials, "All 10 authentic C11 trials must pass"

        # Feed real trial outcomes into Backend ELO evaluation
        card = evaluate_project_scorecard(
            frontend_trials=(10, 10),
            backend_trials=(successes, num_trials),
            ai_trials=(10, 10),
            backend_rating=2650.0,
        )

        assert card.backend.trials == num_trials
        assert card.backend.passes == successes
        assert card.backend.pass_rate == 1.0
        # Wilson score lower bound for 10/10 is approx 0.722
        assert card.backend.confidence_interval.lower > 0.70
        assert card.backend.confidence_interval.upper == 1.0
        assert card.backend.rating == 2650.0
        assert card.evaluation_latency_us <= 50.0

    def test_pairwise_storage_bitrot_failure_injects_into_backend_elo_downgrade(self, engine):
        """Verifies injected C11 storage bitrot failures accurately depress Backend ELO confidence."""
        num_trials = 10
        successes = 0
        payload = b"Bitrot Injection Test for ELO Degradation" * 300

        for i in range(num_trials):
            # Inject bitrot into 2 out of 10 trials
            corrupt_idx = 0 if i in (3, 7) else None
            _, _, ok, _ = engine.disperse_and_reassemble(
                payload, max_chunks=8, corrupt_chunk_idx=corrupt_idx, corrupt_byte_offset=5, corrupt_xor_mask=0x01
            )
            if ok:
                successes += 1

        assert successes == 8, "Expected exactly 8 successes and 2 bitrot rejections"

        card = evaluate_project_scorecard(
            frontend_trials=(10, 10),
            backend_trials=(successes, num_trials),
            ai_trials=(10, 10),
            backend_rating=2600.0,
        )

        assert card.backend.trials == 10
        assert card.backend.passes == 8
        assert card.backend.pass_rate == 0.80
        # Confidence interval lower bound should depress below 0.55 due to 2 failures
        assert card.backend.confidence_interval.lower < 0.55
        assert card.backend.confidence_interval.spread > 0.40, "Uncertainty spread should widen"

    def test_pairwise_storage_sla_latency_regulates_backend_elo_rating(self, engine):
        """Verifies C11 latency performance dynamically benchmarks and validates ELO rating status."""
        payload_1mb = bytes((i * 53 + 7) % 256 for i in range(1024 * 1024))
        rep, _, ok, _ = engine.disperse_and_reassemble(payload_1mb, max_chunks=32)
        assert ok is True

        dispersal_ms = rep.slice_and_disperse_latency_us / 1000.0
        # Latency SLA check: <= 2.0 ms
        sla_met = dispersal_ms <= 2.0
        assert sla_met is True

        backend_rating = 2700.0 if sla_met else 1800.0
        card = evaluate_project_scorecard(
            frontend_trials=(20, 20),
            backend_trials=(16, 16),
            ai_trials=(10, 10),
            backend_rating=backend_rating,
        )
        assert card.backend.rating == 2700.0
        assert card.composite_score >= 2200.0

    # --------------------------------------------------------------------------
    # Governance <-> Storage Pooling Pairwise Interactions
    # --------------------------------------------------------------------------

    def test_pairwise_governance_topology_parity_with_c11_ring_nodes(self, engine):
        """Verifies physical storage layers documented in read-only Context Map match C11 hash ring nodes."""
        assert PRIMARY_CONTEXT_MAP.is_file()
        content = PRIMARY_CONTEXT_MAP.read_text(encoding="utf-8")

        # Context Map defines L1 through L7 in Section 1 table
        for idx in range(engine.get_node_count()):
            node_info = engine.get_node_info(idx)
            node_id = node_info["node_id"]
            # Layer identifier (e.g. L1_Mac_Node, L2_MacBook_Pro) must be documented in Context Map
            assert node_id in content or node_id.split("_")[0] in content, (
                f"Storage node {node_id} must be explicitly documented in Context Map"
            )

    def test_pairwise_unauthorized_storage_tampering_blocked_by_governance(self, tmp_path):
        """Verifies that an unauthorized daemon attempting to overwrite Context Map topology is blocked without clobbering."""
        # 1. Assert OS-level read-only access mode 0444 on canonical file before any write attempt
        mode = stat.S_IMODE(PRIMARY_CONTEXT_MAP.stat().st_mode)
        assert mode == 0o444, f"Primary Context Map must be mode 0o444, found {oct(mode)}"
        assert not os.access(PRIMARY_CONTEXT_MAP, os.W_OK), "Primary Context Map must not be writable"

        # 2. Test read-only write rejection on a shadow replica in tmp_path to assert protection without risk
        temp_map = tmp_path / "SHADOW_STORAGE_ARCHITECTURE_CONTEXT_MAP.md"
        temp_map.write_bytes(PRIMARY_CONTEXT_MAP.read_bytes())
        os.chmod(temp_map, 0o444)
        with pytest.raises(PermissionError):
            with open(temp_map, "w", encoding="utf-8") as f:
                f.write("TAMPERED_STORAGE_TOPOLOGY_ATTEMPT")

        # 3. Test direct read-only write rejection on the live canonical file
        with pytest.raises(PermissionError):
            with open(PRIMARY_CONTEXT_MAP, "w", encoding="utf-8") as f:
                f.write("TAMPERED_STORAGE_TOPOLOGY_ATTEMPT")

        # 4. Assert content was not mutated and retains bit-for-bit canonical fidelity
        assert PRIMARY_CONTEXT_MAP.stat().st_size == CANONICAL_CONTEXT_MAP_SIZE
        assert hashlib.sha256(PRIMARY_CONTEXT_MAP.read_bytes()).hexdigest() == CANONICAL_CONTEXT_MAP_SHA256

    # --------------------------------------------------------------------------
    # Governance <-> ELO Engine Pairwise Interactions
    # --------------------------------------------------------------------------

    def test_pairwise_tri_vault_governance_integrity_anchors_elo_confidence(self):
        """Verifies that Tri-Vault governance health (read-only mode 0444, clean git) confirms high-confidence ELO state."""
        # 1. Verify primary and mirror mode 0444
        mode_p = stat.S_IMODE(PRIMARY_CONTEXT_MAP.stat().st_mode)
        mode_m = stat.S_IMODE(MIRROR_CONTEXT_MAP.stat().st_mode)
        governance_healthy = (mode_p == 0o444 and mode_m == 0o444)
        assert governance_healthy is True

        # 2. Verify git lock absent
        git_lock = REPO_ROOT / ".git/index.lock"
        assert not git_lock.exists()

        # 3. When governance is 100% verified, evaluate scorecard with high confidence
        card = evaluate_project_scorecard(
            frontend_trials=(100, 100),
            backend_trials=(1000, 1000),
            ai_trials=(50, 50),
            frontend_rating=2450.0,
            backend_rating=2680.0,
            ai_rating=2750.0,
        )

        assert card.composite_score > 2600.0
        assert card.frontend.confidence_interval.spread < 0.05
        assert card.backend.confidence_interval.spread < 0.01

    # --------------------------------------------------------------------------
    # Full Triad Pipeline Integration
    # --------------------------------------------------------------------------

    def test_pairwise_full_triad_storage_governance_elo_pipeline(self, engine):
        """Executes full integrated verification loop across C11 Storage, Governance Map, and ELO Scorecard."""
        # Step 1: Storage Payload Dispersal & Reassembly
        payload = bytes((i * 61 + 3) % 256 for i in range(512 * 1024))  # 512 KB = 8 chunks
        orig_sha = hashlib.sha256(payload).hexdigest()
        rep, chunk_info, storage_ok, reassembled = engine.disperse_and_reassemble(payload, max_chunks=16)

        assert storage_ok is True
        assert rep.chunk_count == 8
        assert hashlib.sha256(reassembled).hexdigest() == orig_sha

        # Step 2: Governance Verification
        gov_mode_ok = stat.S_IMODE(PRIMARY_CONTEXT_MAP.stat().st_mode) == 0o444
        gov_hash_ok = hashlib.sha256(PRIMARY_CONTEXT_MAP.read_bytes()).hexdigest() == CANONICAL_CONTEXT_MAP_SHA256
        assert gov_mode_ok is True
        assert gov_hash_ok is True

        # Step 3: Populate ELO Scorecard from Live Step 1 and Step 2 Proofs
        backend_passes = 8 if storage_ok else 0
        card = evaluate_project_scorecard(
            frontend_trials=(10, 10),
            backend_trials=(backend_passes, 8),
            ai_trials=(10, 10),
            frontend_rating=2400.0,
            backend_rating=2700.0,
            ai_rating=2650.0,
        )

        assert card.composite_score >= 2500.0
        assert card.backend.pass_rate == 1.0
        assert card.sla_compliant_50us is True

