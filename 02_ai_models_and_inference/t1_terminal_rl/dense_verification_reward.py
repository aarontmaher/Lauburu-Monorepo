"""
dense_verification_reward.py - Dense Verification Reward & Anti-Hacking Sentinel.

Implements the globally fixed assertion scaling R = min(1.0, P / S) with S=20,
as established in the T1 paper (arXiv:2609.11042). Resolves the reward dilution
pathology of relative pass ratios (P / Total) and includes a turn-growth sentinel
to penalize non-productive multi-turn exploration loops.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AssertionResult:
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int
    raw_output: str = ""

    @property
    def pass_ratio(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.passed / self.total


@dataclass
class RewardOutput:
    raw_reward: float
    effective_reward: float
    passed_assertions: int
    scale_factor_s: int
    penalty_factor: float
    turn_count: int
    reason: str


class DenseVerificationRewardCalculator:
    """
    Computes global-scale dense verification rewards with anti-reward-hacking
    turn growth penalties.
    """

    DEFAULT_SCALE_S: int = 20
    DEFAULT_OPTIMAL_TURNS: int = 15
    DEFAULT_BETA_PENALTY: float = 0.04
    DEFAULT_GROWTH_TOLERANCE: int = 4

    def __init__(
        self,
        scale_s: int = DEFAULT_SCALE_S,
        optimal_turns: int = DEFAULT_OPTIMAL_TURNS,
        beta_penalty: float = DEFAULT_BETA_PENALTY,
        growth_tolerance: int = DEFAULT_GROWTH_TOLERANCE,
    ):
        if scale_s <= 0:
            raise ValueError(f"scale_s must be positive, got {scale_s}")
        self.scale_s = scale_s
        self.optimal_turns = optimal_turns
        self.beta_penalty = beta_penalty
        self.growth_tolerance = growth_tolerance

    def parse_terminal_test_output(self, stdout: str) -> AssertionResult:
        """
        Parses test assertion outcomes from realistic test runners:
        pytest, python unittest, jest/mocha, go test, and cargo test.
        """
        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Pattern 1: Pytest summary line e.g. "== 18 passed, 2 failed, 1 error in 3.42s =="
        # Search for pytest-style summary line or tokens
        summary_lines = [line for line in stdout.splitlines() if "passed" in line or "failed" in line]
        for line in reversed(summary_lines):
            p_match = re.search(r"(\d+)\s+passed", line)
            f_match = re.search(r"(\d+)\s+failed", line)
            e_match = re.search(r"(\d+)\s+errors?", line)
            s_match = re.search(r"(\d+)\s+skipped", line)

            if p_match or f_match or e_match:
                passed = int(p_match.group(1)) if p_match else 0
                failed = int(f_match.group(1)) if f_match else 0
                errors = int(e_match.group(1)) if e_match else 0
                skipped = int(s_match.group(1)) if s_match else 0
                total = passed + failed + errors + skipped
                return AssertionResult(
                    passed=passed,
                    failed=failed,
                    errors=errors,
                    skipped=skipped,
                    total=total,
                    raw_output=stdout,
                )

        # Pattern 2: Python unittest "Ran X tests ... FAILED (failures=Y, errors=Z)" or "OK"
        unittest_ran = re.search(r"Ran (\d+) tests?", stdout)
        if unittest_ran:
            total_ran = int(unittest_ran.group(1))
            failures_match = re.search(r"failures=(\d+)", stdout)
            errors_match = re.search(r"errors=(\d+)", stdout)
            skipped_match = re.search(r"skipped=(\d+)", stdout)

            failed = int(failures_match.group(1)) if failures_match else 0
            errors = int(errors_match.group(1)) if errors_match else 0
            skipped = int(skipped_match.group(1)) if skipped_match else 0
            passed = max(0, total_ran - failed - errors - skipped)

            return AssertionResult(
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                total=total_ran,
                raw_output=stdout,
            )

        # Pattern 3: Go test "PASS: TestX" / "FAIL: TestY"
        go_passes = len(re.findall(r"--- PASS: ", stdout))
        go_fails = len(re.findall(r"--- FAIL: ", stdout))
        if go_passes > 0 or go_fails > 0:
            return AssertionResult(
                passed=go_passes,
                failed=go_fails,
                errors=0,
                skipped=0,
                total=go_passes + go_fails,
                raw_output=stdout,
            )

        # Pattern 4: Generic PASS / FAIL count fallback
        gen_pass = len(re.findall(r"\bPASS\b", stdout))
        gen_fail = len(re.findall(r"\bFAIL\b", stdout))
        if gen_pass > 0 or gen_fail > 0:
            return AssertionResult(
                passed=gen_pass,
                failed=gen_fail,
                errors=0,
                skipped=0,
                total=gen_pass + gen_fail,
                raw_output=stdout,
            )

        return AssertionResult(
            passed=0, failed=0, errors=0, skipped=0, total=0, raw_output=stdout
        )

    def calculate_reward(
        self,
        passed_assertions: int,
        turn_count: int = 1,
        prior_turn_count: Optional[int] = None,
        prior_passed: Optional[int] = None,
    ) -> RewardOutput:
        """
        Calculates R = min(1.0, P / S) and applies turn growth sentinel.
        """
        # Base global scaled reward
        raw_reward = min(1.0, max(0.0, float(passed_assertions) / self.scale_s))

        penalty = 1.0
        reason = "Normal evaluation"

        # Sentinel: Check if turns exploded without assertion improvement
        if prior_turn_count is not None and prior_passed is not None:
            turn_delta = turn_count - prior_turn_count
            passed_delta = passed_assertions - prior_passed

            if turn_delta >= self.growth_tolerance and passed_delta <= 0:
                # Excessive exploration without assertion gain: apply harsh penalty
                excess_turns = turn_count - self.optimal_turns
                if excess_turns > 0:
                    penalty = math.exp(-self.beta_penalty * excess_turns)
                    reason = f"Turn growth penalty: +{turn_delta} turns with 0 assertion gain"
        elif turn_count > self.optimal_turns:
            # Trajectory is longer than optimal horizon
            excess_turns = turn_count - self.optimal_turns
            penalty = math.exp(-self.beta_penalty * excess_turns)
            reason = f"Length penalty: {turn_count} turns > {self.optimal_turns} optimal"

        effective_reward = max(0.0, min(1.0, raw_reward * penalty))

        return RewardOutput(
            raw_reward=round(raw_reward, 6),
            effective_reward=round(effective_reward, 6),
            passed_assertions=passed_assertions,
            scale_factor_s=self.scale_s,
            penalty_factor=round(penalty, 6),
            turn_count=turn_count,
            reason=reason,
        )
