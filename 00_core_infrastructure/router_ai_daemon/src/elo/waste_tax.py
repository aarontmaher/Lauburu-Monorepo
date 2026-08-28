"""
Waste Tax & Economic Realignment Penalty Engine (Feature F9).
Authoritative Specifications: ORIGINAL_REQUEST.md (§R5) & spec_miner_1/analysis.md (§5).

Ties multi-agent AGI currency, API spend, token consumption, and mesh resource drain
directly to ELO deductions when compute is expended without measurable optimization gains.
Enforces auto-revocation of cloud credentials when ELO drops below 1500.
"""

from __future__ import annotations

import datetime
import math
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Canonical Economic Constants & Hyperparameters
# ---------------------------------------------------------------------------
DEFAULT_LAMBDA_BASE: float = 50.0  # Base penalty scale in ELO points
DEFAULT_C0: float = 0.05           # Baseline cost normalization in USD ($0.05)
DEFAULT_T0: float = 2048.0         # Baseline token normalization (2048 tokens)

WEIGHT_COST: float = 0.35          # wc: Weight for API / currency expenditure
WEIGHT_TOKENS: float = 0.25        # wt: Weight for wasted prompt/completion tokens
WEIGHT_MESH: float = 0.25          # wm: Weight for mesh resource drain index
WEIGHT_CALLS: float = 0.15         # wa: Weight for spurious or failing tool calls

DEFAULT_GAMMA: float = 1.25        # Severity exponent for super-linear scaling
DEFAULT_THRESHOLD: float = 0.50    # Optimization threshold (at or above => 0 tax)

MAX_TAX_DEDUCTION: float = -400.0  # Cap on maximum tax deduction per event
ELO_QUARANTINE_THRESHOLD: float = 1500.0  # Threshold below which cloud access is revoked


# ---------------------------------------------------------------------------
# Data Schemas & Models
# ---------------------------------------------------------------------------

@dataclass
class DisciplinaryVerdict:
    """Disciplinary action result from waste tax evaluation."""
    tier: str
    action: str
    tax_amount: float
    previous_elo: float
    new_elo: float
    revoke_cloud: bool = False
    quarantined: bool = False

    @property
    def full_description(self) -> str:
        return f"{self.tier} — {self.action}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "action": self.action,
            "full_description": self.full_description,
            "tax_amount": self.tax_amount,
            "previous_elo": self.previous_elo,
            "new_elo": self.new_elo,
            "revoke_cloud": self.revoke_cloud,
            "quarantined": self.quarantined,
        }


@dataclass
class WasteTaxPenaltyEvent:
    """
    Structured Waste Tax Penalty Event conforming to analysis.md §8.2 JSON Schema.
    """
    event_id: str
    timestamp_utc: str
    agent_id: str
    cost_spent_usd: float
    tokens_wasted: int
    mesh_drain_index: float
    optimization_score: float
    elo_deduction: float
    new_elo: float
    disciplinary_action: str
    disciplinary_tier: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "event_id": self.event_id,
            "timestamp_utc": self.timestamp_utc,
            "agent_id": self.agent_id,
            "cost_spent_usd": round(self.cost_spent_usd, 4),
            "tokens_wasted": int(self.tokens_wasted),
            "mesh_drain_index": round(self.mesh_drain_index, 4),
            "optimization_score": round(self.optimization_score, 4),
            "elo_deduction": round(self.elo_deduction, 2),
            "new_elo": round(self.new_elo, 2),
            "disciplinary_action": self.disciplinary_action,
            "disciplinary_tier": self.disciplinary_tier or self.disciplinary_action,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Core Calculation Functions
# ---------------------------------------------------------------------------

def calculate_mesh_drain_index(
    ram_locked_mb: float = 0.0,
    excess_rtt_ms: float = 0.0,
    battery_drain_high: bool = False,
    flash_writes_detected: bool = False,
) -> float:
    """
    Calculate Mesh Resource Drain Index (Ψ_mesh_drain).

    Formula:
    Ψ = (ΔRAM_locked_mb / 300.0) + (RTT_excess_ms / 100.0)
        + I(BatteryDrain > 5%/hr) * 1.5 + I(FlashWritesDetected) * 5.0
    """
    ram_term = max(0.0, float(ram_locked_mb)) / 300.0
    rtt_term = max(0.0, float(excess_rtt_ms)) / 100.0
    battery_term = 1.5 if battery_drain_high else 0.0
    flash_term = 5.0 if flash_writes_detected else 0.0

    return ram_term + rtt_term + battery_term + flash_term


def calculate_optimization_score(
    test_pass_rate: float,
    ast_valid: bool = True,
    latency_old_ms: float = 0.0,
    latency_new_ms: float = 0.0,
    ram_old_mb: float = 0.0,
    ram_new_mb: float = 0.0,
) -> float:
    """
    Calculate Measurable Optimization Score (ΔΦ_optimization ∈ [0.0, 1.0]).

    Formula:
    ΔΦ = PassRate_tests * [ 0.40 * I(AST_Valid)
         + 0.30 * max(0, (Lat_old - Lat_new) / Lat_old)
         + 0.30 * max(0, (RAM_old - RAM_new) / RAM_old) ]
    """
    pass_rate = max(0.0, min(1.0, float(test_pass_rate)))
    ast_term = 0.40 if ast_valid else 0.0

    lat_term = 0.0
    if latency_old_ms > 0.0:
        lat_diff = (latency_old_ms - latency_new_ms) / latency_old_ms
        lat_term = 0.30 * max(0.0, min(1.0, lat_diff))

    ram_term = 0.0
    if ram_old_mb > 0.0:
        ram_diff = (ram_old_mb - ram_new_mb) / ram_old_mb
        ram_term = 0.30 * max(0.0, min(1.0, ram_diff))

    score = pass_rate * (ast_term + lat_term + ram_term)
    return max(0.0, min(1.0, score))


def calculate_waste_tax(
    spend_usd: float = 0.0,
    tokens_wasted: int = 0,
    spurious_calls: int = 0,
    mesh_drain_index: float = 0.0,
    optimization_score: float = 0.0,
    threshold: float = DEFAULT_THRESHOLD,
    lambda_base: float = DEFAULT_LAMBDA_BASE,
    c0: float = DEFAULT_C0,
    t0: float = DEFAULT_T0,
    gamma: float = DEFAULT_GAMMA,
    max_tax: float = MAX_TAX_DEDUCTION,
) -> float:
    """
    Calculate Economic Realignment Penalty (Tax_waste).

    Formula:
    Tax_waste = -Λ_base * [ wc*(C_spent/C0) + wt*(T_wasted/T0) + wm*Ψ_mesh + wa*N_calls ]^γ * (1.0 - ΔΦ_opt)

    Invariants:
    - If ΔΦ_opt >= threshold: Tax = 0.0
    - Result is returned as a non-positive float (e.g. -50.0).
    - Capped at max_tax (e.g. >= -400.0).
    """
    opt_clamped = max(0.0, min(1.0, float(optimization_score)))
    if opt_clamped >= threshold:
        return 0.0

    c_spent = max(0.0, float(spend_usd))
    t_wasted = max(0, int(tokens_wasted))
    n_calls = max(0, int(spurious_calls))
    psi_mesh = max(0.0, float(mesh_drain_index))

    term_cost = WEIGHT_COST * (c_spent / max(1e-6, c0))
    term_tokens = WEIGHT_TOKENS * (float(t_wasted) / max(1.0, t0))
    term_mesh = WEIGHT_MESH * psi_mesh
    term_calls = WEIGHT_CALLS * float(n_calls)

    inner_sum = max(0.0, term_cost + term_tokens + term_mesh + term_calls)
    penalty = lambda_base * (inner_sum ** gamma) * (1.0 - opt_clamped)

    tax = -abs(penalty)
    if max_tax < 0:
        tax = max(max_tax, tax)

    return float(tax)


def evaluate_disciplinary_action(
    tax_amount: float,
    current_elo: float,
    flash_write_detected: bool = False,
) -> DisciplinaryVerdict:
    """
    Evaluate disciplinary tier, actions, and cloud access revocation.

    Tiers:
    - Tier 1 (Minor): abs(tax) in (0, 25) -> Warning logged
    - Tier 2 (Hallucination/Build break): abs(tax) in [25, 80) -> 5-min cooldown
    - Tier 3 (Severe Gluttony): abs(tax) in [80, 200) -> Cloud API Revocation / Sandboxed
    - Tier 4 (Mesh Threat / Flash Write): abs(tax) >= 200 or Flash write -> SIGKILL / Quarantined
    - Auto-revocation if resulting ELO drops below 1500.0.
    """
    abs_tax = abs(tax_amount)
    new_elo = current_elo + tax_amount  # tax_amount is negative

    if flash_write_detected or abs_tax >= 200.0:
        tier = "Tier 4: Mesh Threat / Flash Invariant Violation"
        action = "Immediate SIGKILL; quarantined from Swarm Leaderboard until retrained."
        revoke_cloud = True
        quarantined = True
    elif abs_tax >= 80.0:
        tier = "Tier 3: Severe Resource Gluttony"
        action = "Revocation of Cloud API permissions; demoted to Sandboxed Local Worker."
        revoke_cloud = True
        quarantined = False
    elif abs_tax >= 25.0:
        tier = "Tier 2: Hallucination / Build Break"
        action = "Temporary 5-minute task dispatch cooldown."
        revoke_cloud = False
        quarantined = False
    elif abs_tax > 0.0:
        tier = "Tier 1: Minor Inefficiency"
        action = "Warning logged to session_logs/waste_tax_ledger.jsonl."
        revoke_cloud = False
        quarantined = False
    else:
        tier = "Tier 0: Compliant"
        action = "No penalty."
        revoke_cloud = False
        quarantined = False

    if new_elo < ELO_QUARANTINE_THRESHOLD:
        revoke_cloud = True
        action += f" (Auto-revoked cloud credentials below {ELO_QUARANTINE_THRESHOLD} ELO threshold)."

    return DisciplinaryVerdict(
        tier=tier,
        action=action,
        tax_amount=tax_amount,
        previous_elo=current_elo,
        new_elo=new_elo,
        revoke_cloud=revoke_cloud,
        quarantined=quarantined,
    )


# ---------------------------------------------------------------------------
# Waste Tax Calculator Class
# ---------------------------------------------------------------------------

class WasteTaxCalculator:
    """
    Stateful calculator for evaluating and assessing waste taxes and disciplinary actions.
    """

    def __init__(
        self,
        lambda_base: float = DEFAULT_LAMBDA_BASE,
        c0: float = DEFAULT_C0,
        t0: float = DEFAULT_T0,
        gamma: float = DEFAULT_GAMMA,
        threshold: float = DEFAULT_THRESHOLD,
        max_tax: float = MAX_TAX_DEDUCTION,
        quarantine_threshold: float = ELO_QUARANTINE_THRESHOLD,
    ) -> None:
        self.lambda_base = lambda_base
        self.c0 = c0
        self.t0 = t0
        self.gamma = gamma
        self.threshold = threshold
        self.max_tax = max_tax
        self.quarantine_threshold = quarantine_threshold

    def calculate_mesh_drain(
        self,
        ram_locked_mb: float = 0.0,
        excess_rtt_ms: float = 0.0,
        battery_drain_high: bool = False,
        flash_writes_detected: bool = False,
    ) -> float:
        return calculate_mesh_drain_index(
            ram_locked_mb=ram_locked_mb,
            excess_rtt_ms=excess_rtt_ms,
            battery_drain_high=battery_drain_high,
            flash_writes_detected=flash_writes_detected,
        )

    def calculate_optimization(
        self,
        test_pass_rate: float,
        ast_valid: bool = True,
        latency_old_ms: float = 0.0,
        latency_new_ms: float = 0.0,
        ram_old_mb: float = 0.0,
        ram_new_mb: float = 0.0,
    ) -> float:
        return calculate_optimization_score(
            test_pass_rate=test_pass_rate,
            ast_valid=ast_valid,
            latency_old_ms=latency_old_ms,
            latency_new_ms=latency_new_ms,
            ram_old_mb=ram_old_mb,
            ram_new_mb=ram_new_mb,
        )

    def calculate_tax(
        self,
        spend_usd: float = 0.0,
        tokens_wasted: int = 0,
        spurious_calls: int = 0,
        mesh_drain_index: float = 0.0,
        optimization_score: float = 0.0,
    ) -> float:
        return calculate_waste_tax(
            spend_usd=spend_usd,
            tokens_wasted=tokens_wasted,
            spurious_calls=spurious_calls,
            mesh_drain_index=mesh_drain_index,
            optimization_score=optimization_score,
            threshold=self.threshold,
            lambda_base=self.lambda_base,
            c0=self.c0,
            t0=self.t0,
            gamma=self.gamma,
            max_tax=self.max_tax,
        )

    def evaluate_penalty_event(
        self,
        agent_id: str,
        current_elo: float,
        spend_usd: float = 0.0,
        tokens_wasted: int = 0,
        spurious_calls: int = 0,
        mesh_drain_index: float = 0.0,
        optimization_score: float = 0.0,
        flash_write_detected: bool = False,
        event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[WasteTaxPenaltyEvent, DisciplinaryVerdict]:
        """
        Compute tax, evaluate disciplinary verdict, and package as a WasteTaxPenaltyEvent.
        """
        tax = self.calculate_tax(
            spend_usd=spend_usd,
            tokens_wasted=tokens_wasted,
            spurious_calls=spurious_calls,
            mesh_drain_index=mesh_drain_index,
            optimization_score=optimization_score,
        )

        verdict = evaluate_disciplinary_action(
            tax_amount=tax,
            current_elo=current_elo,
            flash_write_detected=flash_write_detected,
        )

        event_uid = event_id or f"evt_tax_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        penalty_event = WasteTaxPenaltyEvent(
            event_id=event_uid,
            timestamp_utc=timestamp,
            agent_id=agent_id,
            cost_spent_usd=spend_usd,
            tokens_wasted=tokens_wasted,
            mesh_drain_index=mesh_drain_index,
            optimization_score=optimization_score,
            elo_deduction=tax,
            new_elo=verdict.new_elo,
            disciplinary_action=verdict.full_description,
            disciplinary_tier=verdict.tier,
            metadata=metadata or {},
        )

        return penalty_event, verdict
