#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Lauburu Red/Blue Team Adversarial Arena: Reward Dataset Schemas & Dataset Sinks
Subsystem: 05_agents_and_swarms/red_blue_arena/training/schemas/reward_dataset_schemas.py
Classification: HuggingFace LoRA Training Schemas • Tri-Vault Synchronization • smolagents
==============================================================================
Provides concrete JSONL schemas and resilient file sinks for:
1. Direct Preference Optimization (DPO) Pairwise Records (Prompt, Chosen, Rejected, Metadata).
2. Supervised Fine-Tuning (SFT) Instruction-Thought-Solution Records (Alpaca / ShareGPT format).
3. Group Relative Policy Optimization (GRPO) Step-Wise Trajectory Records.
4. HuggingFace smolagents Multi-Agent Swarm Telemetry & Coordination Metrics.
5. Thread-safe, atomic Dataset Sink Writers for continuous 24/7 LoRA dataset harvesting.
==============================================================================
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Workspace & Dataset Path Resolution
# ---------------------------------------------------------------------------
def resolve_lora_dataset_dir() -> Path:
    """
    Resolves the canonical LoRA dataset directory in the high-throughput data lake.
    Falls back gracefully to local monorepo directory if host volume is unmounted.
    """
    candidates = [
        Path("/Users/aaron/DFS_UNIFIED/lora_datasets"),
        Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_datasets"),
        Path(__file__).resolve().parents[4] / "04_data_and_memory" / "lora_datasets" if len(Path(__file__).resolve().parents) >= 5 else Path.cwd() / "lora_datasets",
        Path.cwd() / "lora_datasets"
    ]
    for c in candidates:
        try:
            c.mkdir(parents=True, exist_ok=True)
            if os.access(c, os.W_OK):
                return c
        except Exception:
            continue
    fallback = Path.cwd() / "lora_datasets"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ---------------------------------------------------------------------------
# 0. HuggingFace smolagents Swarm Telemetry Schema
# ---------------------------------------------------------------------------
@dataclass
class SmolagentsSwarmTelemetry:
    """
    Captures multi-agent swarm coordination telemetry generated via HuggingFace smolagents.
    Tracks dynamic subagent creation, tool execution dispatch, and swarm convergence.
    """
    framework: str = "smolagents"
    swarm_size: int = 1                     # Number of active subagents (e.g. CodeAgent, ToolCallingAgent)
    subagents_deployed: List[str] = field(default_factory=list) # Subagent role names
    tool_calls_executed: int = 0            # Total successful tool calls across swarm
    delegation_depth: int = 1               # Maximum hierarchical agent delegation depth
    parallel_dispatch_count: int = 1        # Parallel branch executions
    coordination_efficiency: float = 1.0    # Ratio of productive to total swarm actions [0.0, 1.0]
    swarm_synthesis_time_s: float = 0.0     # Elapsed time for multi-agent synthesis
    truth_verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "swarm_size": int(self.swarm_size),
            "subagents_deployed": list(self.subagents_deployed),
            "tool_calls_executed": int(self.tool_calls_executed),
            "delegation_depth": int(self.delegation_depth),
            "parallel_dispatch_count": int(self.parallel_dispatch_count),
            "coordination_efficiency": round(float(self.coordination_efficiency), 4),
            "swarm_synthesis_time_s": round(float(self.swarm_synthesis_time_s), 4),
            "truth_verified": bool(self.truth_verified)
        }


# ---------------------------------------------------------------------------
# 1. DPO Pairwise Record Schema
# ---------------------------------------------------------------------------
@dataclass
class DPOPairwiseRecord:
    """
    Direct Preference Optimization pairwise comparison record.
    Used by HuggingFace trl.DPOTrainer with SFT regularization anchor (gamma * L_SFT).
    """
    id: str
    timestamp_utc: str
    domain: str
    task_type: str
    prompt: str
    chosen: str
    rejected: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    swarm_telemetry: Optional[SmolagentsSwarmTelemetry] = None

    def validate(self) -> bool:
        """Validates that prompt, chosen, and rejected strings are non-empty and non-identical."""
        if not self.id or not isinstance(self.id, str):
            raise ValueError("DPO record 'id' must be a non-empty string.")
        if not self.prompt or not isinstance(self.prompt, str):
            raise ValueError("DPO record 'prompt' must be a non-empty string.")
        if not self.chosen or not isinstance(self.chosen, str):
            raise ValueError("DPO record 'chosen' must be a non-empty string.")
        if not self.rejected or not isinstance(self.rejected, str):
            raise ValueError("DPO record 'rejected' must be a non-empty string.")
        if self.chosen.strip() == self.rejected.strip():
            raise ValueError("DPO record 'chosen' and 'rejected' completions cannot be identical.")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serializes record to standard dictionary format."""
        self.validate()
        meta = dict(self.metadata)
        if self.swarm_telemetry is not None:
            meta["smolagents_swarm_telemetry"] = self.swarm_telemetry.to_dict()
        return {
            "id": self.id,
            "timestamp_utc": self.timestamp_utc,
            "domain": self.domain,
            "task_type": self.task_type,
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "metadata": meta
        }

    def to_json(self) -> str:
        """Serializes to single-line JSON string for JSONL sinks."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 2. SFT Instruction-Thought-Solution Record Schema
# ---------------------------------------------------------------------------
@dataclass
class SFTTrainingRecord:
    """
    Supervised Fine-Tuning record supporting both Alpaca and ShareGPT conventions.
    Embeds step-by-step reasoning thought chains before final patch solutions.
    """
    instruction: str
    input: str
    thought: str
    output: str
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    swarm_telemetry: Optional[SmolagentsSwarmTelemetry] = None

    def validate(self) -> bool:
        """Validates SFT structure."""
        if not self.instruction or not isinstance(self.instruction, str):
            raise ValueError("SFT 'instruction' must be a non-empty string.")
        if not self.output or not isinstance(self.output, str):
            raise ValueError("SFT 'output' must be a non-empty string.")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Returns standard Alpaca instruction-input-thought-output dictionary."""
        self.validate()
        meta = dict(self.metadata)
        if self.swarm_telemetry is not None:
            meta["smolagents_swarm_telemetry"] = self.swarm_telemetry.to_dict()
        d: Dict[str, Any] = {
            "instruction": self.instruction,
            "input": self.input,
            "thought": self.thought,
            "output": self.output,
            "timestamp": self.timestamp
        }
        if meta:
            d["metadata"] = meta
        return d

    def to_sharegpt_format(self) -> Dict[str, Any]:
        """Converts to conversational ShareGPT multi-turn format."""
        self.validate()
        meta = dict(self.metadata)
        if self.swarm_telemetry is not None:
            meta["smolagents_swarm_telemetry"] = self.swarm_telemetry.to_dict()
        user_content = f"{self.instruction}\n\nInput Context:\n{self.input}" if self.input else self.instruction
        assistant_content = f"<thought>\n{self.thought}\n</thought>\n{self.output}" if self.thought else self.output
        return {
            "conversations": [
                {"from": "human", "value": user_content},
                {"from": "gpt", "value": assistant_content}
            ],
            "timestamp": self.timestamp,
            "metadata": meta
        }

    def to_json(self) -> str:
        """Serializes to single-line JSON string for JSONL sinks."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 3. GRPO Step-Wise Trajectory Schema
# ---------------------------------------------------------------------------
@dataclass
class GRPOStep:
    """Individual action step in an agentic RL trajectory."""
    step_idx: int
    agent_role: str
    state_observation: str
    action_taken: str
    intermediate_reward: float
    rule_zero_verified: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_idx": self.step_idx,
            "agent_role": self.agent_role,
            "state_observation": self.state_observation,
            "action_taken": self.action_taken,
            "intermediate_reward": round(float(self.intermediate_reward), 4),
            "rule_zero_verified": bool(self.rule_zero_verified),
            "metadata": self.metadata
        }


@dataclass
class GRPOTrajectoryRecord:
    """
    Complete multi-step trajectory record for Group Relative Policy Optimization.
    Tracks sequential state transitions, observations, actions, and cumulative rewards.
    """
    trajectory_id: str
    timestamp_utc: str
    environment: str
    total_reward: float
    steps: List[GRPOStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    swarm_telemetry: Optional[SmolagentsSwarmTelemetry] = None

    def validate(self) -> bool:
        if not self.trajectory_id:
            raise ValueError("GRPO record 'trajectory_id' must be provided.")
        if not self.steps:
            raise ValueError("GRPO record 'steps' list cannot be empty.")
        return True

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        meta = dict(self.metadata)
        if self.swarm_telemetry is not None:
            meta["smolagents_swarm_telemetry"] = self.swarm_telemetry.to_dict()
        return {
            "trajectory_id": self.trajectory_id,
            "timestamp_utc": self.timestamp_utc,
            "environment": self.environment,
            "total_reward": round(float(self.total_reward), 4),
            "steps": [s.to_dict() for s in self.steps],
            "metadata": meta
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 3. Ancestral Tool Memory Schema
# ---------------------------------------------------------------------------
@dataclass
class AncestralToolMemoryRecord:
    """
    Ancestral Tool Memory Record.
    Captures evolutionary tool upgrades, successful probe AST traces, and tool version lineages
    across generations of ephemeral smolagents.
    """
    tool_id: str
    generation: int
    tool_name: str
    timestamp_utc: str
    code_content: str
    target_subsystem: str
    discovered_vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    success_rate: float = 1.0
    evolution_metadata: Dict[str, Any] = field(default_factory=dict)
    truth_verified: bool = True

    def validate(self) -> bool:
        if not self.tool_id:
            raise ValueError("AncestralToolMemoryRecord requires a valid 'tool_id'.")
        if not self.tool_name:
            raise ValueError("AncestralToolMemoryRecord requires a valid 'tool_name'.")
        return True

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "tool_id": self.tool_id,
            "generation": int(self.generation),
            "tool_name": self.tool_name,
            "timestamp_utc": self.timestamp_utc,
            "code_content": self.code_content,
            "target_subsystem": self.target_subsystem,
            "discovered_vulnerabilities": list(self.discovered_vulnerabilities),
            "success_rate": round(float(self.success_rate), 4),
            "evolution_metadata": dict(self.evolution_metadata),
            "truth_verified": bool(self.truth_verified)
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 4. Multi-Sink Dataset Writer (LoRADatasetSink)
# ---------------------------------------------------------------------------
class LoRADatasetSink:
    """
    Thread-safe, atomic file writer for continuous 24/7 LoRA dataset harvesting.
    Writes structured JSONL entries to the canonical data lake with Rule #0 truth gates.
    """

    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        self.base_dir = Path(base_dir) if base_dir else resolve_lora_dataset_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Canonical dataset targets
        self.dpo_security_path = self.base_dir / "code_audit_security_training.jsonl"
        self.sft_debate_path = self.base_dir / "truth_audit_debate.jsonl"
        self.grpo_trajectory_path = self.base_dir / "grpo_adversarial_trajectories.jsonl"
        self.arena_history_path = self.base_dir / "continuous_master_agi_distillation.jsonl"
        self.ancestral_tool_memory_path = self.base_dir / "ancestral_tool_memory.jsonl"

    def append_dpo_record(self, record: DPOPairwiseRecord, target_file: Optional[Path] = None) -> bool:
        """
        Appends a verified DPO record to the target JSONL sink.
        Enforces Rule #0: Rejects writes if truth_verified is False in metadata.
        """
        if record.metadata.get("truth_verified") is False:
            raise ValueError("Rule #0 Violation: Cannot append DPO record with falsified/unverified truth status.")

        record.validate()
        dest = target_file if target_file else self.dpo_security_path
        return self._safe_append_line(dest, record.to_json())

    def append_sft_record(self, record: SFTTrainingRecord, target_file: Optional[Path] = None) -> bool:
        """
        Appends a verified SFT record to truth_audit_debate.jsonl.
        Enforces Rule #0: Rejects writes if truth_verified is explicitly False.
        """
        if record.metadata.get("truth_verified") is False:
            raise ValueError("Rule #0 Violation: Cannot append SFT record with falsified truth status.")

        record.validate()
        dest = target_file if target_file else self.sft_debate_path
        return self._safe_append_line(dest, record.to_json())

    def append_ancestral_tool_record(self, record: AncestralToolMemoryRecord, target_file: Optional[Path] = None) -> bool:
        """
        Appends an ancestral tool memory record to ancestral_tool_memory.jsonl.
        """
        if record.truth_verified is False:
            raise ValueError("Rule #0 Violation: Cannot append ancestral tool record with unverified truth status.")
        record.validate()
        dest = target_file if target_file else self.ancestral_tool_memory_path
        return self._safe_append_line(dest, record.to_json())

    def append_grpo_record(self, record: GRPOTrajectoryRecord, target_file: Optional[Path] = None) -> bool:
        """
        Appends a verified multi-step GRPO trajectory to grpo_adversarial_trajectories.jsonl.
        """
        if record.metadata.get("truth_verified") is False:
            raise ValueError("Rule #0 Violation: Cannot append GRPO trajectory with unverified truth status.")

        record.validate()
        dest = target_file if target_file else self.grpo_trajectory_path
        return self._safe_append_line(dest, record.to_json())

    def _safe_append_line(self, filepath: Path, json_line: str) -> bool:
        """Thread-safe append with fsync to guarantee disk persistence."""
        with self._lock:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json_line.strip() + "\n")
                f.flush()
                os.fsync(f.fileno())
            return True

    def count_records(self, filepath: Optional[Path] = None) -> int:
        """Counts total non-empty JSON lines in a dataset sink."""
        target = filepath if filepath else self.sft_debate_path
        if not target.exists():
            return 0
        count = 0
        with open(target, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
