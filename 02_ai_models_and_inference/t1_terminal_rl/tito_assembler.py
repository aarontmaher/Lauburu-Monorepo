"""
tito_assembler.py - Token-In, Token-Out (TITO) Multi-Turn Trajectory Assembler.

Implements the clean-room specification of T1 Terminal Agent RL for multi-turn
terminal trajectories, eliminating template and tokenization drift over long horizons
(50-300 turns). Action tokens are preserved verbatim with exact loss masking (m_j=1)
and 3-tier boundary repair.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


class TurnType(str, Enum):
    PROMPT = "prompt"
    OBSERVATION = "observation"
    ACTION = "action"
    SYSTEM = "system"


@dataclass
class TurnSegment:
    turn_index: int
    turn_type: TurnType
    token_ids: List[int]
    text: str = ""
    loss_mask: List[int] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0

    def __post_init__(self):
        if not self.loss_mask:
            # Action tokens receive loss_mask=1, all other tokens receive loss_mask=0
            mask_val = 1 if self.turn_type == TurnType.ACTION else 0
            self.loss_mask = [mask_val] * len(self.token_ids)
        elif len(self.loss_mask) != len(self.token_ids):
            raise ValueError(
                f"loss_mask length ({len(self.loss_mask)}) must match token_ids length ({len(self.token_ids)})"
            )


@dataclass
class TITOTrajectory:
    task_id: str
    segments: List[TurnSegment] = field(default_factory=list)
    full_token_ids: List[int] = field(default_factory=list)
    full_loss_mask: List[int] = field(default_factory=list)
    r3_cache: Optional[Dict[str, Any]] = None
    reward: float = 0.0
    effective_reward: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return len(self.full_token_ids)

    @property
    def action_tokens(self) -> int:
        return sum(self.full_loss_mask)

    @property
    def turn_count(self) -> int:
        return len([s for s in self.segments if s.turn_type == TurnType.ACTION])

    @property
    def loss_mask_ratio(self) -> float:
        if not self.full_token_ids:
            return 0.0
        return self.action_tokens / self.total_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "total_tokens": self.total_tokens,
            "action_tokens": self.action_tokens,
            "turn_count": self.turn_count,
            "token_ids": self.full_token_ids,
            "loss_mask": self.full_loss_mask,
            "turn_offsets": [
                {
                    "turn": s.turn_index,
                    "type": s.turn_type.value,
                    "start_idx": s.start_offset,
                    "end_idx": s.end_offset,
                    "token_count": len(s.token_ids),
                }
                for s in self.segments
            ],
            "r3_cache": self.r3_cache,
            "reward": self.reward,
            "effective_reward": self.effective_reward,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TITOTrajectory:
        token_ids = data.get("token_ids", [])
        loss_mask = data.get("loss_mask", [])
        offsets = data.get("turn_offsets", [])
        segments: List[TurnSegment] = []

        for offset in offsets:
            s_idx = offset["start_idx"]
            e_idx = offset["end_idx"]
            t_type = TurnType(offset["type"])
            sub_ids = token_ids[s_idx:e_idx]
            sub_mask = loss_mask[s_idx:e_idx]
            segments.append(
                TurnSegment(
                    turn_index=offset["turn"],
                    turn_type=t_type,
                    token_ids=sub_ids,
                    loss_mask=sub_mask,
                    start_offset=s_idx,
                    end_offset=e_idx,
                )
            )

        return cls(
            task_id=data.get("task_id", "unknown"),
            segments=segments,
            full_token_ids=token_ids,
            full_loss_mask=loss_mask,
            r3_cache=data.get("r3_cache"),
            reward=float(data.get("reward", 0.0)),
            effective_reward=float(data.get("effective_reward", data.get("reward", 0.0))),
            metadata=data.get("metadata", {}),
        )


class TITOAssembler:
    """
    Assembles multi-turn terminal trajectories using exact token stitching and
    executes 3-tier boundary repair to prevent template re-tokenization drift.
    """

    def __init__(
        self,
        action_start_delimiter: str = "<|im_start|>assistant\n<action>\n",
        action_end_delimiter: str = "</action><|im_end|>",
        tokenizer: Optional[Any] = None,
    ):
        self.action_start_delimiter = action_start_delimiter
        self.action_end_delimiter = action_end_delimiter
        self.tokenizer = tokenizer

    def assemble_from_turns(
        self,
        task_id: str,
        turns: List[Dict[str, Any]],
        r3_cache: Optional[Dict[str, Any]] = None,
        reward: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TITOTrajectory:
        """
        Builds a TITOTrajectory from discrete turn dictionaries.
        Each turn dict format:
        {
            "turn_index": int,
            "type": "prompt" | "observation" | "action" | "system",
            "token_ids": List[int],
            "text": Optional[str]
        }
        """
        full_tokens: List[int] = []
        full_masks: List[int] = []
        segments: List[TurnSegment] = []

        current_offset = 0
        for turn_data in turns:
            t_type = TurnType(turn_data["type"])
            t_ids = list(turn_data["token_ids"])
            t_text = turn_data.get("text", "")
            t_idx = turn_data.get("turn_index", len(segments) + 1)

            start = current_offset
            end = current_offset + len(t_ids)
            segment = TurnSegment(
                turn_index=t_idx,
                turn_type=t_type,
                token_ids=t_ids,
                text=t_text,
                start_offset=start,
                end_offset=end,
            )
            segments.append(segment)
            full_tokens.extend(segment.token_ids)
            full_masks.extend(segment.loss_mask)
            current_offset = end

        return TITOTrajectory(
            task_id=task_id,
            segments=segments,
            full_token_ids=full_tokens,
            full_loss_mask=full_masks,
            r3_cache=r3_cache,
            reward=reward,
            effective_reward=reward,
            metadata=metadata or {},
        )

    def repair_boundaries(
        self,
        concatenated_tokens: List[int],
        action_specs: List[Dict[str, Any]],
        detokenizer_fn: Optional[Any] = None,
    ) -> Tuple[List[int], float]:
        """
        Executes 3-Tier Boundary Repair on an arbitrarily packed token stream.
        
        action_specs: list of dicts with:
          - "raw_action_ids": List[int] (Tier 1)
          - "start_anchor_ids": Optional[List[int]] (Tier 2)
          - "end_anchor_ids": Optional[List[int]] (Tier 2)
          - "char_span": Optional[Tuple[int, int]] (Tier 3)

        Returns:
          (loss_mask: List[int], drift_rate: float)
        """
        loss_mask = [0] * len(concatenated_tokens)
        total_target_action_tokens = sum(len(spec["raw_action_ids"]) for spec in action_specs)
        drift_tokens = 0
        search_start = 0

        for spec in action_specs:
            raw_ids = spec["raw_action_ids"]
            action_len = len(raw_ids)
            matched = False

            # Tier 1: Exact Subsequence Match
            for i in range(search_start, len(concatenated_tokens) - action_len + 1):
                if concatenated_tokens[i : i + action_len] == raw_ids:
                    for k in range(i, i + action_len):
                        loss_mask[k] = 1
                    search_start = i + action_len
                    matched = True
                    break

            if matched:
                continue

            # Tier 2: Template Anchor Suffix Match
            start_anchors = spec.get("start_anchor_ids")
            end_anchors = spec.get("end_anchor_ids")
            if start_anchors and end_anchors:
                s_len = len(start_anchors)
                e_len = len(end_anchors)
                found_s = -1
                found_e = -1

                for i in range(search_start, len(concatenated_tokens) - s_len + 1):
                    if concatenated_tokens[i : i + s_len] == start_anchors:
                        found_s = i + s_len
                        break

                if found_s != -1:
                    for j in range(found_s, len(concatenated_tokens) - e_len + 1):
                        if concatenated_tokens[j : j + e_len] == end_anchors:
                            found_e = j
                            break

                if found_s != -1 and found_e != -1 and found_e > found_s:
                    for k in range(found_s, found_e):
                        loss_mask[k] = 1
                    search_start = found_e + e_len
                    matched = True
                    # Check token count difference vs raw
                    token_diff = abs((found_e - found_s) - action_len)
                    drift_tokens += token_diff
                    continue

            # Tier 3: Fallback Character Span Alignment
            if detokenizer_fn and "char_span" in spec:
                # Map character spans back to token indices
                char_start, char_end = spec["char_span"]
                detok_text = detokenizer_fn(concatenated_tokens)
                if char_end <= len(detok_text):
                    # Detokenize prefix incrementally to pinpoint token boundary
                    acc_chars = 0
                    t_start = -1
                    t_end = -1
                    for idx, tok in enumerate(concatenated_tokens):
                        t_str = detokenizer_fn([tok])
                        next_acc = acc_chars + len(t_str)
                        if t_start == -1 and next_acc > char_start:
                            t_start = idx
                        if t_end == -1 and next_acc >= char_end:
                            t_end = idx + 1
                            break
                        acc_chars = next_acc

                    if t_start != -1 and t_end != -1 and t_end > t_start:
                        for k in range(t_start, t_end):
                            loss_mask[k] = 1
                        search_start = t_end
                        matched = True
                        drift_tokens += abs((t_end - t_start) - action_len)
                        continue

            # Unmatched segment counts as complete drift
            if not matched:
                drift_tokens += action_len

        drift_rate = (drift_tokens / total_target_action_tokens) if total_target_action_tokens > 0 else 0.0
        return loss_mask, drift_rate

    def verify_loss_region_drift(
        self,
        trajectory: TITOTrajectory,
        ground_truth_actions: List[List[int]],
    ) -> float:
        """
        Computes the exact drift percentage between trajectory action masks and ground-truth tokens.
        A return value of 0.0000 indicates 0.0000% drift.
        """
        extracted_action_tokens: List[int] = []
        for tok, mask in zip(trajectory.full_token_ids, trajectory.full_loss_mask):
            if mask == 1:
                extracted_action_tokens.append(tok)

        expected_action_tokens: List[int] = []
        for gt in ground_truth_actions:
            expected_action_tokens.extend(gt)

        if not expected_action_tokens:
            return 0.0 if not extracted_action_tokens else 1.0

        if extracted_action_tokens == expected_action_tokens:
            return 0.0000

        # Calculate mismatch count
        mismatches = sum(
            1 for a, b in zip(extracted_action_tokens, expected_action_tokens) if a != b
        ) + abs(len(extracted_action_tokens) - len(expected_action_tokens))

        return float(mismatches) / len(expected_action_tokens)
