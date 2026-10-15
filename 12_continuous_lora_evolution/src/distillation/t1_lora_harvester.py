"""
t1_lora_harvester.py - Continuous LoRA Harvester for T1 Terminal RL Trajectories.

Harvests high-reward T1 terminal trajectories (R >= 0.50), formats them into
supervised fine-tuning (SFT) and Direct Preference Optimization (DPO) training pairs,
and synchronously streams them to the canonical Tri-Vault dataset destination:
/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl.
"""

from __future__ import annotations

import fcntl
import importlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Support importing t1_terminal_rl dynamically to handle directory names starting with digits
MONOREPO_ROOT = Path(__file__).resolve().parents[3]
t1_pkg_dir = MONOREPO_ROOT / "02_ai_models_and_inference"
if str(t1_pkg_dir) not in sys.path:
    sys.path.insert(0, str(t1_pkg_dir))

from t1_terminal_rl.tito_assembler import TITOTrajectory, TurnType

CANONICAL_LORA_PATH = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")


@dataclass
class HarvestSummary:
    trajectories_evaluated: int
    trajectories_accepted: int
    sft_pairs_generated: int
    dpo_pairs_generated: int
    total_action_tokens: int
    output_path: str
    elapsed_seconds: float


class T1LoRAHarvester:
    """
    Harvests verified T1 trajectories and synchronizes them into continuous LoRA datasets.
    """

    def __init__(
        self,
        output_dataset_path: Path = CANONICAL_LORA_PATH,
        min_reward_threshold: float = 0.50,
        model_family: str = "qwen",
    ):
        self.output_path = Path(output_dataset_path)
        self.min_reward_threshold = min_reward_threshold
        self.model_family = model_family
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def trajectory_to_sft_sample(self, traj: TITOTrajectory) -> Optional[Dict[str, Any]]:
        """
        Converts a TITO trajectory to multi-turn conversational SFT format.
        """
        if traj.effective_reward < self.min_reward_threshold:
            return None

        messages: List[Dict[str, str]] = []
        for seg in traj.segments:
            role = "user" if seg.turn_type in (TurnType.PROMPT, TurnType.OBSERVATION) else "assistant"
            # If previous message has same role, concatenate
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"] += f"\n{seg.text}"
            else:
                messages.append({"role": role, "content": seg.text})

        if len(messages) < 2:
            return None

        return {
            "source": "t1_terminal_rl",
            "task_id": traj.task_id,
            "reward": traj.reward,
            "effective_reward": traj.effective_reward,
            "action_tokens": traj.action_tokens,
            "total_tokens": traj.total_tokens,
            "messages": messages,
            "timestamp": time.time(),
        }

    def pair_to_dpo_sample(
        self,
        chosen: TITOTrajectory,
        rejected: TITOTrajectory,
    ) -> Optional[Dict[str, Any]]:
        """
        Builds a DPO pair from a high-reward chosen trajectory and lower-reward rejected trajectory.
        """
        if chosen.effective_reward <= rejected.effective_reward:
            return None
        if chosen.effective_reward < self.min_reward_threshold:
            return None

        # Build prompt from first turn
        prompt_text = chosen.segments[0].text if chosen.segments else ""
        chosen_actions = "\n".join([s.text for s in chosen.segments if s.turn_type == TurnType.ACTION])
        rejected_actions = "\n".join([s.text for s in rejected.segments if s.turn_type == TurnType.ACTION])

        return {
            "source": "t1_terminal_rl_dpo",
            "task_id": chosen.task_id,
            "prompt": prompt_text,
            "chosen": chosen_actions,
            "rejected": rejected_actions,
            "chosen_reward": chosen.effective_reward,
            "rejected_reward": rejected.effective_reward,
            "margin": round(chosen.effective_reward - rejected.effective_reward, 4),
            "timestamp": time.time(),
        }

    def stream_to_dataset(self, records: List[Dict[str, Any]]) -> int:
        """
        Thread-safe file locking write to continuous_lora_dataset.jsonl.
        """
        if not records:
            return 0

        written_count = 0
        with open(self.output_path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    written_count += 1
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

        return written_count

    def harvest_batch(
        self,
        trajectories: List[TITOTrajectory],
    ) -> HarvestSummary:
        start_t = time.time()
        accepted_trajs: List[TITOTrajectory] = []
        sft_records: List[Dict[str, Any]] = []
        total_action_toks = 0

        for traj in trajectories:
            if traj.effective_reward >= self.min_reward_threshold:
                accepted_trajs.append(traj)
                sft_rec = self.trajectory_to_sft_sample(traj)
                if sft_rec:
                    sft_records.append(sft_rec)
                total_action_toks += traj.action_tokens

        # Generate DPO pairs between high-reward and low-reward trajectories
        dpo_records: List[Dict[str, Any]] = []
        for chosen in accepted_trajs:
            for other in trajectories:
                if other.effective_reward < self.min_reward_threshold and other.task_id == chosen.task_id:
                    dpo_rec = self.pair_to_dpo_sample(chosen, other)
                    if dpo_rec:
                        dpo_records.append(dpo_rec)

        all_records = sft_records + dpo_records
        written = self.stream_to_dataset(all_records)

        return HarvestSummary(
            trajectories_evaluated=len(trajectories),
            trajectories_accepted=len(accepted_trajs),
            sft_pairs_generated=len(sft_records),
            dpo_pairs_generated=len(dpo_records),
            total_action_tokens=total_action_toks,
            output_path=str(self.output_path),
            elapsed_seconds=round(time.time() - start_t, 4),
        )
