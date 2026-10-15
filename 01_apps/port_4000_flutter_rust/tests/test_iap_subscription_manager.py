#!/usr/bin/env python3
import pytest
import sys
from pathlib import Path

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust")
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.state.iap_subscription_manager import IAPSubscriptionManager

@pytest.fixture
def iap_mgr():
    return IAPSubscriptionManager()

def test_iap_catalog(iap_mgr):
    catalog = iap_mgr.get_product_catalog()
    assert len(catalog["products"]) == 3
    assert catalog["store_compliance"]["apple_guideline_3_1_1"] == "COMPLIANT_STOREKIT_2"

def test_storekit_receipt_verification(iap_mgr):
    receipt = iap_mgr.verify_storekit_receipt("tx_12345", "orig_tx_12345", "ai.lauburu.athlete.pro")
    assert receipt["verified"] is True
    assert receipt["status"] == "ACTIVE_SUBSCRIPTION"
    assert "pro_tier" in receipt["entitlements_active"]
    assert receipt["token_role"] == "ROLE_ATHLETE_PRO"

def test_feature_access_gating(iap_mgr):
    # Free tier cannot access 3D kinematics
    assert iap_mgr.check_feature_access("ROLE_FREE", "3d_kinematics") is False
    # Pro tier can access 3D kinematics
    assert iap_mgr.check_feature_access("ROLE_ATHLETE_PRO", "3d_kinematics") is True
    # Pro tier cannot access LoRA distillation
    assert iap_mgr.check_feature_access("ROLE_ATHLETE_PRO", "lora_distillation") is False
    # Gym master can access all
    assert iap_mgr.check_feature_access("ROLE_GYM_MASTER", "lora_distillation") is True
