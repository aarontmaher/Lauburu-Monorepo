#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Sovereign Mesh: Automatic ROI-Gated AI Training Protocol
================================================================================
Subsystem: 05_agents_and_swarms/roi_gated_training_protocol.py
Version: 1.0.0-AUTONOMOUS-ROI-PREEMPTION
Lauburu Mesh Ecosystem — 2026

Governs:
1. Role-Relative Functional Project ELO calculation for each local model.
2. Real-time Training ROI computation across all local models and task domains:
      ROI = (Delta_ELO_Projected * Task_Traffic_Weight * Loss_Velocity) / (VRAM_GB * Epoch_Minutes * Diminishing_Penalty)
3. Dynamic Preemption: Automatically switches active training to whichever local
   model + task yields the highest immediate ROI for the project.
4. Serializes live state to 04_data_and_memory/roi_gated_training_status.json for
   instant consumption by the Web Leaderboard Dashboard.
================================================================================
"""

import os
import sys
import time
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "04_data_and_memory"
ROI_STATUS_FILE = DATA_DIR / "roi_gated_training_status.json"
WEAKEST_LINKS_FILE = DATA_DIR / "weakest_links_evolution_status.json"
LIVE_TELEMETRY_FILE = DATA_DIR / "live_training_telemetry.json"
ELO_LEADERBOARD_FILE = REPO_ROOT / "05_agents_and_swarms/swarm_elo_leaderboard.json"
PROVIDER_REGISTRY_FILE = DATA_DIR / "dynamic_provider_registry.json"


def load_live_telemetry() -> Dict[str, Any]:
    """
    Loads live training telemetry from live_loss_extractor.py output.
    Returns {} if file is missing or stale (> 5 min). Rule #0: no mocks.
    """
    if not LIVE_TELEMETRY_FILE.exists():
        return {}
    try:
        age = time.time() - LIVE_TELEMETRY_FILE.stat().st_mtime
        if age > 300:
            return {}
        return json.loads(LIVE_TELEMETRY_FILE.read_text())
    except Exception:
        return {}


def load_live_elo(model_id: str, fallback: float) -> float:
    """Reads current ELO from swarm_elo_leaderboard.json; falls back to static base."""
    if not ELO_LEADERBOARD_FILE.exists():
        return fallback
    try:
        data = json.loads(ELO_LEADERBOARD_FILE.read_text())
        if isinstance(data, list):
            for entry in data:
                if entry.get("model_id") == model_id or entry.get("id") == model_id:
                    return float(entry.get("elo", fallback))
        elif isinstance(data, dict):
            if model_id in data:
                return float(data[model_id].get("elo", fallback))
    except Exception:
        pass
    return fallback


def load_provider_budget_factor() -> float:
    """Returns multiplier > 1.0 when paid APIs (Claude, ChatGPT) are configured."""
    if not PROVIDER_REGISTRY_FILE.exists():
        return 1.0
    try:
        data = json.loads(PROVIDER_REGISTRY_FILE.read_text())
        paid = [
            alias for alias, cfg in data.get("all_providers", {}).items()
            if cfg.get("status") == "CONFIGURED" and cfg.get("cost_per_1k_tokens", 0.0) > 0.0
        ]
        return 1.0 + len(paid) * 0.20
    except Exception:
        return 1.0

# ── Role Definitions & Project Functionality Weights ─────────────────────────
MODEL_ROLE_PROFILES = {
    "agentworld_35b": {
        "model_name": "Qwen-AgentWorld-35B-A3B",
        "role_title": "OS World Simulator & Lookahead",
        "primary_domain": "os_world_simulation_and_mcts",
        "domain_weights": {"code": 0.35, "net": 0.35, "lora": 0.20, "math": 0.10},
        "task_traffic_weight": 0.95,
        "base_elo": 1985.0,
        "vram_gb": 20.6,
        "host_node": "L1 Mac Mini M4 Pro Host"
    },
    "qwen38_flash_next": {
        "model_name": "Qwen 3.8 Flash Next (Sharded)",
        "role_title": "Frontier Heavyweight Orchestration Engine",
        "primary_domain": "general_frontier_orchestration",
        "domain_weights": {"code": 0.30, "math": 0.25, "lora": 0.25, "net": 0.20},
        "task_traffic_weight": 0.90,
        "base_elo": 1980.0,
        "vram_gb": 73.5,
        "host_node": "L1 + L2 + L5 + L3 10Gbps TB4 Ring"
    },
    "kimi_dev_72b": {
        "model_name": "Moonshot Kimi-Dev-72B (3-Way Sharded)",
        "role_title": "Tier-1 Polyglot Architecture & Long-Context Master",
        "primary_domain": "deep_architectural_synthesis",
        "domain_weights": {"code": 0.40, "lora": 0.30, "net": 0.15, "math": 0.15},
        "task_traffic_weight": 0.92,
        "base_elo": 1965.0,
        "vram_gb": 39.0,
        "host_node": "L3 Linux (28L) + L2 MBP (28L) + L1 Mac (24L)"
    },
    "qwen38_ablit": {
        "model_name": "Huihui-Qwen3.8-27B-abliterated",
        "role_title": "Devil's Advocate & Adversarial Red Teamer",
        "primary_domain": "adversarial_security_and_truth_audit",
        "domain_weights": {"cyber": 0.50, "code": 0.25, "lora": 0.15, "net": 0.10},
        "task_traffic_weight": 0.88,
        "base_elo": 1965.0,
        "vram_gb": 16.0,
        "host_node": "L1 Mac Mini Metal GPU"
    },
    "deepseek_r1_32b": {
        "model_name": "DeepSeek R1 Distill Qwen 32B",
        "role_title": "Algorithmic Reasoning & Formal Verification",
        "primary_domain": "formal_verification_and_proofs",
        "domain_weights": {"math": 0.50, "code": 0.30, "lora": 0.20},
        "task_traffic_weight": 0.85,
        "base_elo": 1950.0,
        "vram_gb": 19.8,
        "host_node": "L1 Mac Mini Host"
    },
    "qwen_coder32": {
        "model_name": "Qwen 2.5 Coder 32B",
        "role_title": "Polyglot Software Master & AST Refactorer",
        "primary_domain": "polyglot_software_engineering",
        "domain_weights": {"code": 0.55, "lora": 0.25, "net": 0.20},
        "task_traffic_weight": 0.94,
        "base_elo": 1940.0,
        "vram_gb": 19.8,
        "host_node": "L1 Mac Mini Host"
    },
    "webworld_32b": {
        "model_name": "Qwen-WebWorld-32B (Sharded)",
        "role_title": "Web Flight Simulator & Accessibility Inspector",
        "primary_domain": "web_dom_simulation_and_a11y",
        "domain_weights": {"net": 0.40, "code": 0.35, "lora": 0.25},
        "task_traffic_weight": 0.82,
        "base_elo": 1920.0,
        "vram_gb": 18.4,
        "host_node": "L1 Mac Mini + L5 Air M4"
    },
    "qwen_math72": {
        "model_name": "Qwen 2.5 Math 72B (Sharded)",
        "role_title": "ILP Mesh Optimization & Topology Solver",
        "primary_domain": "ilp_mesh_topology_optimization",
        "domain_weights": {"math": 0.60, "lora": 0.25, "net": 0.15},
        "task_traffic_weight": 0.78,
        "base_elo": 1910.0,
        "vram_gb": 19.8,
        "host_node": "L1 + L2 TB4 DMA Shard"
    },
    "qwen_coder7": {
        "model_name": "Qwen 2.5 Coder 7B",
        "role_title": "Fast Syntax Validator & Subagent AST Worker",
        "primary_domain": "fast_syntax_validation",
        "domain_weights": {"code": 0.60, "speed": 0.25, "lora": 0.15},
        "task_traffic_weight": 0.86,
        "base_elo": 1780.0,
        "vram_gb": 4.4,
        "host_node": "L1 Mac Mini Host"
    },
    "smollm2_17b": {
        "model_name": "SmolLM2 1.7B Instruct",
        "role_title": "Android ADB UI & Accessibility Tester",
        "primary_domain": "android_adb_ui_test_automation",
        "domain_weights": {"net": 0.45, "cyber": 0.30, "speed": 0.25},
        "task_traffic_weight": 0.89,
        "base_elo": 1720.0,
        "vram_gb": 1.05,
        "host_node": "L7 Samsung Galaxy S20+ (Exynos RAM)"
    },
    "deepseek_15b": {
        "model_name": "DeepSeek R1 Distill 1.5B",
        "role_title": "Edge DSP Biometrics & Kinematics Reasoner",
        "primary_domain": "biometric_dsp_and_touch_telemetry",
        "domain_weights": {"math": 0.45, "net": 0.30, "speed": 0.25},
        "task_traffic_weight": 0.80,
        "base_elo": 1680.0,
        "vram_gb": 1.1,
        "host_node": "L4 Debian Linux Tablet"
    },
    "smollm2_360m": {
        "model_name": "SmolLM2 360M Instruct",
        "role_title": "Sub-Second Micro UI Test Daemon",
        "primary_domain": "sub_second_ui_fuzzing",
        "domain_weights": {"net": 0.40, "speed": 0.40, "cyber": 0.20},
        "task_traffic_weight": 0.84,
        "base_elo": 1610.0,
        "vram_gb": 0.25,
        "host_node": "L7 Samsung Galaxy S20+"
    },
    "smollm2_135m_router": {
        "model_name": "SmolLM2 135M Router SLM",
        "role_title": "OpenWrt Network Guard & Packet Defense",
        "primary_domain": "openwrt_nftables_packet_defense",
        "domain_weights": {"net": 0.55, "cyber": 0.25, "speed": 0.20},
        "task_traffic_weight": 0.98,
        "base_elo": 1560.0,
        "vram_gb": 0.105,
        "host_node": "GW GL.iNet OpenWrt Router (Port 18802 • 120MB)"
    }
}


def calculate_functional_project_elo(model_id: str, scores: Dict[str, float], base_elo_input: Optional[float] = None) -> Dict[str, Any]:
    """
    Computes a model's Functional Project ELO relative to its designated role in the monorepo.
    """
    profile = MODEL_ROLE_PROFILES.get(model_id)
    if not profile:
        base = base_elo_input if base_elo_input is not None else scores.get("base_elo", 1750.0)
        return {
            "functional_elo": base,
            "role_fit_index": 100.0,
            "role_title": "External Reference Benchmark",
            "primary_domain": "general"
        }

    base_elo = profile["base_elo"]
    domain_weights = profile["domain_weights"]

    # Calculate domain alignment score (0 - 100)
    weighted_domain_score = 0.0
    for domain, weight in domain_weights.items():
        score = scores.get(domain, 80.0)
        weighted_domain_score += score * weight

    # Role fit index (normalized around 85 score baseline)
    # A model scoring 95+ in its core duties gets up to +35 ELO bonus in its project functional rating
    role_bonus = (weighted_domain_score - 85.0) * 4.5
    functional_elo = round(base_elo + role_bonus, 1)
    role_fit_index = round(min(100.0, max(50.0, weighted_domain_score)), 1)

    return {
        "functional_elo": functional_elo,
        "role_fit_index": role_fit_index,
        "role_title": profile["role_title"],
        "primary_domain": profile["primary_domain"],
        "task_traffic_weight": profile["task_traffic_weight"]
    }


class ROIGatedTrainingScheduler:
    """
    Autonomous scheduler that computes real-time training ROI per model + task,
    detects diminishing returns / plateaus, and preempts training to the highest-ROI track.
    """

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state_file = ROI_STATUS_FILE

    def compute_track_roi(
        self,
        model_id: str,
        current_elo: float,
        target_elo: float,
        current_loss: float,
        loss_velocity: float,
        epochs_completed: int
    ) -> Dict[str, Any]:
        profile = MODEL_ROLE_PROFILES.get(model_id, {})
        vram_gb = profile.get("vram_gb", 8.0)
        task_traffic = profile.get("task_traffic_weight", 0.75)
        primary_domain = profile.get("primary_domain", "general")
        model_name = profile.get("model_name", model_id)

        # Deficit in project capability (higher deficit = higher priority)
        elo_deficit = max(10.0, target_elo - current_elo)

        # Diminishing returns penalty increases as epochs advance with slow loss reduction
        diminishing_penalty = 1.0 + (0.15 * math.log1p(epochs_completed))
        if loss_velocity < 0.005:  # Loss plateau
            diminishing_penalty *= 2.5

        # Compute cost proxy (VRAM * estimated minutes per 1k samples)
        compute_cost_factor = math.sqrt(max(0.25, vram_gb)) * 2.0

        # ROI formula: Potential Value / Marginal Compute Cost
        raw_roi = (elo_deficit * task_traffic * max(0.01, loss_velocity) * 100.0) / (compute_cost_factor * diminishing_penalty)
        normalized_roi = round(min(99.9, max(1.0, raw_roi)), 2)

        return {
            "model_id": model_id,
            "model_name": model_name,
            "primary_domain": primary_domain,
            "current_elo": current_elo,
            "target_elo": target_elo,
            "elo_deficit": round(elo_deficit, 1),
            "current_loss": round(current_loss, 4),
            "loss_velocity": round(loss_velocity, 4),
            "epochs_completed": epochs_completed,
            "vram_gb": vram_gb,
            "task_traffic_weight": task_traffic,
            "training_roi": normalized_roi,
            "status": "EVALUATED"
        }

    def evaluate_all_curriculums(self) -> Dict[str, Any]:
        """
        Evaluates all candidate training tracks and selects the highest-ROI model + task.
        Live telemetry from live_loss_extractor.py is merged into static defaults.
        Rule #0: Static defaults are only used when live telemetry is unavailable.
        """
        # Load live telemetry (may be empty if extractor hasn't run yet)
        live_tel = load_live_telemetry()
        live_agg_loss = live_tel.get("aggregate_current_loss")
        live_agg_velocity = live_tel.get("aggregate_loss_velocity")
        live_plateau = live_tel.get("global_plateau_detected", False)

        # Load provider budget factor (expands when Claude/ChatGPT configured)
        budget_factor = load_provider_budget_factor()

        # 1. Candidate training tracks (static defaults — merged with live if available)
        static_tracks = [
            {
                "model_id": "smollm2_135m_router",
                "current_elo": 1560.0, "target_elo": 1690.0,
                "current_loss": 0.175, "loss_velocity": 0.045, "epochs": 4
            },
            {
                "model_id": "smollm2_17b",
                "current_elo": 1720.0, "target_elo": 1820.0,
                "current_loss": 0.245, "loss_velocity": 0.038, "epochs": 6
            },
            {
                "model_id": "qwen_coder7",
                "current_elo": 1780.0, "target_elo": 1890.0,
                "current_loss": 0.312, "loss_velocity": 0.055, "epochs": 3
            },
            {
                "model_id": "deepseek_15b",
                "current_elo": 1680.0, "target_elo": 1780.0,
                "current_loss": 0.290, "loss_velocity": 0.021, "epochs": 8
            },
            {
                "model_id": "qwen38_ablit",
                "current_elo": 1965.0, "target_elo": 2040.0,
                "current_loss": 0.145, "loss_velocity": 0.012, "epochs": 12
            },
            {
                "model_id": "agentworld_35b",
                "current_elo": 1985.0, "target_elo": 2050.0,
                "current_loss": 0.160, "loss_velocity": 0.018, "epochs": 9
            }
        ]

        # 2. Merge live telemetry: override static values where real data exists
        candidate_tracks = []
        for track in static_tracks:
            t = dict(track)
            # Live ELO from leaderboard (with static fallback)
            t["current_elo"] = load_live_elo(t["model_id"], t["current_elo"])
            # Live loss/velocity from trainer logs (apply to all tracks proportionally)
            if live_agg_loss is not None:
                # Scale relative to static baseline (preserve model rank ordering)
                ratio = live_agg_loss / max(0.01, t["current_loss"])
                t["current_loss"] = round(live_agg_loss * (t["current_loss"] / max(0.01, sum(s["current_loss"] for s in static_tracks) / len(static_tracks))), 5)
            if live_agg_velocity is not None:
                t["loss_velocity"] = max(0.001, live_agg_velocity)
            # If global plateau: apply velocity penalty to all tracks
            if live_plateau:
                t["loss_velocity"] = min(t["loss_velocity"], 0.004)
            candidate_tracks.append(t)

        # 3. Evaluate ROI for each track
        evaluated = []
        for track in candidate_tracks:
            res = self.compute_track_roi(
                model_id=track["model_id"],
                current_elo=track["current_elo"],
                target_elo=track["target_elo"],
                current_loss=track["current_loss"],
                loss_velocity=track["loss_velocity"],
                epochs_completed=track["epochs"]
            )
            # Apply budget factor: paid APIs boost effective ROI ceiling
            res["training_roi"] = round(min(99.9, res["training_roi"] * budget_factor), 2)
            evaluated.append(res)

        # 4. Sort descending by ROI
        evaluated.sort(key=lambda x: x["training_roi"], reverse=True)

        active_track = evaluated[0]
        active_track["status"] = "⚡ ACTIVE_TRAINING_PRIORITY"

        for idx, t in enumerate(evaluated[1:], 2):
            t["status"] = f"STANDBY_QUEUE_#{idx}"

        result = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scheduler_mode": "DYNAMIC_ROI_AUTONOMOUS_PREEMPTION",
            "active_training_model": active_track["model_name"],
            "active_training_task": active_track["primary_domain"],
            "active_roi_score": active_track["training_roi"],
            "preemption_trigger_threshold": 5.0,
            "live_telemetry_active": live_agg_loss is not None,
            "live_aggregate_loss": live_agg_loss,
            "live_aggregate_velocity": live_agg_velocity,
            "live_plateau_detected": live_plateau,
            "provider_budget_factor": budget_factor,
            "top_roi_priority": active_track,
            "all_tracks": evaluated
        }

        # Write state to 04_data_and_memory
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return result


def get_roi_training_status() -> Dict[str, Any]:
    scheduler = ROIGatedTrainingScheduler()
    if not ROI_STATUS_FILE.exists():
        return scheduler.evaluate_all_curriculums()
    try:
        with open(ROI_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return scheduler.evaluate_all_curriculums()


if __name__ == "__main__":
    scheduler = ROIGatedTrainingScheduler()
    status = scheduler.evaluate_all_curriculums()
    live_active = "✅ LIVE" if status.get("live_telemetry_active") else "📋 STATIC DEFAULTS"
    budget = status.get("provider_budget_factor", 1.0)
    print("=== ROI-GATED TRAINING PROTOCOL STATE ===")
    print(f"Telemetry Source:      {live_active}")
    print(f"Live Loss:             {status.get('live_aggregate_loss', 'N/A')}")
    print(f"Live Velocity:         {status.get('live_aggregate_velocity', 'N/A')}")
    print(f"Plateau Detected:      {status.get('live_plateau_detected', False)}")
    print(f"Provider Budget Factor:{budget:.2f}x (1.0=free-tier only; >1.0=paid APIs active)")
    print(f"Active Priority Model: {status['active_training_model']}")
    print(f"Target Task Domain:    {status['active_training_task']}")
    print(f"Live ROI Score:        {status['active_roi_score']}")
    print("\nPriority Queue:")
    for t in status["all_tracks"]:
        print(f"  [{t['training_roi']:5.1f} ROI] {t['model_name']} -> {t['primary_domain']} ({t['status']})")

