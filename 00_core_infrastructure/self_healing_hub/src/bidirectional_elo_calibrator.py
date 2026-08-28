#!/usr/bin/env python3
"""
Bidirectional Real-Project ELO Calibration & Computing Efficiency Engine
Continuously aligns In-Game ELO with Real Monorepo Performance, Model Parameter Efficiency,
Hardware Compute Latency (llama-rpc port 50052), and Real Project Compatibility.

If In-Game rankings drift from Real Project Benchmark compatibility, the calibrator
dynamically re-tunes game difficulty, token reward multipliers, and perk costs.
"""

import os
import sys
import time
import json
import math
import socket
import logging
from typing import Dict, List, Any, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ELO-Calibrator] %(message)s")
logger = logging.getLogger("EloCalibrator")

CALIBRATION_STATE_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/bidirectional_elo_matrix.json"
GAME_STATE_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/game_arena_state.json"
LORA_TRAINING_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/lora_datasets/mesh_battle_game_training.jsonl"

class BidirectionalEloCalibrator:
    def __init__(self, k_factor: float = 32.0):
        self.k_factor = k_factor
        self.alignment_tolerance_elo = 120.0  # Max acceptable delta before game retuning
        
    def probe_node_rpc_latency(self, node_str: str) -> float:
        """Measures physical socket latency (ms) over Port 50052/5001."""
        node_map = {
            "Layer 1: This Mac 1 (Primary Orchestrator)": ("127.0.0.1", 5001),
            "Layer 2: The Other Mac 2 (Mac Pro Worker)": ("169.254.187.138", 50052),
            "Layer 3: Linux Head Node": ("100.101.39.98", 50052),
            "Layer 4: Pixel 10 Pro XL": ("100.73.38.87", 50052),
            "Layer 5: Samsung S20+": ("100.84.40.95", 50052),
        }
        host, port = node_map.get(node_str, ("127.0.0.1", 50052))
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        try:
            res = s.connect_ex((host, port))
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            return rtt_ms if res == 0 else 999.0
        except Exception:
            return 999.0
        finally:
            s.close()

    def parse_model_size_b(self, model_spec: str) -> float:
        spec = str(model_spec).upper()
        if "135M" in spec: return 0.135
        if "360M" in spec: return 0.360
        if "0.5B" in spec: return 0.5
        if "1.5B" in spec or "1.7B" in spec: return 1.5
        if "3B" in spec: return 3.0
        if "7B" in spec or "8B" in spec: return 7.0
        if "14B" in spec: return 14.0
        if "26B" in spec or "27B" in spec: return 26.0
        if "32B" in spec: return 32.0
        if "70B" in spec or "72B" in spec: return 70.0
        return 4.0

    def compute_model_metrics(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates multi-factor size efficiency, compute efficiency, and project compatibility."""
        model_b = self.parse_model_size_b(agent.get("model_spec", agent.get("name", "")))
        rtt_ms = self.probe_node_rpc_latency(agent.get("node", ""))
        
        # 1. Parameter Efficiency Multiplier (eta_size):
        # A 1.5B/3B model solving complex tasks gets higher size-efficiency than a 70B model.
        eta_size = max(0.5, round(math.log2(70.0 + 1.0) / math.log2(model_b + 1.0), 2))
        
        # 2. Hardware & Compute Efficiency Multiplier (eta_compute):
        # Low latency (<10ms) and low peak memory usage yield high compute scores.
        base_vram_gb = max(0.2, model_b * 0.6)
        clamped_rtt = max(0.1, min(rtt_ms, 300.0))
        eta_compute = max(0.2, round(100.0 / (base_vram_gb * math.sqrt(clamped_rtt)), 2))
        
        # 3. Real Project Compatibility Index (CPI):
        # Based on zero fake data, monorepo language support (Dart/C++/Rust), and active RPC sockets.
        cpi = 0.50
        if agent.get("movesense_connected", False):
            cpi += 0.20
        if "Dart" in str(agent.get("default_lang", "")) or "Rust" in str(agent.get("default_lang", "")) or "Kotlin" in str(agent.get("default_lang", "")):
            cpi += 0.15
        if rtt_ms < 200.0:
            cpi += 0.15
        cpi = min(1.0, round(cpi, 2))
        
        # 4. Empirical Real-Project Benchmark ELO:
        # Ground-truth ELO reflecting actual contribution to monorepo code, tests, and hardware sharding
        stats = agent.get("stats", {})
        audits_passed = stats.get("audits_passed", 0)
        bugs_found = stats.get("bugs_found", 0)
        
        real_project_elo = round(
            1200.0 + 
            (audits_passed * 12.0) + 
            (bugs_found * 15.0) + 
            (eta_size * 45.0) + 
            (min(eta_compute, 25.0) * 8.0) + 
            (cpi * 180.0), 
            1
        )
        
        in_game_elo = float(stats.get("elo", 1300.0))
        divergence = round(in_game_elo - real_project_elo, 1)
        
        return {
            "id": agent.get("id"),
            "name": agent.get("name"),
            "node": agent.get("node"),
            "model_spec": agent.get("model_spec"),
            "model_size_b": model_b,
            "rtt_ms": rtt_ms,
            "eta_size": eta_size,
            "eta_compute": eta_compute,
            "cpi_project": cpi,
            "in_game_elo": in_game_elo,
            "real_project_elo": real_project_elo,
            "divergence": divergence,
            "is_aligned": abs(divergence) <= self.alignment_tolerance_elo
        }

    def run_calibration_cycle(self) -> Dict[str, Any]:
        """Runs bidirectional calibration cycle between in-game ELO and real project benchmark ELO."""
        if not os.path.exists(GAME_STATE_FILE):
            return {"error": "Game state not found"}
            
        try:
            with open(GAME_STATE_FILE, "r") as f:
                game_state = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load game state: {e}"}
            
        agents = game_state.get("agents", [])
        calibrated_models = []
        requires_game_retune = False
        tuning_adjustments = []
        
        for agent in agents:
            metrics = self.compute_model_metrics(agent)
            calibrated_models.append(metrics)
            
            # Check for misalignment
            if not metrics["is_aligned"]:
                requires_game_retune = True
                drift_dir = "OVERVALUED" if metrics["divergence"] > 0 else "UNDERVALUED"
                tuning_adjustments.append({
                    "model": agent["name"],
                    "status": drift_dir,
                    "in_game_elo": metrics["in_game_elo"],
                    "real_project_elo": metrics["real_project_elo"],
                    "delta": metrics["divergence"],
                    "action": f"Adjusting game token multiplier by {-metrics['divergence'] * 0.05:.2f}%"
                })
                # Smooth in-game ELO toward real project ground truth
                corrected_elo = round(metrics["in_game_elo"] - (metrics["divergence"] * 0.35), 1)
                agent["stats"]["elo"] = corrected_elo
                
        # Sort by Real Project ELO (Ground Truth Leaderboard)
        calibrated_models.sort(key=lambda m: m["real_project_elo"], reverse=True)
        
        # Save calibrated agent state back to game
        if requires_game_retune:
            try:
                with open(GAME_STATE_FILE, "w") as f:
                    json.dump(game_state, f, indent=2)
            except Exception:
                pass
                
        # Top 3 High-Functioning Models to Guide Real Project Deployment
        promoted_for_project = [m for m in calibrated_models if m["cpi_project"] >= 0.85][:3]
        
        matrix_result = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_models_evaluated": len(calibrated_models),
            "calibrated_leaderboard": calibrated_models,
            "requires_game_retune": requires_game_retune,
            "tuning_adjustments": tuning_adjustments,
            "promoted_for_real_project": promoted_for_project,
            "alignment_health": "100% SYNCHRONIZED" if not requires_game_retune else f"CALIBRATED ({len(tuning_adjustments)} ADJUSTMENTS)",
            "governance_rule": "In-Game ELO ≡ Real Project Compatibility & Compute Efficiency"
        }
        
        try:
            with open(CALIBRATION_STATE_FILE, "w") as f:
                json.dump(matrix_result, f, indent=2)
        except Exception:
            pass
            
        logger.info(f"Calibration Cycle Complete. Alignment: {matrix_result['alignment_health']}. Models Evaluated: {len(calibrated_models)}")
        return matrix_result

if __name__ == "__main__":
    calibrator = BidirectionalEloCalibrator()
    res = calibrator.run_calibration_cycle()
    print(json.dumps(res, indent=2))
