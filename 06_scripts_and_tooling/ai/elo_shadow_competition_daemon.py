#!/usr/bin/env python3
"""
ELO Shadow Competition Daemon (Rule 15 Enforcer)
Includes explicit real-world task categories for evaluation, including
the new "Agentic Architecting" category.
"""

import json
import math
import os
import urllib.request
from dataclasses import dataclass
from typing import Optional

MONOREPO_ROOT = os.environ.get("LAUBURU_MONOREPO_ROOT", "/Volumes/Lauburu-Monorepo")
LEADERBOARD_PATH = os.path.join(MONOREPO_ROOT, "04_data_and_memory/data/empirical_leaderboard.json")

@dataclass
class CompetitionStats:
    model_name: str
    tasks_completed: int = 0
    wins: int = 0
    
    @property
    def win_rate(self) -> Optional[float]:
        return self.wins / self.tasks_completed if self.tasks_completed > 0 else None

def calculate_confidence_interval(wins: int, n: int, z_score: float = 2.576) -> Optional[float]:
    if n <= 0:
        return None
    p = wins / n
    denominator = 1 + z_score**2 / n
    centre_adj = p + z_score**2 / (2 * n)
    variance = z_score * math.sqrt((p * (1 - p) + z_score**2 / (4 * n)) / n)
    return (centre_adj - variance) / denominator

def probe_endpoint(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def run_shadow_competition():
    incumbent = "Huihui-Qwen3.8-27B-Abliterated"
    challenger = "Hermes-3-Llama-3.1-8B"
    
    print("⚔️ ELO SHADOW COMPETITION AUDITOR (ZERO-MOCK MODE) ⚔️\n")
    incumbent_online = probe_endpoint("http://100.121.247.8:8082/health")
    challenger_online = probe_endpoint("http://100.119.199.76:8080/health")
    print(f"Incumbent ({incumbent} @ L8:8082): {'ONLINE' if incumbent_online else 'DISCONNECTED'}")
    print(f"Challenger ({challenger} @ L1:8080): {'ONLINE' if challenger_online else 'DISCONNECTED'}")
    print("-" * 80)

    if not os.path.exists(LEADERBOARD_PATH):
        print(json.dumps({
            "status": "DISCONNECTED",
            "reason": f"Empirical leaderboard not found at {LEADERBOARD_PATH}",
            "win_rate": None,
            "confidence_lower_bound": None
        }, indent=2))
        return

    try:
        with open(LEADERBOARD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(json.dumps({
            "status": "DISCONNECTED",
            "reason": str(exc),
            "win_rate": None,
            "confidence_lower_bound": None
        }, indent=2))
        return

    models = data.get("models", data if isinstance(data, list) else [])
    if not models:
        print(json.dumps({
            "status": "DISCONNECTED",
            "reason": "No empirical competition records found.",
            "win_rate": None,
            "confidence_lower_bound": None
        }, indent=2))
        return

    for entry in models:
        if isinstance(entry, dict):
            name = entry.get("model") or entry.get("name") or "unknown"
            wins = int(entry.get("wins", 0) or 0)
            total = int(entry.get("matches", entry.get("tasks_completed", 0)) or 0)
            elo = entry.get("elo")
            ci = calculate_confidence_interval(wins, total)
            wr = f"{(wins / total) * 100:.1f}%" if total > 0 else "--"
            ci_str = f"{ci * 100:.1f}%" if ci is not None else "--"
            print(f"Model: {name} | ELO: {elo if elo is not None else '--'} | Tasks: {total} | Win Rate: {wr} | 99% CI Lower Bound: {ci_str}")

if __name__ == "__main__":
    run_shadow_competition()
