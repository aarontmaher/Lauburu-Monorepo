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
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

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

MIN_ELO_RATING: float = 1000.0  # Canonical minimum ELO rating bound
MAX_ELO_RATING: float = 3000.0  # Canonical maximum ELO rating bound


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
        Clamps exponent to [-20.0, 20.0] to eliminate OverflowError.

        E_A = 1.0 / (1.0 + 10^((R_B - R_A) / 400.0))
        E_B = 1.0 - E_A
        """
        exp = max(-20.0, min(20.0, (float(rating_b) - float(rating_a)) / 400.0))
        ea = 1.0 / (1.0 + 10.0 ** exp)
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
        r_david = max(MIN_ELO_RATING, min(MAX_ELO_RATING, float(r_david)))
        r_goliath = max(MIN_ELO_RATING, min(MAX_ELO_RATING, float(r_goliath)))
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

        new_david = max(MIN_ELO_RATING, min(MAX_ELO_RATING, current_elo_david + total_delta_david))
        new_goliath = max(MIN_ELO_RATING, min(MAX_ELO_RATING, current_elo_goliath + total_delta_goliath))

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


# ---------------------------------------------------------------------------
# Wilson Score Confidence Intervals & Multi-Category Scorecard (Feature F7)
# Authoritative Reference: ORIGINAL_REQUEST.md (§R3) & PROJECT.md (§Interface Contract #4)
# ---------------------------------------------------------------------------

class WilsonConfidenceInterval(tuple):
    """
    Tuple subclass representing a confidence interval [lower, upper].
    Provides .lower, .upper, .spread attributes and dictionary serialization.
    """
    def __new__(cls, lower: float, upper: float):
        return super().__new__(cls, (float(lower), float(upper)))

    @property
    def lower(self) -> float:
        return self[0]

    @property
    def upper(self) -> float:
        return self[1]

    @property
    def spread(self) -> float:
        return self[1] - self[0]

    def to_dict(self) -> Dict[str, float]:
        return {
            "lower": round(self[0], 4),
            "upper": round(self[1], 4),
            "spread": round(self.spread, 4),
        }


def _norm_ppf_from_confidence(confidence: float) -> float:
    """
    Compute normal quantile z for a given symmetric two-tailed confidence level.
    For confidence=0.95, returns 1.959963984540054.
    Uses Acklam / Beasley-Springer-Moro rational approximation with 10^-9 precision.
    """
    if abs(confidence - 0.95) < 1e-6:
        return 1.959963984540054
    p = 1.0 - (1.0 - max(0.0001, min(0.9999, float(confidence)))) / 2.0
    if p == 0.5:
        return 0.0

    a = [
        -3.969683028665376e+01,  2.209460984245205e+02,
        -2.759285104469687e+02,  1.383577518672690e+02,
        -3.066479806614716e+01,  2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01,  1.615858368580409e+02,
        -1.556989798598866e+02,  6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00,  2.938163982698783e+00,
    ]
    d = [
         7.784695709041462e-03,  3.224671290700398e-01,
         2.445134137142996e+00,  3.754408661907416e+00,
    ]
    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)


def calculate_wilson_confidence_interval(
    k: int,
    n: int,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """
    Calculate closed-form Wilson score interval for binomial proportions.
    Guarantees strict [0.0, 1.0] bounds and non-zero uncertainty for k == n.
    Used for qualitative/sensorless software verification components under finite Bernoulli trials.

    Formula:
    center = (p_hat + z^2 / (2n)) / (1 + z^2 / n)
    spread = (z * sqrt((p_hat * (1 - p_hat) + z^2 / (4n^2)) / n)) / (1 + z^2 / n)
    [lower, upper] = [max(0.0, center - spread), min(1.0, center + spread)]
    """
    if n <= 0:
        return WilsonConfidenceInterval(0.0, 1.0)

    n_flt = float(n)
    k_clamped = max(0, min(int(n), int(k)))
    p_hat = float(k_clamped) / n_flt

    z = _norm_ppf_from_confidence(confidence)
    z2 = z * z

    denom = 1.0 + (z2 / n_flt)
    center = (p_hat + (z2 / (2.0 * n_flt))) / denom
    radicand = (p_hat * (1.0 - p_hat) + (z2 / (4.0 * n_flt))) / n_flt
    spread = (z * math.sqrt(max(0.0, radicand))) / denom

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    if k_clamped == 0:
        lower = 0.0
    if k_clamped == int(n):
        upper = 1.0
    return WilsonConfidenceInterval(lower, upper)


@dataclass
class CategoryScorecard:
    """
    Evaluation scorecard for a single system category.
    Conforms to PROJECT.md §Interface Contract #4 and R3 requirements.
    """
    category: str
    rating: float
    confidence_interval: Tuple[float, float]
    trials: int
    passes: int
    expected_vs_baseline: float = 0.5

    @property
    def successes(self) -> int:
        return self.passes

    @property
    def pass_rate(self) -> float:
        return float(self.passes) / float(self.trials) if self.trials > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        ci = self.confidence_interval
        ci_dict = {
            "lower": round(ci[0], 4),
            "upper": round(ci[1], 4),
            "spread": round(ci[1] - ci[0], 4),
        }
        return {
            "category": self.category,
            "rating": round(self.rating, 1),
            "trials": self.trials,
            "passes": self.passes,
            "successes": self.passes,
            "pass_rate": round(self.pass_rate, 4),
            "confidence_interval": ci_dict,
            "confidence_interval_tuple": (round(ci[0], 4), round(ci[1], 4)),
            "expected_vs_baseline": round(self.expected_vs_baseline, 4),
        }


@dataclass
class ProjectEloScorecard:
    """
    Aggregated project-level ELO scorecard across Frontend, Backend, and AI Models.
    Conforms to PROJECT.md §Interface Contract #4 and R3 requirements.
    """
    timestamp: str
    frontend: CategoryScorecard
    backend: CategoryScorecard
    ai_models: CategoryScorecard
    composite_score: float
    evaluation_latency_us: float

    @property
    def timestamp_utc(self) -> str:
        return self.timestamp

    @property
    def composite_elo(self) -> float:
        return self.composite_score

    @property
    def sla_compliant_50us(self) -> bool:
        return self.evaluation_latency_us <= 50.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "timestamp_utc": self.timestamp,
            "frontend": self.frontend.to_dict(),
            "backend": self.backend.to_dict(),
            "ai_models": self.ai_models.to_dict(),
            "composite_score": round(self.composite_score, 1),
            "composite_elo": round(self.composite_score, 1),
            "evaluation_latency_us": round(self.evaluation_latency_us, 2),
            "sla_compliant_50us": self.sla_compliant_50us,
        }


def _parse_trials_arg(arg: Any) -> Tuple[int, int]:
    """
    Extract (passes, trials) from a tuple or list.
    Handles both (passes, trials) and (trials, passes).
    """
    if isinstance(arg, (tuple, list)) and len(arg) >= 2:
        a, b = int(arg[0]), int(arg[1])
        if a > b and b >= 0:
            return (b, a)
        return (max(0, a), max(0, b))
    return (0, 0)


def evaluate_project_scorecard(
    frontend_trials: Any = (0, 0),
    backend_trials: Any = (0, 0),
    ai_trials: Any = (0, 0),
    *extra_args,
    frontend_rating: float = 2000.0,
    backend_rating: float = 2000.0,
    ai_rating: float = 2000.0,
    w_frontend: float = 0.30,
    w_backend: float = 0.35,
    w_ai: float = 0.35,
    baseline_rating: float = 2000.0,
    confidence: float = 0.95,
    **extra_kwargs,
) -> ProjectEloScorecard:
    """
    Evaluate 3-category ELO scorecard (Frontend, Backend, AI Models) in <= 50 µs.
    Conforms to PROJECT.md §Interface Contract #4 and R3 requirements.

    Accepts:
    1. Standard contract: evaluate_project_scorecard(fe_trials=(k, n), be_trials=(k, n), ai_trials=(k, n), ...)
    2. Positional ratings: evaluate_project_scorecard(fe_trials, be_trials, ai_trials, fe_rating, be_rating, ai_rating)
    3. 9-arg signature: evaluate_project_scorecard(fe_rating, fe_trials, fe_passes, be_rating, be_trials, be_passes, ai_rating, ai_trials, ai_passes)
    """
    t0 = time.perf_counter_ns()

    # Pattern check: 9 positional scalar arguments (fe_rating, fe_trials, fe_passes, ...)
    if not isinstance(frontend_trials, (tuple, list)) and len(extra_args) >= 6:
        fe_r = float(frontend_trials)
        fe_t = int(backend_trials)
        fe_p = int(ai_trials)
        be_r = float(extra_args[0])
        be_t = int(extra_args[1])
        be_p = int(extra_args[2])
        ai_r = float(extra_args[3])
        ai_t = int(extra_args[4])
        ai_p = int(extra_args[5])
        if len(extra_args) >= 7:
            w_frontend = float(extra_args[6])
        if len(extra_args) >= 8:
            w_backend = float(extra_args[7])
        if len(extra_args) >= 9:
            w_ai = float(extra_args[8])
        if len(extra_args) >= 10:
            baseline_rating = float(extra_args[9])
    else:
        fe_p, fe_t = _parse_trials_arg(frontend_trials)
        be_p, be_t = _parse_trials_arg(backend_trials)
        ai_p, ai_t = _parse_trials_arg(ai_trials)
        fe_r = float(extra_kwargs.get("frontend_rating", extra_args[0] if len(extra_args) > 0 else frontend_rating))
        be_r = float(extra_kwargs.get("backend_rating", extra_args[1] if len(extra_args) > 1 else backend_rating))
        ai_r = float(extra_kwargs.get("ai_rating", extra_args[2] if len(extra_args) > 2 else ai_rating))

    # Rating boundary enforcement [1000.0, 3000.0]
    r_fe = max(MIN_ELO_RATING, min(MAX_ELO_RATING, fe_r))
    r_be = max(MIN_ELO_RATING, min(MAX_ELO_RATING, be_r))
    r_ai = max(MIN_ELO_RATING, min(MAX_ELO_RATING, ai_r))

    # Closed-form Wilson score confidence intervals
    ci_fe = calculate_wilson_confidence_interval(fe_p, fe_t, confidence=confidence)
    ci_be = calculate_wilson_confidence_interval(be_p, be_t, confidence=confidence)
    ci_ai = calculate_wilson_confidence_interval(ai_p, ai_t, confidence=confidence)

    # Bradley-Terry expected scores vs baseline standard
    e_fe = 1.0 / (1.0 + 10.0 ** max(-20.0, min(20.0, (baseline_rating - r_fe) / 400.0)))
    e_be = 1.0 / (1.0 + 10.0 ** max(-20.0, min(20.0, (baseline_rating - r_be) / 400.0)))
    e_ai = 1.0 / (1.0 + 10.0 ** max(-20.0, min(20.0, (baseline_rating - r_ai) / 400.0)))

    # Composite weighted ELO score
    sum_w = w_frontend + w_backend + w_ai
    if sum_w > 0.0:
        composite = (w_frontend * r_fe + w_backend * r_be + w_ai * r_ai) / sum_w
    else:
        composite = (r_fe + r_be + r_ai) / 3.0
    composite_clamped = max(MIN_ELO_RATING, min(MAX_ELO_RATING, composite))
    t1 = time.perf_counter_ns()
    eval_latency_us = (t1 - t0) / 1000.0

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return ProjectEloScorecard(
        timestamp=now_iso,
        frontend=CategoryScorecard(
            category="Frontend",
            rating=r_fe,
            confidence_interval=ci_fe,
            trials=fe_t,
            passes=fe_p,
            expected_vs_baseline=e_fe,
        ),
        backend=CategoryScorecard(
            category="Backend",
            rating=r_be,
            confidence_interval=ci_be,
            trials=be_t,
            passes=be_p,
            expected_vs_baseline=e_be,
        ),
        ai_models=CategoryScorecard(
            category="AI Models",
            rating=r_ai,
            confidence_interval=ci_ai,
            trials=ai_t,
            passes=ai_p,
            expected_vs_baseline=e_ai,
        ),
        composite_score=composite_clamped,
        evaluation_latency_us=eval_latency_us,
    )


# Attach as static methods on EloEngine for class-level access
EloEngine.calculate_wilson_confidence_interval = staticmethod(calculate_wilson_confidence_interval)
EloEngine.evaluate_project_scorecard = staticmethod(evaluate_project_scorecard)
