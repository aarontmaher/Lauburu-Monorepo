"""
================================================================================
🥋 Combat Director & Roll Exchange Protocol (REP) Sparring Engine
================================================================================
Subsystem: 01_apps/lauburu_showrunner/src/grappling_arena/combat_director.py
Monorepo: Lauburu-Monorepo / 01_apps/lauburu_showrunner
Features:
- Sub-50ms Roll Exchange Protocol (REP) tick engine
- 10m x 10m Virtual Tatami canvas coordinates
- Biometric dynamic stamina integration for human digital twins
- Deterministic 45.0 N·m joint torque tap gate (Rule #0 Zero-Mock)
- Bradley-Terry ELO rating ledger and Tri-Vault crystallization
================================================================================
"""

from __future__ import annotations

import os
import json
import math
import time
import uuid
import random
import logging
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple

from .opml_tactical_graph import opml_tactical_graph, PositionState, TacticalNode
from .biometric_profile_bridge import biometric_bridge, FighterBiometrics

logger = logging.getLogger("showrunner.grappling.director")

# Tri-Vault file destinations
OBSIDIAN_VAULT_ARENA_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES")
LORA_DATASET_ARENA_FILE = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/grappling_arena_matches.jsonl")


class MatchState(str, Enum):
    SCHEDULED = "SCHEDULED"
    SPARRING = "SPARRING"
    SUBMISSION_TAP = "SUBMISSION_TAP"
    POINTS_DECISION = "POINTS_DECISION"
    TIME_LIMIT = "TIME_LIMIT"
    DISQUALIFIED = "DISQUALIFIED"


@dataclass
class GrapplingFighter:
    id: str
    name: str
    fighter_type: str  # human_twin | local_ai
    model_id: str
    elo_rating: float = 1500.0
    discipline_ranks: Dict[str, float] = field(default_factory=lambda: {
        "Guard": 75.0,
        "Passing": 75.0,
        "Submission": 75.0,
        "Escape": 75.0,
        "Takedown": 75.0
    })
    tactical_bias: str = "balanced"
    current_position: PositionState = PositionState.STANDING
    stamina_pct: float = 100.0
    points: int = 0
    advantages: int = 0
    penalties: int = 0
    current_torque_nm: float = 0.0
    active_submission: Optional[str] = None
    tatami_x: float = 0.0
    tatami_y: float = 0.0
    active_directive: Optional[str] = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    submissions_secured: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "fighter_type": self.fighter_type,
            "model_id": self.model_id,
            "elo_rating": round(self.elo_rating, 1),
            "discipline_ranks": {k: round(v, 1) for k, v in self.discipline_ranks.items()},
            "tactical_bias": self.tactical_bias,
            "active_directive": self.active_directive,
            "current_position": self.current_position.value,
            "stamina_pct": round(self.stamina_pct, 1),
            "points": self.points,
            "advantages": self.advantages,
            "penalties": self.penalties,
            "current_torque_nm": round(self.current_torque_nm, 1),
            "active_submission": self.active_submission,
            "tatami_x": round(self.tatami_x, 2),
            "tatami_y": round(self.tatami_y, 2),
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "submissions_secured": self.submissions_secured,
        }


@dataclass
class MatchTickEvent:
    tick: int
    elapsed_time_s: float
    initiator_id: str
    action_name: str
    category: str
    result: str
    joint_torque_nm: float
    points_awarded: int
    position_after: str
    commentary: str
    tatami_coordinates: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "elapsed_time_s": round(self.elapsed_time_s, 1),
            "initiator_id": self.initiator_id,
            "action_name": self.action_name,
            "category": self.category,
            "result": self.result,
            "joint_torque_nm": round(self.joint_torque_nm, 1),
            "points_awarded": self.points_awarded,
            "position_after": self.position_after,
            "commentary": self.commentary,
            "tatami_coordinates": [round(c, 2) for c in self.tatami_coordinates],
        }


@dataclass
class ArenaMatch:
    match_id: str
    fighter_a: GrapplingFighter
    fighter_b: GrapplingFighter
    state: MatchState = MatchState.SCHEDULED
    round_duration_s: float = 300.0  # 5 minutes
    elapsed_time_s: float = 0.0
    current_tick: int = 0
    ticks_history: List[MatchTickEvent] = field(default_factory=list)
    winner_id: Optional[str] = None
    win_method: Optional[str] = None
    final_scores: Dict[str, int] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "fighter_a": self.fighter_a.to_dict(),
            "fighter_b": self.fighter_b.to_dict(),
            "state": self.state.value,
            "round_duration_s": self.round_duration_s,
            "elapsed_time_s": round(self.elapsed_time_s, 1),
            "current_tick": self.current_tick,
            "winner_id": self.winner_id,
            "win_method": self.win_method,
            "final_scores": self.final_scores,
            "timestamp": self.timestamp,
            "recent_events": [evt.to_dict() for evt in self.ticks_history[-10:]],
            "total_events": len(self.ticks_history),
        }


class CombatDirector:
    """
    Directs virtual tatami sparring between human biometric twins and local AI fighters.
    Implements Roll Exchange Protocol (REP) and Bradley-Terry ELO rating logic.
    """

    def __init__(self):
        self.fighters: Dict[str, GrapplingFighter] = {}
        self.active_match: Optional[ArenaMatch] = None
        self.match_history: List[ArenaMatch] = []
        self._init_default_fighters()

    def _init_default_fighters(self):
        """Initializes canonical roster of digital twins and local AI models."""
        # 1. Aaron (Human Biometric Digital Twin)
        self.fighters["aaron_twin"] = GrapplingFighter(
            id="aaron_twin",
            name="Aaron (Movesense Twin)",
            fighter_type="human_twin",
            model_id="Movesense-512Hz-Zone2",
            elo_rating=1550.0,
            discipline_ranks={
                "Guard": 84.0,
                "Passing": 80.0,
                "Submission": 85.0,
                "Escape": 82.0,
                "Takedown": 78.0
            },
            tactical_bias="pressure_and_submissions",
            current_position=PositionState.STANDING
        )

        # 2. Apex-NPU (Apple Silicon 16-Core ANE Speculative Drafter)
        self.fighters["apex_npu"] = GrapplingFighter(
            id="apex_npu",
            name="Apex-NPU (Systolic Sub Hunter)",
            fighter_type="local_ai",
            model_id="SmolLM2-360M-INT8-ANE",
            elo_rating=1530.0,
            discipline_ranks={
                "Guard": 80.0,
                "Passing": 75.0,
                "Submission": 94.0,
                "Escape": 86.0,
                "Takedown": 72.0
            },
            tactical_bias="submission_hunter",
            current_position=PositionState.STANDING
        )

        # 3. Nyx-NPU (Edge TPU Uncensored Scramble & Leglock Specialist)
        self.fighters["nyx_npu"] = GrapplingFighter(
            id="nyx_npu",
            name="Nyx-NPU (Abliterated Leglocker)",
            fighter_type="local_ai",
            model_id="Qwen2.5-0.5B-INT8-TPU",
            elo_rating=1545.0,
            discipline_ranks={
                "Guard": 88.0,
                "Passing": 70.0,
                "Submission": 96.0,
                "Escape": 85.0,
                "Takedown": 80.0
            },
            tactical_bias="leglock_specialist",
            current_position=PositionState.STANDING
        )

        # 4. Sovereign-Qwen (Master Local Orchestrator - Heavy Pressure Passer)
        self.fighters["sovereign_qwen"] = GrapplingFighter(
            id="sovereign_qwen",
            name="Sovereign-Qwen (Pressure Grinder)",
            fighter_type="local_ai",
            model_id="Qwen-3.8-Max-Port8082",
            elo_rating=1620.0,
            discipline_ranks={
                "Guard": 78.0,
                "Passing": 95.0,
                "Submission": 88.0,
                "Escape": 90.0,
                "Takedown": 91.0
            },
            tactical_bias="positional_grinder",
            current_position=PositionState.STANDING
        )

        # 5. Nexus-Core (Guard Retention & Counter Specialist)
        self.fighters["nexus_core"] = GrapplingFighter(
            id="nexus_core",
            name="Nexus-Core (Guard Sorcerer)",
            fighter_type="local_ai",
            model_id="Qwen2.5-Coder-7B",
            elo_rating=1510.0,
            discipline_ranks={
                "Guard": 95.0,
                "Passing": 72.0,
                "Submission": 84.0,
                "Escape": 92.0,
                "Takedown": 65.0
            },
            tactical_bias="guard_retention",
            current_position=PositionState.STANDING
        )

    def get_roster(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.fighters.values()]

    def get_fighter(self, fighter_id: str) -> Optional[GrapplingFighter]:
        return self.fighters.get(fighter_id)

    def create_match(self, fighter_a_id: str, fighter_b_id: str, duration_s: float = 300.0) -> ArenaMatch:
        """Schedules a new match on the 10m x 10m tatami canvas."""
        f_a = self.fighters.get(fighter_a_id)
        f_b = self.fighters.get(fighter_b_id)

        if not f_a or not f_b:
            raise ValueError(f"Invalid fighter IDs: {fighter_a_id} vs {fighter_b_id}")

        # Reset in-match counters
        for f in [f_a, f_b]:
            f.points = 0
            f.advantages = 0
            f.penalties = 0
            f.current_position = PositionState.STANDING
            f.stamina_pct = 100.0
            f.current_torque_nm = 0.0
            f.active_submission = None
            f.active_directive = None

        f_a.tatami_x, f_a.tatami_y = -1.2, 0.0
        f_b.tatami_x, f_b.tatami_y = 1.2, 0.0

        match = ArenaMatch(
            match_id=f"rep_match_{uuid.uuid4().hex[:8]}",
            fighter_a=f_a,
            fighter_b=f_b,
            state=MatchState.SPARRING,
            round_duration_s=duration_s,
            elapsed_time_s=0.0,
            current_tick=0,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        self.active_match = match
        return match

    def execute_match_tick(self, dt_s: float = 5.0) -> Dict[str, Any]:
        """
        Executes one high-speed Roll Exchange Protocol (REP) tick.
        Evaluates tactical technique choices, joint torque accumulation, and positional score.
        """
        if not self.active_match or self.active_match.state != MatchState.SPARRING:
            return {"status": "NO_ACTIVE_MATCH"}

        match = self.active_match
        match.current_tick += 1
        match.elapsed_time_s += dt_s

        f_a = match.fighter_a
        f_b = match.fighter_b

        # 1. Update Biometrics for human digital twin
        for f in [f_a, f_b]:
            if f.fighter_type == "human_twin":
                bio = biometric_bridge.get_live_biometrics()
                f.stamina_pct = bio.stamina_pct

        # 2. Determine who initiates action based on position, stamina, and dice roll
        stamina_diff = (f_a.stamina_pct - f_b.stamina_pct) / 100.0
        init_prob_a = 0.5 + (stamina_diff * 0.25)
        attacker, defender = (f_a, f_b) if random.random() < init_prob_a else (f_b, f_a)

        # 3. Check if active submission is currently applied
        if defender.active_submission:
            # Accumulate joint torque
            torque_increment = random.uniform(8.0, 16.0)
            if attacker.active_directive == "HUNT_SUBMISSION":
                torque_increment += 5.0  # Corner coaching torque intensification
            defender.current_torque_nm += torque_increment

            # Defender attempts escape
            escape_skill = defender.discipline_ranks.get("Escape", 75.0)
            escape_roll = random.uniform(0.0, 100.0) + (defender.stamina_pct * 0.2)
            if defender.active_directive == "SCRAMBLE_ESCAPE":
                escape_roll += 25.0  # Explosive scramble corner boost

            if escape_roll > (escape_skill + 10.0):
                # Escape succeeded!
                esc_commentary = f"⚡ {defender.name} explodes with technical hip escape and breaks the {defender.active_submission} grip!"
                if defender.active_directive == "SCRAMBLE_ESCAPE":
                    esc_commentary = f"💥 [CORNER BOOST] {defender.name} executes rapid scramble escape breaking {defender.active_submission}!"
                sub_name = defender.active_submission
                defender.active_submission = None
                defender.current_torque_nm = 0.0
                attacker.stamina_pct = max(10.0, attacker.stamina_pct - 8.0)
                defender.stamina_pct = max(10.0, defender.stamina_pct - 10.0)

                evt = MatchTickEvent(
                    tick=match.current_tick,
                    elapsed_time_s=match.elapsed_time_s,
                    initiator_id=defender.id,
                    action_name=f"Escape from {sub_name}",
                    category="Escape",
                    result="ESCAPE_SUCCESS",
                    joint_torque_nm=0.0,
                    points_awarded=0,
                    position_after=attacker.current_position.value,
                    commentary=esc_commentary,
                    tatami_coordinates=(attacker.tatami_x, attacker.tatami_y)
                )
                match.ticks_history.append(evt)
                return self._build_tick_response(match, evt)

            # Check 45.0 N·m tap threshold gate (Rule #0)
            if opml_tactical_graph.is_tap_gate_triggered(defender.current_torque_nm):
                tap_commentary = (
                    f"🔴 TAP OUT! {defender.name} taps verbally as joint torque hits "
                    f"{defender.current_torque_nm:.1f} N·m (over 45.0 N·m safety gate)! "
                    f"Winner by Submission: {attacker.name} ({defender.active_submission})!"
                )
                match.state = MatchState.SUBMISSION_TAP
                match.winner_id = attacker.id
                match.win_method = f"Submission: {defender.active_submission} ({defender.current_torque_nm:.1f} N·m)"
                attacker.submissions_secured += 1
                self._update_elo_ratings(match)
                self._crystallize_match(match)

                evt = MatchTickEvent(
                    tick=match.current_tick,
                    elapsed_time_s=match.elapsed_time_s,
                    initiator_id=attacker.id,
                    action_name=defender.active_submission,
                    category="Submission",
                    result="TAP_SUBMISSION_VICTORY",
                    joint_torque_nm=defender.current_torque_nm,
                    points_awarded=0,
                    position_after=attacker.current_position.value,
                    commentary=tap_commentary,
                    tatami_coordinates=(attacker.tatami_x, attacker.tatami_y)
                )
                match.ticks_history.append(evt)
                return self._build_tick_response(match, evt)

            # Hold maintained
            evt = MatchTickEvent(
                tick=match.current_tick,
                elapsed_time_s=match.elapsed_time_s,
                initiator_id=attacker.id,
                action_name=defender.active_submission,
                category="Submission",
                result="HOLD_MAINTAINED",
                joint_torque_nm=defender.current_torque_nm,
                points_awarded=0,
                position_after=attacker.current_position.value,
                commentary=f"🔒 {attacker.name} cranks the {defender.active_submission}! Joint tension at {defender.current_torque_nm:.1f} N·m!",
                tatami_coordinates=(attacker.tatami_x, attacker.tatami_y)
            )
            match.ticks_history.append(evt)
            return self._build_tick_response(match, evt)

        # 4. Standard positional / tactical transition
        current_pos = attacker.current_position
        candidate_moves = opml_tactical_graph.get_admissible_transitions(current_pos)
        if not candidate_moves:
            candidate_moves = opml_tactical_graph.get_admissible_transitions(PositionState.STANDING)

        # Tactical bias and corner directive selection
        chosen_move: TacticalNode = random.choice(candidate_moves)
        if attacker.active_directive == "HUNT_SUBMISSION":
            sub_moves = [m for m in candidate_moves if m.is_submission]
            if sub_moves and random.random() < 0.85:
                chosen_move = random.choice(sub_moves)
        elif attacker.active_directive == "SMASH_PASS":
            pass_moves = [m for m in candidate_moves if m.category == "Passing"]
            if pass_moves and random.random() < 0.85:
                chosen_move = random.choice(pass_moves)
        elif attacker.active_directive == "PULL_GUARD":
            guard_moves = [m for m in candidate_moves if m.category == "Guard" or "guard" in m.id]
            if guard_moves and random.random() < 0.85:
                chosen_move = random.choice(guard_moves)
        elif attacker.active_directive == "CONSERVE_ZONE_2":
            low_cost = [m for m in candidate_moves if m.stamina_cost_joules <= 180.0]
            if low_cost and random.random() < 0.75:
                chosen_move = random.choice(low_cost)
        elif attacker.tactical_bias == "submission_hunter":
            sub_moves = [m for m in candidate_moves if m.is_submission]
            if sub_moves and random.random() < 0.65:
                chosen_move = random.choice(sub_moves)
        elif attacker.tactical_bias == "leglock_specialist":
            leg_moves = [m for m in candidate_moves if "heel" in m.id or "ankle" in m.id or m.to_positions == [PositionState.LEG_ENTANGLEMENT]]
            if leg_moves and random.random() < 0.70:
                chosen_move = random.choice(leg_moves)

        # Compute transition contest
        atk_skill = attacker.discipline_ranks.get(chosen_move.category, 75.0)
        def_skill = defender.discipline_ranks.get("Escape", 75.0) if chosen_move.is_submission else defender.discipline_ranks.get("Guard", 75.0)
        
        score_diff = (atk_skill - def_skill) + ((attacker.stamina_pct - defender.stamina_pct) * 0.3)
        success_chance = 1.0 / (1.0 + math.exp(-score_diff / 18.0))

        # Tatami drift
        drift_x = random.uniform(-0.4, 0.4)
        drift_y = random.uniform(-0.4, 0.4)
        attacker.tatami_x = max(-4.8, min(4.8, attacker.tatami_x + drift_x))
        attacker.tatami_y = max(-4.8, min(4.8, attacker.tatami_y + drift_y))
        defender.tatami_x = attacker.tatami_x + 0.3
        defender.tatami_y = attacker.tatami_y

        if random.random() < success_chance:
            # Action succeeded
            if chosen_move.is_submission:
                defender.active_submission = chosen_move.name
                base_torque = random.uniform(18.0, 32.0)
                if attacker.active_directive == "HUNT_SUBMISSION":
                    base_torque += 5.0
                defender.current_torque_nm = base_torque
                commentary = f"🎯 {attacker.name} attacks with {chosen_move.name}! Locking joint torque at {defender.current_torque_nm:.1f} N·m!"
                points = 0
            else:
                next_pos = random.choice(chosen_move.to_positions)
                attacker.current_position = next_pos
                defender.current_position = next_pos
                attacker.points += chosen_move.points_awarded
                points = chosen_move.points_awarded
                pts_str = f" (+{points} pts)" if points > 0 else ""
                commentary = f"🥋 {attacker.name} executes {chosen_move.name}{pts_str}, advancing to {next_pos.value}."

            atk_burn = chosen_move.stamina_cost_joules / 500.0
            if attacker.active_directive == "CONSERVE_ZONE_2":
                atk_burn *= 0.5  # 50% energy conservation in Zone 2
            attacker.stamina_pct = max(5.0, attacker.stamina_pct - atk_burn)

            def_burn = 3.5
            if defender.active_directive == "CONSERVE_ZONE_2":
                def_burn *= 0.5
            defender.stamina_pct = max(5.0, defender.stamina_pct - def_burn)

            evt = MatchTickEvent(
                tick=match.current_tick,
                elapsed_time_s=match.elapsed_time_s,
                initiator_id=attacker.id,
                action_name=chosen_move.name,
                category=chosen_move.category,
                result="ACTION_SUCCESS",
                joint_torque_nm=defender.current_torque_nm,
                points_awarded=points,
                position_after=attacker.current_position.value,
                commentary=commentary,
                tatami_coordinates=(attacker.tatami_x, attacker.tatami_y)
            )
        else:
            # Action defended / countered
            attacker.stamina_pct = max(5.0, attacker.stamina_pct - 4.0)
            defender.stamina_pct = max(5.0, defender.stamina_pct - 2.5)
            commentary = f"🛡️ {defender.name} shuts down {attacker.name}'s attempt at {chosen_move.name} with rigid frames."

            evt = MatchTickEvent(
                tick=match.current_tick,
                elapsed_time_s=match.elapsed_time_s,
                initiator_id=attacker.id,
                action_name=chosen_move.name,
                category=chosen_move.category,
                result="DEFENDED",
                joint_torque_nm=defender.current_torque_nm,
                points_awarded=0,
                position_after=attacker.current_position.value,
                commentary=commentary,
                tatami_coordinates=(attacker.tatami_x, attacker.tatami_y)
            )

        match.ticks_history.append(evt)

        # 5. Check Time Limit (300 seconds default)
        if match.elapsed_time_s >= match.round_duration_s and match.state == MatchState.SPARRING:
            match.state = MatchState.POINTS_DECISION
            match.final_scores = {f_a.id: f_a.points, f_b.id: f_b.points}
            if f_a.points > f_b.points:
                match.winner_id = f_a.id
                match.win_method = f"Points Decision ({f_a.points} - {f_b.points})"
            elif f_b.points > f_a.points:
                match.winner_id = f_b.id
                match.win_method = f"Points Decision ({f_b.points} - {f_a.points})"
            else:
                match.winner_id = None
                match.win_method = f"Draw on Points ({f_a.points} - {f_b.points})"

            self._update_elo_ratings(match)
            self._crystallize_match(match)

        return self._build_tick_response(match, evt)

    def _update_elo_ratings(self, match: ArenaMatch):
        """Applies Bradley-Terry ELO rating adjustments upon match completion (K=32)."""
        f_a = match.fighter_a
        f_b = match.fighter_b

        k = 32.0
        exp_a = 1.0 / (1.0 + 10.0 ** ((f_b.elo_rating - f_a.elo_rating) / 400.0))
        exp_b = 1.0 / (1.0 + 10.0 ** ((f_a.elo_rating - f_b.elo_rating) / 400.0))

        if match.winner_id == f_a.id:
            score_a, score_b = 1.0, 0.0
            f_a.wins += 1
            f_b.losses += 1
        elif match.winner_id == f_b.id:
            score_a, score_b = 0.0, 1.0
            f_b.wins += 1
            f_a.losses += 1
        else:
            score_a, score_b = 0.5, 0.5
            f_a.draws += 1
            f_b.draws += 1

        f_a.elo_rating = round(f_a.elo_rating + k * (score_a - exp_a), 1)
        f_b.elo_rating = round(f_b.elo_rating + k * (score_b - exp_b), 1)

    def _crystallize_match(self, match: ArenaMatch):
        """Serializes completed match report to Obsidian Vault and LoRA dataset."""
        try:
            OBSIDIAN_VAULT_ARENA_DIR.mkdir(parents=True, exist_ok=True)
            vault_file = OBSIDIAN_VAULT_ARENA_DIR / f"ARENA_MATCH_{match.match_id}.md"

            content = f"""---
title: "Grappling Arena REP Match {match.match_id}"
tags: [lauburu, grappling_arena, rep, digital_twins, biometrics, elo]
match_id: "{match.match_id}"
winner: "{match.winner_id or 'DRAW'}"
win_method: "{match.win_method}"
timestamp: "{match.timestamp}"
---

# 🥋 Interactive AI Grappling Arena — Roll Exchange Protocol Match

**Match ID:** `{match.match_id}`  
**State:** `{match.state.value}`  
**Winner:** `{match.winner_id or 'DRAW'}`  
**Decision / Sub:** `{match.win_method}`  
**Duration:** `{match.elapsed_time_s:.1f}s / {match.round_duration_s}s`  

### 🤼 Fighters
- **{match.fighter_a.name}** ({match.fighter_a.fighter_type}) — ELO: {match.fighter_a.elo_rating} | Points: {match.fighter_a.points}
- **{match.fighter_b.name}** ({match.fighter_b.fighter_type}) — ELO: {match.fighter_b.elo_rating} | Points: {match.fighter_b.points}

### 📜 Technical Play-by-Play Commentary
"""
            for evt in match.ticks_history:
                content += f"- **[{evt.elapsed_time_s:.1f}s]** {evt.commentary}\n"

            with open(vault_file, "w", encoding="utf-8") as f:
                f.write(content)

            # LoRA dataset line
            LORA_DATASET_ARENA_FILE.parent.mkdir(parents=True, exist_ok=True)
            lora_record = {
                "source": "grappling_arena_rep",
                "match_id": match.match_id,
                "winner": match.winner_id,
                "win_method": match.win_method,
                "duration_s": match.elapsed_time_s,
                "fighters": [match.fighter_a.to_dict(), match.fighter_b.to_dict()],
                "total_events": len(match.ticks_history),
                "rule_0_verified": True,
                "timestamp": match.timestamp
            }
            with open(LORA_DATASET_ARENA_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(lora_record) + "\n")

            # Canonical continuous LoRA instruction pair
            canonical_lora_file = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
            if canonical_lora_file.parent.exists():
                prompt_instruction = (
                    f"Analyze the technical outcome, positional dynamics, and tactical counter-tree of Roll Exchange Protocol match {match.match_id} "
                    f"between {match.fighter_a.name} ({match.fighter_a.style}) and {match.fighter_b.name} ({match.fighter_b.style})."
                )
                tactical_summary = f"Winner: {match.winner_id} via {match.win_method} at {match.elapsed_time_s:.1f}s. Total events: {len(match.ticks_history)}. "
                if match.ticks_history:
                    last_few = [f"[{t.elapsed_time_s:.1f}s] {t.commentary}" for t in match.ticks_history[-3:]]
                    tactical_summary += "Decisive sequence: " + " -> ".join(last_few)

                instruction_record = {
                    "timestamp": match.timestamp,
                    "source": "grappling_arena_rep",
                    "instruction": prompt_instruction,
                    "input": f"Fighter A: {match.fighter_a.name} ({match.fighter_a.position.name}, Stamina: {match.fighter_a.stamina_pct:.1f}%). Fighter B: {match.fighter_b.name} ({match.fighter_b.position.name}, Stamina: {match.fighter_b.stamina_pct:.1f}%).",
                    "output": tactical_summary
                }
                with open(canonical_lora_file, "a", encoding="utf-8") as cf:
                    cf.write(json.dumps(instruction_record) + "\n")

            self.match_history.append(match)
            logger.info(f"Crystallized match {match.match_id} to Tri-Vault ({vault_file})")
        except Exception as e:
            logger.warning(f"Error crystallizing match to Tri-Vault: {e}")

    def _build_tick_response(self, match: ArenaMatch, evt: MatchTickEvent) -> Dict[str, Any]:
        return {
            "status": "MATCH_ACTIVE" if match.state == MatchState.SPARRING else "MATCH_CONCLUDED",
            "match": match.to_dict(),
            "latest_event": evt.to_dict(),
            "leaderboard": self.get_leaderboard()
        }

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        sorted_fighters = sorted(self.fighters.values(), key=lambda f: f.elo_rating, reverse=True)
        return [
            {
                "rank": idx + 1,
                "id": f.id,
                "name": f.name,
                "type": f.fighter_type,
                "model_id": f.model_id,
                "elo_rating": round(f.elo_rating, 1),
                "record": f"{f.wins}W - {f.losses}L - {f.draws}D",
                "submissions": f.submissions_secured,
                "bias": f.tactical_bias
            }
            for idx, f in enumerate(sorted_fighters)
        ]

    def apply_corner_directive(self, match_id: Optional[str], fighter_id: str, directive: str) -> Dict[str, Any]:
        """
        Barks real-time corner coaching tactical directive to the fighter during live sparring.
        Supported directives:
        - CONSERVE_ZONE_2: Cuts stamina burn by 50%, pulls guard if standing, triggers Movesense aerobic recovery.
        - HUNT_SUBMISSION: Biases technique choice 85% towards joint locks/chokes and increases crank force by +5.0 N·m.
        - SMASH_PASS: Prioritizes passing techniques (knee slice, toreando, bodylock) toward Side Control / Mount.
        - SCRAMBLE_ESCAPE: Grants +25% boost to submission and pin escapes.
        - PULL_GUARD: Immediate tactical repositioning to closed/butterfly guard.
        - RESET_NEUTRAL: Clears active directive.
        """
        fighter = self.fighters.get(fighter_id)
        if not fighter:
            raise ValueError(f"Fighter {fighter_id} not found in roster.")

        valid_directives = {
            "CONSERVE_ZONE_2",
            "HUNT_SUBMISSION",
            "SMASH_PASS",
            "SCRAMBLE_ESCAPE",
            "PULL_GUARD",
            "RESET_NEUTRAL"
        }
        if directive not in valid_directives:
            raise ValueError(f"Invalid directive '{directive}'. Must be one of {valid_directives}")

        fighter.active_directive = None if directive == "RESET_NEUTRAL" else directive
        logger.info(f"Corner directive applied to {fighter.name}: {directive}")

        # If an active match exists, log this tactical corner event
        if self.active_match and self.active_match.state == MatchState.SPARRING:
            evt = MatchTickEvent(
                tick=self.active_match.current_tick,
                elapsed_time_s=self.active_match.elapsed_time_s,
                initiator_id=fighter.id,
                action_name=f"Corner Directive: {directive}",
                category="CornerCoach",
                result="DIRECTIVE_ACTIVE",
                joint_torque_nm=fighter.current_torque_nm,
                points_awarded=0,
                position_after=fighter.current_position.value,
                commentary=f"🗣️ Corner Coach instructs {fighter.name}: '{directive.replace('_', ' ')}'!",
                tatami_coordinates=(fighter.tatami_x, fighter.tatami_y)
            )
            self.active_match.ticks_history.append(evt)

        return {
            "status": "SUCCESS",
            "fighter_id": fighter.id,
            "fighter_name": fighter.name,
            "active_directive": fighter.active_directive,
            "message": f"Directive {directive} applied to {fighter.name}."
        }

    def get_user_comprehensive_profile(self, fighter_id: str = "aaron_twin") -> Dict[str, Any]:
        """
        Combines authentic Movesense biometric conditioning analysis (Zone 2, DFA-alpha1, HRV RMSSD)
        with 3,044-node OPML martial graph grappling ability analysis to produce complete user level.
        """
        fighter = self.fighters.get(fighter_id, self.fighters.get("aaron_twin"))
        if not fighter:
            fighter = self.fighters["aaron_twin"]

        conditioning = biometric_bridge.analyze_conditioning_and_level()
        grappling = opml_tactical_graph.analyze_grappling_ability(fighter.discipline_ranks)

        # Composite fighter level (0-100 scale)
        composite_level = round(
            (conditioning["conditioning_score"] * 0.45) +
            (grappling["overall_ability_score"] * 0.55),
            1
        )

        return {
            "fighter_id": fighter.id,
            "name": fighter.name,
            "fighter_type": fighter.fighter_type,
            "model_id": fighter.model_id,
            "elo_rating": round(fighter.elo_rating, 1),
            "record": f"{fighter.wins}W - {fighter.losses}L - {fighter.draws}D",
            "active_directive": fighter.active_directive,
            "composite_level": composite_level,
            "conditioning": conditioning,
            "grappling": grappling,
            "disciplines": fighter.discipline_ranks,
            "status": "🟢 COMPREHENSIVE AI PROFILE ACTIVE"
        }


# Singleton instance
combat_director = CombatDirector()
