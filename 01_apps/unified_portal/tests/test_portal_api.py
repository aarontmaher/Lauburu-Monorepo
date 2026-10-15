import pytest
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.payments import PaymentEngine
from modules.compute_calculator import ComputeCalculator
from modules.movesense_readiness import MovesenseReadinessEngine
from modules.addon_apps import AddonAppsEngine
from modules.cross_app_rag import CrossAppRAGEngine
from modules.permissions import PermissionGovernor

def test_payments_and_credit_ledger():
    uid = f"test_user_{int(time.time()*1000)}"
    status = PaymentEngine.get_account_status(uid)
    assert "compute_credits_balance" in status
    assert "tier" in status
    assert status["tier"] == "FREE"

    # Purchase credits
    res = PaymentEngine.purchase_credits(uid, "PACK_50K")
    assert res["status"] == "SUCCESS"
    assert res["credits_added"] == 50000
    assert res["new_balance"] == 60000

def test_compute_savings_calculator():
    calc = ComputeCalculator.calculate_mesh_savings(1_000_000)
    assert calc["local_tokens_generated"] == 1_000_000
    assert calc["net_savings_aud"] > 0
    assert calc["roi_multiplier"] > 10.0
    assert "openai_gpt4o" in calc["cloud_costs_avoided_usd"]

def test_movesense_readiness_engine():
    readiness = MovesenseReadinessEngine.get_live_readiness()
    assert "heart_rate_bpm" in readiness
    assert "hrv_rmssd_ms" in readiness
    assert "dfa_alpha1" in readiness
    assert 0 <= readiness["readiness_score"] <= 100
    assert readiness["qrs_detection_confidence"] > 0.95

def test_addon_apps_and_screen_lens_engine():
    data = AddonAppsEngine.get_all_dashboard_data()
    assert "zone2_endurance" in data
    assert "nutrition" in data
    assert "sleep_analysis" in data
    assert "workout_analysis" in data
    assert "screen_lens" in data
    assert "automatic_journal" in data
    assert "weight_training" in data
    assert "training_analysis" in data
    assert data["screen_lens"]["focus_score"] >= 80

def test_permissions_governor():
    perms = PermissionGovernor.get_all_permissions()
    assert len(perms) >= 6
    p_ids = [p["id"] for p in perms]
    assert "screen_capture" in p_ids
    assert "bluetooth_ble" in p_ids
    assert "local_vault_storage" in p_ids

    # Toggle permission test
    res = PermissionGovernor.update_permission("screen_capture", False)
    assert res["status"] == "SUCCESS"
    assert PermissionGovernor.is_granted("screen_capture") is False

    # Restore permission
    PermissionGovernor.update_permission("screen_capture", True)
    assert PermissionGovernor.is_granted("screen_capture") is True

def test_cross_app_rag_context_and_chat():
    context = CrossAppRAGEngine.build_holistic_context()
    assert "Movesense HR+" in context
    assert "Automatic Daily Journal" in context
    assert "Weight Training" in context
    assert "Screen Lens" in context

    chat_res = CrossAppRAGEngine.generate_chat_response("Summarize my focus score and readiness.")
    assert "response" in chat_res
    assert chat_res["rag_grounded"] is True
    assert len(chat_res["response"]) > 50
