"""Unit and Integration Tests for Dual-Account Authentication & Client Isolation Engine.

Verifies:
1. Personal Admin (aaron.t.maher@gmail.com) ADC token loading, refresh, and API key fallback.
2. Workspace Business (lauburu@lauburugrappling.com) OAuth2 token loading, refresh, and Service Account DWD fallback.
3. Client isolation: Distinct google.genai.Client instances with zero global environment bleed.
4. Dry-run mode: On-disk validation and simulation without external network mutation.
5. Edge cases: Missing files, malformed JSON, inactive profiles, expired tokens, and error handling.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from google.oauth2 import service_account

import pytest

from auth_manager import (
    AccountProfile,
    AccountRole,
    AccountSession,
    CredentialType,
    DualAccountManager,
    create_dual_account_manager,
)


class TestAccountModels:
    """Tests data structures and schema validation."""

    def test_account_role_enum_values(self):
        assert AccountRole.PERSONAL_ADMIN.value == "personal_admin"
        assert AccountRole.WORKSPACE_BUSINESS.value == "workspace_business"

    def test_credential_type_enum_values(self):
        assert CredentialType.API_KEY.value == "api_key"
        assert CredentialType.OAUTH2_TOKEN.value == "oauth2_token"
        assert CredentialType.SERVICE_ACCOUNT_DWD.value == "service_account_dwd"
        assert CredentialType.ADC.value == "adc"

    def test_account_profile_from_dict(self):
        raw = {
            "account_id": "test@example.com",
            "role": "personal_admin",
            "primary_cred_type": "adc",
            "cred_file_path": "~/.config/test.json",
            "api_key_env_var": "TEST_KEY",
            "fallback_cred_type": "api_key",
            "scopes": ["scope1", "scope2"],
            "rate_limit_rpm": 20,
            "rate_limit_rpd": 2000,
            "is_active": True,
            "metadata": {"env": "test"}
        }
        profile = AccountProfile.from_dict(raw)
        assert profile.account_id == "test@example.com"
        assert profile.role == AccountRole.PERSONAL_ADMIN
        assert profile.primary_cred_type == CredentialType.ADC
        assert profile.fallback_cred_type == CredentialType.API_KEY
        assert profile.rate_limit_rpm == 20
        assert profile.rate_limit_rpd == 2000
        assert profile.is_active is True
        assert len(profile.scopes) == 2

    def test_account_session_expiry_property(self):
        now = time.time()
        # Non-expired session
        session_valid = AccountSession(
            account_id="valid@example.com",
            role="personal_admin",
            is_authenticated=True,
            auth_method="simulated_dry_run",
            token_expiry=now + 3600.0
        )
        assert session_valid.is_expired is False

        # Expired session
        session_expired = AccountSession(
            account_id="expired@example.com",
            role="personal_admin",
            is_authenticated=True,
            auth_method="simulated_dry_run",
            token_expiry=now - 60.0
        )
        assert session_expired.is_expired is True

        # Unauthenticated session is always treated as expired
        session_unauth = AccountSession(
            account_id="unauth@example.com",
            role="personal_admin",
            is_authenticated=False,
            auth_method="none",
            token_expiry=now + 3600.0
        )
        assert session_unauth.is_expired is True

    def test_account_session_to_dict_redaction(self):
        session = AccountSession(
            account_id="test@example.com",
            role="workspace_business",
            is_authenticated=True,
            auth_method="oauth2",
            token_expiry=1791720000.0,
            client=object(),
            credentials=object(),
            last_refreshed=1791719000.0,
            metadata={"domain": "lauburugrappling.com"}
        )
        d = session.to_dict()
        assert d["account_id"] == "test@example.com"
        assert d["role"] == "workspace_business"
        assert d["is_authenticated"] is True
        assert d["has_client"] is True
        assert "token" not in d  # No secret credentials leaked
        assert "refresh_token" not in d
        assert "client_secret" not in d


class TestCredentialValidation:
    """Tests file inspection and schema validation on disk."""

    def test_validate_adc_file_valid(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "client_id": "mock_id",
                "client_secret": "mock_secret",
                "refresh_token": "mock_refresh",
                "type": "authorized_user"
            }, f)
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.ADC)
            assert valid is True
            assert err is None
        finally:
            os.remove(temp_path)

    def test_validate_adc_file_missing(self):
        manager = DualAccountManager(dry_run=True)
        valid, err = manager.validate_credentials_file("/non/existent/path/adc.json", CredentialType.ADC)
        assert valid is False
        assert "File not found" in err

    def test_validate_adc_file_corrupt_json(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("NOT_VALID_JSON{:::}")
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.ADC)
            assert valid is False
            assert "Invalid JSON" in err
        finally:
            os.remove(temp_path)

    def test_validate_adc_file_invalid_schema(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"foo": "bar"}, f)
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.ADC)
            assert valid is False
            assert "Missing ADC required fields" in err
        finally:
            os.remove(temp_path)

    def test_validate_oauth2_file_valid(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "token": "valid_access_token",
                "refresh_token": "valid_refresh_token",
                "client_id": "ws_client"
            }, f)
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.OAUTH2_TOKEN)
            assert valid is True
            assert err is None
        finally:
            os.remove(temp_path)

    def test_validate_oauth2_file_missing_tokens(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"client_id": "ws_client"}, f)
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.OAUTH2_TOKEN)
            assert valid is False
            assert "missing both 'token' and 'refresh_token'" in err
        finally:
            os.remove(temp_path)

    def test_validate_service_account_file_valid(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "type": "service_account",
                "project_id": "test-project",
                "private_key_id": "12345",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n",
                "client_email": "sa@test-project.iam.gserviceaccount.com"
            }, f)
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.SERVICE_ACCOUNT_DWD)
            assert valid is True
            assert err is None
        finally:
            os.remove(temp_path)

    def test_validate_service_account_file_invalid_type(self):
        manager = DualAccountManager(dry_run=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"type": "authorized_user", "private_key": "some_key"}, f)
            temp_path = f.name

        try:
            valid, err = manager.validate_credentials_file(temp_path, CredentialType.SERVICE_ACCOUNT_DWD)
            assert valid is False
            assert "Invalid service account schema" in err
        finally:
            os.remove(temp_path)


class TestPersonalAdminAuth:
    """Tests authentication for aaron.t.maher@gmail.com."""

    def test_personal_admin_dry_run_auth(self):
        manager = DualAccountManager(dry_run=True)
        session = manager.authenticate_account("aaron.t.maher@gmail.com")

        assert session.account_id == "aaron.t.maher@gmail.com"
        assert session.role == "personal_admin"
        assert session.is_authenticated is True
        assert session.auth_method == "simulated_dry_run"
        assert session.token_expiry is not None
        assert session.token_expiry > time.time()
        assert session.is_expired is False
        assert session.client is not None
        assert session.error is None
        assert session.metadata.get("dry_run") is True

    def test_personal_admin_live_auth(self):
        manager = DualAccountManager(dry_run=False)
        session = manager.authenticate_account("aaron.t.maher@gmail.com")

        assert session.account_id == "aaron.t.maher@gmail.com"
        assert session.role == "personal_admin"
        assert session.is_authenticated is True
        assert session.auth_method in ("adc", "api_key")
        assert session.client is not None
        assert session.error is None

    def test_personal_admin_fallback_to_api_key(self, monkeypatch):
        # Point primary cred to non-existent path, set GEMINI_API_KEY
        test_config = {
            "accounts": {
                "aaron.t.maher@gmail.com": {
                    "account_id": "aaron.t.maher@gmail.com",
                    "role": "personal_admin",
                    "primary_cred_type": "adc",
                    "cred_file_path": "/non/existent/path/adc.json",
                    "api_key_env_var": "MOCK_GEMINI_KEY",
                    "fallback_cred_type": "api_key",
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
                }
            }
        }
        monkeypatch.setenv("MOCK_GEMINI_KEY", "test-api-key-12345")
        manager = DualAccountManager(config_data=test_config, dry_run=False)
        session = manager.authenticate_account("aaron.t.maher@gmail.com")

        assert session.is_authenticated is True
        assert session.auth_method == "api_key"
        assert session.client is not None
        assert session.error is None

    def test_personal_admin_refresh_credentials(self):
        manager = DualAccountManager(dry_run=False)
        manager.authenticate_account("aaron.t.maher@gmail.com")
        refreshed = manager.refresh_credentials("aaron.t.maher@gmail.com")
        assert refreshed is True
        session = manager.get_session("aaron.t.maher@gmail.com")
        assert session is not None
        assert session.is_authenticated is True

    def test_personal_admin_missing_all_creds_graceful_failure(self, monkeypatch):
        test_config = {
            "accounts": {
                "aaron.t.maher@gmail.com": {
                    "account_id": "aaron.t.maher@gmail.com",
                    "role": "personal_admin",
                    "primary_cred_type": "adc",
                    "cred_file_path": "/non/existent/path/adc.json",
                    "api_key_env_var": "NON_EXISTENT_VAR",
                    "fallback_cred_type": "api_key"
                }
            }
        }
        monkeypatch.delenv("NON_EXISTENT_VAR", raising=False)
        manager = DualAccountManager(config_data=test_config, dry_run=False)
        session = manager.authenticate_account("aaron.t.maher@gmail.com")

        assert session.is_authenticated is False
        assert session.client is None
        assert session.error is not None


class TestWorkspaceBusinessAuth:
    """Tests authentication for lauburu@lauburugrappling.com."""

    def test_workspace_business_dry_run_auth(self):
        manager = DualAccountManager(dry_run=True)
        session = manager.authenticate_account("lauburu@lauburugrappling.com")

        assert session.account_id == "lauburu@lauburugrappling.com"
        assert session.role == "workspace_business"
        assert session.is_authenticated is True
        assert session.auth_method == "simulated_dry_run"
        assert session.token_expiry is not None
        assert session.token_expiry > time.time()
        assert session.is_expired is False
        assert session.client is not None
        assert session.error is None

    def test_workspace_business_live_auth(self):
        manager = DualAccountManager(dry_run=False)
        session = manager.authenticate_account("lauburu@lauburugrappling.com")

        assert session.account_id == "lauburu@lauburugrappling.com"
        assert session.role == "workspace_business"
        assert session.is_authenticated is True
        assert session.auth_method in ("oauth2", "service_account_dwd")
        assert session.client is not None
        assert session.error is None

    def test_workspace_business_service_account_fallback(self):
        # Configure primary to point to missing file, fallback to service_account.json
        # When service account DWD credentials refresh succeeds, authenticates as service_account_dwd
        sa_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/service_account.json"
        test_config = {
            "accounts": {
                "lauburu@lauburugrappling.com": {
                    "account_id": "lauburu@lauburugrappling.com",
                    "role": "workspace_business",
                    "primary_cred_type": "oauth2_token",
                    "cred_file_path": "/non/existent/workspace_token.json",
                    "fallback_cred_type": "service_account_dwd",
                    "fallback_cred_file_path": sa_path,
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
                }
            }
        }

        def mock_sa_refresh(self, req):
            self.token = "mock-valid-sa-token"
            self.expiry = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=1)

        with patch.object(service_account.Credentials, "refresh", mock_sa_refresh):
            manager = DualAccountManager(config_data=test_config, dry_run=False)
            session = manager.authenticate_account("lauburu@lauburugrappling.com")

            assert session.is_authenticated is True
            assert session.auth_method == "service_account_dwd"
            assert session.client is not None
            assert session.error is None

    def test_workspace_business_service_account_unauthorized_falls_back_to_api_key(self, monkeypatch):
        from google.auth.exceptions import RefreshError
        sa_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/service_account.json"
        test_config = {
            "accounts": {
                "lauburu@lauburugrappling.com": {
                    "account_id": "lauburu@lauburugrappling.com",
                    "role": "workspace_business",
                    "primary_cred_type": "oauth2_token",
                    "cred_file_path": "/non/existent/workspace_token.json",
                    "fallback_cred_type": "service_account_dwd",
                    "fallback_cred_file_path": sa_path,
                    "api_key_env_var": "TEST_WORKSPACE_API_KEY",
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
                }
            }
        }
        monkeypatch.setenv("TEST_WORKSPACE_API_KEY", "test-fallback-ws-key-123")

        def mock_unauthorized(self, req):
            raise RefreshError("unauthorized_client", {"error": "unauthorized_client"})

        with patch.object(service_account.Credentials, "refresh", mock_unauthorized):
            manager = DualAccountManager(config_data=test_config, dry_run=False)
            session = manager.authenticate_account("lauburu@lauburugrappling.com")

            assert session.is_authenticated is True
            assert session.auth_method == "api_key"
            assert session.client is not None
            assert session.error is None

    def test_workspace_business_service_account_unauthorized_without_api_key_fails_safely(self, monkeypatch):
        from google.auth.exceptions import RefreshError
        sa_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/service_account.json"
        test_config = {
            "accounts": {
                "lauburu@lauburugrappling.com": {
                    "account_id": "lauburu@lauburugrappling.com",
                    "role": "workspace_business",
                    "primary_cred_type": "oauth2_token",
                    "cred_file_path": "/non/existent/workspace_token.json",
                    "fallback_cred_type": "service_account_dwd",
                    "fallback_cred_file_path": sa_path,
                    "api_key_env_var": "MISSING_ENV_VAR_XYZ",
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
                }
            }
        }
        monkeypatch.delenv("MISSING_ENV_VAR_XYZ", raising=False)

        def mock_unauthorized(self, req):
            raise RefreshError("unauthorized_client", {"error": "unauthorized_client"})

        with patch.object(service_account.Credentials, "refresh", mock_unauthorized):
            manager = DualAccountManager(config_data=test_config, dry_run=False)
            session = manager.authenticate_account("lauburu@lauburugrappling.com")

            assert session.is_authenticated is False
            assert session.client is None
            assert session.error is not None
            assert "unauthorized_client" in session.error

    def test_workspace_business_token_refresh(self):
        manager = DualAccountManager(dry_run=False)
        manager.authenticate_account("lauburu@lauburugrappling.com")
        refreshed = manager.refresh_credentials("lauburu@lauburugrappling.com")
        assert refreshed is True
        session = manager.get_session("lauburu@lauburugrappling.com")
        assert session is not None
        assert session.is_authenticated is True


class TestClientIsolation:
    """Verifies that personal and workspace GenAI clients are completely isolated."""

    def test_dual_clients_have_distinct_identities(self):
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()

        client_personal = manager.get_genai_client("aaron.t.maher@gmail.com")
        client_workspace = manager.get_genai_client("lauburu@lauburugrappling.com")

        assert client_personal is not None
        assert client_workspace is not None
        # Identity uniqueness: instances must not be identical
        assert client_personal is not client_workspace

    def test_dual_clients_have_isolated_api_clients(self):
        manager = DualAccountManager(dry_run=False)
        manager.authenticate_all()

        client_personal = manager.get_genai_client("aaron.t.maher@gmail.com")
        client_workspace = manager.get_genai_client("lauburu@lauburugrappling.com")

        assert client_personal is not None
        assert client_workspace is not None
        assert client_personal._api_client is not client_workspace._api_client

    def test_env_var_isolation_no_bleed(self, monkeypatch):
        # Set a dummy global GEMINI_API_KEY in environment
        monkeypatch.setenv("GEMINI_API_KEY", "personal-env-key-999")
        monkeypatch.setenv("GEMINI_API_KEY_WORKSPACE", "workspace-env-key-888")

        manager = DualAccountManager(dry_run=True)
        sessions = manager.authenticate_all()

        # Both authenticate using their respective on-disk credentials rather than falling back to colliding env vars
        assert sessions["aaron.t.maher@gmail.com"].is_authenticated is True
        assert sessions["lauburu@lauburugrappling.com"].is_authenticated is True

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")
        assert c1 is not None and c2 is not None
        assert c1 is not c2
        assert c1._api_client is not c2._api_client

        h1 = c1._api_client._http_options.headers or {}
        h2 = c2._api_client._http_options.headers or {}
        auth1 = h1.get("Authorization") or h1.get("x-goog-api-key")
        auth2 = h2.get("Authorization") or h2.get("x-goog-api-key")
        assert auth1 is not None and auth2 is not None
        assert auth1 != auth2, "Authorization headers between personal and workspace must be distinct"
        assert auth2 != "personal-env-key-999", "Workspace client must not inherit ambient personal API key"
        assert getattr(c2._api_client, "api_key", None) != "personal-env-key-999"

    def test_status_manifest_isolation_verification(self):
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()

        manifest = manager.export_status_manifest()
        assert manifest["client_isolation_verified"] is True
        assert manifest["total_accounts"] == 2
        assert manifest["authenticated_accounts"] == 2
        assert "aaron.t.maher@gmail.com" in manifest["accounts"]
        assert "lauburu@lauburugrappling.com" in manifest["accounts"]


class TestEdgeCasesAndResilience:
    """Tests configuration edge cases, missing accounts, and resilience."""

    def test_authenticate_unknown_account_returns_unauthenticated(self):
        manager = DualAccountManager(dry_run=True)
        session = manager.authenticate_account("unknown@nowhere.com")

        assert session.is_authenticated is False
        assert session.auth_method == "none"
        assert "No account profile" in session.error

    def test_authenticate_inactive_account_skips_auth(self):
        test_config = {
            "accounts": {
                "inactive@example.com": {
                    "account_id": "inactive@example.com",
                    "role": "personal_admin",
                    "primary_cred_type": "adc",
                    "cred_file_path": "~/.config/gcloud/legacy_credentials/aaron.t.maher@gmail.com/adc.json",
                    "is_active": False
                }
            }
        }
        manager = DualAccountManager(config_data=test_config, dry_run=True)
        session = manager.authenticate_account("inactive@example.com")

        assert session.is_authenticated is False
        assert session.auth_method == "disabled"
        assert "inactive" in session.error

    def test_custom_config_loading(self):
        custom_config = {
            "accounts": {
                "custom@domain.org": {
                    "account_id": "custom@domain.org",
                    "role": "workspace_business",
                    "primary_cred_type": "api_key",
                    "api_key_env_var": "CUSTOM_KEY",
                    "rate_limit_rpm": 30
                }
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(custom_config, f)
            temp_path = f.name

        try:
            manager = DualAccountManager(config_path=temp_path, dry_run=True)
            profile = manager.get_profile("custom@domain.org")
            assert profile is not None
            assert profile.rate_limit_rpm == 30
            assert profile.role == AccountRole.WORKSPACE_BUSINESS
        finally:
            os.remove(temp_path)

    def test_missing_config_uses_default_profiles(self):
        manager = DualAccountManager(config_path="/non/existent/config.json", dry_run=True)
        assert "aaron.t.maher@gmail.com" in manager.profiles
        assert "lauburu@lauburugrappling.com" in manager.profiles

    def test_export_status_manifest_structure(self):
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()
        manifest = manager.export_status_manifest()

        assert "timestamp_utc" in manifest
        assert "dry_run" in manifest
        assert "total_accounts" in manifest
        assert "authenticated_accounts" in manifest
        assert "client_isolation_verified" in manifest
        assert "accounts" in manifest
        assert isinstance(manifest["accounts"], dict)


class TestAcceptanceCriteriaContract:
    """Verifies that acceptance criteria requirements are strictly met."""

    def test_both_accounts_authenticated_in_dry_run(self):
        """Acceptance Criteria: Script successfully authenticates with the required services

        and logs simulated sync output for both user accounts.
        """
        manager = create_dual_account_manager(dry_run=True)
        sessions = manager.authenticate_all()

        assert len(sessions) == 2
        assert "aaron.t.maher@gmail.com" in sessions
        assert "lauburu@lauburugrappling.com" in sessions

        for acct_id, session in sessions.items():
            assert session.is_authenticated is True
            assert session.auth_method == "simulated_dry_run"
            assert session.token_expiry is not None
            assert session.token_expiry > time.time()
            assert session.client is not None
            assert session.error is None

    def test_both_accounts_authenticated_in_live_run(self):
        """Authentic live verification: both accounts succeed in live mode."""
        manager = create_dual_account_manager(dry_run=False)
        sessions = manager.authenticate_all()

        assert len(sessions) == 2
        for acct_id, session in sessions.items():
            assert session.is_authenticated is True
            assert session.client is not None
            assert session.error is None


class TestAdvancedBoundaryAndCrossCombinations:
    """Tier 2 & Tier 3 boundary and cross-feature integration tests."""

    def test_token_expiry_extraction_various_formats(self):
        manager = DualAccountManager(dry_run=True)

        class DummyCreds:
            def __init__(self, expiry):
                self.expiry = expiry

        # None expiry
        assert manager._extract_expiry_timestamp(DummyCreds(None)) is None

        # Float/int expiry
        assert manager._extract_expiry_timestamp(DummyCreds(1700000000.5)) == 1700000000.5
        assert manager._extract_expiry_timestamp(DummyCreds(1700000000)) == 1700000000.0

        # Naive datetime
        dt_naive = datetime.datetime(2026, 10, 11, 12, 0, 0)
        ts_expected = dt_naive.replace(tzinfo=datetime.timezone.utc).timestamp()
        assert manager._extract_expiry_timestamp(DummyCreds(dt_naive)) == ts_expected

        # Aware datetime
        dt_aware = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=datetime.timezone.utc)
        assert manager._extract_expiry_timestamp(DummyCreds(dt_aware)) == ts_expected

    def test_authenticate_all_dry_run_override_parameter(self):
        manager = DualAccountManager(dry_run=False)
        sessions = manager.authenticate_all(dry_run=True)
        for s in sessions.values():
            assert s.auth_method == "simulated_dry_run"
            assert s.metadata.get("dry_run") is True

    def test_client_isolation_with_synthetic_credentials(self):
        from google.oauth2.credentials import Credentials
        creds_a = Credentials(
            token="token_a",
            refresh_token="ref_a",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="id_a",
            client_secret="sec_a"
        )
        creds_b = Credentials(
            token="token_b",
            refresh_token="ref_b",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="id_b",
            client_secret="sec_b"
        )
        manager = DualAccountManager(dry_run=True)
        c_a = manager._instantiate_genai_client(credentials=creds_a)
        c_b = manager._instantiate_genai_client(credentials=creds_b)
        assert c_a is not None
        assert c_b is not None
        assert c_a is not c_b
        assert c_a._api_client is not c_b._api_client

    def test_corrupt_workspace_token_gracefully_falls_back_to_service_account(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("MALFORMED_JSON_GARBAGE")
            bad_token_path = f.name

        sa_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/service_account.json"
        test_config = {
            "accounts": {
                "lauburu@lauburugrappling.com": {
                    "account_id": "lauburu@lauburugrappling.com",
                    "role": "workspace_business",
                    "primary_cred_type": "oauth2_token",
                    "cred_file_path": bad_token_path,
                    "fallback_cred_type": "service_account_dwd",
                    "fallback_cred_file_path": sa_path,
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
                }
            }
        }

        def mock_sa_refresh(self, req):
            self.token = "mock-valid-sa-token"
            self.expiry = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=1)

        try:
            with patch.object(service_account.Credentials, "refresh", mock_sa_refresh):
                manager = DualAccountManager(config_data=test_config, dry_run=False)
                session = manager.authenticate_account("lauburu@lauburugrappling.com")
                assert session.is_authenticated is True
                assert session.auth_method == "service_account_dwd"
        finally:
            os.remove(bad_token_path)

    def test_concurrent_independent_account_refresh(self):
        manager = DualAccountManager(dry_run=False)
        manager.authenticate_all()

        session_personal_before = manager.get_session("aaron.t.maher@gmail.com")
        session_ws_before = manager.get_session("lauburu@lauburugrappling.com")

        ok = manager.refresh_credentials("lauburu@lauburugrappling.com")
        assert ok is True

        session_personal_after = manager.get_session("aaron.t.maher@gmail.com")
        session_ws_after = manager.get_session("lauburu@lauburugrappling.com")

        assert session_personal_after.is_authenticated is True
        assert session_personal_after.auth_method == session_personal_before.auth_method
        assert session_ws_after.is_authenticated is True

    def test_factory_function_create_dual_account_manager(self):
        mgr = create_dual_account_manager(dry_run=True)
        assert isinstance(mgr, DualAccountManager)
        assert mgr.dry_run is True

