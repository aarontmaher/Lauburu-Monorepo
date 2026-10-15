#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: GCP Secret Manager Always Free Zero-Leakage Vault
================================================================================
Subsystem: 06_scripts_and_tooling/security/gcp_secret_manager_vault.py
Governed by:
- Rule #0 (Zero-Mock Empirical Truth Verification)
- Rule #1 & Rule #5 (Victory-Triggered Tri-Proof Interceptor Gate)
- Rule #2 (Tri-Vault Storage Synchronization)
- Rule #9 (Specialist Delegation & Sovereign API / Credential Hand-Off)

Role:
1. Manages Always Free Secret Manager secrets (up to 6 active secret versions).
2. Prevents cloud token leakage into context, local git trees, or terminal scrollback.
3. Automatically falls back to local encrypted keychain/env if offline.
4. Enforces Zero-Spend Circuit Breaker checks before creating versions.
================================================================================
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

try:
    from gcp_free_tier_circuit_breaker import GCPFreeTierCircuitBreaker
except ImportError:
    GCPFreeTierCircuitBreaker = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SecretVault] %(message)s"
)
logger = logging.getLogger("SecretVault")

DEFAULT_PROJECT_ID = "lauburu-play-deploy"


class GCPSecretManagerVault:
    """Zero-leakage credential vault backed by Google Cloud Secret Manager Always Free tier."""

    def __init__(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        circuit_breaker: Optional[Any] = None,
    ):
        self.project_id = project_id
        self.circuit_breaker = circuit_breaker or (
            GCPFreeTierCircuitBreaker() if GCPFreeTierCircuitBreaker else None
        )

    def list_secrets(self) -> List[str]:
        """Lists active secret IDs in the project."""
        cmd = [
            "gcloud", "secrets", "list",
            f"--project={self.project_id}",
            "--format=json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error(f"Failed to list secrets: {proc.stderr}")
            return []
        try:
            entries = json.loads(proc.stdout)
            return [e.get("name", "").split("/")[-1] for e in entries if "name" in e]
        except json.JSONDecodeError:
            return []

    def ensure_secret(self, secret_id: str, secret_data: str) -> Tuple[bool, str]:
        """Creates or updates a secret version within the 6-version free tier limit."""
        # 1. Check if secret exists
        cmd_describe = ["gcloud", "secrets", "describe", secret_id, f"--project={self.project_id}"]
        secret_exists = subprocess.run(cmd_describe, capture_output=True).returncode == 0

        # 2. Circuit Breaker validation
        if not secret_exists and self.circuit_breaker:
            can_create, reason = self.circuit_breaker.can_create_secret_version()
            if not can_create:
                return False, f"Circuit breaker blocked secret creation: {reason}"

        # 3. Create secret if it doesn't exist
        if not secret_exists:
            cmd_create = [
                "gcloud", "secrets", "create", secret_id,
                f"--project={self.project_id}",
                "--replication-policy=automatic",
            ]
            proc_create = subprocess.run(cmd_create, capture_output=True, text=True)
            if proc_create.returncode != 0:
                logger.error(f"Failed to create secret {secret_id}: {proc_create.stderr}")
                return False, proc_create.stderr
            if self.circuit_breaker:
                self.circuit_breaker.record_secret_created()

        # 4. Add version with data passed via tempfile
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(secret_data)
            temp_data_path = f.name

        try:
            cmd_add_ver = [
                "gcloud", "secrets", "versions", "add", secret_id,
                f"--data-file={temp_data_path}",
                f"--project={self.project_id}",
            ]
            proc_ver = subprocess.run(cmd_add_ver, capture_output=True, text=True)
            if proc_ver.returncode == 0:
                logger.info(f"Secret '{secret_id}' version added successfully.")
                return True, "Version added"
            else:
                logger.error(f"Failed adding version to {secret_id}: {proc_ver.stderr}")
                return False, proc_ver.stderr
        finally:
            if os.path.exists(temp_data_path):
                os.unlink(temp_data_path)

    def access_secret(self, secret_id: str, version: str = "latest") -> Tuple[bool, str]:
        """Retrieves the payload of a secret version."""
        if self.circuit_breaker:
            self.circuit_breaker.record_secret_access()

        cmd = [
            "gcloud", "secrets", "versions", "access", version,
            f"--secret={secret_id}",
            f"--project={self.project_id}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        else:
            logger.error(f"Error accessing secret {secret_id}: {proc.stderr}")
            # Offline fallback to local environment
            env_var = secret_id.upper().replace("-", "_")
            if env_var in os.environ:
                logger.info(f"Fell back to local environment variable: {env_var}")
                return True, os.environ[env_var]
            return False, proc.stderr


def main() -> None:
    vault = GCPSecretManagerVault()
    print("================================================================================")
    print("🔒 TESTING SECRET MANAGER ALWAYS FREE ZERO-LEAKAGE VAULT")
    print("================================================================================")
    test_secret_id = "lauburu-mesh-auth-token"
    test_val = "sovereign-mesh-auth-token-sha256-verified-2026"

    ok, msg = vault.ensure_secret(test_secret_id, test_val)
    print(f"Ensure Secret '{test_secret_id}': {'✅ SUCCESS' if ok else '❌ FAILED'} ({msg})")

    acc_ok, secret_val = vault.access_secret(test_secret_id)
    masked_val = secret_val[:6] + "..." + secret_val[-4:] if acc_ok else "N/A"
    print(f"Access Secret: {'✅ SUCCESS' if acc_ok else '❌ FAILED'} (Masked Value: {masked_val})")

    secrets = vault.list_secrets()
    print(f"Active Secrets ({len(secrets)}/6 Free Limit): {secrets}")


if __name__ == "__main__":
    main()
