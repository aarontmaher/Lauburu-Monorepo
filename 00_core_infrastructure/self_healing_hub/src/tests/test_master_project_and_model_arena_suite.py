#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Master Project-by-Project and Multi-Model Arena Suite
(Unconstrained 64-Model Fleet Verification)
"""

import sys
import pytest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from master_project_and_model_arena_suite import (
    run_master_suite,
    ALL_MODELS_DATA,
    REPORT_MD
)


def test_all_7_projects_pass_rate_100():
    res = run_master_suite()
    assert res["status"] == "SUCCESS"
    assert res["projects_tested"] == 7
    assert res["models_evaluated"] >= 60


def test_model_categories_coverage():
    categories = {m["cat"] for m in ALL_MODELS_DATA}
    assert "Cloud Frontier" in categories
    assert "Local Heavy / Giant" in categories
    assert "Mid-Weight Workhorses" in categories
    assert "Small & Edge Models" in categories
    assert "Sub-100M Nano & Micro Models" in categories
    assert "NPU Hardware Acceleration" in categories


def test_unconstrained_model_fleet_presence():
    model_ids = {m["id"] for m in ALL_MODELS_DATA}
    # Cloud Frontier & Apex Reasoners
    assert "gemini_3_1_pro" in model_ids
    assert "deepseek_r1_671b" not in model_ids, "Unrunnable 671B behemoth must be excluded"
    assert "deepseek_r1_distill_32b" in model_ids
    assert "gemini_3_8_flash_high" in model_ids
    # Local Giants & Distributed MoE
    assert "qwen3_next_80b_moe" in model_ids
    assert "mixtral_8x22b_moe" in model_ids
    assert "llama_33_70b_dense" in model_ids
    assert "qwen_38_max" in model_ids
    assert "qwen_38_max_abliterated" in model_ids
    # Mid-weight Workhorses
    assert "gpt_oss_20b" in model_ids
    assert "deepseek_coder_v2_lite" in model_ids
    assert "qwen_2_5_coder_14b" in model_ids
    assert "qwen_2_5_coder_7b" in model_ids
    # Small & Edge Models
    assert "qwen_2_5_coder_1_5b" in model_ids
    assert "smollm2_135m_speculative" in model_ids
    # Sub-100M Nano & Micro Models
    assert "pythia_70m" in model_ids
    assert "faster_whisper_tiny_39m" in model_ids
    assert "tinystories_20m" in model_ids
    assert "silero_vad_v6_onnx" in model_ids
    assert "tinystories_656k" in model_ids
    # NPU Hardware Models
    assert "pantompkins_qrs_8m_npu" in model_ids
    assert "silero_vad_9m_npu" in model_ids
    assert "nanovision_ocr_10m_npu" in model_ids


def test_npu_models_latency_and_efficiency():
    npu_models = [m for m in ALL_MODELS_DATA if m["cat"] == "NPU Hardware Acceleration"]
    assert len(npu_models) >= 7
    for m in npu_models:
        # All NPU models must achieve sub-3ms TTFT
        assert m["ttft"] <= 3.0, f"NPU model {m['name']} exceeded 3ms TTFT: {m['ttft']}ms"
        assert m["tps"] >= 100.0, f"NPU model {m['name']} below 100 t/s: {m['tps']}"


def test_sub100m_nano_models_latency_and_efficiency():
    nano_models = [m for m in ALL_MODELS_DATA if m["cat"] == "Sub-100M Nano & Micro Models"]
    assert len(nano_models) >= 5
    for m in nano_models:
        assert m["ttft"] <= 1.5, f"Nano model {m['name']} exceeded 1.5ms TTFT: {m['ttft']}ms"
        assert m["tps"] >= 300.0, f"Nano model {m['name']} below 300 t/s: {m['tps']}"


def test_obsidian_report_generated():
    assert REPORT_MD.exists()
    assert REPORT_MD.stat().st_size > 5000
    with open(REPORT_MD, "r", encoding="utf-8") as f:
        content = f.read()
    assert "00_core_infrastructure" in content
    assert "01_apps" in content
    assert "02_ai_models_and_inference" in content
    assert "Apple Neural Engine (ANE)" in content
    assert "Google Tensor G5 Edge TPU" in content
    assert "TinyStories-656K" in content
    assert "Qwen3-Next-80B-A3B MoE" in content


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
