"""
dual_core_router.py — Dual-Core Decision Coordinator & Divergence Detector.

Implements Feature F3 & Feature F4: Coordinates primary smolagi reasoning engine
with secondary Genetic Router evolutionary engine. Computes vector divergence Delta,
executes sub-3.5ms fast-path on concord (Delta <= 0.15), and triggers 3-round
micro-debate deliberation on discord.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from src.consensus.genetic_router import GeneticRouter
from src.consensus.micro_debate import (
    MicroDebateEngine,
    calculate_utility,
    compute_cosine_accord,
)


# -----------------------------------------------------------------------------
# Divergence Mathematical Formulation
# -----------------------------------------------------------------------------

def compute_divergence(
    d1: Dict[str, Any],
    d2: Dict[str, Any],
    wp: float = 0.60,
    wc: float = 0.40,
) -> float:
    """
    Calculate decision vector divergence Delta between smolagi (D1) and Genetic Router (D2).
    
    Formula:
    Delta = I(a1 != a2) * 1.0 + I(a1 == a2) * [ (||p1 - p2|| / ||p_max||) * wp + |c1 - f2| * wc ]
    
    Where:
    - Discrete action inequality immediately yields maximum divergence (1.0).
    - Equal actions compute weighted normalized parameter distance and confidence gap.
    """
    a1 = d1.get("action")
    a2 = d2.get("action")

    if a1 != a2:
        return 1.0

    # Calculate parameter distance normalized by parameter magnitudes
    p1 = d1.get("params", {})
    p2 = d2.get("params", {})
    all_keys = set(p1.keys()).union(set(p2.keys()))

    if not all_keys:
        param_dist = 0.0
    else:
        diffs = []
        max_magnitudes = []
        for k in all_keys:
            v1 = p1.get(k, 0.0)
            v2 = p2.get(k, 0.0)
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                diffs.append((float(v1) - float(v2)) ** 2)
                max_magnitudes.append(max(abs(float(v1)), abs(float(v2)), 1.0) ** 2)
            else:
                diffs.append(0.0 if v1 == v2 else 1.0)
                max_magnitudes.append(1.0)

        numerator = math.sqrt(sum(diffs))
        denominator = math.sqrt(sum(max_magnitudes))
        param_dist = min(1.0, numerator / max(1.0, denominator))

    c1 = float(d1.get("confidence", 0.85))
    f2 = float(d2.get("fitness", 0.85))
    conf_diff = abs(c1 - f2)

    return min(1.0, (param_dist * wp) + (conf_diff * wc))


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class DecisionVector:
    """Represents a single core's decision vector."""

    core: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.90
    fitness: Optional[float] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core": self.core,
            "action": self.action,
            "params": self.params,
            "confidence": self.confidence,
            "fitness": self.fitness if self.fitness is not None else self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class RoutingContext:
    """Payload context for routing decision evaluation."""

    intent: str
    candidate_routes: List[Any] = field(default_factory=list)
    mesh_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    failed_node: Optional[str] = None
    payload_kb: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_input(cls, data: Union[RoutingContext, Dict[str, Any], str]) -> RoutingContext:
        if isinstance(data, RoutingContext):
            return data
        if isinstance(data, str):
            return cls(intent=data)
        if isinstance(data, dict):
            return cls(
                intent=data.get("intent", "ROUTE_DEFAULT"),
                candidate_routes=data.get("candidate_routes", []),
                mesh_metrics=data.get("mesh_metrics", {}),
                timestamp=data.get("timestamp", time.time()),
                failed_node=data.get("failed_node"),
                payload_kb=data.get("payload_kb"),
                metadata=data.get("metadata", {}),
            )
        return cls(intent="ROUTE_DEFAULT")


@dataclass
class ConsensusResult:
    """Ratified output of Dual-Core Consensus evaluation."""

    consensus_route: Dict[str, Any]
    agreed: bool
    divergence: float
    debate_rounds: int
    consensus_score: float
    execution_time_ms: float
    debate_record: Optional[Dict[str, Any]] = None
    consensus_signature: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus_route": self.consensus_route,
            "agreed": self.agreed,
            "divergence": round(self.divergence, 4),
            "debate_rounds": self.debate_rounds,
            "consensus_score": round(self.consensus_score, 4),
            "execution_time_ms": round(self.execution_time_ms, 3),
            "debate_record": self.debate_record,
            "consensus_signature": self.consensus_signature,
        }


# -----------------------------------------------------------------------------
# Dual-Core Coordinator Implementation
# -----------------------------------------------------------------------------

class DualCoreRouter:
    """
    Dual-Core Consensus Coordinator.
    
    Synchronously cross-verifies decisions between Core 1 (smolagi reasoning)
    and Core 2 (Genetic Router evolutionary policy).
    """

    AGREEMENT_THRESHOLD: float = 0.15

    def __init__(
        self,
        genetic_router: Optional[GeneticRouter] = None,
        micro_debate_engine: Optional[MicroDebateEngine] = None,
        model_id: str = "smollm2-360m-instruct",
        signing_secret: str = "lauburu_dual_core_consensus_secret",
    ) -> None:
        self.genetic_router = genetic_router or GeneticRouter()
        self.micro_debate_engine = micro_debate_engine or MicroDebateEngine()
        self.model_id = model_id
        self.signing_secret = signing_secret

    def evaluate_routing_intent(
        self,
        context_or_payload: Union[RoutingContext, Dict[str, Any], str],
        decision_smolagi_override: Optional[Dict[str, Any]] = None,
        decision_genetic_override: Optional[Dict[str, Any]] = None,
    ) -> ConsensusResult:
        """
        Evaluate routing intent with synchronous dual-core cross-verification.
        
        SLA:
        - Fast-path concord (Delta <= 0.15): < 3.5ms
        - Micro-debate deliberation (Delta > 0.15): < 50ms
        """
        t_start = time.perf_counter()
        ctx = RoutingContext.from_input(context_or_payload)
        context_dict = {
            "intent": ctx.intent,
            "candidate_routes": ctx.candidate_routes,
            "mesh_metrics": ctx.mesh_metrics,
            "timestamp": ctx.timestamp,
            "failed_node": ctx.failed_node,
            "payload_kb": ctx.payload_kb,
            **ctx.metadata,
        }

        # 1. Generate Core 1 (smolagi) decision
        if decision_smolagi_override:
            d1 = dict(decision_smolagi_override)
        else:
            d1 = self._generate_smolagi_decision(ctx)

        # 2. Generate Core 2 (Genetic Router) decision
        if decision_genetic_override:
            d2 = dict(decision_genetic_override)
        else:
            d2 = self.genetic_router.propose_routing_decision(
                intent=ctx.intent,
                candidate_routes=ctx.candidate_routes,
                mesh_metrics=ctx.mesh_metrics,
            )

        # 3. Cross-Verification Gate: Calculate vector divergence
        divergence = compute_divergence(d1, d2)

        debate_record_dict = None
        if divergence <= self.AGREEMENT_THRESHOLD:
            # -----------------------------------------------------------------
            # FAST-PATH CONCORD (< 3.5ms)
            # -----------------------------------------------------------------
            agreed = True
            debate_rounds = 0
            # Blend agreed parameters
            merged_params = {**d2.get("params", {}), **d1.get("params", {})}
            consensus_route = {
                "action": d1.get("action"),
                "params": merged_params,
                "core": "dual_core_concord",
                "target_ip": merged_params.get("target_ip", "192.168.8.230"),
                "port": merged_params.get("port", 8081),
            }
            conf1 = float(d1.get("confidence", 0.90))
            fit2 = float(d2.get("fitness", 0.90))
            consensus_score = (conf1 + fit2) / 2.0
        else:
            # -----------------------------------------------------------------
            # DISCORD -> 3-ROUND MICRO-DEBATE
            # -----------------------------------------------------------------
            action, params, debate_record = self.micro_debate_engine.deliberate(
                decision_smolagi=d1,
                decision_genetic=d2,
                divergence=divergence,
                context=context_dict,
            )
            agreed = debate_record.accord.get("is_consensus_passed", False)
            debate_rounds = 3
            consensus_score = float(debate_record.accord.get("composite_phi", 0.85))
            consensus_route = {
                "action": action,
                "params": params,
                "core": debate_record.accord.get("ratified_winner", "micro_debate"),
                "target_ip": params.get("target_ip", "192.168.8.230"),
                "port": params.get("port", 8081),
            }
            debate_record_dict = debate_record.to_dict()

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        # Consensus Signature for asset packaging / telemetry proof
        signature_payload = f"{consensus_route.get('action')}:{divergence:.4f}:{consensus_score:.4f}:{time.time()}"
        sig_hmac = hmac.new(
            self.signing_secret.encode("utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        consensus_sig = {
            "dual_core_ratified": True,
            "divergence": round(divergence, 4),
            "consensus_phi": round(consensus_score, 4),
            "timestamp": time.time(),
            "hmac_signature": sig_hmac,
        }

        return ConsensusResult(
            consensus_route=consensus_route,
            agreed=agreed,
            divergence=divergence,
            debate_rounds=debate_rounds,
            consensus_score=consensus_score,
            execution_time_ms=elapsed_ms,
            debate_record=debate_record_dict,
            consensus_signature=consensus_sig,
        )

    def _generate_smolagi_decision(self, ctx: RoutingContext) -> Dict[str, Any]:
        """Cognitive heuristic proposal generation for smolagi (Core 1)."""
        intent = ctx.intent.upper()
        
        # If candidates are provided, select based on intent heuristics
        if ctx.candidate_routes:
            best_cand = ctx.candidate_routes[0]
            action = best_cand if isinstance(best_cand, str) else best_cand.get("action", "ROUTE_LAN_1GBPS")
            params = best_cand.get("params", {}) if isinstance(best_cand, dict) else {}
            return {
                "core": "smolagi",
                "action": action,
                "params": params,
                "confidence": 0.92,
                "timestamp": time.time(),
            }

        # Intent-driven routing logic
        if "TB4" in intent or "TENSOR" in intent or "HIGH_SPEED" in intent:
            return {
                "core": "smolagi",
                "action": "ROUTE_TB4_DMA",
                "params": {"target_ip": "169.254.187.138", "port": 8082, "timeout_ms": 50},
                "confidence": 0.95,
                "timestamp": time.time(),
            }
        elif "FAILOVER" in intent:
            return {
                "core": "smolagi",
                "action": "ROUTE_LAN_1GBPS",
                "params": {"target_ip": "192.168.8.230", "port": 8081, "timeout_ms": 100},
                "confidence": 0.90,
                "timestamp": time.time(),
            }
        elif "SWARM" in intent or "SCALE" in intent:
            return {
                "core": "smolagi",
                "action": "SCALE_SWARM_UP",
                "params": {"count": 2, "layer": "L1"},
                "confidence": 0.88,
                "timestamp": time.time(),
            }
        else:
            return {
                "core": "smolagi",
                "action": "ROUTE_LAN_1GBPS",
                "params": {"target_ip": "192.168.8.230", "port": 8081, "timeout_ms": 100},
                "confidence": 0.88,
                "timestamp": time.time(),
            }
