"""
test_tito_assembler.py - Test Suite for Token-In, Token-Out (TITO) Assembler.

Verifies:
1. 50+ turn trajectory assembly with exactly 0.0000% loss-region token drift.
2. Exact action token loss masking (m_j = 1 for actions, m_j = 0 for observations/prompts).
3. 3-Tier boundary repair across exact slices, template delimiters, and character spans.
4. Loss mask ratio and serialization/deserialization integrity.
"""

import json
import pytest
from pathlib import Path
import sys

# Add parent directory to path
PKG_DIR = Path(__file__).resolve().parents[2]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from t1_terminal_rl.tito_assembler import (
    TurnType,
    TurnSegment,
    TITOTrajectory,
    TITOAssembler,
)


def test_tito_segment_masking():
    # Observation segment: mask must be 0
    obs_seg = TurnSegment(
        turn_index=1,
        turn_type=TurnType.OBSERVATION,
        token_ids=[101, 102, 103],
        text="ls -la output",
    )
    assert obs_seg.loss_mask == [0, 0, 0]

    # Action segment: mask must be 1
    act_seg = TurnSegment(
        turn_index=1,
        turn_type=TurnType.ACTION,
        token_ids=[201, 202, 203, 204],
        text="cat file.txt",
    )
    assert act_seg.loss_mask == [1, 1, 1, 1]


def test_tito_50_turn_assembly_zero_drift():
    assembler = TITOAssembler()
    turns = []
    ground_truth_actions = []

    # Assemble a realistic 50-turn trajectory (1 prompt, 50 observation-action pairs)
    turns.append({
        "turn_index": 0,
        "type": "prompt",
        "token_ids": [151644, 872, 198, 500, 501, 502],
        "text": "Task: Fix failing test in test_engine.py",
    })

    current_tok = 1000
    for t in range(1, 51):
        # Observation turn
        obs_tokens = [current_tok + i for i in range(10)]
        current_tok += 10
        turns.append({
            "turn_index": t,
            "type": "observation",
            "token_ids": obs_tokens,
            "text": f"terminal output step {t}",
        })

        # Action turn
        act_tokens = [current_tok + i for i in range(8)]
        current_tok += 8
        turns.append({
            "turn_index": t,
            "type": "action",
            "token_ids": act_tokens,
            "text": f"command execution step {t}",
        })
        ground_truth_actions.append(act_tokens)

    traj = assembler.assemble_from_turns(
        task_id="swe_bench_task_verify_50_turns",
        turns=turns,
        reward=0.85,
    )

    # Assertions on trajectory metrics
    assert traj.task_id == "swe_bench_task_verify_50_turns"
    assert traj.turn_count == 50
    assert traj.action_tokens == 50 * 8  # 400 action tokens
    assert traj.total_tokens == 6 + (50 * 10) + (50 * 8)  # 906 total tokens

    # Mathematical drift verification (Target: 0.0000% drift)
    drift = assembler.verify_loss_region_drift(traj, ground_truth_actions)
    assert drift == 0.0000, f"Expected 0.0000% drift, got {drift}"

    # Verify loss mask alignment
    action_token_sum = sum(traj.full_loss_mask)
    assert action_token_sum == traj.action_tokens


def test_tito_3_tier_boundary_repair():
    assembler = TITOAssembler()

    # Tier 1: Exact slice match
    full_tokens = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    specs = [
        {"raw_action_ids": [40, 50, 60]},
        {"raw_action_ids": [80, 90]},
    ]
    mask, drift = assembler.repair_boundaries(full_tokens, specs)
    assert drift == 0.0
    assert mask == [0, 0, 0, 1, 1, 1, 0, 1, 1, 0]

    # Tier 2: Template delimiter anchor match
    # Delimiters: start=[999, 998], end=[777, 776]
    drifted_tokens = [1, 2, 999, 998, 55, 56, 57, 777, 776, 3, 4]
    spec_tier2 = [
        {
            "raw_action_ids": [55, 56, 57],
            "start_anchor_ids": [999, 998],
            "end_anchor_ids": [777, 776],
        }
    ]
    mask2, drift2 = assembler.repair_boundaries(drifted_tokens, spec_tier2)
    assert drift2 == 0.0
    # tokens 55, 56, 57 are at indices 4, 5, 6
    assert mask2 == [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0]

    # Tier 3: Detokenizer character span alignment
    detok_dict = {100: "python ", 101: "-m ", 102: "pytest ", 103: "-v"}
    def mock_detok(ids):
        return "".join(detok_dict.get(i, f"tok{i}") for i in ids)

    token_stream = [500, 100, 101, 102, 103, 600]
    # In mock_detok: "tok500python -m pytest -vtok600"
    # char span for "python -m pytest -v" is (6, 26)
    full_str = mock_detok(token_stream)
    start_c = full_str.find("python ")
    end_c = start_c + len("python -m pytest -v")

    spec_tier3 = [
        {
            "raw_action_ids": [9999],  # Intentional mismatched raw IDs to force Tier 3
            "char_span": (start_c, end_c),
        }
    ]
    mask3, drift3 = assembler.repair_boundaries(token_stream, spec_tier3, detokenizer_fn=mock_detok)
    # Tokens 100, 101, 102, 103 at indices 1, 2, 3, 4 should be marked
    assert mask3 == [0, 1, 1, 1, 1, 0]


def test_tito_serialization_roundtrip():
    assembler = TITOAssembler()
    turns = [
        {"turn_index": 0, "type": "prompt", "token_ids": [1, 2, 3], "text": "init"},
        {"turn_index": 1, "type": "observation", "token_ids": [4, 5], "text": "obs"},
        {"turn_index": 1, "type": "action", "token_ids": [6, 7, 8], "text": "act"},
    ]
    traj = assembler.assemble_from_turns("roundtrip_test", turns, reward=0.75)

    data = traj.to_dict()
    # Serialize to JSON string and back
    json_str = json.dumps(data)
    loaded_data = json.loads(json_str)
    restored = TITOTrajectory.from_dict(loaded_data)

    assert restored.task_id == traj.task_id
    assert restored.full_token_ids == traj.full_token_ids
    assert restored.full_loss_mask == traj.full_loss_mask
    assert restored.action_tokens == traj.action_tokens
    assert restored.turn_count == traj.turn_count
    assert restored.reward == traj.reward
