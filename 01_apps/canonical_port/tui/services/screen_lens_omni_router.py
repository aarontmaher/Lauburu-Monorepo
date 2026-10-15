import re
import json
import os
import time

class ScreenLensOmniRouter:
    """
    Omniscient Router & Universal ELO Engine - Acts as the master traffic controller.
    Analyzes intent and dynamically routes to the exact right specialist behind the scenes,
    while continually adjusting ELO scores based on direct evidence of functionality.
    """
    ELO_DB_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/elo_leaderboard.json"

    def __init__(self):
        self.elo_scores = self._load_elo_db()
        self._ensure_baselines()

    def _load_elo_db(self):
        if os.path.exists(self.ELO_DB_PATH):
            try:
                with open(self.ELO_DB_PATH, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_elo_db(self):
        os.makedirs(os.path.dirname(self.ELO_DB_PATH), exist_ok=True)
        with open(self.ELO_DB_PATH, "w") as f:
            json.dump(self.elo_scores, f, indent=4)

    def _ensure_baselines(self):
        baselines = {
            "sovereign_orchestrator_max": 1800,
            "syntax_worker_coder": 1600,
            "red_team_abliterated": 1700,
            "lens_vision_native": 1500,
            "cloud_agy_tools": 1400,
            "skill_loop": 1500,
            "skill_ai_debate": 1500
        }
        for k, v in baselines.items():
            if k not in self.elo_scores:
                self.elo_scores[k] = {"elo": v, "matches": 0, "success_rate": 1.0, "latency_avg": 0.0}
        self._save_elo_db()

    def route_intent(self, prompt: str) -> str:
        """
        Analyzes the prompt and dynamically routes it to the specialist with the highest ELO
        for that specific category.
        """
        lower_prompt = prompt.lower()
        
        # Determine category
        if any(w in lower_prompt for w in ["look at", "see", "screen", "vision", "screenshot", "read this image"]):
            category_candidates = ["lens_vision_native"]
        elif any(w in lower_prompt for w in ["security", "validate", "check", "vulnerability", "hack", "bypass", "red team", "audit"]):
            category_candidates = ["red_team_abliterated"]
        elif any(w in lower_prompt for w in ["syntax", "fix", "parse", "format", "lint", "typo", "refactor"]):
            category_candidates = ["syntax_worker_coder", "sovereign_orchestrator_max"]
        elif any(w in lower_prompt for w in ["search", "internet", "openrouter", "api", "research", "download", "find"]):
            category_candidates = ["cloud_agy_tools"]
        else:
            category_candidates = ["sovereign_orchestrator_max", "cloud_agy_tools"]
            
        # Select highest ELO candidate in category
        best_candidate = category_candidates[0]
        best_elo = -1
        for candidate in category_candidates:
            score = self.elo_scores.get(candidate, {}).get("elo", 1500)
            if score > best_elo:
                best_elo = score
                best_candidate = candidate
                
        return best_candidate

    def report_outcome(self, entity_name: str, success: bool, latency_ms: float):
        """
        Direct evidence feedback loop. Adjusts ELO based on success/fail and speed.
        """
        if entity_name not in self.elo_scores:
            self.elo_scores[entity_name] = {"elo": 1500, "matches": 0, "success_rate": 1.0, "latency_avg": 0.0}
            
        stats = self.elo_scores[entity_name]
        
        # Calculate new ELO (K-factor 32)
        # Expected score is roughly 0.8 against environment baseline
        expected = 0.8 
        actual = 1.0 if success else 0.0
        
        # Apply penalty for high latency if successful
        if success and latency_ms > 5000:
            actual = 0.7  # Partial win due to speed penalty
            
        elo_change = int(32 * (actual - expected))
        
        stats["elo"] += elo_change
        stats["matches"] += 1
        
        # Update running averages
        old_rate = stats["success_rate"]
        stats["success_rate"] = ((old_rate * (stats["matches"] - 1)) + actual) / stats["matches"]
        
        old_lat = stats["latency_avg"]
        stats["latency_avg"] = ((old_lat * (stats["matches"] - 1)) + latency_ms) / stats["matches"]
        
        self._save_elo_db()
        return elo_change

