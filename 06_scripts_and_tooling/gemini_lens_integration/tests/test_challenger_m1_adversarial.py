"""Adversarial Challenge & Stress Test Suite for Milestone 1 (auth_manager.py).

Authored by challenger_m1_2.
Tests boundary conditions, corrupt configurations, invalid credentials,
zero permissions, missing environment variables, revoked tokens, and CLI behavior.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
import unittest.mock

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_manager import (
    AccountProfile,
    AccountRole,
    AccountSession,
    CredentialType,
    DualAccountManager,
    create_dual_account_manager,
)


class TestAdverseConfigurations:
    """Stress tests for malformed, corrupt, or missing configuration files."""

    def test_corrupt_json_config_raises_json_decode_error(self, tmp_path: Path):
        """Test behavior when config file contains invalid JSON syntax: raises JSONDecodeError."""
        corrupt_cfg = tmp_path / "corrupt_syntax.json"
        corrupt_cfg.write_text("{ this is not valid json !!!", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            DualAccountManager(config_path=corrupt_cfg)

    def test_empty_config_file_raises_json_decode_error(self, tmp_path: Path):
        """Test behavior when config file is empty (0 bytes): raises JSONDecodeError."""
        empty_cfg = tmp_path / "empty.json"
        empty_cfg.write_text("", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            DualAccountManager(config_path=empty_cfg)

    def test_config_with_empty_accounts_dict(self, tmp_path: Path):
        """Test config with valid JSON but empty accounts dictionary."""
        cfg_file = tmp_path / "empty_accounts.json"
        cfg_file.write_text(json.dumps({"accounts": {}}), encoding="utf-8")

        mgr = DualAccountManager(config_path=cfg_file)
        assert len(mgr.profiles) == 0
        sessions = mgr.authenticate_all(dry_run=True)
        assert len(sessions) == 0
        manifest = mgr.export_status_manifest()
        assert manifest["total_accounts"] == 0
        assert manifest["authenticated_accounts"] == 0

    def test_config_with_non_dict_accounts_handled_gracefully(self, tmp_path: Path):
        """Test config where accounts is a list instead of a dict: handled gracefully without crash."""
        cfg_file = tmp_path / "list_accounts.json"
        cfg_file.write_text(json.dumps({"accounts": ["account1", "account2"]}), encoding="utf-8")

        mgr = DualAccountManager(config_path=cfg_file)
        assert len(mgr.profiles) == 0
        manifest = mgr.export_status_manifest()
        assert manifest["total_accounts"] == 0


    def test_config_with_missing_account_id_raises_key_error(self, tmp_path: Path):
        """Test config where account profile dictionary misses required 'account_id'."""
        cfg_file = tmp_path / "missing_id.json"
        cfg_file.write_text(
            json.dumps({"accounts": {"bad_entry": {"role": "personal_admin"}}}),
            encoding="utf-8",
        )

        with pytest.raises(KeyError):
            DualAccountManager(config_path=cfg_file)

    def test_config_with_invalid_role_enum_raises_value_error(self, tmp_path: Path):
        """Test config where role is an unrecognized string."""
        cfg_file = tmp_path / "bad_role.json"
        cfg_file.write_text(
            json.dumps({
                "accounts": {
                    "test@example.com": {
                        "account_id": "test@example.com",
                        "role": "super_mega_admin_role_xyz"
                    }
                }
            }),
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            DualAccountManager(config_path=cfg_file)


class TestAdverseCredentialsAndPaths:
    """Stress tests for credential validation against bad files, zero permissions, etc."""

    def test_non_existent_credential_path_graceful(self):
        """Non-existent credential file should return (False, error) without raising."""
        mgr = DualAccountManager(dry_run=True)
        valid, err = mgr.validate_credentials_file(
            "/path/that/definitely/does/not/exist/999.json",
            CredentialType.ADC
        )
        assert not valid
        assert "File not found" in err

    def test_directory_passed_as_credential_file(self, tmp_path: Path):
        """Passing a directory instead of a file should fail gracefully without unhandled exception."""
        mgr = DualAccountManager(dry_run=True)
        valid, err = mgr.validate_credentials_file(tmp_path, CredentialType.ADC)
        assert not valid
        assert err is not None

    def test_zero_permission_credential_file(self, tmp_path: Path):
        """File with 000 permissions (unreadable) should return (False, error) without crash."""
        unreadable_file = tmp_path / "unreadable_adc.json"
        unreadable_file.write_text('{"client_id": "test", "refresh_token": "xyz"}', encoding="utf-8")
        unreadable_file.chmod(0o000)

        mgr = DualAccountManager(dry_run=True)
        try:
            valid, err = mgr.validate_credentials_file(unreadable_file, CredentialType.ADC)
            assert not valid
            assert "Permission" in err or "Invalid" in err
        finally:
            unreadable_file.chmod(0o644)  # Restore for cleanup

    def test_corrupt_json_in_credential_file(self, tmp_path: Path):
        """File with corrupt JSON content should return (False, error)."""
        bad_json = tmp_path / "bad_json.json"
        bad_json.write_text("This is NOT JSON", encoding="utf-8")

        mgr = DualAccountManager(dry_run=True)
        valid, err = mgr.validate_credentials_file(bad_json, CredentialType.ADC)
        assert not valid
        assert "Invalid JSON" in err

    def test_non_dict_json_in_credential_file(self, tmp_path: Path):
        """Credential file with JSON array instead of object."""
        array_json = tmp_path / "array_adc.json"
        array_json.write_text('["client_id", "refresh_token"]', encoding="utf-8")

        mgr = DualAccountManager(dry_run=True)
        for ctype in [CredentialType.ADC, CredentialType.OAUTH2_TOKEN, CredentialType.SERVICE_ACCOUNT_DWD]:
            valid, err = mgr.validate_credentials_file(array_json, ctype)
            assert not valid
            assert "not a JSON object" in err

    def test_empty_json_object_in_credential_file(self, tmp_path: Path):
        """Credential file with empty object {} missing required fields."""
        empty_obj = tmp_path / "empty_obj.json"
        empty_obj.write_text("{}", encoding="utf-8")

        mgr = DualAccountManager(dry_run=True)
        for ctype in [CredentialType.ADC, CredentialType.OAUTH2_TOKEN, CredentialType.SERVICE_ACCOUNT_DWD]:
            valid, err = mgr.validate_credentials_file(empty_obj, ctype)
            assert not valid
            assert "missing" in err.lower() or "invalid" in err.lower()


class TestMissingEnvAndStrippedEnvironment:
    """Stress tests under completely stripped or missing environment variables."""

    def test_dry_run_with_clean_environment(self, monkeypatch):
        """Dry-run should succeed using genuine on-disk credentials even when all GEMINI env vars are stripped."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY_WORKSPACE", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

        mgr = DualAccountManager(dry_run=True)
        sessions = mgr.authenticate_all()
        assert len(sessions) == 2
        for s in sessions.values():
            assert s.is_authenticated, f"Account {s.account_id} failed with: {s.error}"

    def test_fallback_api_key_when_env_var_missing(self, monkeypatch, tmp_path: Path):
        """When primary creds fail and fallback is API_KEY but env var is missing, degradation should be graceful."""
        monkeypatch.delenv("NON_EXISTENT_KEY_VAR", raising=False)

        profile = AccountProfile(
            account_id="test@example.com",
            role=AccountRole.PERSONAL_ADMIN,
            primary_cred_type=CredentialType.ADC,
            cred_file_path=tmp_path / "missing_adc.json",
            fallback_cred_type=CredentialType.API_KEY,
            api_key_env_var="NON_EXISTENT_KEY_VAR"
        )

        mgr = DualAccountManager(dry_run=True, config_data={"accounts": {}})
        mgr.profiles["test@example.com"] = profile

        # Dry run
        session_dry = mgr.authenticate_account("test@example.com", dry_run=True)
        assert not session_dry.is_authenticated
        assert "Credentials validation failed" in session_dry.error

        # Live run
        session_live = mgr.authenticate_account("test@example.com", dry_run=False)
        assert not session_live.is_authenticated
        assert session_live.error is not None


class TestRevokedAndExpiredTokens:
    """Stress tests simulating expired or invalid tokens."""

    def test_expired_token_live_refresh_failure_graceful(self, tmp_path: Path):
        """When live token refresh fails (e.g. invalid refresh token), it must not crash with unhandled exception."""
        bogus_token = tmp_path / "bogus_refresh_token.json"
        bogus_token.write_text(json.dumps({
            "token": "expired_dummy_access_token",
            "refresh_token": "revoked_or_invalid_refresh_token_12345",
            "client_id": "dummy_client.apps.googleusercontent.com",
            "client_secret": "dummy_secret",
            "token_uri": "https://oauth2.googleapis.com/token",
            "expiry": "2020-01-01T00:00:00Z"
        }), encoding="utf-8")

        profile = AccountProfile(
            account_id="expired_test@example.com",
            role=AccountRole.WORKSPACE_BUSINESS,
            primary_cred_type=CredentialType.OAUTH2_TOKEN,
            cred_file_path=bogus_token,
            fallback_cred_type=None
        )

        mgr = DualAccountManager(dry_run=False, config_data={"accounts": {}})
        mgr.profiles["expired_test@example.com"] = profile

        session = mgr.authenticate_account("expired_test@example.com", dry_run=False)
        assert not session.is_authenticated
        assert session.client is None
        assert session.error is not None
        assert "failed" in session.error.lower() or "error" in session.error.lower()

    def test_revoked_token_in_dry_run_is_accepted_on_schema_only(self, tmp_path: Path):
        """In dry-run mode, on-disk schema is checked without network token revocation check."""
        bogus_token = tmp_path / "bogus_dry_token.json"
        bogus_token.write_text(json.dumps({
            "token": "dummy_token",
            "refresh_token": "dummy_refresh",
            "client_id": "client.apps.googleusercontent.com",
            "client_secret": "secret"
        }), encoding="utf-8")

        profile = AccountProfile(
            account_id="dry_test@example.com",
            role=AccountRole.WORKSPACE_BUSINESS,
            primary_cred_type=CredentialType.OAUTH2_TOKEN,
            cred_file_path=bogus_token
        )

        mgr = DualAccountManager(dry_run=True, config_data={"accounts": {}})
        mgr.profiles["dry_test@example.com"] = profile

        session = mgr.authenticate_account("dry_test@example.com", dry_run=True)
        assert session.is_authenticated
        assert session.metadata.get("dry_run") is True

    def test_dry_run_refresh_credentials_does_not_trigger_network(self):
        """Document empirical behavior: refresh_credentials on dry_run session bypasses network call."""
        mgr = DualAccountManager(dry_run=True)
        mgr.authenticate_all()
        # Verify that refresh_credentials in dry-run mode does not call Request()
        with unittest.mock.patch("google.auth.transport.requests.Request.__call__", side_effect=Exception("NETWORK_BLOCKED")) as mock_req:
            res = mgr.refresh_credentials("lauburu@lauburugrappling.com")
            assert res is True
            assert mock_req.called is False



class TestCLIExecutionAndFlags:
    """Stress tests on CLI execution, arguments, and stdout cleanliness."""

    def test_cli_dry_run_exit_code_zero(self):
        """Verify CLI execution with --dry-run returns exit code 0."""
        cmd = ["/opt/homebrew/bin/python3", "auth_manager.py", "--dry-run"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 0, f"CLI dry run exited with {res.returncode}. Stderr: {res.stderr}"

    def test_cli_stdout_contains_logger_pollution(self):
        """Empirically test whether CLI stdout has log pollution before JSON.
        
        Logger StreamHandler writes to sys.stderr!
        Direct json.loads(res.stdout) succeeds cleanly without JSONDecodeError.
        """
        cmd = ["/opt/homebrew/bin/python3", "auth_manager.py", "--dry-run"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["dry_run"] is True
        assert data["client_isolation_verified"] is True
        assert data["total_accounts"] == 2
        assert data["authenticated_accounts"] == 2

    def test_cli_custom_config_flag(self, tmp_path: Path):
        """Verify CLI --config flag loads custom configuration."""
        custom_cfg = tmp_path / "custom_sync.json"
        custom_cfg.write_text(json.dumps({
            "accounts": {
                "custom@example.com": {
                    "account_id": "custom@example.com",
                    "role": "personal_admin",
                    "primary_cred_type": "adc",
                    "cred_file_path": str(Path("~/.config/gcloud/legacy_credentials/aaron.t.maher@gmail.com/adc.json").expanduser()),
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
                }
            }
        }), encoding="utf-8")

        cmd = [
            "/opt/homebrew/bin/python3",
            "auth_manager.py",
            "--dry-run",
            "--config",
            str(custom_cfg)
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 0
        json_start = res.stdout.find("{")
        data = json.loads(res.stdout[json_start:])
        assert data["total_accounts"] == 1
        assert "custom@example.com" in data["accounts"]

    def test_cli_unrecognized_argument_account_flag(self):
        """Empirically test whether --account is supported by auth_manager.py CLI."""
        cmd = [
            "/opt/homebrew/bin/python3",
            "auth_manager.py",
            "--dry-run",
            "--account",
            "aaron.t.maher@gmail.com"
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert "aaron.t.maher@gmail.com" in data["accounts"]
        assert len(data["accounts"]) == 1


    def test_cli_exit_code_1_on_failed_authentication(self, tmp_path: Path):
        """CLI should exit with code 1 when an account fails authentication."""
        failing_cfg = tmp_path / "failing_sync.json"
        failing_cfg.write_text(json.dumps({
            "accounts": {
                "failing@example.com": {
                    "account_id": "failing@example.com",
                    "role": "personal_admin",
                    "primary_cred_type": "adc",
                    "cred_file_path": "/non/existent/adc.json"
                }
            }
        }), encoding="utf-8")

        cmd = [
            "/opt/homebrew/bin/python3",
            "auth_manager.py",
            "--dry-run",
            "--config",
            str(failing_cfg)
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 1
        json_start = res.stdout.find("{")
        data = json.loads(res.stdout[json_start:])
        assert data["authenticated_accounts"] == 0
