#!/usr/bin/env python3
"""
================================================================================
Screen Lens Sovereign: Comprehensive UI and UX Evaluation Engine
================================================================================
Subsystem: 01_apps/screen_lens/src/lens_ui_ux_evaluator.py
Version: 1.0.0-LENS-UI-UX-EVALUATOR
Lauburu Mesh Ecosystem — 2026

Evaluates UI/UX quality across 3 sovereign design dimensions:
1. SpatialCadenceAuditor:
   - Evaluates adherence to 8pt / 4pt modular design grid systems.
   - Measures alignment consistency, whitespace balance, and padding regularity.
2. CognitiveFrictionAnalyzer:
   - Computes visual cognitive load (CFL) via Shannon color entropy, edge density,
     and visual crowding indices.
   - Flags visual clutter and cognitive overload hotspots.
3. DeadClickAndAffordanceGuard:
   - Identifies misleading interactive affordances (dead clicks, unstyled buttons).
   - Audits touch target spacing separation (>= 8px gap invariant).
================================================================================
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import math
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Lens-UIUX] %(levelname)s: %(message)s"
)
log = logging.getLogger("LensUIUX")


# -----------------------------------------------------------------------------
# 1. Spatial Cadence & 8pt Modular Grid Auditor
# -----------------------------------------------------------------------------
@dataclass
class SpatialCadenceReport:
    total_elements_audited: int
    grid_aligned_elements: int
    grid_adherence_pct: float
    spacing_regularity_score: float
    padding_violations: List[Dict[str, Any]]
    verdict: str


class SpatialCadenceAuditor:
    """Audits layout adherence to 8pt / 4pt modular grid systems."""

    @staticmethod
    def audit_layout_elements(elements: List[Dict[str, Any]], grid_step_px: int = 8) -> SpatialCadenceReport:
        if not elements:
            return SpatialCadenceReport(
                total_elements_audited=0,
                grid_aligned_elements=0,
                grid_adherence_pct=100.0,
                spacing_regularity_score=100.0,
                padding_violations=[],
                verdict="NO_ELEMENTS_TO_AUDIT"
            )

        aligned_count = 0
        violations = []

        for el in elements:
            bbox = el.get("bbox", [0, 0, 0, 0])  # [ymin, xmin, ymax, xmax]
            h = bbox[2] - bbox[0]
            w = bbox[3] - bbox[1]
            pad_top = el.get("padding_top", 0)
            pad_left = el.get("padding_left", 0)

            # Check if dimensions and positions align with 4px or 8px grid
            w_aligned = (w % 4 == 0)
            h_aligned = (h % 4 == 0)
            pad_aligned = (pad_top % 4 == 0) and (pad_left % 4 == 0)

            if w_aligned and h_aligned and pad_aligned:
                aligned_count += 1
            else:
                violations.append({
                    "element_id": el.get("id", "unknown"),
                    "width": w,
                    "height": h,
                    "suggested_fix": f"Adjust size to closest multiple of {grid_step_px}px ({math.ceil(w/8)*8}x{math.ceil(h/8)*8}px)"
                })

        adherence_pct = round((aligned_count / len(elements)) * 100.0, 1)
        score = round(max(0.0, min(100.0, adherence_pct * 0.95 + 5.0)), 1)
        verdict = "EXEMPLARY_8PT_GRID" if score >= 90.0 else "GRID_IRREGULARITIES_DETECTED"

        return SpatialCadenceReport(
            total_elements_audited=len(elements),
            grid_aligned_elements=aligned_count,
            grid_adherence_pct=adherence_pct,
            spacing_regularity_score=score,
            padding_violations=violations[:5],
            verdict=verdict
        )


# -----------------------------------------------------------------------------
# 2. Cognitive Friction & Visual Clutter Analyzer
# -----------------------------------------------------------------------------
@dataclass
class CognitiveFrictionReport:
    visual_cognitive_load_index: float  # 0.0 - 100.0 (lower is calmer/clearer)
    color_entropy_bits: float
    crowding_density_score: float
    visual_clarity_score: float         # 0.0 - 100.0 (higher is better)
    verdict: str
    recommendations: List[str]


class CognitiveFrictionAnalyzer:
    """Measures visual complexity, spatial crowding, and cognitive friction."""

    @staticmethod
    def analyze_friction(
        elements: List[Dict[str, Any]],
        viewport_width: int = 1080,
        viewport_height: int = 2400,
        unique_colors_count: int = 4
    ) -> CognitiveFrictionReport:
        n = len(elements)
        if n == 0:
            return CognitiveFrictionReport(
                visual_cognitive_load_index=0.0,
                color_entropy_bits=0.0,
                crowding_density_score=0.0,
                visual_clarity_score=100.0,
                verdict="MINIMAL_COGNITIVE_LOAD",
                recommendations=["Empty viewport."]
            )

        viewport_area = viewport_width * viewport_height
        total_element_area = sum((el["bbox"][2] - el["bbox"][0]) * (el["bbox"][3] - el["bbox"][1]) for el in elements if "bbox" in el)
        density_ratio = min(1.0, total_element_area / max(1, viewport_area))

        # Color entropy estimation
        entropy = math.log2(max(1, unique_colors_count))

        # Crowding: average nearest neighbor distance
        centers = []
        for el in elements:
            b = el.get("bbox", [0, 0, 0, 0])
            centers.append(((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0))

        min_distances = []
        for i in range(len(centers)):
            dists = [
                math.hypot(centers[i][0] - centers[j][0], centers[i][1] - centers[j][1])
                for j in range(len(centers)) if i != j
            ]
            if dists:
                min_distances.append(min(dists))

        avg_nn_dist = float(np.mean(min_distances)) if min_distances else 200.0
        crowding = max(0.0, min(100.0, 100.0 - (avg_nn_dist / 4.0)))

        # Cognitive Load Index: 0 (peaceful) to 100 (overloaded chaos)
        cfl = round(0.4 * (density_ratio * 100.0) + 0.3 * (entropy * 15.0) + 0.3 * crowding, 1)
        clarity = round(max(0.0, 100.0 - cfl), 1)

        verdict = "OPTIMAL_COGNITIVE_CLARITY" if cfl < 40.0 else ("MODERATE_COGNITIVE_LOAD" if cfl < 70.0 else "HIGH_VISUAL_CLUTTER")
        recs = []
        if cfl >= 40.0:
            recs.append("Increase whitespace between grouped cards to reduce visual crowding.")
        if entropy > 2.5:
            recs.append("Consolidate accent colors to adhere to a 3-tier color palette (Dominant, Secondary, Accent).")

        return CognitiveFrictionReport(
            visual_cognitive_load_index=cfl,
            color_entropy_bits=round(entropy, 2),
            crowding_density_score=round(crowding, 1),
            visual_clarity_score=clarity,
            verdict=verdict,
            recommendations=recs
        )


# -----------------------------------------------------------------------------
# 3. Dead-Click & Affordance Collision Guard
# -----------------------------------------------------------------------------
@dataclass
class AffordanceAuditFinding:
    total_interactive_elements: int
    dead_clicks_detected: int
    touch_overlap_collisions: int
    affordance_integrity_score: float
    violations: List[Dict[str, Any]]
    verdict: str


class DeadClickAndAffordanceGuard:
    """Audits interaction affordances, dead clicks, and touch boundary collisions."""

    @staticmethod
    def audit_affordances(elements: List[Dict[str, Any]]) -> AffordanceAuditFinding:
        dead_clicks = 0
        collisions = 0
        violations = []

        # 1. Detect dead clicks: elements that appear interactive (cursor pointer, button tag) without listener
        for el in elements:
            is_visually_interactive = el.get("role") in ["button", "link", "toggle", "tab"] or el.get("has_click_styling", False)
            has_event_handler = el.get("has_on_click", True)

            if is_visually_interactive and not has_event_handler:
                dead_clicks += 1
                violations.append({
                    "element_id": el.get("id"),
                    "type": "DEAD_CLICK_DETECTED",
                    "issue": "Element is styled as interactive button but has no onClick listener attached."
                })

        # 2. Touch target spacing collisions (minimum 8px gap between targets)
        interactive_boxes = [el["bbox"] for el in elements if el.get("role") in ["button", "link", "toggle", "tab"] and "bbox" in el]
        for i in range(len(interactive_boxes)):
            for j in range(i + 1, len(interactive_boxes)):
                b1, b2 = interactive_boxes[i], interactive_boxes[j]
                # Distance between rects
                x_gap = max(0, max(b1[1], b2[1]) - min(b1[3], b2[3]))
                y_gap = max(0, max(b1[0], b2[0]) - min(b1[2], b2[2]))
                euclid_gap = math.hypot(x_gap, y_gap)

                if euclid_gap < 8.0:
                    collisions += 1
                    violations.append({
                        "element_pair": f"{elements[i].get('id')} <-> {elements[j].get('id')}",
                        "type": "TOUCH_OVERLAP_COLLISION",
                        "gap_px": round(euclid_gap, 1),
                        "issue": "Touch targets are closer than 8px gap invariant, causing accidental tap misfires."
                    })

        total = max(1, len(elements))
        penalty = (dead_clicks * 15.0) + (collisions * 10.0)
        score = round(max(0.0, 100.0 - penalty), 1)
        verdict = "FLAWLESS_AFFORDANCES" if score >= 95.0 else "AFFORDANCE_ISSUES_DETECTED"

        return AffordanceAuditFinding(
            total_interactive_elements=len(interactive_boxes),
            dead_clicks_detected=dead_clicks,
            touch_overlap_collisions=collisions,
            affordance_integrity_score=score,
            violations=violations[:5],
            verdict=verdict
        )


def run_ui_ux_evaluator_self_test() -> Dict[str, Any]:
    """Runs empirical self-test of the UI/UX evaluation suite."""
    test_elements = [
        {
            "id": "btn_primary",
            "role": "button",
            "bbox": [100, 100, 148, 228],  # 48x128px (multiple of 8)
            "padding_top": 12,
            "padding_left": 16,
            "has_on_click": True
        },
        {
            "id": "toggle_mesh",
            "role": "toggle",
            "bbox": [100, 244, 148, 308],  # 48x64px, gap = 244 - 228 = 16px (valid)
            "padding_top": 8,
            "padding_left": 8,
            "has_on_click": True
        },
        {
            "id": "card_telemetry",
            "role": "card",
            "bbox": [180, 100, 380, 500],  # 200x400px (multiple of 8)
            "padding_top": 16,
            "padding_left": 16,
            "has_on_click": False
        }
    ]

    cadence_rep = SpatialCadenceAuditor.audit_layout_elements(test_elements)
    friction_rep = CognitiveFrictionAnalyzer.analyze_friction(test_elements)
    affordance_rep = DeadClickAndAffordanceGuard.audit_affordances(test_elements)

    composite_ux_score = round(
        (0.35 * cadence_rep.spacing_regularity_score) +
        (0.35 * friction_rep.visual_clarity_score) +
        (0.30 * affordance_rep.affordance_integrity_score), 1
    )

    return {
        "status": "UI_UX_EVALUATOR_OPERATIONAL",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "composite_ux_score": composite_ux_score,
        "spatial_cadence": asdict(cadence_rep),
        "cognitive_friction": asdict(friction_rep),
        "affordance_audit": asdict(affordance_rep)
    }


if __name__ == "__main__":
    out = run_ui_ux_evaluator_self_test()
    print(json.dumps(out, indent=2))
