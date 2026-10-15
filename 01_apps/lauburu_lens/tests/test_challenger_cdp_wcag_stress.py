#!/usr/bin/env python3
"""
================================================================================
Adversarial Stress Test Suite: test_challenger_cdp_wcag_stress.py
================================================================================
Subsystem: 01_apps/lauburu_lens
Role: teamwork_preview_challenger_1 (Adversarial CDP & WCAG Challenger)

Adversarially probes:
1. Bounding Box Edge Cases & Reverse Hit-Testing (document.elementFromPoint)
   - Viewport boundary coordinates (0,0), negative coordinates, zero width/height
   - 4K resolution scaling vs 1080p active viewport
   - Viewport boundary leak (cx >= viewport_width when bridge is None)
   - Live CDP hit-testing on authentic unoccluded button
   - Live CDP hit-testing on DIV modal overlay (correctly rejected)
   - EMPIRICAL BUG PROOF: Live CDP hit-testing on button occluded by button (false pass)
   - EMPIRICAL BUG PROOF: Live CDP hit-testing on visibility:hidden element (false pass)

2. WCAG Luminance Math & Extreme Color Pairs
   - Pure black on pure white (21.0:1) & symmetry
   - Pure white on pure white (1.0:1) & pure black on black (1.0:1)
   - Semi-transparent text (rgba(255,255,255,0.54)) on #070B12 (6.06:1)
   - Normal text WCAG AAA (>= 7.0:1) failure vs Large text WCAG AAA (>= 4.5:1) pass
   - Transparent background fallback to DEFAULT_DARK_BG (#070B12)
   - EMPIRICAL GAP PROOF: Transparent element inside light container false rejection (1.07:1)
   - EMPIRICAL GAP PROOF: Transparent element inside light container false pass (19.71:1)
   - W3C Rec. 709 linear conversion precision & Porter-Duff compositing invariants

3. Live Endpoint Resilience & CDP Bridge Robustness
   - Voilà Console (:8890) dynamic loading & title retrieval
   - Self-Healing Hub (:18802) REST API pre element extraction & clean teardown
   - Port 4000 Console (:4000) MoveSense button & interactive DOM elements
   - Closed port (:54321) navigation & error page DOM extraction resilience
   - Closed CDP port (:9999) and 404 status resilience
   - CDP bridge evaluate error resilience (malformed JS, thrown errors)
   - Bridge context manager clean resource release
================================================================================
"""

import sys
import math
import urllib.parse
from pathlib import Path
import pytest

# Ensure lauburu_lens is in python path
CURRENT_DIR = Path(__file__).resolve().parent
LENS_DIR = CURRENT_DIR.parent
APPS_DIR = LENS_DIR.parent
if str(LENS_DIR) not in sys.path:
    sys.path.insert(0, str(LENS_DIR))
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from chrome_debugging_bridge import ChromeDebuggingBridge
from dom_element_extractor import DomElementExtractor, DomElement, BoundingRect, ElementStyles
from wcag_contrast_gate import WcagContrastGate, VerificationResult, DEFAULT_DARK_BG


# ==============================================================================
# 1. Bounding Box Edge Cases & Reverse Hit-Testing
# ==============================================================================
class TestChallengerBoundingBoxAndHitTesting:

    def test_viewport_edge_origin_0_0(self):
        """Element at top-left edge (0, 0) with valid dimensions must pass viewport gate."""
        el = DomElement(
            tag="button",
            id="origin_btn",
            text="Origin",
            rect=BoundingRect(left=0.0, top=0.0, width=100.0, height=40.0, cx=50.0, cy=20.0),
            styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
        )
        res = WcagContrastGate.verify_element(el)
        assert res.is_within_viewport is True
        assert res.passed is True

    def test_zero_and_negative_dimensions(self):
        """Zero or negative width/height must fail within_viewport check."""
        # Width = 0
        el_zero_w = DomElement(
            tag="button", id="z_w", text="",
            rect=BoundingRect(left=10.0, top=10.0, width=0.0, height=40.0, cx=10.0, cy=30.0),
            styles=ElementStyles()
        )
        assert WcagContrastGate.verify_element(el_zero_w).is_within_viewport is False

        # Height = 0
        el_zero_h = DomElement(
            tag="button", id="z_h", text="",
            rect=BoundingRect(left=10.0, top=10.0, width=100.0, height=0.0, cx=60.0, cy=10.0),
            styles=ElementStyles()
        )
        assert WcagContrastGate.verify_element(el_zero_h).is_within_viewport is False

        # Negative width
        el_neg_w = DomElement(
            tag="button", id="neg_w", text="",
            rect=BoundingRect(left=10.0, top=10.0, width=-50.0, height=40.0, cx=-15.0, cy=30.0),
            styles=ElementStyles()
        )
        assert WcagContrastGate.verify_element(el_neg_w).is_within_viewport is False

    def test_offscreen_coordinates_negative_and_overflow(self):
        """Completely offscreen elements must fail within_viewport check."""
        # Negative offscreen
        el_neg = DomElement(
            tag="button", id="neg_off", text="",
            rect=BoundingRect(left=-200.0, top=-200.0, width=100.0, height=40.0, cx=-150.0, cy=-180.0),
            styles=ElementStyles()
        )
        assert WcagContrastGate.verify_element(el_neg).is_within_viewport is False

        # Overflow right
        el_right = DomElement(
            tag="button", id="right_off", text="",
            rect=BoundingRect(left=2500.0, top=100.0, width=100.0, height=40.0, cx=2550.0, cy=120.0),
            styles=ElementStyles()
        )
        assert WcagContrastGate.verify_element(el_right).is_within_viewport is False

        # Overflow bottom
        el_bottom = DomElement(
            tag="button", id="bot_off", text="",
            rect=BoundingRect(left=100.0, top=2000.0, width=100.0, height=40.0, cx=150.0, cy=2020.0),
            styles=ElementStyles()
        )
        assert WcagContrastGate.verify_element(el_bottom).is_within_viewport is False

    def test_4k_resolution_viewport_scaling(self):
        """Element at 4K coordinates (2560x1440) fails 1080p viewport but passes 4K viewport."""
        el_4k = DomElement(
            tag="button", id="btn_4k", text="4K Button",
            rect=BoundingRect(left=2560.0, top=1440.0, width=200.0, height=60.0, cx=2660.0, cy=1470.0),
            styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
        )
        # Default 1920x1080 -> FAILS
        res_1080p = WcagContrastGate.verify_element(el_4k, viewport_width=1920, viewport_height=1080)
        assert res_1080p.is_within_viewport is False
        assert res_1080p.passed is False

        # 4K 3840x2160 -> PASSES
        res_4k = WcagContrastGate.verify_element(el_4k, viewport_width=3840, viewport_height=2160)
        assert res_4k.is_within_viewport is True
        assert res_4k.passed is True

    def test_viewport_boundary_leak_center_offscreen(self):
        """
        Adversarial Boundary Flaw:
        When left < 1920 but cx >= 1920 (e.g. left=1910, width=100 -> cx=1960),
        without bridge is_within_viewport returns True because cx < viewport_width is not checked!
        """
        el_leak = DomElement(
            tag="button", id="leak_btn", text="Leaky Button",
            rect=BoundingRect(left=1910.0, top=100.0, width=100.0, height=50.0, cx=1960.0, cy=125.0),
            styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
        )
        # Without bridge: is_within_viewport evaluates to True due to missing upper bound on cx
        res_no_bridge = WcagContrastGate.verify_element(el_leak, bridge=None)
        assert res_no_bridge.is_within_viewport is True, (
            "Empirical vulnerability confirmed: cx >= 1920 is not validated in is_within_viewport"
        )

    def test_authentic_unoccluded_button_hit_live_cdp(self):
        """Live CDP: Unoccluded button receives authentic hit pass from elementFromPoint."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            html = """<!DOCTYPE html><html><head><style>
            #btn_live_1 { position: absolute; left: 80px; top: 80px; width: 120px; height: 40px; }
            </style></head><body><button id="btn_live_1">Live Click</button></body></html>"""
            bridge.navigate("data:text/html;charset=utf-8," + urllib.parse.quote(html), wait_seconds=0.5)

            el = DomElement(
                tag="button", id="btn_live_1", text="Live Click",
                rect=BoundingRect(left=80.0, top=80.0, width=120.0, height=40.0, cx=140.0, cy=100.0),
                styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
            )
            res = WcagContrastGate.verify_element(el, bridge=bridge)
            assert res.is_authentic_hit is True
            assert res.passed is True
            assert res.hit_tag == "BUTTON"
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()

    def test_occluded_by_div_modal_rejected_live_cdp(self):
        """Live CDP: Button occluded by a fixed DIV modal backdrop fails authentic hit test."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            html = """<!DOCTYPE html><html><head><style>
            #btn_bg_2 { position: absolute; left: 80px; top: 80px; width: 120px; height: 40px; }
            #div_backdrop_2 { position: fixed; left: 0; top: 0; width: 1000px; height: 1000px; z-index: 999; background: rgba(0,0,0,0.5); }
            </style></head><body>
            <button id="btn_bg_2">Covered Button</button>
            <div id="div_backdrop_2">Modal Overlay</div>
            </body></html>"""
            bridge.navigate("data:text/html;charset=utf-8," + urllib.parse.quote(html), wait_seconds=0.5)

            el = DomElement(
                tag="button", id="btn_bg_2", text="Covered Button",
                rect=BoundingRect(left=80.0, top=80.0, width=120.0, height=40.0, cx=140.0, cy=100.0),
                styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
            )
            res = WcagContrastGate.verify_element(el, bridge=bridge)
            assert res.is_authentic_hit is False
            assert res.passed is False
            assert res.hit_tag == "DIV"
            assert "Reverse hit-test failed" in res.reason
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()

    def test_occluded_by_another_button_bug_demonstration_live_cdp(self):
        """
        EMPIRICAL BUG DEMONSTRATION:
        When a button is completely occluded by another button (e.g. overlapping floating action button),
        WcagContrastGate falsely reports is_authentic_hit=True because it only checks hit.tagName === targetTag
        and includes || hit.tagName === 'BUTTON'.
        """
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            html = """<!DOCTYPE html><html><head><style>
            #btn_underneath_3 { position: absolute; left: 80px; top: 80px; width: 120px; height: 40px; }
            #btn_overlay_3 { position: fixed; left: 0; top: 0; width: 500px; height: 500px; z-index: 999; }
            </style></head><body>
            <button id="btn_underneath_3">Underneath</button>
            <button id="btn_overlay_3">Top Button</button>
            </body></html>"""
            bridge.navigate("data:text/html;charset=utf-8," + urllib.parse.quote(html), wait_seconds=0.5)

            el_under = DomElement(
                tag="button", id="btn_underneath_3", text="Underneath",
                rect=BoundingRect(left=80.0, top=80.0, width=120.0, height=40.0, cx=140.0, cy=100.0),
                styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
            )
            res = WcagContrastGate.verify_element(el_under, bridge=bridge)
            # Strict fail-closed verification: occluded button must fail authentic hit test
            assert res.is_authentic_hit is False, "Occluded button must fail authentic hit test"
            assert res.passed is False
            assert "Reverse hit-test failed" in res.reason

            # Challenger 1 Hardening: Un-IDed element occluded by same tag must also fail
            el_under_no_id = DomElement(
                tag="button", id="", text="Underneath",
                rect=BoundingRect(left=80.0, top=80.0, width=120.0, height=40.0, cx=140.0, cy=100.0),
                styles=ElementStyles(color="#ffffff", backgroundColor="#070b12")
            )
            res_no_id = WcagContrastGate.verify_element(el_under_no_id, bridge=bridge)
            assert res_no_id.is_authentic_hit is False, "Un-IDed occluded button must fail authentic hit test"
            assert res_no_id.passed is False
            assert "Reverse hit-test failed" in res_no_id.reason
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()

    def test_hidden_visibility_element_bug_demonstration_live_cdp(self):
        """
        EMPIRICAL BUG DEMONSTRATION:
        When an element has visibility: hidden, elementFromPoint returns <html>.
        WcagContrastGate falsely reports is_authentic_hit=True because <html>.contains(el) is true for any DOM node!
        """
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            html = """<!DOCTYPE html><html><head><style>
            #btn_hidden_4 { position: absolute; left: 350px; top: 350px; width: 120px; height: 40px; visibility: hidden; }
            </style></head><body><button id="btn_hidden_4">Hidden</button></body></html>"""
            bridge.navigate("data:text/html;charset=utf-8," + urllib.parse.quote(html), wait_seconds=0.5)

            el_hidden = DomElement(
                tag="button", id="btn_hidden_4", text="Hidden",
                rect=BoundingRect(left=350.0, top=350.0, width=120.0, height=40.0, cx=410.0, cy=370.0),
                styles=ElementStyles(color="#ffffff", backgroundColor="#070b12", visibility="hidden")
            )
            res = WcagContrastGate.verify_element(el_hidden, bridge=bridge)
            # Strict fail-closed verification: invisible element must fail authentic hit test
            assert res.is_authentic_hit is False, "Invisible element must fail authentic hit test"
            assert res.passed is False
            assert "Reverse hit-test failed" in res.reason
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()


# ==============================================================================
# 2. WCAG Luminance Math & Extreme Color Pairs
# ==============================================================================
class TestChallengerWcagLuminanceMath:

    def test_pure_black_on_pure_white_21_to_1(self):
        """Pure black (#000000) on pure white (#ffffff) yields exactly 21.0:1 contrast ratio."""
        cr, fg, bg = WcagContrastGate.calculate_contrast_ratio("#000000", "#ffffff")
        assert cr == 21.0
        assert fg == "rgb(0, 0, 0)"
        assert bg == "rgb(255, 255, 255)"

        # Symmetry test: white on black
        cr_rev, fg_rev, bg_rev = WcagContrastGate.calculate_contrast_ratio("#ffffff", "#000000")
        assert cr_rev == 21.0
        assert fg_rev == "rgb(255, 255, 255)"
        assert bg_rev == "rgb(0, 0, 0)"

    def test_pure_white_on_pure_white_1_to_1(self):
        """Pure white on pure white yields 1.0:1 contrast ratio."""
        cr, fg, bg = WcagContrastGate.calculate_contrast_ratio("#ffffff", "#ffffff")
        assert cr == 1.0

        # Pure black on black
        cr_blk, _, _ = WcagContrastGate.calculate_contrast_ratio("#000000", "#000000")
        assert cr_blk == 1.0

    def test_semi_transparent_white_54_on_dark_bg_ratio_6_06(self):
        """
        Semi-transparent text rgba(255, 255, 255, 0.54) over #070B12 composites to rgb(141, 143, 146)
        and yields authentic floating point contrast ratio of 6.06:1.
        """
        cr, fg, bg = WcagContrastGate.calculate_contrast_ratio("rgba(255, 255, 255, 0.54)", "#070B12")
        assert math.isclose(cr, 6.06, abs_tol=0.05)
        assert fg == "rgb(141, 143, 146)"
        assert bg == "rgb(7, 11, 18)"

    def test_semi_transparent_white_54_fails_normal_text_aaa(self):
        """rgba(255, 255, 255, 0.54) on dark theme must FAIL WCAG AAA normal text threshold (7.0:1)."""
        el_normal = DomElement(
            tag="span", id="muted_label", text="Muted",
            rect=BoundingRect(left=10.0, top=10.0, width=60.0, height=20.0, cx=40.0, cy=20.0),
            styles=ElementStyles(
                color="rgba(255, 255, 255, 0.54)",
                backgroundColor="#070B12",
                fontSize="14px",
                fontWeight="400"
            )
        )
        res = WcagContrastGate.verify_element(el_normal)
        assert res.contrast_ratio < 7.0
        assert res.passes_wcag_aaa is False
        assert res.passed is False
        assert "below WCAG AAA required 7.0:1" in res.reason

    def test_semi_transparent_white_54_passes_large_text_aaa(self):
        """rgba(255, 255, 255, 0.54) on dark theme must PASS WCAG AAA large text threshold (4.5:1)."""
        el_large = DomElement(
            tag="h1", id="muted_header", text="Header",
            rect=BoundingRect(left=10.0, top=10.0, width=200.0, height=40.0, cx=110.0, cy=30.0),
            styles=ElementStyles(
                color="rgba(255, 255, 255, 0.54)",
                backgroundColor="#070B12",
                fontSize="24px",
                fontWeight="400"
            )
        )
        res = WcagContrastGate.verify_element(el_large)
        assert res.is_large_text is True
        assert res.required_aaa_ratio == 4.5
        assert res.contrast_ratio >= 4.5
        assert res.passes_wcag_aaa is True
        assert res.passed is True

    def test_transparent_background_defaults_to_dark_base(self):
        """Transparent background composites against DEFAULT_DARK_BG (#070B12)."""
        cr, fg, bg = WcagContrastGate.calculate_contrast_ratio("#ffffff", "transparent")
        assert math.isclose(cr, 19.71, abs_tol=0.1)
        assert bg == "rgb(7, 11, 18)"

    def test_transparent_bg_ancestor_climbing_gap_dark_text_false_rejection(self):
        """
        EMPIRICAL GAP DEMONSTRATION:
        Black text inside a white container with transparent element background
        is falsely rejected (1.07:1) because WcagContrastGate lacks ancestor climbing
        and assumes DEFAULT_DARK_BG behind it.
        """
        el_black_on_card = DomElement(
            tag="button", id="card_btn", text="Card Button",
            rect=BoundingRect(left=50.0, top=50.0, width=100.0, height=40.0, cx=100.0, cy=70.0),
            styles=ElementStyles(color="rgb(0, 0, 0)", backgroundColor="transparent")
        )
        res = WcagContrastGate.verify_element(el_black_on_card)
        # PROVE THE GAP: 1.07:1 ratio computed against dark canvas instead of light container
        assert res.contrast_ratio == 1.07
        assert res.passes_wcag_aaa is False
        assert res.passed is False

    def test_transparent_bg_ancestor_climbing_gap_white_text_false_pass(self):
        """
        EMPIRICAL GAP DEMONSTRATION:
        White text on a white container with transparent element background
        is falsely PASSED (19.71:1) because WcagContrastGate lacks ancestor climbing
        and assumes DEFAULT_DARK_BG behind it, even though the text is invisible in reality.
        """
        el_white_on_card = DomElement(
            tag="button", id="inv_btn", text="Invisible Button",
            rect=BoundingRect(left=50.0, top=50.0, width=100.0, height=40.0, cx=100.0, cy=70.0),
            styles=ElementStyles(color="rgb(255, 255, 255)", backgroundColor="transparent")
        )
        res = WcagContrastGate.verify_element(el_white_on_card)
        # PROVE THE GAP: 19.71:1 false pass on invisible white-on-white text
        assert res.contrast_ratio == 19.71
        assert res.passes_wcag_aaa is True
        assert res.passed is True

    def test_w3c_srgb_linearization_curve_mathematical_precision(self):
        """Verify linearization strictly follows the piecewise threshold 0.04045."""
        # Exact threshold boundary
        c_low = 0.04045 * 255.0  # 10.31475
        lin_low = WcagContrastGate.linearize_srgb(c_low)
        assert math.isclose(lin_low, 0.04045 / 12.92, rel_tol=1e-5)

        # Value just above threshold
        c_high = 0.04046 * 255.0
        lin_high = WcagContrastGate.linearize_srgb(c_high)
        expected_high = math.pow((0.04046 + 0.055) / 1.055, 2.4)
        assert math.isclose(lin_high, expected_high, rel_tol=1e-4)

    def test_w3c_relative_luminance_rec709_coefficients(self):
        """Verify Rec. 709 luminance coefficients: 0.2126 R + 0.7152 G + 0.0722 B."""
        assert math.isclose(WcagContrastGate.relative_luminance(255, 0, 0), 0.2126, abs_tol=1e-4)
        assert math.isclose(WcagContrastGate.relative_luminance(0, 255, 0), 0.7152, abs_tol=1e-4)
        assert math.isclose(WcagContrastGate.relative_luminance(0, 0, 255), 0.0722, abs_tol=1e-4)


# ==============================================================================
# 3. Live Endpoint Resilience & CDP Bridge Robustness
# ==============================================================================
class TestChallengerLiveEndpointResilience:

    def test_endpoint_8890_voila_resilience(self):
        """Live Endpoint :8890 (Voilà): Bridge connects, navigates, reads title without crash."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            ok = bridge.navigate("http://127.0.0.1:8890", wait_seconds=1.0)
            assert ok is True
            title = bridge.evaluate("document.title")
            assert title is not None
            assert len(title) > 0
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()

    def test_endpoint_18802_self_healing_hub_resilience(self):
        """Live Endpoint :18802 (Self-Healing Hub): REST API responds with HEALTHY and closes connection cleanly."""
        import urllib.request
        import json
        req = urllib.request.Request("http://127.0.0.1:18802/health", headers={"Connection": "close", "User-Agent": "LensTest/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "HEALTHY"
            assert data.get("port") == 18802
            assert data.get("service") == "self_healing_hub"

    def test_endpoint_4000_movesense_console_resilience(self):
        """Live Endpoint :4000 (Port 4000): Bridge extracts authentic MoveSense button and tabs."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            ok = bridge.navigate("http://127.0.0.1:4000", wait_seconds=0.5)
            assert ok is True
            extractor = DomElementExtractor(bridge)
            elements = extractor.extract_interactive_elements(bridge)
            # In default tab view, 7 primary interactive elements are visible
            assert len(elements) >= 5

            # Verify authentic interactive button on MoveSense console
            ms_btn = next((e for e in elements if any(k in e.text.upper() for k in ["MOVESENSE", "READINESS", "PPG", "CATALOG"])), None)
            assert ms_btn is not None
            assert ms_btn.tag == "BUTTON"
            assert ms_btn.rect.width > 0
            assert ms_btn.rect.height > 0
            assert ms_btn.rect.cx > 0
            assert ms_btn.rect.cy > 0

            # Verify verification gate on live element
            res = WcagContrastGate.verify_element(ms_btn, bridge=bridge)
            assert res.is_within_viewport is True
            assert res.is_authentic_hit is True
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()

    def test_endpoint_closed_port_error_page_resilience(self):
        """Closed web port (:54321): Navigation and DOM extraction complete without unhandled exception."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            ok = bridge.navigate("http://127.0.0.1:54321", wait_seconds=0.5)
            assert ok is True  # CDP Page.navigate succeeds even when target returns net error
            extractor = DomElementExtractor(bridge)
            elements = extractor.extract_interactive_elements(bridge)
            # Chrome renders net error page with list items or headings
            assert isinstance(elements, list)
        finally:
            bridge.navigate("about:blank", wait_seconds=0.2)
            bridge.close()

    def test_cdp_status_closed_port_resilience(self):
        """CDP status check on closed port (:9999) returns online=False without throwing."""
        bridge = ChromeDebuggingBridge()
        status = bridge.check_cdp_status(9999)
        assert status["online"] is False
        assert status["port"] == 9999
        assert "error" in status

    def test_cdp_status_404_resilience(self):
        """CDP status check on port returning 404 (:9222) returns online=False without crashing."""
        bridge = ChromeDebuggingBridge()
        status = bridge.check_cdp_status(9222)
        assert status["online"] is False
        assert status["port"] == 9222

    def test_bridge_fallback_port_activation(self):
        """Bridge automatically falls back to 9224 when default port 9222 is not responsive."""
        bridge = ChromeDebuggingBridge(port=9222, fallback_port=9224)
        bridge.connect()
        try:
            assert bridge.active_port == 9224
            assert bridge.ws is not None
        finally:
            bridge.close()

    def test_bridge_evaluate_malformed_js_resilience(self):
        """Bridge evaluate with malformed JS returns None without raising unhandled exception."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            res = bridge.evaluate("function {{{ malformed syntax %%%")
            assert res is None
        finally:
            bridge.close()

    def test_bridge_evaluate_thrown_exception_resilience(self):
        """Bridge evaluate with JavaScript runtime exception returns None without raising."""
        bridge = ChromeDebuggingBridge()
        bridge.connect()
        try:
            res = bridge.evaluate("(() => { throw new Error('Adversarial probe'); })()")
            assert res is None
        finally:
            bridge.close()

    def test_bridge_context_manager_clean_lifecycle(self):
        """Bridge context manager connects and closes cleanly."""
        with ChromeDebuggingBridge() as b:
            assert b.ws is not None
            title = b.evaluate("1 + 1")
            assert title == 2
        assert b.ws is None
