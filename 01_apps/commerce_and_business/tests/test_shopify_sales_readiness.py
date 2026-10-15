#!/usr/bin/env python3
"""
test_shopify_sales_readiness.py
================================
Empirical Test Suite for Shopify AI Storefront & Athlete Membership Monetization.
Verifies Storefront GraphQL cart generation, webhook HMAC security, and RevenueCat entitlement grants.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import hashlib
import hmac
from shopify_storefront_engine import ShopifyStorefrontEngine, MEMBERSHIP_TIERS, HARDWARE_KITS

@pytest.fixture
def engine():
    return ShopifyStorefrontEngine(webhook_secret="production_secure_webhook_secret_2026")

def test_membership_catalog(engine):
    tiers = engine.list_membership_tiers()
    assert len(tiers) >= 3
    tier_ids = [t["tier_id"] for t in tiers]
    assert "athlete_starter" in tier_ids
    assert "athlete_pro" in tier_ids
    assert "mesh_gym_master" in tier_ids

def test_cart_creation_subscription_only(engine):
    cart = engine.create_checkout_cart("athlete_starter", include_hardware_kit=False)
    assert cart["status"] == "ready_for_checkout"
    assert cart["total_aud"] == 9.00
    assert len(cart["items"]) == 1
    assert cart["items"][0]["sku"] == "SUB-ATHLETE_STARTER"

def test_cart_creation_with_hardware_kit_discount(engine):
    # Pro tier has 15% discount on $249 hardware kit ($249 - $37.35 = $211.65) + $29.00 sub = $240.65
    cart = engine.create_checkout_cart("athlete_pro", include_hardware_kit=True)
    assert cart["status"] == "ready_for_checkout"
    expected_hw_price = round(249.00 - (249.00 * 0.15), 2)
    expected_total = round(29.00 + expected_hw_price, 2)
    assert cart["total_aud"] == expected_total
    assert len(cart["items"]) == 2

def test_webhook_hmac_cryptographic_verification(engine):
    body = b"{\"id\": 99999, \"email\": \"test@lauburu.ai\"}"
    secret = "production_secure_webhook_secret_2026"
    valid_hmac = hashlib.sha256(secret.encode("utf-8") + body).hexdigest()
    
    # Valid signature check
    assert engine.verify_webhook_hmac(valid_hmac, body) is True
    # Tampered signature check
    assert engine.verify_webhook_hmac("tampered_invalid_hmac", body) is False

def test_order_created_webhook_entitlement_grant(engine):
    order = {
        "id": 8209829119461,
        "email": "champion@lauburu.ai",
        "line_items": [
            {"title": "Lauburu Mesh Node & Biometrics Kit", "sku": "LBR-HW-001"},
            {"title": "Athlete Pro & Combat", "sku": "SUB-ATHLETE_PRO"}
        ]
    }
    res = engine.handle_order_created_webhook(order)
    assert res["status"] == "success"
    assert res["email"] == "champion@lauburu.ai"
    assert len(res["entitlements_processed"]) == 2

def test_token_gate_module_authorization(engine):
    auth = engine.verify_customer_token_gate("cust_123", "grappling_3d")
    assert auth["access_granted"] is True
    assert auth["member_role"] == "ROLE_GYM_MASTER"
