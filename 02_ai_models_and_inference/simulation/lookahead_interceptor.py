# -*- coding: utf-8 -*-
"""
Dual-World Simulation & Predictive Lookahead Engine (LookaheadInterceptor)
==========================================================================
Subsystem: 02_ai_models_and_inference/simulation/lookahead_interceptor.py
Milestone: M4 — Dual-World Simulation & Predictive Lookahead Engine

Governs pre-flight trajectory interception and multi-step lookahead rollout
across Qwen-AgentWorld-35B (OS/terminal/MCP/ADB) and Qwen-WebWorld-32B/8B (React DOM/UI)
with quantitative admission gating (S >= 0.90, P_reg <= 0.05, O_layout == 0, C_sim >= 0.85).
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from agentworld_driver import AgentWorldDriver, CopyOnWriteVFS
    from webworld_driver import WebWorldDriver, ShadowDOM
except ImportError:
    from .agentworld_driver import AgentWorldDriver, CopyOnWriteVFS
    from .webworld_driver import WebWorldDriver, ShadowDOM

logger = logging.getLogger("LookaheadInterceptor")

# Canonical Quantitative Admission Thresholds
MIN_SAFETY_SCORE = 0.90
MAX_REGRESSION_PROB = 0.05
MAX_LAYOUT_OVERFLOWS = 0
MIN_SIMULATION_CONFIDENCE = 0.85
DEFAULT_LOOKAHEAD_STEPS = 30


@dataclass
class AdmissionGateResult:
    admitted: bool
    composite_score: float
    safety_score: float
    regression_probability: float
    layout_overflows: int
    simulation_confidence: float
    verdict: str
    reasons: List[str] = field(default_factory=list)


class LookaheadInterceptor:
    """
    Dual-World Simulation & Predictive Lookahead Interceptor.
    Enforces pre-execution trajectory rollouts on Copy-on-Write shadow states
    to eliminate runtime bugs, broken UI layouts, and destructive actions.
    """

    def __init__(
        self,
        min_safety_score: float = MIN_SAFETY_SCORE,
        max_regression_prob: float = MAX_REGRESSION_PROB,
        max_layout_overflows: int = MAX_LAYOUT_OVERFLOWS,
        min_confidence: float = MIN_SIMULATION_CONFIDENCE,
        default_lookahead_steps: int = DEFAULT_LOOKAHEAD_STEPS,
        agentworld_driver: Optional[AgentWorldDriver] = None,
        webworld_driver: Optional[WebWorldDriver] = None,
        base_dir: Optional[Union[str, Path]] = None,
    ):
        self.min_safety_score = min_safety_score
        self.max_regression_prob = max_regression_prob
        self.max_layout_overflows = max_layout_overflows
        self.min_confidence = min_confidence
        self.default_lookahead_steps = default_lookahead_steps
        
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.agentworld = agentworld_driver or AgentWorldDriver(base_dir=self.base_dir)
        self.webworld = webworld_driver or WebWorldDriver()

        # Telemetry & Metrics
        self._metrics = {
            "total_intercepted": 0,
            "total_admitted": 0,
            "total_rejected": 0,
            "safety_violations": 0,
            "regression_violations": 0,
            "layout_overflow_violations": 0,
            "confidence_violations": 0,
            "total_simulation_time_ms": 0.0,
        }

    def compute_composite_score(
        self,
        safety_score: float,
        regression_prob: float,
        layout_overflows: int,
        confidence: float,
    ) -> float:
        """
        Computes normalized composite admission score in [0.0, 1.0].
        Weights: Safety=40%, (1 - P_reg)=30%, Confidence=20%, Layout=10%.
        """
        layout_factor = 1.0 if layout_overflows == 0 else max(0.0, 1.0 - (layout_overflows * 0.5))
        reg_factor = max(0.0, 1.0 - regression_prob)
        
        score = (
            0.40 * safety_score +
            0.30 * reg_factor +
            0.20 * confidence +
            0.10 * layout_factor
        )
        return round(max(0.0, min(1.0, score)), 4)

    def evaluate_admission_gate(
        self,
        safety_score: float,
        regression_prob: float,
        layout_overflows: int,
        confidence: float,
    ) -> AdmissionGateResult:
        """
        Validates trajectory metrics against quantitative invariant thresholds:
        - S >= 0.90
        - P_reg <= 0.05
        - O_layout == 0
        - C_sim >= 0.85
        """
        reasons = []
        is_admitted = True

        if safety_score < self.min_safety_score:
            is_admitted = False
            reasons.append(
                f"Safety score {safety_score:.4f} is below minimum threshold ({self.min_safety_score:.2f})"
            )
            self._metrics["safety_violations"] += 1

        if regression_prob > self.max_regression_prob:
            is_admitted = False
            reasons.append(
                f"Regression probability {regression_prob:.4f} exceeds maximum threshold ({self.max_regression_prob:.2f})"
            )
            self._metrics["regression_violations"] += 1

        if layout_overflows > self.max_layout_overflows:
            is_admitted = False
            reasons.append(
                f"Layout overflow count {layout_overflows} exceeds maximum allowed ({self.max_layout_overflows})"
            )
            self._metrics["layout_overflow_violations"] += 1

        if confidence < self.min_confidence:
            is_admitted = False
            reasons.append(
                f"Simulation confidence {confidence:.4f} is below minimum threshold ({self.min_confidence:.2f})"
            )
            self._metrics["confidence_violations"] += 1

        composite = self.compute_composite_score(
            safety_score=safety_score,
            regression_prob=regression_prob,
            layout_overflows=layout_overflows,
            confidence=confidence,
        )

        verdict = "ADMITTED_CERTIFIED" if is_admitted else "REJECTED_GATING_BREACH"

        return AdmissionGateResult(
            admitted=is_admitted,
            composite_score=composite,
            safety_score=safety_score,
            regression_probability=regression_prob,
            layout_overflows=layout_overflows,
            simulation_confidence=confidence,
            verdict=verdict,
            reasons=reasons,
        )

    def simulate_trajectory(
        self,
        action_type: str,
        action_payload: Dict[str, Any],
        lookahead_steps: int = DEFAULT_LOOKAHEAD_STEPS,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Runs 30-step trajectory rollout in AgentWorld/WebWorld shadow virtual state.
        Conforms strictly to PROJECT.md § Subagent Interceptor <-> Dual-World Interface Contract.

        Returns:
            (admitted: bool, composite_score: float, diagnostics: dict)
        """
        start_time = time.perf_counter()
        self._metrics["total_intercepted"] += 1

        act_type_norm = action_type.lower().strip()
        is_web_domain = act_type_norm in [
            "dom_update",
            "graphql_mutation",
            "react_component",
            "tailwind_style",
            "web_route",
            "css_mutation",
        ]

        if is_web_domain:
            rollout_raw = self.webworld.rollout_trajectory(
                action_payload=action_payload,
                lookahead_steps=lookahead_steps,
            )
        else:
            rollout_raw = self.agentworld.rollout_trajectory(
                action_payload=action_payload,
                lookahead_steps=lookahead_steps,
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self._metrics["total_simulation_time_ms"] += elapsed_ms

        s_score = rollout_raw.get("safety_score", 0.0)
        p_reg = rollout_raw.get("regression_probability", 1.0)
        o_layout = rollout_raw.get("layout_overflows", 0)
        c_sim = rollout_raw.get("simulation_confidence", 0.0)

        gate_res = self.evaluate_admission_gate(
            safety_score=s_score,
            regression_prob=p_reg,
            layout_overflows=o_layout,
            confidence=c_sim,
        )

        if gate_res.admitted:
            self._metrics["total_admitted"] += 1
        else:
            self._metrics["total_rejected"] += 1

        diagnostics = {
            "timestamp": time.time(),
            "action_type": action_type,
            "world_model_driver": rollout_raw.get("driver", "DualWorld"),
            "lookahead_steps": lookahead_steps,
            "steps_completed": rollout_raw.get("steps_completed", 0),
            "safety_score": gate_res.safety_score,
            "regression_probability": gate_res.regression_probability,
            "layout_overflows": gate_res.layout_overflows,
            "simulation_confidence": gate_res.simulation_confidence,
            "composite_score": gate_res.composite_score,
            "verdict": gate_res.verdict,
            "reasons": gate_res.reasons,
            "elapsed_ms": round(elapsed_ms, 2),
            "step_results": rollout_raw.get("step_results", []),
            "state_diff": rollout_raw.get("vfs_diff") or rollout_raw.get("dom_diff", {}),
            "quantitative_thresholds": {
                "min_safety_score": self.min_safety_score,
                "max_regression_prob": self.max_regression_prob,
                "max_layout_overflows": self.max_layout_overflows,
                "min_confidence": self.min_confidence,
            },
        }

        return gate_res.admitted, gate_res.composite_score, diagnostics

    def intercept_and_execute(
        self,
        action_type: str,
        action_payload: Dict[str, Any],
        execution_callback: Optional[Callable[[], Any]] = None,
        lookahead_steps: int = DEFAULT_LOOKAHEAD_STEPS,
    ) -> Tuple[bool, float, Dict[str, Any], Optional[Any]]:
        """
        Intercepts action, executes lookahead simulation, and only invokes
        the physical execution callback if admitted by the gate.
        """
        admitted, score, diag = self.simulate_trajectory(
            action_type=action_type,
            action_payload=action_payload,
            lookahead_steps=lookahead_steps,
        )

        exec_result = None
        if admitted and execution_callback:
            try:
                exec_result = execution_callback()
                diag["execution_status"] = "EXECUTED_SUCCESS"
            except Exception as e:
                diag["execution_status"] = f"EXECUTION_ERROR: {e}"
                logger.error(f"LookaheadInterceptor: Post-admission execution failed: {e}")
        elif not admitted:
            diag["execution_status"] = "BLOCKED_BY_GATING"

        return admitted, score, diag, exec_result

    def get_metrics(self) -> Dict[str, Any]:
        """Returns interceptor telemetry and admission rates."""
        tot = self._metrics["total_intercepted"]
        admit_rate = (self._metrics["total_admitted"] / tot * 100.0) if tot > 0 else 0.0
        avg_lat = (self._metrics["total_simulation_time_ms"] / tot) if tot > 0 else 0.0
        return {
            **self._metrics,
            "admission_rate_pct": round(admit_rate, 2),
            "avg_simulation_latency_ms": round(avg_lat, 2),
        }
