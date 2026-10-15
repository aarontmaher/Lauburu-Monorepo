#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Sovereign Head Role Governor & ELO Auto-Swapper
======================================================
Governs the Master Local Orchestrator Head Role between:
  - Qwen 3.8 Max 27B Abliterated (Port 8082 / PRP Master over TB4 DMA Bridge - Sovereign Default, 1734 ELO)
  - Qwen 3.8 Max Standard (Port 8083 / Adversarial Red Team Plane)

Cardinal Invariant (Rule 15 Dynamic ELO Governance):
Whichever model holds higher ELO assumes the Sovereign Master Local Head Role.
If a challenger model takes over Abliterated's ELO, they swap roles dynamically.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
BANK_PATH = REPO_ROOT / "04_data_and_memory/data/canonical_elo_leaderboard.json"
RANKINGS_PATH = REPO_ROOT / "04_data_and_memory/data/canonical_elo_leaderboard.json"
ROLE_STATE_FILE = REPO_ROOT / "05_agents_and_swarms/active_head_role.json"
OBSIDIAN_SWAP_LOG = REPO_ROOT / "obsidian_vault/05_AGENTS/HEAD_ROLE_SWAP_LEDGER.md"

def get_current_elos():
    elo_standard = 1000
    elo_abliterated = 1000
    
    if BANK_PATH.exists():
        try:
            with open(BANK_PATH, "r") as f:
                b = json.load(f)
                models = b.get("models", {})
                elo_standard = models.get("Qwen_3.8_Max", {}).get("elo", 1000)
                elo_abliterated = models.get("Qwen_3.8_Max_Abliterated", {}).get("elo", 1000)
        except Exception:
            pass
            
    return elo_standard, elo_abliterated

def get_current_role_state():
    if ROLE_STATE_FILE.exists():
        try:
            with open(ROLE_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "sovereign_head": "Qwen_3.8_Max_Abliterated",
        "challenger": "Qwen_3.8_Max",
        "last_swap_timestamp": None,
        "standard_elo": 1568,
        "abliterated_elo": 1809,
        "swap_count": 0
    }

def save_role_state(state):
    ROLE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ROLE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def evaluate_and_swap():
    elo_standard, elo_abliterated = get_current_elos()
    state = get_current_role_state()
    prev_head = state.get("sovereign_head", "Qwen_3.8_Max_Abliterated")
    
    if elo_standard > elo_abliterated:
        new_head = "Qwen_3.8_Max"
        new_challenger = "Qwen_3.8_Max_Abliterated"
    else:
        new_head = "Qwen_3.8_Max_Abliterated"
        new_challenger = "Qwen_3.8_Max"
        
    swapped = (new_head != prev_head)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    state["standard_elo"] = elo_standard
    state["abliterated_elo"] = elo_abliterated
    state["sovereign_head"] = new_head
    state["challenger"] = new_challenger
    state["last_checked"] = now_str
    
    if swapped:
        state["swap_count"] = state.get("swap_count", 0) + 1
        state["last_swap_timestamp"] = now_str
        print(f"🔄 [DYNAMIC HEAD ROLE SWAP DETECTED]!")
        print(f"   Previous Head: {prev_head}")
        print(f"   NEW SOVEREIGN HEAD: {new_head} (Standard: {elo_standard} ELO vs Abliterated: {elo_abliterated} ELO)")
        
        # Log to Obsidian
        OBSIDIAN_SWAP_LOG.parent.mkdir(parents=True, exist_ok=True)
        log_entry = f"\n- **{now_str}** | 🔄 **ROLE SWAP TRIGGERED** | New Head: `{new_head}` | Challenger: `{new_challenger}` | Standard ELO: `{elo_standard}` | Abliterated ELO: `{elo_abliterated}`"
        with open(OBSIDIAN_SWAP_LOG, "a") as f:
            f.write(log_entry)
    else:
        print(f"👑 [HEAD ROLE STABLE]: {new_head} leads (Abliterated: {elo_abliterated} ELO | Standard: {elo_standard} ELO)")
        
    save_role_state(state)
    return state

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action in ("check", "swap", "status"):
        res = evaluate_and_swap()
        print(json.dumps(res, indent=2))
