#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Strongest-First Free-Tier Teacher Distillation Pipeline
================================================================================
Subsystem: 06_scripts_and_tooling/benchmarks/gcp_free_tier_distillation_pipeline.py
Governed by:
- Rule #0 (Zero-Mock Empirical Truth Verification)
- Rule #1 & Rule #5 (Victory-Triggered Tri-Proof Interceptor Gate)
- Rule #2 (Tri-Vault Storage Synchronization)
- Rule #3 (Host Sanctuary & Dynamic RAM Governance Invariant)
- Rule #6 (Multi-Provider Cloud Quota & Graduated Autonomy Protocol)
- Rule #8 & Rule #10 (Sovereign Local AI Hierarchy: Qwen 3.8 Max + Apple Silicon Metal)

Role:
1. Always harnesses the strongest available Google AI Studio Free-Tier model
   (gemini-3.8-flash -> gemini-3.7-flash -> gemini-3.6-flash -> gemini-3.5-flash -> local Qwen 3.8 Max).
2. Evaluates response quality through QualityGate (syntax AST, length, zero-mock).
3. Synthesizes high-fidelity Chain-of-Thought (CoT) teacher reasoning and DPO pairs.
4. Serializes training datasets into 04_data_and_memory/free_tier_harvest/.
5. Enforces Zero-Spend Circuit Breaker checks before every invocation ($0.00 cost).
================================================================================
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

try:
    from gcp_free_tier_circuit_breaker import GCPFreeTierCircuitBreaker
except ImportError:
    GCPFreeTierCircuitBreaker = None

try:
    from strongest_free_tier_client import StrongestFreeTierClient, QualityGate, FallbackResponse
except ImportError:
    StrongestFreeTierClient = None
    QualityGate = None
    FallbackResponse = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [FreeDistillation] %(message)s"
)
logger = logging.getLogger("FreeDistillation")

OUTPUT_DATASET = REPO_ROOT / "04_data_and_memory/free_tier_harvest/gemini_distillation_pairs.jsonl"


class FreeTierDistillationPipeline:
    """Distillation pipeline harnessing Google AI Studio Free Tier with strongest-first waterfall."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,  # Optional override, defaults to strongest waterfall
        min_interval_seconds: float = 4.2,  # 15 RPM = 60/15 = 4.0s + 0.2s buffer
        circuit_breaker: Optional[Any] = None,
        client: Optional[Any] = None,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.min_interval_seconds = min_interval_seconds
        self.circuit_breaker = circuit_breaker or (
            GCPFreeTierCircuitBreaker() if GCPFreeTierCircuitBreaker else None
        )

        if client:
            self.client = client
        elif StrongestFreeTierClient:
            custom_waterfall = None
            if model_name:
                custom_waterfall = [
                    {"id": model_name, "name": model_name, "tier": 1, "type": "cloud"}
                ]
            self.client = StrongestFreeTierClient(
                api_key=self.api_key,
                waterfall=custom_waterfall,
                min_interval_seconds=self.min_interval_seconds,
                circuit_breaker=self.circuit_breaker,
            )
        else:
            self.client = None

    def generate_distillation_pair(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        expect_code: bool = False,
        min_length: int = 60,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Generates a verified high-quality teacher distillation pair via the strongest free model."""
        if not self.api_key:
            return False, {}, "GEMINI_API_KEY is not configured"

        if not self.client:
            return False, {}, "StrongestFreeTierClient is not available"

        gate = QualityGate(
            min_length=min_length,
            expect_code=expect_code,
            strict_zero_mock=True,
        ) if QualityGate else None

        resp = self.client.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            quality_gate=gate,
            temperature=0.2,
        )

        if not resp.success:
            return False, {}, resp.error_message or "Waterfall exhausted without passing QualityGate"

        distillation_record = {
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "teacher_model": resp.model_used,
            "teacher_tier": resp.model_tier,
            "tier": "Free Tier (Unbilled)",
            "quality_score": resp.quality_score,
            "latency_seconds": resp.latency_seconds,
            "fallback_steps_count": len(resp.fallback_path) - 1,
            "input_prompt": prompt,
            "teacher_reasoning": resp.text,
            "cost_usd": 0.00,
            "is_local": resp.is_local,
        }

        # Append to dataset
        OUTPUT_DATASET.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_DATASET, "a", encoding="utf-8") as f:
            f.write(json.dumps(distillation_record) + "\n")

        logger.info(
            f"Generated high-quality distillation pair via {resp.model_used} "
            f"(Score: {resp.quality_score}, {len(resp.text)} chars, $0.00)"
        )
        return True, distillation_record, "OK"


def main() -> None:
    pipeline = FreeTierDistillationPipeline()
    print("================================================================================")
    print("🧬 TESTING STRONGEST-FIRST FREE-TIER DISTILLATION PIPELINE")
    print("================================================================================")
    test_prompt = (
        "Explain in 2 concise sentences how Pan-Tompkins QRS detection isolates "
        "the 512Hz ECG R-peak using derivative and moving-window integration."
    )
    ok, record, msg = pipeline.generate_distillation_pair(
        test_prompt,
        system_instruction="You are a medical biometrics DSP engineer adhering to zero-mock principles."
    )
    print(f"Distillation Generation: {'✅ SUCCESS' if ok else '❌ FAILED'} ({msg})")
    if ok:
        print(f"Model Used: {record.get('teacher_model')} (Tier {record.get('teacher_tier')})")
        print(f"Quality Score: {record.get('quality_score')}")
        print("Teacher Reasoning:")
        print(record.get("teacher_reasoning", "").strip())
        print(f"Recorded in: {OUTPUT_DATASET}")


if __name__ == "__main__":
    main()
