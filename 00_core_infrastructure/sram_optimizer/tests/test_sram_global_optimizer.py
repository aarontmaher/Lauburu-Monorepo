#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Global SRAM Optimizer & Zero-Allocation Memoryview Tiling Engine
==============================================================================
Subsystem: 00_core_infrastructure/sram_optimizer/tests/test_sram_global_optimizer.py
Compliant with: Rule 0 (Zero-Mock), Rule 3 (Host RAM Sanctuary)
"""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure/sram_optimizer"))

from sram_global_optimizer import (
    SramGlobalOptimizer,
    SramRingBuffer,
    StreamingAttentionSinkLimiter,
    TILE_SIZES
)


class TestSramGlobalOptimizer:
    def test_singleton_initialization(self):
        opt = SramGlobalOptimizer.get_instance()
        assert opt is not None
        assert opt.stats.total_preallocated_bytes > 0
        assert "4KB" in opt.tile_pools
        assert "16KB" in opt.tile_pools
        assert "64KB" in opt.tile_pools
        assert "1MB" in opt.tile_pools

    def test_borrow_tile_zero_copy(self):
        opt = SramGlobalOptimizer.get_instance()
        initial_hits = opt.stats.zero_copy_hits
        tile = opt.borrow_tile("64KB")
        assert len(tile) == 64 * 1024
        assert isinstance(tile, memoryview)
        assert opt.stats.zero_copy_hits == initial_hits + 1
        assert opt.stats.average_access_latency_us < 50.0  # Must be sub-microsecond in SRAM

    def test_ring_buffer_zero_reallocation(self):
        buf = SramRingBuffer(capacity_elements=128, item_format="f")
        for i in range(256):
            buf.push(float(i))
        assert buf.count == 128
        assert buf.total_writes == 256
        latest = buf.get_latest(4)
        assert latest == [252.0, 253.0, 254.0, 255.0]

    def test_ring_buffer_integer_format(self):
        buf = SramRingBuffer(capacity_elements=64, item_format="i")
        for i in range(10):
            buf.push(i * 10)
        assert buf.get_latest(3) == [70, 80, 90]

    def test_streaming_attention_sink_limiter_o1_bounds(self):
        limiter = StreamingAttentionSinkLimiter(sink_tokens=4, window_tokens=124, embedding_dim=128)
        footprint_kb = limiter.get_sram_footprint_kb()
        # 128 tokens * 128 * 2 bytes = 32768 bytes = 32 KB
        assert footprint_kb == 32.0

        # Push 200 tokens (exceeding window)
        for t in range(200):
            token_kv = (f"tok_{t}").encode("utf-8")
            pos = limiter.append_token_kv(t, token_kv)
            assert 0 <= pos < 128

        # Static memoryview size must remain strictly 32 KB
        assert limiter.get_sram_footprint_kb() == 32.0

    def test_monorepo_sram_efficiency_audit(self):
        opt = SramGlobalOptimizer.get_instance()
        audit = opt.audit_monorepo_sram_efficiency()
        assert audit["health_score_pct"] >= 90.0
        assert audit["total_pipelines_audited"] >= 3
        assert "Mac_Node" in audit["hardware_profiles"]
        assert "Pixel_10_Pro_XL" in audit["hardware_profiles"]

    def test_compact_memory(self):
        opt = SramGlobalOptimizer.get_instance()
        res = opt.compact_memory()
        assert res["status"] == "COMPACTED"
        assert res["cleared_bytes"] > 0
