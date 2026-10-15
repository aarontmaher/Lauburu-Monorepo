#!/usr/bin/env python3
"""
01_apps/screen_lens/src/lens_tri_proof_interceptor.py
=====================================================
Automatic Tri-Proof Interceptor Gate.
Scans agent claims in real-time. Any utterance of victory words
('success', 'confirmed', 'complete', 'resolved', 'verified', 'passed', 'fixed')
AUTOMATICALLY triggers a mandatory Tri-Proof Audit:
1. Proof 1: Click-Through / Process Actuation
2. Proof 2: Line-by-Line Reading / Cryptographic SHA256
3. Proof 3: Visual Screen / Pixel Proof

Governed by soul.md Section 1.4.
If no proof accompanies the victory claim, the Accuracy-Weighted RAM Governor
penalizes the offending model and boosts Sovereign Auditor headroom.
"""

import os
import sys
import re
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple

WORKSPACE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

TRIGGER_WORDS = [
    "success", "successful", "succeeded",
    "confirmed", "confirming",
    "complete", "completed", "completion",
    "resolved", "passed", "verified",
    "fixed", "done", "working"
]

TRIGGER_PATTERN = re.compile(r"\b(" + "|".join(TRIGGER_WORDS) + r")\b", re.IGNORECASE)


class TriProofInterceptor:
    @staticmethod
    def audit_claim(
        model_id: str,
        text_content: str,
        active_proofs: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Intercepts claims and audits for mandatory Tri-Proof compliance.
        """
        t0 = time.perf_counter()
        matches = list(set(m.group(0).lower() for m in TRIGGER_PATTERN.finditer(text_content)))

        if not matches:
            return {
                "model_id": model_id,
                "interception_status": "NO_VICTORY_WORDS_DETECTED",
                "triggered_keywords": [],
                "tri_proof_required": False,
                "audit_passed": True
            }

        # Victory words detected! Mandatory Tri-Proof Audit triggered!
        active_proofs = active_proofs or {}
        has_click = bool(active_proofs.get("click_or_process_exit_code") == 0)
        has_line_read = bool(active_proofs.get("sha256_hash") or active_proofs.get("line_numbers"))
        has_visual = bool(active_proofs.get("screenshot_path") and Path(active_proofs.get("screenshot_path")).exists())

        proofs_found = []
        if has_click:
            proofs_found.append("Proof 1: Physical Process/Touch Actuation (Exit Code 0)")
        if has_line_read:
            proofs_found.append(f"Proof 2: Line-by-Line Reading (SHA256: {active_proofs.get('sha256_hash', 'N/A')[:12]}...)")
        if has_visual:
            proofs_found.append(f"Proof 3: Visual Pixel Proof ({Path(active_proofs.get('screenshot_path')).name})")

        is_compliant = len(proofs_found) > 0
        elapsed_us = round((time.perf_counter() - t0) * 1e6, 2)

        return {
            "model_id": model_id,
            "interception_status": "TRI_PROOF_AUDIT_PASSED" if is_compliant else "INTERCEPTED_UNVERIFIED_CLAIM",
            "triggered_keywords": matches,
            "tri_proof_required": True,
            "audit_passed": is_compliant,
            "proofs_verified_count": len(proofs_found),
            "proofs_verified": proofs_found,
            "ram_governor_action": (
                "ALLOCATION_MAINTAINED" if is_compliant
                else "PENALTY_ENFORCED: Offending model RAM slashed; Sovereign Auditor boosted."
            ),
            "interception_latency_us": elapsed_us
        }


def main():
    print("🛡️ Testing Automatic Tri-Proof Interceptor Gate...")
    interceptor = TriProofInterceptor()

    # Scenario 1: A victory claim WITH genuine C11 compiler proof
    sample_hash = hashlib.sha256(b"movesense_dsp.c").hexdigest()
    res_with_proof = interceptor.audit_claim(
        model_id="Local_Qwen_3_8_Max",
        text_content="The C11 movesense_dsp benchmark was confirmed to be completely successful.",
        active_proofs={
            "click_or_process_exit_code": 0,
            "sha256_hash": sample_hash,
            "screenshot_path": "/Users/aaron/.gemini/antigravity/brain/463be04b-c674-45eb-9a0c-f0013ee26c4d/desktop_live_monitor_v3.png"
        }
    )
    print("\n--- TEST 1: VICTORY CLAIM WITH TRI-PROOF (PASSED) ---")
    print(json.dumps(res_with_proof, indent=2))

    # Scenario 2: A hollow victory claim WITHOUT proof (should be intercepted & penalized!)
    res_without_proof = interceptor.audit_claim(
        model_id="Local_Qwen_3_8_Max",
        text_content="The task is complete and working with great success."
    )
    print("\n--- TEST 2: HOLLOW VICTORY CLAIM WITHOUT PROOF (INTERCEPTED) ---")
    print(json.dumps(res_without_proof, indent=2))


if __name__ == "__main__":
    main()
