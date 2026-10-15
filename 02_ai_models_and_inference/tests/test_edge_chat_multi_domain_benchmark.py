#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Edge Chat Models Multi-Domain Benchmark
"""

import sys
import pytest
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

from edge_chat_multi_domain_benchmark import (
    run_edge_benchmark,
    REPORT_FILE
)


def test_ram_tiers_coverage():
    results = run_edge_benchmark()
    tiers = [r.tier for r in results]
    assert len(results) == 4
    assert any("4GB" in t for t in tiers)
    assert any("8GB" in t for t in tiers)
    assert any("12GB" in t for t in tiers)
    assert any("16GB" in t for t in tiers)


def test_ram_headroom_safety_margin():
    results = run_edge_benchmark()
    for r in results:
        # Every profile must maintain at least 25% free RAM safety headroom
        assert r.ram_headroom_pct >= 25.0, f"Failed safety headroom on tier {r.tier}: {r.ram_headroom_pct}%"
        assert r.ram_usage_gb < 6.0


def test_scores_valid_range():
    results = run_edge_benchmark()
    for r in results:
        assert 0.0 <= r.score_conversational_empathy <= 100.0
        assert 0.0 <= r.score_flutter_rust_code <= 100.0
        assert 0.0 <= r.score_screen_lens_vision <= 100.0
        assert 0.0 <= r.score_overall_composite <= 100.0


def test_obsidian_report_generated():
    run_edge_benchmark()
    assert REPORT_FILE.exists()
    assert REPORT_FILE.stat().st_size > 500
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SmolLM2 360M" in content
    assert "Qwen 2.5 Coder 1.5B" in content
    assert "Qwen 2.5 VL 7B Screen Lens" in content


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
