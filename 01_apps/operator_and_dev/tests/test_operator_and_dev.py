import sys
import os
import pytest

# Ensure operator_and_dev root is on path
OPERATOR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if OPERATOR_ROOT not in sys.path:
    sys.path.insert(0, OPERATOR_ROOT)

from smolagents_duel_sandbox.presentation.sandbox import SmolAgentsArenaHub
from smolagents_duel_sandbox.core.config import SandboxConfig
from smolagents_duel_sandbox.core.models import AgentAction, DuelExecutionRecord
from qwen_math_trend_optimizer.presentation.optimizer import AutonomousMathTrendOptimizer
from qwen_math_trend_optimizer.models.latency_proofs import compute_inverse_variance_weights
from qwen_math_trend_optimizer.models.ram_headroom import compute_ram_safety_headroom
from qwen_math_trend_optimizer.models.loss_trajectory import compute_loss_trajectory, compute_optimal_learning_rate
from qwen_math_trend_optimizer.models.cardiac_coherence import compute_cardiac_coherence

def test_smolagents_arena_hub_step():
    hub = SmolAgentsArenaHub()
    record = hub.step()
    assert record.step_id == 1
    assert record.red_action.agent_id == "hermes_3_red"
    assert record.red_action.status == "SUCCESS"
    assert record.blue_action.agent_id == "luci_blue"
    assert record.blue_action.status == "SUCCESS"
    assert "TB4_PROBE" in str(record.red_action.output)
    assert "FILTER_GUARD" in str(record.blue_action.output)
    assert record.red_action.execution_time_ms >= 0.0

def test_qwen_math_trend_optimizer_evaluate():
    opt = AutonomousMathTrendOptimizer()
    res = opt.evaluate_all()
    assert "latency_proofs" in res
    assert "ram_proof" in res
    assert "loss_forecast" in res
    assert "coherence" in res
    
    # Latency weights
    proofs = res["latency_proofs"]
    assert len(proofs) == 3
    assert proofs[0].is_optimal_primary is True  # TB4 DMA is lowest latency
    
    # RAM proof
    ram_proof = res["ram_proof"]
    assert ram_proof.is_safe is True
    assert ram_proof.ram_headroom_gb > 2.5
    
    # Loss trajectory
    loss = res["loss_forecast"]
    assert "step_1000" in loss.step_samples
    assert loss.optimal_learning_rate > 0

def test_cardiac_coherence():
    coherence = compute_cardiac_coherence(hr_bpm=72.0, rmssd_ms=48.0)
    assert coherence.is_zone2_optimal is True
    assert 0.0 <= coherence.coherence_ratio <= 1.0
