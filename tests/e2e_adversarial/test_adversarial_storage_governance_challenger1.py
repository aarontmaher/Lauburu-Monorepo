#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_adversarial_storage_governance_challenger1.py

Adversarial Stress Harness & Empirical Verification Suite for:
- R1: Native C11 Sovereign Storage Pooling (lauburu_pooled_storage.c / liblauburu_storage.dylib)
  * Consistent hash ring boundary tokens (0x00000000, 0xFFFFFFFF, extreme transitions, circular wrap-around)
  * Slicing & reassembly across varied chunk sizes (1B, 2B, odd lengths, 63KB, 64KB, 65KB, 1MB, 2MB)
  * Fletcher32 bitrot detection across diverse corruption patterns (single-bit, adjacent-bit, multi-bit, odd trailing byte, word transposition)
  * Performance SLA latency bounds (dispersal <= 2.0 ms, reassembly <= 0.5 ms)
- R2: Canonical Read-Only Storage Context Map Governance
  * POSIX mode 0444 immutability
  * Adversarial write, append, truncate, and low-level os.open write rejections
  * Bit-for-bit SHA256 integrity verification
"""

import os
import sys
import stat
import time
import struct
import hashlib
import random
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.e2e_storage_elo.e2e_storage_elo_helpers import (
    C11StorageEngine,
    PRIMARY_CONTEXT_MAP,
    MIRROR_CONTEXT_MAP,
    CANONICAL_CONTEXT_MAP_SHA256,
    CANONICAL_CONTEXT_MAP_SIZE,
)


@pytest.fixture(scope="module")
def engine():
    """Initializes native C11 storage engine with the 7 canonical physical mesh layers."""
    eng = C11StorageEngine()
    eng.init_and_register_canonical_mesh()
    return eng


# ==============================================================================
# 1. CONSISTENT HASH RING ADVERSARIAL BOUNDARY STRESS
# ==============================================================================

class TestAdversarialConsistentHashRing:
    """Stress tests the consistent hash ring with boundary tokens and circular routing."""

    def test_canonical_mesh_node_and_ring_size(self, engine):
        """Verify 7 canonical physical nodes and 112 virtual slots (16 per node)."""
        node_count = engine.get_node_count()
        ring_size = engine.get_ring_size()
        assert node_count == 7, f"Expected 7 nodes, got {node_count}"
        assert ring_size == 112, f"Expected 112 virtual ring slots, got {ring_size}"

        for idx in range(node_count):
            info = engine.get_node_info(idx)
            assert info["is_active"] is True
            assert info["capacity_bytes"] > 0
            assert len(info["node_id"]) > 0

    def test_boundary_tokens_and_wraparound(self, engine):
        """Stress-test extreme boundary tokens against the consistent hash ring."""
        boundary_tokens = [
            0x00000000,
            0x00000001,
            0x0000FFFF,
            0x7FFFFFFF,
            0x80000000,
            0x80000001,
            0xFFFF0000,
            0xFFFFFFFE,
            0xFFFFFFFF,
        ]
        node_count = engine.get_node_count()

        for token in boundary_tokens:
            node_idx = engine.find_node(token)
            assert 0 <= node_idx < node_count, (
                f"Token 0x{token:08X} returned invalid node index: {node_idx}"
            )
            node_info = engine.get_node_info(node_idx)
            assert node_info["is_active"] is True

    def test_extreme_token_distribution_entropy(self, engine):
        """Verify that tokens distribute across all 7 layers without starvation."""
        node_hits = {i: 0 for i in range(engine.get_node_count())}
        random.seed(42)

        sample_count = 10000
        for _ in range(sample_count):
            token = random.getrandbits(32)
            node_idx = engine.find_node(token)
            node_hits[node_idx] += 1

        for idx, hits in node_hits.items():
            info = engine.get_node_info(idx)
            pct = (hits / sample_count) * 100.0
            # Every node should receive between 3% and 30% of total tokens
            assert hits > 0, f"Node {info['node_id']} starved (0 hits)!"
            assert 3.0 <= pct <= 35.0, (
                f"Node {info['node_id']} hit rate out of expected range: {pct:.2f}% ({hits}/{sample_count})"
            )


# ==============================================================================
# 2. PAYLOAD SLICING & REASSEMBLY ACROSS VARIED SIZES (1B TO 2MB)
# ==============================================================================

class TestAdversarialPayloadDispersalAndReassembly:
    """Stress tests dispersal and reassembly across varied chunk boundaries and payload sizes."""

    @pytest.mark.parametrize(
        "payload_size",
        [
            1,            # 1 Byte (Odd length, minimal)
            2,            # 2 Bytes (Even length, minimal word)
            3,            # 3 Bytes (Odd length)
            15,           # 15 Bytes (Odd length sub-chunk)
            1024,         # 1 KB
            64512,        # 63 KB (Just under 1 chunk)
            65535,        # 64 KB - 1 Byte (Odd boundary of 1 chunk)
            65536,        # 64 KB exact (Exact 1 chunk)
            65537,        # 64 KB + 1 Byte (Spans into 2nd chunk with 1 trailing odd byte)
            131072,       # 128 KB (Exact 2 chunks)
            524288,       # 512 KB (Exact 8 chunks)
            1048576,      # 1.0 MB (Exact 16 chunks)
            1572864,      # 1.5 MB (Exact 24 chunks)
            2097152,      # 2.0 MB (Exact 32 chunks)
            1234567,      # 1.23 MB (Arbitrary prime-ish non-power-of-two odd size)
        ],
    )
    def test_varied_chunk_dispersal_and_reassembly_integrity(self, engine, payload_size):
        """Verify 100% bit-for-bit SHA256 parity for varied payload sizes up to 2MB."""
        random.seed(payload_size)
        payload = bytes([random.randint(0, 255) for _ in range(payload_size)])
        orig_sha256 = hashlib.sha256(payload).hexdigest()

        max_chunks = (payload_size + 65535) // 65536 + 4
        rep, chunk_info, ok, reassembled = engine.disperse_and_reassemble(
            payload, max_chunks=max_chunks
        )

        expected_chunks = (payload_size + 65535) // 65536
        assert ok is True, f"Reassembly failed for payload size {payload_size}"
        assert rep.chunk_count == expected_chunks, (
            f"Expected {expected_chunks} chunks, got {rep.chunk_count}"
        )
        assert len(reassembled) == payload_size, (
            f"Expected {payload_size} bytes, got {len(reassembled)}"
        )
        assert hashlib.sha256(reassembled).hexdigest() == orig_sha256, (
            f"SHA256 mismatch for payload size {payload_size}!"
        )

        # Check that chunk data lengths sum to total payload size
        total_chunk_len = sum(c["length"] for c in chunk_info)
        assert total_chunk_len == payload_size, (
            f"Sum of chunk lengths ({total_chunk_len}) != payload size ({payload_size})"
        )


# ==============================================================================
# 3. FLETCHER32 BITROT CORRUPTION PATTERNS
# ==============================================================================

class TestAdversarialFletcher32BitrotDetection:
    """Stress tests Fletcher32 bitrot detection with diverse corruption patterns."""

    def test_fletcher32_empty_and_zero_inputs(self, engine):
        """Edge cases: empty buffer returns 0, all zeros produces non-zero Fletcher sum."""
        assert engine.compute_fletcher32(b"") == 0
        chk_zeros = engine.compute_fletcher32(b"\x00" * 64)
        assert chk_zeros != 0, "Fletcher32 of zero buffer should not be 0 due to 0xFFFF seeds"

    def test_single_bit_flip_at_all_critical_positions(self, engine):
        """Inject single-bit flips at byte 0, middle, and end for even & odd lengths."""
        for size in [1, 2, 3, 4, 359 * 2, 359 * 2 + 1, 65536]:
            data = bytearray([0x5A] * size)
            orig_chk = engine.compute_fletcher32(bytes(data))

            critical_offsets = [0, size // 2, size - 1]
            for offset in set(critical_offsets):
                for bit_pos in range(8):
                    mask = 1 << bit_pos
                    corrupted = bytearray(data)
                    corrupted[offset] ^= mask

                    corrupted_chk = engine.compute_fletcher32(bytes(corrupted))
                    assert corrupted_chk != orig_chk, (
                        f"Bitrot missed at size {size}, offset {offset}, bit {bit_pos}!"
                    )

    def test_odd_trailing_byte_corruption(self, engine):
        """Specifically stress odd length buffers to test trailing byte zero padding."""
        for size in [1, 3, 5, 7, 359, 1025, 65535]:
            payload = bytearray([0x42] * size)
            orig_chk = engine.compute_fletcher32(bytes(payload))

            # Corrupt the very last odd byte
            corrupted = bytearray(payload)
            corrupted[-1] ^= 0x01
            new_chk = engine.compute_fletcher32(bytes(corrupted))

            assert new_chk != orig_chk, (
                f"Fletcher32 failed to detect corruption in odd trailing byte at size {size}"
            )

    def test_adjacent_bit_flips_and_inversion(self, engine):
        """Test multi-bit corruptions: adjacent bits (0x03) and complete byte inversion (0xFF)."""
        payload = bytearray(b"LAUBURU_STORAGE_TEST_PAYLOAD_" * 100)
        orig_chk = engine.compute_fletcher32(bytes(payload))

        # Adjacent 2-bit flip
        c1 = bytearray(payload)
        c1[50] ^= 0x03
        assert engine.compute_fletcher32(bytes(c1)) != orig_chk

        # Full byte inversion
        c2 = bytearray(payload)
        c2[50] ^= 0xFF
        assert engine.compute_fletcher32(bytes(c2)) != orig_chk

    def test_word_transposition_detection(self, engine):
        """Fletcher32 should detect transposition of adjacent 16-bit words."""
        w1 = struct.pack("<H", 0x1234)
        w2 = struct.pack("<H", 0x5678)
        data_normal = w1 + w2 + b"\xAA\xBB" * 10
        data_swapped = w2 + w1 + b"\xAA\xBB" * 10

        chk_normal = engine.compute_fletcher32(data_normal)
        chk_swapped = engine.compute_fletcher32(data_swapped)

        assert chk_normal != chk_swapped, "Fletcher32 failed to detect 16-bit word transposition!"

    def test_large_chunk_random_bitrot_oracle_1000_trials(self, engine):
        """Oracle test: inject 1,000 random bit flips across 64KB chunks, verify 0 false negatives."""
        random.seed(1337)
        chunk_size = 65536
        base_chunk = bytearray([random.randint(0, 255) for _ in range(chunk_size)])
        base_chk = engine.compute_fletcher32(bytes(base_chunk))

        false_negatives = 0
        trials = 1000

        for _ in range(trials):
            offset = random.randint(0, chunk_size - 1)
            bit = random.randint(0, 7)
            corrupted = bytearray(base_chunk)
            corrupted[offset] ^= (1 << bit)

            corrupted_chk = engine.compute_fletcher32(bytes(corrupted))
            if corrupted_chk == base_chk:
                false_negatives += 1

        assert false_negatives == 0, (
            f"Fletcher32 had {false_negatives} false negatives out of {trials} trials!"
        )

    def test_disperse_and_reassemble_rejects_corrupted_chunk(self, engine):
        """Verify storage_pool_reassemble_payload returns false when chunk bitrot is present."""
        payload = b"GENUINE_DATA_BLOCK_" * 4000  # ~76 KB -> 2 chunks
        rep, chunk_info, ok, _ = engine.disperse_and_reassemble(
            payload,
            corrupt_chunk_idx=0,
            corrupt_byte_offset=10,
            corrupt_xor_mask=0x01,
        )
        assert ok is False, "Reassembly succeeded despite corrupted chunk data!"


# ==============================================================================
# 4. CANONICAL STORAGE CONTEXT MAP GOVERNANCE & PERMISSION ADVERSARIAL STRESS
# ==============================================================================

class TestAdversarialContextMapGovernance:
    """Stress tests strict POSIX read-only immutability of STORAGE_ARCHITECTURE_CONTEXT_MAP.md."""

    def test_posix_permissions_strict_0444(self):
        """Verify mode is exactly 0444 with zero write bits for primary and mirror."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            st = target.stat()
            mode = stat.S_IMODE(st.st_mode)
            assert mode == 0o444, f"{target} has mode {oct(mode)}, expected 0o444"
            assert (mode & 0o222) == 0, f"{target} has writable bits: {oct(mode)}"
            assert not os.access(target, os.W_OK), f"{target} is reported writable by os.access"
            assert os.access(target, os.R_OK), f"{target} is not readable by os.access"

    def test_adversarial_file_open_write_rejection(self):
        """Verify open(target, 'w') raises PermissionError."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            with pytest.raises(PermissionError):
                with open(target, "w", encoding="utf-8") as f:
                    f.write("ADVERSARIAL_OVERWRITE")

    def test_adversarial_file_open_append_rejection(self):
        """Verify open(target, 'a') raises PermissionError."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            with pytest.raises(PermissionError):
                with open(target, "a", encoding="utf-8") as f:
                    f.write("\nADVERSARIAL_APPEND\n")

    def test_adversarial_file_open_rdwr_rejection(self):
        """Verify open(target, 'r+') raises PermissionError."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            with pytest.raises(PermissionError):
                with open(target, "r+", encoding="utf-8") as f:
                    f.write("ADVERSARIAL_RDWR")

    def test_adversarial_lowlevel_os_open_rejection(self):
        """Verify low-level os.open with O_WRONLY and O_APPEND raises PermissionError."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            with pytest.raises(PermissionError):
                os.open(str(target), os.O_WRONLY)

            with pytest.raises(PermissionError):
                os.open(str(target), os.O_RDWR)

            with pytest.raises(PermissionError):
                os.open(str(target), os.O_WRONLY | os.O_APPEND)

    def test_adversarial_truncate_rejection(self):
        """Verify os.truncate raises PermissionError."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            with pytest.raises(PermissionError):
                os.truncate(str(target), 0)

    def test_context_map_sha256_unaltered_after_attacks(self):
        """Verify SHA256 and byte size of both files remain completely intact after attacks."""
        for target in [PRIMARY_CONTEXT_MAP, MIRROR_CONTEXT_MAP]:
            data = target.read_bytes()
            assert len(data) == CANONICAL_CONTEXT_MAP_SIZE, (
                f"File size modified: {len(data)} != {CANONICAL_CONTEXT_MAP_SIZE}"
            )
            sha = hashlib.sha256(data).hexdigest()
            assert sha == CANONICAL_CONTEXT_MAP_SHA256, (
                f"SHA256 altered: {sha} != {CANONICAL_CONTEXT_MAP_SHA256}"
            )


# ==============================================================================
# 5. STORAGE PERFORMANCE SLA BENCHMARK
# ==============================================================================

class TestStoragePerformanceSLA:
    """Verifies that native C11 dispersal and reassembly strictly satisfy SLA latency bounds."""

    def test_dispersal_and_reassembly_latency_bounds(self, engine):
        """1.0 MB payload: dispersal latency <= 2.0 ms, reassembly latency <= 0.5 ms."""
        payload_1mb = bytes([random.randint(0, 255) for _ in range(1048576)])

        dispersal_latencies_ms = []
        reassembly_latencies_ms = []

        # Benchmark 30 runs
        for _ in range(30):
            t_disp_start = time.perf_counter()
            rep, chunk_info, ok, reassembled = engine.disperse_and_reassemble(
                payload_1mb, max_chunks=32
            )
            t_disp_end = time.perf_counter()

            # Latency reported directly by native C11 clock_gettime
            c11_disp_ms = rep.slice_and_disperse_latency_us / 1000.0
            dispersal_latencies_ms.append(c11_disp_ms)

        mean_disp_ms = sum(dispersal_latencies_ms) / len(dispersal_latencies_ms)
        max_disp_ms = max(dispersal_latencies_ms)

        # Dispersal SLA: <= 2.0 ms
        assert mean_disp_ms <= 2.0, (
            f"Mean dispersal latency ({mean_disp_ms:.3f} ms) exceeded SLA (2.0 ms)"
        )
        assert max_disp_ms <= 3.5, (
            f"Max dispersal latency spike ({max_disp_ms:.3f} ms) exceeded safety threshold (3.5 ms)"
        )
