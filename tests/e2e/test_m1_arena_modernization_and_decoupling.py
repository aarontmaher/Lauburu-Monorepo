"""
Milestone 1 E2E Verification Suite — Arena Modernization & Movesense Decoupling
================================================================================
Validates:
1. Complete Movesense decoupling from arena_canvas.html (public, dist, experimental_pwas).
2. Purge of movesense_* attributes from game_arena_state.json files.
3. GameArenaManager duel execution across all 24 challenge modes with 0 errors.
4. Dedicated "ai_sharding_speed" branch returning 4-tier model sharding benchmarks,
   Speedify MPQUIC packet striping, dynamic RAM headroom, and structured JSON manifests.
5. Dual Qwen-3.8Max fighters equipped with complete project context and skill declarations.
"""

import os
import re
import json
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")


class TestM1ArenaModernization:

    def test_arena_canvas_movesense_decoupling(self):
        """Verify all arena_canvas.html copies are completely decoupled from Movesense."""
        canvas_paths = [
            REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "frontend" / "public" / "arena_canvas.html",
            REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "frontend" / "dist" / "arena_canvas.html",
            REPO_ROOT / "01_apps" / "experimental_pwas" / "swarm_dashboard" / "arena_canvas.html",
        ]

        forbidden_tokens = [
            "#ecg-bar",
            "ecg-canvas",
            "ecg-label",
            "ecg-stat",
            "connectMovesense",
            "startDemoECG",
            "generateECGSample",
            "resizeECG",
            "drawECG",
            "192.168.8.230:4001",
            "ecgBuffer",
            "ecgPhase",
            "movesense"
        ]

        for p in canvas_paths:
            assert p.exists(), f"Canvas path does not exist: {p}"
            content = p.read_text(encoding="utf-8")

            # Verify grid layout reclaimed 160px
            grid_matches = re.findall(r"grid-template-rows:\s*([^;]+);", content)
            assert any("56px 1fr" in g for g in grid_matches), f"Grid rows not 56px 1fr in {p}: {grid_matches}"

            # Verify 0 occurrences of forbidden tokens
            for token in forbidden_tokens:
                assert token.lower() not in content.lower(), f"Found forbidden token '{token}' in {p}"

    def test_game_arena_state_purged_movesense_attributes(self):
        """Verify all game_arena_state.json files are free of movesense_* attributes."""
        state_paths = [
            REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src" / "game_arena_state.json",
            REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "frontend" / "public" / "game_arena_state.json",
            REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "frontend" / "dist" / "game_arena_state.json",
            REPO_ROOT / "04_data_and_memory" / "session_logs" / "game_arena_state.json",
            REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src" / "session_logs" / "game_arena_state.json",
        ]

        def check_no_movesense(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    assert "movesense" not in k.lower(), f"Found movesense key '{k}' at path '{path}'"
                    check_no_movesense(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_no_movesense(v, f"{path}[{i}]")

        for p in state_paths:
            assert p.exists(), f"State path does not exist: {p}"
            data = json.loads(p.read_text(encoding="utf-8"))
            check_no_movesense(data, str(p))

    def test_dual_qwen_38_max_fighters_equipped(self):
        """Verify dual Qwen-3.8Max fighters are equipped with full project context."""
        import sys
        hub_src = str(REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src")
        if hub_src not in sys.path:
            sys.path.insert(0, hub_src)
        from game_arena_manager import GameArenaManager

        manager = GameArenaManager()
        fighters = {f["id"]: f for f in manager.state["fighters"]}

        assert "qwen_38_max" in fighters, "qwen_38_max missing from fighters"
        qwen_max = fighters["qwen_38_max"]
        assert "Antigravity SDK" in qwen_max["specialty"]
        assert "Smolagents" in qwen_max["specialty"]
        assert "MCP" in qwen_max["specialty"]
        assert "docker_mesh_rpc_sharding" in qwen_max["specialist_skills"]
        assert qwen_max["specialist_skills"]["docker_mesh_rpc_sharding"] >= 99.0

        assert "qwen_38_27b" in fighters, "qwen_38_27b missing from fighters"
        qwen_math = fighters["qwen_38_27b"]
        assert "RAM Headroom" in qwen_math["specialty"] or "Math" in qwen_math["name"]
        assert "docker_mesh_rpc_sharding" in qwen_math["specialist_skills"]

    def test_ai_sharding_speed_challenge_mode_manifest(self):
        """Verify Challenge Mode 2 'ai_sharding_speed' generates structured diagnostic manifest."""
        import sys
        hub_src = str(REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src")
        if hub_src not in sys.path:
            sys.path.insert(0, hub_src)
        from game_arena_manager import GameArenaManager

        manager = GameArenaManager()
        res = manager.execute_duel(
            fighter1_id="qwen_38_max",
            fighter2_id="antigravity_preview",
            challenge_mode="ai_sharding_speed"
        )

        assert res is not None
        assert "winner_id" in res
        cot = res["cot_solution"]
        assert "DISTRIBUTED_AI_SHARDING_SPEED_OPTIMIZATION" in cot
        assert "llama_rpc" in cot
        assert "petals_dht" in cot
        assert "exo_mlx" in cot
        assert "hf_accelerate" in cot
        assert "4_TIER_SHARDING_OPTIMAL" in cot

        # Extract and parse JSON block
        json_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", cot)
        assert json_match is not None, f"No JSON block in CoT: {cot}"
        manifest = json.loads(json_match.group(1))
        assert manifest["benchmark"] == "DISTRIBUTED_AI_SHARDING_SPEED_OPTIMIZATION"
        assert manifest["status"] == "4_TIER_SHARDING_OPTIMAL"
        assert manifest["tensor_parallelism_efficiency_pct"] >= 90.0
        assert manifest["ttft_latency_ms"] <= 20.0
        assert manifest["ram_safety_headroom_gb"] >= 2.50

    def test_all_24_challenge_modes_execute_without_errors(self):
        """Verify all 24 challenge modes execute duels with 0 errors."""
        import sys
        hub_src = str(REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src")
        if hub_src not in sys.path:
            sys.path.insert(0, hub_src)
        from game_arena_manager import GameArenaManager, CHALLENGE_MODES

        manager = GameArenaManager()
        assert len(CHALLENGE_MODES) >= 20, f"Expected at least 20 modes, got {len(CHALLENGE_MODES)}"

        for mode_id in CHALLENGE_MODES.keys():
            res = manager.execute_duel(
                fighter1_id="qwen_38_max",
                fighter2_id="antigravity_preview",
                challenge_mode=mode_id
            )
            assert res is not None
            assert "winner_id" in res
            assert "cot_solution" in res
            assert len(res["cot_solution"]) > 20
            # Ensure no stale Kamath / DFA biometrics in default fallback
            if "Kamath" in res["cot_solution"]:
                assert mode_id in ["project_context_accuracy", "agents_last_exam_reasoning"]
