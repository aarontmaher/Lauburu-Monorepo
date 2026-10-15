#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Tier 2: Boundary Value Analysis & Corner Cases (Opaque-Box Verification Suite)
================================================================================
Subsystem: tests/e2e_storage_elo/test_tier2_boundary_corner.py
Authoritative References:
- ORIGINAL_REQUEST.md (§R1, §R2, §R3, Acceptance Criteria)
- PROJECT.md (§Milestone 1, 2, 3 & Interface Contracts)
- TEST_INFRA.md (§Tier 2 Specification)

Evaluates:
- Storage Pooling: 0-byte payload, 1-byte payload, exact 64KB/128KB boundaries, odd-byte Fletcher32 trailing bitrot, max nodes boundary
- Governance: Write modes ("w", "a", "r+", "wb", "ab"), truncation rejection, disk headroom threshold, distinct inode parity
- Bradley-Terry ELO: Extreme delta R (100,000 overflow guard), Wilson CI (n=0, k=0, k=n, k>n), zero-weight scorecard fallback, rating clamps [1000, 3000]

Zero-Mock Mandate (Rule #0): Real boundary values evaluated against authentic code.
================================================================================
"""

import os
import stat
import math
import shutil
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
    ResourceUsage,
)


# ==============================================================================
# Feature 1-3: Storage Pooling Boundary & Corner Cases
# ==============================================================================

class TestTier2StoragePoolingBoundaryCases:
    """Verifies boundary values, extreme lengths, and edge conditions for C11 Storage Pooling."""

    @pytest.fixture
    def engine(self):
        eng = C11StorageEngine()
        eng.init_and_register_canonical_mesh()
        return eng

    def test_bva_storage_zero_byte_empty_payload(self, engine):
        """Verifies dispersing 0-byte payload handles safely and reassembly rejects 0-chunk payload."""
        empty_payload = b""
        rep, chunk_info, ok, reassembled = engine.disperse_and_reassemble(empty_payload, max_chunks=8)
        assert rep.total_payload_bytes == 0
        assert rep.chunk_count == 0
        assert len(chunk_info) == 0
        assert ok is False, "Reassembly of 0 chunks must return False"
        assert len(reassembled) == 0

    def test_bva_storage_single_byte_payload(self, engine):
        """Verifies 1-byte payload generates 1 chunk, Fletcher32 pads safely, and reassembles exactly."""
        single_byte = b"\xA5"
        rep, chunk_info, ok, reassembled = engine.disperse_and_reassemble(single_byte, max_chunks=8)
        assert rep.total_payload_bytes == 1
        assert rep.chunk_count == 1
        assert chunk_info[0]["length"] == 1
        assert ok is True
        assert reassembled == single_byte

    def test_bva_storage_exact_64kb_and_128kb_chunk_boundaries(self, engine):
        """Verifies exact 65,536-byte and 131,072-byte payloads produce exactly 1 and 2 chunks."""
        # Exact 64 KB
        p64 = bytes(i % 256 for i in range(65536))
        rep64, info64, ok64, reasm64 = engine.disperse_and_reassemble(p64, max_chunks=8)
        assert rep64.chunk_count == 1
        assert info64[0]["length"] == 65536
        assert ok64 is True
        assert reasm64 == p64

        # Exact 128 KB
        p128 = bytes((i * 3) % 256 for i in range(131072))
        rep128, info128, ok128, reasm128 = engine.disperse_and_reassemble(p128, max_chunks=8)
        assert rep128.chunk_count == 2
        assert info128[0]["length"] == 65536
        assert info128[1]["length"] == 65536
        assert ok128 is True
        assert reasm128 == p128

    def test_bva_storage_odd_length_trailing_byte_corruption_caught(self, engine):
        """Verifies odd-length chunk trailing byte is checksummed and caught upon bitrot."""
        odd_len = 65535  # Odd length (64KB - 1 byte)
        payload = bytes((i * 7 + 11) % 256 for i in range(odd_len))

        # Corrupt the very last byte (offset 65534)
        rep, _, ok, _ = engine.disperse_and_reassemble(
            payload, max_chunks=8, corrupt_chunk_idx=0, corrupt_byte_offset=odd_len - 1, corrupt_xor_mask=0x80
        )
        assert ok is False, "Corruption in trailing odd byte of Fletcher32 must be detected"

    def test_bva_storage_node_capacity_overflow_and_max_nodes_clamp(self):
        """Verifies adding beyond MAX_STORAGE_NODES (8 nodes) is rejected with False."""
        eng = C11StorageEngine()
        eng.lib.storage_pool_init_ring()

        # Add 8 nodes (maximum capacity)
        for i in range(8):
            ok = eng.lib.storage_pool_add_node(f"Node_{i}".encode("utf-8"), b"Test Role", 1024 * 1024)
            assert ok is True, f"Node {i} must be added successfully"

        assert eng.get_node_count() == 8

        # 9th node must be rejected
        ok_9 = eng.lib.storage_pool_add_node(b"Node_9", b"Overflow Role", 1024 * 1024)
        assert ok_9 is False, "Adding 9th node beyond MAX_STORAGE_NODES (8) must return False"
        assert eng.get_node_count() == 8

    def test_bva_storage_unregistered_empty_ring_handling(self):
        """Verifies clean handling when finding nodes on an empty ring."""
        eng = C11StorageEngine()
        eng.lib.storage_pool_init_ring()
        assert eng.get_node_count() == 0
        assert eng.get_ring_size() == 0

        # find_node on empty ring must safely return 0 without segfault
        node_idx = eng.find_node(0x12345678)
        assert node_idx == 0


# ==============================================================================
# Feature 4-5: Context Map Governance Boundary & Corner Cases
# ==============================================================================

class TestTier2ContextMapGovernanceBoundaryCases:
    """Verifies edge conditions, multiple write modes, and filesystem boundaries for Governance."""

    def test_bva_governance_multiple_write_modes_rejected(self):
        """Verifies multiple file write modes raise PermissionError under mode 0444."""
        modes = ["w", "a", "r+", "w+", "a+", "wb", "ab"]
        for m in modes:
            with pytest.raises(PermissionError):
                with open(PRIMARY_CONTEXT_MAP, m):
                    pass
            with pytest.raises(PermissionError):
                with open(MIRROR_CONTEXT_MAP, m):
                    pass

    def test_bva_governance_os_truncate_rejection(self):
        """Verifies os.truncate on mode 0444 files raises PermissionError."""
        with pytest.raises(PermissionError):
            os.truncate(str(PRIMARY_CONTEXT_MAP), 100)
        with pytest.raises(PermissionError):
            os.truncate(str(MIRROR_CONTEXT_MAP), 100)

    def test_bva_governance_file_stat_st_size_exact_parity(self):
        """Verifies exact file metadata (st_size, st_mode) parity between primary and mirror."""
        st_p = PRIMARY_CONTEXT_MAP.stat()
        st_m = MIRROR_CONTEXT_MAP.stat()

        assert st_p.st_size == st_m.st_size == CANONICAL_CONTEXT_MAP_SIZE
        assert stat.S_IMODE(st_p.st_mode) == stat.S_IMODE(st_m.st_mode) == 0o444
        # Assert they are distinct filesystem inodes (not a hardlink)
        assert st_p.st_ino != st_m.st_ino, "Primary and mirror should be distinct mirrored inodes"

    def test_bva_governance_tri_vault_disk_headroom_boundary(self):
        """Verifies host free disk space satisfies the mandatory >= 5.0 GB threshold."""
        free_bytes = shutil.disk_usage(str(REPO_ROOT)).free
        free_gb = free_bytes / (1024 ** 3)
        assert free_gb >= 5.0, f"Host free disk space {free_gb:.2f} GB below mandatory 5.0 GB threshold"

    def test_bva_governance_obsidian_master_index_wikilinks_boundary(self):
        """Verifies Obsidian Index.md contains all mandatory canonical Wikilinks."""
        index_path = REPO_ROOT / "obsidian_vault/Index.md"
        assert index_path.is_file()
        content = index_path.read_text(encoding="utf-8")
        mandatory_wikilinks = [
            "[[Index]]",
            "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
            "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
        ]
        for link in mandatory_wikilinks:
            assert link in content, f"Missing mandatory Wikilink {link} in {index_path}"


# ==============================================================================
# Feature 6-8: Bradley-Terry ELO & Confidence Boundary Cases
# ==============================================================================

class TestTier2BradleyTerryEloBoundaryCases:
    """Verifies numerical limits, extreme rating bounds, and edge cases in ELO & Wilson intervals."""

    def test_bva_elo_extreme_rating_differences_overflow_guard(self):
        """Verifies rating differences up to 100,000 do not raise OverflowError in 10^(diff/400)."""
        extreme_pairs = [
            (3000.0, 1000.0),
            (1000.0, 3000.0),
            (100000.0, 0.0),
            (0.0, 100000.0),
            (-50000.0, 50000.0),
        ]
        for r_a, r_b in extreme_pairs:
            ea, eb = EloEngine.calculate_expected_score(r_a, r_b)
            assert math.isclose(ea + eb, 1.0, rel_tol=1e-9)
            assert 0.0 <= ea <= 1.0
            assert 0.0 <= eb <= 1.0

    def test_bva_wilson_ci_zero_trials_uninformative_prior(self):
        """Verifies n=0 safely defaults to uninformative prior [0.0, 1.0] without ZeroDivisionError."""
        ci_0_0 = calculate_wilson_confidence_interval(0, 0)
        assert ci_0_0.lower == 0.0
        assert ci_0_0.upper == 1.0
        assert ci_0_0.spread == 1.0

        ci_neg = calculate_wilson_confidence_interval(-5, -1)
        assert ci_neg.lower == 0.0
        assert ci_neg.upper == 1.0

    def test_bva_wilson_ci_zero_passes_boundary(self):
        """Verifies 0 passes out of n trials produces lower bound of exactly 0.0 and positive upper."""
        ci_0_50 = calculate_wilson_confidence_interval(0, 50, confidence=0.95)
        assert ci_0_50.lower == 0.0
        assert 0.0 < ci_0_50.upper < 0.15
        assert ci_0_50.spread == ci_0_50.upper

    def test_bva_wilson_ci_perfect_100_percent_passes_boundary(self):
        """Verifies n passes out of n trials produces upper bound of exactly 1.0 and non-zero uncertainty."""
        ci_50_50 = calculate_wilson_confidence_interval(50, 50, confidence=0.95)
        assert ci_50_50.upper == 1.0
        assert 0.85 < ci_50_50.lower < 1.0
        assert ci_50_50.spread > 0.0, "Even 100% pass rate must retain non-zero statistical uncertainty"

    def test_bva_wilson_ci_clamping_passes_exceeding_trials(self):
        """Verifies passes k > n is clamped to n without raising ValueError."""
        ci_clamped = calculate_wilson_confidence_interval(150, 100, confidence=0.95)
        assert ci_clamped.upper == 1.0
        assert 0.0 <= ci_clamped.lower <= 1.0

    def test_bva_scorecard_zero_weights_sum_fallback(self):
        """Verifies zero sum of category weights falls back to simple unweighted average."""
        card = evaluate_project_scorecard(
            frontend_trials=(10, 10),
            backend_trials=(10, 10),
            ai_trials=(10, 10),
            frontend_rating=2100.0,
            backend_rating=2400.0,
            ai_rating=2700.0,
            w_frontend=0.0,
            w_backend=0.0,
            w_ai=0.0,
        )
        # Average of (2100 + 2400 + 2700) / 3 = 2400.0
        assert math.isclose(card.composite_score, 2400.0, rel_tol=1e-5)

    def test_bva_scorecard_extreme_clamping_both_sides(self):
        """Verifies ratings below MIN_ELO or above MAX_ELO are clamped on both sides."""
        card = evaluate_project_scorecard(
            frontend_trials=(5, 10),
            backend_trials=(5, 10),
            ai_trials=(5, 10),
            frontend_rating=9999.0,   # > 3000
            backend_rating=-2000.0,   # < 1000
            ai_rating=2000.0,
        )
        assert card.frontend.rating == MAX_ELO_RATING
        assert card.backend.rating == MIN_ELO_RATING
        assert card.ai_models.rating == 2000.0
        assert MIN_ELO_RATING <= card.composite_score <= MAX_ELO_RATING

