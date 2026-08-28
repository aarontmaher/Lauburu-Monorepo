"""
Unit Tests: Master AGI Governance & Sharding Contracts (Features 3, 4, 5, 6)
Verifies Kimi 88B Tandem, Qwen 3.8 Max, 82.8GB Pooled VRAM, Debate Accord, and Action Dispatcher.
Derived from ORIGINAL_REQUEST.md §R1 and PROJECT.md §2.
"""

import pytest
from typing import Dict, List, Any

class MasterAGIGovernor:
    """Reference governor logic implementing Master AGI specifications and VRAM sharding."""
    def __init__(self, models: List[Dict[str, Any]], cluster_vram: Dict[str, Any]):
        self.models = {m["id"]: m for m in models}
        self.cluster_vram = cluster_vram
        self.debate_history: List[Dict[str, Any]] = []
        self.stagnation_counter = 0

    def get_model(self, model_id: str) -> Dict[str, Any]:
        return self.models.get(model_id, {})

    def calculate_total_allocated_vram(self) -> float:
        return sum(m.get("vramFootprintGb", 0.0) for m in self.models.values() if m.get("status") == "active")

    def calculate_free_headroom(self) -> float:
        pooled = self.cluster_vram.get("pooledVramGb", 82.8)
        allocated = self.calculate_total_allocated_vram()
        return round(pooled - allocated, 2)

    def verify_dynamic_ram_ceilings(self) -> Dict[str, bool]:
        compliance = {}
        for node in self.cluster_vram.get("nodes", []):
            cap_ratio = node["aiVramCapGb"] / node["ramTotalGb"]
            expected_cap = node["dynamicCapPercent"] / 100.0
            compliance[node["nodeId"]] = abs(cap_ratio - expected_cap) < 0.01
        return compliance

    def evaluate_debate_round(self, scores: List[float]) -> Dict[str, Any]:
        accord = sum(scores) / len(scores) if scores else 0.0
        is_consensus = accord >= 0.98
        if len(self.debate_history) > 0 and accord <= self.debate_history[-1].get("accord", 0.0):
            self.stagnation_counter += 1
        else:
            self.stagnation_counter = 0
        
        is_stagnated = self.stagnation_counter >= 3
        record = {
            "round": len(self.debate_history) + 1,
            "accord": round(accord, 4),
            "isConsensus": is_consensus,
            "isStagnated": is_stagnated
        }
        self.debate_history.append(record)
        return record

    def dispatch_action(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        VALID_COMMANDS = ["/audit", "/duel", "/cron", "/storage", "/ping", "/revive"]
        if command not in VALID_COMMANDS:
            return {"success": False, "error": f"Unknown action command: {command}"}
        return {
            "success": True,
            "command": command,
            "payload": payload,
            "targetPort": 18802,
            "status": "DISPATCHED"
        }


def test_master_agi_models_roster_contract(master_agi_models):
    assert len(master_agi_models) >= 2
    model_ids = [m["id"] for m in master_agi_models]
    assert "kimi_tandem_titan" in model_ids
    assert "qwen_38_max" in model_ids

def test_kimi_tandem_sharding_spec(master_agi_models):
    kimi = next(m for m in master_agi_models if m["id"] == "kimi_tandem_titan")
    assert kimi["name"] == "Kimi 88B Tandem Titan"
    assert "-ts 28,28,24" in kimi["shardingStrategy"]
    assert 50052 in kimi["ports"]
    assert 8085 in kimi["ports"]
    assert 8081 in kimi["ports"]
    assert kimi["vramFootprintGb"] == 48.8
    assert kimi["contextWindow"] >= 16384
    assert kimi["eloRating"] >= 3000.0

def test_qwen_38_max_spec(master_agi_models):
    qwen = next(m for m in master_agi_models if m["id"] == "qwen_38_max")
    assert "Qwen 3.8 Max" in qwen["name"]
    assert 8084 in qwen["ports"]
    assert qwen["throughputTokPerSec"] >= 40.0
    assert qwen["status"] == "active"

def test_cluster_pooled_vram_and_headroom(master_agi_models, cluster_vram_topology):
    gov = MasterAGIGovernor(master_agi_models, cluster_vram_topology)
    assert cluster_vram_topology["pooledVramGb"] == 82.8
    assert cluster_vram_topology["totalPhysicalRamGb"] == 108.0
    assert cluster_vram_topology["interconnect"]["latencyMs"] < 0.30
    
    allocated = gov.calculate_total_allocated_vram()
    assert allocated > 50.0  # Kimi 48.8 + Qwen 5.85 = 54.65
    headroom = gov.calculate_free_headroom()
    assert headroom > 20.0  # Adequate free headroom remaining
    assert round(allocated + headroom, 1) == 82.8

def test_7_layer_dynamic_ram_ceilings(master_agi_models, cluster_vram_topology):
    gov = MasterAGIGovernor(master_agi_models, cluster_vram_topology)
    compliance = gov.verify_dynamic_ram_ceilings()
    assert len(compliance) == 7
    for node_id, is_compliant in compliance.items():
        assert is_compliant is True, f"Node {node_id} dynamic ceiling violated"

def test_tri_orchestrator_debate_consensus(master_agi_models, cluster_vram_topology):
    gov = MasterAGIGovernor(master_agi_models, cluster_vram_topology)
    # High accord round
    res = gov.evaluate_debate_round([0.99, 0.985, 0.982])
    assert res["accord"] >= 0.98
    assert res["isConsensus"] is True
    assert res["isStagnated"] is False

def test_tri_orchestrator_stagnation_failsafe(master_agi_models, cluster_vram_topology):
    gov = MasterAGIGovernor(master_agi_models, cluster_vram_topology)
    # 3 stagnant rounds
    gov.evaluate_debate_round([0.80, 0.82, 0.81])
    gov.evaluate_debate_round([0.80, 0.80, 0.80])
    gov.evaluate_debate_round([0.79, 0.79, 0.80])
    res4 = gov.evaluate_debate_round([0.78, 0.79, 0.79])
    assert res4["isStagnated"] is True
    assert res4["isConsensus"] is False

def test_swarm_action_dispatcher_commands(master_agi_models, cluster_vram_topology):
    gov = MasterAGIGovernor(master_agi_models, cluster_vram_topology)
    commands = ["/audit", "/duel", "/cron", "/storage", "/ping", "/revive"]
    for cmd in commands:
        res = gov.dispatch_action(cmd, {"source": "unit_test", "priority": "P0"})
        assert res["success"] is True
        assert res["command"] == cmd
        assert res["targetPort"] == 18802

    # Invalid action
    res_err = gov.dispatch_action("/invalid_cmd", {})
    assert res_err["success"] is False
    assert "error" in res_err
