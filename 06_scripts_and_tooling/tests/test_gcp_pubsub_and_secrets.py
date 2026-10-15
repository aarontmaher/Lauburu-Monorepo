#!/usr/bin/env python3
"""
Unit tests for GCP Always Free Pub/Sub Mesh Bus and Secret Manager Vault
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/network"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/security"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

from gcp_pubsub_mesh_bus import GCPPubSubMeshBus
from gcp_secret_manager_vault import GCPSecretManagerVault


class TestGCPPubSubAndSecrets(unittest.TestCase):
    def setUp(self):
        self.mock_breaker = MagicMock()
        self.mock_breaker.can_publish_pubsub.return_value = (True, "OK")
        self.mock_breaker.can_create_secret_version.return_value = (True, "OK")

        self.bus = GCPPubSubMeshBus(
            project_id="test-project",
            circuit_breaker=self.mock_breaker,
        )
        self.vault = GCPSecretManagerVault(
            project_id="test-project",
            circuit_breaker=self.mock_breaker,
        )

    @patch("subprocess.run")
    def test_pubsub_publish_circuit_breaker_blocking(self, mock_sub):
        self.mock_breaker.can_publish_pubsub.return_value = (False, "PubSub monthly quota exceeded")
        ok, msg = self.bus.publish_event("TEST_EVENT", {"key": "val"})
        self.assertFalse(ok)
        self.assertIn("Circuit breaker blocked", msg)
        mock_sub.assert_not_called()

    @patch("subprocess.run")
    def test_pubsub_publish_success(self, mock_sub):
        mock_sub.return_value = MagicMock(returncode=0, stdout="messageIds:\n- 123456789\n", stderr="")
        ok, msg_id = self.bus.publish_event("NODE_ALERT", {"temp_c": 75.2})
        self.assertTrue(ok)
        self.assertEqual(msg_id, "123456789")
        self.mock_breaker.record_pubsub_publish.assert_called_once()

    @patch("subprocess.run")
    def test_secret_vault_create_blocking(self, mock_sub):
        # Mock describe failing (secret does not exist)
        mock_sub.return_value = MagicMock(returncode=1, stdout="", stderr="Not found")
        # Circuit breaker blocks
        self.mock_breaker.can_create_secret_version.return_value = (False, "Max versions reached")

        ok, msg = self.vault.ensure_secret("test-secret", "secret-value")
        self.assertFalse(ok)
        self.assertIn("Circuit breaker blocked", msg)

    @patch("subprocess.run")
    def test_secret_vault_offline_fallback(self, mock_sub):
        # Mock gcloud failing
        mock_sub.return_value = MagicMock(returncode=1, stdout="", stderr="Network unreachable")
        os.environ["OFFLINE_SECRET_KEY"] = "sovereign-offline-token"

        ok, val = self.vault.access_secret("offline-secret-key")
        self.assertTrue(ok)
        self.assertEqual(val, "sovereign-offline-token")


if __name__ == "__main__":
    unittest.main()
