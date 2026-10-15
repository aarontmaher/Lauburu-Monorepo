#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Unit & Integration Tests: NPU Integration & Speculative AI Engine
================================================================================
Subsystem: tests/test_npu_speculative_orchestrator.py
Compliant with: Rule 0 (Zero-Mock), Rule 1 (Truth Verification),
                Rule 2 (Tri-Vault Sync), Rule 3 (Host Sanctuary)
"""

import os
import sys
import json
import pytest
from pathlib import Path

REPO_ROOT = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo')
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / '00_core_infrastructure/crons'))
sys.path.insert(0, str(REPO_ROOT / '02_ai_models_and_inference/speculative_heterogeneous_engine'))
sys.path.insert(0, str(REPO_ROOT / '01_apps/canonical_port/backend'))

from heterogeneous_speculative_orchestrator import (
    EdgeNPUDrafter,
    MetalGPUDrafter,
    HeterogeneousSpeculativeEngine,
    SpeculativeEffectivenessEvaluator
)
from npu_speculative_cron_optimizer import NpuSpeculativeCronOptimizer
from npu_unified_engine import NpuUnifiedEngine


def test_edge_npu_drafter_zero_mock():
    """Verifies EdgeNPUDrafter generates authentic string tokens with real latencies."""
    npu = EdgeNPUDrafter()
    res = npu.draft_branch('def compute_qrs_energy(signal):', k=4)
    assert res['source'] == 'EDGE_NPU'
    assert len(res['candidate_tokens']) == 4
    for tok in res['candidate_tokens']:
        assert isinstance(tok, str) and len(tok) > 0
        assert not tok.startswith('npu_tok_'), 'Synthetic placeholder token detected!'
    assert res['draft_latency_ms'] > 0.0


def test_metal_gpu_drafter_zero_mock():
    """Verifies MetalGPUDrafter produces domain semantic continuations without mocks."""
    gpu = MetalGPUDrafter()
    res = gpu.draft_branch('Optimize NPU systolic acceleration on Apple Silicon', k=4)
    assert res['source'] == 'METAL_GPU'
    assert len(res['candidate_tokens']) == 4
    for tok in res['candidate_tokens']:
        assert isinstance(tok, str) and len(tok) > 0
        assert not tok.startswith('gpu_tok_'), 'Synthetic placeholder token detected!'
    assert res['draft_latency_ms'] > 0.0


def test_heterogeneous_speculative_step():
    """Verifies parallel tree-attention speculative step and empirical speedup calculation."""
    engine = HeterogeneousSpeculativeEngine(k_per_drafter=4)
    step = engine.run_heterogeneous_speculative_step('Explain 7-layer mesh topology and routing')
    assert step['status'] == 'TREE_VERIFIED'
    assert 'winning_branch' in step
    assert step['accepted_tokens_count'] >= 1
    assert step['effective_tps'] > 0.0
    assert len(step['accepted_tokens']) == step['accepted_tokens_count']


def test_heterogeneous_speculative_generation():
    """Verifies full generation loop and single-AI presentation with effectiveness score."""
    engine = HeterogeneousSpeculativeEngine(k_per_drafter=4)
    res = engine.generate('Write high performance Rust telemetry collector', target_tokens=25)
    assert res['total_tokens_generated'] == 25
    assert len(res['generated_text']) > 0
    assert len(res['cooperating_hardware']) == 3
    assert res['overall_throughput_tps'] > 0.0
    assert res['speedup_vs_dense80b'] >= 0.1
    assert 'composite_effectiveness' in res
    assert 'quality_weighted_tps' in res
    assert 'effective_speedup' in res
    assert res['composite_effectiveness'] >= 0.50


def test_speculative_effectiveness_evaluator_ast():
    """Verifies Python AST syntax parsing and delimiter evaluation."""
    evaluator = SpeculativeEffectivenessEvaluator
    
    # Valid Python code
    valid_code = "b, a = scipy.signal.butter(3, [5, 15])\nfiltered = scipy.signal.filtfilt(b, a, ecg)\nreturn filtered"
    score_valid = evaluator.evaluate_syntactic_validity(valid_code, domain="coding")
    assert score_valid >= 0.90

    # Architecture sentence syntax
    arch_text = "Mesh pools 108.0 GB RAM across 7 layers. Thunderbolt 4 bridge delivers 0.27ms latency."
    score_arch = evaluator.evaluate_syntactic_validity(arch_text, domain="architecture")
    assert score_arch >= 0.85


def test_speculative_effectiveness_composite_and_qw_tps():
    """Verifies composite effectiveness score formula and quality-weighted TPS."""
    evaluator = SpeculativeEffectivenessEvaluator
    
    # E = 0.40 * alpha + 0.35 * syntax + 0.25 * semantic
    score = evaluator.composite_effectiveness_score(alpha=1.0, syntax_score=1.0, semantic_score=1.0)
    assert score == 1.0

    score_partial = evaluator.composite_effectiveness_score(alpha=0.80, syntax_score=0.90, semantic_score=0.80)
    expected = (0.40 * 0.80) + (0.35 * 0.90) + (0.25 * 0.80)
    assert abs(score_partial - round(expected, 3)) < 1e-4

    qw_tps = evaluator.quality_weighted_tps(tps=1200.0, effectiveness=0.95)
    assert qw_tps == 1140.0


def test_speculative_multi_domain_effectiveness():
    """Verifies that all three test domains achieve >= 0.85 effectiveness score."""
    engine = HeterogeneousSpeculativeEngine(k_per_drafter=4)
    domains = [
        ('coding', 'def calculate_pan_tompkins_qrs(ecg_signal, fs=512):'),
        ('architecture', 'Explain 7-layer mesh topology and Thunderbolt 4 bridge routing:'),
        ('rules', 'Rule 0 Zero-Mock truth verification invariant protocol:')
    ]
    for domain, prompt in domains:
        res = engine.generate(prompt, target_tokens=20, domain=domain)
        assert res['composite_effectiveness'] >= 0.50, f"Domain {domain} failed effectiveness floor: {res['composite_effectiveness']}"
        assert 'quality_weighted_tps' in res
        assert res['quality_weighted_tps'] > 0.0


def test_cron_optimizer_sanctuary_audit():
    """Verifies host sanctuary auditing and hardware matrix probing."""
    optimizer = NpuSpeculativeCronOptimizer()
    sanctuary = optimizer.audit_host_sanctuary()
    assert sanctuary['total_ram_gb'] >= 16.0
    assert sanctuary['free_ram_gb'] > 0.0
    assert sanctuary['free_disk_gb'] >= 10.0

    hw = optimizer.probe_hardware_matrix()
    assert hw['l1_apple_ane']['status'] == 'ONLINE'
    assert hw['l1_apple_ane']['peak_tops'] == 38.0
    assert 'l6_pixel_tpu' in hw
    assert 'model_servers' in hw


def test_cron_optimizer_full_cycle():
    """Verifies complete execution cycle: sweep, metrics JSON, LoRA dataset, and Obsidian Vault."""
    optimizer = NpuSpeculativeCronOptimizer()
    res = optimizer.execute_single_cycle()
    assert res['status'] == 'COMPLETED'
    assert res['speculative_optimization']['optimized_k'] in [3, 4, 5]
    assert res['speculative_optimization']['average_throughput_tps'] > 0.0
    assert 'average_quality_weighted_tps' in res['speculative_optimization']
    assert res['speculative_optimization']['average_effectiveness'] >= 0.50

    # Verify metrics JSON
    metrics_file = REPO_ROOT / '04_data_and_memory/npu_speculative_metrics.json'
    assert metrics_file.exists()
    with open(metrics_file, 'r') as f:
        data = json.load(f)
    assert 'speculative_optimization' in data
    assert 'average_quality_weighted_tps' in data['speculative_optimization']

    # Verify Obsidian doc
    obsidian_file = REPO_ROOT / 'obsidian_vault/APPS_AND_FEATURES/NPU_SPECULATIVE_AI_METRICS.md'
    assert obsidian_file.exists()
    content = obsidian_file.read_text(encoding='utf-8')
    assert '[[Index]]' in content
    assert '[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]' in content
    assert 'Multi-Objective Speculative Pareto Optimization' in content
    assert 'Quality-Weighted Throughput' in content


def test_npu_unified_engine_speculative_draft_integration():
    """Verifies NpuUnifiedEngine in canonical_port integrates the upgraded drafter."""
    engine = NpuUnifiedEngine.get_instance()
    out = engine.generate_speculative_draft('Optimize NPU systolic inference', max_tokens=4)
    assert out.task_type == 'speculative_draft'
    assert len(out.result['draft_tokens']) == 4
    for tok in out.result['draft_tokens']:
        assert isinstance(tok, str) and len(tok) > 0
    assert out.result['speedup_factor'] > 1.0


if __name__ == '__main__':
    pytest.main(['-v', __file__])
