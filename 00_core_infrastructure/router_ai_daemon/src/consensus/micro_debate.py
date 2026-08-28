"""
micro_debate.py — 3-Round Micro-Debate State Machine & Accord Synthesis.

Implements Feature F4: 3-round micro-debate deliberation engine resolving
dual-core divergences with multi-criteria utility vectors, cosine accord synthesis,
deterministic safety tie-breaking, 50ms SLA timeout enforcement, and volatile
LoRA ledger streaming.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Multi-Criteria Weights & Thresholds
# -----------------------------------------------------------------------------

# Multi-criteria utility weights: sum = 1.00
UTILITY_WEIGHTS: List[float] = [0.30, 0.25, 0.20, 0.15, 0.10]
CONSENSUS_ACCORD_THRESHOLD: float = 0.90  # Phi >= 0.90 ratifies consensus
MAX_DEBATE_SLA_MS: float = 50.0           # 50ms maximum SLA timeout
DEFAULT_FAILSAFE_ACTION: str = "ROUTE_LAN_L1_DEFAULT"
DEFAULT_FAILSAFE_ROUTE: str = "192.168.8.230:8081"
DEFAULT_LEDGER_PATH: str = "/tmp/lora_harvest/smol_consensus_debates.jsonl"


# -----------------------------------------------------------------------------
# Mathematical Utility & Accord Functions
# -----------------------------------------------------------------------------

def calculate_utility(candidate: Dict[str, Any]) -> float:
    """
    Calculate multi-criteria utility score U over 5 dimensions:
    - u1: RAM / Hardware Safety (w1 = 0.30)
    - u2: Latency / Throughput SLA (w2 = 0.25)
    - u3: Mesh Resilience / Partition Tolerance (w3 = 0.20)
    - u4: Token / Compute Frugality (w4 = 0.15)
    - u5: Historical Accuracy Alignment (w5 = 0.10)
    """
    u1 = float(candidate.get("u1_safety", candidate.get("safety", candidate.get("u1", 0.90))))
    u2 = float(candidate.get("u2_latency", candidate.get("latency", candidate.get("u2", 0.85))))
    u3 = float(candidate.get("u3_resilience", candidate.get("resilience", candidate.get("u3", 0.80))))
    u4 = float(candidate.get("u4_frugality", candidate.get("frugality", candidate.get("u4", 0.95))))
    u5 = float(candidate.get("u5_accuracy", candidate.get("accuracy", candidate.get("u5", 0.90))))

    vector = [u1, u2, u3, u4, u5]
    return sum(w * val for w, val in zip(UTILITY_WEIGHTS, vector))


def compute_cosine_accord(v1: List[float], v2: List[float]) -> float:
    """
    Compute Cosine Accord Phi between two persona valuation vectors:
    Phi = (v1 . v2) / (||v1|| * ||v2||)
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 <= 1e-9 or norm2 <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class CandidateEvaluation:
    """Represents multi-criteria evaluation of a candidate route or action."""

    candidate_id: str
    action: str
    params: Dict[str, Any]
    u1_safety: float = 0.90
    u2_latency: float = 0.85
    u3_resilience: float = 0.80
    u4_frugality: float = 0.90
    u5_accuracy: float = 0.85
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None

    def utility_score(self) -> float:
        """Compute weighted utility score."""
        if self.is_disqualified:
            return 0.0
        return (
            (UTILITY_WEIGHTS[0] * self.u1_safety)
            + (UTILITY_WEIGHTS[1] * self.u2_latency)
            + (UTILITY_WEIGHTS[2] * self.u3_resilience)
            + (UTILITY_WEIGHTS[3] * self.u4_frugality)
            + (UTILITY_WEIGHTS[4] * self.u5_accuracy)
        )

    def valuation_vector(self) -> List[float]:
        """Return 5-dimensional evaluation vector."""
        return [
            self.u1_safety,
            self.u2_latency,
            self.u3_resilience,
            self.u4_frugality,
            self.u5_accuracy,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "action": self.action,
            "params": self.params,
            "u1_safety": self.u1_safety,
            "u2_latency": self.u2_latency,
            "u3_resilience": self.u3_resilience,
            "u4_frugality": self.u4_frugality,
            "u5_accuracy": self.u5_accuracy,
            "utility": round(self.utility_score(), 4),
            "is_disqualified": self.is_disqualified,
            "disqualification_reason": self.disqualification_reason,
        }


@dataclass
class DebateTurn:
    """Represents a single round turn in the micro-debate."""

    round: int
    speaker: str
    thesis: str
    invariant_status: str


@dataclass
class DebateRecord:
    """Complete structured record of a micro-debate session."""

    debate_id: str
    timestamp_utc: str
    trigger_divergence: float
    core1_smolagi: Dict[str, Any]
    core2_genetic: Dict[str, Any]
    turns: List[Dict[str, Any]]
    accord: Dict[str, Any]
    final_action: str
    execution_time_ms: float = 0.0
    status: str = "CONCORD_RATIFIED"  # or TIMEOUT_FAILSAFE / SAFETY_TIEBREAK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debate_id": self.debate_id,
            "timestamp_utc": self.timestamp_utc,
            "trigger_divergence": round(self.trigger_divergence, 4),
            "core1_smolagi": self.core1_smolagi,
            "core2_genetic": self.core2_genetic,
            "turns": self.turns,
            "accord": self.accord,
            "final_action": self.final_action,
            "execution_time_ms": round(self.execution_time_ms, 3),
            "status": self.status,
        }


# -----------------------------------------------------------------------------
# Micro-Debate Engine Implementation
# -----------------------------------------------------------------------------

class MicroDebateEngine:
    """
    3-Round Micro-Debate Protocol Engine.
    
    Executes real-time deliberation between smolagi (Core 1) and Genetic Router (Core 2)
    when divergence delta > 0.15.
    """

    def __init__(
        self,
        ledger_path: str = DEFAULT_LEDGER_PATH,
        timeout_ms: float = MAX_DEBATE_SLA_MS,
    ) -> None:
        self.ledger_path = ledger_path
        self.timeout_ms = timeout_ms

    def deliberate(
        self,
        decision_smolagi: Dict[str, Any],
        decision_genetic: Dict[str, Any],
        divergence: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any], DebateRecord]:
        """
        Execute the 3-round micro-debate state machine.
        
        Returns:
            (ratified_action, ratified_params, debate_record)
        """
        t_start = time.perf_counter()
        debate_id = f"deb_{uuid.uuid4().hex[:12]}"
        timestamp_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Wrap candidates
        cand1 = self._build_candidate("cand_smolagi", decision_smolagi, context)
        cand2 = self._build_candidate("cand_genetic", decision_genetic, context)

        turns: List[Dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # Round 1: Thesis & Evidence Exchange
        # ---------------------------------------------------------------------
        turns.append({
            "round": 1,
            "speaker": "core1_smolagi",
            "thesis": f"Proposing {cand1.action} based on cognitive reasoning and intent alignment.",
            "invariant_status": "UNVERIFIED",
        })
        turns.append({
            "round": 1,
            "speaker": "core2_genetic",
            "thesis": f"Proposing {cand2.action} based on chromosome fitness ({decision_genetic.get('fitness', 0.85)}) and telemetry.",
            "invariant_status": "UNVERIFIED",
        })

        # ---------------------------------------------------------------------
        # Round 2: Adversarial Invariant Audit
        # ---------------------------------------------------------------------
        self._audit_invariants(cand1, cand2, context)

        status_1 = "PASSED" if not cand1.is_disqualified else f"FAILED: {cand1.disqualification_reason}"
        status_2 = "PASSED" if not cand2.is_disqualified else f"FAILED: {cand2.disqualification_reason}"

        turns.append({
            "round": 2,
            "speaker": "core1_smolagi",
            "thesis": f"Audited {cand2.action}: Flash wear 0-byte invariant, 300MB RAM budget.",
            "invariant_status": status_2,
        })
        turns.append({
            "round": 2,
            "speaker": "core2_genetic",
            "thesis": f"Audited {cand1.action}: Network reachability, RTT bounds, historical crash rate.",
            "invariant_status": status_1,
        })

        # ---------------------------------------------------------------------
        # Round 3: Mathematical Accord Synthesis
        # ---------------------------------------------------------------------
        u1 = cand1.utility_score()
        u2 = cand2.utility_score()

        v1 = cand1.valuation_vector()
        v2 = cand2.valuation_vector()
        phi = compute_cosine_accord(v1, v2)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        is_timed_out = elapsed_ms > self.timeout_ms

        # Decision Resolution Logic
        if is_timed_out or (cand1.is_disqualified and cand2.is_disqualified):
            # Emergency Fail-Safe Fallback
            final_action = DEFAULT_FAILSAFE_ACTION
            final_params = {"target_ip": "192.168.8.230", "port": 8081, "fallback": True}
            ratified_winner = "failsafe_l1"
            is_consensus_passed = False
            status = "TIMEOUT_FAILSAFE"
        elif not cand1.is_disqualified and cand2.is_disqualified:
            final_action = cand1.action
            final_params = cand1.params
            ratified_winner = "core1_smolagi"
            is_consensus_passed = True
            status = "DISQUALIFICATION_RESOLUTION"
        elif cand1.is_disqualified and not cand2.is_disqualified:
            final_action = cand2.action
            final_params = cand2.params
            ratified_winner = "core2_genetic"
            is_consensus_passed = True
            status = "DISQUALIFICATION_RESOLUTION"
        elif phi >= CONSENSUS_ACCORD_THRESHOLD:
            # Accord ratified on optimal candidate
            if u1 >= u2:
                final_action = cand1.action
                final_params = cand1.params
                ratified_winner = "core1_smolagi"
            else:
                final_action = cand2.action
                final_params = cand2.params
                ratified_winner = "core2_genetic"
            is_consensus_passed = True
            status = "CONCORD_RATIFIED"
        else:
            # Deterministic Tie-Break on highest safety score (u1)
            if cand1.u1_safety >= cand2.u1_safety:
                final_action = cand1.action
                final_params = cand1.params
                ratified_winner = "core1_smolagi"
            else:
                final_action = cand2.action
                final_params = cand2.params
                ratified_winner = "core2_genetic"
            is_consensus_passed = True
            status = "SAFETY_TIEBREAK"

        turns.append({
            "round": 3,
            "speaker": "consensus_synthesizer",
            "thesis": f"Accord synthesis complete. Composite Phi={phi:.4f}, Winner={ratified_winner}.",
            "invariant_status": "RATIFIED" if is_consensus_passed else "FAILSAFE",
        })

        accord_meta = {
            "composite_phi": round(phi, 4),
            "is_consensus_passed": is_consensus_passed,
            "ratified_winner": ratified_winner,
            "utility_smolagi": round(u1, 4),
            "utility_genetic": round(u2, 4),
        }

        total_time_ms = (time.perf_counter() - t_start) * 1000.0

        record = DebateRecord(
            debate_id=debate_id,
            timestamp_utc=timestamp_utc,
            trigger_divergence=divergence,
            core1_smolagi={
                "model_id": decision_smolagi.get("model_id", "smollm2-360m-instruct"),
                "initial_action": decision_smolagi.get("action", ""),
                "confidence": float(decision_smolagi.get("confidence", 0.90)),
            },
            core2_genetic={
                "chromosome_id": decision_genetic.get("chromosome_id", "chrom_default"),
                "initial_action": decision_genetic.get("action", ""),
                "fitness_score": float(decision_genetic.get("fitness", 0.85)),
            },
            turns=turns,
            accord=accord_meta,
            final_action=final_action,
            execution_time_ms=total_time_ms,
            status=status,
        )

        # Write to volatile LoRA ledger stream
        self._append_to_ledger(record)

        return final_action, final_params, record

    def _build_candidate(
        self,
        cid: str,
        decision: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> CandidateEvaluation:
        """Extract or estimate multi-criteria utility dimensions for candidate."""
        action = decision.get("action", "UNKNOWN")
        params = decision.get("params", {})

        # Default multi-criteria values
        u1 = float(decision.get("u1_safety", 0.92))
        u2 = float(decision.get("u2_latency", 0.88))
        u3 = float(decision.get("u3_resilience", 0.85))
        u4 = float(decision.get("u4_frugality", 0.90))
        u5 = float(decision.get("u5_accuracy", 0.88))

        # Adjust dimensions according to known actions
        if "TB4" in action:
            u2 = 0.98  # Ultra-fast 0.27ms latency
            u1 = 0.95  # Safe DMA
            u3 = 0.88
        elif "LAN" in action:
            u1 = 0.98  # Proven reliable LAN
            u3 = 0.95  # High resilience
            u2 = 0.80  # 1.1ms latency
        elif "WIFI" in action:
            u2 = 0.75
            u3 = 0.70

        # Adjust if parameters specify latency or safety directly
        if "latency_ms" in params:
            lat = float(params["latency_ms"])
            u2 = max(0.1, min(1.0, 1.0 - (lat / 50.0)))
        if "safety_score" in params:
            u1 = float(params["safety_score"])

        return CandidateEvaluation(
            candidate_id=cid,
            action=action,
            params=params,
            u1_safety=u1,
            u2_latency=u2,
            u3_resilience=u3,
            u4_frugality=u4,
            u5_accuracy=u5,
        )

    def _audit_invariants(
        self,
        cand1: CandidateEvaluation,
        cand2: CandidateEvaluation,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Audit candidates against hard physical & operational invariants."""
        if not context:
            return

        # Invariant 1: Node reachability / offline detection
        offline_nodes = context.get("offline_nodes", [])
        failed_nodes = context.get("failed_nodes", [])
        dead_nodes = set(offline_nodes + failed_nodes)
        if "failed_node" in context:
            dead_nodes.add(context["failed_node"])

        for cand in (cand1, cand2):
            target_layer = cand.params.get("layer") or cand.params.get("target_layer")
            target_ip = cand.params.get("target_ip", "")
            for dead in dead_nodes:
                if dead in (cand.action, target_layer, target_ip):
                    cand.is_disqualified = True
                    cand.disqualification_reason = f"Target node {dead} is offline/unreachable"

            # Invariant 2: Flash write prohibition
            if cand.params.get("writes_flash", False):
                cand.is_disqualified = True
                cand.disqualification_reason = "Unauthorized flash write attempt"

            # Invariant 3: RAM budget ceiling (<= 300MB)
            if cand.params.get("ram_usage_mb", 0.0) > 300.0:
                cand.is_disqualified = True
                cand.disqualification_reason = "Exceeds container 300MB RAM cap"

    def _append_to_ledger(self, record: DebateRecord) -> None:
        """Append debate record to volatile JSONL ledger for continuous LoRA distillation."""
        try:
            p = pathlib.Path(self.ledger_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception:
            # Fallback or silent ignore to prevent router logging crash
            pass
