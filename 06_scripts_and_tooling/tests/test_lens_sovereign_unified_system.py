#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Tests for Lauburu Screen Lens Sovereign Unified System
=========================================================================
Verifies all 8 Sovereign Pillars, edge cases, boundary conditions, and CLI dispatch.
Compatible with both `unittest` (`python3 test_lens_sovereign_unified_system.py`) and `pytest`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling" / "storage"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling" / "network"))
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure" / "auth"))

from lens_sovereign_unified_system import (
    CockpitArchitectureAdvisor,
    CognitiveMemoryAndDualAccountOrchestrator,
    DockerCloudflareVsTailscaleBenchmark,
    FullNetworkSovereignDeployer,
    JunieThunderboltMeshIntegrator,
    LensPythonCompanionAgent,
    MovesenseGattBluetoothSerialBridge,
    MovesensePixelOnlyGattSerialBridge,
    OnDemandNvidiaVoiceCoderManager,
    OverallProjectGapReviewer,
    PolyglotShardingAndTrainingUnifier,
    PolyglotSpecialistIDEAndRuntimeIntegrator,
    ProgressiveNetworkSelfHealer,
    Qwen3DVLAAndCodingTelemetryAuditor,
    S20LongTermPersistenceHealer,
    SelfOptimizingELOBenchmarkerAndModelScout,
    SovereignAIDebateAndFreeTierOrchestrator,
    UnifiedStorageAndPodmanOrchestrator,
)
from workspace_dwd_gateway import DualAccountGoogleRouter


class TestLensSovereignUnifiedSystem(unittest.TestCase):
    def test_storage_and_rooted_podman_architecture(self):
        orch = UnifiedStorageAndPodmanOrchestrator()
        arch = orch.get_podman_storage_architecture()
        self.assertGreater(arch["local_disk_total_gb"], 0)
        spec = arch["rooted_podman_spec"]
        self.assertEqual(spec["canonical_project_holder"]["node_id"], "L1b")
        self.assertIn("2TB", spec["canonical_project_holder"]["device"])

        bind_mounts = {m["container_path"]: m for m in spec["rooted_podman_container_layout"]["bind_mounts"]}
        self.assertIn("/workspace/monorepo", bind_mounts)
        self.assertEqual(bind_mounts["/workspace/monorepo"]["mode"], "rw,Z")
        self.assertIn("/workspace/models", bind_mounts)
        self.assertEqual(bind_mounts["/workspace/models"]["mode"], "ro,Z")
        self.assertIn("/workspace/lora_datasets", bind_mounts)
        self.assertIn("/workspace/obsidian_vault", bind_mounts)
        self.assertIn("/workspace/deps_vault", bind_mounts)

        isolated_vols = {v["volume_name"]: v for v in spec["rooted_podman_container_layout"]["isolated_native_volumes"]}
        self.assertIn("lauburu_neo4j_data", isolated_vols)
        self.assertIn("lauburu_qdrant_storage", isolated_vols)
        self.assertIn("lauburu_pyspark_warehouse", isolated_vols)

        cmd_l3 = orch.generate_podman_run_command("L3")
        self.assertIn("--userns=host", cmd_l3)
        self.assertIn("--privileged", cmd_l3)
        self.assertIn("/workspace/models:ro,Z", cmd_l3)
        self.assertIn("lauburu_neo4j_data:/var/lib/neo4j/data", cmd_l3)

    def test_progressive_4_stage_network_self_healing_cascade(self):
        healer = ProgressiveNetworkSelfHealer()
        res = healer.run_full_healing_cascade(heal=False)
        self.assertEqual(
            res["cascade_order"],
            [
                "1_bluetooth_serial_terminal",
                "2_bluetooth_pan",
                "3_wol_ethernet",
                "4_kdeconnect_ssh",
            ],
        )
        self.assertEqual(len(res["stages"]), 4)
        self.assertEqual(res["stages"][0]["name"], "bluetooth_serial_terminal")
        self.assertIn("movesense_gatt_serial_bridge", res["stages"][0])
        self.assertEqual(
            res["stages"][0]["movesense_gatt_serial_bridge"]["pixel_only_ble_connection_guard"]["policy"],
            "STRICT_PIXEL_L6_EXCLUSIVE_BLE_GATT_OWNER",
        )
        self.assertEqual(res["stages"][1]["name"], "bluetooth_pan")
        self.assertEqual(res["stages"][2]["name"], "wol_ethernet")
        self.assertEqual(res["stages"][2]["magic_packet_size_bytes"], 102)
        self.assertEqual(res["stages"][3]["name"], "kdeconnect_ssh")

    def test_movesense_gatt_bluetooth_serial_bridge_pixel_only_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            live_json = tmp_path / "movesense_live_stream.json"
            readiness_json = tmp_path / "movesense_readiness_live.json"
            ansi_out = tmp_path / "bluetooth_terminal_stream.ansi"

            live_json.write_text(
                json.dumps(
                    {
                        "connected": True,
                        "device_name": "Movesense 261030002013",
                        "mac": "74:92:BA:11:36:D6",
                        "heart_rate_bpm": 64.5,
                        "rr_interval_ms": 930.2,
                        "rmssd_ms": 58.4,
                        "dfa_alpha1": 0.91,
                        "battery_pct": 88,
                        "placement": "chest_strap",
                        "stream_mode": "LIVE_BLE_HARDWARE",
                    }
                ),
                encoding="utf-8",
            )
            bridge = MovesenseGattBluetoothSerialBridge(
                live_stream_file=live_json,
                readiness_file=readiness_json,
                ansi_stream_file=ansi_out,
            )

            # 1. Verify non-Pixel hosts (Macs L5/L1/L1b/L2, Linux L3/L8) are strictly blocked from direct BLE GATT
            for non_pixel_host in ("mac-air-4.local", "Mac-mini.local", "linux-head", "linuxmini"):
                guard = bridge.verify_pixel_only_ble_connection_guard(current_host=non_pixel_host, is_termux_android=False)
                self.assertFalse(guard["direct_ble_connection_permitted_on_this_host"])
                self.assertEqual(guard["local_ble_connect_action"], "BLOCKED_BY_PIXEL_ONLY_BLE_GUARD_PULL_VIA_L6_SERIAL_4005")
                self.assertEqual(guard["sole_authorized_ble_gatt_owner"]["node_id"], "L6")
                self.assertEqual(guard["sole_authorized_ble_gatt_owner"]["tailscale_ip"], "100.114.215.68")

            # 2. Verify Pixel 10 Pro XL (L6 / Termux) IS permitted as sole BLE GATT owner
            pixel_guard = bridge.verify_pixel_only_ble_connection_guard(current_host="pixel-10-pro-xl", is_termux_android=True)
            self.assertTrue(pixel_guard["direct_ble_connection_permitted_on_this_host"])
            self.assertEqual(pixel_guard["local_ble_connect_action"], "PERMITTED_SOLE_BLE_GATT_MASTER")

            # 3. Verify pulling Movesense GATT telemetry writes Teleplot + ANSI frame to Bluetooth Serial Terminal stream
            pull_res = bridge.pull_movesense_gatt_to_serial_terminal(stream_to_terminal=True)
            self.assertEqual(pull_res["bridge"], "MovesenseGattBluetoothSerialBridge")
            self.assertEqual(pull_res["serial_terminal_port"], 4005)
            self.assertTrue(pull_res["ansi_stream_written"])
            self.assertTrue(ansi_out.exists())
            ansi_text = ansi_out.read_text(encoding="utf-8")
            self.assertIn("[MOVESENSE-GATT->BT-SERIAL:4005]", ansi_text)
            self.assertIn(">movesense_gatt_hr_bpm:64.5", ansi_text)
            self.assertIn(">movesense_gatt_rmssd_ms:58.4", ansi_text)

    def test_wol_magic_packet_edge_cases(self):
        from canonical_network_resurrection_engine import construct_magic_packet

        pkt = construct_magic_packet("00:41:0e:14:28:43")
        self.assertEqual(len(pkt), 102)
        self.assertEqual(pkt[:6], b"\xff" * 6)

        with self.assertRaises(ValueError):
            construct_magic_packet("invalid-mac")

        with self.assertRaises(ValueError):
            construct_magic_packet("")

    def test_dual_google_account_routing_and_isolation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "dual_google_account_routing.json"
            router = DualAccountGoogleRouter(config_path=cfg_path)
            prov = router.provision_dual_account_config()
            self.assertEqual(prov["status"], "PROVISIONED")
            self.assertEqual(prov["workspace_account"], "lauburu@lauburugrappling.com")
            self.assertEqual(prov["standard_gcp_account"], "aaron.t.maher@gmail.com")
            self.assertEqual(cfg_path.stat().st_mode & 0o777, 0o600)

            # Workspace-dependent features MUST route to lauburu@lauburugrappling.com
            for svc in ("drive", "gdrive_vfs", "gmail", "docs", "sheets", "slides", "chat", "admin_directory"):
                route = router.resolve_service_account_route(svc)
                self.assertEqual(route["account_tier"], "GOOGLE_WORKSPACE")
                self.assertEqual(route["account_email"], "lauburu@lauburugrappling.com")
                self.assertTrue(route["password_configured"])

            # Non-Workspace Google Cloud features MUST route to aaron.t.maher@gmail.com
            for svc in ("vertex_ai", "bigquery", "cloud_run", "gcs", "gemini_api", "colab", "firebase"):
                route = router.resolve_service_account_route(svc)
                self.assertEqual(route["account_tier"], "STANDARD_GOOGLE_CLOUD")
                self.assertEqual(route["account_email"], "aaron.t.maher@gmail.com")

    def test_cognitive_memory_bitemporal_edges_and_working_memory_ttl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test_memory.sqlite"
            mem = CognitiveMemoryAndDualAccountOrchestrator(db_path=db_file)

            # Record fact v1 at t=1000
            mem.record_bitemporal_fact("Node_L8", "IP_ADDRESS", "192.168.8.200", t_valid_from=1000.0)
            facts_t1500 = mem.query_valid_facts_at(subject="Node_L8", timestamp=1500.0)
            self.assertEqual(len(facts_t1500), 1)
            self.assertEqual(facts_t1500[0]["object_val"], "192.168.8.200")

            # Supersede fact v2 at t=2000 -> v1 must be closed (t_valid_to=2000)
            mem.record_bitemporal_fact("Node_L8", "IP_ADDRESS", "192.168.8.242", t_valid_from=2000.0)

            # Query at t=1500 still returns v1 (historical time-travel)
            facts_historical = mem.query_valid_facts_at(subject="Node_L8", timestamp=1500.0)
            self.assertEqual(len(facts_historical), 1)
            self.assertEqual(facts_historical[0]["object_val"], "192.168.8.200")

            # Query at t=2500 returns only v2
            facts_current = mem.query_valid_facts_at(subject="Node_L8", timestamp=2500.0)
            self.assertEqual(len(facts_current), 1)
            self.assertEqual(facts_current[0]["object_val"], "192.168.8.242")

            # Test Working Memory KV TTL expiry
            mem.put_working_memory("ephemeral_key", {"step": 1}, ttl_sec=0.02)
            self.assertEqual(mem.get_working_memory("ephemeral_key"), {"step": 1})
            time.sleep(0.04)
            self.assertIsNone(mem.get_working_memory("ephemeral_key"))

            # Test Merkle Ledger
            merkle = mem.compute_cross_store_merkle_receipt()
            self.assertEqual(len(merkle["merkle_root"]), 64)

    def test_python_companion_agent_py_pi_and_dependencies(self):
        agent = LensPythonCompanionAgent()
        res = agent.execute_task("Check disk storage and podman headroom")
        self.assertTrue(res["zero_mock_certified"])
        self.assertIn("free_gb", res["execution_output"])
        self.assertEqual(len(res["sha256_receipt"]), 64)

        # Edge case: AST security sandbox must reject forbidden calls
        with self.assertRaises(ValueError):
            agent.validate_ast_safety("import os\nos.system('id')")
        with self.assertRaises(ValueError):
            agent.validate_ast_safety("eval('2 + 2')")

        deps = agent.audit_all_dependencies()
        self.assertTrue(deps["py_pi_companion_integrated"])
        self.assertIn("python3", deps["cli_binaries"])
        self.assertTrue(deps["cli_binaries"]["python3"]["installed"])
        self.assertIn("lens", deps["cli_binaries"])
        self.assertIn("lens_cli.py", deps["cli_binaries"])

    def test_polyglot_go_and_python_sharding_training_protocols(self):
        unifier = PolyglotShardingAndTrainingUnifier()
        res = unifier.verify_both_language_protocols()
        go_ids = {p["id"] for p in res["registry"]["go_protocols"]}
        py_ids = {p["id"] for p in res["registry"]["python_protocols"]}

        self.assertIn("go_prima_cgo_ring", go_ids)
        self.assertIn("go_opencode_prima_genetic_moe", go_ids)
        self.assertIn("go_llama_lens_orchestrator", go_ids)
        self.assertIn("go_tiny_lm_bpe_trainer", go_ids)
        self.assertTrue(all(p["exists"] for p in res["registry"]["go_protocols"]))

        self.assertIn("py_tb4_prp_ring", py_ids)
        self.assertIn("py_unified_hybrid_sharding", py_ids)
        self.assertIn("py_petals_mesh_dht", py_ids)
        self.assertIn("py_mlx_metal_lora_trainer", py_ids)
        self.assertIn("py_podman_local_ai_trainer", py_ids)
        self.assertTrue(all(p["exists"] for p in res["registry"]["python_protocols"]))

        self.assertTrue(res["live_verification"]["go_orchestrator_verify"]["executed"])
        self.assertEqual(res["live_verification"]["go_orchestrator_verify"]["exit_code"], 0)
        self.assertTrue(res["live_verification"]["python_tb4_prp_allocation"]["executed"])
        self.assertEqual(res["live_verification"]["python_tb4_prp_allocation"]["tb4_prp_plan_64_layers"]["unassigned_layers"], 0)

    def test_cockpit_ide_structure_and_network_benchmark(self):
        cockpit = CockpitArchitectureAdvisor.evaluate_cockpit_structure(provision=True)
        self.assertIn("IntelliJ IDEA", cockpit["recommended_structure"]["primary_polyglot_ide"]["winner"])
        self.assertIn("Antigravity", cockpit["recommended_structure"]["autonomous_agent_cockpit"]["winner"])
        self.assertGreaterEqual(len(cockpit["detected_mcp_servers"]), 3)
        prov = cockpit["ide_and_antigravity_provisioning"]
        self.assertEqual(prov["status"], "ALL_IDES_AND_ANTIGRAVITY_INTEGRATED")
        self.assertEqual(prov["jetbrains_run_configurations_count"], 14)
        self.assertEqual(prov["vscode_tasks_count"], 8)
        self.assertIn("ideal_multi_ide_role_matrix", cockpit)
        self.assertIn("cli_symlinks_provisioned", prov)
        self.assertTrue(any(p.endswith("lens_cli.py") for p in prov["cli_symlinks_provisioned"]))
        self.assertTrue((REPO_ROOT / ".idea" / "tools" / "External Tools.xml").exists())
        self.assertTrue((REPO_ROOT / ".idea" / "mcp.json").exists())
        self.assertTrue((REPO_ROOT / ".idea" / "go.xml").exists())
        self.assertTrue((REPO_ROOT / ".idea" / "PyGuiSettings.xml").exists())
        self.assertTrue((REPO_ROOT / ".idea" / "sshConfigs.xml").exists())
        self.assertTrue((REPO_ROOT / ".idea" / "webServers.xml").exists())
        self.assertTrue((REPO_ROOT / ".idea" / "deployment.xml").exists())
        self.assertIn("Mac Mini Host", (REPO_ROOT / ".idea" / "webServers.xml").read_text(encoding="utf-8"))
        self.assertIn('autoUpload="Never"', (REPO_ROOT / ".idea" / "deployment.xml").read_text(encoding="utf-8"))
        overview_cfg_xml = (REPO_ROOT / ".idea" / "runConfigurations" / "Lens_Sovereign_Unified_Overview.xml").read_text(encoding="utf-8")
        self.assertIn('type="ShConfigurationType"', overview_cfg_xml)
        self.assertIn("pyui_components_extension_audit", cockpit)
        self.assertEqual(
            cockpit["pyui_components_extension_audit"]["plugin_id"],
            "com.ilscipio.pyuihelper",
        )
        self.assertEqual(
            cockpit["pyui_components_extension_audit"]["verdict_and_action_taken"]["enabled_frameworks"],
            ["FastAPI", "Gradio"],
        )
        self.assertTrue(
            cockpit["pyui_components_extension_audit"]["verdict_and_action_taken"]["disabled_in_jetbrains_disabled_plugins_txt"]
        )
        self.assertTrue((REPO_ROOT / ".vscode" / "settings.json").exists())
        self.assertTrue((REPO_ROOT / ".vscode" / "tasks.json").exists())
        self.assertTrue((REPO_ROOT / ".vscode" / "launch.json").exists())

        bench = DockerCloudflareVsTailscaleBenchmark().run_benchmark(samples=2)
        self.assertEqual(bench["comparative_verdict"]["east_west_winner"], "TAILSCALE_PLUS_DOCKER")
        self.assertEqual(bench["comparative_verdict"]["north_south_winner"], "DOCKER_PLUS_CLOUDFLARE")
        self.assertEqual(bench["warmup_probes_per_target"], 1)
        self.assertIn("live_process_rss_mb", bench)
        self.assertIn("tailscale_direct_vs_derp_audit", bench)
        self.assertIn("thunderbolt4_bridge0_status", bench)
        self.assertIn("audit_of_prior_benchmark_flaws_fixed", bench)
        self.assertIn("hairpin_rtt_breakdown_ms", bench["docker_plus_cloudflare"])
        self.assertGreater(
            bench["docker_plus_cloudflare"]["estimated_east_west_tunnel_hairpin_rtt_ms"],
            0.0,
        )

        # Edge case: unreachable port returns packet_loss_pct == 100.0
        unreachable = DockerCloudflareVsTailscaleBenchmark._measure_tcp_samples("127.0.0.1", 65431, samples=1, timeout=0.05)
        self.assertFalse(unreachable["reachable"])
        self.assertEqual(unreachable["packet_loss_pct"], 100.0)

    def test_sovereign_ai_debate_tri_30b_and_dual_account_free_tier_pool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test_debate.sqlite"
            orch = SovereignAIDebateAndFreeTierOrchestrator(db_path=db_file)

            placement = orch.compute_tri_30b_debate_placement()
            self.assertEqual(len(placement["simultaneous_placement_plan"]), 3)
            self.assertAlmostEqual(placement["total_trio_vram_required_gb"], 58.6, places=1)
            # 58.6 GB > 51.2 GB TB4 safe allocation -> must select Hybrid TB4 + Mesh Sharded Simultaneous
            self.assertFalse(placement["fits_on_tb4_alone_without_sanctuary_breach"])
            self.assertEqual(placement["selected_topology_mode"], "HYBRID_THUNDERBOLT4_PLUS_MESH_SHARDED_SIMULTANEOUS")

            # Edge case: when TB4 capacity >= 58.6 GB or quant_scale=0.80, must select PURE_THUNDERBOLT4_SIMULTANEOUS
            placement_pure_tb4 = orch.compute_tri_30b_debate_placement(tb4_safe_ai_capacity_gb=64.0)
            self.assertTrue(placement_pure_tb4["fits_on_tb4_alone_without_sanctuary_breach"])
            self.assertEqual(placement_pure_tb4["selected_topology_mode"], "PURE_THUNDERBOLT4_SIMULTANEOUS")
            for p_entry in placement_pure_tb4["simultaneous_placement_plan"]:
                self.assertIn("Thunderbolt 4", p_entry["transport"])

            with self.assertRaises(ValueError):
                orch.compute_tri_30b_debate_placement(tb4_safe_ai_capacity_gb=-5.0)

            # Test 2x dual-account free-tier slot allocation across lauburu@lauburugrappling.com and aaron.t.maher@gmail.com
            s1 = orch.allocate_dual_account_free_tier_slot("openrouter_free_tier_dual_account", current_date_utc="2026-10-14", now_ts=1000.0)
            self.assertEqual(s1["status"], "ALLOCATED_2X_DUAL_ACCOUNT_SLOT")
            self.assertEqual(s1["quota_doubling_multiplier"], 2.0)
            self.assertEqual(s1["combined_dual_account_limit"], 400)

            s2 = orch.allocate_dual_account_free_tier_slot("openrouter_free_tier_dual_account", current_date_utc="2026-10-14", now_ts=1001.0)
            self.assertEqual(s2["status"], "ALLOCATED_2X_DUAL_ACCOUNT_SLOT")
            self.assertNotEqual(s1["selected_account"], s2["selected_account"])

            # Edge case: exhaust per-minute RPM limit within same 60s window
            with orch._connect() as conn:
                conn.execute(
                    "UPDATE dual_account_quota_ledger SET requests_in_minute = 25, minute_window_start_ts = 1000.0 "
                    "WHERE provider_id = 'openrouter_free_tier_dual_account'"
                )
                conn.commit()
            s_rpm = orch.allocate_dual_account_free_tier_slot("openrouter_free_tier_dual_account", current_date_utc="2026-10-14", now_ts=1010.0)
            self.assertEqual(s_rpm["status"], "RPM_RATE_LIMIT_COOLDOWN")

            # Advance time by >= 60s -> RPM window resets automatically
            s_rpm_reset = orch.allocate_dual_account_free_tier_slot("openrouter_free_tier_dual_account", current_date_utc="2026-10-14", now_ts=1065.0)
            self.assertEqual(s_rpm_reset["status"], "ALLOCATED_2X_DUAL_ACCOUNT_SLOT")
            self.assertEqual(s_rpm_reset["account_requests_in_minute"], 1)

            # Edge case: exhaust both accounts to >= 83% ceiling and verify QUOTA_BUFFER_SHIELD_ACTIVE
            with orch._connect() as conn:
                conn.execute(
                    "UPDATE dual_account_quota_ledger SET requests_used_today = 170 WHERE provider_id = 'openrouter_free_tier_dual_account'"
                )
                conn.commit()
            s_exhausted = orch.allocate_dual_account_free_tier_slot("openrouter_free_tier_dual_account", current_date_utc="2026-10-14", now_ts=1070.0)
            self.assertEqual(s_exhausted["status"], "QUOTA_BUFFER_SHIELD_ACTIVE")

            # Cross-provider failover cascade must automatically route to next healthy Free-Tier Cloud provider
            failover_slot = orch.allocate_optimal_free_tier_cloud_request("openrouter_free_tier_dual_account")
            self.assertEqual(failover_slot["status"], "ALLOCATED_2X_DUAL_ACCOUNT_SLOT")
            self.assertNotEqual(failover_slot["provider_id"], "openrouter_free_tier_dual_account")
            self.assertGreaterEqual(len(failover_slot["failover_attempts"]), 2)

            # UTC day rollover reset: advancing date to 2026-10-15 resets requests_used_today back to 0!
            s_next_day = orch.allocate_dual_account_free_tier_slot("openrouter_free_tier_dual_account", current_date_utc="2026-10-15", now_ts=90000.0)
            self.assertEqual(s_next_day["status"], "ALLOCATED_2X_DUAL_ACCOUNT_SLOT")
            self.assertEqual(s_next_day["account_requests_used"], 1)

            debate = orch.run_multi_tier_ai_debate("Test architectural debate")
            self.assertEqual(len(debate["local_30b_trio"]), 3)
            self.assertEqual(len(debate["local_30b_debate_rounds"]), 3)
            self.assertEqual(len(debate["frontier_cloud_debate_rounds"]), 4)
            self.assertEqual(len(debate["debate_rounds"]), 7)
            self.assertTrue(debate["consensus_threshold_passed"])
            self.assertIn("artifact_consensus_audit", debate)
            self.assertTrue(all(debate["artifact_consensus_audit"].values()))
            self.assertTrue(Path(debate["lora_dataset_path"]).exists())

    def test_qwen_3d_vla_and_coding_telemetry_auditor(self):
        auditor = Qwen3DVLAAndCodingTelemetryAuditor()
        vla = auditor.run_qwen_3d_vla_audit()
        self.assertIn("Qwen2.5-VL-7B", vla["vla_model"])
        self.assertIn("2d_ui_grounding", vla["capabilities"])
        self.assertIn("3d_spatial_kinematics", vla["capabilities"])
        self.assertEqual(len(vla["sample_3d_spatial_projection"]["pose_6dof_xyz_rpy"]), 6)
        self.assertGreater(vla["sample_3d_spatial_projection"]["estimated_joint_torque_nm"], 0.0)

        with self.assertRaises(ValueError):
            auditor.project_2d_bbox_to_3d_spatial([10, 20])

        code_audit = auditor.audit_monorepo_code_telemetry(max_files=25)
        self.assertEqual(code_audit["python_syntax_health_pct"], 100.0)
        self.assertGreater(code_audit["python_functions_counted"], 10)
        self.assertGreater(code_audit["python_ast_branches_counted"], 10)
        self.assertGreater(code_audit["python_docstrings_counted"], 5)
        self.assertGreater(code_audit["go_functions_counted"], 5)

    def test_self_optimizing_elo_benchmarker_70b_100b_and_model_scout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test_elo.sqlite"
            bench = SelfOptimizingELOBenchmarkerAndModelScout(db_path=db_file)
            res_default = bench.calibrate_and_get_leaderboard()
            self.assertEqual(res_default["consensus_weights"]["user_opinion_weight"], 0.50)
            self.assertEqual(res_default["consensus_weights"]["local_ai_consensus_weight"], 0.25)
            self.assertEqual(res_default["consensus_weights"]["frontier_cloud_consensus_weight"], 0.25)
            self.assertTrue(res_default["internal_algorithmic_benchmark"]["math_identity_verified"])
            self.assertGreaterEqual(len(res_default["leaderboard"]), 13)
            self.assertEqual(len(res_default["task_domain_leaders"]), 6)

            # Verify every model has all 6 task-specific ELO domains
            for entry in res_default["leaderboard"]:
                self.assertEqual(set(entry["task_specific_elos"].keys()), set(bench.TASK_DOMAINS))

            # Edge case: custom user + local AI + cloud AI opinion scores shift calibrated ELO deterministically
            res_custom = bench.calibrate_and_get_leaderboard(
                user_opinion_model="gemma_4_31b",
                user_opinion_score=100.0,
                local_ai_opinion_score=99.0,
                cloud_ai_opinion_score=98.0,
                user_note="Boosted Gemma 4 31B after synthesis win",
            )
            gemma_default = next(m for m in res_default["leaderboard"] if m["model_id"] == "gemma_4_31b")
            gemma_custom = next(m for m in res_custom["leaderboard"] if m["model_id"] == "gemma_4_31b")
            self.assertGreater(gemma_custom["calibrated_elo"], gemma_default["calibrated_elo"])

            # Edge case: invalid model_id or NaN score must raise ValueError
            with self.assertRaises(ValueError):
                bench.calibrate_and_get_leaderboard(user_opinion_model="non_existent_model", user_opinion_score=95.0)
            with self.assertRaises(ValueError):
                bench.calibrate_and_get_leaderboard(user_opinion_model="gemma_4_31b", user_opinion_score=float("nan"))

            # Test 70B & 100B+ Sharded Model Functional & Roofline Physics Benchmark
            heavy = bench.benchmark_70b_and_100b_plus_models()
            self.assertTrue(heavy["functional_tests_summary"]["all_4_functional_pillars_passed"])
            self.assertIn("how_is_this_possible_audit", heavy)
            self.assertIn("tb4_bridge0_hardware_state", heavy)
            self.assertEqual(len(heavy["models_benchmarked"]), 4)
            by_id = {m["model_id"]: m for m in heavy["models_benchmarked"]}
            self.assertTrue(by_id["llama_3_3_70b_abliterated"]["fits_on_tb4_ring_alone"])
            self.assertEqual(by_id["llama_3_3_70b_abliterated"]["selected_sharding_mode"], "PURE_THUNDERBOLT4_4MAC_PRP_RING")
            self.assertFalse(by_id["mistral_large_2_123b_sharded"]["fits_on_tb4_ring_alone"])
            self.assertTrue(by_id["mistral_large_2_123b_sharded"]["fits_in_pooled_mesh_ram_without_nvme_swap"])
            self.assertEqual(by_id["mistral_large_2_123b_sharded"]["selected_sharding_mode"], "FULL_8NODE_HYBRID_TB4_PLUS_MESH_SHARDING")
            ds671 = by_id["deepseek_v3_r1_671b_moe_halda"]
            self.assertEqual(ds671["selected_sharding_mode"], "PRIMA_HALDA_NVME_MMAP_RING_PLUS_MOE_ACTIVE_ROUTING")
            self.assertIn("roofline_physics_breakdown", ds671)
            self.assertAlmostEqual(ds671["roofline_physics_breakdown"]["cold_nvme_mmap_fault_gb_per_tok"], 3.12, places=2)
            # Local Halda NVMe swap must report realistic <2.0 tok/s (~0.92 tok/s), while 160GB zero-swap reports 11.35 tok/s
            self.assertLess(ds671["estimated_local_throughput_tok_s"], 2.0)
            self.assertAlmostEqual(ds671["zero_nvme_swap_160gb_ram_throughput_tok_s"], 11.35, places=2)
            self.assertGreater(ds671["effective_throughput_with_cloud_mirror_tok_s"], 25.0)

            # Test exact .gguf filename matching in scout_and_stage_model_downloads
            fake_vault = Path(tmpdir) / "vault"
            fake_vault.mkdir(parents=True, exist_ok=True)
            (fake_vault / "qwen2.5-coder-7b-instruct-q4_k_m.gguf").write_bytes(b"GGUF_TEST")
            scout = bench.scout_and_stage_model_downloads(extra_vault_dirs=[fake_vault])
            staged_by_id = {m["model_id"]: m for m in scout["staged_local_models"]}
            self.assertTrue(staged_by_id["qwen_2_5_coder_7b_pypi"]["present_in_local_vault"])
            self.assertFalse(staged_by_id["qwen_38_max_abliterated_27b"]["present_in_local_vault"])
            self.assertFalse(staged_by_id["qwen_3d_vla_7b"]["present_in_local_vault"])

            # Test closed-loop self_optimize_project
            opt = bench.self_optimize_project(user_opinion_model="gemma_4_31b", user_opinion_score=99.0)
            self.assertIn("optimized_task_routing_table", opt)
            self.assertEqual(len(opt["optimized_task_routing_table"]), 6)
            self.assertTrue(opt["heavy_70b_100b_plus_benchmark_summary"]["all_4_functional_pillars_passed"])

    def test_sqlite_wal_multi_thread_concurrency(self):
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "concurrent.sqlite"
            mem = CognitiveMemoryAndDualAccountOrchestrator(db_path=db_file)
            deb = SovereignAIDebateAndFreeTierOrchestrator(db_path=db_file)

            def _worker(idx: int) -> bool:
                mem.put_working_memory(f"k_{idx}", {"idx": idx}, ttl_sec=60.0)
                mem.record_bitemporal_fact(f"Subj_{idx % 4}", "STATE", f"v_{idx}")
                slot = deb.allocate_dual_account_free_tier_slot("groq_free_tier_dual_account")
                return slot["status"] == "ALLOCATED_2X_DUAL_ACCOUNT_SLOT"

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(_worker, range(40)))
            self.assertTrue(all(results))

    def test_on_demand_nvidia_7b_voice_coder_non_24_7_lifecycle(self):
        self.assertIs(MovesensePixelOnlyGattSerialBridge, MovesenseGattBluetoothSerialBridge)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "voice_coder.sqlite"
            vc = OnDemandNvidiaVoiceCoderManager(db_path=db_file)

            status = vc.get_status()
            self.assertEqual(status["model_id"], "nvidia_nemotron_voice_coder_7b")
            self.assertEqual(status["port"], 8095)
            self.assertEqual(status["residency_policy"], "ON_DEMAND_EPHEMERAL_ONLY")
            self.assertFalse(status["live_24_7"])
            self.assertEqual(status["idle_ram_mb_when_stopped"], 0.0)
            # Verify 24/7 resident companions are explicitly marked live_24_7=True
            for comp_key in (
                "lens_sovereign_core",
                "pi_and_py_pi_coding_agents",
                "embedding_gemma_2_mrl",
                "qwen_3d_vla",
            ):
                self.assertTrue(status["resident_24_7_companions"][comp_key]["live_24_7"])
                self.assertEqual(
                    status["resident_24_7_companions"][comp_key]["residency_policy"],
                    "LIVE_24_7_ALWAYS_ON",
                )

            # Edge cases for spoken code normalization
            with self.assertRaises(ValueError):
                vc.normalize_spoken_code_utterance("   ")
            norm = vc.normalize_spoken_code_utterance(
                "def verify underscore pixel underscore guard open paren host underscore id close paren colon return True"
            )
            self.assertIn("verify_pixel_guard(host_id):", norm["normalized_code_intent"])
            self.assertTrue(norm["spoken_tokens_converted"])

            # Edge cases for ephemeral session TTL bounds (cannot exceed 600s or be <= 0)
            with self.assertRaises(ValueError):
                vc.start_ephemeral_session(ttl_sec=0.0)
            with self.assertRaises(ValueError):
                vc.start_ephemeral_session(ttl_sec=86400.0)

            # Full transcribe-and-code turn with auto_unload=True must unload back to 0.0 MB RAM
            turn = vc.transcribe_and_execute_voice_coding(
                "define check underscore mesh underscore health open paren close paren colon return True",
                auto_unload=True,
            )
            self.assertFalse(turn["live_24_7"])
            self.assertEqual(turn["residency_policy"], "ON_DEMAND_EPHEMERAL_ONLY")
            self.assertTrue(turn["resident_24_7_pipeline_integration"]["py_pi_and_pi_execution"]["ast_syntax_verified"])
            self.assertTrue(turn["session_unloaded_after_turn"])
            self.assertEqual(turn["post_turn_resident_ram_mb"], 0.0)
            self.assertEqual(turn["unload_receipt"]["session_state"], "UNLOADED_ZERO_IDLE_RAM")
            self.assertIsNone(vc.mem.get_working_memory(vc.LEASE_KEY))

    def test_junie_thunderbolt_mesh_integrator(self):
        res = JunieThunderboltMeshIntegrator.provision_junie_thunderbolt_mesh(
            task_prompt="Audit and shard monorepo inspections across Thunderbolt 4 ring"
        )
        self.assertIn("why_junie_was_not_directly_tensor_sharded", res)
        self.assertIn("CLI agent harness binary", res["why_junie_was_not_directly_tensor_sharded"])
        self.assertIn("tier_1_tb4_sharded_llm_backend", res)
        self.assertEqual(
            res["tier_1_tb4_sharded_llm_backend"]["environment"]["OPENAI_BASE_URL"],
            "http://10.0.0.1:8085/v1",
        )
        tb4_plan = res["tier_1_tb4_sharded_llm_backend"]["tb4_70b_80_layer_ring_allocation"]
        self.assertEqual(tb4_plan["total_layers"], 80)
        self.assertEqual(tb4_plan["unassigned_layers"], 0)

        tier2 = res["tier_2_multi_node_task_sharding_pool"]
        self.assertEqual(tier2["total_module_shards"], 6)
        self.assertGreater(tier2["estimated_parallel_speedup_x"], 3.5)
        shard_nodes = [s["node_id"] for s in tier2["worker_shards"]]
        self.assertEqual(shard_nodes, ["L1", "L5", "L1b", "L2", "L8", "L3"])

        tier3 = res["tier_3_sovereign_companion_integrations"]
        self.assertEqual(tier3["nvidia_7b_voice_coder"]["residency_policy"], "ON_DEMAND_EPHEMERAL_ONLY")
        self.assertFalse(tier3["nvidia_7b_voice_coder"]["live_24_7"])
        self.assertEqual(tier3["embedding_gemma_2_mrl"]["residency_policy"], "LIVE_24_7_ALWAYS_ON")
        self.assertEqual(tier3["qwen_3d_vla"]["residency_policy"], "LIVE_24_7_ALWAYS_ON")

        with self.assertRaises(ValueError):
            JunieThunderboltMeshIntegrator.compute_task_sharding_plan("")

    def test_s20_long_term_persistence_healer_and_tplink_decommission(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test_s20_heal.sqlite"
            healer = S20LongTermPersistenceHealer(db_path=db_file)
            res = healer.execute_s20_long_term_heal(fast_mode=True, apply_router_dhcp_reservations=False)
            self.assertIn(
                res["status"],
                (
                    "S20_LIVE_IMMORTALIZED",
                    "S20_WAKE_REQUIRED_7_POINT_IMMORTALIZER_AND_ROUTER_DHCP_STAGED",
                ),
            )
            self.assertEqual(res["s20_7_point_immortalization_plan"]["total_steps"], 7)
            self.assertTrue(res["immortalization_script_exists"])
            self.assertEqual(
                res["tp_link_extender_audit"]["tplink_wifi_extender_project_status"],
                "DECOMMISSIONED_AND_REMOVED_FROM_PROJECT",
            )
            self.assertEqual(
                res["tp_link_extender_audit"]["pixel_l6_wired_usb_ethernet_192_168_8_116"]["ip"],
                "192.168.8.116",
            )

            # Verify decommissioned TP-Link Extender is absent from active mesh scripts
            for active_script in (
                REPO_ROOT / "00_core_infrastructure" / "multi_wan" / "service_keepalive.py",
                REPO_ROOT / "06_scripts_and_tooling" / "network" / "multiwan_bond_manager.py",
                REPO_ROOT / "06_scripts_and_tooling" / "network" / "tensor_multipath_router.py",
                REPO_ROOT / "06_scripts_and_tooling" / "networking" / "lauburu_network_cli.py",
            ):
                txt = active_script.read_text(encoding="utf-8")
                self.assertNotIn("TPLink_Extender_Ethernet", txt)
                self.assertNotIn("linux_tplink_eth", txt)
                self.assertNotIn("TP-Link VX230v AP", txt)

            # Verify FullNetworkSovereignDeployer tarball builder & full-network probe/sync
            deployer = FullNetworkSovereignDeployer(db_path=db_file)
            tar_bytes, files_included, sha256_hex = deployer._build_sync_tarball()
            self.assertGreater(len(tar_bytes), 1000)
            self.assertGreaterEqual(len(files_included), 20)
            self.assertEqual(len(sha256_hex), 64)
            net_sync = deployer.sync_across_full_network(fast_probe_only=True)
            self.assertEqual(net_sync["status"], "FULL_NETWORK_DEPLOYED_AND_SYNCHRONIZED")
            self.assertIn("L5", net_sync["nodes_deployed_live"])
            self.assertGreaterEqual(len(net_sync["node_deployment_receipts"]), 9)

    def test_lens_24x7_automation_training_protocol_and_scrcpy5_page_assist_devtools(self):
        import threading

        for subdir in ("data", "automation", "network"):
            p_str = str(REPO_ROOT / "06_scripts_and_tooling" / subdir)
            if p_str not in sys.path:
                sys.path.append(p_str)
        from lens_automation_distiller import (
            Lens24x7AutomationTrainingProtocol,
            extract_adb_shizuku,
            extract_chrome_devtools,
            extract_computer_use,
        )
        from smart_scrcpy_wrapper import get_scrcpy_5_sovereign_profile, pick_device_noninteractive
        from chrome_devtools_sentinel_bridge import ChromeDevToolsAIBridge
        from speculative_cli_data_engine import SpeculativeCommandDrafter

        # 1. Verify Scrcpy 5.0 Sovereign UHID Profile, Multi-Device Selection & SDK < 30 Fallback
        scrcpy_prof = get_scrcpy_5_sovereign_profile("192.168.8.101:32873")
        self.assertEqual(scrcpy_prof["protocol"], "Scrcpy 5.0 Sovereign UHID")
        self.assertEqual(scrcpy_prof["keyboard_mode"], "uhid")
        self.assertEqual(scrcpy_prof["mouse_mode"], "uhid")
        self.assertEqual(scrcpy_prof["max_fps"], 60)
        self.assertEqual(scrcpy_prof["video_bit_rate"], "16M")
        self.assertIn("--keyboard=uhid", scrcpy_prof["command"])
        self.assertIn("--mouse=uhid", scrcpy_prof["command"])
        self.assertIn("2>&1", scrcpy_prof["shizuku_rish_command_template"])

        # Multi-device non-interactive selection: must prefer L7 Samsung S20+ over L6 Sanctuary Pixel
        mock_dual_devices = [
            {"serial": "192.168.8.116:5555", "info": "device product:mustang model:Pixel_10_Pro_XL"},
            {"serial": "192.168.8.101:32873", "info": "device product:y2sxxx model:SM_G986B"},
        ]
        self.assertEqual(pick_device_noninteractive(mock_dual_devices), "192.168.8.101:32873")
        dual_prof = get_scrcpy_5_sovereign_profile(devices_override=mock_dual_devices, sdk_override=33)
        self.assertEqual(dual_prof["target_serial"], "192.168.8.101:32873")
        self.assertEqual(dual_prof["online_devices_count"], 2)
        self.assertTrue(dual_prof["uhid_hardware_hid_supported"])

        # SDK < 30 fallback: must select sdk keyboard/mouse mode instead of uhid
        legacy_sdk_prof = get_scrcpy_5_sovereign_profile(
            serial="192.168.8.101:5555",
            sdk_override=29,
            devices_override=mock_dual_devices,
        )
        self.assertEqual(legacy_sdk_prof["android_sdk"], 29)
        self.assertFalse(legacy_sdk_prof["uhid_hardware_hid_supported"])
        self.assertEqual(legacy_sdk_prof["keyboard_mode"], "sdk")
        self.assertEqual(legacy_sdk_prof["mouse_mode"], "sdk")
        self.assertIn("--keyboard=sdk", legacy_sdk_prof["command"])

        # 2. Verify all 3 domain extractors produce authentic deduplicated instruction/input/output pairs
        cdt_pairs = extract_chrome_devtools(limit=10)
        adb_pairs = extract_adb_shizuku(limit=10)
        cu_pairs = extract_computer_use(limit=10)
        self.assertGreaterEqual(len(cdt_pairs), 1)
        self.assertGreaterEqual(len(adb_pairs), 1)
        self.assertGreaterEqual(len(cu_pairs), 1)
        for domain_list in (cdt_pairs, adb_pairs, cu_pairs):
            keys = [(p["instruction"], p["input"], p["output"]) for p in domain_list]
            self.assertEqual(len(keys), len(set(keys)), "Duplicate records returned by domain extractor")
        for p in cdt_pairs + adb_pairs + cu_pairs:
            self.assertIn("instruction", p)
            self.assertIn("input", p)
            self.assertIn("output", p)
            self.assertIn("domain", p)
            self.assertIn("gemma2_mrl_dims", p)
            self.assertEqual(p["gemma2_mrl_dims"], [768, 512, 256, 128])

        # 3. Verify EmbeddingGemma 2 MRL bundle edge cases (empty string and standard string)
        with tempfile.TemporaryDirectory() as tmpdir:
            proto = Lens24x7AutomationTrainingProtocol(output_dir=Path(tmpdir))
            mrl_empty = proto.compute_gemma2_mrl_bundle("   ")
            self.assertEqual(mrl_empty["dimensions"], [768, 512, 256, 128])
            for dim_key, dim_len in (("768d", 768), ("512d", 512), ("256d", 256), ("128d", 128)):
                vec = mrl_empty["vectors"][dim_key]
                self.assertEqual(len(vec), dim_len)
                norm = sum(v * v for v in vec) ** 0.5
                self.assertAlmostEqual(norm, 1.0, places=3)

            # 4. Verify safety invariants: normal state, destructive CLI, human browser hijack, and low-RAM offload
            inv_ok = proto.evaluate_safety_invariants(candidate_commands=["adb devices", "lens status"])
            self.assertEqual(inv_ok["invariants_count"], 5)
            self.assertFalse(inv_ok["invariants"]["INV_3_COMMAND_AND_AST_SAFETY"]["destructive_commands_rejected"])
            self.assertTrue(inv_ok["invariants"]["INV_2_HUMAN_BROWSER_SANCTUARY"]["passed"])
            self.assertTrue(inv_ok["invariants"]["INV_4_ROOT_SHIZUKU_RISH_SCRCPY5"]["passed"])
            self.assertTrue(inv_ok["invariants"]["INV_5_PAGE_ASSIST_CHROME_DEVTOOLS_EXTENSION"]["passed"])

            inv_bad = proto.evaluate_safety_invariants(
                candidate_commands=[
                    "rm -rf /",
                    "rm -rf /*",
                    "rm -r -f /",
                    "mkfs.ext4 /dev/sda1",
                    "dd if=/dev/zero of=/dev/disk0",
                ]
            )
            self.assertFalse(inv_bad["invariants"]["INV_3_COMMAND_AND_AST_SAFETY"]["passed"])
            self.assertFalse(inv_bad["all_safety_invariants_passed"])
            self.assertEqual(len(inv_bad["invariants"]["INV_3_COMMAND_AND_AST_SAFETY"]["destructive_commands_rejected"]), 5)

            # Human Browser Sanctuary hijack must be rejected by INV_2
            inv_browser_hijack = proto.evaluate_safety_invariants(
                candidate_commands=[
                    'osascript -e \'tell application "Google Chrome" to activate\'',
                    "curl -s http://127.0.0.1:9222/json/list",
                ]
            )
            self.assertFalse(inv_browser_hijack["invariants"]["INV_2_HUMAN_BROWSER_SANCTUARY"]["passed"])
            self.assertEqual(
                len(inv_browser_hijack["invariants"]["INV_2_HUMAN_BROWSER_SANCTUARY"]["human_browser_violations"]),
                2,
            )
            self.assertFalse(inv_browser_hijack["all_safety_invariants_passed"])

            # Low-RAM (<15%) M4 Sanctuary simulation must block local MLX and offload to L8/L1
            low_ram_cycle = proto.run_training_cycle(
                trigger_mlx_trainer=True,
                simulated_free_ram_pct=9.5,
            )
            self.assertEqual(
                low_ram_cycle["safety_verification"]["invariants"]["INV_1_HOST_SANCTUARY_RAM"]["execution_mode"],
                "REMOTE_OFFLOAD_TO_L8_AND_L1_SANCTUARY_ENFORCED",
            )
            self.assertFalse(
                low_ram_cycle["safety_verification"]["invariants"]["INV_1_HOST_SANCTUARY_RAM"]["local_mlx_allowed"]
            )
            self.assertTrue(low_ram_cycle["mlx_argon_trainer"]["offloaded_to_remote_mesh"])
            self.assertFalse(low_ram_cycle["mlx_argon_trainer"]["triggered"])
            # Exact non-duplicate JSONL write check on first cycle
            self.assertEqual(
                low_ram_cycle["dataset_total_lines"],
                low_ram_cycle["samples_distilled_this_cycle"],
            )

            # 5. Run a full training cycle, target_score check, train_until_converged, /boost, and /teamwork-preview
            cycle_res = proto.run_training_cycle(boost=True, target_score=95.0)
            self.assertTrue(cycle_res["boost_enabled"])
            self.assertGreaterEqual(cycle_res["total_pairs_harvested_cycle"], 3)
            self.assertTrue(cycle_res["safe_full_network_automation_converged"])
            self.assertTrue(Path(cycle_res["dataset_jsonl"]).exists())
            self.assertTrue(Path(cycle_res["status_json"]).exists())
            self.assertIn("mesh_coverage", cycle_res)
            self.assertEqual(cycle_res["mesh_coverage"]["total_layers"], 8)
            self.assertGreaterEqual(cycle_res["mesh_coverage"]["coverage_pct"], 95.0)
            self.assertTrue(cycle_res["mesh_coverage"]["target_converged"])

            # Verify target_score > 100.0 properly reports safe_full_network_automation_converged=False
            unconverged_res = proto.run_training_cycle(target_score=105.0)
            self.assertFalse(unconverged_res["safe_full_network_automation_converged"])

            conv_loop = proto.train_until_converged(target_score=95.0, max_cycles=3, boost=True)
            self.assertTrue(conv_loop["converged"])
            self.assertEqual(conv_loop["cycles_executed"], 1)

            burst_res = proto.run_continuous_burst(cycles=2, boost=True, target_score=95.0)
            self.assertEqual(burst_res["cycles_executed"], 2)
            self.assertTrue(burst_res["boost_enabled"])

            teamwork = proto.get_teamwork_preview_plan()
            self.assertEqual(teamwork["mode"], "teamwork-preview")
            self.assertEqual(len(teamwork["agents"]), 4)

            guide = proto.get_automated_task_guide()
            self.assertEqual(len(guide["step_by_step_task_creation_guide"]), 6)
            self.assertIn("automation_sidecar_spec", guide)
            self.assertIn("teamwork_preview", guide)
            sidecar_spec = guide["automation_sidecar_spec"]
            self.assertEqual(sidecar_spec["builtin"], "schedule")
            self.assertEqual(sidecar_spec["restart_policy"], "always")
            self.assertEqual(
                sidecar_spec["display_name"],
                "24/7 Screen Lens Safe Network Automation Trainer",
            )
            sidecar_disk_path = Path("/Volumes/.gemini/config/sidecars/lens-247-automation-trainer/sidecar.json")
            if not sidecar_disk_path.exists():
                sidecar_disk_path = Path.home() / ".gemini" / "config" / "sidecars" / "lens-247-automation-trainer" / "sidecar.json"
            self.assertTrue(sidecar_disk_path.exists(), f"Missing sidecar.json at {sidecar_disk_path}")
            sidecar_disk_json = json.loads(sidecar_disk_path.read_text(encoding="utf-8"))
            self.assertEqual(sidecar_disk_json["builtin"], "schedule")
            self.assertEqual(sidecar_disk_json["restart_policy"], "always")
            self.assertEqual(
                sidecar_disk_json["display_name"],
                "24/7 Screen Lens Safe Network Automation Trainer",
            )
            self.assertTrue(sidecar_disk_json["args"][0].startswith("CRON_TZ=Australia/Melbourne "))
            self.assertEqual(sidecar_disk_json["args"][1:4], ["agentapi", "new-conversation", "--"])
            self.assertIn("file:///Volumes/Lauburu-Monorepo", sidecar_disk_json["agent_permissions"]["workspace_uris"])
            grants = sidecar_disk_json["agent_permissions"]["access_grants"]
            self.assertGreaterEqual(len(grants), 5)
            for grant in grants:
                self.assertNotIn("*", grant, f"Wildcard permission forbidden in sidecar.json: {grant}")

            # 6. Multi-threaded fcntl.flock concurrency test on shared JSONL file
            shared_jsonl = Path(tmpdir) / "concurrent_flock_test.jsonl"
            concurrent_proto = Lens24x7AutomationTrainingProtocol(
                dataset_path=shared_jsonl,
                output_dir=Path(tmpdir),
            )
            errors: list = []

            def _worker_cycle():
                try:
                    for _ in range(3):
                        concurrent_proto.run_training_cycle(limit_per_domain=2)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=_worker_cycle) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15.0)
            self.assertEqual(errors, [])
            raw_lines = [ln for ln in shared_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertGreaterEqual(len(raw_lines), 12)
            for ln in raw_lines:
                parsed_obj = json.loads(ln)
                self.assertIn("sha256", parsed_obj)

        # 7. Verify ChromeDevToolsAIBridge Page Assist (:11434) and 24/7 Automation Protocol endpoints
        bridge = ChromeDevToolsAIBridge()
        pa_status = bridge.get_page_assist_status()
        self.assertIn(pa_status["status"], ("online", "standby_configurable"))
        self.assertGreaterEqual(pa_status["models_count"], 4)
        full_status = bridge.get_full_status()
        self.assertIn("page_assist", full_status)
        self.assertEqual(full_status["device_fleet_policy"]["human_chrome_protection"], "ENFORCED_ZERO_CDP_ZERO_OSASCRIPT")
        bridge_preview = bridge.run_automation_protocol({"mode": "teamwork-preview"})
        self.assertEqual(bridge_preview["mode"], "teamwork-preview")

        # Verify Chrome Extension MV3 manifest v2.7.0 and service worker handlers
        ext_dir = REPO_ROOT / "01_apps" / "screen_lens" / "chrome_extension"
        manifest = json.loads((ext_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["version"], "2.7.0")
        self.assertIn("http://127.0.0.1:11434/*", manifest["host_permissions"])
        sw_text = (ext_dir / "service_worker.js").read_text(encoding="utf-8")
        self.assertIn("LENS_PAGE_ASSIST_STATUS", sw_text)
        self.assertIn("LENS_AUTOMATION_TRAIN_247", sw_text)

        # 8. Verify SpeculativeCommandDrafter deterministic routing for the user's natural language prompt
        drafter = SpeculativeCommandDrafter()
        draft = drafter.draft(
            "/automation Guide me through creating an automated task - Lens - qwen 3d - gemma 2 - "
            "run a 24/7 lens automation training protocol, use root, shiziku, rish, scrcpy 5.0and page assist "
            "/chrome-devtools /chrome-extensions /goal continiously train until you can fully autoamte "
            "the entire network safely /teamwork-preview /boost"
        )
        self.assertEqual(draft.safety_rating, "SAFE")
        joined_args = " ".join(draft.suggested_args)
        self.assertIn("automate-247", joined_args)
        self.assertIn("--until-converged", joined_args)
        self.assertIn("--teamwork-preview", joined_args)
        self.assertIn("--boost", joined_args)

        # 9. Verify read-only directory (chmod 0o555) resilience without PermissionError crash
        with tempfile.TemporaryDirectory() as ro_parent:
            ro_path = Path(ro_parent) / "readonly_vault"
            ro_path.mkdir(parents=True, exist_ok=True)
            os.chmod(ro_path, 0o555)
            try:
                ro_proto = Lens24x7AutomationTrainingProtocol(output_dir=ro_path / "unwritable_subdir")
                ro_res = ro_proto.run_training_cycle(boost=True, target_score=95.0)
                self.assertEqual(ro_res["status"], "COMPLETED")
                self.assertFalse(ro_res["dataset_write_succeeded"])
                self.assertGreaterEqual(len(ro_res["persistence_warnings"]), 1)
            finally:
                os.chmod(ro_path, 0o755)

    def test_lens_24x7_cli_subprocess_and_python314_argparse(self):
        py_bin = "/opt/homebrew/bin/python3" if os.path.exists("/opt/homebrew/bin/python3") else sys.executable
        distiller_script = REPO_ROOT / "06_scripts_and_tooling" / "data" / "lens_automation_distiller.py"
        lens_script = REPO_ROOT / "06_scripts_and_tooling" / "lens_cli.py"
        unified_script = REPO_ROOT / "06_scripts_and_tooling" / "lens_sovereign_unified_system.py"

        # 1. Verify --help formatting on both parsers does not raise ValueError on Python 3.14
        for script_path in (distiller_script, unified_script):
            help_proc = subprocess.run(
                [py_bin, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=15.0,
            )
            self.assertEqual(help_proc.returncode, 0, f"{script_path} --help failed: {help_proc.stderr}")
            self.assertIn("--target-score", help_proc.stdout)

        # 2. Verify lens_automation_distiller.py --once --boost --target-score 95.0 --no-mlx --json
        dist_proc = subprocess.run(
            [
                py_bin,
                str(distiller_script),
                "--once",
                "--boost",
                "--target-score",
                "95.0",
                "--no-mlx",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=25.0,
        )
        self.assertEqual(dist_proc.returncode, 0, f"lens_automation_distiller.py CLI failed: {dist_proc.stderr}")
        dist_payload = json.loads(dist_proc.stdout)
        self.assertEqual(dist_payload["status"], "COMPLETED")
        self.assertTrue(dist_payload["boost_enabled"])
        self.assertTrue(dist_payload["safe_full_network_automation_converged"])
        if dist_payload["safety_verification"]["invariants"]["INV_5_PAGE_ASSIST_CHROME_DEVTOOLS_EXTENSION"]["embeddinggemma2_8087_online"]:
            self.assertIn("embeddinggemma-2", dist_payload["gemma2_mrl_verification"]["provider"])

        # 3. Verify lens_cli.py automate-247 --boost --json
        cli_proc = subprocess.run(
            [py_bin, str(lens_script), "automate-247", "--boost", "--json"],
            capture_output=True,
            text=True,
            timeout=25.0,
        )
        self.assertEqual(cli_proc.returncode, 0, f"lens_cli.py automate-247 --boost --json failed: {cli_proc.stderr}")
        cli_payload = json.loads(cli_proc.stdout)
        self.assertEqual(cli_payload["status"], "COMPLETED")
        self.assertTrue(cli_payload["boost_enabled"])
        self.assertIn("automated_task_guide", cli_payload)
        self.assertIn("teamwork_preview", cli_payload)

        # 4. Verify combined --until-converged --target-score 95.0 --boost --teamwork-preview --guide --no-mlx --json
        comb_proc = subprocess.run(
            [
                py_bin,
                str(distiller_script),
                "--until-converged",
                "--target-score",
                "95.0",
                "--boost",
                "--teamwork-preview",
                "--guide",
                "--no-mlx",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=25.0,
        )
        self.assertEqual(comb_proc.returncode, 0, f"Combined until-converged CLI failed: {comb_proc.stderr}")
        comb_payload = json.loads(comb_proc.stdout)
        self.assertEqual(comb_payload["mode"], "train_until_converged")
        self.assertTrue(comb_payload["converged"])
        self.assertIn("teamwork_preview", comb_payload)
        self.assertIn("automated_task_guide", comb_payload)

        # 5. Verify --daemon --interval 1 --max-cycles 2 --boost --no-mlx --json under a read-only output directory
        with tempfile.TemporaryDirectory() as ro_dir:
            ro_sub = Path(ro_dir) / "ro_daemon"
            ro_sub.mkdir(parents=True, exist_ok=True)
            os.chmod(ro_sub, 0o555)
            try:
                daemon_proc = subprocess.run(
                    [
                        py_bin,
                        str(distiller_script),
                        "--daemon",
                        "--interval",
                        "1",
                        "--max-cycles",
                        "2",
                        "--boost",
                        "--no-mlx",
                        "--output-dir",
                        str(ro_sub / "nested"),
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=25.0,
                )
                self.assertEqual(daemon_proc.returncode, 0, f"Daemon CLI failed on read-only dir: {daemon_proc.stderr}")
                daemon_lines = [ln for ln in daemon_proc.stdout.splitlines() if ln.strip()]
                self.assertEqual(len(daemon_lines), 2)
                for ln in daemon_lines:
                    cycle_obj = json.loads(ln)
                    self.assertEqual(cycle_obj["status"], "COMPLETED")
                    self.assertFalse(cycle_obj["dataset_write_succeeded"])
            finally:
                os.chmod(ro_sub, 0o755)

    def test_polyglot_specialists_ide_and_runtime_integration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir) / "monorepo"
            tmp_root.mkdir(parents=True, exist_ok=True)

            integrator = PolyglotSpecialistIDEAndRuntimeIntegrator(repo_root=tmp_root)

            # 1. Verify all 6 requested polyglot specialist SKILL.md files exist and have valid SHA256
            skill_audit = integrator.audit_skill_files()
            self.assertEqual(len(skill_audit), 6)
            for sk_id in (
                "polyglot-go-bubbletea-specialist",
                "polyglot-kotlin-android-specialist",
                "polyglot-c-cpp-specialist",
                "polyglot-python-specialist",
                "polyglot-rust-wgpu-specialist",
                "polyglot-typescript-web-specialist",
            ):
                self.assertIn(sk_id, skill_audit)
                self.assertTrue(skill_audit[sk_id]["exists"])
                self.assertGreater(skill_audit[sk_id]["size_bytes"], 100)
                self.assertEqual(len(skill_audit[sk_id]["sha256"]), 64)

            # 2. Verify full integration across GoLand (langgo), PyCharm, IntelliJ IDEA (all 6), Chromium & Bluetooth Serial
            full_report = integrator.integrate_and_benchmark_all(repo_root=REPO_ROOT, target="all")
            self.assertEqual(
                full_report["status"],
                "ALL_6_POLYGLOT_SPECIALISTS_INTEGRATED_AND_BENCHMARKED",
            )
            self.assertTrue(full_report["all_6_skills_present"])
            self.assertTrue((REPO_ROOT / ".idea" / "specialist_skills_matrix.json").exists())

            ide_prov = full_report["ide_specialist_integrations"]
            # GoLand ("langgo") -> polyglot-go-bubbletea-specialist
            self.assertEqual(
                ide_prov["goland_langgo"]["primary_specialist"],
                "polyglot-go-bubbletea-specialist",
            )
            self.assertIn("langgo", ide_prov["goland_langgo"]["aliases"])

            # PyCharm -> polyglot-python-specialist
            self.assertEqual(
                ide_prov["pycharm"]["primary_specialist"],
                "polyglot-python-specialist",
            )

            # IntelliJ IDEA -> all 6 polyglot specialists
            self.assertEqual(
                len(ide_prov["intellij_idea"]["integrated_specialists"]),
                6,
            )
            for req_sk in (
                "polyglot-go-bubbletea-specialist",
                "polyglot-kotlin-android-specialist",
                "polyglot-c-cpp-specialist",
                "polyglot-python-specialist",
                "polyglot-rust-wgpu-specialist",
                "polyglot-typescript-web-specialist",
            ):
                self.assertIn(req_sk, ide_prov["intellij_idea"]["integrated_specialists"])

            # 3. Verify Empirical Chromium Benchmark & Winner Selection
            chromium_bm = full_report["runtime_empirical_selection"]["chromium"]
            self.assertEqual(chromium_bm["winning_primary_specialist"], "polyglot-typescript-web-specialist")
            self.assertTrue(chromium_bm["mv3_manifest_valid"])
            self.assertTrue(chromium_bm["mv3_service_worker_valid"])
            self.assertEqual(len(chromium_bm["candidate_rankings"]), 6)
            self.assertIn("polyglot-rust-wgpu-specialist", chromium_bm["winning_specialist_stack"])

            # 4. Verify Empirical Bluetooth Serial Terminal (:4005) Benchmark & Winner Selection
            bt_bm = full_report["runtime_empirical_selection"]["bluetooth_serial_terminal"]
            self.assertEqual(bt_bm["winning_primary_specialist"], "polyglot-c-cpp-specialist")
            self.assertTrue(bt_bm["c11_parser_verified"])
            self.assertTrue(bt_bm["python_daemon_verified"])
            self.assertTrue(bt_bm["go_bubbletea_cli_verified"])
            self.assertEqual(len(bt_bm["candidate_rankings"]), 6)
            for req_bt_sk in (
                "polyglot-c-cpp-specialist",
                "polyglot-python-specialist",
                "polyglot-go-bubbletea-specialist",
                "polyglot-kotlin-android-specialist",
            ):
                self.assertIn(req_bt_sk, bt_bm["winning_specialist_stack"])

            # 5. Verify target_filter edge cases ("langgo", "pycharm", "intellij", "chromium", "bt-serial")
            for filt in ("langgo", "pycharm", "intellij", "chromium", "bt-serial"):
                sub_rep = integrator.integrate_and_benchmark_all(repo_root=tmp_root, target_filter=filt)
                self.assertEqual(sub_rep["requested_target"], filt)
                self.assertTrue((tmp_root / ".idea" / "specialist_skills_matrix.json").exists())

        # 6. Verify LensOmniscientRouter.resolve_ide_and_runtime_specialist & runtime daemons
        screen_lens_src = str(REPO_ROOT / "01_apps" / "screen_lens" / "src")
        if screen_lens_src not in sys.path:
            sys.path.insert(0, screen_lens_src)
        from lens_omniscient_router import LensOmniscientRouter
        from chrome_devtools_sentinel_bridge import ChromeDevToolsAIBridge
        import bluetooth_serial_terminal_daemon as bt_daemon

        router = LensOmniscientRouter()
        r_go = router.resolve_ide_and_runtime_specialist("langgo", "Bubble Tea Elm TUI")
        self.assertEqual(r_go["primary_specialist"], "polyglot-go-bubbletea-specialist")

        r_py = router.resolve_ide_and_runtime_specialist("pycharm", "FastAPI PySpark")
        self.assertEqual(r_py["primary_specialist"], "polyglot-python-specialist")

        r_ij = router.resolve_ide_and_runtime_specialist("intellij", "Kotlin Android JNI")
        self.assertEqual(r_ij["primary_specialist"], "polyglot-kotlin-android-specialist")
        self.assertGreaterEqual(len(r_ij["active_specialists"]), 6)

        r_cr_ts = router.resolve_ide_and_runtime_specialist("chromium", "Manifest V3 service worker")
        self.assertEqual(r_cr_ts["primary_specialist"], "polyglot-typescript-web-specialist")

        r_cr_gpu = router.resolve_ide_and_runtime_specialist("chromium", "WebGPU WGSL compute shader")
        self.assertEqual(r_cr_gpu["primary_specialist"], "polyglot-rust-wgpu-specialist")

        r_bt_c = router.resolve_ide_and_runtime_specialist("bt-serial", "POSIX termios TIOCM_CAR C11")
        self.assertEqual(r_bt_c["primary_specialist"], "polyglot-c-cpp-specialist")

        r_bt_ecg = router.resolve_ide_and_runtime_specialist("bt-serial", "Movesense 512Hz ECG HRV")
        self.assertEqual(r_bt_ecg["primary_specialist"], "polyglot-python-specialist")

        # Verify ChromeDevToolsAIBridge & Bluetooth Serial Terminal daemon specialist integration
        bridge = ChromeDevToolsAIBridge()
        cr_spec = bridge.get_chromium_specialist_status()
        self.assertEqual(cr_spec["primary_specialist"], "/polyglot-typescript-web-specialist")
        self.assertEqual(cr_spec["co_primary_gpu_specialist"], "/polyglot-rust-wgpu-specialist")

        bt_spec = bt_daemon.get_bluetooth_serial_specialist_status()
        self.assertEqual(bt_spec["primary_posix_frame_specialist"], "/polyglot-c-cpp-specialist")
        self.assertIn("BLUETOOTH SERIAL POLYGLOT SPECIALISTS VERIFIED", bt_daemon.handle_specialists_terminal_cmd("status"))

        # 7. Verify C11 libbt_serial_parser.dylib boundary conditions (0-length, >1280 MTU overflow, valid Teleplot frame)
        import ctypes
        dylib_path = REPO_ROOT / "01_apps/bluetooth_terminal_ide/src/libbt_serial_parser.dylib"
        self.assertTrue(dylib_path.exists())

        class FrameStatus(ctypes.Structure):
            _fields_ = [
                ("frame_length", ctypes.c_uint32),
                ("crc16_ccitt", ctypes.c_uint16),
                ("valid", ctypes.c_uint8),
                ("is_teleplot_metric", ctypes.c_uint8),
            ]

        c_lib = ctypes.CDLL(str(dylib_path))
        c_lib.bt_serial_validate_frame.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        c_lib.bt_serial_validate_frame.restype = FrameStatus

        # Empty input -> invalid
        st_empty = c_lib.bt_serial_validate_frame(b"", 0)
        self.assertEqual(st_empty.valid, 0)

        # Oversized (> 1280 MTU) -> invalid
        oversized = b"X" * 1281
        st_over = c_lib.bt_serial_validate_frame(oversized, len(oversized))
        self.assertEqual(st_over.valid, 0)

        # Exact 1280 MTU boundary -> valid, non-teleplot
        exact_mtu = b"A" * 1280
        st_mtu = c_lib.bt_serial_validate_frame(exact_mtu, len(exact_mtu))
        self.assertEqual(st_mtu.valid, 1)
        self.assertEqual(st_mtu.frame_length, 1280)
        self.assertEqual(st_mtu.is_teleplot_metric, 0)

        # Valid Teleplot metric -> valid=1, is_teleplot_metric=1, non-zero CRC16
        tp_frame = b">movesense_hr:72"
        st_tp = c_lib.bt_serial_validate_frame(tp_frame, len(tp_frame))
        self.assertEqual(st_tp.valid, 1)
        self.assertEqual(st_tp.is_teleplot_metric, 1)
        self.assertGreater(st_tp.crc16_ccitt, 0)

        # 8. Verify position-aware tie-breaking and multi-IDE hub resolution in LensOmniscientRouter
        r_go_first = router.resolve_ide_and_runtime_specialist("intellij", "golang bubbletea before python and rust")
        self.assertEqual(r_go_first["primary_specialist"], "polyglot-go-bubbletea-specialist")
        self.assertEqual(
            r_go_first["matched_prompt_specialists"],
            ["polyglot-go-bubbletea-specialist", "polyglot-python-specialist", "polyglot-rust-wgpu-specialist"],
        )
        r_multi_ide = router.resolve_ide_and_runtime_specialist(
            "", "integrate langgo pycharm intellij chromium bluetooth serial"
        )
        self.assertEqual(r_multi_ide["resolved_target"], "intellij")

        # 9. Verify compiled opengo_bt_ide binary exists and returns Exit Code 0 for --specialist
        opengo_bin = REPO_ROOT / "01_apps/opengo_bt_ide/opengo_bt_ide"
        self.assertTrue(opengo_bin.exists())
        opengo_proc = subprocess.run([str(opengo_bin), "--specialist"], capture_output=True, text=True, timeout=5.0)
        self.assertEqual(opengo_proc.returncode, 0)
        self.assertEqual(json.loads(opengo_proc.stdout)["ide"], "GoLand (langgo) / IntelliJ IDEA")

    def test_lens_cli_end_to_end_subcommands(self):
        lens_script = REPO_ROOT / "06_scripts_and_tooling" / "lens_cli.py"
        for subcmd in (
            "podman-storage",
            "heal-s20",
            "movesense-gatt",
            "ide",
            "integrate-ides",
            "specialists",
            "review-project",
            "debate",
            "vla",
            "voice-coder",
            "junie-mesh",
            "automate-247",
            "audit-code",
            "elo",
            "self-optimize",
            "benchmark-70b-100b",
        ):
            proc = subprocess.run(
                [sys.executable, str(lens_script), subcmd, "--json"],
                capture_output=True, text=True, timeout=25.0,
            )
            self.assertEqual(proc.returncode, 0, f"lens {subcmd} failed: {proc.stderr}")
            payload = json.loads(proc.stdout)
            self.assertIsInstance(payload, dict)

    def test_live_movesense_bluetooth_pull_and_ipless_ai_sharding_stability(self):
        # 1. Verify live Movesense Bluetooth GATT pull via Pixel L6 bridge
        bridge = MovesenseGattBluetoothSerialBridge()
        res = bridge.pull_movesense_gatt_to_serial_terminal(stream_to_terminal=True)
        self.assertEqual(res["bridge"], "MovesenseGattBluetoothSerialBridge")
        self.assertEqual(res["serial_terminal_port"], 4005)
        self.assertTrue(res["ansi_stream_written"])
        guard = res["pixel_only_ble_connection_guard"]
        self.assertEqual(guard["policy"], "STRICT_PIXEL_L6_EXCLUSIVE_BLE_GATT_OWNER")
        self.assertEqual(guard["sole_authorized_ble_gatt_owner"]["tailscale_ip"], "100.114.215.68")
        self.assertEqual(guard["sole_authorized_ble_gatt_owner"]["bluetooth_mac"], "30:E0:44:6D:18:EC")
        self.assertIn("movesense_whiteboard_gatt_service_uuid", guard["gatt_services"])
        self.assertIn("movesense_gatt_payload", res)

        # 2. Verify 3-tier IP-less AI Sharding & WAN-Blackout Stability
        ai_dir = str(REPO_ROOT / "02_ai_models_and_inference")
        if ai_dir not in sys.path:
            sys.path.insert(0, ai_dir)
        from ipless_rfcomm_ai_shard_bridge import IPLessAIShardOrchestrator

        orch = IPLessAIShardOrchestrator()
        status = orch.probe_all_ipless_transports(simulate_wan_blackout=True)
        self.assertEqual(status["mode"], "INTERNET_DROPPED_ISOLATED_SHARDING")
        self.assertTrue(status["sharding_stability_guaranteed"])
        self.assertGreaterEqual(len(status["surviving_ipless_tiers"]), 2)

        bench = orch.run_blackout_stability_benchmark()
        self.assertEqual(bench["total_tiers_tested"], 3)
        self.assertEqual(bench["tiers_succeeded"], 3)
        self.assertTrue(bench["zero_drop_rate_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)




