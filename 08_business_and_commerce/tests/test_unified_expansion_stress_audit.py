#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_unified_expansion_stress_audit.py
============================================
Adversarial empirical stress-test suite for Milestones 2 & 3:
- EAN-13 GS1 Modulo-10 checksum audit for all 30 variants
- Unit economics & landed cost recalculation across FX 0.60 to 0.70 (margin >= 65% gate)
- 30-variant matrix topology, size/edition uniqueness, SKU and barcode deduplication
- Webhook HMAC-SHA256 signature verification & constant-time timing attack immunity
- LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL bypass vulnerability analysis
"""

import sys
import os
import json
import hmac
import hashlib
import base64
import time
from pathlib import Path
import pytest

COMMERCE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce")
EXPANSION_PLAN_DIR = COMMERCE_ROOT / "unified_expansion_plan"
PAYLOAD_PATH = EXPANSION_PLAN_DIR / "shopify_catalog_rashguards_payload.json"
DIRECTIVE_PATH = EXPANSION_PLAN_DIR / "subliminator_sample_order_directive.json"
NEO_MCP_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/commerce_and_business/shopify_ai")

sys.path.insert(0, str(NEO_MCP_PATH))


@pytest.fixture(scope="session")
def catalog_payload():
    assert PAYLOAD_PATH.exists(), f"Payload file missing: {PAYLOAD_PATH}"
    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_directive():
    assert DIRECTIVE_PATH.exists(), f"Directive file missing: {DIRECTIVE_PATH}"
    with open(DIRECTIVE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_gs1_check_digit(digits_12: str) -> int:
    """Official GS1 Modulo-10 checksum algorithm for EAN-13."""
    assert len(digits_12) == 12 and digits_12.isdigit(), f"Invalid input: {digits_12}"
    total = 0
    for i, char in enumerate(digits_12):
        digit = int(char)
        # Even positions from 1-based (i=1, 3, 5, 7, 9, 11) weight 3; odd positions (i=0, 2, 4, 6, 8, 10) weight 1
        weight = 3 if (i % 2 == 1) else 1
        total += digit * weight
    remainder = total % 10
    return 0 if remainder == 0 else (10 - remainder)


def verify_ean13_barcode(barcode: str) -> bool:
    """Verify that a 13-digit EAN-13 barcode has a valid GS1 check digit."""
    if not isinstance(barcode, str) or len(barcode) != 13 or not barcode.isdigit():
        return False
    expected_check = calculate_gs1_check_digit(barcode[:12])
    actual_check = int(barcode[12])
    return expected_check == actual_check


# ==============================================================================
# 1. GS1 MODULO-10 EAN-13 BARCODE AUDIT
# ==============================================================================
def test_all_variant_barcodes_are_valid_ean13(catalog_payload):
    """Requirement 1: Mathematically audit every variant's EAN-13 barcode using official GS1 Modulo-10."""
    variants = catalog_payload["shopify_product_graphql_mutation_payload"]["input"]["variants"]
    assert len(variants) == 30, f"Expected 30 variants, found {len(variants)}"

    invalid_barcodes = []
    audit_log = []

    for v in variants:
        sku = v.get("sku", "UNKNOWN")
        barcode = v.get("barcode")
        valid = verify_ean13_barcode(barcode)
        expected_check = calculate_gs1_check_digit(barcode[:12]) if (barcode and len(barcode) >= 12) else None
        actual_check = int(barcode[12]) if (barcode and len(barcode) == 13 and barcode.isdigit()) else None

        audit_entry = {
            "sku": sku,
            "barcode": barcode,
            "expected_check_digit": expected_check,
            "actual_check_digit": actual_check,
            "valid": valid
        }
        audit_log.append(audit_entry)

        if not valid:
            invalid_barcodes.append(audit_entry)

    print(f"\n[BARCODE AUDIT] Verified {len(variants)} barcodes. Invalid count: {len(invalid_barcodes)}")
    assert len(invalid_barcodes) == 0, f"Found {len(invalid_barcodes)} invalid EAN-13 barcodes: {invalid_barcodes}"


# ==============================================================================
# 2. UNIT ECONOMICS & MARGIN DEFENSE STRESS AUDIT ACROSS FX [0.60, 0.70]
# ==============================================================================
def test_unit_economics_margin_defense_across_fx_rates(catalog_payload, sample_directive):
    """
    Requirement 2: Recalculate landed costs across AUD/USD exchange rates (0.60 to 0.70)
    to ensure margin never drops below 65% in worst case.
    """
    # Extract prices from catalog payload and sample directive
    variants = catalog_payload["shopify_product_graphql_mutation_payload"]["input"]["variants"]
    catalog_prices = [float(v["price"]) for v in variants]
    catalog_retail_price_aud = catalog_prices[0]
    
    # Check directive prices
    directive_dtc = sample_directive["unit_economics_and_margin_defense"]["dtc_retail_channel_economics"]
    directive_retail_aud = float(directive_dtc["retail_price_aud"])
    
    # Bulk terms
    bulk_terms = sample_directive["unit_economics_and_margin_defense"]["bulk_manufacturing_contract_terms"]
    factory_cogs_usd = float(bulk_terms["rashguard_bulk_express_usd"]) # $24.00 USD
    
    landed_model = sample_directive["unit_economics_and_margin_defense"]["landed_cost_modeling_bulk_run_200_units"]
    freight_per_unit_usd = float(landed_model["freight_per_unit_usd"]) # $3.50 USD
    customs_duty_per_unit_usd = float(landed_model["customs_and_import_duty_usd"]) / 200.0 # $1.375 USD
    total_landed_usd = factory_cogs_usd + freight_per_unit_usd + customs_duty_per_unit_usd # $28.875 USD
    
    processing_fee_aud = 2.60 # Standard Shopify + gateway fee

    fx_rates = [0.60, 0.62, 0.64, 0.66, 0.68, 0.70]
    
    results_catalog_price = []
    results_directive_price = []

    print("\n" + "="*80)
    print("UNIT ECONOMICS STRESS TEST: AUD/USD FX SENSITIVITY [0.60 -> 0.70]")
    print(f"Factory Base COGS: ${factory_cogs_usd:.2f} USD | Total Landed USD: ${total_landed_usd:.3f} USD")
    print("="*80)
    
    print("\n--- Model A: Catalog Payload Price ($85.00 AUD) ---")
    for fx in fx_rates:
        landed_cogs_aud = total_landed_usd / fx
        factory_only_cogs_aud = factory_cogs_usd / fx
        
        gross_profit = catalog_retail_price_aud - landed_cogs_aud
        gross_margin = (gross_profit / catalog_retail_price_aud) * 100.0
        
        net_profit = catalog_retail_price_aud - landed_cogs_aud - processing_fee_aud
        net_margin = (net_profit / catalog_retail_price_aud) * 100.0
        
        # Factory-only margin (no shipping/duty)
        factory_gross_profit = catalog_retail_price_aud - factory_only_cogs_aud
        factory_gross_margin = (factory_gross_profit / catalog_retail_price_aud) * 100.0
        
        res = {
            "fx": fx,
            "landed_cogs_aud": round(landed_cogs_aud, 2),
            "gross_margin_percent": round(gross_margin, 2),
            "net_margin_percent": round(net_margin, 2),
            "factory_gross_margin_percent": round(factory_gross_margin, 2),
            "passes_65_pct_threshold": gross_margin >= 65.0
        }
        results_catalog_price.append(res)
        print(f"FX {fx:.2f} | Landed COGS: ${landed_cogs_aud:.2f} AUD | Gross Margin: {gross_margin:.2f}% | Net Margin: {net_margin:.2f}% | Pass >=65%: {res['passes_65_pct_threshold']}")

    print("\n--- Model B: Directive Retail Price ($97.50 AUD) ---")
    for fx in fx_rates:
        landed_cogs_aud = total_landed_usd / fx
        factory_only_cogs_aud = factory_cogs_usd / fx
        
        gross_profit = directive_retail_aud - landed_cogs_aud
        gross_margin = (gross_profit / directive_retail_aud) * 100.0
        
        net_profit = directive_retail_aud - landed_cogs_aud - processing_fee_aud
        net_margin = (net_profit / directive_retail_aud) * 100.0
        
        factory_gross_profit = directive_retail_aud - factory_only_cogs_aud
        factory_gross_margin = (factory_gross_profit / directive_retail_aud) * 100.0
        
        res = {
            "fx": fx,
            "landed_cogs_aud": round(landed_cogs_aud, 2),
            "gross_margin_percent": round(gross_margin, 2),
            "net_margin_percent": round(net_margin, 2),
            "factory_gross_margin_percent": round(factory_gross_margin, 2),
            "passes_65_pct_threshold": gross_margin >= 65.0
        }
        results_directive_price.append(res)
        print(f"FX {fx:.2f} | Landed COGS: ${landed_cogs_aud:.2f} AUD | Gross Margin: {gross_margin:.2f}% | Net Margin: {net_margin:.2f}% | Pass >=65%: {res['passes_65_pct_threshold']}")

    # Critical Assertion Check:
    # 1. At $85.00 AUD (in shopify payload), margin is NEVER >= 65% for any FX rate in [0.60, 0.70]!
    all_catalog_failed = all(not r["passes_65_pct_threshold"] for r in results_catalog_price)
    
    # 2. At $97.50 AUD, even at FX=0.60 with full landed cost ($28.875 USD / 0.60 = $48.125 AUD),
    # Gross margin is (97.50 - 48.125) / 97.50 = 50.64%!
    # Only if landed cost is sea-consolidated or factory-only does margin exceed 65%.
    
    print("\n[STRESS AUDIT VERDICT ON MARGIN DEFENSE]:")
    print(f"Catalog Payload Price ($85.00 AUD) fails >= 65% margin in ALL cases: {all_catalog_failed}")
    
    # Return both results for analysis
    assert not all_catalog_failed, (
        f"CRITICAL DEFECT: Catalog payload lists retail price as $85.00 AUD. "
        f"At $85.00 AUD, gross margin ranges from {results_catalog_price[0]['gross_margin_percent']}% (at FX=0.60) "
        f"to {results_catalog_price[-1]['gross_margin_percent']}% (at FX=0.70). "
        f"It FAILS the >=65% margin gate across the ENTIRE exchange rate range!"
    )


# ==============================================================================
# 3. TOPOLOGY & VARIANT MATRIX VALIDATION (30 VARIANTS, 5 SIZES, 6 EDITIONS)
# ==============================================================================
def test_variant_matrix_topology_and_uniqueness(catalog_payload):
    """
    Requirement 3: Validate that all 30 variants map cleanly across 5 sizes and 6 editions
    without duplicate SKUs or handles.
    """
    input_data = catalog_payload["shopify_product_graphql_mutation_payload"]["input"]
    product_handle = input_data["handle"]
    options = input_data["options"]
    variants = input_data["variants"]

    assert product_handle == "lauburu-belt-ranked-competition-rashguard"
    
    # Verify Options
    assert len(options) == 2, f"Expected 2 options (Size, Edition), found {len(options)}"
    size_option = next(o for o in options if o["name"] == "Size")
    edition_option = next(o for o in options if o["name"] == "Edition")

    expected_sizes = ["S", "M", "L", "XL", "2XL"]
    expected_editions = [
        "Black & Gold Sovereign Master",
        "IBJJF Ranked White",
        "IBJJF Ranked Blue",
        "IBJJF Ranked Purple",
        "IBJJF Ranked Brown",
        "IBJJF Ranked Black"
    ]

    assert size_option["values"] == expected_sizes
    assert edition_option["values"] == expected_editions

    # Verify Variants Count
    assert len(variants) == 30, f"Expected exactly 30 variants, found {len(variants)}"

    # Check for duplicate SKUs and duplicate Barcodes
    skus = [v["sku"] for v in variants]
    barcodes = [v["barcode"] for v in variants]
    titles = [v["title"] for v in variants]

    assert len(skus) == len(set(skus)), f"Duplicate SKUs detected! {len(skus) - len(set(skus))} duplicates."
    assert len(barcodes) == len(set(barcodes)), f"Duplicate barcodes detected! {len(barcodes) - len(set(barcodes))} duplicates."
    assert len(titles) == len(set(titles)), f"Duplicate titles detected! {len(titles) - len(set(titles))} duplicates."

    # Verify clean mapping across all 5 sizes x 6 editions
    mapped_combinations = set()
    for v in variants:
        opts = {opt["name"]: opt["value"] for opt in v["selectedOptions"]}
        size_val = opts.get("Size")
        edition_val = opts.get("Edition")
        assert size_val in expected_sizes, f"Unknown size: {size_val} in SKU {v['sku']}"
        assert edition_val in expected_editions, f"Unknown edition: {edition_val} in SKU {v['sku']}"
        
        pair = (size_val, edition_val)
        assert pair not in mapped_combinations, f"Duplicate option pair detected: {pair}"
        mapped_combinations.add(pair)

    assert len(mapped_combinations) == 30, f"Expected 30 unique combinations, found {len(mapped_combinations)}"
    print(f"\n[TOPOLOGY AUDIT] Verified 30 unique variants perfectly covering 5 sizes x 6 editions with 0 collisions.")


# ==============================================================================
# 4. WEBHOOK HMAC-SHA256 SIGNATURE VERIFICATION & TIMING ATTACK SECURITY
# ==============================================================================
def test_webhook_hmac_sha256_timing_attack_security():
    """
    Requirement 4: Verify webhook HMAC-SHA256 signature verification logic and payload security against timing attacks.
    """
    import neo_mcp_server

    secret = "production_webhook_secret_test_key_2026"
    valid_payload = json.dumps({"event": "orders/paid", "order_id": 982103, "sku": "LBR-RG-M-BLK-GLD", "total": "97.50"})
    
    # Compute signature
    digest = hmac.new(secret.encode("utf-8"), valid_payload.encode("utf-8"), hashlib.sha256).digest()
    valid_hmac = base64.b64encode(digest).decode("utf-8")

    # 1. Valid Signature Test
    res_valid = neo_mcp_server.verify_webhook_signature(valid_payload, valid_hmac, secret)
    assert res_valid["valid"] is True, "Valid signature must verify as True"

    # 2. Tampered Payload Test (Bit-flip attack)
    tampered_payload = valid_payload.replace("97.50", "07.50")
    res_tampered = neo_mcp_server.verify_webhook_signature(tampered_payload, valid_hmac, secret)
    assert res_tampered["valid"] is False, "Tampered payload must verify as False"

    # 3. Forged / Timing Attack Probe
    # Test timing of compare_digest across varied signature prefixes
    # hmac.compare_digest in Python C implementation executes in constant time
    forged_hmac_close = valid_hmac[:-4] + "AAAA"
    res_forged = neo_mcp_server.verify_webhook_signature(valid_payload, forged_hmac_close, secret)
    assert res_forged["valid"] is False, "Forged signature must verify as False"

    # 4. Confirm hmac.compare_digest is utilized in code (inspect source)
    import inspect
    src = inspect.getsource(neo_mcp_server.verify_webhook_signature)
    assert "hmac.compare_digest" in src, "Implementation MUST use constant-time hmac.compare_digest"
    assert "==" not in src.split("compare_digest")[0], "Naive equality check must not precede constant-time check"
    print("\n[WEBHOOK AUDIT] Confirmed Spec-11 constant-time HMAC-SHA256 verification and anti-tamper resilience.")


# ==============================================================================
# 5. PHYSICAL SAMPLE GATE BYPASS VULNERABILITY AUDIT
# ==============================================================================
def test_locked_until_physical_sample_approval_bypass_vulnerability(catalog_payload):
    """
    Requirement 5: Verify that LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL invariant cannot be bypassed by draft publishing.
    """
    input_data = catalog_payload["shopify_product_graphql_mutation_payload"]["input"]
    status = input_data["status"]
    variants = input_data["variants"]
    inventory_gov = catalog_payload.get("inventory_governance", {})
    gate_status = inventory_gov.get("physical_sample_gate_invariants", {}).get("gate_status")
    
    assert status == "DRAFT", "Initial status in payload must be DRAFT"
    assert gate_status == "LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL"

    # STRESS TEST ATTACK VECTOR:
    # Does the payload or webhook architecture contain an active circuit breaker preventing
    # sales if an administrative user or automated tool changes status to "ACTIVE"?
    
    vulnerabilities = []

    # Vulnerability 1: inventoryPolicy is set to CONTINUE on ALL 30 variants!
    continue_policies = [v for v in variants if v.get("inventoryPolicy") == "CONTINUE"]
    if len(continue_policies) == 30:
        vulnerabilities.append({
            "vector": "STOREFRONT_OVERSOLD_UPON_ACTIVE_PUBLISH",
            "finding": (
                "All 30 variants specify 'inventoryPolicy': 'CONTINUE'. If a Shopify merchant or "
                "automated workflow toggles product status from DRAFT to ACTIVE, Shopify immediately "
                "permits unlimited customer purchases without inventory deduction, directly violating "
                "the LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL restriction."
            )
        })

    # Vulnerability 2: Webhook routing filter does not validate sample approval gate
    webhook_arch = catalog_payload.get("subliminator_fulfillment_and_webhook_architecture", {})
    routing_filter = webhook_arch.get("ingress_webhook_endpoint", {}).get("order_routing_filter", {})
    
    # Check if order_routing_filter checks gate status
    filter_checks_gate = "gate" in str(routing_filter).lower() or "sample" in str(routing_filter).lower()
    if not filter_checks_gate:
        vulnerabilities.append({
            "vector": "WEBHOOK_ROUTER_AUTOMATIC_FACTORY_DISPATCH_WITHOUT_GATE_CHECK",
            "finding": (
                "The webhook ingress filter automatically dispatches any SKU starting with 'LBR-RG-' "
                "to Subliminator POST /v1/orders without verifying whether physical_sample_gate_invariants.gate_status "
                "has transitioned from LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL to APPROVED."
            )
        })

    # Vulnerability 3: Missing Shopify Storefront Cart Validation Function / Checkout Rule
    # Check if any validation function or checkout extension is configured in the payload
    has_checkout_validation = "checkout_validation" in catalog_payload or "cart_transform" in catalog_payload
    if not has_checkout_validation:
        vulnerabilities.append({
            "vector": "LACK_OF_SHOPIFY_FUNCTION_CHECKOUT_VALIDATION",
            "finding": (
                "There is no Shopify Function or Cart/Checkout Validation extension declared in the payload "
                "to block customer checkout at the Shopify platform level if sample gate is locked."
            )
        })

    print("\n" + "="*80)
    print("PHYSICAL SAMPLE GATE PENETRATION AUDIT RESULTS:")
    print(f"Total Critical Vulnerabilities Identified: {len(vulnerabilities)}")
    for i, v in enumerate(vulnerabilities, 1):
        print(f"[{i}] Vector: {v['vector']}")
        print(f"    Finding: {v['finding']}")
    print("="*80)

    # In an empirical review, if vulnerabilities exist that allow bypass by draft publishing,
    # the invariant CAN be bypassed!
    assert len(vulnerabilities) == 0, (
        f"SECURITY BREACH: LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL CAN be bypassed by draft publishing! "
        f"{len(vulnerabilities)} vulnerabilities detected: {[v['vector'] for v in vulnerabilities]}"
    )


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
