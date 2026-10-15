#!/usr/bin/env python3
"""
tests/test_omni_agent_samsung_s20_e2e.py
========================================
E2E Automated Feature & Functionality Test Suite for Omni Agent Lauburu on Samsung Galaxy S20+ 5G (L7).
Strictly governed by:
- Rule 0 (Zero-Mock): Authentic Movesense MD binary records, live Bluetooth hardware queries.
- Rule 1 (Tri-Proof): Physical actuation exit codes, cryptographic SHA256 checksums, visual screen captures.
- Rule 5 & Rule 6: Mandatory Free-Tier Cloud Review on claimed proof.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
APK_PATH = REPO_ROOT / "01_apps/Omni_Agent_Lauburu.apk"
MECG_ZIP = REPO_ROOT / "01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg.zip"
DSP_SCRIPT = REPO_ROOT / "03_biometrics_and_telemetry/pan_tompkins_qrs_dsp.py"
AUDITOR_SCRIPT = REPO_ROOT / "06_scripts_and_tooling/cloud/free_tier_proof_auditor.py"
OBSIDIAN_AUDIT_LOG = REPO_ROOT / "obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_CLOUD_AUDIT_REVIEWS.md"
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestOmniAgentSamsungS20E2E:

    def test_01_bluetooth_l7_mesh_pairing(self):
        """Validates physical Layer-0 Bluetooth connectivity to Samsung S20+ (5c-cb-99-05-81-41)."""
        res = subprocess.run(["blueutil", "--connected"], capture_output=True, text=True, timeout=5)
        assert res.returncode == 0, "blueutil failed to execute"
        assert "5c-cb-99-05-81-41" in res.stdout.lower(), f"Samsung S20+ not connected over Bluetooth:\n{res.stdout}"
        assert "Aaron's S20+" in res.stdout or "s20" in res.stdout.lower()

    def test_02_omni_agent_apk_cryptographic_integrity(self):
        """Validates Omni Agent Lauburu APK binary integrity and metadata."""
        assert APK_PATH.exists(), f"Missing APK at {APK_PATH}"
        size = APK_PATH.stat().st_size
        assert size == 50392410, f"Unexpected APK size: {size}"
        sha = compute_sha256(APK_PATH)
        assert sha == "86309d022f3a3f799c0f2701d4cc48c5f3cd077d5174400ef0f345d1a560ada9", f"APK SHA256 mismatch: {sha}"

    def test_03_zero_mock_pan_tompkins_512hz_dsp(self):
        """Executes authentic Pan-Tompkins QRS DSP pipeline across Movesense MD raw samples."""
        assert MECG_ZIP.exists(), f"Missing Movesense MECG archive at {MECG_ZIP}"
        mecg_sha = compute_sha256(MECG_ZIP)
        assert mecg_sha == "71ba53e0d1e8175c696f58495b5bb693a882cab10addf12bddeeaa94d9c86927"

        res = subprocess.run([sys.executable, str(DSP_SCRIPT)], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"DSP script failed: {res.stderr}"
        assert "AUTHENTIC ZERO-MOCK DSP SUITE PASSED" in res.stdout
        assert "R-Peaks Detected:" in res.stdout
        assert "Movesense MD (Serial: 242230000604)" in res.stdout

    def test_04_screen_lens_visual_proof_artifacts(self):
        """Validates Screen Lens screenshots captured during live S20 human click-through."""
        artifacts_dir = Path("/Users/aaron/.gemini/antigravity/brain/d161e75c-1d12-4715-8ca2-2eb3cab65eed")
        expected_artifacts = [
            "screen_lens_samsung_s20_omni_agent.png",
            "screen_lens_s20_e2e_step1_terminal.png",
            "screen_lens_s20_e2e_step2_connected.png",
            "screen_lens_s20_e2e_step3_identify.png"
        ]
        for name in expected_artifacts:
            path = artifacts_dir / name
            assert path.exists(), f"Missing visual proof artifact: {name}"
            assert path.stat().st_size > 50000, f"Artifact {name} appears empty or corrupted"

    def test_05_mandatory_cloud_free_tier_audit(self):
        """Verifies that free-tier cloud auditing records are populated in Obsidian Vault & LoRA lake."""
        assert AUDITOR_SCRIPT.exists(), f"Missing free_tier_proof_auditor at {AUDITOR_SCRIPT}"
        assert OBSIDIAN_AUDIT_LOG.exists(), f"Missing Obsidian audit log at {OBSIDIAN_AUDIT_LOG}"
        content = OBSIDIAN_AUDIT_LOG.read_text(encoding="utf-8")
        assert "Cloud Audit Review" in content
        assert "groq_qwen_3.8_27b" in content or "gemini" in content

        assert LORA_DATASET.exists(), f"Missing LoRA dataset at {LORA_DATASET}"
        lora_lines = LORA_DATASET.read_text(encoding="utf-8").strip().splitlines()
        assert len(lora_lines) > 0, "LoRA dataset is empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
