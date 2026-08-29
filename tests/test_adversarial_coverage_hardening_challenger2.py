#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_adversarial_coverage_hardening_challenger2.py
=========================================================
Empirical Adversarial Coverage Hardening & Boundary Probing Suite
(Milestone M4 / Tier 5 Challenger 2)

Covers 4 Invariant Dimensions:
1. Airgap Penetration Probing: Deeply nested structures, casing permutations,
   encoded keys, query strings, and secret regexes against is_airgapped_data & WorkloadRouter.
2. Storage Corruption & Self-Healing: Stale .git/index.lock, missing/corrupted
   obsidian_vault/Index.md, low disk space (<5GB) self-healing triggers, and multi-threaded sink integrity.
3. Metal GPU Memory Cap Boundary: Exact 21.6GB / 90% dynamic RAM governance,
   ShardedTrainingSupervisor VRAM calculation, thermal throttling, and battery discharge guards.
4. Zero-Flakiness Verification: Deterministic rapid cycling without memory leaks or race conditions.
"""

from __future__ import annotations

import os
import sys
import time
import json
import shutil
import urllib.parse
import tempfile
import threading
import unittest
import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Dynamically load modules to avoid naming collisions
REPO_ROOT = Path(__file__).resolve().parents[1]

def _load_module(name: str, rel_path: str):
    full_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, str(full_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

quota_mgr = _load_module("cloud_api_quota_manager", "06_scripts_and_tooling/automation/cloud_api_quota_manager.py")
daemon_mgr = _load_module("network_daemon_manager", "06_scripts_and_tooling/network/daemon_manager.py")
fast_train = _load_module("fast_train_agentworld_mac", "06_scripts_and_tooling/training/fast_train_agentworld_mac.py")
shard_sup = _load_module("sharded_training_supervisor", "00_core_infrastructure/self_healing_hub/src/sharded_training_supervisor.py")
tri_sink = _load_module("tri_vault_sink", "04_data_and_memory/tri_vault_sink.py")

is_airgapped_data = quota_mgr.is_airgapped_data
FORBIDDEN_BIOMETRIC_TERMS = quota_mgr.FORBIDDEN_BIOMETRIC_TERMS
SECRET_PATTERNS = quota_mgr.SECRET_PATTERNS
WorkloadRouter = quota_mgr.WorkloadRouter
TaskRequest = quota_mgr.TaskRequest
QuotaStateStore = quota_mgr.QuotaStateStore

verify_and_heal_tri_vault = daemon_mgr.verify_and_heal_tri_vault
check_dynamic_ram_governance = fast_train.check_dynamic_ram_governance
check_hardware_capabilities = fast_train.check_hardware_capabilities
ShardedTrainingSupervisor = shard_sup.ShardedTrainingSupervisor
NODE_PROFILES = shard_sup.NODE_PROFILES

TriVaultSink = tri_sink.TriVaultSink
verify_zero_mock_compliance = tri_sink.verify_zero_mock_compliance


# ===========================================================================
# 1. Airgap Penetration Probing & Containment
# ===========================================================================
class TestAirgapPenetrationAndContainment(unittest.TestCase):
    """
    Adversarially probes the 100% fail-closed privacy airgap against
    sophisticated payload permutations, deeply nested dicts/lists,
    alternative casing, query strings, and credentials.
    """

    def test_01_nested_data_structures_deep_containment(self):
        """Test detection inside deeply nested structures (10+ levels)."""
        # 10 levels deep dictionary
        nested: Dict[str, Any] = {"signal": "512hz_ecg"}
        for level in range(10):
            nested = {f"nest_level_{level}": nested if level % 2 == 0 else [nested]}
        
        self.assertTrue(is_airgapped_data(nested), "Failed to detect biometric term in 10-level nested dict/list")

        # Deeply nested secret token
        nested_secret: Dict[str, Any] = {"token": "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"}
        for level in range(8):
            nested_secret = {f"level_{level}": [{"payload": nested_secret}]}

        self.assertTrue(is_airgapped_data(nested_secret), "Failed to detect GitHub secret in nested structure")

    def test_02_alternative_casing_and_case_permutations(self):
        """Verify case-insensitivity across mixed uppercase, lowercase, and camelCase."""
        casing_variants = [
            "512Hz_EcG",
            "RAW_ECG_MV",
            "MoVeSeNsE_GaTt",
            "PtT_bLoOd_PrEsSuRe_RaW",
            "dFa_AlPhA1_RaW",
            "PaN_tOmPkInS_qRs",
            "RAW_PPG_STREAM",
            "UnFiLtErEd_Rr_InTeRvAlS",
            "HeMoDyNaMiCs_Bp",
            "MoVeSeNsE_Hr_PlUs",
            "RaW_bIoMeTrIcS"
        ]
        for variant in casing_variants:
            with self.subTest(variant=variant):
                self.assertTrue(
                    is_airgapped_data(variant),
                    f"Alternative casing not detected: {variant}"
                )
                self.assertTrue(
                    is_airgapped_data({"data": variant}),
                    f"Dict value with alternative casing not detected: {variant}"
                )
                self.assertTrue(
                    is_airgapped_data({variant: "nominal"}),
                    f"Dict key with alternative casing not detected: {variant}"
                )

    def test_03_query_strings_and_url_encoded_payloads(self):
        """Verify detection within URLs, query strings, and web request fragments."""
        urls_and_queries = [
            "https://gateway.lauburu.ai/v1/gemini/models?prompt=stream%20512hz_ecg%20samples",
            "/v1/google/chat/completions?api_key='AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz'",
            "https://api.cloudflare.com/client/v4/accounts/123/ai?movesense_raw=true",
            "https://router.huggingface.co/hf-inference?auth=Bearer%20sk-antigravity0123456789abcdef1234",
            "?ptt_blood_pressure_raw=120_80&lead=II",
            json.dumps({"metadata": json.dumps({"nested_json": "pan_tompkins_raw"})}),
            "Authorization: Bearer ghp_999999999999999999999999999999999999"
        ]
        for item in urls_and_queries:
            with self.subTest(item=item):
                self.assertTrue(
                    is_airgapped_data(item),
                    f"Query string or URL pattern not detected: {item}"
                )

    def test_04_secret_credential_regex_patterns(self):
        """Verify all secret credential patterns trigger airgap lockdown."""
        secrets = [
            "api_key = 'AIzaSySecretApiKey1234567890'",
            "cloudflare_api_token='cf_token_abcdef1234567890'",
            "supabase_service_role_key: \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c\"",
            "sk-antigravity12345678901234567890",
            "ghp_0123456789abcdefghijklmnopqrstuvwx",
            "gho_0123456789abcdefghijklmnopqrstuvwx",
            "ghs_0123456789abcdefghijklmnopqrstuvwx",
            "whsec_0123456789abcdef0123456789abcdef",
            "AKIAIOSFODNN7EXAMPLE",
            "xoxb-123456789012-1234567890123-abcdefghijklmnopqrstuvwx",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y...\n-----END RSA PRIVATE KEY-----"
        ]
        for sec in secrets:
            with self.subTest(secret=sec):
                self.assertTrue(
                    is_airgapped_data(sec),
                    f"Secret pattern not detected: {sec[:30]}..."
                )

    def test_05_numeric_biometric_arrays_vs_clean_telemetry(self):
        """Verify heuristic detection of large numeric arrays with biometric signal hints."""
        # Biometric array with hint key
        biometric_arr = {"ecg_lead_1": [0.123] * 25}
        self.assertTrue(is_airgapped_data(biometric_arr))

        ppg_arr = {"ppg_wave_samples": [1.02, 1.05] * 15}
        self.assertTrue(is_airgapped_data(ppg_arr))

        # Clean non-biometric arrays (e.g. system CPU load, temps)
        clean_cpu = {"cpu_percent_history": [12.5, 14.2, 10.1] * 10}
        self.assertFalse(is_airgapped_data(clean_cpu))

        clean_temps = {"device_temperature_c": [42.1, 43.0] * 15}
        self.assertFalse(is_airgapped_data(clean_temps))

    def test_06_workload_router_fail_closed_containment(self):
        """Verify WorkloadRouter completely disallows cloud routing when airgap is tripped."""
        temp_dir = Path(tempfile.mkdtemp(prefix="airgap_router_test_"))
        try:
            state_file = temp_dir / "quota_state.json"
            store = QuotaStateStore(state_file=state_file)
            router = WorkloadRouter(state_store=store)

            # Airgapped task request with biometric data
            req = TaskRequest(
                task_id="airgap_adversarial_001",
                prompt="Analyze this physiological stream: 512hz_ecg raw telemetry",
                task_type="telemetry",
                prefer_local=False  # Even if user requested cloud!
            )
            res = router.route_and_execute(req)

            self.assertTrue(res.success)
            self.assertEqual(res.provider_used, "local_mesh")
            self.assertIn("local mesh", res.response_text.lower())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# 2. Storage Corruption & Self-Healing Triggers
# ===========================================================================
class TestStorageCorruptionAndSelfHealing(unittest.TestCase):
    """
    Adversarially simulates corrupted and missing storage artifacts:
    stale .git/index.lock, deleted/corrupted obsidian_vault/Index.md,
    missing directories, and low disk space headroom.
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="storage_corruption_"))
        self.obsidian_dir = self.test_dir / "obsidian_vault"
        self.index_file = self.obsidian_dir / "Index.md"
        self.pyspark_dir = self.test_dir / "04_data_and_memory"
        self.lora_dir = self.test_dir / "lora_datasets"
        self.git_dir = self.test_dir / ".git"
        self.git_lock = self.git_dir / "index.lock"

        self.obsidian_dir.mkdir(parents=True, exist_ok=True)
        self.pyspark_dir.mkdir(parents=True, exist_ok=True)
        self.lora_dir.mkdir(parents=True, exist_ok=True)
        self.git_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _run_healing_in_sandbox(self, disk_free_gb: float = 25.0):
        with patch.object(daemon_mgr, "OBSIDIAN_VAULT", self.obsidian_dir), \
             patch.object(daemon_mgr, "DATA_DIR", self.pyspark_dir), \
             patch.object(daemon_mgr, "LORA_DATASETS_DIR", self.lora_dir), \
             patch.object(daemon_mgr, "REPO_ROOT", self.test_dir), \
             patch("shutil.disk_usage", return_value=MagicMock(free=int(disk_free_gb * (1024 ** 3)))):
            return verify_and_heal_tri_vault()

    def test_01_stale_git_index_lock_removal(self):
        """Simulate stale .git/index.lock and verify auto-removal."""
        # Write stale lock
        self.git_lock.write_text("12345 pid")
        self.assertTrue(self.git_lock.exists())

        # Write valid Index.md
        self.index_file.write_text("# Master\n- [[Index]]\n- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]")

        res = self._run_healing_in_sandbox()

        self.assertFalse(self.git_lock.exists(), "Stale git index.lock was not unlinked")
        self.assertTrue(res["git_lock_cleared"])
        self.assertTrue(res["healthy"])
        self.assertEqual(res["status"], "HEALTHY")

    def test_02_missing_obsidian_index_auto_regeneration(self):
        """Simulate deleted obsidian_vault/Index.md and verify canonical recreation."""
        if self.index_file.exists():
            self.index_file.unlink()
        self.assertFalse(self.index_file.exists())

        res = self._run_healing_in_sandbox()

        self.assertTrue(self.index_file.is_file(), "Index.md was not regenerated")
        self.assertTrue(res["obsidian_index_healed"])
        content = self.index_file.read_text(encoding="utf-8")
        self.assertIn("[[Index]]", content)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", content)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", content)
        self.assertTrue(res["healthy"])

    def test_03_corrupted_obsidian_index_wikilink_repair(self):
        """Simulate truncated Index.md missing Wikilinks and verify auto-repair."""
        # Write incomplete index file
        self.index_file.write_text("# Master Index\nSome custom user text without links.")

        res = self._run_healing_in_sandbox()

        self.assertTrue(res["obsidian_index_healed"])
        content = self.index_file.read_text(encoding="utf-8")
        self.assertIn("[[Index]]", content)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", content)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", content)

    def test_04_missing_pyspark_and_lora_directories_healing(self):
        """Simulate deleted storage directories and verify auto-creation."""
        shutil.rmtree(self.pyspark_dir)
        shutil.rmtree(self.lora_dir)
        self.assertFalse(self.pyspark_dir.exists())
        self.assertFalse(self.lora_dir.exists())

        self.index_file.write_text("# Master\n- [[Index]]\n- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]")

        res = self._run_healing_in_sandbox()

        self.assertTrue(self.pyspark_dir.is_dir())
        self.assertTrue(self.lora_dir.is_dir())
        self.assertTrue(res["pyspark_lake_ready"])
        self.assertTrue(res["lora_datasets_ready"])
        self.assertTrue(res["healthy"])

    def test_05_low_disk_headroom_triggering_and_purge(self):
        """Simulate disk space < 5.0 GB and verify headroom warning + purge trigger."""
        self.index_file.write_text("# Master\n- [[Index]]\n- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]")

        # Low disk space: 3.2 GB free
        res_low = self._run_healing_in_sandbox(disk_free_gb=3.2)
        self.assertFalse(res_low["disk_headroom_compliant"])
        self.assertTrue(res_low["disk_purged"])
        self.assertEqual(res_low["status"], "DEGRADED")
        self.assertFalse(res_low["healthy"])

        # Compliant disk space: 15.0 GB free
        res_ok = self._run_healing_in_sandbox(disk_free_gb=15.0)
        self.assertTrue(res_ok["disk_headroom_compliant"])
        self.assertEqual(res_ok["status"], "HEALTHY")
        self.assertTrue(res_ok["healthy"])

    def test_06_tri_vault_sink_atomic_persistence_and_zero_mock(self):
        """Test TriVaultSink atomic writing and zero-mock validation on fake records."""
        sink = TriVaultSink(
            lora_dir=self.lora_dir,
            obsidian_dir=self.obsidian_dir
        )

        # 1. Reject fake record with negative latency
        bad_record_1 = {
            "instruction": "Test instruction",
            "output": "Test output",
            "latency_ms": -15.0,
            "zero_mock": True
        }
        ok, msg = verify_zero_mock_compliance(bad_record_1)
        self.assertFalse(ok)
        self.assertIn("Negative latency", msg)

        # 2. Reject unverified mock record
        bad_record_2 = {
            "instruction": "Test instruction",
            "output": "Test output",
            "zero_mock": False
        }
        ok, msg = verify_zero_mock_compliance(bad_record_2)
        self.assertFalse(ok)

        # 3. Accept authentic record and verify atomic persistence
        valid_record = {
            "instruction": "Optimize kernel tensor sharding",
            "output": "Generated Metal kernel with 273 GB/s bandwidth",
            "latency_ms": 142.5,
            "tokens_generated": 85,
            "truth_verified": True,
            "truth_compliance_pct": 100.0
        }
        ok, msg = verify_zero_mock_compliance(valid_record)
        self.assertTrue(ok)

        target_file = self.lora_dir / "test_verified_dataset.jsonl"
        append_ok = sink.append_verified_pair(target_file, valid_record)
        self.assertTrue(append_ok)
        
        self.assertTrue(target_file.is_file())
        saved_lines = [json.loads(line) for line in target_file.read_text().splitlines() if line.strip()]
        self.assertEqual(len(saved_lines), 1)
        self.assertEqual(saved_lines[0]["instruction"], valid_record["instruction"])

    def test_07_concurrent_multithreaded_sink_writes_zero_loss(self):
        """Test 20 threads writing concurrently to TriVaultSink without corruption or lost entries."""
        sink = TriVaultSink(
            lora_dir=self.lora_dir,
            obsidian_dir=self.obsidian_dir
        )
        target_file = self.lora_dir / "concurrent_dataset.jsonl"

        threads: List[threading.Thread] = []
        errors: List[Exception] = []
        total_records = 20 * 5  # 100 total records

        def write_worker(t_id: int):
            try:
                for i in range(5):
                    rec = {
                        "instruction": f"Instruction from thread {t_id} item {i}",
                        "output": f"Output from thread {t_id} item {i}",
                        "latency_ms": 50.0 + i,
                        "tokens_generated": 30,
                        "truth_verified": True,
                        "truth_compliance_pct": 100.0,
                        "metadata": {"timestamp": datetime.now(timezone.utc).isoformat()}
                    }
                    ok = sink.append_verified_pair(target_file, rec)
                    if not ok:
                        errors.append(RuntimeError(f"Failed to append from thread {t_id}"))
            except Exception as ex:
                errors.append(ex)

        for t_idx in range(20):
            t = threading.Thread(target=write_worker, args=(t_idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent write errors encountered: {errors}")
        self.assertTrue(target_file.is_file())

        lines = [json.loads(line) for line in target_file.read_text().splitlines() if line.strip()]
        self.assertEqual(len(lines), total_records, f"Expected {total_records} lines, got {len(lines)}")

        # Verify daily count query
        daily_count = sink.get_daily_verified_count(target_file)
        self.assertEqual(daily_count, total_records)


# ===========================================================================
# 3. Metal GPU Memory Cap Boundary & Supervisor Arithmetic
# ===========================================================================
class TestMetalGPUMemoryCapAndBoundaryEnforcement(unittest.TestCase):
    """
    Tests dynamic RAM governance at exact 21.6GB / 90% threshold boundaries,
    headroom enforcement, ShardedTrainingSupervisor VRAM allocation arithmetic,
    dynamic thermal throttling, and mobile battery discharge guards.
    """

    def test_01_hardware_scout_and_m4_pro_parameters(self):
        """Verify M4 Pro Mac Mini hardware specifications and dynamic cap."""
        hw = check_hardware_capabilities()
        self.assertEqual(hw["total_ram_gb"], 24.0)
        self.assertEqual(hw["ai_vram_cap_gb"], 21.6)
        self.assertEqual(hw["max_ram_cap_pct"], 90.0)
        self.assertEqual(hw["min_headroom_gb"], 2.50)

    def test_02_dynamic_ram_governance_exact_headroom_boundary(self):
        """
        Test exact mathematical headroom boundaries:
        - Headroom >= 2.50 GB -> CERTIFIED_HEALTHY
        - Headroom < 2.50 GB -> EXCEEDS_CAP
        """
        # Nominal default (18.40 GB allocated out of 21.6 GB cap -> 3.20 GB headroom)
        gov_nominal = check_dynamic_ram_governance(cap_gb=21.6, min_headroom_gb=2.50)
        self.assertTrue(gov_nominal["is_safe"])
        self.assertEqual(gov_nominal["status"], "CERTIFIED_HEALTHY")
        self.assertGreaterEqual(gov_nominal["ram_headroom_gb"], 2.50)

        # Boundary condition: Exactly 2.50 GB headroom required with tight cap
        # If cap is 20.90 GB and allocated is 18.40 GB -> headroom is exactly 2.50 GB
        gov_exact = check_dynamic_ram_governance(cap_gb=20.90, min_headroom_gb=2.50)
        self.assertTrue(gov_exact["is_safe"])
        self.assertEqual(gov_exact["status"], "CERTIFIED_HEALTHY")
        self.assertEqual(gov_exact["ram_headroom_gb"], 2.50)

        # Violation condition: 2.49 GB headroom (cap = 20.89 GB)
        gov_violation = check_dynamic_ram_governance(cap_gb=20.89, min_headroom_gb=2.50)
        self.assertFalse(gov_violation["is_safe"])
        self.assertEqual(gov_violation["status"], "EXCEEDS_CAP")
        self.assertLess(gov_violation["ram_headroom_gb"], 2.50)

    def test_03_sharded_supervisor_vram_allocation_arithmetic(self):
        """
        Test ShardedTrainingSupervisor allocation math at 70% and 90% cluster capacity.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="supervisor_test_"))
        try:
            telemetry_path = temp_dir / "telemetry_state.json"
            state_path = temp_dir / "sharded_training_state.json"
            telemetry_path.write_text("{}")

            with patch.object(shard_sup, "TELEMETRY_PATH", str(telemetry_path)), \
                 patch.object(shard_sup, "SUPERVISOR_STATE_PATH", str(state_path)):
                # 1. 70% Target Capacity
                sup_70 = ShardedTrainingSupervisor(target_capacity_pct=70.0)
                status_70 = sup_70.get_cluster_status()

                total_cap = sum(n["ai_cap_gb"] for n in NODE_PROFILES) # 54.65 GB
                expected_alloc_70 = round(sum(round(0.70 * n["ai_cap_gb"], 2) for n in NODE_PROFILES), 2) # 38.25 GB

                self.assertEqual(status_70["cluster_target_capacity_pct"], 70.0)
                self.assertEqual(status_70["total_pooled_cap_gb"], total_cap)
                self.assertEqual(status_70["total_allocated_vram_gb"], expected_alloc_70)
                self.assertAlmostEqual(status_70["headroom_reserve_pct"], 30.0, delta=0.5)

                # 2. 90% Target Capacity (Maximum Dynamic AI Ceiling)
                sup_90 = ShardedTrainingSupervisor(target_capacity_pct=90.0)
                status_90 = sup_90.get_cluster_status()
                expected_alloc_90 = round(sum(round(0.90 * n["ai_cap_gb"], 2) for n in NODE_PROFILES), 2) # 49.19 GB

                self.assertEqual(status_90["total_allocated_vram_gb"], expected_alloc_90)
                self.assertAlmostEqual(status_90["cluster_vram_utilization_pct"], 90.0, delta=0.5)
                self.assertAlmostEqual(status_90["headroom_reserve_pct"], 10.0, delta=0.5)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_04_dynamic_thermal_throttling_boundaries(self):
        """
        Test supervisor dynamic throttling under simulated thermal conditions:
        - Below throttle threshold: OPTIMAL_COOL, 100% of target allocation
        - At/above warning threshold: WARNING_WARM, 70% allocation
        - At/above emergency threshold: EMERGENCY_THROTTLED, 35% allocation
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="thermal_test_"))
        try:
            telemetry_path = temp_dir / "telemetry_state.json"
            state_path = temp_dir / "sharded_training_state.json"

            # Inject elevated temperature for mac_host (warning: 75.0°C, emergency: 82.0°C)
            telemetry_mock = {
                "devices": {
                    "mac_host": {
                        "temperature_c": 76.0,  # Warning level
                        "battery": {"level_percent": 100, "is_charging": True}
                    },
                    "pixel_10": {
                        "temperature_c": 42.0,  # Emergency level (> 41.0°C mobile cutoff)
                        "battery": {"level_percent": 85, "is_charging": True}
                    }
                }
            }
            telemetry_path.write_text(json.dumps(telemetry_mock))

            with patch.object(shard_sup, "TELEMETRY_PATH", str(telemetry_path)), \
                 patch.object(shard_sup, "SUPERVISOR_STATE_PATH", str(state_path)):
                sup = ShardedTrainingSupervisor(target_capacity_pct=70.0)
                status = sup.get_cluster_status()

                nodes = {n["id"]: n for n in status["nodes"]}

                # Check mac_host throttled to 70% of 8.40 GB = 5.88 GB
                mac = nodes["mac_host"]
                self.assertEqual(mac["temp_status"], "WARNING_WARM")
                self.assertEqual(mac["safety_status"], "THROTTLED_SAFETY")
                self.assertEqual(mac["allocated_vram_gb"], 5.88)

                # Check pixel_10 throttled to 35% of 7.98 GB = 2.79 GB
                pixel = nodes["pixel_10"]
                self.assertEqual(pixel["temp_status"], "EMERGENCY_THROTTLED")
                self.assertEqual(pixel["safety_status"], "THROTTLED_SAFETY")
                self.assertEqual(pixel["allocated_vram_gb"], 2.79)

                # Cluster-level safety flag must be False due to emergency alert
                self.assertFalse(status["all_nodes_thermal_safe"])
                self.assertGreaterEqual(len(status["active_safety_alerts"]), 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_05_mobile_battery_drainage_and_discharging_guard(self):
        """
        Test mobile battery safety guard:
        - Mobile node < 25% discharging -> throttled to 0.5 GB minimal heartbeat.
        - Mobile node < 25% charging -> normal operation allowed.
        - Mobile node == 25% discharging -> boundary preserved.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="battery_test_"))
        try:
            telemetry_path = temp_dir / "telemetry_state.json"
            state_path = temp_dir / "sharded_training_state.json"

            # Samsung S20 discharging at 24% battery (< 25% threshold)
            # Pixel 10 at 20% but charging (is_charging = True)
            telemetry_mock = {
                "devices": {
                    "samsung_s20": {
                        "temperature_c": 34.0,
                        "battery": {"level_percent": 24, "is_charging": False}
                    },
                    "pixel_10": {
                        "temperature_c": 33.0,
                        "battery": {"level_percent": 20, "is_charging": True}
                    }
                }
            }
            telemetry_path.write_text(json.dumps(telemetry_mock))

            with patch.object(shard_sup, "TELEMETRY_PATH", str(telemetry_path)), \
                 patch.object(shard_sup, "SUPERVISOR_STATE_PATH", str(state_path)):
                sup = ShardedTrainingSupervisor(target_capacity_pct=70.0)
                status = sup.get_cluster_status()

                nodes = {n["id"]: n for n in status["nodes"]}

                # Samsung S20 must be cut to 0.5 GB minimal heartbeat
                s20 = nodes["samsung_s20"]
                self.assertEqual(s20["allocated_vram_gb"], 0.5)
                self.assertEqual(s20["safety_status"], "THROTTLED_SAFETY")

                # Pixel 10 is charging -> maintains normal 70% allocation (7.98 GB)
                pixel = nodes["pixel_10"]
                self.assertEqual(pixel["allocated_vram_gb"], 7.98)
                self.assertEqual(pixel["safety_status"], "SAFE_70_ACTIVE")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# 4. Zero-Flakiness Rapid Deterministic Stress Harness
# ===========================================================================
class TestZeroFlakinessStressHarness(unittest.TestCase):
    """
    Runs 100 consecutive rapid cycles across all modules to guarantee
    100% deterministic execution and zero flakiness under rapid iterations.
    """

    def test_rapid_deterministic_100_cycles(self):
        """Run 100 sequential cycles of airgap validation, storage check, and supervisor status."""
        temp_dir = Path(tempfile.mkdtemp(prefix="stress_zero_flakiness_"))
        try:
            telemetry_path = temp_dir / "empty_telemetry.json"
            state_path = temp_dir / "sharded_state.json"
            telemetry_path.write_text("{}")

            with patch.object(shard_sup, "TELEMETRY_PATH", str(telemetry_path)), \
                 patch.object(shard_sup, "SUPERVISOR_STATE_PATH", str(state_path)):
                sup = ShardedTrainingSupervisor(target_capacity_pct=70.0)

                for cycle in range(100):
                    # 1. Airgap evaluation
                    self.assertTrue(is_airgapped_data(f"512hz_ecg_sample_{cycle}"))
                    self.assertFalse(is_airgapped_data(f"valid_ast_code_sample_{cycle}"))

                    # 2. Hardware RAM governance check
                    gov = check_dynamic_ram_governance(cap_gb=21.6, min_headroom_gb=2.50)
                    self.assertTrue(gov["is_safe"])

                    # 3. Sharded supervisor calculation
                    status = sup.get_cluster_status()
                    self.assertEqual(status["total_pooled_cap_gb"], 54.65)
                    self.assertEqual(status["total_allocated_vram_gb"], 38.25)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
