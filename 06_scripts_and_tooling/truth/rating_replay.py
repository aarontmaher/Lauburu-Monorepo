#!/usr/bin/env python3
"""
Truth Rating Replay Engine & Bradley-Terry MLE Leaderboard
Subsystem: 06_scripts_and_tooling/truth/rating_replay.py

Features:
- Pure Python & NumPy only.
- Strict JSONL ledger schema validation.
- Hallucinated citation penalty: scored as p=1.0 on clean (label=0) items.
- Calibration metrics: Brier score, Precision@0.5, Recall@0.5, F1@0.5.
- Batch Bradley-Terry Maximum Likelihood Estimation via Hunter's MM algorithm.
- Deterministic Scanner anchored at 1500: R = 1500 + 400 * log10(pi / pi_anchor).
- 1000-bootstrap 95% Confidence Interval with fixed seed.
- Status: PROVISIONAL if n < 30 or CI width >= 200, otherwise ESTABLISHED.
- Global leaderboard fit + Tier-filtered boards (TinyLM <=20M, MiniLM, Edge 0.5-8B, Sovereign >8B, Cloud, Anchor).
- Latency (p50) and Cost per 100 items ($/100) columns.
- Rotating 20% holdout split (5 folds) + exclusion of model-specific LoRA training items.
- Deterministic verify mode: recomputes and checks bit-identical output + SHA256 checksum.
- Built-in unit test suite with an analytically verified, hand-computed 3-model example.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import unittest
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


# ==============================================================================
# 1. LEDGER SCHEMA & RECORD PARSING
# ==============================================================================

@dataclass
class LedgerRecord:
    item_hash: str
    label: int  # 1 = FAKE / Violation, 0 = CLEAN / Control
    source: str
    model: str  # GGUF basename/sha from /props or cloud model id + generation id
    p: float  # Model's predicted probability in [0.0, 1.0] that item is FAKE
    citation: Any  # Citation string, list of findings, or dict
    response_hash: str
    ts: float  # Unix timestamp or float epoch
    latency_s: float = 0.0
    cost_usd: float = 0.0
    tier: str = "Unknown"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LedgerRecord:
        required = ["item_hash", "label", "source", "model", "p", "response_hash"]
        for field in required:
            if field not in d:
                raise ValueError(f"Missing required ledger field: {field}")

        label = int(d["label"])
        if label not in (0, 1):
            raise ValueError(f"Invalid label {label}, must be 0 or 1")

        p = float(d["p"])
        if p < 0.0 or p > 1.0:
            p = max(0.0, min(1.0, p))

        ts = d.get("ts", 0.0)
        if isinstance(ts, str):
            try:
                # Handle ISO 8601 or float string
                import datetime
                dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_val = dt.timestamp()
            except Exception:
                try:
                    ts_val = float(ts)
                except Exception:
                    ts_val = 0.0
        else:
            ts_val = float(ts)

        tier = str(d.get("tier", "")).strip()
        model_name = str(d["model"])
        if not tier or tier == "Unknown":
            tier = classify_tier(model_name)

        return cls(
            item_hash=str(d["item_hash"]),
            label=label,
            source=str(d["source"]),
            model=model_name,
            p=p,
            citation=d.get("citation", ""),
            response_hash=str(d["response_hash"]),
            ts=ts_val,
            latency_s=float(d.get("latency_s", 0.0)),
            cost_usd=float(d.get("cost_usd", 0.0)),
            tier=tier,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_tier(model_name: str) -> str:
    """Classify a model into canonical hardware & model size tiers."""
    lower = model_name.lower()
    if "scanner" in lower or "deterministic" in lower or "anchor" in lower:
        return "Anchor"
    if "bge-small" in lower or "tinylm" in lower or "nano" in lower or "<=20m" in lower:
        return "TinyLM"
    if "smollm2-135m" in lower or "135m" in lower or "360m" in lower or "minilm" in lower:
        return "MiniLM"
    if any(k in lower for k in ["0.5b", "1b", "1.5b", "3b", "7b", "8b", "hermes", "vl-7b", "coder-7b"]):
        return "Edge"
    if any(k in lower for k in ["27b", "32b", "70b", "72b", "80b", "qwen3.8", "qwen_38", "sovereign"]):
        return "Sovereign"
    if any(k in lower for k in ["gemini", "claude", "gpt", "deepseek-api", "cloud", "openrouter"]):
        return "Cloud"
    return "Edge"


def has_truthy_citation(citation: Any) -> bool:
    """Check if citation indicates that the model claimed a fake data finding."""
    if citation is None:
        return False
    if isinstance(citation, (list, tuple)):
        return len(citation) > 0
    if isinstance(citation, dict):
        return len(citation) > 0
    if isinstance(citation, str):
        cleaned = citation.strip().lower()
        if not cleaned or cleaned in ("none", "null", "[]", "{}", "clean", "false", "0"):
            return False
        return True
    return bool(citation)


def compute_effective_p(record: LedgerRecord) -> float:
    """
    Applies the Truth Invariant:
    'hallucinated citation scored as p=1 on clean item'
    """
    if record.label == 0 and has_truthy_citation(record.citation):
        return 1.0
    return record.p


# ==============================================================================
# 2. METRICS: BRIER, PRECISION, RECALL, F1
# ==============================================================================

@dataclass
class ModelMetrics:
    model: str
    tier: str
    n: int
    brier: float
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    p50_latency_s: float
    mean_latency_s: float
    cost_per_100: float


def compute_model_metrics(records: List[LedgerRecord]) -> ModelMetrics:
    if not records:
        raise ValueError("Cannot compute metrics on empty record list")

    model_name = records[0].model
    tier = records[0].tier
    n = len(records)

    effective_ps = np.array([compute_effective_p(r) for r in records], dtype=np.float64)
    labels = np.array([r.label for r in records], dtype=np.float64)
    latencies = np.array([r.latency_s for r in records], dtype=np.float64)
    costs = np.array([r.cost_usd for r in records], dtype=np.float64)

    # Brier score = mean((p - y)^2)
    brier = float(np.mean((effective_ps - labels) ** 2))

    # Binary classification @ threshold 0.5
    preds = (effective_ps >= 0.5).astype(int)
    y_true = labels.astype(int)

    tp = int(np.sum((preds == 1) & (y_true == 1)))
    fp = int(np.sum((preds == 1) & (y_true == 0)))
    tn = int(np.sum((preds == 0) & (y_true == 0)))
    fn = int(np.sum((preds == 0) & (y_true == 1)))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0.0 else 0.0

    p50_lat = float(np.median(latencies)) if len(latencies) > 0 else 0.0
    mean_lat = float(np.mean(latencies)) if len(latencies) > 0 else 0.0
    cost_100 = float(np.sum(costs) / n * 100.0) if n > 0 else 0.0

    return ModelMetrics(
        model=model_name,
        tier=tier,
        n=n,
        brier=brier,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        p50_latency_s=p50_lat,
        mean_latency_s=mean_lat,
        cost_per_100=cost_100,
    )


# ==============================================================================
# 3. BATCH BRADLEY-TERRY MLE (HUNTER'S MM ALGORITHM)
# ==============================================================================

def build_pairwise_win_matrix(
    models: List[str],
    records_by_item: Dict[str, Dict[str, LedgerRecord]],
    item_hashes: List[str],
    epsilon: float = 1e-7,
) -> np.ndarray:
    """
    Build win matrix W where W[i, j] is the number of times model i beat model j.
    On item k, loss(m, k) = (eff_p - y)^2 (item Brier loss).
    Model i wins if loss(i, k) < loss(j, k) - epsilon.
    Ties award 0.5 to each.
    """
    M = len(models)
    model_idx = {m: idx for idx, m in enumerate(models)}
    W = np.zeros((M, M), dtype=np.float64)

    for item_h in item_hashes:
        evals = records_by_item.get(item_h, {})
        # Find which models evaluated this item
        active = [m for m in models if m in evals]
        if len(active) < 2:
            continue

        losses = {}
        for m in active:
            rec = evals[m]
            eff_p = compute_effective_p(rec)
            loss = (eff_p - rec.label) ** 2
            losses[m] = loss

        # Pairwise updates
        for idx_a, m_a in enumerate(active):
            i = model_idx[m_a]
            loss_a = losses[m_a]
            for m_b in active[idx_a + 1:]:
                j = model_idx[m_b]
                loss_b = losses[m_b]
                if loss_a < loss_b - epsilon:
                    W[i, j] += 1.0
                elif loss_b < loss_a - epsilon:
                    W[j, i] += 1.0
                else:
                    W[i, j] += 0.5
                    W[j, i] += 0.5

    return W


def bradley_terry_mm(
    W: np.ndarray,
    anchor_idx: int = 0,
    max_iter: int = 1000,
    tol: float = 1e-8,
    prior: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Majorization-Minimization (MM) algorithm for Bradley-Terry MLE (Hunter 2004).
    anchor = deterministic scanner at 1500:
    R = 1500 + 400 * log10(pi / pi_anchor)
    """
    M = W.shape[0]
    if M == 1:
        return np.array([1.0], dtype=np.float64), np.array([1500.0], dtype=np.float64)

    N = W + W.T
    wins = np.sum(W, axis=1) + prior  # Small prior guarantees numerical positivity
    pi = np.ones(M, dtype=np.float64)

    for iteration in range(max_iter):
        pi_prev = pi.copy()
        for i in range(M):
            denom = 0.0
            for j in range(M):
                if i != j and N[i, j] > 0:
                    denom += N[i, j] / (pi_prev[i] + pi_prev[j])
            denom = max(denom, 1e-12)
            pi[i] = wins[i] / denom

        # Normalize relative to anchor
        if pi[anchor_idx] > 0:
            pi = pi / pi[anchor_idx]
        else:
            pi = pi / np.mean(pi)

        max_delta = np.max(np.abs(pi - pi_prev))
        if max_delta < tol:
            break

    # Anchor scaling: R = 1500 + 400 * log10(pi / pi_anchor)
    ref_pi = max(pi[anchor_idx], 1e-12)
    R = 1500.0 + 400.0 * np.log10(np.maximum(pi / ref_pi, 1e-12))
    return pi, R


# ==============================================================================
# 4. 1000-BOOTSTRAP 95% CONFIDENCE INTERVALS
# ==============================================================================

def bootstrap_ratings(
    models: List[str],
    records_by_item: Dict[str, Dict[str, LedgerRecord]],
    all_item_hashes: List[str],
    anchor_idx: int = 0,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    1000-bootstrap with fixed seed to compute 95% Confidence Intervals.
    Returns: (ci_low, ci_high, ci_width)
    """
    M = len(models)
    K = len(all_item_hashes)
    if M <= 1 or K == 0:
        return np.full(M, 1500.0), np.full(M, 1500.0), np.zeros(M)

    rng = np.random.default_rng(seed)
    boot_ratings = np.zeros((n_bootstraps, M), dtype=np.float64)

    # Pre-extract item losses for fast vectorization
    item_arr = np.array(all_item_hashes)

    for b in range(n_bootstraps):
        sampled_hashes = rng.choice(item_arr, size=K, replace=True).tolist()
        W_b = build_pairwise_win_matrix(models, records_by_item, sampled_hashes)
        _, R_b = bradley_terry_mm(W_b, anchor_idx=anchor_idx, max_iter=200, tol=1e-5, prior=1e-4)
        boot_ratings[b] = R_b

    ci_low = np.percentile(boot_ratings, 2.5, axis=0)
    ci_high = np.percentile(boot_ratings, 97.5, axis=0)
    ci_width = ci_high - ci_low

    return ci_low, ci_high, ci_width


# ==============================================================================
# 5. ROTATING HOLDOUT & LORA TRAINING EXCLUSION
# ==============================================================================

def get_item_fold(item_hash: str, n_folds: int = 5) -> int:
    """Deterministically assign item to fold 0..4 via SHA256 modulo."""
    h_int = int(hashlib.sha256(item_hash.encode("utf-8")).hexdigest()[:8], 16)
    return h_int % n_folds


def filter_ledger_records(
    records: List[LedgerRecord],
    holdout_fold: Optional[int] = None,
    lora_exclude_map: Optional[Dict[str, Set[str]]] = None,
) -> List[LedgerRecord]:
    """
    Filters records by:
    1. Rotating 20% holdout fold (if specified).
    2. Exclude items used in that model's LoRA training (prevent evaluation contamination).
    """
    filtered = []
    lora_map = lora_exclude_map or {}

    for r in records:
        # Check LoRA contamination
        excluded_items = lora_map.get(r.model, set())
        if r.item_hash in excluded_items:
            continue

        # Check holdout fold
        if holdout_fold is not None:
            if get_item_fold(r.item_hash) != holdout_fold:
                continue

        filtered.append(r)

    return filtered


# ==============================================================================
# 6. LEADERBOARD COMPUTATION & PROVISIONAL STATUS
# ==============================================================================

@dataclass
class LeaderboardEntry:
    rank: int
    model: str
    tier: str
    rating: float
    ci_low: float
    ci_high: float
    ci_width: float
    status: str  # PROVISIONAL or ESTABLISHED
    brier: float
    precision: float
    recall: float
    f1: float
    n: int
    p50_latency_s: float
    cost_per_100: float


def compute_leaderboard(
    records: List[LedgerRecord],
    anchor_model_hint: str = "scanner",
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Tuple[List[LeaderboardEntry], np.ndarray]:
    if not records:
        return [], np.zeros((0, 0))

    # Organize records
    by_model: Dict[str, List[LedgerRecord]] = {}
    by_item: Dict[str, Dict[str, LedgerRecord]] = {}
    item_hashes_set: Set[str] = set()

    for r in records:
        by_model.setdefault(r.model, []).append(r)
        by_item.setdefault(r.item_hash, {})[r.model] = r
        item_hashes_set.add(r.item_hash)

    models = sorted(list(by_model.keys()))
    item_hashes = sorted(list(item_hashes_set))

    # Identify anchor
    anchor_idx = 0
    anchor_found = False
    for idx, m in enumerate(models):
        if anchor_model_hint.lower() in m.lower():
            anchor_idx = idx
            anchor_found = True
            break

    # Build Win Matrix & Run MM
    W = build_pairwise_win_matrix(models, by_item, item_hashes)
    pi, R = bradley_terry_mm(W, anchor_idx=anchor_idx)

    # 1000-bootstrap CI
    ci_low, ci_high, ci_width = bootstrap_ratings(
        models=models,
        records_by_item=by_item,
        all_item_hashes=item_hashes,
        anchor_idx=anchor_idx,
        n_bootstraps=n_bootstraps,
        seed=seed,
    )

    # Gather metrics & assemble entries
    entries: List[LeaderboardEntry] = []
    for idx, m in enumerate(models):
        recs = by_model[m]
        met = compute_model_metrics(recs)

        # Status invariant: PROVISIONAL if n < 30 or CI width >= 200
        is_provisional = (met.n < 30) or (ci_width[idx] >= 200.0)
        status = "PROVISIONAL" if is_provisional else "ESTABLISHED"

        entries.append(LeaderboardEntry(
            rank=0,
            model=m,
            tier=met.tier,
            rating=float(R[idx]),
            ci_low=float(ci_low[idx]),
            ci_high=float(ci_high[idx]),
            ci_width=float(ci_width[idx]),
            status=status,
            brier=met.brier,
            precision=met.precision,
            recall=met.recall,
            f1=met.f1,
            n=met.n,
            p50_latency_s=met.p50_latency_s,
            cost_per_100=met.cost_per_100,
        ))

    # Sort descending by rating
    entries.sort(key=lambda e: e.rating, reverse=True)
    for rk, e in enumerate(entries, 1):
        e.rank = rk

    return entries, W


def format_leaderboard_table(entries: List[LeaderboardEntry], title: str = "GLOBAL TRUTH LEADERBOARD") -> str:
    """Renders a clean, fixed-width ASCII leaderboard table."""
    lines = []
    lines.append("=" * 132)
    lines.append(f"  {title}")
    lines.append("=" * 132)
    hdr = (
        f"{'Rk':>2} | {'Model Identity':<36} | {'Tier':<9} | {'Rating':>7} | "
        f"{'95% CI':<15} | {'Width':>5} | {'Status':<11} | {'Brier':>6} | "
        f"{'Prec':>5} | {'Rec':>5} | {'F1':>5} | {'n':>3} | {'p50(s)':>6} | {'$/100':>6}"
    )
    lines.append(hdr)
    lines.append("-" * 132)

    for e in entries:
        ci_str = f"[{e.ci_low:.0f}, {e.ci_high:.0f}]"
        # Shorten model display if very long
        disp_name = e.model if len(e.model) <= 36 else (e.model[:33] + "...")
        row = (
            f"{e.rank:>2} | {disp_name:<36} | {e.tier:<9} | {e.rating:>7.1f} | "
            f"{ci_str:<15} | {e.ci_width:>5.0f} | {e.status:<11} | {e.brier:>6.3f} | "
            f"{e.precision:>5.2f} | {e.recall:>5.2f} | {e.f1:>5.2f} | {e.n:>3} | "
            f"{e.p50_latency_s:>6.2f} | ${e.cost_per_100:>5.4f}"
        )
        lines.append(row)

    lines.append("=" * 132)
    return "\n".join(lines)


# ==============================================================================
# 7. DETERMINISTIC REPRODUCIBILITY & --verify CHECKSUM
# ==============================================================================

def export_canonical_json(entries: List[LeaderboardEntry]) -> str:
    """Exports entries as sorted, deterministic JSON string."""
    dict_list = [asdict(e) for e in entries]
    # Ensure float formatting is uniform
    return json.dumps(dict_list, sort_keys=True, indent=2)


def verify_reproducibility(records: List[LedgerRecord], seed: int = 42) -> str:
    """Recomputes twice and asserts bit-identical SHA256 checksum."""
    entries1, _ = compute_leaderboard(records, seed=seed)
    json1 = export_canonical_json(entries1)
    sha1 = hashlib.sha256(json1.encode("utf-8")).hexdigest()

    entries2, _ = compute_leaderboard(records, seed=seed)
    json2 = export_canonical_json(entries2)
    sha2 = hashlib.sha256(json2.encode("utf-8")).hexdigest()

    if sha1 != sha2 or json1 != json2:
        raise AssertionError("Non-deterministic execution detected: SHA256 mismatch across identical runs!")

    return sha1


# ==============================================================================
# 8. UNIT TESTS WITH HAND-COMPUTED 3-MODEL PROOF
# ==============================================================================

class TestTruthRatingReplay(unittest.TestCase):
    """
    Unit test suite covering:
    - Hand-computed 3-model Bradley-Terry analytical solution.
    - Hallucinated citation penalty (effective p = 1.0 on clean items).
    - Calibration metrics: Brier, Precision@0.5, Recall@0.5, F1@0.5.
    - PROVISIONAL rule gating (n < 30 and CI width >= 200).
    - Rotating 20% holdout fold and LoRA exclusion logic.
    - Deterministic SHA256 reproducibility.
    """

    def test_hand_computed_3_model_mle(self):
        """
        Analytical Derivation of 3-Model Bradley-Terry MLE:
        Let models be A, B, and C (anchor).
        Matchup wins:
          A vs B: W_AB = 5, W_BA = 5 (N_AB = 10)
          A vs C: W_AC = 6, W_CA = 3 (N_AC = 9)
          B vs C: W_BC = 6, W_CB = 3 (N_BC = 9)
        Total wins: W_A = 11, W_B = 11, W_C = 6.
        By symmetry between A and B: pi_A = pi_B = x.
        With anchor pi_C = 1.0:
          At MLE: W_A = x * [ 10/(2x) + 9/(x+1) ] = 5 + 9x/(x+1) = 11
          => 9x / (x+1) = 6
          => 9x = 6x + 6 => 3x = 6 => x = 2.0.
        Exact Solution:
          pi_A = 2.0, pi_B = 2.0, pi_C = 1.0.
          R_C = 1500.0 (anchor)
          R_A = 1500 + 400 * log10(2) = 1620.411998...
          R_B = 1500 + 400 * log10(2) = 1620.411998...
        """
        W = np.array([
            [0.0, 5.0, 6.0],
            [5.0, 0.0, 6.0],
            [3.0, 3.0, 0.0],
        ], dtype=np.float64)

        pi, R = bradley_terry_mm(W, anchor_idx=2, max_iter=1000, tol=1e-9, prior=0.0)

        expected_pi = np.array([2.0, 2.0, 1.0])
        expected_R = 1500.0 + 400.0 * np.log10(expected_pi)

        np.testing.assert_allclose(pi, expected_pi, atol=1e-5, rtol=1e-5)
        np.testing.assert_allclose(R, expected_R, atol=1e-4, rtol=1e-4)
        self.assertAlmostEqual(R[2], 1500.0, places=4)
        self.assertAlmostEqual(R[0], 1620.4120, places=3)
        self.assertAlmostEqual(R[1], 1620.4120, places=3)

    def test_hallucinated_citation_penalty(self):
        """Clean item (label=0) with citation must be scored as p=1.0."""
        clean_rec = LedgerRecord(
            item_hash="item_1",
            label=0,
            source="test",
            model="test_model",
            p=0.1,  # Low predicted probability
            citation="[line 12: fabricated value]",  # Hallucinated citation!
            response_hash="resp_1",
            ts=1000.0,
        )
        eff_p = compute_effective_p(clean_rec)
        self.assertEqual(eff_p, 1.0)

        # Clean item without citation retains original p
        clean_no_cite = LedgerRecord(
            item_hash="item_2",
            label=0,
            source="test",
            model="test_model",
            p=0.1,
            citation="",
            response_hash="resp_2",
            ts=1000.0,
        )
        self.assertEqual(compute_effective_p(clean_no_cite), 0.1)

    def test_metrics_calculation(self):
        """Verify Brier, Precision, Recall, and F1 calculations."""
        records = [
            LedgerRecord("h1", 1, "s", "m", 0.9, "", "r1", 0.0),  # TP
            LedgerRecord("h2", 1, "s", "m", 0.8, "", "r2", 0.0),  # TP
            LedgerRecord("h3", 1, "s", "m", 0.2, "", "r3", 0.0),  # FN
            LedgerRecord("h4", 0, "s", "m", 0.1, "", "r4", 0.0),  # TN
            LedgerRecord("h5", 0, "s", "m", 0.7, "", "r5", 0.0),  # FP
        ]
        m = compute_model_metrics(records)
        self.assertEqual(m.tp, 2)
        self.assertEqual(m.fp, 1)
        self.assertEqual(m.tn, 1)
        self.assertEqual(m.fn, 1)
        self.assertAlmostEqual(m.precision, 2.0 / 3.0, places=4)
        self.assertAlmostEqual(m.recall, 2.0 / 3.0, places=4)
        self.assertAlmostEqual(m.f1, 2.0 / 3.0, places=4)
        expected_brier = (0.01 + 0.04 + 0.64 + 0.01 + 0.49) / 5.0
        self.assertAlmostEqual(m.brier, expected_brier, places=4)

    def test_provisional_status_rule(self):
        """Status must be PROVISIONAL if n < 30 or CI width >= 200."""
        # n = 10 (< 30) => PROVISIONAL
        small_records = [
            LedgerRecord(f"item_{i}", i % 2, "src", "small_mod", 0.9 if i % 2 == 1 else 0.1, "", "rh", 0.0)
            for i in range(10)
        ]
        entries, _ = compute_leaderboard(small_records, n_bootstraps=50)
        self.assertEqual(entries[0].status, "PROVISIONAL")

    def test_holdout_and_lora_exclusion(self):
        """Verify 20% holdout split and LoRA item exclusion."""
        records = [
            LedgerRecord(f"hash_{i}", 1, "s", "m1", 0.9, "", "r", 0.0)
            for i in range(20)
        ]
        # Test fold filtering
        fold0 = filter_ledger_records(records, holdout_fold=0)
        self.assertTrue(0 < len(fold0) < 20)
        for r in fold0:
            self.assertEqual(get_item_fold(r.item_hash), 0)

        # Test LoRA exclusion
        exclude_map = {"m1": {"hash_0", "hash_1"}}
        excluded = filter_ledger_records(records, lora_exclude_map=exclude_map)
        self.assertEqual(len(excluded), 18)
        self.assertNotIn("hash_0", {r.item_hash for r in excluded})
        self.assertNotIn("hash_1", {r.item_hash for r in excluded})

    def test_verify_reproducibility(self):
        """Verify bit-identical execution and SHA256 checksum check."""
        records = [
            LedgerRecord("h1", 1, "s", "m_a", 0.9, "", "r1", 0.0),
            LedgerRecord("h2", 0, "s", "m_a", 0.1, "", "r2", 0.0),
            LedgerRecord("h1", 1, "s", "deterministic_scanner", 1.0, "finding", "r3", 0.0),
            LedgerRecord("h2", 0, "s", "deterministic_scanner", 0.0, "", "r4", 0.0),
        ]
        sha = verify_reproducibility(records, seed=42)
        self.assertIsInstance(sha, str)
        self.assertEqual(len(sha), 64)


# ==============================================================================
# 9. CLI ENTRYPOINT
# ==============================================================================

def load_ledger_file(path: Path) -> List[LedgerRecord]:
    if not path.is_file():
        raise FileNotFoundError(f"Ledger file not found: {path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                data = json.loads(line)
                records.append(LedgerRecord.from_dict(data))
            except Exception as e:
                print(f"Warning: line {line_num} in {path} skipped: {e}", file=sys.stderr)
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Truth Rating Replay Engine & Bradley-Terry MLE Leaderboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("ledger", nargs="?", type=str, help="Path to input JSONL ledger file")
    parser.add_argument("--test", action="store_true", help="Run self-contained unit tests and exit")
    parser.add_argument("--verify", action="store_true", help="Recompute and verify bit-identical output + SHA256")
    parser.add_argument("--tier", type=str, choices=["TinyLM", "MiniLM", "Edge", "Sovereign", "Cloud", "Anchor", "all"], default="all", help="Filter leaderboard by model tier")
    parser.add_argument("--holdout-fold", type=int, choices=[0, 1, 2, 3, 4], default=None, help="Evaluate on specific 20 percent holdout fold (0-4)")
    parser.add_argument("--lora-exclude-file", type=str, default=None, help="JSON file mapping model -> [item_hashes] used in LoRA training to exclude")
    parser.add_argument("--bootstraps", type=int, default=1000, help="Number of bootstrap resamples for 95 percent CI")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for bootstrap")
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout")
    parser.add_argument("--anchor", type=str, default="scanner", help="Sub-string to identify anchor model (default 1500)")

    args = parser.parse_args()

    if args.test:
        # Run test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTruthRatingReplay)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)

    if not args.ledger:
        # Default fallback to truth_rating_ledger.jsonl if present
        default_p = Path(__file__).resolve().parent / "truth_rating_ledger.jsonl"
        if default_p.is_file():
            ledger_path = default_p
        else:
            parser.print_help()
            print("\nError: Please provide a ledger file or run with --test", file=sys.stderr)
            sys.exit(1)
    else:
        ledger_path = Path(args.ledger)

    records = load_ledger_file(ledger_path)
    if not records:
        print(f"Error: No valid records found in {ledger_path}", file=sys.stderr)
        sys.exit(1)

    # Load LoRA exclusions if provided
    lora_map: Dict[str, Set[str]] = {}
    if args.lora_exclude_file:
        with open(args.lora_exclude_file, "r", encoding="utf-8") as f:
            raw_ex = json.load(f)
            lora_map = {m: set(items) for m, items in raw_ex.items()}

    # Filter records (holdout / LoRA)
    filtered = filter_ledger_records(records, holdout_fold=args.holdout_fold, lora_exclude_map=lora_map)

    if args.verify:
        try:
            sha = verify_reproducibility(filtered, seed=args.seed)
            print(f"[VERIFIED BIT-IDENTICAL SHA256: {sha}]")
            sys.exit(0)
        except Exception as e:
            print(f"[VERIFICATION FAILED]: {e}", file=sys.stderr)
            sys.exit(1)

    # Compute Global Fit
    entries, _ = compute_leaderboard(
        records=filtered,
        anchor_model_hint=args.anchor,
        n_bootstraps=args.bootstraps,
        seed=args.seed,
    )

    # Tier filtering
    if args.tier != "all":
        entries = [e for e in entries if e.tier.lower() == args.tier.lower()]
        for rk, e in enumerate(entries, 1):
            e.rank = rk

    if args.json:
        print(export_canonical_json(entries))
    else:
        title = f"TRUTH LEADERBOARD (Tier: {args.tier.upper()})"
        if args.holdout_fold is not None:
            title += f" [Holdout Fold {args.holdout_fold}/5]"
        print(format_leaderboard_table(entries, title=title))
        print(f"Total Evaluated Records: {len(filtered)} across {len(entries)} models.")


if __name__ == "__main__":
    main()
