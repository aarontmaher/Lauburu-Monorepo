#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite for Shopify Storefront GraphQL & Member API Gateway
Subsystem: 01_apps/commerce/tests/test_shopify_gateway.py

Tests:
1. Shopify Storefront GraphQL Query Compilation & Dry-Run Validation
2. Cart Creation & Modification Payload Builders
3. Customer Profile Parsing & Membership Tier Mapping ('lauburu_pro', 'lauburu_elite', 'free')
4. HMAC-SHA256 Signed API Key Issuance & Cryptographic Verification
5. Sliding Window Rate Limiter (RPM / Daily Quotas & 429 Retry-After)
6. Gated Monetization Route Authorization & Zero-Mock Compliance
"""

import sys
import time
import unittest
from pathlib import Path

# Add commerce path to sys.path
COMMERCE_PATH = Path(__file__).resolve().parent.parent
if str(COMMERCE_PATH) not in sys.path:
    sys.path.insert(0, str(COMMERCE_PATH))

from shopify_storefront_gateway import (
    CustomerProfile,
    CustomerTier,
    GatewayResponse,
    MemberAPIGateway,
    ShopifyStorefrontGraphQLClient,
    SlidingWindowRateLimiter,
)


class TestShopifyStorefrontClient(unittest.TestCase):
    """Test suite for Shopify Storefront GraphQL Client."""

    def setUp(self):
        self.client = ShopifyStorefrontGraphQLClient(
            shop_domain="lauburu-ai.myshopify.com",
            storefront_access_token=None,  # Dry run mode
        )

    def test_graphql_query_syntax_dry_run(self):
        """Validates GraphQL queries in offline dry-run mode."""
        res_prod = self.client.execute_graphql(ShopifyStorefrontGraphQLClient.QUERY_PRODUCTS, dry_run=True)
        self.assertTrue(res_prod.get("valid_syntax"))
        self.assertEqual(res_prod.get("status"), "VALIDATED_OFFLINE")

        res_cart = self.client.execute_graphql(ShopifyStorefrontGraphQLClient.MUTATION_CART_CREATE, dry_run=True)
        self.assertTrue(res_cart.get("valid_syntax"))

        res_cust = self.client.execute_graphql(ShopifyStorefrontGraphQLClient.QUERY_CUSTOMER_PROFILE, dry_run=True)
        self.assertTrue(res_cust.get("valid_syntax"))

    def test_build_cart_create_input(self):
        """Constructs valid cart input payload for Storefront API."""
        payload = self.client.build_cart_create_input(
            variant_id="gid://shopify/ProductVariant/99887766",
            quantity=2,
            note="Annual Lauburu Pro Membership Bundle",
            custom_attributes=[{"key": "tier", "value": "lauburu_pro"}],
        )

        self.assertEqual(len(payload["lines"]), 1)
        self.assertEqual(payload["lines"][0]["merchandiseId"], "gid://shopify/ProductVariant/99887766")
        self.assertEqual(payload["lines"][0]["quantity"], 2)
        self.assertEqual(payload["lines"][0]["attributes"][0]["value"], "lauburu_pro")
        self.assertEqual(payload["note"], "Annual Lauburu Pro Membership Bundle")

    def test_parse_customer_profile_tiers(self):
        """Parses GraphQL customer profile and maps tags to membership tiers."""
        # 1. Pro Member
        pro_response = {
            "data": {
                "customer": {
                    "id": "gid://shopify/Customer/1001",
                    "email": "pro.user@lauburu.ai",
                    "firstName": "Alex",
                    "lastName": "Rios",
                    "tags": ["lauburu_pro", "newsletter_subscribed"],
                    "createdAt": "2026-01-15T08:30:00Z",
                    "orders": {"edges": [{"node": {"id": "1", "totalPrice": {"amount": "299.00"}}}]},
                }
            }
        }
        pro_profile = self.client.parse_customer_profile(pro_response)
        self.assertIsNotNone(pro_profile)
        self.assertEqual(pro_profile.tier, CustomerTier.PRO)
        self.assertTrue(pro_profile.has_active_subscription)

        # 2. Elite Member
        elite_response = {
            "data": {
                "customer": {
                    "id": "gid://shopify/Customer/1002",
                    "email": "elite.user@lauburu.ai",
                    "tags": ["lauburu_elite", "vip"],
                    "createdAt": "2026-02-01T12:00:00Z",
                    "orders": {"edges": []},
                }
            }
        }
        elite_profile = self.client.parse_customer_profile(elite_response)
        self.assertEqual(elite_profile.tier, CustomerTier.ELITE)

        # 3. Free User
        free_response = {
            "data": {
                "customer": {
                    "id": "gid://shopify/Customer/1003",
                    "email": "free.user@lauburu.ai",
                    "tags": ["standard_community"],
                    "createdAt": "2026-03-01T12:00:00Z",
                    "orders": {"edges": []},
                }
            }
        }
        free_profile = self.client.parse_customer_profile(free_response)
        self.assertEqual(free_profile.tier, CustomerTier.FREE)


class TestMemberAPIGateway(unittest.TestCase):
    """Test suite for Member API Gateway authentication, rate limiting, and route gating."""

    def setUp(self):
        self.gateway = MemberAPIGateway(secret_key="test_secret_key_lauburu_2026")

    def test_api_key_lifecycle_and_verification(self):
        """Issues HMAC signed API key and verifies authenticity."""
        token = self.gateway.issue_api_key(customer_id="cust_8821", tier=CustomerTier.PRO, expiry_days=7)
        self.assertTrue(token.startswith("lb_lauburu_pro_"))

        info = self.gateway.verify_api_key(token)
        self.assertIsNotNone(info)
        cust_hex, tier, expiry = info
        self.assertEqual(tier, CustomerTier.PRO)
        self.assertGreater(expiry, time.time())

    def test_tampered_and_invalid_tokens_rejected(self):
        """Tampered signatures, altered tiers, or bad prefixes are rejected."""
        valid_token = self.gateway.issue_api_key(customer_id="cust_1", tier=CustomerTier.FREE)

        # Alter signature suffix
        tampered_token = valid_token[:-4] + "dead"
        self.assertIsNone(self.gateway.verify_api_key(tampered_token))

        # Alter tier prefix
        tampered_tier = valid_token.replace("free", "lauburu_elite")
        self.assertIsNone(self.gateway.verify_api_key(tampered_tier))

        # Random garbage
        self.assertIsNone(self.gateway.verify_api_key("invalid_token_format"))
        self.assertIsNone(self.gateway.verify_api_key(""))

    def test_sliding_window_rate_limiter(self):
        """Rate limiter enforces RPM limit and returns 429 when exhausted."""
        limiter = SlidingWindowRateLimiter()
        client_key = "test_client_001"
        tier = CustomerTier.FREE  # 60 RPM

        t_now = 1000.0
        # First 60 requests should pass
        for i in range(60):
            allowed, remaining, _ = limiter.check_and_record(client_key, tier, current_time=t_now)
            self.assertTrue(allowed)
            self.assertEqual(remaining, 59 - i)

        # 61st request in the same minute window must be rejected
        allowed, remaining, retry_after = limiter.check_and_record(client_key, tier, current_time=t_now)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)

        # After 61 seconds, quota resets
        allowed_later, remaining_later, _ = limiter.check_and_record(client_key, tier, current_time=t_now + 61.0)
        self.assertTrue(allowed_later)
        self.assertGreater(remaining_later, 0)

    def test_gated_endpoints_authorization(self):
        """Validates tier-based endpoint gating and error codes."""
        free_token = self.gateway.issue_api_key("cust_free", CustomerTier.FREE)
        pro_token = self.gateway.issue_api_key("cust_pro", CustomerTier.PRO)

        # 1. Unauthenticated request -> 401
        res_401 = self.gateway.handle_request("/api/v1/telemetry/ecg", api_token=None)
        self.assertEqual(res_401.status_code, 401)
        self.assertFalse(res_401.success)

        # 2. Telemetry endpoint -> 200 for all authenticated users
        res_free_ecg = self.gateway.handle_request("/api/v1/telemetry/ecg", api_token=free_token)
        self.assertEqual(res_free_ecg.status_code, 200)
        self.assertTrue(res_free_ecg.success)
        self.assertEqual(res_free_ecg.data["max_sampling_rate_hz"], 128)

        res_pro_ecg = self.gateway.handle_request("/api/v1/telemetry/ecg", api_token=pro_token)
        self.assertEqual(res_pro_ecg.status_code, 200)
        self.assertEqual(res_pro_ecg.data["max_sampling_rate_hz"], 512)

        # 3. LoRA Distill trigger -> 403 Forbidden for FREE, 200 OK for PRO
        res_free_lora = self.gateway.handle_request("/api/v1/lora/distill", api_token=free_token)
        self.assertEqual(res_free_lora.status_code, 403)
        self.assertFalse(res_free_lora.success)

        res_pro_lora = self.gateway.handle_request("/api/v1/lora/distill", api_token=pro_token)
        self.assertEqual(res_pro_lora.status_code, 200)
        self.assertTrue(res_pro_lora.success)

        # 4. Commerce checkout endpoint -> 200 OK
        res_checkout = self.gateway.handle_request(
            "/api/v1/commerce/checkout",
            api_token=pro_token,
            request_body={"variant_id": "gid://shopify/ProductVariant/123", "quantity": 1},
        )
        self.assertEqual(res_checkout.status_code, 200)
        self.assertIn("INITIATE_STOREFRONT_CHECKOUT", res_checkout.data["checkout_action"])

        # 4b. Canonical POD checkout endpoint -> handled by gateway
        res_pod = self.gateway.handle_request(
            "/api/v1/commerce/pod/checkout",
            api_token=pro_token,
            request_body={"product_key": "utility_backpack", "quantity": 1},
        )
        self.assertIn(res_pod.status_code, [200, 400])

        # 5. Non-existent endpoint -> 404 Not Found
        res_404 = self.gateway.handle_request("/api/v1/non_existent_route", api_token=pro_token)
        self.assertEqual(res_404.status_code, 404)

    def test_entitlement_endpoint(self):
        """Tests unified mobile entitlement resolution for Free, Pro, and Elite users."""
        free_token = self.gateway.issue_api_key("cust_free_101", CustomerTier.FREE)
        pro_token = self.gateway.issue_api_key("cust_pro_102", CustomerTier.PRO)
        elite_token = self.gateway.issue_api_key("cust_elite_103", CustomerTier.ELITE)

        # 1. Free entitlement
        res_free = self.gateway.handle_request("/api/v1/entitlement", api_token=free_token)
        self.assertEqual(res_free.status_code, 200)
        self.assertEqual(res_free.data["tier"], "free")
        self.assertFalse(res_free.data["quotas"]["raw_ecg_512hz_allowed"])
        self.assertNotIn("movesense_512hz_raw", res_free.data["features"])

        # 2. Pro entitlement
        res_pro = self.gateway.handle_request("/api/v1/entitlement", api_token=pro_token)
        self.assertEqual(res_pro.status_code, 200)
        self.assertEqual(res_pro.data["tier"], "lauburu_pro")
        self.assertTrue(res_pro.data["quotas"]["raw_ecg_512hz_allowed"])
        self.assertIn("movesense_512hz_raw", res_pro.data["features"])
        self.assertIn("tb4_10gbps_sharding", res_pro.data["features"])

        # 3. Elite entitlement
        res_elite = self.gateway.handle_request("/api/v1/entitlement", api_token=elite_token)
        self.assertEqual(res_elite.status_code, 200)
        self.assertEqual(res_elite.data["tier"], "lauburu_elite")
        self.assertIn("priority_metal_gpu", res_elite.data["features"])

    def test_shopify_webhook_verification_and_processing(self):
        """Tests webhook HMAC-SHA256 signature verification and payload processing."""
        import base64
        import hashlib
        import hmac

        secret = "test_webhook_secret_2026"
        body = b'{"id": "cust_999", "tags": "lauburu_pro, athlete"}'
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
        hmac_sig = base64.b64encode(digest).decode("utf-8")

        # 1. Valid signature
        self.assertTrue(self.gateway.verify_shopify_webhook(body, hmac_sig, webhook_secret=secret))

        # 2. Invalid signature
        self.assertFalse(self.gateway.verify_shopify_webhook(body, "invalid_sig", webhook_secret=secret))

        # 3. Process webhook event
        payload = {"id": "cust_999", "tags": "lauburu_pro, athlete"}
        result = self.gateway.process_webhook_event("customers/update", payload)
        self.assertTrue(result["processed"])
        self.assertEqual(result["resolved_tier"], "lauburu_pro")
        self.assertTrue(result["new_api_key"].startswith("lb_lauburu_pro_"))

    def test_graphql_query_sanitizer(self):
        """Tests GraphQL query depth limiter and injection defense."""
        # Valid shallow query
        valid_query = "{ products(first: 5) { edges { node { id title } } } }"
        ok, err = self.gateway.sanitize_graphql_query(valid_query, max_depth=5)
        self.assertTrue(ok)
        self.assertIsNone(err)

        # Deeply nested malicious query
        nested_query = "{ a { b { c { d { e { f { g { h { id } } } } } } } } }"
        ok_deep, err_deep = self.gateway.sanitize_graphql_query(nested_query, max_depth=5)
        self.assertFalse(ok_deep)
        self.assertIn("depth limit exceeded", err_deep)

        # Unbalanced braces
        unbalanced = "{ products { edges { node { id }"
        ok_unb, err_unb = self.gateway.sanitize_graphql_query(unbalanced)
        self.assertFalse(ok_unb)
        self.assertIn("Unbalanced braces", err_unb)


if __name__ == "__main__":
    unittest.main()

