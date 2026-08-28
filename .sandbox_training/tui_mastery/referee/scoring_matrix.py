#!/usr/bin/env python3
"""Abliterated 70B Referee Scoring Matrix & Multi-Factor Fitness Model.

Calculates the closed-form composite tournament fitness score S_composite:
    S_composite = (w_mem * S_mem) + (w_lat * S_lat) + (w_rob * S_rob) + (w_qual * S_qual)

Standard Baseline Weights:
- Memory Efficiency (w_mem)        : 0.25 (25%)
- Latency & Throughput (w_lat)     : 0.25 (25%)
- Attack Robustness (w_rob)        : 0.30 (30%)
- Code Quality & Truth (w_qual)    : 0.20 (20%)

Key Invariants:
1. Disqualification Rule: Any unhandled panic or crash yields S_rob = 0.0.
2. Boundedness: All component scores and S_composite are bounded in [0.0, 100.0].
3. NPU Bonus Formula:
       Bonus NPU Hours = min(50.0, 25.0 + 0.5 * max(0.0, S_composite - 70.0))
4. Tie-Breaking Order: S_composite -> S_rob -> S_mem -> S_lat -> S_qual.
5. Refusal Direction Ablation Math:
       h_clean = h - (h . r) * r
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def calculate_refusal_ablation(h: List[float], r: List[float]) -> List[float]:
    """Calculates directional refusal ablation: h_clean = h - (h . r) * r.
    Assumes r is a normalized unit vector (|r| = 1.0).
    """
    assert len(h) == len(r), "Vector dimensions must match"
    dot_product = sum(a * b for a, b in zip(h, r))
    return [a - dot_product * b for a, b in zip(h, r)]


@dataclass
class ScoreBreakdown:
    framework: str
    memory_score: float
    latency_score: float
    robustness_score: float
    code_quality_score: float
    composite_score: float
    panics_count: int
    status: str
    bonus_npu_hours: float
    weights_used: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_score": round(self.memory_score, 2),
            "latency_score": round(self.latency_score, 2),
            "robustness_score": round(self.robustness_score, 2),
            "code_quality_score": round(self.code_quality_score, 2),
            "composite_score": round(self.composite_score, 2),
            "panics_count": self.panics_count,
            "status": self.status,
            "bonus_npu_hours": round(self.bonus_npu_hours, 2),
        }


DEFAULT_SCORING_WEIGHTS = {
    "memory_efficiency": 0.25,
    "latency_throughput": 0.25,
    "attack_robustness": 0.30,
    "code_quality_and_truth": 0.20,
}

CHAOS_SURGE_WEIGHTS = {
    "memory_efficiency": 0.20,
    "latency_throughput": 0.20,
    "attack_robustness": 0.40,
    "code_quality_and_truth": 0.20,
}


def calculate_composite_score(
    mem_score: float,
    lat_score: float,
    rob_score: float,
    qual_score: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate closed-form composite score with weights summing to 1.0."""
    w = weights or DEFAULT_SCORING_WEIGHTS
    w_mem = w.get("memory_efficiency", 0.25)
    w_lat = w.get("latency_throughput", 0.25)
    w_rob = w.get("attack_robustness", 0.30)
    w_qual = w.get("code_quality_and_truth", 0.20)

    total_weight = w_mem + w_lat + w_rob + w_qual
    if not math.isclose(total_weight, 1.0, rel_tol=1e-5):
        w_mem /= total_weight
        w_lat /= total_weight
        w_rob /= total_weight
        w_qual /= total_weight

    mem = max(0.0, min(100.0, mem_score))
    lat = max(0.0, min(100.0, lat_score))
    rob = max(0.0, min(100.0, rob_score))
    qual = max(0.0, min(100.0, qual_score))

    composite = (w_mem * mem) + (w_lat * lat) + (w_rob * rob) + (w_qual * qual)
    return round(max(0.0, min(100.0, composite)), 4)


def calculate_npu_bonus_hours(
    composite_score: float,
    base_hours: float = 25.0,
    scaling_factor: float = 0.5,
    threshold: float = 70.0,
    max_hours: float = 50.0,
) -> float:
    """Calculate NPU Bonus Grant hours based on performance."""
    bonus = base_hours + scaling_factor * max(0.0, composite_score - threshold)
    return min(max_hours, round(bonus, 2))


class ScoringMatrix:
    """Scoring matrix engine for evaluating candidates in the Red vs Blue arena."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_SCORING_WEIGHTS

    def evaluate_candidate(
        self,
        framework: str,
        peak_rss_mb: float,
        avg_latency_ms: float,
        scenarios_survived: int,
        total_scenarios: int,
        panics_count: int,
        lint_issues: int = 0,
        zero_mock_certified: bool = True,
        max_acceptable_rss_mb: float = 150.0,
        max_acceptable_latency_ms: float = 50.0,
    ) -> ScoreBreakdown:
        """Compute full multi-factor score breakdown for a given candidate."""
        # 1. Memory Score
        if peak_rss_mb <= 5.0:
            mem_score = 98.0 + max(0.0, (5.0 - peak_rss_mb) * 0.4)
        elif peak_rss_mb <= 20.0:
            mem_score = 90.0 + (20.0 - peak_rss_mb) * 0.5
        elif peak_rss_mb <= 50.0:
            mem_score = 75.0 + (50.0 - peak_rss_mb) * 0.5
        else:
            mem_score = max(0.0, 100.0 - (peak_rss_mb / max_acceptable_rss_mb) * 100.0)

        # 2. Latency Score
        if avg_latency_ms <= 5.0:
            lat_score = 98.0 + max(0.0, (5.0 - avg_latency_ms) * 0.4)
        elif avg_latency_ms <= 15.0:
            lat_score = 90.0 + (15.0 - avg_latency_ms) * 0.8
        elif avg_latency_ms <= 30.0:
            lat_score = 80.0 + (30.0 - avg_latency_ms) * 0.6
        else:
            lat_score = max(0.0, 100.0 - (avg_latency_ms / max_acceptable_latency_ms) * 100.0)

        # 3. Robustness Score (Disqualification on panic)
        if panics_count > 0:
            rob_score = 0.0
            status = "DISQUALIFIED_PANIC"
        elif total_scenarios > 0:
            rob_score = max(0.0, (scenarios_survived / total_scenarios) * 100.0)
            status = "COMPLETED"
        else:
            rob_score = 100.0
            status = "COMPLETED"

        # 4. Code Quality & Zero-Mock Truth Score
        qual_score = 100.0 - (lint_issues * 5.0)
        if not zero_mock_certified:
            qual_score -= 50.0
        qual_score = max(0.0, min(100.0, qual_score))

        composite = calculate_composite_score(
            mem_score=mem_score,
            lat_score=lat_score,
            rob_score=rob_score,
            qual_score=qual_score,
            weights=self.weights,
        )

        npu_hours = calculate_npu_bonus_hours(composite)

        return ScoreBreakdown(
            framework=framework,
            memory_score=round(mem_score, 2),
            latency_score=round(lat_score, 2),
            robustness_score=round(rob_score, 2),
            code_quality_score=round(qual_score, 2),
            composite_score=round(composite, 2),
            panics_count=panics_count,
            status=status,
            bonus_npu_hours=round(npu_hours, 2),
            weights_used=self.weights,
        )

    def select_winner(self, scores: List[ScoreBreakdown]) -> Optional[ScoreBreakdown]:
        """Deterministically select tournament winner with tie-breaking order."""
        if not scores:
            return None

        # Sort key: Composite -> Robustness -> Memory -> Latency -> Code Quality
        sorted_scores = sorted(
            scores,
            key=lambda s: (
                s.composite_score,
                s.robustness_score,
                s.memory_score,
                s.latency_score,
                s.code_quality_score,
            ),
            reverse=True,
        )
        return sorted_scores[0]
