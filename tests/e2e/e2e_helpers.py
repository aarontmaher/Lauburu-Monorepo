#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Helpers & Reference Implementation Models
Project: End-to-End Autonomous AI Training, Storage & RAM Mesh Engine
================================================================================
Authoritative Reference implementations, mathematical models, schema validators,
and invariant verifiers for all 20 features (F1 - F20) defined in PROJECT.md:

F1:  Autonomous 24/7 LoRA/DPO Training Pipeline
F2:  Bradley-Terry ELO Promotion Gate (>= 65% Win-Rate)
F3:  SWE-bench Evaluation Harness & Patch Generation
F4:  Canonical Tri-Vault Synchronization (Obsidian, PySpark, Git)
F5:  Isolated Git Worktree Lifecycle (.worktrees/<task_id>)
F6:  Automated Storage Self-Healing (10GB NVMe Disk Headroom Guarantee)
F7:  PySpark Semantic Deduplication (Qdrant Cosine >= 0.92, Entropy H >= 3.20)
F8:  Real-Time Dynamic RAM Watchdog (< 85% Host RAM Ceiling & User Elasticity)
F9:  PyTorch MPS Cache Purge & Dynamic Throttling (>= 80% Threshold)
F10: Dynamic 10Gbps TB4 DMA Layer Offload (< 0.30ms RTT)
F11: 7-Layer Distributed Mesh Sharding (Prima PRP, RPC, Petals, Exo)
F12: Edge Tokenization & Router Micro-SLM (<= 35MB Router RAM Limit)
F13: Dual-World Simulation Engine (AgentWorld-35B + WebWorld-32B)
F14: 30-Step Trajectory Rollout Interceptor
F15: Quantitative Admission Gating (S >= 0.90, P_reg <= 0.05, O_layout = 0, C_sim >= 0.85)
F16: Closed-Loop Auto-Rollback Watchdog (Loss divergence, memory leak, frame drops)
F17: Movesense 512Hz ECG & DSP Pipeline (Pan-Tompkins, PTT, DFA-alpha1, Rule #0)
F18: Triple-TUI Parity & Latency Benchmarks (Textual, Ratatui, React, < 50ms)
F19: Commercial Scalability & Shopify Storefront GraphQL
F20: E2E Acceptance & Adversarial Hardening
"""

from __future__ import annotations

import os
import re
import sys
import math
import json
import time
import shutil
import hashlib
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Any, Optional, Sequence, Union, Set

PROJECT_ROOT = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo')
LORA_DATASETS_ROOT = Path('/Users/aaron/DFS_UNIFIED/lora_datasets')
OBSIDIAN_VAULT_ROOT = PROJECT_ROOT / 'obsidian_vault'
DATA_AND_MEMORY_ROOT = PROJECT_ROOT / '04_data_and_memory'

CANONICAL_MODULES = [
    '00_core_infrastructure',
    '01_apps',
    '02_ai_models_and_inference',
    '03_biometrics_and_telemetry',
    '04_data_and_memory',
    '05_agents_and_swarms',
    '06_scripts_and_tooling',
    '07_docs_and_architecture',
    '08_business_and_commerce',
    '09_app_store_and_release',
    '10_spatial_grappling_kinematics',
    '11_security_and_governance',
    '12_continuous_lora_evolution'
]

REQUIRED_OBSIDIAN_WIKILINKS = [
    "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
    "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
    "[[Index]]"
]

HARDWARE_MESH_MATRIX = {
    "L1": {"name": "Mac_Node", "ip": "192.168.8.230", "tailscale_ip": "100.119.199.76", "ram_gb": 24.0, "ai_cap_gb": 21.6, "cap_pct": 90.0, "role": "Host & Memory Governor"},
    "L2": {"name": "MacBook_Pro", "ip": "192.168.8.127", "tailscale_ip": "100.103.212.21", "tb4_ip": "169.254.187.138", "ram_gb": 16.0, "ai_cap_gb": 14.0, "cap_pct": 90.0, "role": "TB4 Metal Worker"},
    "L3": {"name": "Linux_Head_Node", "ip": "192.168.8.224", "tailscale_ip": "100.101.39.98", "ram_gb": 16.0, "ai_cap_gb": 13.8, "cap_pct": 80.0, "role": "Compute Hub & Ray"},
    "L4": {"name": "Linux_Tablet", "ip": "DHCP", "tailscale_ip": "100.81.92.125", "ram_gb": 8.0, "ai_cap_gb": 6.5, "cap_pct": 75.0, "role": "Mobile DSP"},
    "L5": {"name": "MacBook_Air", "ip": "192.168.8.222", "tailscale_ip": "100.93.158.96", "ram_gb": 16.0, "ai_cap_gb": 14.0, "cap_pct": 90.0, "role": "Metal LoRA Distillation"},
    "L6": {"name": "Pixel_10_Pro_XL", "ip": "DHCP", "tailscale_ip": "100.73.38.87", "ram_gb": 16.0, "ai_cap_gb": 12.5, "cap_pct": 85.0, "role": "Tensor G5 TPU & Vision"},
    "L7": {"name": "Samsung_S20", "ip": "DHCP", "tailscale_ip": "100.84.40.95", "ram_gb": 12.0, "ai_cap_gb": 9.0, "cap_pct": 75.0, "role": "Automated UI Tester"},
    "GW": {"name": "GL_iNet_Router", "ip": "192.168.8.1", "tailscale_ip": "100.122.185.123", "ram_gb": 0.512, "ai_cap_gb": 0.035, "cap_pct": 100.0, "role": "Core Gateway & Hardware ADB"}
}


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_canonical_modules() -> List[str]:
    return CANONICAL_MODULES


# ============================================================================
# F1: AUTONOMOUS 24/7 LORA/DPO TRAINING PIPELINE HELPERS
# ============================================================================

def validate_dpo_sample_schema(sample: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates Hugging Face DPO / RLHF instruction pair schema."""
    errors = []
    if not isinstance(sample, dict):
        return False, ["Sample must be a JSON dictionary"]
    
    # Check DPO schema (prompt, chosen, rejected) or SFT schema (instruction, output)
    is_dpo = "prompt" in sample and "chosen" in sample and "rejected" in sample
    is_sft = ("instruction" in sample or "prompt" in sample) and ("output" in sample or "response" in sample)
    
    if not (is_dpo or is_sft):
        errors.append("Sample must adhere to either DPO (prompt, chosen, rejected) or SFT (instruction, output) schema")
        
    if is_dpo:
        for k in ["prompt", "chosen", "rejected"]:
            val = sample.get(k)
            if not isinstance(val, (str, list, dict)) or (isinstance(val, str) and len(val.strip()) == 0):
                errors.append(f"DPO field '{k}' must be non-empty")
                
    return len(errors) == 0, errors


def simulate_lora_epoch_loss(initial_loss: float, epoch: int, learning_rate: float = 2e-4) -> float:
    """Computes mathematical reference loss decay curve for QLoRA fine-tuning."""
    decay = math.exp(-0.45 * epoch)
    final_loss = round(initial_loss * decay + (0.12 * (1.0 - decay)), 4)
    return max(0.01, final_loss)


def check_free_tier_quota_limits(gemini_rpm: int, gemini_rpd: int, cf_neurons: int) -> Tuple[bool, Dict[str, Any]]:
    """Verifies that automated cron calls adhere strictly to free-tier quotas."""
    gemini_rpm_safe = gemini_rpm <= 14  # Safety cap below 15 RPM
    gemini_rpd_safe = gemini_rpd <= 1400  # Safety cap below 1,500 RPD
    cf_neurons_safe = cf_neurons <= 10000  # Free tier daily limit
    
    all_safe = gemini_rpm_safe and gemini_rpd_safe and cf_neurons_safe
    return all_safe, {
        "gemini_rpm": gemini_rpm,
        "gemini_rpm_safe": gemini_rpm_safe,
        "gemini_rpd": gemini_rpd,
        "gemini_rpd_safe": gemini_rpd_safe,
        "cf_neurons": cf_neurons,
        "cf_neurons_safe": cf_neurons_safe,
        "is_compliant": all_safe
    }


# ============================================================================
# F2: BRADLEY-TERRY ELO PROMOTION GATE HELPERS
# ============================================================================

def calculate_bradley_terry_win_prob(rating_a: float, rating_b: float) -> float:
    """
    Computes exact Bradley-Terry pairwise win probability:
    P(A > B) = 1 / (1 + 10^((R_B - R_A) / 400))
    """
    exponent = (rating_b - rating_a) / 400.0
    return 1.0 / (1.0 + math.pow(10.0, exponent))


def update_elo_ratings(rating_a: float, rating_b: float, outcome: float, k_factor: float = 32.0) -> Tuple[float, float]:
    """
    Updates ELO ratings based on match outcome (1.0 = A wins, 0.5 = draw, 0.0 = B wins).
    """
    expected_a = calculate_bradley_terry_win_prob(rating_a, rating_b)
    expected_b = 1.0 - expected_a
    new_a = round(rating_a + k_factor * (outcome - expected_a), 2)
    new_b = round(rating_b + k_factor * ((1.0 - outcome) - expected_b), 2)
    return new_a, new_b


def evaluate_promotion_gate(candidate_wins: int, total_battles: int, min_win_rate: float = 0.65) -> Tuple[bool, float, str]:
    """Evaluates candidate model promotion with >=65% win-rate threshold."""
    if total_battles <= 0:
        return False, 0.0, "NO_BATTLES_EVALUATED"
    win_rate = float(candidate_wins) / float(total_battles)
    promoted = win_rate >= min_win_rate
    status = "PROMOTED_TO_PRODUCTION" if promoted else "REJECTED_BELOW_THRESHOLD"
    return promoted, round(win_rate, 4), status


# ============================================================================
# F3: SWE-BENCH EVALUATION HARNESS HELPERS
# ============================================================================

def validate_swe_bench_task_schema(task: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates SWE-bench task definition."""
    errors = []
    required_keys = ["instance_id", "repo", "problem_statement", "golden_test"]
    for rk in required_keys:
        if rk not in task or not task[rk]:
            errors.append(f"Missing required SWE-bench field: {rk}")
    return len(errors) == 0, errors


def evaluate_swe_patch_syntax(patch_diff: str) -> Tuple[bool, Dict[str, Any]]:
    """Evaluates unified diff patch syntax for SWE-bench execution."""
    if not patch_diff or len(patch_diff.strip()) == 0:
        return False, {"error": "Empty patch content", "hunks": 0}
    
    lines = patch_diff.splitlines()
    has_header = any(l.startswith("---") or l.startswith("diff --git") for l in lines)
    hunk_count = sum(1 for l in lines if l.startswith("@@"))
    additions = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    
    valid = has_header and hunk_count > 0
    return valid, {
        "valid": valid,
        "hunks": hunk_count,
        "additions": additions,
        "deletions": deletions
    }


# ============================================================================
# F4: CANONICAL TRI-VAULT STORAGE SYNCHRONIZATION HELPERS
# ============================================================================

def is_storage_healthy(project_root: Optional[Path] = None) -> Tuple[bool, Dict[str, Any]]:
    """Validates the Tri-Vault storage invariants (<3ms fast-path)."""
    root = project_root or PROJECT_ROOT
    obs_dir = root / 'obsidian_vault'
    lora_dir = LORA_DATASETS_ROOT
    data_mem_dir = root / '04_data_and_memory'
    
    obsidian_ok = obs_dir.is_dir()
    pyspark_ok = lora_dir.is_dir() or data_mem_dir.is_dir()
    
    try:
        free_bytes = shutil.disk_usage(str(root)).free
        disk_free_gb = free_bytes / (1024 ** 3)
    except Exception:
        disk_free_gb = 0.0
        
    git_ok = (root / '.git').exists()
    no_lock = not (root / '.git' / 'index.lock').exists()
    
    healthy = obsidian_ok and pyspark_ok and (disk_free_gb >= 5.0) and git_ok and no_lock
    return healthy, {
        'obsidian_ok': obsidian_ok,
        'pyspark_ok': pyspark_ok,
        'disk_free_gb': round(disk_free_gb, 2),
        'git_ok': git_ok,
        'no_index_lock': no_lock,
        'is_healthy': healthy
    }


def validate_obsidian_master_index(index_path: Path) -> Tuple[bool, List[str]]:
    """Validates Obsidian master index frontmatter and canonical wikilinks."""
    errors = []
    if not index_path.exists() or index_path.stat().st_size == 0:
        return False, ["Obsidian Index.md does not exist or is empty"]
    
    try:
        content = index_path.read_text(encoding='utf-8')
    except Exception as e:
        return False, [f"Failed to read Index.md: {e}"]
        
    for req_link in REQUIRED_OBSIDIAN_WIKILINKS:
        if req_link not in content:
            errors.append(f"Missing required master wikilink: {req_link}")
            
    return len(errors) == 0, errors


# ============================================================================
# F5: ISOLATED GIT WORKTREE LIFECYCLE HELPERS
# ============================================================================

def validate_worktree_path_isolation(worktree_path: Path, repo_root: Path) -> Tuple[bool, str]:
    """Validates that a worktree path is properly isolated and sandboxed."""
    try:
        resolved_wt = worktree_path.resolve()
        resolved_root = repo_root.resolve()
        if resolved_wt == resolved_root:
            return False, "Worktree path cannot be the repository root"
        return True, "Path is isolated"
    except Exception as e:
        return False, str(e)


# ============================================================================
# F6: AUTOMATED STORAGE SELF-HEALING HELPERS
# ============================================================================

def self_heal_tri_vault_invariants(target_root: Path, lora_root: Optional[Path] = None) -> Dict[str, Any]:
    """Performs idempotent self-healing of Tri-Vault directories and index files."""
    healed_items = []
    
    obsidian_dir = target_root / "obsidian_vault"
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    healed_items.append(str(obsidian_dir))
    
    lora_dir = lora_root or (target_root / "04_data_and_memory")
    lora_dir.mkdir(parents=True, exist_ok=True)
    healed_items.append(str(lora_dir))
    
    data_mem = target_root / "04_data_and_memory"
    data_mem.mkdir(parents=True, exist_ok=True)
    healed_items.append(str(data_mem))
    
    # Heal Index.md if missing
    index_file = obsidian_dir / "Index.md"
    if not index_file.exists() or index_file.stat().st_size == 0:
        index_content = """---
title: "Lauburu AI Monorepo - Master Knowledge Graph"
tags: [lauburu, root, master_index, swarm, ai_debate]
---
# 🧠 Lauburu AI Monorepo - Master Knowledge Vault
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[Index]]
"""
        index_file.write_text(index_content, encoding='utf-8')
        healed_items.append(str(index_file))
        
    return {
        "status": "HEALED",
        "healed_count": len(healed_items),
        "healed_items": healed_items
    }


# ============================================================================
# F7: PYSPARK SEMANTIC DEDUPLICATION & SHANNON ENTROPY HELPERS
# ============================================================================

def calculate_shannon_entropy(text: str) -> float:
    """Calculates byte/character-level Shannon Entropy H(X) = -sum(p_i * log2(p_i))."""
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    
    n = float(len(text))
    entropy = 0.0
    for count in freq.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def compute_cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Computes cosine similarity between two numeric embedding vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return round(dot / (norm_a * norm_b), 6)


# ============================================================================
# F8 & F9: REAL-TIME DYNAMIC RAM GOVERNOR & MPS PURGE HELPERS
# ============================================================================

def compute_user_aware_elasticity(ram_used_pct: float, user_idle_sec: float) -> Tuple[float, str, float, float]:
    """
    Adaptive User-Aware Dynamic VRAM Elasticity:
    - User Active (idle < 60s): Interactive Mode (Throttles background compute, strict 75% cap).
    - User Idle (idle >= 60s): Maximum Burst Mode (Unthrottled 88% cap for overnight training).
    Returns (throttle_factor, mode_name, active_warn_pct, active_crit_pct).
    """
    is_user_active = user_idle_sec < 60.0
    mode = "INTERACTIVE_USER_ACTIVE" if is_user_active else "MAXIMUM_BURST_IDLE"

    active_warn = 65.0 if is_user_active else 82.0
    active_crit = 75.0 if is_user_active else 88.0

    if ram_used_pct < active_warn:
        base_throttle = 0.5 if is_user_active else 1.0
    elif ram_used_pct < active_crit:
        base_throttle = 0.2 if is_user_active else 0.5
    else:
        base_throttle = 0.05 if is_user_active else 0.1

    return base_throttle, mode, active_warn, active_crit


def evaluate_memory_pressure_state(ram_pct: float, warn_pct: float = 80.0, crit_pct: float = 85.0) -> Dict[str, Any]:
    """Evaluates RAM pressure state and determines governance action."""
    if ram_pct >= crit_pct:
        status = "CRITICAL_HEADROOM"
        action = "PURGE_AND_THROTTLE"
        throttle_factor = 0.50
    elif ram_pct >= warn_pct:
        status = "WARNING_HEADROOM"
        action = "MPS_CACHE_PURGE"
        throttle_factor = 0.80
    else:
        status = "HEALTHY"
        action = "NONE"
        throttle_factor = 1.00
        
    return {
        "ram_pct": ram_pct,
        "status": status,
        "action": action,
        "throttle_factor": throttle_factor,
        "is_safe": ram_pct < crit_pct
    }


# ============================================================================
# F10: DYNAMIC TB4 LAYER OFFLOAD HELPERS
# ============================================================================

def partition_model_layers_for_tb4(total_layers: int, host_ram_pct: float, tb4_available: bool = True) -> Dict[str, Any]:
    """Calculates tensor layer partition between Host (L1) and MacBook Pro (L2) over TB4."""
    if not tb4_available or host_ram_pct < 80.0:
        return {
            "host_layers": list(range(total_layers)),
            "offloaded_layers": [],
            "offload_pct": 0.0,
            "target_node": "L1_HOST_ONLY"
        }
        
    # Scale offloaded layers dynamically based on pressure
    if host_ram_pct >= 90.0:
        offload_ratio = 0.60
    elif host_ram_pct >= 85.0:
        offload_ratio = 0.40
    else:
        offload_ratio = 0.25
        
    offload_count = int(math.ceil(total_layers * offload_ratio))
    host_count = total_layers - offload_count
    
    return {
        "host_layers": list(range(host_count)),
        "offloaded_layers": list(range(host_count, total_layers)),
        "offload_pct": round(offload_ratio * 100.0, 1),
        "target_node": "L2_MACBOOK_PRO_TB4"
    }


# ============================================================================
# F11: 7-LAYER DISTRIBUTED MESH SHARDING HELPERS
# ============================================================================

def compute_mesh_routing_cost(node_id: str, payload_tokens: int, node_health: float, node_latency_ms: float) -> float:
    """Computes Dijkstra cost objective with health penalty for distributed sharding."""
    if node_health <= 0.0:
        return float('inf')
    base_cost = (payload_tokens / 100.0) + node_latency_ms
    health_multiplier = 1.0 / max(0.01, node_health)
    return round(base_cost * health_multiplier, 4)


# ============================================================================
# F12: EDGE TOKENIZATION & ROUTER SLM HELPERS
# ============================================================================

def validate_router_ram_safety(router_ram_used_mb: float, max_limit_mb: float = 35.0) -> Tuple[bool, Dict[str, Any]]:
    """Verifies that GL-MT3600BE Router RAM does not exceed 35MB safety ceiling."""
    is_safe = router_ram_used_mb <= max_limit_mb
    return is_safe, {
        "router_ram_used_mb": router_ram_used_mb,
        "max_limit_mb": max_limit_mb,
        "is_safe": is_safe
    }


# ============================================================================
# F13, F14, F15: DUAL-WORLD SIMULATION & ADMISSION GATING HELPERS
# ============================================================================

@dataclass
class SimulationTrajectoryMetrics:
    success_score: float
    regression_probability: float
    layout_overflow_count: int
    simulation_confidence: float
    step_count: int = 30


def evaluate_admission_gating(metrics: SimulationTrajectoryMetrics) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Evaluates 30-step simulation trajectory against quantitative thresholds:
    - S >= 0.90
    - P_reg <= 0.05
    - O_layout == 0
    - C_sim >= 0.85
    """
    pass_s = metrics.success_score >= 0.90
    pass_preg = metrics.regression_probability <= 0.05
    pass_layout = metrics.layout_overflow_count == 0
    pass_conf = metrics.simulation_confidence >= 0.85
    
    admitted = pass_s and pass_preg and pass_layout and pass_conf
    verdict = "ADMITTED" if admitted else "REJECTED"
    
    return admitted, verdict, {
        "success_score": metrics.success_score,
        "pass_success": pass_s,
        "regression_probability": metrics.regression_probability,
        "pass_regression": pass_preg,
        "layout_overflow_count": metrics.layout_overflow_count,
        "pass_layout": pass_layout,
        "simulation_confidence": metrics.simulation_confidence,
        "pass_confidence": pass_conf,
        "step_count": metrics.step_count,
        "verdict": verdict
    }


# ============================================================================
# F16: CLOSED-LOOP AUTO-ROLLBACK WATCHDOG HELPERS
# ============================================================================

def detect_training_anomaly(loss_history: List[float], max_loss_delta: float = 2.0) -> Tuple[bool, str]:
    """Detects loss divergence (NaN, Inf, or sudden spike)."""
    if not loss_history:
        return False, "EMPTY_HISTORY"
    
    for val in loss_history:
        if math.isnan(val) or math.isinf(val):
            return True, "LOSS_CONTAINS_NAN_OR_INF"
            
    if len(loss_history) >= 2:
        last = loss_history[-1]
        prev = loss_history[-2]
        if last - prev > max_loss_delta:
            return True, f"LOSS_SPIKE_DETECTED ({prev} -> {last})"
            
    return False, "NORMAL_TRAINING"


# ============================================================================
# F17: REFERENCE BIOMETRICS DSP & CARDIORESPIRATORY MATH
# ============================================================================

def generate_synthetic_synthetic_ecg_beat(fs: int = 512, bpm: float = 60.0, duration_sec: float = 5.0) -> List[float]:
    """Generates a reference physiological ECG waveform for algorithm verification."""
    total_samples = int(fs * duration_sec)
    signal = [0.0] * total_samples
    samples_per_beat = int((60.0 / bpm) * fs)
    
    for b_start in range(int(0.2 * fs), total_samples - samples_per_beat, samples_per_beat):
        p_peak = b_start + int(0.12 * fs)
        q_peak = b_start + int(0.18 * fs)
        r_peak = b_start + int(0.20 * fs)
        s_peak = b_start + int(0.22 * fs)
        t_peak = b_start + int(0.35 * fs)
        
        for i in range(max(0, b_start), min(total_samples, b_start + samples_per_beat)):
            p_val = 0.15 * math.exp(-((i - p_peak) ** 2) / (2 * (0.02 * fs) ** 2))
            q_val = -0.15 * math.exp(-((i - q_peak) ** 2) / (2 * (0.01 * fs) ** 2))
            r_val = 1.50 * math.exp(-((i - r_peak) ** 2) / (2 * (0.012 * fs) ** 2))
            s_val = -0.25 * math.exp(-((i - s_peak) ** 2) / (2 * (0.01 * fs) ** 2))
            t_val = 0.30 * math.exp(-((i - t_peak) ** 2) / (2 * (0.04 * fs) ** 2))
            signal[i] += (p_val + q_val + r_val + s_val + t_val)
            
    return signal


def reference_pan_tompkins_qrs(ecg_signal: Sequence[float], fs: int = 512) -> Tuple[List[int], List[float]]:
    """Reference Pan-Tompkins 1985 implementation."""
    if not ecg_signal or len(ecg_signal) < int(fs * 0.5):
        return [], []
    
    n = len(ecg_signal)
    filtered = [0.0] * n
    for i in range(2, n - 2):
        filtered[i] = ecg_signal[i] - 0.5 * (ecg_signal[i - 2] + ecg_signal[i + 2])
        
    deriv = [0.0] * n
    scale = fs / 8.0
    for i in range(2, n - 2):
        deriv[i] = (-filtered[i - 2] - 2.0 * filtered[i - 1] + 2.0 * filtered[i + 1] + filtered[i + 2]) * scale / fs
        
    squared = [x * x for x in deriv]
    mwi_win = max(2, int(0.150 * fs))
    mwi = [0.0] * n
    curr_sum = sum(squared[:min(mwi_win, n)])
    for i in range(n):
        if i >= mwi_win:
            curr_sum += squared[i] - squared[i - mwi_win]
        elif i > 0:
            curr_sum += squared[i]
        mwi[i] = curr_sum / float(min(i + 1, mwi_win))
        
    threshold = max(mwi) * 0.30 if mwi else 0.0
    peaks = []
    refractory = int(0.200 * fs)
    last_p = -refractory
    
    for i in range(1, n - 1):
        if mwi[i] > threshold and mwi[i] > mwi[i - 1] and mwi[i] >= mwi[i + 1]:
            if i - last_p >= refractory:
                s_start = max(0, i - mwi_win)
                s_end = min(n, i + mwi_win)
                r_apex = max(range(s_start, s_end), key=lambda idx: ecg_signal[idx])
                peaks.append(r_apex)
                last_p = r_apex
                
    rr_intervals = []
    for i in range(1, len(peaks)):
        rr_ms = ((peaks[i] - peaks[i - 1]) / float(fs)) * 1000.0
        if 250.0 <= rr_ms <= 2200.0:
            rr_intervals.append(round(rr_ms, 1))
            
    return peaks, rr_intervals


def reference_kamath_artifact_filter(rr_intervals: Sequence[float], threshold_pct: float = 20.0) -> Tuple[List[float], int]:
    """Kamath 2004 20% clinical RR artifact filter."""
    if not rr_intervals or len(rr_intervals) < 2:
        return [float(x) for x in (rr_intervals or [])], 0
        
    thresh = threshold_pct / 100.0
    cleaned = [float(rr_intervals[0])]
    artifacts = 0
    
    for i in range(1, len(rr_intervals)):
        prev = cleaned[-1]
        curr = float(rr_intervals[i])
        if prev > 0 and (abs(curr - prev) / prev) <= thresh:
            cleaned.append(curr)
        else:
            artifacts += 1
            cleaned.append(prev)
            
    return cleaned, artifacts


def reference_calculate_rmssd(rr_intervals: Sequence[float]) -> Optional[float]:
    if not rr_intervals or len(rr_intervals) < 2:
        return None
    diffs = [float(rr_intervals[i]) - float(rr_intervals[i - 1]) for i in range(1, len(rr_intervals))]
    sum_sq = sum(d * d for d in diffs)
    return round(math.sqrt(sum_sq / float(len(rr_intervals) - 1)), 2)


def reference_calculate_ptt_bp(ptt_ms: Optional[float], hr_bpm: Optional[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Reference Hemodynamic PTT Blood Pressure Inversion formula."""
    if ptt_ms is None or (isinstance(ptt_ms, (int, float)) and math.isnan(ptt_ms)) or ptt_ms <= 0:
        return None, None, None
    delta_ptt = 200.0 - float(ptt_ms)
    hr_adj = ((float(hr_bpm) - 70.0) * 0.15) if (hr_bpm and not math.isnan(hr_bpm)) else 0.0
    sbp = round(max(80.0, min(220.0, 120.0 + (delta_ptt * 0.45) + hr_adj)), 1)
    dbp = round(max(50.0, min(130.0, 80.0 + (delta_ptt * 0.25) + (hr_adj * 0.5))), 1)
    map_val = round((sbp + 2.0 * dbp) / 3.0, 1)
    return sbp, dbp, map_val


# ============================================================================
# F18: TRIPLE-TUI PARITY & A11Y CONTRAST HELPERS
# ============================================================================

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def relative_luminance(r: int, g: int, b: int) -> float:
    def srgb_to_lin(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def calculate_contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculates WCAG 2.1 contrast ratio between two hex colors."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    l1 = relative_luminance(r1, g1, b1)
    l2 = relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


# ============================================================================
# F19: SHOPIFY STOREFRONT GRAPHQL & MEMBERSHIP AUTH HELPERS
# ============================================================================

def validate_shopify_customer_query(query_str: str) -> Tuple[bool, List[str]]:
    """Validates Storefront GraphQL customer query structure."""
    errors = []
    if not query_str or "customer" not in query_str:
        errors.append("Query does not contain customer field")
    if "accessToken" not in query_str and "customerAccessToken" not in query_str:
        errors.append("Query lacks customerAccessToken argument")
    return len(errors) == 0, errors


def generate_mock_jwt_membership_token(user_id: str, tier: str = "PRO", expiry_sec: int = 3600) -> str:
    """Generates verifiable headless membership token representation."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "tier": tier,
        "exp": int(time.time()) + expiry_sec,
        "mesh_access": True
    }
    encoded = f"{json.dumps(header)}.{json.dumps(payload)}"
    sig = hashlib.sha256(encoded.encode()).hexdigest()[:16]
    return f"eyJ_{hashlib.md5(user_id.encode()).hexdigest()[:10]}.{sig}"


# ============================================================================
# ADDITIONAL COMMON E2E TEST UTILITIES & SCHEMAS
# ============================================================================

def validate_pwa_manifest(manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    required = ["name", "short_name", "start_url", "display", "icons"]
    for k in required:
        if k not in manifest:
            errors.append(f"Missing required manifest field: {k}")
    return len(errors) == 0, errors


def parse_grappling_opml(opml_content: str) -> List[Dict[str, Any]]:
    if not opml_content or "<opml" not in opml_content:
        return []
    try:
        root = ET.fromstring(opml_content)
        body = root.find("body")
        if body is None:
            return []
        nodes = []
        for outline in body.findall(".//outline"):
            text = outline.get("text", "")
            if text:
                nodes.append({"text": text, "category": outline.get("category", "General")})
        return nodes
    except Exception:
        return []


def generate_synthetic_synthetic_ecg_beat(fs: float = 512.0, hr_bpm: float = 60.0) -> List[float]:
    samples = int(fs * (60.0 / hr_bpm))
    beat = [0.0] * samples
    r_idx = samples // 3
    for i in range(samples):
        dt = (i - r_idx) / (fs * 0.02)
        beat[i] = round(1.2 * math.exp(-0.5 * dt * dt), 4)
    return beat


def reference_uth_sorensen_vo2max(hr_max: float, hr_rest: float) -> float:
    if hr_rest <= 0:
        return 0.0
    return round(15.3 * (hr_max / hr_rest), 2)


def validate_tactical_objective_schema(obj: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    for k in ["id", "title", "status"]:
        if k not in obj:
            errors.append(f"Missing objective field: {k}")
    return len(errors) == 0, errors


VALID_GAME_MODES = ["tactical", "duel", "coop", "sandbox"]
