#!/usr/bin/env python3
"""
================================================================================
Lauburu Lens: WCAG 2.1 AAA Contrast & Two-Way Hit-Testing Gate (2026)
================================================================================
Subsystem: 01_apps/lauburu_lens/wcag_contrast_gate.py
Lauburu Mesh Ecosystem — Rule #0 Zero-Mock & Anti-Hallucination Verification

Features:
  1. Two-Way Coordinate Anti-Hallucination Verification:
     - Forward bounding box getBoundingClientRect()
     - Reverse hit-testing document.elementFromPoint(cx, cy)
  2. Authentic WCAG 2.1 Relative Luminance & Contrast Engine:
     - sRGB channel linearization
     - CIE 1931 Rec. 709 relative luminance
     - Porter-Duff source-over alpha compositing
     - Ancestor background traversal for transparent layers
  3. WCAG AAA Threshold Enforcement:
     - Normal text (<24px, or <18.66px bold): CR >= 7.0:1
     - Large text (>=24px, or >=18.66px bold): CR >= 4.5:1
================================================================================
"""

import re
import math
import logging
import json
from dataclasses import dataclass, asdict
from typing import Tuple, Optional, Dict, Any, List
try:
    from .dom_element_extractor import DomElement
except ImportError:
    from dom_element_extractor import DomElement

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Lens-WCAG-Gate] %(message)s")
log = logging.getLogger("WcagContrastGate")

DEFAULT_DARK_BG = (7, 11, 18, 1.0)  # #070B12 canonical dark theme


@dataclass
class VerificationResult:
    is_authentic_hit: bool
    is_within_viewport: bool
    contrast_ratio: float
    passes_wcag_aaa: bool
    passed: bool
    effective_fg: str = "rgb(255, 255, 255)"
    effective_bg: str = "rgb(7, 11, 18)"
    required_aaa_ratio: float = 7.0
    is_large_text: bool = False
    hit_tag: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_OFFLINE_SENTINEL = object()


class WcagContrastGate:
    """
    Authentic WCAG 2.1 AAA Contrast and Two-Way Anti-Hallucination Gate.
    """

    @staticmethod
    def linearize_srgb(c_8bit: float) -> float:
        """
        Convert 8-bit sRGB color channel [0, 255] to linear luminance factor.
        C_linear = C_s / 12.92 if C_s <= 0.04045 else ((C_s + 0.055) / 1.055) ** 2.4
        """
        c_s = max(0.0, min(255.0, c_8bit)) / 255.0
        if c_s <= 0.04045:
            return c_s / 12.92
        return math.pow((c_s + 0.055) / 1.055, 2.4)

    @staticmethod
    def relative_luminance(r: float, g: float, b: float) -> float:
        """
        Calculate relative luminance according to W3C WCAG 2.1 / CIE 1931 Rec. 709:
        L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin
        """
        r_lin = WcagContrastGate.linearize_srgb(r)
        g_lin = WcagContrastGate.linearize_srgb(g)
        b_lin = WcagContrastGate.linearize_srgb(b)
        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

    @staticmethod
    def parse_css_color(color_str: str) -> Tuple[float, float, float, float]:
        """
        Parse CSS color string (rgb, rgba, hex, or named) into (R, G, B, A).
        Defaults to (255, 255, 255, 1.0) if unparseable.
        """
        if not color_str:
            return (255.0, 255.0, 255.0, 1.0)
        c = color_str.strip().lower()

        # Check transparent
        if c in ("transparent", "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)"):
            return (0.0, 0.0, 0.0, 0.0)

        # Check rgb/rgba
        rgba_match = re.match(r"rgba?\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)", c)
        if rgba_match:
            r = float(rgba_match.group(1))
            g = float(rgba_match.group(2))
            b = float(rgba_match.group(3))
            a = float(rgba_match.group(4)) if rgba_match.group(4) is not None else 1.0
            return (r, g, b, a)

        # Check hex #RRGGBB or #RGB
        if c.startswith("#"):
            hex_body = c[1:]
            if len(hex_body) == 3:
                r = int(hex_body[0] * 2, 16)
                g = int(hex_body[1] * 2, 16)
                b = int(hex_body[2] * 2, 16)
                return (float(r), float(g), float(b), 1.0)
            elif len(hex_body) == 6:
                r = int(hex_body[0:2], 16)
                g = int(hex_body[2:4], 16)
                b = int(hex_body[4:6], 16)
                return (float(r), float(g), float(b), 1.0)
            elif len(hex_body) == 8:
                r = int(hex_body[0:2], 16)
                g = int(hex_body[2:4], 16)
                b = int(hex_body[4:6], 16)
                a = int(hex_body[6:8], 16) / 255.0
                return (float(r), float(g), float(b), a)

        # Named colors
        named = {
            "white": (255.0, 255.0, 255.0, 1.0),
            "black": (0.0, 0.0, 0.0, 1.0),
            "red": (255.0, 0.0, 0.0, 1.0),
            "green": (0.0, 255.0, 0.0, 1.0),
            "blue": (0.0, 0.0, 255.0, 1.0)
        }
        if c in named:
            return named[c]

        return (255.0, 255.0, 255.0, 1.0)

    @staticmethod
    def alpha_composite(
        fg: Tuple[float, float, float, float],
        bg: Tuple[float, float, float, float]
    ) -> Tuple[float, float, float, float]:
        """
        Porter-Duff source-over alpha compositing:
        C_out = a_fg * C_fg + (1 - a_fg) * a_bg * C_bg
        a_out = a_fg + a_bg * (1 - a_fg)
        """
        r_fg, g_fg, b_fg, a_fg = fg
        r_bg, g_bg, b_bg, a_bg = bg

        a_out = a_fg + a_bg * (1.0 - a_fg)
        if a_out <= 0.0:
            return (0.0, 0.0, 0.0, 0.0)

        r_out = (r_fg * a_fg + r_bg * a_bg * (1.0 - a_fg)) / a_out
        g_out = (g_fg * a_fg + g_bg * a_bg * (1.0 - a_fg)) / a_out
        b_out = (b_fg * a_fg + b_bg * a_bg * (1.0 - a_fg)) / a_out

        return (r_out, g_out, b_out, a_out)

    @classmethod
    def resolve_ancestor_background(
        cls,
        bg_stack: List[str],
        base_bg: Tuple[float, float, float, float] = DEFAULT_DARK_BG
    ) -> Tuple[float, float, float, float]:
        """
        Composite an ancestor background stack (innermost element to outermost ancestor)
        down to the dark theme base canvas (#070B12) using Porter-Duff source-over.
        """
        if not bg_stack:
            return base_bg
        parsed_layers = [cls.parse_css_color(c) for c in bg_stack]
        curr_bg = base_bg
        for layer in reversed(parsed_layers):
            if layer[3] > 0.0:
                curr_bg = cls.alpha_composite(layer, curr_bg)
        return curr_bg

    @classmethod
    def calculate_contrast_ratio(
        cls,
        fg_color: str,
        bg_color: str,
        base_bg: Tuple[float, float, float, float] = DEFAULT_DARK_BG,
        ancestor_bg_stack: Optional[List[str]] = None
    ) -> Tuple[float, str, str]:
        """
        Calculate WCAG contrast ratio with alpha compositing against ancestor background hierarchy
        and fallback to dark theme base (#070B12).
        Returns: (contrast_ratio, effective_fg_str, effective_bg_str)
        """
        raw_fg = cls.parse_css_color(fg_color)
        raw_bg = cls.parse_css_color(bg_color)

        if raw_bg[3] >= 1.0:
            effective_bg = raw_bg
        else:
            underlying_bg = cls.resolve_ancestor_background(ancestor_bg_stack, base_bg=base_bg) if ancestor_bg_stack else base_bg
            effective_bg = cls.alpha_composite(raw_bg, underlying_bg)

        # Composite foreground over effective background
        effective_fg = cls.alpha_composite(raw_fg, effective_bg) if raw_fg[3] < 1.0 else raw_fg

        l_fg = cls.relative_luminance(effective_fg[0], effective_fg[1], effective_fg[2])
        l_bg = cls.relative_luminance(effective_bg[0], effective_bg[1], effective_bg[2])

        lighter = max(l_fg, l_bg)
        darker = min(l_fg, l_bg)
        cr = (lighter + 0.05) / (darker + 0.05)

        eff_fg_str = f"rgb({int(round(effective_fg[0]))}, {int(round(effective_fg[1]))}, {int(round(effective_fg[2]))})"
        eff_bg_str = f"rgb({int(round(effective_bg[0]))}, {int(round(effective_bg[1]))}, {int(round(effective_bg[2]))})"

        return (round(cr, 2), eff_fg_str, eff_bg_str)

    @classmethod
    def verify_element(
        cls,
        element: DomElement,
        bridge: Any = _OFFLINE_SENTINEL,
        viewport_width: int = 1920,
        viewport_height: int = 1080
    ) -> VerificationResult:
        """
        Execute two-way anti-hallucination verification and WCAG AAA contrast evaluation.
        """
        r = element.rect
        st = element.styles

        # 1. Forward Viewport Bounding Verification
        is_within_viewport = (
            r.width > 0 and r.height > 0 and
            r.left < viewport_width and (r.left + r.width) > 0 and
            r.top < viewport_height and (r.top + r.height) > 0 and
            r.cx >= 0 and r.cy >= 0
        )

        # Strict fail-closed initialization:
        # If bridge is None (explicitly unattached), fail closed (is_authentic_hit = False).
        # If bridge is provided, query CDP reverse hit-test and fail closed on exception or occlusion.
        # If bridge is omitted (_OFFLINE_SENTINEL), allow offline unit test verification of viewport & contrast.
        if bridge is None:
            is_authentic_hit = False
            hit_tag = None
            ancestor_bg_stack = None
        elif bridge is not _OFFLINE_SENTINEL:
            is_authentic_hit = False
            hit_tag = None
            ancestor_bg_stack = None

            # 2. Reverse Hit-Test & Ancestor DOM Background Climbing via CDP
            if is_within_viewport:
                try:
                    target_tag_json = json.dumps(element.tag.upper())
                    target_id_json = json.dumps(element.id or "")
                    target_width = float(r.width)
                    target_height = float(r.height)
                    target_cx = float(r.cx)
                    target_cy = float(r.cy)
                    check_script = f"""
                    (() => {{
                        const hit = document.elementFromPoint({int(round(r.cx))}, {int(round(r.cy))});
                        if (!hit) return {{hit: false, tag: null}};
                        const targetTag = {target_tag_json};
                        const targetId = {target_id_json};
                        const targetEl = targetId ? document.getElementById(targetId) : null;
                        const targetWidth = {target_width};
                        const targetHeight = {target_height};
                        const targetCx = {target_cx};
                        const targetCy = {target_cy};
                        
                        let isAuthentic = false;
                        if (targetId) {{
                            if (targetEl) {{
                                isAuthentic = (hit === targetEl) || targetEl.contains(hit);
                            }} else {{
                                isAuthentic = false;
                            }}
                        }} else {{
                            const candidate = (hit.tagName === targetTag) ? hit : hit.closest(targetTag.toLowerCase());
                            if (candidate) {{
                                const hitRect = candidate.getBoundingClientRect();
                                const encompasses = (
                                    hitRect.left <= targetCx + 1 &&
                                    hitRect.right >= targetCx - 1 &&
                                    hitRect.top <= targetCy + 1 &&
                                    hitRect.bottom >= targetCy - 1
                                );
                                const sizeMatches = (
                                    Math.abs(hitRect.width - targetWidth) < 5 &&
                                    Math.abs(hitRect.height - targetHeight) < 5
                                );
                                isAuthentic = (targetEl && (hit === targetEl || targetEl.contains(hit))) || (encompasses && sizeMatches);
                            }} else {{
                                isAuthentic = Boolean(targetEl && (hit === targetEl || targetEl.contains(hit)));
                            }}
                        }}

                        // Climb ancestor background colors from element's parent up to opaque layer
                        const bgStack = [];
                        let curr = (targetEl || hit) ? (targetEl || hit).parentElement : null;
                        while (curr && curr.nodeType === Node.ELEMENT_NODE) {{
                            const style = window.getComputedStyle(curr);
                            const bg = style.backgroundColor;
                            if (bg && bg !== "transparent" && bg !== "rgba(0, 0, 0, 0)") {{
                                bgStack.push(bg);
                                const m = bg.match(/rgba?\\(\\s*[\\d.]+\\s*,\\s*[\\d.]+\\s*,\\s*[\\d.]+(?:\\s*,\\s*([\\d.]+))?\\s*\\)/);
                                if (m) {{
                                    const a = m[1] !== undefined ? parseFloat(m[1]) : 1.0;
                                    if (a >= 0.999) break;
                                }} else if (bg.startsWith("#") && (bg.length === 4 || bg.length === 7)) {{
                                    break;
                                }}
                            }}
                            curr = curr.parentElement;
                        }}

                        return {{
                            hit: Boolean(isAuthentic),
                            tag: hit.tagName,
                            bg_stack: bgStack
                        }};
                    }})()
                    """
                    hit_res = bridge.evaluate(check_script)
                    if hit_res and isinstance(hit_res, dict):
                        is_authentic_hit = bool(hit_res.get("hit", False))
                        hit_tag = hit_res.get("tag") or element.tag
                        if isinstance(hit_res.get("bg_stack"), list):
                            ancestor_bg_stack = [str(b) for b in hit_res.get("bg_stack")]
                except Exception as e:
                    log.warning(f"CDP reverse hit test exception: {e}")
                    is_authentic_hit = False
                    hit_tag = None
        else:
            # Offline unit testing mode when bridge is omitted
            is_authentic_hit = True
            hit_tag = element.tag
            ancestor_bg_stack = None

        # 3. Typography Classification
        try:
            font_size_px = float(re.findall(r"[\d.]+", st.fontSize)[0])
        except (IndexError, ValueError):
            font_size_px = 16.0

        try:
            font_weight = int(re.findall(r"\d+", st.fontWeight)[0])
        except (IndexError, ValueError):
            font_weight = 700 if "bold" in st.fontWeight.lower() else 400

        is_large_text = (font_size_px >= 24.0) or (font_size_px >= 18.66 and font_weight >= 700)
        required_aaa_ratio = 4.5 if is_large_text else 7.0

        # 4. WCAG Luminance & Contrast Calculation with Ancestor Background Climbing
        cr, eff_fg, eff_bg = cls.calculate_contrast_ratio(st.color, st.backgroundColor, ancestor_bg_stack=ancestor_bg_stack)
        passes_wcag_aaa = cr >= required_aaa_ratio

        passed = is_within_viewport and is_authentic_hit and passes_wcag_aaa

        reason = "Pass"
        if not is_within_viewport:
            reason = "Element outside active viewport"
        elif not is_authentic_hit:
            reason = f"Reverse hit-test failed; hit {hit_tag} instead of {element.tag}"
        elif not passes_wcag_aaa:
            reason = f"Contrast ratio {cr}:1 below WCAG AAA required {required_aaa_ratio}:1"

        return VerificationResult(
            is_authentic_hit=is_authentic_hit,
            is_within_viewport=is_within_viewport,
            contrast_ratio=cr,
            passes_wcag_aaa=passes_wcag_aaa,
            passed=passed,
            effective_fg=eff_fg,
            effective_bg=eff_bg,
            required_aaa_ratio=required_aaa_ratio,
            is_large_text=is_large_text,
            hit_tag=hit_tag,
            reason=reason
        )


def main():
    # Verify contrast calculation on dark theme sample
    print("Testing WCAG AAA Contrast Engine:")
    cr, fg, bg = WcagContrastGate.calculate_contrast_ratio("rgb(248, 250, 252)", "transparent")
    print(f"  White over #070B12: CR={cr}:1 (FG={fg}, BG={bg})")

    cr_failing, fg_f, bg_f = WcagContrastGate.calculate_contrast_ratio("rgb(100, 116, 139)", "rgb(15, 23, 42)")
    print(f"  Muted Gray over Dark Slate: CR={cr_failing}:1 (FG={fg_f}, BG={bg_f})")

if __name__ == "__main__":
    main()
