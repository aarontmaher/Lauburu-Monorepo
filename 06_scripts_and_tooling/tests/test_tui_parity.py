#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Parity Test Suite for Terminal User Interface (TUI) Benchmarking
Subsystem: 06_scripts_and_tooling/tests/test_tui_parity.py

Tests:
1. Textual (Python) TUI Latency & A11y Audit Engine
2. Ratatui (Rust) Immediate-Mode Sub-Millisecond Benchmark & Zero-Allocation Engine
3. Triple-TUI Parity Comparator (Textual vs Ratatui vs Web TUI Port 8088)
4. WCAG 2.1 AA Contrast Ratio & Relative Luminance Math
"""

import sys
import unittest
from pathlib import Path

# Add TUI path to sys.path
TUI_PATH = Path(__file__).resolve().parent.parent / "tui"
if str(TUI_PATH) not in sys.path:
    sys.path.insert(0, str(TUI_PATH))

from textual_tui_benchmark import (
    A11yAuditReport,
    MockTextualDashboard,
    TextualBenchmarkResult,
    TextualTUIBenchmark,
    calculate_contrast_ratio,
    calculate_relative_luminance,
    hex_to_rgb,
)
from ratatui_tui_benchmark import (
    RatatuiBenchmarkResult,
    RatatuiBufferModel,
    RatatuiTUIBenchmark,
    TripleTUIParityComparator,
    TripleTUIParityReport,
    WebTUIBenchmarkResult,
)


class TestTextualTUIBenchmark(unittest.TestCase):
    """Test suite for Textual TUI Latency, Memory & A11y Benchmark."""

    def test_contrast_ratio_calculations(self):
        """WCAG contrast ratio calculations on known color pairs."""
        # Pure Black (#000000) on Pure White (#FFFFFF) => 21.0 : 1
        cr_bw = calculate_contrast_ratio("#FFFFFF", "#000000")
        self.assertAlmostEqual(cr_bw, 21.0, delta=0.5)

        # Same colors => 1.0 : 1
        cr_same = calculate_contrast_ratio("#10B981", "#10B981")
        self.assertAlmostEqual(cr_same, 1.0, delta=0.1)

        # White on Slate (#0F172A) => high contrast >= 12:1
        cr_slate = calculate_contrast_ratio("#FFFFFF", "#0F172A")
        self.assertGreater(cr_slate, 12.0)

    def test_hex_to_rgb_and_luminance(self):
        """Color conversions and luminance calculations."""
        r, g, b = hex_to_rgb("#10b981")
        self.assertEqual((r, g, b), (16, 185, 129))

        lum_white = calculate_relative_luminance(255, 255, 255)
        self.assertAlmostEqual(lum_white, 1.0, places=2)

        lum_black = calculate_relative_luminance(0, 0, 0)
        self.assertAlmostEqual(lum_black, 0.0, places=2)

    def test_a11y_tree_audit(self):
        """A11y tree audit evaluates widget roles, focus order, and contrast."""
        bench = TextualTUIBenchmark(iterations=20, high_contrast=True)
        report = bench.audit_a11y_tree()

        self.assertIsInstance(report, A11yAuditReport)
        self.assertGreaterEqual(report.score_pct, 90.0)
        self.assertTrue(report.wcag_aa_compliant)
        self.assertTrue(report.focus_order_valid)
        self.assertGreaterEqual(report.min_contrast_ratio, 4.5)

    def test_textual_benchmark_execution(self):
        """Executes full Textual TUI benchmark and verifies latency stats."""
        bench = TextualTUIBenchmark(iterations=50)
        res = bench.run_benchmark()

        self.assertIsInstance(res, TextualBenchmarkResult)
        self.assertEqual(res.framework, "Textual (Python)")
        self.assertEqual(res.render_cycles, 50)
        self.assertGreater(res.duration_sec, 0.0)
        self.assertGreater(res.throughput_fps, 0.0)
        self.assertGreaterEqual(res.latency_p95_ms, res.latency_p50_ms)
        self.assertGreaterEqual(res.latency_p99_ms, res.latency_p95_ms)
        self.assertEqual(res.frames_exceeding_50ms, 0)
        self.assertTrue(res.sla_passed)


class TestRatatuiTUIBenchmark(unittest.TestCase):
    """Test suite for Ratatui immediate-mode sub-ms benchmark."""

    def test_buffer_model_draw_pass(self):
        """RatatuiBufferModel executes immediate-mode draw into pre-allocated cells."""
        buf = RatatuiBufferModel(width=100, height=30)
        cells = buf.draw_pass(hr_bpm=75.0, ptt_bp_sbp=120, ptt_bp_dbp=80, dfa_a1=0.85)

        self.assertEqual(cells, 3000)
        self.assertEqual(len(buf.buffer_symbols), 3000)
        # Verify header title is written in symbols
        rendered_str = "".join(buf.buffer_symbols[:28])
        self.assertIn("LAUBURU MESH TUI", rendered_str)

    def test_ratatui_benchmark_sub_millisecond_sla(self):
        """Ratatui benchmark achieves sub-millisecond P95 latency (<= 1.0ms)."""
        bench = RatatuiTUIBenchmark(iterations=100)
        res = bench.run_benchmark()

        self.assertIsInstance(res, RatatuiBenchmarkResult)
        self.assertEqual(res.framework, "Ratatui (Rust)")
        self.assertLessEqual(res.latency_p95_ms, 1.0)
        self.assertEqual(res.frames_exceeding_16ms, 0)
        self.assertEqual(res.frames_exceeding_50ms, 0)
        self.assertTrue(res.zero_allocation_verified)
        self.assertTrue(res.sla_passed)


class TestTripleTUIParityComparator(unittest.TestCase):
    """Test suite for Triple-TUI Parity comparison."""

    def test_triple_tui_comparison_and_concordance(self):
        """Evaluates all three TUI frameworks and computes concordance score."""
        comparator = TripleTUIParityComparator(iterations=50)
        report = comparator.compare_all()

        self.assertIsInstance(report, TripleTUIParityReport)
        self.assertIn("textual", report.textual["framework"].lower())
        self.assertIn("ratatui", report.ratatui["framework"].lower())
        self.assertIn("react", report.web_tui["framework"].lower())

        # Concordance score must be >= 90%
        self.assertGreaterEqual(report.concordance_score, 0.90)
        self.assertTrue(report.sla_all_passed)
        self.assertIn("Triple-TUI Parity Verified", report.parity_summary)


if __name__ == "__main__":
    unittest.main()
