import pytest
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from sensor_condenser import EdgeSensorCondenser
from speculative_draft_router import SpeculativeDraftEngine
from fast_adversarial_auditor import FastAdversarialAuditor
from unified_specialist_mesh_coordinator import UnifiedSpecialistMeshCoordinator


def test_edge_sensor_condenser():
    condenser = EdgeSensorCondenser()
    raw_ecg = [float(x) for x in range(512)]
    res = condenser.condense_512hz_ecg_stream(raw_ecg)
    assert res["raw_samples_ingested"] == 512
    assert "heart_rate_bpm" in res["semantic_card"]
    assert "dfa_alpha1" in res["semantic_card"]
    assert "Biometrics:" in res["prompt_injection_text"]


def test_speculative_draft_engine():
    engine = SpeculativeDraftEngine(draft_k=4)
    res = engine.generate_speculative_block("Test prompt", total_target_tokens=20)
    assert res["total_tokens_generated"] == 20
    assert res["effective_tps"] > 50.0
    assert res["mean_tokens_per_step"] >= 1.0


def test_fast_adversarial_auditor():
    auditor = FastAdversarialAuditor()
    # Clean proposal
    res_clean = auditor.audit_proposal("Valid implementation with live movesense stream", {})
    assert res_clean["verdict"] == "APPROVED_BY_ADVERSARY"
    assert res_clean["rule_0_clean"] is True

    # Dirty proposal with mock
    res_dirty = auditor.audit_proposal("Generate mock simulated ecg dataset", {})
    assert res_dirty["verdict"] == "VETOED_BY_ADVERSARY"
    assert res_dirty["rule_0_clean"] is False


def test_unified_specialist_coordinator():
    coordinator = UnifiedSpecialistMeshCoordinator()
    raw_ecg = [float(x) for x in range(512)]
    res = coordinator.process_raw_stream_pipeline(raw_ecg, "Valid prompt")
    assert res["status"] == "SUCCESS"
    assert res["pipeline_metrics"]["context_tokens_saved"] > 400
    assert res["adversarial_audit"] == "APPROVED_BY_ADVERSARY"
