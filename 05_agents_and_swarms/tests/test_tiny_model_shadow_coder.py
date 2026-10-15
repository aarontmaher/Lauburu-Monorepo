#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Test Suite: Tiny Model Shadow Coder & Generational Handoff Engine
======================================================================================
Test Target: 05_agents_and_swarms/tiny_model_shadow_coder_and_handoff_engine.py
Subsystem: 05_agents_and_swarms / 04_data_and_memory
Covers:
- Tiny Model Multi-Stage Shadow Code Inspection & AST Validation
- Syntax Error & Indentation Error Interception (Zero Mistake Propagation)
- Rule #0 Zero-Mock Enforcement (Intercepts mock tokens and simulated arrays)
- Empty Function Stub Detection
- Teacher Auto-Correction & High-Signal DPO Pair Harvesting
- Multi-Provider Cloud Opinions Synthesis in Generational Handoffs
- Generational Consensus Scoring (>0.98 Threshold)
- Zero-Dollar Spend Invariant ($0.00 Cost Guarantee)
Rule #0 Compliance: 100% genuine execution, zero mock facades.
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
import pytest

# Ensure module paths are accessible
REPO_ROOT = Path(__file__).resolve().parents[2]
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
DATA_DIR = REPO_ROOT / "04_data_and_memory"

for p in [str(REPO_ROOT), str(SWARMS_DIR), str(DATA_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from tiny_model_shadow_coder_and_handoff_engine import (
    TinyModelShadowCoder,
    GenerationalHandoffSynthesizer,
    CERTIFIED_TINY_MODELS
)


@pytest.fixture
def temp_shadow_workspace():
    """Provides an isolated workspace for shadow coder and handoff engine tests."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_shadow_coder_test_")
    ws = Path(temp_dir)
    data_dir = ws / "04_data_and_memory"
    lora_dir = ws / "lora_datasets"
    obsidian_dir = ws / "obsidian_vault" / "05_SWARMS" / "handoffs"

    data_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    ledger_file = data_dir / "test_shadow_ledger.json"
    coder = TinyModelShadowCoder(ledger_path=ledger_file)
    synthesizer = GenerationalHandoffSynthesizer(shadow_coder=coder)

    yield {
        "workspace": ws,
        "data_dir": data_dir,
        "lora_dir": lora_dir,
        "obsidian_dir": obsidian_dir,
        "ledger_file": ledger_file,
        "coder": coder,
        "synthesizer": synthesizer,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# 1. Tiny Model Shadow Coder & Error Interception Tests
# ============================================================================

class TestTinyModelShadowCoder:
    """Verifies that the shadow coder intercepts all mistakes from tiny models."""

    def test_clean_python_code_approved(self, temp_shadow_workspace):
        coder = temp_shadow_workspace["coder"]
        code = (
            "def calculate_total(items: list) -> float:\n"
            "    return sum(item['price'] for item in items)\n"
        )
        res = coder.inspect_code_draft("smol_135m", "Calculate total price", code, language="python")
        assert res["valid"] is True
        assert res["error_category"] is None
        assert res["zero_mock_passed"] is True
        assert res["teacher_corrected_code"] is None

    def test_syntax_error_intercepted_and_corrected(self, temp_shadow_workspace):
        coder = temp_shadow_workspace["coder"]
        # Code missing colon
        broken_code = "def add_numbers(a, b)\n    return a + b"
        res = coder.inspect_code_draft("smol_360m", "Add two numbers", broken_code, language="python")
        assert res["valid"] is False
        assert res["error_category"] == "SYNTAX_ERROR"
        assert res["teacher_corrected_code"] is not None
        assert res["dpo_distilled"] is True
        # Verify mistake was recorded in ledger
        assert coder.state["total_mistakes_intercepted"] >= 1
        assert coder.state["interceptions_by_category"]["SYNTAX_ERROR"] >= 1

    def test_rule_0_mock_token_intercepted(self, temp_shadow_workspace):
        coder = temp_shadow_workspace["coder"]
        mock_code = (
            "def get_ecg_telemetry():\n"
            "    mock_data = [1, 2, 3, 4, 5]\n"
            "    return mock_data\n"
        )
        res = coder.inspect_code_draft("qwen_0_5b", "Get ECG telemetry", mock_code, language="python")
        assert res["valid"] is False
        assert res["zero_mock_passed"] is False
        assert res["error_category"] == "RULE_0_MOCK_DETECTED"
        assert "mock_data" in res["error_detail"]
        assert res["teacher_corrected_code"] is not None

    def test_empty_stub_function_intercepted(self, temp_shadow_workspace):
        coder = temp_shadow_workspace["coder"]
        stub_code = "def handle_packet(pkt: bytes):\n    pass"
        res = coder.inspect_code_draft("llama_1b", "Handle incoming packet", stub_code, language="python")
        assert res["valid"] is False
        assert res["error_category"] == "EMPTY_STUB_FUNCTION"

    def test_bracket_mismatch_for_non_python(self, temp_shadow_workspace):
        coder = temp_shadow_workspace["coder"]
        broken_dart = "void main() { print('hello world');"  # missing closing brace
        res = coder.inspect_code_draft("smol_1_7b", "Main entry point", broken_dart, language="dart")
        assert res["valid"] is False
        assert res["error_category"] == "UNCLOSED_BRACKETS"


# ============================================================================
# 2. Generational Handoff & Cloud Opinions Ingestion Tests
# ============================================================================

class TestGenerationalHandoffSynthesizer:
    """Verifies synthesis of handoff manifests with multi-provider cloud opinions."""

    def test_synthesize_generation_handoff(self, temp_shadow_workspace):
        synthesizer = temp_shadow_workspace["synthesizer"]
        res = synthesizer.synthesize_generation_handoff(generation_number=5)

        assert res["generation"] == 5
        assert res["consensus_score"] >= 0.98
        assert res["critics_count"] == 4
        assert res["dpo_distilled"] is True

        handoff_path = Path(res["handoff_file"])
        assert handoff_path.exists()
        content = handoff_path.read_text(encoding="utf-8")

        # Verify all 4 cloud providers are represented
        assert "Google AI Studio" in content
        assert "NVIDIA NIM" in content
        assert "Cloudflare Workers AI" in content
        assert "xAI Developer API" in content
        assert "CONSENSUS ACHIEVED" in content

    def test_cloud_opinions_dpo_file_written(self, temp_shadow_workspace):
        synthesizer = temp_shadow_workspace["synthesizer"]
        res = synthesizer.synthesize_generation_handoff(generation_number=6)
        assert res["dpo_distilled"] is True

        from tiny_model_shadow_coder_and_handoff_engine import HANDOFF_OPINIONS_DPO_FILE
        assert HANDOFF_OPINIONS_DPO_FILE.exists()
        with open(HANDOFF_OPINIONS_DPO_FILE, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        assert len(records) >= 1
        assert "consensus_score" in records[-1]
        assert records[-1]["financial_cost"] == 0.00
