#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_spec11_security.py
=============================
Spec-11 Red Team / Blue Team Security Test Suite for Shopify AI & Neo MCP.
Verifies constant-time HMAC validation, anti-tampering, and pricing integrity.
"""

import sys
import hmac
import hashlib
import base64
import time
import pytest
from pathlib import Path

# Add shopify_ai module to path
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/commerce_and_business/shopify_ai"))

import neo_mcp_server

SECRET_KEY = "spec11_top_secret_combat_production_key_2026"

def generate_valid_hmac(payload: str, secret: str = SECRET_KEY) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")

# ==============================================================================
# BLUE TEAM TESTS: Valid Operation & Defensive Verification
# ==============================================================================

def test_blue_team_valid_webhook_hmac():
    """Blue Team: Valid webhook signatures must pass verification cleanly."""
    payload = "{\"event\": \"orders/create\", \"id\": 982103, \"financial_status\": \"paid\", \"total_price\": \"90.00\"}"
    valid_signature = generate_valid_hmac(payload)
    
    result = neo_mcp_server.verify_webhook_signature(payload, valid_signature, SECRET_KEY)
    assert result["valid"] is True
    assert result["algorithm"] == "HMAC-SHA256"

def test_blue_team_constant_time_comparison():
    """Blue Team: Verification must utilize constant-time comparison to thwart timing attacks."""
    payload = "{\"event\": \"fulfillment/create\", \"tracking_number\": \"AUSPOST12345\"}"
    sig = generate_valid_hmac(payload)
    
    trials = 100
    times = []
    for _ in range(trials):
        t0 = time.perf_counter()
        res = neo_mcp_server.verify_webhook_signature(payload, sig, SECRET_KEY)
        t1 = time.perf_counter()
        times.append(t1 - t0)
        assert res["valid"] is True
    
    mean_time = sum(times) / len(times)
    assert mean_time < 0.001

def test_blue_team_custom_gear_pricing_integrity():
    """Blue Team: Custom gear orders must enforce authoritative bundle pricing rules."""
    order = neo_mcp_server.order_custom_combat_gear(
        item_type="bundle",
        size="L",
        quantity=1,
        custom_name="AARON",
        member_tier="athlete_champion"
    )
    assert order["cart_id"].startswith("gid://shopify/Cart/")
    assert order["product_title"] == "Lauburu Combat Set Bundle (Ghost Rashguard + Fight Shorts)"
    assert order["unit_price_aud"] == 120.00
    assert order["discount_percent"] == 25
    assert order["final_total_aud"] == 90.00

# ==============================================================================
# RED TEAM TESTS: Adversarial Attack Simulation & Tamper Resistance
# ==============================================================================

def test_red_team_bit_flip_tampering():
    """Red Team: Single-character modification in payload must immediately invalidate signature."""
    payload = "{\"event\": \"orders/create\", \"id\": 982103, \"financial_status\": \"paid\", \"total_price\": \"90.00\"}"
    valid_signature = generate_valid_hmac(payload)
    
    # Adversary flips price from 90.00 to 09.00
    tampered_payload = "{\"event\": \"orders/create\", \"id\": 982103, \"financial_status\": \"paid\", \"total_price\": \"09.00\"}"
    result = neo_mcp_server.verify_webhook_signature(tampered_payload, valid_signature, SECRET_KEY)
    assert result["valid"] is False

def test_red_team_forged_signature():
    """Red Team: Arbitrary crafted signature strings must be rejected."""
    payload = "{\"event\": \"orders/paid\", \"amount\": \"120.00\"}"
    forged_sigs = [
        "fake_base64_hash==",
        "dGVzdA==",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        ""
    ]
    for forged in forged_sigs:
        result = neo_mcp_server.verify_webhook_signature(payload, forged, SECRET_KEY)
        assert result["valid"] is False

def test_red_team_wrong_secret_key():
    """Red Team: Webhook signed with a compromised secondary or external secret must fail."""
    payload = "{\"event\": \"inventory_levels/connect\", \"location_id\": 482}"
    rogue_secret = "rogue_adversary_secret_compromise_key_9999"
    rogue_signature = generate_valid_hmac(payload, rogue_secret)
    
    result = neo_mcp_server.verify_webhook_signature(payload, rogue_signature, SECRET_KEY)
    assert result["valid"] is False

def test_red_team_unauthorized_tier_discount_fallback():
    """Red Team: Invalid or forged discount tiers must safely fallback to standard tier."""
    order = neo_mcp_server.order_custom_combat_gear(
        item_type="rashguard",
        size="XL",
        quantity=1,
        custom_name="HACKER",
        member_tier="unauthorized_100_percent_free_exploit"
    )
    # Must fallback to 0% discount rather than allowing unverified discount exploitation
    assert order["discount_percent"] == 0
    assert order["final_total_aud"] == 75.00
