#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
tests/test_continuous_specialist_role_trainer.py
================================================================================
Comprehensive Test Suite for Continuous Specialist Local AI Training
--------------------------------------------------------------------------------
Lauburu Mesh Ecosystem — 2026
================================================================================
"""

import json
import os
import sys
from pathlib import Path
import pytest

# Dynamic Monorepo Root Resolution
p = Path(__file__).resolve()
while p.parent != p:
    if (p / "PROJECT.md").exists() or (p / "obsidian_vault").exists():
        REPO_ROOT = p
        break
    p = p.parent
else:
    REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

PROTOCOLS_DIR = REPO_ROOT / "05_agents_and_swarms" / "training_protocols"
if str(PROTOCOLS_DIR) not in sys.path:
    sys.path.insert(0, str(PROTOCOLS_DIR))

from continuous_specialist_role_trainer import (
    CANONICAL_SPECIALIST_ROLES,
    ContinuousSpecialistRoleTrainer,
    SpecialistRoleSpec,
    SpecialistTrainingReceipt,
    check_host_ram_safe
)


class TestSpecialistRoleCatalog:
    """Tests the completeness and specification of all 24 specialist AI roles."""

    def test_canonical_24_roles_complete(self):
        assert len(CANONICAL_SPECIALIST_ROLES) == 24, (
            f"Expected exactly 24 specialist roles, found {len(CANONICAL_SPECIALIST_ROLES)}"
        )
        role_ids = [r.role_id for r in CANONICAL_SPECIALIST_ROLES]
        assert len(set(role_ids)) == 24, "Duplicate role IDs detected!"

    def test_all_7_projects_covered(self):
        project_ids = {r.project_id for r in CANONICAL_SPECIALIST_ROLES}
        expected_projects = {
            "00_core_infrastructure",
            "01_apps",
            "02_ai_models_and_inference",
            "03_biometrics_and_telemetry",
            "04_data_and_memory",
            "05_agents_and_swarms",
            "06_scripts_and_tooling"
        }
        for ep in expected_projects:
            assert ep in project_ids, f"Project {ep} missing from specialist role catalog!"

    def test_specs_contain_valid_parameters(self):
        for r in CANONICAL_SPECIALIST_ROLES:
            assert len(r.role_id) > 3
            assert len(r.target_model_name) > 3
            assert len(r.target_quant) > 1
            assert len(r.target_layer) > 1
            assert len(r.contract_verification_command) > 5
            assert r.target_loss < r.initial_loss
            assert r.target_accuracy > r.baseline_accuracy


class TestDomainTrainingPairGeneration:
    """Tests authentic SFT/DPO pair generation with Rule #0 zero-mock enforcement."""

    def test_generate_pair_for_sample_roles(self):
        trainer = ContinuousSpecialistRoleTrainer()
        sample_roles = [
            CANONICAL_SPECIALIST_ROLES[0],  # posix_gateway_healer
            CANONICAL_SPECIALIST_ROLES[3],  # screen_lens_vla_auditor
            CANONICAL_SPECIALIST_ROLES[4],  # movesense_clinical_dsp
            CANONICAL_SPECIALIST_ROLES[9],  # sovereign_master_orchestrator
        ]

        for spec in sample_roles:
            record = trainer.synthesize_domain_training_pair(spec, step_idx=1)
            assert record["role_id"] == spec.role_id
            assert "1. Specialist Role Domain Analysis" in record["teacher_cot"]
            assert len(record["chosen"]) > 20
            assert "MOCK_DETECTED" in record["rejected"]

            # Verify dataset file exists
            role_file = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/specialists") / f"{spec.role_id}.jsonl"
            assert role_file.exists()
            assert role_file.stat().st_size > 0


class TestSpecialistTrainingStepExecution:
    """Tests execution of Apple Silicon Metal training steps and receipt logging."""

    def test_single_role_training_step(self):
        trainer = ContinuousSpecialistRoleTrainer()
        spec = CANONICAL_SPECIALIST_ROLES[0]  # posix_gateway_healer
        receipt = trainer.execute_specialist_training_step(spec, epoch=1)

        assert isinstance(receipt, SpecialistTrainingReceipt)
        assert receipt.role_id == spec.role_id
        assert receipt.final_loss < receipt.initial_loss
        assert receipt.loss_reduction_pct > 0.0
        assert receipt.post_tuning_accuracy > receipt.pre_tuning_accuracy
        assert receipt.verification_exit_code == 0
        assert receipt.retention_verdict == "RETAINED_NICHE_LEADER"
        assert len(receipt.verification_hash) > 0

        # Verify receipt written to canonical file
        receipts_file = REPO_ROOT / "04_data_and_memory" / "lora_datasets" / "niche_fine_tuning_receipts.jsonl"
        assert receipts_file.exists()
        assert receipts_file.stat().st_size > 0


class TestFull24RoleTrainingPass:
    """Tests full sweep across all 24 project and app specific local AI roles."""

    def test_full_24_role_training_sweep(self):
        trainer = ContinuousSpecialistRoleTrainer()
        receipts = trainer.train_all_24_specialist_roles(epoch=1)

        assert len(receipts) == 24
        for r in receipts:
            assert r.verification_exit_code == 0, f"Role {r.role_id} failed verification!"
            assert r.loss_reduction_pct > 0.0
            assert r.accuracy_boost_pct > 0.0

        # Verify Markdown mastery report
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "SPECIALIST_AI_TRAINING_AND_MASTERY_REPORT.md"
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "24 / 24" in content
        assert "100% PASSED" in content
        for spec in CANONICAL_SPECIALIST_ROLES:
            assert spec.role_id in content


class TestTriVaultDocumentationIntegrity:
    """Verifies that the catalog and report exist and are cross-linked."""

    def test_roles_catalog_and_mastery_report_exist(self):
        catalog = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "PROJECT_AND_APP_SPECIFIC_LOCAL_AI_ROLES_CATALOG.md"
        mastery = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "SPECIALIST_AI_TRAINING_AND_MASTERY_REPORT.md"
        assert catalog.exists()
        assert mastery.exists()

        cat_text = catalog.read_text(encoding="utf-8")
        assert "24 dedicated, specialized Local AI roles" in cat_text
        assert "[[SPECIALIST_AI_TRAINING_AND_MASTERY_REPORT]]" in cat_text


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
