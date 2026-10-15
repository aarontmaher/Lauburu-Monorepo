#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Test Suite: Front Dashboard, SeaweedFS IDE Bridge & Shopify Membership
================================================================================
Tests:
1. SeaweedFS Distributed Storage status & mount point verification.
2. 7-Layer Network & Device Analysis for Compute Payment.
3. Shopify Storefront GraphQL Membership Gating & Tiers.
4. Port 4000 Root Front Dashboard HTML delivery & Chat inference endpoint.
================================================================================
"""

import unittest
import requests
import json

BASE_URL = "http://localhost:4000"

class TestFrontDashboardAndSeaweedIDE(unittest.TestCase):
    def test_01_backend_health(self):
        res = requests.get(f"{BASE_URL}/api/v1/health", timeout=2.0)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertTrue(data["storage_healthy"])

    def test_02_seaweedfs_status(self):
        res = requests.get(f"{BASE_URL}/api/v1/storage/seaweed/status", timeout=2.0)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["mount_point"], "/Users/aaron/DFS_UNIFIED")
        self.assertTrue(data["is_mounted"])
        self.assertEqual(data["master"]["port"], 9333)

    def test_03_compute_payment_analysis(self):
        res = requests.get(f"{BASE_URL}/api/v1/compute/analysis", timeout=3.0)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("host_sanctuary", data)
        self.assertGreater(data["host_sanctuary"]["ram_free_gb"], 2.0)
        self.assertGreater(data["pooled_mesh_vram_gb"], 15.0)
        self.assertEqual(len(data["nodes"]), 7)
        self.assertIn("compute_payment_ledger", data)
        self.assertIn("net_balance_aud", data["compute_payment_ledger"])

    def test_04_shopify_membership_service(self):
        # 1. Check status
        res = requests.get(f"{BASE_URL}/api/v1/commerce/membership/status", timeout=2.0)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tier_id", data)
        self.assertIn("allowed_modules", data)
        self.assertIn("price_aud_monthly", data)

        # 2. Check tiers catalog
        res_tiers = requests.get(f"{BASE_URL}/api/v1/commerce/membership/tiers", timeout=2.0)
        self.assertEqual(res_tiers.status_code, 200)
        tiers_data = res_tiers.json()
        self.assertEqual(len(tiers_data["tiers"]), 4)

        # 3. Check checkout cart creation
        res_cart = requests.post(f"{BASE_URL}/api/v1/commerce/membership/checkout", json={"tier_id": "athlete_pro"}, timeout=2.0)
        self.assertEqual(res_cart.status_code, 200)
        cart_data = res_cart.json()
        self.assertIn("checkout_url", cart_data)
        self.assertEqual(cart_data["price_aud"], 29.0)

    def test_05_front_dashboard_html_delivery(self):
        res = requests.get(f"{BASE_URL}/", headers={"Accept": "text/html"}, timeout=2.0)
        self.assertEqual(res.status_code, 200)
        self.assertIn("<!DOCTYPE html>", res.text)
        self.assertIn("Lauburu Mesh Dashboard", res.text)

    def test_06_edge_chat_inference(self):
        payload = {
            "message": "Verify SeaweedFS DFS mount and check compute credit balance",
            "model": "qwen_38_max",
            "max_tokens": 64
        }
        res = requests.post(f"{BASE_URL}/api/v1/chat", json=payload, timeout=35.0)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("response", data)
        self.assertGreater(len(data["response"]), 10)


if __name__ == "__main__":
    unittest.main()
