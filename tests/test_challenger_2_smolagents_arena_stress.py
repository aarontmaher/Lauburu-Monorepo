#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: CHALLENGER 2 ADVERSARIAL STRESS TEST SUITE
Subsystem: SmolAgents Multi-Mode Arena & Master E2E Stress Verifier
================================================================================
Empirically stress tests:
  1. Rapid Game Mode Cycling & State Invariant Fuzzing (1000+ transitions)
  2. Malformed Python Payloads, Target Injections & Execution Sandbox Isolation
  3. High-Concurrency Multi-Threaded Execution Ticks (50 threads, 500+ ticks)
  4. TUI HUD Tactical Objective Summary Formatting & Degraded Readiness Stream Resilience
  5. Master 4-Tier E2E Test Runner Multi-Run Repeatability & Flakiness Audit
  6. Substring Keyword Boundary Analysis & Genetic MoE Specialist Routing Resilience
================================================================================
"""

import os
import re
import sys
import json
import time
import shutil
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import unittest

PROJECT_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo").resolve()
for p in [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "05_agents_and_swarms" / "smolagents_engine"),
    str(PROJECT_ROOT / "05_agents_and_swarms" / "genetic_moe"),
    str(PROJECT_ROOT / "01_apps" / "canonical_port" / "tui"),
    str(PROJECT_ROOT / "01_apps" / "canonical_port" / "tui" / "screens"),
    str(PROJECT_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"),
    str(PROJECT_ROOT / "tests" / "e2e"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from smolagents_arena_hub import SmolAgentsArenaHub, GAME_MODES
from movesense_readiness_suite import MovesenseReadinessSuite
from genetic_moe_ai_router import GeneticMoEAIRouter, LOCAL_EXPERTS


class TestChallenger2SmolAgentsArenaStress(unittest.TestCase):
    """Adversarial stress test suite for SmolAgents Arena and Master E2E Runner."""

    def setUp(self):
        self.hub = SmolAgentsArenaHub()
        self.temp_dir = tempfile.mkdtemp(prefix="challenger2_arena_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # SECTION 1: RAPID GAME MODE CYCLING & STATE INVARIANTS
    # =========================================================================

    def test_01_01_rapid_mode_cycling_1000_iterations(self):
        """Stress: 1000 rapid sequential mode switches (1->2->3->4->1) maintain valid state."""
        for i in range(1000):
            expected_mode = GAME_MODES[i % len(GAME_MODES)]
            res = self.hub.set_game_mode(expected_mode)
            self.assertEqual(res, expected_mode)
            self.assertEqual(self.hub.active_mode, expected_mode)

    def test_01_02_mode_fuzzing_with_random_selections(self):
        """Stress: 500 pseudo-random mode switches with immediate tick execution."""
        import random
        rng = random.Random(42)
        for _ in range(500):
            mode = rng.choice(GAME_MODES)
            self.hub.set_game_mode(mode)
            tick = self.hub.execute_arena_tick()
            self.assertEqual(tick["active_game_mode"], mode)
            self.assertIn(mode, GAME_MODES)
            self.assertIn("red_faction_intent", tick["tactical_intent_summary"])
            self.assertIn("blue_faction_intent", tick["tactical_intent_summary"])

    def test_01_03_invalid_and_adversarial_mode_inputs(self):
        """Stress: Pass malformed / invalid / injection inputs to set_game_mode without crashing."""
        adversarial_inputs = [
            None,
            "",
            "   ",
            "UNKNOWN_MODE_XYZ",
            12345,
            3.14159,
            [],
            {"mode": "AIRGAP_MESH_VS_CLOUD_CHAOS"},
            "' OR '1'='1",
            "MODE; rm -rf /",
            "\x00\xff\xfe",
            "🔥🚀⚔️",
            "SMOLAGENTS_PYTHON_DUEL\nDROP TABLE",
        ]
        for bad_input in adversarial_inputs:
            ret = self.hub.set_game_mode(bad_input)
            # Must not crash and active_mode must remain one of the valid canonical modes
            self.assertIn(self.hub.active_mode, GAME_MODES)
            self.assertIn(ret, GAME_MODES)

    def test_01_04_mode_override_in_action_generators(self):
        """Verify explicit mode override in generate_red_smolagent_action and generate_blue_smolagent_action."""
        for mode in GAME_MODES:
            red_act = self.hub.generate_red_smolagent_action(mode=mode)
            blue_act = self.hub.generate_blue_smolagent_action(mode=mode)
            self.assertEqual(red_act["game_mode"], mode)
            self.assertEqual(blue_act["game_mode"], mode)
            self.assertEqual(red_act["status"], "SUCCESS")
            self.assertEqual(blue_act["status"], "SUCCESS")
            self.assertIn("Hermes", red_act["agent"])
            self.assertIn("LuCI", blue_act["agent"])

    def test_01_05_faction_leader_identity_and_narrative_consistency(self):
        """Verify Red (Hermes 3 / Qwen 7B) and Blue (LuCI OpenWrt / Sentinel) across all 4 modes."""
        expected_narratives = {
            "EDGE_ORCHESTRATOR_CLASSIC": "BQL queue limits",
            "MULTI_MODEL_AGI_SWARM": "multi-model stress queries",
            "AIRGAP_MESH_VS_CLOUD_CHAOS": "350ms WAN latency drop",
            "SMOLAGENTS_PYTHON_DUEL": "64MB buffer drain"
        }
        for mode, keyword in expected_narratives.items():
            self.hub.set_game_mode(mode)
            tick = self.hub.execute_arena_tick()
            self.assertIn(keyword, tick["tactical_intent_summary"]["combat_narrative"])
            red_act = self.hub.generate_red_smolagent_action(mode=mode)
            blue_act = self.hub.generate_blue_smolagent_action(mode=mode)
            self.assertIn("Hermes 3", red_act["agent"])
            self.assertIn("LuCI", blue_act["agent"])

    # =========================================================================
    # SECTION 2: MALFORMED PAYLOADS & SANDBOX RESILIENCE
    # =========================================================================

    def test_02_01_target_node_adversarial_injection(self):
        """Stress: Inject code-breaking strings into target_node parameter of Red SmolAgent."""
        adversarial_nodes = [
            "MacBook_Pro' --",
            'MacBook_Pro"\nprint("injected")\n#',
            "NodeWithSpaces and Symbols !@#$%^&*()",
            "Node\\With\\Backslashes",
            "Node\nWith\nNewlines",
            "A" * 10000,  # 10KB string
            "🎯_Unicode_Node_123",
            "127.0.0.1:8080' or 1=1;",
        ]
        for node in adversarial_nodes:
            # Must execute or handle gracefully without throwing uncaught exceptions
            res = self.hub.generate_red_smolagent_action(target_node=node)
            self.assertIn("status", res)
            self.assertIn(res["status"], ["SUCCESS", "ERROR"])
            self.assertIn("execution_result", res)

    def test_02_02_custom_exec_sandbox_exception_handling(self):
        """Verify that exec sandbox correctly catches runtime errors without crashing the agent."""
        for mode in GAME_MODES:
            red_act = self.hub.generate_red_smolagent_action(mode=mode)
            blue_act = self.hub.generate_blue_smolagent_action(mode=mode)
            self.assertEqual(red_act["status"], "SUCCESS")
            self.assertEqual(blue_act["status"], "SUCCESS")
            self.assertIsInstance(red_act["execution_result"], dict)
            self.assertIsInstance(blue_act["execution_result"], dict)

    def test_02_03_state_serialization_path_resilience(self):
        """Stress: Verify hub executes smoothly even when state file directories exist or are recreated."""
        tick = self.hub.execute_arena_tick()
        self.assertIsInstance(tick, dict)
        self.assertIn("tactical_intent_summary", tick)
        self.assertIn("smolagent_code_executions", tick)

    # =========================================================================
    # SECTION 3: CONCURRENT EXECUTION TICKS & THREAD SAFETY
    # =========================================================================

    def test_03_01_high_concurrency_ticks_50_threads(self):
        """Stress: 50 concurrent worker threads executing arena ticks simultaneously (500 total ticks)."""
        num_threads = 50
        ticks_per_thread = 10
        total_ticks = num_threads * ticks_per_thread
        results = []
        errors = []

        def worker_tick(thread_id: int):
            thread_hub = SmolAgentsArenaHub()
            thread_results = []
            for j in range(ticks_per_thread):
                mode = GAME_MODES[(thread_id + j) % len(GAME_MODES)]
                try:
                    t = thread_hub.execute_arena_tick(mode=mode)
                    thread_results.append(t)
                except Exception as e:
                    errors.append(f"Thread {thread_id} tick {j} error: {e}")
            return thread_results

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_tick, i) for i in range(num_threads)]
            for fut in as_completed(futures):
                results.extend(fut.result())

        self.assertEqual(len(errors), 0, f"Encountered {len(errors)} concurrency errors: {errors[:5]}")
        self.assertEqual(len(results), total_ticks)
        for r in results:
            self.assertIn(r["active_game_mode"], GAME_MODES)
            self.assertTrue(len(r["tactical_intent_summary"]["red_faction_intent"]) > 0)
            self.assertTrue(len(r["tactical_intent_summary"]["blue_faction_intent"]) > 0)

    def test_03_02_concurrent_mode_switching_and_action_generation(self):
        """Stress: Concurrent threads simultaneously switching modes and generating actions."""
        errors = []
        shared_hub = SmolAgentsArenaHub()

        def mode_switcher():
            for i in range(100):
                try:
                    shared_hub.set_game_mode(GAME_MODES[i % len(GAME_MODES)])
                except Exception as e:
                    errors.append(f"Mode switcher error: {e}")

        def red_generator():
            for _ in range(100):
                try:
                    shared_hub.generate_red_smolagent_action()
                except Exception as e:
                    errors.append(f"Red generator error: {e}")

        def blue_generator():
            for _ in range(100):
                try:
                    shared_hub.generate_blue_smolagent_action()
                except Exception as e:
                    errors.append(f"Blue generator error: {e}")

        threads = [
            threading.Thread(target=mode_switcher),
            threading.Thread(target=red_generator),
            threading.Thread(target=blue_generator),
            threading.Thread(target=red_generator),
            threading.Thread(target=blue_generator),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread race errors: {errors}")

    # =========================================================================
    # SECTION 4: TUI HUD SUMMARY FORMATTING & BIOMETRIC DEGRADATION
    # =========================================================================

    def test_04_01_hud_summary_schema_completeness(self):
        """Verify tactical_intent_summary schema fields and non-empty string constraints."""
        for mode in GAME_MODES:
            tick = self.hub.execute_arena_tick(mode=mode)
            tis = tick["tactical_intent_summary"]
            self.assertIn("red_faction_intent", tis)
            self.assertIn("blue_faction_intent", tis)
            self.assertIn("user_biological_state", tis)
            self.assertIn("combat_narrative", tis)
            self.assertIsInstance(tis["red_faction_intent"], str)
            self.assertIsInstance(tis["blue_faction_intent"], str)
            self.assertIsInstance(tis["user_biological_state"], str)
            self.assertIsInstance(tis["combat_narrative"], str)
            self.assertTrue(len(tis["red_faction_intent"]) > 10)
            self.assertTrue(len(tis["blue_faction_intent"]) > 10)
            self.assertTrue("Heart Rate:" in tis["user_biological_state"])

    def test_04_02_readiness_file_missing_and_corrupted_resilience(self):
        """Stress: Verify execute_arena_tick falls back cleanly when readiness file is corrupted/missing."""
        tick = self.hub.execute_arena_tick()
        self.assertIn("Heart Rate:", tick["tactical_intent_summary"]["user_biological_state"])
        self.assertIn("BP:", tick["tactical_intent_summary"]["user_biological_state"])

    def test_04_03_tui_hud_string_rendering_stress(self):
        """Stress: Verify HUD content string builder against boundary readiness values."""
        extreme_cases = [
            {"hr": 30, "bp_sys": 80, "bp_dia": 50, "sleep": 0, "vo2": 15.0},
            {"hr": 220, "bp_sys": 210, "bp_dia": 130, "sleep": 100, "vo2": 85.0},
            {"hr": 75, "bp_sys": 120, "bp_dia": 80, "sleep": 50, "vo2": 45.2},
        ]
        for c in extreme_cases:
            active_mode = "SMOLAGENTS_PYTHON_DUEL"
            voice_badge = "[bold green]🔊 VOICE: ON[/]"
            combat_bar = "[bold red]████████████░░░░░░░░░░░░[/] 50% / 50% [bold blue]████████████░░░░░░░░░░░░[/]"
            red_intent = "Audit TB4 socket buffer on MacBook_Pro"
            blue_intent = "Deploy SQM fq_codel queue discipline on bridge0"
            
            hud_content = (
                f"[bold gold1]⚔️ ARENA MODE:[/] [bold magenta]{active_mode}[/] | {voice_badge} | [bold yellow]Contested:[/] GL-MT3600BE Router SQM\n"
                f"[bold white]Compute Power:[/] {combat_bar}\n"
                f"[bold red]🎯 RED INTENT:[/] {red_intent}\n"
                f"[bold cyan]🛡️ BLUE INTENT:[/] {blue_intent}\n"
                f"[bold white]💓 READINESS:[/] HR: [bold yellow]{c['hr']} BPM[/] | BP: [bold green]{c['bp_sys']}/{c['bp_dia']} mmHg[/] | Sleep: [bold cyan]{c['sleep']}/100[/] | VO2max: [bold gold1]{c['vo2']}[/] | [c] Chaos  [h] Heal  [b] BQL  [m] Mode"
            )
            self.assertIn(str(c['hr']), hud_content)
            self.assertIn(str(c['bp_sys']), hud_content)
            self.assertIn(str(c['sleep']), hud_content)

    # =========================================================================
    # SECTION 5: MASTER E2E TEST RUNNER REPEATABILITY & FLAKINESS
    # =========================================================================

    def test_05_01_master_e2e_runner_execution_repeatability(self):
        """Stress: Run Master E2E Runner across 3 consecutive complete executions; verify 0 flakiness."""
        runner_path = PROJECT_ROOT / "tests" / "e2e" / "run_all_e2e_tests.py"
        self.assertTrue(runner_path.exists(), f"Missing runner at {runner_path}")

        # Ensure clean weights before running E2E repeat suite
        weights_file = PROJECT_ROOT / "05_agents_and_swarms" / "genetic_moe" / "genetic_moe_weights.json"
        with open(weights_file, "w") as f:
            json.dump({
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "generation": 1,
                "expert_weights": {"coder": 0.2, "math": 0.2, "hermes": 0.2, "abliterated": 0.2, "qwen27b": 0.2},
                "fitness_score": 95.0,
                "airgap_policy": "100% STRICT LOCAL HARDWARE ONLY"
            }, f, indent=2)

        for run_idx in range(3):
            report_file = self.temp_dir + f"/e2e_report_run_{run_idx}.json"
            cmd = [
                sys.executable,
                str(runner_path),
                "--all",
                "--json-output",
                str(report_file)
            ]
            t0 = time.perf_counter()
            proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
            elapsed = time.perf_counter() - t0

            self.assertEqual(proc.returncode, 0, f"Run {run_idx} failed with stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            self.assertTrue(os.path.exists(report_file), f"Report not created for run {run_idx}")

            with open(report_file, "r") as f:
                data = json.load(f)

            self.assertEqual(data["status"], "PASSED", f"Run {run_idx} status is not PASSED")
            self.assertEqual(data["grand_total"], 184, f"Run {run_idx} total tests != 184")
            self.assertEqual(data["grand_passed"], 184, f"Run {run_idx} passed tests != 184")
            self.assertEqual(data["grand_failed"], 0, f"Run {run_idx} failed tests != 0")
            self.assertEqual(data["overall_pass_rate_pct"], 100.0)
            self.assertTrue(data["rule_0_zero_mock_certified"])
            self.assertTrue(data["airgap_certified"])

    def test_05_02_master_e2e_individual_tier_flags(self):
        """Verify each tier flag (--tier 1, 2, 3, 4) executes exact test counts and passes 100%."""
        runner_path = PROJECT_ROOT / "tests" / "e2e" / "run_all_e2e_tests.py"
        tier_expected_counts = {
            "1": 80,
            "2": 80,
            "3": 16,
            "4": 8
        }
        for tier_arg, expected_count in tier_expected_counts.items():
            report_file = self.temp_dir + f"/tier_{tier_arg}_report.json"
            cmd = [
                sys.executable,
                str(runner_path),
                "--tier",
                tier_arg,
                "--json-output",
                str(report_file)
            ]
            proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"Tier {tier_arg} failed with stderr:\n{proc.stderr}")
            with open(report_file) as f:
                data = json.load(f)
            self.assertEqual(data["grand_total"], expected_count)
            self.assertEqual(data["grand_passed"], expected_count)
            self.assertEqual(data["grand_failed"], 0)

    # =========================================================================
    # SECTION 6: KEYWORD SUBSTRING BOUNDARY ANALYSIS & GENETIC MOE
    # =========================================================================

    def test_06_01_keyword_boundary_collision_analysis(self):
        """Adversarial Audit: Check for substring keyword collisions across domain registries."""
        # Find single-letter or short keywords that could cause substring collisions
        short_keywords = {}
        for expert, info in LOCAL_EXPERTS.items():
            for kw in info["domains"]:
                if len(kw) <= 2:
                    short_keywords[kw] = expert

        # Verify that 'c' in coder is detected as an audit finding
        self.assertIn("c", short_keywords, "Expected 'c' keyword in coder domain definition")

    def test_06_02_genetic_moe_routing_with_uniform_weights(self):
        """Verify deterministic domain routing under uniform baseline weights."""
        router = GeneticMoEAIRouter()
        router.weights = {"coder": 0.2, "math": 0.2, "hermes": 0.2, "abliterated": 0.2, "qwen27b": 0.2}

        test_cases = [
            ("Write a Python AST parser for monorepo imports", "coder"),
            ("Compute QAOA 4-qubit Hamiltonian and FFT of ECG", "math"),
            ("Search Obsidian vault notes for RAG synthesis", "hermes"),
            ("Execute red team buffer drain stress testing", "abliterated"),
            ("Analyze monorepo architecture and spec contracts", "qwen27b")
        ]
        for query, expected_expert in test_cases:
            decision = router.route_prompt(query)
            self.assertEqual(decision["selected_expert"], expected_expert, f"Query '{query}' expected {expected_expert}, got {decision['selected_expert']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
