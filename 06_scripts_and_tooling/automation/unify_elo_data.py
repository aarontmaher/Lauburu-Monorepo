import os
import json
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
SSOT_CANDIDATE = REPO_ROOT / "04_data_and_memory/data/ai_elo_leaderboard.json"
CANONICAL_PATH = REPO_ROOT / "04_data_and_memory/data/canonical_elo_leaderboard.json"

OTHER_FILES = [
    REPO_ROOT / "05_agents_and_swarms/elo_bank.json",
    REPO_ROOT / "05_agents_and_swarms/endless_pit/elo_rankings.json",
    REPO_ROOT / "04_data_and_memory/universal_elo_tracker.json"
]

def load_json(p):
    if p.exists():
        with open(p, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

# 1. Load base SSOT
if SSOT_CANDIDATE.exists():
    ssot = load_json(SSOT_CANDIDATE)
else:
    ssot = {"version": "4.0.0", "schema": "CATEGORIZED_SSOT_MULTI_TIER_ELO", "models": {}}

if "models" not in ssot:
    ssot["models"] = {}

# 2. Scrape models from other files and add if missing
for p in OTHER_FILES:
    data = load_json(p)
    
    if "elo_bank.json" in str(p):
        for k, v in data.items():
            if k not in ssot["models"]:
                ssot["models"][k] = {"elo": v, "tier": "LOCAL_MODEL", "tasks_scored": 0, "win_rate_pct": 50.0}
    elif "elo_rankings.json" in str(p):
        # Endless pit structure: {"global": {"Alpha_Qwen_Max": 1200...}, "domains": {...}}
        gl = data.get("global", {})
        for k, v in gl.items():
            if k != "total_battles" and k not in ssot["models"]:
                ssot["models"][k] = {"elo": v, "tier": "LOCAL_MODEL", "tasks_scored": 0, "win_rate_pct": 50.0}
    elif "universal_elo_tracker.json" in str(p):
        mods = data.get("models", {})
        for k, v in mods.items():
            if k not in ssot["models"]:
                ssot["models"][k] = {"elo": v, "tier": "LOCAL_MODEL", "tasks_scored": 0, "win_rate_pct": 50.0}

# 3. Save canonical
with open(CANONICAL_PATH, "w") as f:
    json.dump(ssot, f, indent=4)

print(f"✅ Unified {len(ssot['models'])} models into {CANONICAL_PATH}")
