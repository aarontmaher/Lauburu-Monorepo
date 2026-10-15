#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
01_apps/screen_lens/src/screen_lens_closed_loop_fix_engine.py
================================================================================
Screen Lens Sovereign — Closed-Loop Visual Analysis & Autonomous Repair Engine.

Governed by:
- Rule #0 (Zero-Mock & Authentic Verification)
- Rule #5 (Victory-Triggered Tri-Proof Interceptor Gate)
- Rule #7 (Live Screen & Device Telemetry)

Core Architecture:
1. Stage 1: Screen Perception (What is ON the screen) -> S_actual
2. Stage 2: Ground-Truth Specification (What SHOULD be on screen) -> S_expected
3. Stage 3: Discrepancy & Root Cause Localization -> Delta(S_actual, S_expected)
4. Stage 4: Autonomous Remediation Synthesis & Actuation -> Patch Application
5. Stage 5: Post-Fix Visual Re-Perception Verification -> Delta_new -> 0
================================================================================
"""

import os
import sys
import json
import time
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")


class ObservedScreenState:
    """Represents the multi-modal state extracted from the screen."""
    def __init__(
        self,
        elements: List[Dict[str, Any]],
        text_content: List[str],
        error_banners: List[str],
        layout_anomalies: List[str],
        contrast_violations: List[str],
        mock_data_violations: List[str]
    ):
        self.elements = elements
        self.text_content = text_content
        self.error_banners = error_banners
        self.layout_anomalies = layout_anomalies
        self.contrast_violations = contrast_violations
        self.mock_data_violations = mock_data_violations

    @property
    def is_flawless(self) -> bool:
        return (
            len(self.error_banners) == 0 and
            len(self.layout_anomalies) == 0 and
            len(self.contrast_violations) == 0 and
            len(self.mock_data_violations) == 0
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elements_count": len(self.elements),
            "text_content": self.text_content,
            "error_banners": self.error_banners,
            "layout_anomalies": self.layout_anomalies,
            "contrast_violations": self.contrast_violations,
            "mock_data_violations": self.mock_data_violations,
            "is_flawless": (
                len(self.error_banners) == 0 and
                len(self.layout_anomalies) == 0 and
                len(self.contrast_violations) == 0 and
                len(self.mock_data_violations) == 0
            )
        }


class ScreenSpecContract:
    """Defines what SHOULD be on the screen according to ground-truth invariants."""
    def __init__(
        self,
        required_elements: List[str],
        forbidden_patterns: List[str],
        max_container_width: Optional[int] = None,
        zero_mock_enforced: bool = True,
        min_contrast_ratio: float = 7.0
    ):
        self.required_elements = required_elements
        self.forbidden_patterns = forbidden_patterns
        self.max_container_width = max_container_width
        self.zero_mock_enforced = zero_mock_enforced
        self.min_contrast_ratio = min_contrast_ratio


class DiscrepancyReport:
    """Calculates Delta(S_actual, S_expected)."""
    def __init__(
        self,
        missing_elements: List[str],
        forbidden_found: List[str],
        layout_overflows: List[str],
        mock_violations: List[str],
        error_messages: List[str],
        root_cause_hints: List[str]
    ):
        self.missing_elements = missing_elements
        self.forbidden_found = forbidden_found
        self.layout_overflows = layout_overflows
        self.mock_violations = mock_violations
        self.error_messages = error_messages
        self.root_cause_hints = root_cause_hints

    @property
    def has_defects(self) -> bool:
        return any([
            self.missing_elements,
            self.forbidden_found,
            self.layout_overflows,
            self.mock_violations,
            self.error_messages
        ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_defects": self.has_defects,
            "missing_elements": self.missing_elements,
            "forbidden_found": self.forbidden_found,
            "layout_overflows": self.layout_overflows,
            "mock_violations": self.mock_violations,
            "error_messages": self.error_messages,
            "root_cause_hints": self.root_cause_hints
        }


class ScreenLensClosedLoopFixEngine:
    """
    Central Closed-Loop Engine for Screen Lens Sovereign.
    Orchestrates the complete analyze -> specify -> delta -> repair -> verify loop.
    """

    def __init__(self, workspace: Path = WORKSPACE):
        self.workspace = Path(workspace)

    def perceive_screen(
        self,
        dom_or_markup: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080
    ) -> ObservedScreenState:
        """
        Stage 1: Analyzes what is currently rendered on screen.
        Extracts visual elements, text content, error toasts, and layout constraints.
        """
        elements = []
        text_content = []
        error_banners = []
        layout_anomalies = []
        contrast_violations = []
        mock_data_violations = []

        # 1. Detect Error Banners / Exceptions
        error_matches = re.findall(
            r'(?:class=[\'"][^\'"]*error[^\'"]*[\'"]|role=[\'"]alert[\'"])[^>]*>(.*?)<',
            dom_or_markup,
            re.IGNORECASE | re.DOTALL
        )
        for err in error_matches:
            clean_err = err.strip()
            if clean_err:
                error_banners.append(clean_err)

        # Detect raw unhandled errors or 404/500 strings
        for raw_err in re.findall(r'(?:TypeError|ReferenceError|ECONNREFUSED|404 Not Found|500 Internal Server Error)[^<]*', dom_or_markup):
            if raw_err.strip() and raw_err.strip() not in error_banners:
                error_banners.append(raw_err.strip())

        # 2. Detect Fixed-Width Overflow Anomalies
        fixed_widths = re.findall(r'width:\s*([0-9]+)px', dom_or_markup)
        for w_str in fixed_widths:
            w_val = int(w_str)
            if w_val > viewport_width:
                layout_anomalies.append(f"Fixed width {w_val}px exceeds viewport {viewport_width}px (Horizontal Overflow)")

        # Detect hardcoded width exceeding mobile responsive containers (e.g. 1200px without max-width)
        if "width: 1200px" in dom_or_markup and "max-width: 100%" not in dom_or_markup:
            layout_anomalies.append("Hardcoded desktop container width (1200px) lacks responsive constraint max-width: 100%")

        # 3. Detect Rule #0 Mock Data Violations
        mock_patterns = [
            (r'\b72(?:\.0)?\s*BPM\b', "Mock Heart Rate (72 BPM) detected; must render '-- BPM' until authentic sensor frame arrives"),
            (r'\b48\.5\s*ms\b', "Mock Latency (48.5 ms) detected; must show authentic measured RTT or '-- ms'"),
            (r'\b50%\s*Recovery\b', "Mock Recovery percentage detected"),
            (r'\[\s*10,\s*20,\s*30,\s*40\s*\]', "Synthetic mock array detected; violates Rule #0")
        ]
        for pat, desc in mock_patterns:
            if re.search(pat, dom_or_markup):
                mock_data_violations.append(desc)

        # 4. Extract Text Content & Elements
        text_content = [t.strip() for t in re.findall(r'>([^<]+)<', dom_or_markup) if t.strip()]

        for tag in re.findall(r'<([a-zA-Z0-9]+)[^>]*>', dom_or_markup):
            elements.append({"tag": tag.lower()})

        return ObservedScreenState(
            elements=elements,
            text_content=text_content,
            error_banners=error_banners,
            layout_anomalies=layout_anomalies,
            contrast_violations=contrast_violations,
            mock_data_violations=mock_data_violations
        )

    def evaluate_against_spec(
        self,
        observed: ObservedScreenState,
        spec: ScreenSpecContract,
        raw_markup: str
    ) -> DiscrepancyReport:
        """
        Stage 2 & 3: Compares Observed (What IS on screen) against Spec (What SHOULD be on screen).
        Calculates the delta and pinpoints root-cause hints.
        """
        missing_elements = []
        forbidden_found = []
        root_cause_hints = []

        for req in spec.required_elements:
            if not any(req.lower() in t.lower() for t in observed.text_content) and req not in raw_markup:
                missing_elements.append(req)
                root_cause_hints.append(f"Required element '{req}' missing from rendered DOM tree.")

        for forb in spec.forbidden_patterns:
            if forb in raw_markup or any(forb in t for t in observed.text_content):
                forbidden_found.append(forb)
                root_cause_hints.append(f"Forbidden pattern '{forb}' rendered on screen.")

        if spec.zero_mock_enforced and observed.mock_data_violations:
            for v in observed.mock_data_violations:
                root_cause_hints.append(f"Rule #0 Violation: {v}")

        for anomaly in observed.layout_anomalies:
            root_cause_hints.append(f"Layout Defect: {anomaly}")

        for err in observed.error_banners:
            root_cause_hints.append(f"Runtime Crash/Error: {err}")

        return DiscrepancyReport(
            missing_elements=missing_elements,
            forbidden_found=forbidden_found,
            layout_overflows=observed.layout_anomalies,
            mock_violations=observed.mock_data_violations,
            error_messages=observed.error_banners,
            root_cause_hints=root_cause_hints
        )

    def localize_root_cause(
        self,
        discrepancy: DiscrepancyReport,
        target_source_code: str
    ) -> Dict[str, Any]:
        """
        Stage 3: Maps the discrepancy to specific lines in the target source code.
        """
        lines = target_source_code.splitlines()
        offending_lines = []

        if discrepancy.mock_violations:
            for idx, line in enumerate(lines, 1):
                if re.search(r'72(?:\.0)?\s*BPM|48\.5|fake|mock', line, re.IGNORECASE):
                    offending_lines.append({"line": idx, "content": line.strip(), "issue": "Hardcoded mock value"})

        if discrepancy.layout_overflows:
            for idx, line in enumerate(lines, 1):
                if "width: 1200px" in line or "width:1200px" in line:
                    offending_lines.append({"line": idx, "content": line.strip(), "issue": "Rigid desktop width lacking responsive constraint"})

        if discrepancy.error_messages:
            for idx, line in enumerate(lines, 1):
                for err in discrepancy.error_messages:
                    if "TypeError" in err and any(term in line for term in ["user.profile", "metrics", "data.reading"]):
                        offending_lines.append({"line": idx, "content": line.strip(), "issue": "Missing null guard / optional chaining"})
                    elif "ECONNREFUSED" in err and "3000" in line:
                        offending_lines.append({"line": idx, "content": line.strip(), "issue": "Misconfigured port endpoint (3000 instead of 4000)"})

        return {
            "discrepancy_count": len(discrepancy.root_cause_hints),
            "offending_lines": offending_lines,
            "suggested_actions": discrepancy.root_cause_hints
        }

    def execute_closed_loop_repair(
        self,
        candidate_name: str,
        challenge_id: str,
        initial_source: str,
        spec: ScreenSpecContract,
        patch_fn
    ) -> Dict[str, Any]:
        """
        Full Closed-Loop Execution:
        1. Perceive initial state
        2. Compute discrepancy
        3. Localize root cause
        4. Synthesize patch via candidate model/fn
        5. Apply patch
        6. Re-perceive new state
        7. Evaluate against spec -> verify Delta_new == 0
        """
        start_time = time.time()

        obs_initial = self.perceive_screen(initial_source)
        discrepancy_initial = self.evaluate_against_spec(obs_initial, spec, initial_source)

        if not discrepancy_initial.has_defects:
            return {
                "candidate": candidate_name,
                "challenge_id": challenge_id,
                "success": True,
                "status": "NO_INITIAL_DEFECTS",
                "latency_ms": (time.time() - start_time) * 1000
            }

        localization = self.localize_root_cause(discrepancy_initial, initial_source)

        patch_result = patch_fn(
            candidate_name=candidate_name,
            challenge_id=challenge_id,
            source_code=initial_source,
            discrepancy=discrepancy_initial,
            localization=localization
        )

        repaired_source = patch_result.get("repaired_code", initial_source)
        patch_diff = "".join(difflib.unified_diff(
            initial_source.splitlines(keepends=True),
            repaired_source.splitlines(keepends=True),
            fromfile="before_fix.html",
            tofile="after_fix.html"
        ))

        obs_repaired = self.perceive_screen(repaired_source)
        discrepancy_repaired = self.evaluate_against_spec(obs_repaired, spec, repaired_source)

        elapsed_ms = (time.time() - start_time) * 1000
        is_fixed = not discrepancy_repaired.has_defects

        return {
            "candidate": candidate_name,
            "challenge_id": challenge_id,
            "initial_defects_count": len(discrepancy_initial.root_cause_hints),
            "remaining_defects_count": len(discrepancy_repaired.root_cause_hints),
            "is_fixed": is_fixed,
            "localization_accuracy": 1.0 if localization["offending_lines"] else 0.0,
            "patch_diff": patch_diff,
            "latency_ms": round(elapsed_ms, 2),
            "obs_initial": obs_initial.to_dict(),
            "obs_repaired": obs_repaired.to_dict(),
            "remaining_defects": discrepancy_repaired.root_cause_hints
        }


if __name__ == "__main__":
    engine = ScreenLensClosedLoopFixEngine()
    print("Screen Lens Closed-Loop Fix Engine initialized successfully.")
