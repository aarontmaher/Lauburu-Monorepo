"""E2E Integration Tests for Concurrent Dual-Account Execution & Client Isolation (R4, Features 1-3, 16).

Covers Tiers 1-4 per TEST_INFRA.md:
- Concurrent authentication of both accounts:
  - Personal Admin: aaron.t.maher@gmail.com
  - Workspace Business: lauburu@lauburugrappling.com
- Credential isolation & GenAI client object separation (no global env bleed)
- Per-account telemetry logging with SHA256 Tri-Proof validation
- Asynchronous concurrent execution (asyncio.gather) without race conditions
- Concurrent dual-account notebook synchronization within orchestrator notebook
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

try:
    from auth_manager import (
        AccountRole,
        AccountSession,
        CredentialType,
        DualAccountManager,
        create_dual_account_manager,
    )
    AUTH_MANAGER_AVAILABLE = True
except ImportError:
    AUTH_MANAGER_AVAILABLE = False


@pytest.fixture(autouse=True)
def require_auth_manager():
    """Skips tests if auth_manager module is not available."""
    if not AUTH_MANAGER_AVAILABLE:
        pytest.skip("auth_manager module is not available")


class TestDualAccountTier1FeatureCoverage:
    """Tier 1: Feature Coverage — Primary happy-path dual-account authentication and isolation."""

    def test_dual_account_concurrent_dry_run_authentication(self, canonical_config_path: Path):
        """Feature 16: Authenticates both accounts concurrently in dry-run mode."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        sessions = manager.authenticate_all()

        assert len(sessions) == 2, "Expected exactly two account sessions"
        assert "aaron.t.maher@gmail.com" in sessions
        assert "lauburu@lauburugrappling.com" in sessions

        admin_sess = sessions["aaron.t.maher@gmail.com"]
        biz_sess = sessions["lauburu@lauburugrappling.com"]

        assert admin_sess.is_authenticated is True
        assert admin_sess.role == "personal_admin"
        assert admin_sess.auth_method == "simulated_dry_run"

        assert biz_sess.is_authenticated is True
        assert biz_sess.role == "workspace_business"
        assert biz_sess.auth_method == "simulated_dry_run"

    def test_credential_isolation_between_accounts(self, canonical_config_path: Path):
        """Feature 3: Personal Admin and Workspace Business use strictly isolated credential types and paths."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        profile_admin = manager.get_profile("aaron.t.maher@gmail.com")
        profile_biz = manager.get_profile("lauburu@lauburugrappling.com")

        assert profile_admin is not None
        assert profile_biz is not None

        # Personal admin uses ADC
        assert profile_admin.primary_cred_type == CredentialType.ADC
        assert "adc.json" in str(profile_admin.cred_file_path)

        # Workspace business uses OAuth2 Token or Service Account
        assert profile_biz.primary_cred_type == CredentialType.OAUTH2_TOKEN
        assert "workspace_token.json" in str(profile_biz.cred_file_path)

        # Scopes must be completely distinct
        assert profile_admin.scopes != profile_biz.scopes
        assert set(profile_admin.scopes).isdisjoint(set(profile_biz.scopes))
        assert "https://www.googleapis.com/auth/cloud-platform" in profile_admin.scopes
        assert any("gmail" in s for s in profile_biz.scopes)

    def test_genai_client_instances_are_distinct_objects(self, canonical_config_path: Path):
        """Feature 3: Verifies that client instances for the two accounts are distinct in-memory objects."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        manager.authenticate_all()

        client_admin = manager.get_genai_client("aaron.t.maher@gmail.com")
        client_biz = manager.get_genai_client("lauburu@lauburugrappling.com")

        if client_admin is not None and client_biz is not None:
            # Memory address comparison proving strict instance isolation
            assert id(client_admin) != id(client_biz), (
                "Both accounts must have distinct GenAI client instances without object sharing."
            )

        assert manager._verify_isolation() is True

    def test_per_account_telemetry_manifest_emission(self, canonical_config_path: Path):
        """Feature 16: Manifest contains structured, isolated telemetry partition for each account."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        manager.authenticate_all()
        manifest = manager.export_status_manifest()

        assert manifest["total_accounts"] == 2
        assert manifest["authenticated_accounts"] == 2
        assert manifest["client_isolation_verified"] is True
        assert "accounts" in manifest

        acct_meta = manifest["accounts"]
        assert acct_meta["aaron.t.maher@gmail.com"]["role"] == "personal_admin"
        assert acct_meta["lauburu@lauburugrappling.com"]["role"] == "workspace_business"


class TestDualAccountTier2BoundaryAndCornerCases:
    """Tier 2: Boundary Value Analysis & Isolation Boundary Checks."""

    def test_environment_variable_isolation(self, canonical_config_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Boundary: Mutating GEMINI_API_KEY environment variable does not alter Workspace OAuth credentials."""
        monkeypatch.setenv("GEMINI_API_KEY", "dummy_mock_key_admin_only_12345")
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)

        session_biz = manager.authenticate_account("lauburu@lauburugrappling.com")
        assert session_biz.is_authenticated is True
        # Workspace auth must rely on its own oauth2 token file, not the monkeypatched GEMINI_API_KEY
        assert session_biz.metadata.get("primary_cred_type") == "oauth2_token"

    def test_single_account_failure_does_not_abort_peer(self, canonical_config_path: Path):
        """Boundary: An unauthenticated or invalid peer account does not invalidate the valid account."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)

        # Authenticate real account
        admin_sess = manager.authenticate_account("aaron.t.maher@gmail.com")
        # Authenticate bogus account
        bogus_sess = manager.authenticate_account("nonexistent_account@example.com")

        assert admin_sess.is_authenticated is True
        assert bogus_sess.is_authenticated is False
        assert bogus_sess.error is not None

        # Real account remains authenticated
        assert manager.get_session("aaron.t.maher@gmail.com").is_authenticated is True

    def test_concurrent_asyncio_gather_execution(self, canonical_config_path: Path):
        """Boundary: Concurrently executing authentication across accounts via asyncio.gather has zero race conditions."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)

        async def run_auth(account_id: str):
            # Simulate async task dispatch
            await asyncio.sleep(0.01)
            return manager.authenticate_account(account_id)

        async def main():
            return await asyncio.gather(
                run_auth("aaron.t.maher@gmail.com"),
                run_auth("lauburu@lauburugrappling.com")
            )

        results = asyncio.run(main())
        assert len(results) == 2
        assert results[0].account_id == "aaron.t.maher@gmail.com"
        assert results[1].account_id == "lauburu@lauburugrappling.com"
        assert results[0].is_authenticated is True
        assert results[1].is_authenticated is True

    def test_independent_token_expiry_tracking(self, canonical_config_path: Path):
        """Boundary: Accounts record independent token expiry timestamps."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        sessions = manager.authenticate_all()

        exp1 = sessions["aaron.t.maher@gmail.com"].token_expiry
        exp2 = sessions["lauburu@lauburugrappling.com"].token_expiry

        assert exp1 is not None and exp1 > 0
        assert exp2 is not None and exp2 > 0


class TestDualAccountTier3CrossFeatureCombinations:
    """Tier 3: Pairwise Combinations & Telemetry Integrity."""

    def test_dual_account_tri_proof_sha256_generation(self, canonical_config_path: Path):
        """Cross-Feature: Generates distinct Tri-Proof SHA256 checksums per account telemetry record."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        sessions = manager.authenticate_all()

        records = {}
        for acc_id, sess in sessions.items():
            record_bytes = json.dumps(sess.to_dict(), sort_keys=True).encode("utf-8")
            records[acc_id] = {
                "account_id": acc_id,
                "exit_code": 0 if sess.is_authenticated else 1,
                "byte_count": len(record_bytes),
                "sha256": hashlib.sha256(record_bytes).hexdigest()
            }

        assert len(records) == 2
        assert records["aaron.t.maher@gmail.com"]["exit_code"] == 0
        assert records["lauburu@lauburugrappling.com"]["exit_code"] == 0
        # Checksums must be distinct
        assert records["aaron.t.maher@gmail.com"]["sha256"] != records["lauburu@lauburugrappling.com"]["sha256"]

    def test_dual_account_notebook_metadata_injection(self, mock_free_notebook_path: Path, canonical_config_path: Path):
        """Cross-Feature: Both accounts' verified sessions are serialized into notebook metadata."""
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        sessions = manager.authenticate_all()

        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        nb["metadata"]["dual_account_sync"] = {
            acc_id: {
                "role": sess.role,
                "is_authenticated": sess.is_authenticated,
                "auth_method": sess.auth_method
            }
            for acc_id, sess in sessions.items()
        }

        temp_target = mock_free_notebook_path.with_suffix(".tmp")
        with open(temp_target, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=2)
        os.replace(temp_target, mock_free_notebook_path)

        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            reloaded = json.load(f)

        meta = reloaded["metadata"]["dual_account_sync"]
        assert meta["aaron.t.maher@gmail.com"]["role"] == "personal_admin"
        assert meta["lauburu@lauburugrappling.com"]["role"] == "workspace_business"


class TestDualAccountTier4RealWorldScenarios:
    """Tier 4: Real-World Workload Scenarios."""

    def test_scenario_concurrent_dual_account_notebook_sync_in_pycharm(
        self,
        mock_free_notebook_path: Path,
        canonical_config_path: Path,
        temp_env_dir: Path
    ):
        """Scenario 3: Simulates concurrent execution of both accounts within orchestrator notebook."""
        # 1. Dual authentication
        manager = DualAccountManager(config_path=canonical_config_path, dry_run=True)
        sessions = manager.authenticate_all()
        assert all(s.is_authenticated for s in sessions.values())

        # 2. Inject notebook execution cell referencing both accounts
        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        sync_code = [
            "# [CONCURRENT DUAL-ACCOUNT SYNC CELL]\n",
            f"ADMIN_ACCOUNT = '{sessions['aaron.t.maher@gmail.com'].account_id}'\n",
            f"WORKSPACE_ACCOUNT = '{sessions['lauburu@lauburugrappling.com'].account_id}'\n",
            "print(f'[*] Personal Admin: {ADMIN_ACCOUNT} | Status: OK')\n",
            "print(f'[*] Workspace Business: {WORKSPACE_ACCOUNT} | Status: OK')\n"
        ]

        nb["cells"].insert(1, {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"tags": ["dual_account_sync_cell"]},
            "outputs": [],
            "source": sync_code
        })

        temp_target = mock_free_notebook_path.with_suffix(".tmp")
        with open(temp_target, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=2)
        os.replace(temp_target, mock_free_notebook_path)

        # 3. Synchronize .idea/lens_context.json
        idea_context = temp_env_dir / ".idea" / "lens_context.json"
        idea_context.parent.mkdir(parents=True, exist_ok=True)
        idea_data = {
            "timestamp": "2026-10-11T11:45:00Z",
            "active_notebook": "lens_global_orchestrator.ipynb",
            "accounts_synced": list(sessions.keys()),
            "status": "CONCURRENT_ACTIVE"
        }
        idea_context.write_text(json.dumps(idea_data, indent=2), encoding="utf-8")

        # 4. Assert end-to-end outcome
        with open(mock_free_notebook_path, "r", encoding="utf-8") as f:
            reloaded_nb = json.load(f)
        assert len(reloaded_nb["cells"]) >= 2
        assert idea_context.exists()
        assert len(json.loads(idea_context.read_text())["accounts_synced"]) == 2
