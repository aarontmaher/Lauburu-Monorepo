#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Test Suite: Google Cloud $1,400 Credit Escalation, Local AI Multi-Model Training,
Shopify Webhook Callback Listener, and SeaweedFS Minidump Offloader
================================================================================
"""

import os
import sys
import json
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
BASE_URL = "http://localhost:4000"


class TestGcpEscalationAndShopifyWebhook(unittest.TestCase):
    def test_01_gcp_credit_status(self):
        """Test GCP credit governor endpoint returns $1,400 AUD pool and circuit breaker."""
        url = f"{BASE_URL}/api/v1/cloud/gcp/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["billing_account_id"], "01823E-7DAC2A-D66F09")
            self.assertEqual(data["project_id"], "lauburu-play-deploy")
            self.assertEqual(data["total_grant_aud"], 1400.00)
            self.assertGreaterEqual(data["remaining_reserve_aud"], 0.0)
            self.assertIn("shutdown -h +45", data["circuit_breaker"])

    def test_02_gcp_burst_preview(self):
        """Test Spot GPU micro-burst preview calculation and tranche cap enforcement."""
        url = f"{BASE_URL}/api/v1/cloud/gcp/burst/preview"
        payload = json.dumps({"batch_id": "BATCH_01_EDGE_SLMS", "projected_spend_aud": 14.00}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["batch_id"], "BATCH_01_EDGE_SLMS")
            self.assertGreater(data["estimated_gpu_hours"], 0.0)
            self.assertIn("NVIDIA L4", data["instance_type"])
            self.assertTrue(data["safe_to_dispatch"])

    def test_03_gcp_lakehouse_dataset_export(self):
        """Test Lakehouse LoRA dataset export formatted for Vertex AI batch distillation."""
        url = f"{BASE_URL}/api/v1/cloud/gcp/dataset/export"
        payload = json.dumps({"limit": 5}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertGreater(data["pairs_exported"], 0)
            self.assertEqual(data["format"], "Vertex AI JSONL Multi-Turn")
            self.assertTrue(os.path.exists(data["export_file"]))

    def test_04_shopify_webhook_handling(self):
        """Test Shopify Webhook endpoint handling an orders/paid upgrade event."""
        url = f"{BASE_URL}/api/v1/commerce/webhook/shopify"
        payload = json.dumps({
            "topic": "orders/paid",
            "line_items": [
                {"title": "Athlete Pro Monthly Access", "price": "29.00"}
            ]
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Topic": "orders/paid"
            }
        )
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["active_tier"], "athlete_pro")

        # Restore Sovereign Gym Master default
        override_url = f"{BASE_URL}/api/v1/commerce/membership/override"
        override_payload = json.dumps({"tier_id": "mesh_gym_master"}).encode("utf-8")
        req2 = urllib.request.Request(override_url, data=override_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2, timeout=3.0) as res2:
            self.assertEqual(res2.status, 200)

    def test_05_seaweedfs_asan_offload(self):
        """Test offloading AddressSanitizer crash minidump to SeaweedFS DFS."""
        url = f"{BASE_URL}/api/v1/storage/seaweed/offload_asan"
        payload = json.dumps({
            "crash_id": "asan_unit_test_01",
            "error_type": "global-buffer-overflow",
            "crash_log": "ERROR: AddressSanitizer: global-buffer-overflow on address 0x1000",
            "source_file": "crypto_mesh.c"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["crash_id"], "asan_unit_test_01")
            self.assertTrue(data["dfs_mounted"])
            self.assertTrue(os.path.exists(data["dump_path"]))

    def test_06_local_ai_training_telemetry(self):
        """Test local AI training telemetry endpoint returns live daemon status."""
        url = f"{BASE_URL}/api/v1/training/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertGreater(data["running_daemons"], 0)
            self.assertGreater(data["lakehouse"]["harvested_pairs_count"], 0)
            self.assertGreater(len(data["models_matrix"]), 0)


if __name__ == "__main__":
    unittest.main()
