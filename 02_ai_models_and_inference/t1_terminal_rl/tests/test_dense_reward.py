"""
test_dense_reward.py - Test Suite for Dense Verification Reward (S=20) & Turn Growth Sentinel.

Verifies:
1. Mathematical scaling R = min(1.0, P / 20) against edge cases (0, 10, 20, 35 passed).
2. Contrast between relative pass ratio (P/T) vs. fixed global scale (P/20).
3. Test output parsing across realistic pytest, unittest, and go test formats.
4. Anti-reward-hacking turn growth sentinel penalties.
"""

import pytest
from pathlib import Path
import sys

PKG_DIR = Path(__file__).resolve().parents[2]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from t1_terminal_rl.dense_verification_reward import (
    DenseVerificationRewardCalculator,
    AssertionResult,
    RewardOutput,
)


def test_dense_reward_scaling_s20():
    calc = DenseVerificationRewardCalculator(scale_s=20)

    # 0 passed -> 0.0
    r0 = calc.calculate_reward(passed_assertions=0)
    assert r0.raw_reward == 0.0
    assert r0.effective_reward == 0.0

    # 10 passed out of S=20 -> 0.50
    r10 = calc.calculate_reward(passed_assertions=10)
    assert r10.raw_reward == 0.50
    assert r10.effective_reward == 0.50

    # 18 passed out of S=20 -> 0.90
    r18 = calc.calculate_reward(passed_assertions=18)
    assert r18.raw_reward == 0.90
    assert r18.effective_reward == 0.90

    # 20 passed out of S=20 -> 1.00
    r20 = calc.calculate_reward(passed_assertions=20)
    assert r20.raw_reward == 1.00
    assert r20.effective_reward == 1.00

    # 35 passed out of S=20 -> clamped to 1.00
    r35 = calc.calculate_reward(passed_assertions=35)
    assert r35.raw_reward == 1.00
    assert r35.effective_reward == 1.00


def test_relative_ratio_vs_fixed_scale_contrast():
    """
    Demonstrates why T1 rejects relative pass ratios P/T:
    Trivial task (2/2) vs Hard task (18/20).
    """
    calc = DenseVerificationRewardCalculator(scale_s=20)

    # Trivial task: 2/2 assertions passed
    p_trivial, total_trivial = 2, 2
    relative_trivial = p_trivial / total_trivial  # 1.00
    t1_trivial = calc.calculate_reward(p_trivial).raw_reward  # 0.10

    # Hard task: 18/20 assertions passed
    p_hard, total_hard = 18, 20
    relative_hard = p_hard / total_hard  # 0.90
    t1_hard = calc.calculate_reward(p_hard).raw_reward  # 0.90

    # Under relative ratio: trivial task gets higher reward (1.0 > 0.90) - DILUTION ERROR
    assert relative_trivial > relative_hard

    # Under T1 S=20 fixed scale: hard task gets 9x the reward (0.90 vs 0.10) - CORRECT
    assert t1_hard > t1_trivial
    assert t1_hard == pytest.approx(9.0 * t1_trivial)


def test_pytest_output_parser():
    calc = DenseVerificationRewardCalculator(scale_s=20)

    pytest_out = """
============================= test session starts ==============================
collected 21 items

tests/test_core.py .................F.                                  [100%]

=================================== FAILURES ===================================
_________________________________ test_timeout _________________________________
AssertionError: timeout exceeded
=========================== short test summary info ============================
FAILED tests/test_core.py::test_timeout - AssertionError: timeout exceeded
=================== 18 passed, 2 failed, 1 error in 3.42s =====================
"""
    parsed = calc.parse_terminal_test_output(pytest_out)
    assert parsed.passed == 18
    assert parsed.failed == 2
    assert parsed.errors == 1
    assert parsed.total == 21

    reward = calc.calculate_reward(parsed.passed)
    assert reward.raw_reward == 0.90


def test_unittest_output_parser():
    calc = DenseVerificationRewardCalculator(scale_s=20)

    unittest_out = """
Ran 12 tests in 0.045s

FAILED (failures=2, errors=1)
"""
    parsed = calc.parse_terminal_test_output(unittest_out)
    assert parsed.passed == 9
    assert parsed.failed == 2
    assert parsed.errors == 1
    assert parsed.total == 12

    reward = calc.calculate_reward(parsed.passed)
    assert reward.raw_reward == 0.45


def test_turn_growth_sentinel_penalty():
    calc = DenseVerificationRewardCalculator(
        scale_s=20,
        optimal_turns=10,
        beta_penalty=0.05,
        growth_tolerance=3,
    )

    # Normal turn count <= optimal_turns: no penalty
    normal = calc.calculate_reward(passed_assertions=16, turn_count=8)
    assert normal.raw_reward == 0.80
    assert normal.effective_reward == 0.80
    assert normal.penalty_factor == 1.0

    # Excessive turn expansion without assertion gain:
    # Jump from turn 10 to turn 16 (+6 turns) while passed assertions remain 12
    stalled = calc.calculate_reward(
        passed_assertions=12,
        turn_count=16,
        prior_turn_count=10,
        prior_passed=12,
    )
    assert stalled.raw_reward == 0.60
    assert stalled.penalty_factor < 1.0
    assert stalled.effective_reward < stalled.raw_reward
    assert "Turn growth penalty" in stalled.reason
