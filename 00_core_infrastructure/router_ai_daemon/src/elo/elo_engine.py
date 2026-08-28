"""
David vs Goliath ELO Scoring Engine (Features F7, F8).
Authoritative Specifications: ORIGINAL_REQUEST.md (§R4) & spec_miner_1/analysis.md (§4).

Implements asymmetric efficiency-weighted ELO ratings where resource-constrained "David" models
(sub-1B parameter models on router) receive massive ELO multipliers when solving complex tasks,
while massive "Goliath" models (70B+ frontier models) receive near-zero ELO when expending gluttonous
compute on simple tasks.
"""

from __future__ import annotations

import datetime
import math
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

from .waste_tax import (
    DEFAULT_THRESHOLD,
    MAX_TAX_DEDUCTION,
    WasteTaxCalculator,
    calculate_waste_tax,
    evaluate_disciplinary_action,
)


# ---------------------------------------------------------------------------
# Default Constants & Hyperparameters
# ---------------------------------------------------------------------------
DEFAULT_ALPHA: float = 0.30  # Exponent for parameter count ratio
DEFAULT_BETA: float = 0.20   # Exponent for RAM / memory ratio
DEFAULT_DELTA: float = 0.15  # Exponent for token consumption ratio

DAVID_MIN_MULTIPLIER: float = 1.00
DAVID_MAX_MULTIPLIER: float = 50.00

GOLIATH_MIN_MULTIPLIER: float = 0.01
GOLIATH_MAX_MULTIPLIER: float = 1.00

MAX_DAVID_ELO_GAIN: float = 350.0  # Max positive delta clamp for David


# ---------------------------------------------------------------------------
# Dataclasses & Interface Contracts
# ---------------------------------------------------------------------------

@dataclass
class ResourceUsage:
    """Resource consumption profile for a contender in a match."""
    params_b: float           # Parameter count in Billions (e.g. 0.36 for 360M, 70.0 for 70B)
    ram_mb: float             # Runtime RAM consumption in MB (e.g. 98.0, 42000.0)
    tokens: int               # Total tokens consumed to generate solution
    execution_time_s: float = 0.0
    spend_usd: float = 0.0
    spurious_calls: int = 0
    mesh_drain_index: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodeOffMatch:
    """
    Match record for a Shadow Coding challenge between David and Goliath.
    Conforms to PROJECT.md §Interface Contract #3.
    """
    task_id: str
    david_model: str
    goliath_model: str
    task_difficulty: float    # Ω_task in [0.10, 3.00+]
    david_solved: bool
    goliath_solved: bool
    david_resources: ResourceUsage
    goliath_resources: ResourceUsage
    match_id: Optional[str] = None
    challenge_type: str = "SHADOW_CODING_CHALLENGE"
    timestamp_utc: Optional[str] = None
    truth_factor: float = 1.00
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.match_id is None:
            self.match_id = f"match_{uuid.uuid4().hex[:12]}"
        if self.timestamp_utc is None:
            self.timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class EloUpdateResult:
    """
    Result of an ELO rating update from a Shadow Coding match.
    Conforms to PROJECT.md §Interface Contract #3.
    """
    delta_elo_david: float
    delta_elo_goliath: float
    waste_tax_applied: float
    new_elo_david: float
    new_elo_goliath: float
    match_id: str = ""
    david_multiplier: float = 1.0
    goliath_multiplier: float = 1.0
    expected_david: float = 0.5
    expected_goliath: float = 0.5
    david_score: float = 0.0
    goliath_score: float = 0.0
    disciplinary_action_david: Optional[Dict[str, Any]] = None
    disciplinary_action_goliath: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "delta_elo_david": round(self.delta_elo_david, 1),
            "delta_elo_goliath": round(self.delta_elo_goliath, 2),
            "waste_tax_applied": round(self.waste_tax_applied, 2),
            "new_elo_david": round(self.new_elo_david, 1),
            "new_elo_goliath": round(self.new_elo_goliath, 1),
            "david_multiplier": round(self.david_multiplier, 4),
            "goliath_multiplier": round(self.goliath_multiplier, 4),
            "expected_david": round(self.expected_david, 4),
            "expected_goliath": round(self.expected_goliath, 4),
            "david_score": self.david_score,
            "goliath_score": self.goliath_score,
            "disciplinary_action_david": self.disciplinary_action_david,
            "disciplinary_action_goliath": self.disciplinary_action_goliath,
        }


# ---------------------------------------------------------------------------
# Core Elo Engine
# ---------------------------------------------------------------------------

class EloEngine:
    """
    Asymmetric 'David vs Goliath' ELO Scoring Engine.
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        delta: float = DEFAULT_DELTA,
        max_david_gain: float = MAX_DAVID_ELO_GAIN,
        waste_tax_calc: Optional[WasteTaxCalculator] = None,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.delta = delta
        self.max_david_gain = max_david_gain
        self.waste_tax_calc = waste_tax_calc or WasteTaxCalculator()

    # -----------------------------------------------------------------------
    # Mathematical Formulas
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_expected_score(rating_a: float, rating_b: float) -> Tuple[float, float]:
        """
        Calculate standard logistic expected scores for two contenders.

        E_A = 1.0 / (1.0 + 10^((R_B - R_A) / 400.0))
        E_B = 1.0 - E_A
        """
        ea = 1.0 / (1.0 + 10.0 ** ((float(rating_b) - float(rating_a)) / 400.0))
        eb = 1.0 - ea
        return ea, eb

    @staticmethod
    def calculate_david_multiplier(
        param_goliath_b: float,
        param_david_b: float,
        ram_goliath_mb: float,
        ram_david_mb: float,
        tokens_goliath: int,
        tokens_david: int,
        task_complexity: float,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        delta: float = DEFAULT_DELTA,
    ) -> float:
        """
        Calculate Asymmetric Frugality Leverage Multiplier for David (μ_D).

        Formula:
        μ_D = (P_G / P_D)^α * (M_G / M_D)^β * ((T_G + 1) / (T_D + 1))^δ * max(0.10, Ω_task)
        Clamped to [1.00, 50.00].
        """
        p_g = max(0.001, float(param_goliath_b))
        p_d = max(0.001, float(param_david_b))
        p_ratio = max(1.0, p_g / p_d)

        m_g = max(1.0, float(ram_goliath_mb))
        m_d = max(1.0, float(ram_david_mb))
        m_ratio = max(1.0, m_g / m_d)

        t_g = max(0.0, float(tokens_goliath))
        t_d = max(0.0, float(tokens_david))
        t_ratio = max(1.0, (t_g + 1.0) / (t_d + 1.0))

        omega = max(0.10, float(task_complexity))

        mu_d = (p_ratio ** alpha) * (m_ratio ** beta) * (t_ratio ** delta) * omega
        return max(DAVID_MIN_MULTIPLIER, min(DAVID_MAX_MULTIPLIER, float(mu_d)))

    @staticmethod
    def calculate_goliath_multiplier(
        param_david_b: float,
        param_goliath_b: float,
        ram_david_mb: float,
        ram_goliath_mb: float,
        task_complexity: float,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
    ) -> float:
        """
        Calculate Resource Gluttony Penalty Multiplier for Goliath (μ_G).

        Formula:
        μ_G = (P_D / P_G)^α * (M_D / M_G)^β * (1.0 / max(0.10, Ω_task))
        Clamped to [0.01, 1.00].
        """
        p_g = max(0.001, float(param_goliath_b))
        p_d = max(0.001, float(param_david_b))
        p_ratio = min(1.0, max(0.0001, p_d / p_g))

        m_g = max(1.0, float(ram_goliath_mb))
        m_d = max(1.0, float(ram_david_mb))
        m_ratio = min(1.0, max(0.0001, m_d / m_g))

        omega = max(0.10, float(task_complexity))

        mu_g = (p_ratio ** alpha) * (m_ratio ** beta) * (1.0 / omega)
        return max(GOLIATH_MIN_MULTIPLIER, min(GOLIATH_MAX_MULTIPLIER, float(mu_g)))

    @staticmethod
    def calculate_k_factor(
        matches_played: int,
        challenge_type: str = "SHADOW_CODING_CHALLENGE",
        truth_factor: float = 1.00,
    ) -> float:
        """
        Calculate dynamic composite K-factor.

        K0 = 48.0 if matches < 10 else (32.0 if matches < 50 else 24.0)
        K_base = K0 * η_type * η_truth
        """
        if matches_played < 10:
            k0 = 48.0
        elif matches_played < 50:
            k0 = 32.0
        else:
            k0 = 24.0

        eta_type = 1.50 if challenge_type == "SHADOW_CODING_CHALLENGE" else 1.00
        eta_truth = max(0.0, float(truth_factor))

        return k0 * eta_type * eta_truth

    @staticmethod
    def calculate_waste_tax(
        spend_usd: float = 0.0,
        tokens_wasted: int = 0,
        spurious_calls: int = 0,
        mesh_drain_index: float = 0.0,
        optimization_score: float = 0.0,
        threshold: float = DEFAULT_THRESHOLD,
        lambda_base: float = 50.0,
        c0: float = 0.05,
        t0: float = 2048.0,
        gamma: float = 1.25,
        max_tax: float = MAX_TAX_DEDUCTION,
    ) -> float:
        """Helper forwarding to waste_tax module."""
        return calculate_waste_tax(
            spend_usd=spend_usd,
            tokens_wasted=tokens_wasted,
            spurious_calls=spurious_calls,
            mesh_drain_index=mesh_drain_index,
            optimization_score=optimization_score,
            threshold=threshold,
            lambda_base=lambda_base,
            c0=c0,
            t0=t0,
            gamma=gamma,
            max_tax=max_tax,
        )

    # -----------------------------------------------------------------------
    # Match Evaluation & Update Execution
    # -----------------------------------------------------------------------

    def evaluate_match_deltas(
        self,
        r_david: float,
        r_goliath: float,
        david_solved: bool,
        goliath_solved: bool,
        david_resources: ResourceUsage,
        goliath_resources: ResourceUsage,
        task_difficulty: float,
        matches_played_david: int = 0,
        matches_played_goliath: int = 0,
        challenge_type: str = "SHADOW_CODING_CHALLENGE",
        truth_factor: float = 1.00,
    ) -> Dict[str, Any]:
        """
        Evaluate full ELO deltas, multipliers, and expected scores for both contenders.
        """
        e_david, e_goliath = self.calculate_expected_score(r_david, r_goliath)

        mu_david = self.calculate_david_multiplier(
            param_goliath_b=goliath_resources.params_b,
            param_david_b=david_resources.params_b,
            ram_goliath_mb=goliath_resources.ram_mb,
            ram_david_mb=david_resources.ram_mb,
            tokens_goliath=goliath_resources.tokens,
            tokens_david=david_resources.tokens,
            task_complexity=task_difficulty,
            alpha=self.alpha,
            beta=self.beta,
            delta=self.delta,
        )

        mu_goliath = self.calculate_goliath_multiplier(
            param_david_b=david_resources.params_b,
            param_goliath_b=goliath_resources.params_b,
            ram_david_mb=david_resources.ram_mb,
            ram_goliath_mb=goliath_resources.ram_mb,
            task_complexity=task_difficulty,
            alpha=self.alpha,
            beta=self.beta,
        )

        k_david = self.calculate_k_factor(matches_played_david, challenge_type, truth_factor)
        k_goliath = self.calculate_k_factor(matches_played_goliath, challenge_type, truth_factor)

        s_david = 1.0 if david_solved else 0.0
        s_goliath = 1.0 if goliath_solved else 0.0

        # When David wins (S_D > E_D), David's gain is multiplied by μ_D (leverage).
        # When David fails (S_D <= E_D), David's loss is NOT multiplied by μ_D (unamplified loss ~ -1.5).
        if s_david > e_david:
            raw_delta_david = k_david * mu_david * (s_david - e_david)
        else:
            raw_delta_david = k_david * 1.0 * (s_david - e_david)

        # When Goliath wins (S_G > E_G), Goliath's gain is multiplied by μ_G <= 1.0 (gluttony discount).
        # When Goliath fails (S_G <= E_G), Goliath suffers full un-discounted loss (~ -35.0).
        if s_goliath > e_goliath:
            raw_delta_goliath = k_goliath * mu_goliath * (s_goliath - e_goliath)
        else:
            raw_delta_goliath = k_goliath * 1.0 * (s_goliath - e_goliath)

        # David positive gain is clamped to max_david_gain (e.g. +350.0)
        if raw_delta_david > 0:
            delta_david = min(self.max_david_gain, round(raw_delta_david, 1))
        else:
            delta_david = round(raw_delta_david, 1)

        delta_goliath = round(raw_delta_goliath, 2)

        return {
            "delta_david": delta_david,
            "delta_goliath": delta_goliath,
            "mu_david": mu_david,
            "mu_goliath": mu_goliath,
            "e_david": e_david,
            "e_goliath": e_goliath,
            "s_david": s_david,
            "s_goliath": s_goliath,
            "k_david": k_david,
            "k_goliath": k_goliath,
        }

    def record_code_off_result(
        self,
        match: CodeOffMatch,
        current_elo_david: float = 2100.0,
        current_elo_goliath: float = 2800.0,
        matches_played_david: int = 0,
        matches_played_goliath: int = 0,
        ledger: Optional[Any] = None,
    ) -> EloUpdateResult:
        """
        Record and execute a complete code-off match outcome.
        Conforms to PROJECT.md §Interface Contract #3.
        """
        # If ledger is provided, fetch latest ratings & match counts
        if ledger is not None:
            if hasattr(ledger, "get_rating"):
                current_elo_david = ledger.get_rating(match.david_model, default=current_elo_david)
                current_elo_goliath = ledger.get_rating(match.goliath_model, default=current_elo_goliath)
            if hasattr(ledger, "get_match_count"):
                matches_played_david = ledger.get_match_count(match.david_model)
                matches_played_goliath = ledger.get_match_count(match.goliath_model)

        eval_res = self.evaluate_match_deltas(
            r_david=current_elo_david,
            r_goliath=current_elo_goliath,
            david_solved=match.david_solved,
            goliath_solved=match.goliath_solved,
            david_resources=match.david_resources,
            goliath_resources=match.goliath_resources,
            task_difficulty=match.task_difficulty,
            matches_played_david=matches_played_david,
            matches_played_goliath=matches_played_goliath,
            challenge_type=match.challenge_type,
            truth_factor=match.truth_factor,
        )

        base_delta_david = eval_res["delta_david"]
        base_delta_goliath = eval_res["delta_goliath"]

        # Calculate Waste Tax if either contender failed or had wasted spend
        waste_tax_applied = 0.0
        disciplinary_david = None
        disciplinary_goliath = None

        total_delta_david = base_delta_david
        total_delta_goliath = base_delta_goliath

        # Check Goliath waste tax if Goliath failed or had wasteful spend
        if not match.goliath_solved or match.goliath_resources.spend_usd > 0:
            opt_score_goliath = 1.0 if match.goliath_solved else 0.0
            tax_goliath = self.calculate_waste_tax(
                spend_usd=match.goliath_resources.spend_usd,
                tokens_wasted=match.goliath_resources.tokens if not match.goliath_solved else 0,
                spurious_calls=match.goliath_resources.spurious_calls,
                mesh_drain_index=match.goliath_resources.mesh_drain_index,
                optimization_score=opt_score_goliath,
            )
            if tax_goliath < 0:
                waste_tax_applied += tax_goliath
                verdict = evaluate_disciplinary_action(tax_goliath, current_elo_goliath + base_delta_goliath)
                disciplinary_goliath = verdict.to_dict()
                total_delta_goliath += tax_goliath

        # Check David waste tax if David failed and spent money/tokens
        if not match.david_solved and (match.david_resources.spend_usd > 0 or match.david_resources.spurious_calls > 0):
            tax_david = self.calculate_waste_tax(
                spend_usd=match.david_resources.spend_usd,
                tokens_wasted=match.david_resources.tokens,
                spurious_calls=match.david_resources.spurious_calls,
                mesh_drain_index=match.david_resources.mesh_drain_index,
                optimization_score=0.0,
            )
            if tax_david < 0:
                waste_tax_applied += tax_david
                verdict = evaluate_disciplinary_action(tax_david, current_elo_david + base_delta_david)
                disciplinary_david = verdict.to_dict()
                total_delta_david += tax_david

        new_david = current_elo_david + total_delta_david
        new_goliath = current_elo_goliath + total_delta_goliath

        update_result = EloUpdateResult(
            match_id=match.match_id or f"match_{uuid.uuid4().hex[:8]}",
            delta_elo_david=total_delta_david,
            delta_elo_goliath=total_delta_goliath,
            waste_tax_applied=waste_tax_applied,
            new_elo_david=new_david,
            new_elo_goliath=new_goliath,
            david_multiplier=eval_res["mu_david"],
            goliath_multiplier=eval_res["mu_goliath"],
            expected_david=eval_res["e_david"],
            expected_goliath=eval_res["e_goliath"],
            david_score=eval_res["s_david"],
            goliath_score=eval_res["s_goliath"],
            disciplinary_action_david=disciplinary_david,
            disciplinary_action_goliath=disciplinary_goliath,
        )

        # Persist to ledger if provided
        if ledger is not None and hasattr(ledger, "record_match"):
            ledger.record_match({
                "match_id": update_result.match_id,
                "timestamp_utc": match.timestamp_utc,
                "task_id": match.task_id,
                "task_difficulty": match.task_difficulty,
                "david_model": match.david_model,
                "goliath_model": match.goliath_model,
                "david_solved": match.david_solved,
                "goliath_solved": match.goliath_solved,
                "delta_elo_david": total_delta_david,
                "delta_elo_goliath": total_delta_goliath,
                "new_elo_david": new_david,
                "new_elo_goliath": new_goliath,
                "waste_tax_applied": waste_tax_applied,
                "david_multiplier": eval_res["mu_david"],
                "goliath_multiplier": eval_res["mu_goliath"],
            })

        return update_result
